#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 PaddleOCR 的「结果序号」对齐回 PDF 物理页。

背景（R2-03-R1 实测）：
  PaddleOCR-VL-1.6 异步接口把 PDF 切成每 3 页一个分片返回，
  每行 jsonl 含 3 个 layoutParsingResults，但**分片返回顺序不是 PDF 页序**。
  skill 的 save_results 按结果顺序递增 page 字段，导致 page 与 PDF 物理页
  出现 +3~+15 的累计漂移。直接按 page 内连接 Vision 结果会得到错误对照。

本工具用「汉字多重集合 Jaccard」在 ±WINDOW 页窗口内为每页找最相似页，
建立 paddle_page -> pdf_page 映射，供 paddle_rerun.py compare 使用。
不修改、不覆盖任何 OCR 原文。

用法：
  python3 tools/paddle_align.py            # 产出 alignment.json 与终端报告
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import paddle_rerun as pr

WINDOW = 25
MIN_SIM = 0.55
OUT = pr.PADDLE_ROOT / "alignment.json"


def counters(rows: dict[int, dict]) -> dict[int, Counter]:
    return {p: Counter(pr.han_only(r["text"])) for p, r in rows.items()}


def jaccard(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    inter = sum((a & b).values())
    union = sum((a | b).values())
    return inter / union if union else 0.0


def main() -> int:
    result: dict[str, dict] = {}
    for book_id, _ in pr.BOOK_SPECS:
        vp = pr.VISION_ROOT / book_id / "pages.jsonl"
        pp = pr.PADDLE_ROOT / book_id / "pages.jsonl"
        if not (vp.exists() and pp.exists()):
            print(f"[跳过] {book_id}: 缺少输入")
            continue
        vision, paddle = pr.load_jsonl(vp), pr.load_jsonl(pp)
        vc, pc = counters(vision), counters(paddle)
        # 先按汉字数粗筛，避免明显不匹配的页做集合运算
        vlen = {p: sum(c.values()) for p, c in vc.items()}
        plen = {q: sum(c.values()) for q, c in pc.items()}

        # 全局降序贪心：先收集所有候选，再按置信度从高到低做一对一分配。
        # 按 Vision 页序逐个抢占会让低置信页抢走高置信页的正确位置，覆盖率骤降。
        candidates: list[tuple[float, int, int]] = []
        for p in sorted(vc):
            if vlen[p] < 30:
                continue
            for q in range(max(0, p - WINDOW), min(max(plen) + 1, p + WINDOW + 1)):
                if q not in pc or plen[q] < 30:
                    continue
                if abs(vlen[p] - plen[q]) / max(vlen[p], plen[q]) > 0.65:
                    continue
                s = jaccard(vc[p], pc[q])
                if s >= MIN_SIM:
                    candidates.append((s, p, q))
        candidates.sort(reverse=True)
        mapping: dict[int, int] = {}   # paddle_page -> pdf_page
        sims: list[float] = []
        used_p: set[int] = set()
        for s, p, q in candidates:
            if p in used_p or q in mapping:
                continue
            mapping[q] = p
            used_p.add(p)
            sims.append(s)

        offsets = sorted(q - p for q, p in mapping.items())
        info = {
            "engine_paddle": pr.ENGINE,
            "engine_vision": "macos-vision-rev2",
            "vision_pages": len(vision),
            "paddle_pages": len(paddle),
            "aligned_pages": len(mapping),
            "coverage": round(len(mapping) / len(vision), 4),
            "mean_sim": round(sum(sims) / len(sims), 4) if sims else 0,
            "min_sim": round(min(sims), 4) if sims else 0,
            "offset_min": offsets[0] if offsets else None,
            "offset_max": offsets[-1] if offsets else None,
            "window": WINDOW,
            "min_sim_threshold": MIN_SIM,
            "method": "汉字多重集合 Jaccard，±25 页窗口，贪心唯一匹配",
            "mapping": {str(q): p for q, p in sorted(mapping.items())},
        }
        result[book_id] = info
        print(f"  {book_id:20s} 对齐 {info['aligned_pages']:4d}/{info['vision_pages']:4d} "
              f"({info['coverage']*100:.1f}%)  平均相似 {info['mean_sim']}  "
              f"偏移范围 {info['offset_min']:+d}~{info['offset_max']:+d}")

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n映射已写入 {OUT}")
    print("注意：未达阈值的页不参与对齐，compare 会显式标注 aligned=0，不做猜测配对。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
