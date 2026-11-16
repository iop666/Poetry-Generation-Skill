#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 poetry_rules_r2_05 的引文替换为源文本中的逐字原文（含原书引号）。

规则：把引号类字符统一归一后做定位，再用原文切片回填，
      保证入库引文与 OCR 文本完全一致（不是模型改写）。
"""
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import importlib.util
spec = importlib.util.spec_from_file_location("dump", ROOT / "tools/r2_05_dump.py")
dump = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dump)

QUOTES = str.maketrans({
    "“": '"', "”": '"', "‘": "'", "’": "'",
    "「": '"', "」": '"', "『": '"', "』": '"',
    "《": "<", "》": ">",
    # 原书大量使用 ASCII 括号，引文常被写成全角；归一后才能定位，
    # 回填时取原文切片，因此入库引文仍是原书的 ASCII 括号。
    "（": "(", "）": ")", "，": ",", "：": ":", "；": ";",
    "！": "!", "？": "?", "、": ",",
})
WS = re.compile(r"[\s\u3000]+")


def norm(s: str) -> str:
    return WS.sub("", s.translate(QUOTES))


def main() -> int:
    rows = dump.load()
    con = sqlite3.connect(ROOT / "database/poetry.db")
    items = con.execute("SELECT rule_id,book_code,pdf_page,quote FROM poetry_rules_r2_05 "
                        "WHERE book_code IN ('A','B')").fetchall()
    fixed, failed = 0, []
    for rid, bc, pdf, quote in items:
        window = "".join(rows.get(p, "") for p in range(pdf, pdf + 3))
        if not window:
            failed.append((rid, "无文本"))
            continue
        # 逐段定位（引文以 …… 分段）
        parts = [p for p in quote.split("……") if p.strip()]
        out, cur = [], 0
        ok = True
        nw = norm(window)
        # 归一化后的位置 → 原文位置映射
        idx_map, k = [], 0
        for ch in window:
            if WS.match(ch):
                continue
            idx_map.append(k)
            k += 1
        # 反查：norm 后第 i 个字符对应 window 的下标
        keep = [i for i, ch in enumerate(window) if not WS.match(ch)]

        for part in parts:
            np_ = norm(part)
            # 去掉首尾标点做容错
            probe = np_.strip('，。；：、,.;:')
            if len(probe) < 6:
                ok = False
                break
            j = nw.find(probe, cur)
            if j < 0:
                ok = False
                break
            start = keep[j]
            end = keep[j + len(probe) - 1] + 1
            out.append(window[start:end])
            cur = j + len(probe)
        if ok and out:
            newq = "……".join(out)
            if newq != quote:
                con.execute("UPDATE poetry_rules_r2_05 SET quote=? WHERE rule_id=?", (newq, rid))
                fixed += 1
        else:
            failed.append((rid, "定位失败"))
    con.commit()
    con.close()
    print(f"回填 {fixed} 条；失败 {len(failed)} 条")
    for f in failed:
        print("  ", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
