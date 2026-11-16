#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect_polyphones.py —— 汇总「因平仄两收而无法判定」的字，作为 ROUND 2 消歧表的输入清单。

不猜读音，只做统计：哪些字、在哪一句、韵书给了哪几个读音、共出现几次。
输出 reports/round-1-audit/logs/polyphone_pending.json 与同名 .md。
"""

from __future__ import annotations

import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(BASE, "engine"))

from gedou import UNKNOWN, check_ci, check_poem  # noqa: E402
from yunshu import LEX, POLICY_LENIENT  # noqa: E402

LOGDIR = os.path.join(BASE, "reports", "round-1-audit", "logs")


def corpus():
    """测试集全部样本 + 创作库作品卡中的诗句。"""
    out = []
    for path in sorted(glob.glob(os.path.join(BASE, "tests", "*.json"))):
        spec = json.load(open(path, encoding="utf-8"))
        cases = list(spec.get("样本", []))
        if spec.get("基线"):
            cases.append(spec["基线"])
        for c in cases:
            out.append((os.path.basename(path) + "/" + c.get("id", "?"), c.get("词牌"), c["文"]))
    return out


def main() -> int:
    hits = collections.defaultdict(lambda: {"次数": 0, "读音": [], "位置": []})
    total_unknown = 0
    per_case = []

    for cid, cipai, text in corpus():
        try:
            res = check_ci(text, cipai, cid) if cipai else check_poem(text, cid)
        except SystemExit:
            continue
        n_unknown = 0
        rows = res.get("平仄", []) if cipai else res.get("平仄表", [])
        for row in rows:
            for cell in row["格"]:
                if cell["状态"] != UNKNOWN:
                    continue
                ch = cell["字"]
                if LEX.tone_state(ch) != "两读":
                    continue
                n_unknown += 1
                info = hits[ch]
                info["次数"] += 1
                info["读音"] = [f"{r['g']}{r['y']}" for r in LEX.readings(ch)]
                info["位置"].append(f"{cid} 第{row['句']}句第{cell['第']}字")
        total_unknown += n_unknown
        per_case.append({"用例": cid, "待确认字数": n_unknown})

    rows = sorted(hits.items(), key=lambda kv: (-kv[1]["次数"], kv[0]))
    data = {
        "说明": "「因平仄两收而返回 UNKNOWN」的字频统计。本表是 ROUND 2 消歧表的输入，不是读音结论。",
        "样本来源": "tests/*.json 全部样本",
        "涉及字数": len(rows),
        "待判定位置合计": total_unknown,
        "白名单字数": len(POLICY_LENIENT),
        "白名单": sorted(POLICY_LENIENT),
        "字频": [{"字": ch, **v} for ch, v in rows],
        "按用例": per_case,
    }
    os.makedirs(LOGDIR, exist_ok=True)
    with open(os.path.join(LOGDIR, "polyphone_pending.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    md = ["# 多音字待消歧清单（自动生成）", "",
          "> 由 `tools/collect_polyphones.py` 生成。只统计「因平仄两收、无法据义定音而返回 UNKNOWN」的位置，",
          "> 不含白名单放宽与真正未收录的字。本表不是读音结论，是 ROUND 2 的工作输入。", "",
          f"- 涉及字数：{len(rows)}",
          f"- 待判定位置：{total_unknown}",
          f"- 白名单字数：{len(POLICY_LENIENT)}（{'、'.join(sorted(POLICY_LENIENT))}）", "",
          "| 字 | 出现次数 | 韵书所载读音 | 出现位置 |", "|---|---|---|---|"]
    for ch, v in rows:
        md.append(f"| {ch} | {v['次数']} | {'／'.join(v['读音'])} | {'；'.join(v['位置'][:3])}"
                  + ("…" if len(v["位置"]) > 3 else "") + " |")
    with open(os.path.join(LOGDIR, "polyphone_pending.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"涉及 {len(rows)} 字，待判定位置 {total_unknown} 处")
    for ch, v in rows[:15]:
        print(f"  {ch} ×{v['次数']}　{'／'.join(v['读音'])}")
    print(f"[写入] {os.path.relpath(LOGDIR, BASE)}/polyphone_pending.json / .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
