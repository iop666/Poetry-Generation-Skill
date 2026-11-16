#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
coverage.py + cards —— 历史时期覆盖率统计 + 100 首代表性作品研究卡

输出：
  audit/coverage.json
  audit/coverage.md
  research/poetry_analysis/cards_auto.md     100 首结构化卡（自动生成，待复核）
  catalog/cards.jsonl
"""

from __future__ import annotations

import collections
import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "database", "poetry.db")
AUDIT = os.path.join(BASE, "audit")
RES = os.path.join(BASE, "research", "poetry_analysis")

# 任务书要求覆盖的历史时期
PERIODS = ["先秦", "汉代", "魏晋南北朝", "隋代", "唐代", "五代", "宋代", "辽代", "金代", "元代", "明代", "清代"]
# ROUND 2-01：新增 魏晋南北朝 / 隋 / 金 / 明 四类（前两代由《古詩紀》补，金由《中州集》补，明由《明詩綜》补）
DYN_MAP = {"先秦": "先秦", "汉魏": "汉代", "魏晋南北朝": "魏晋南北朝", "隋": "隋代",
           "唐": "唐代", "五代": "五代", "宋": "宋代", "金": "辽金",
           "元": "元代", "明": "明代", "清": "清代",
           # 审核意见：不得用「辽金」合并掩盖辽代为零，必须分列
           "金": "金代", "辽": "辽代", "未定": "未定（朝代不可判）"}

# 100 首取样：按 朝代 × 体裁 分层，兼顾名家与非名家
SAMPLE_PLAN = [
    ("先秦", "四言诗", 6), ("先秦", "楚辞", 4), ("汉魏", "古体诗", 4),
    ("唐", "五言绝句", 8), ("唐", "七言绝句", 8), ("唐", "五言律诗", 8),
    ("唐", "七言律诗", 8), ("唐", "古体诗", 8), ("唐", "五言排律", 3),
    ("五代", "词", 5),
    ("宋", "词", 14), ("宋", "七言绝句", 6), ("宋", "七言律诗", 6),
    ("宋", "五言绝句", 3), ("宋", "古体诗", 3),
    ("元", "曲", 5), ("清", "词", 4),
]


def main() -> int:
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    os.makedirs(AUDIT, exist_ok=True)
    os.makedirs(RES, exist_ok=True)

    # ---------- 覆盖率 ----------
    rows = c.execute("SELECT dynasty, genre, COUNT(*) n FROM works GROUP BY dynasty, genre").fetchall()
    by_period = collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        by_period[DYN_MAP.get(r["dynasty"], r["dynasty"] or "未标")][r["genre"]] += r["n"]

    total = c.execute("SELECT COUNT(*) FROM works").fetchone()[0]
    cov = {"作品总数": total, "分时期": {}, "缺口": []}
    for p in PERIODS:
        g = dict(by_period.get(p, {}))
        n = sum(g.values())
        cov["分时期"][p] = {"作品数": n, "体裁": g}
        if n == 0:
            cov["缺口"].append(p)

    # 名家覆盖
    # 用 author_canonical 而非 author_s：ROUND 2-01 的名家缺口（陶渊明=0、曹植=0）
    # 实为解析缺陷 —— 同一人被拆成「陶淵明／陶潛」「陳思王植／曹植」两串。
    # author_canonical 已在 author_canon.py 归并，此处改用它，并保留显示名。
    CELEBS = ["屈原", "陶渊明", "曹植", "李白", "杜甫", "王维", "孟浩然", "白居易",
              "李商隐", "苏轼", "辛弃疾", "李清照", "柳永", "陆游", "黄庭坚", "姜夔", "纳兰性德"]
    DISPLAY = {"陶渊明": "陶潜"}     # 规范名用「陶潜」（本名），显示沿用通行称法
    celebs = {}
    for a in CELEBS:
        key = DISPLAY.get(a, a)
        celebs[a] = c.execute(
            "SELECT COUNT(*) FROM works WHERE author_canonical=?", (key,)).fetchone()[0]
    cov["名家覆盖"] = celebs
    cov["名家缺口"] = [k for k, v in celebs.items() if v == 0]

    with open(os.path.join(AUDIT, "coverage.json"), "w", encoding="utf-8") as f:
        json.dump(cov, f, ensure_ascii=False, indent=1)

    md = ["# 历史时期覆盖率（自动生成）", "",
          f"作品总数：{total:,}", "",
          "| 时期 | 作品数 | 主要体裁 |", "|---|---|---|"]
    for p in PERIODS:
        d = cov["分时期"][p]
        gs = "、".join(f"{k}{v:,}" for k, v in sorted(d["体裁"].items(), key=lambda x: -x[1])[:4])
        md.append(f"| {p} | {d['作品数']:,} | {gs or '**无**'} |")
    # 「未定」不属任何一朝，单列，禁止并入总数冒充覆盖
    un = dict(by_period.get("未定（朝代不可判）", {}))
    if un:
        cov["分时期"]["未定（朝代不可判）"] = {"作品数": sum(un.values()), "体裁": un}
        md.append(f"| 未定（朝代不可判） | {sum(un.values()):,} | "
                  + "、".join(f"{k}{v:,}" for k, v in sorted(un.items(), key=lambda x: -x[1])[:4]) + " |")
    md += ["", "## 名家覆盖", "", "| 作者 | 作品数 |", "|---|---|"]
    for k, v in sorted(celebs.items(), key=lambda x: -x[1]):
        md.append(f"| {k} | {v:,}{' **缺失**' if v == 0 else ''} |")
    md += ["", "## 缺口", ""]
    md.append("- 完全无作品的时期：" + ("、".join(cov["缺口"]) if cov["缺口"] else "无"))
    md.append("- 无作品的名家：" + ("、".join(cov["名家缺口"]) if cov["名家缺口"] else "无"))
    md.append("- 说明：本库不含《先秦汉魏晋南北朝诗》《全明诗》《全清诗》等总集，"
              "汉魏六朝、辽金、明、清三代覆盖极薄，属本轮已知缺口，不是数据错误。")
    with open(os.path.join(AUDIT, "coverage.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    # ---------- 100 首研究卡 ----------
    cards = []
    used = set()
    for dynasty, genre, n in SAMPLE_PLAN:
        q = """SELECT * FROM works WHERE dynasty=? AND genre=? AND dup_status!='DUPLICATE'
               ORDER BY char_count DESC, author_name LIMIT ?"""
        pool = c.execute(q, (dynasty, genre, n * 3)).fetchall()
        # 作者去重采样：先每作者取一首，不足再补
        picked, seen_auth = [], set()
        for r in pool:
            if r["author_name"] in seen_auth:
                continue
            seen_auth.add(r["author_name"])
            picked.append(r)
            if len(picked) >= n:
                break
        if len(picked) < n:
            for r in pool:
                if r["work_id"] not in {p["work_id"] for p in picked}:
                    picked.append(r)
                if len(picked) >= n:
                    break
        for r in picked:
            if r["work_id"] in used:
                continue
            used.add(r["work_id"])
            text = r["text_norm"]
            sents = [s for s in re.split(r"[，。；！？]", "，".join(
                [text[i:i + 7] for i in range(0, 0)])) if s]  # 占位，不使用
            cards.append({
                "work_id": r["work_id"],
                "标题": r["title_norm"], "作者": r["author_name"], "朝代": r["dynasty"],
                "体裁": r["genre"], "词牌": r["cipai"],
                "字数": len(text), "正文": text,
                "来源": r["source_id"], "版本": "chinese-poetry 整理本（未对勘）",
                "核验状态": r["verify_status"], "自动标注": True,
            })

    with open(os.path.join(BASE, "catalog", "cards.jsonl"), "w", encoding="utf-8") as f:
        for x in cards:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")

    md2 = ["# 代表性作品研究卡（100 首，自动生成）", "",
           "> 本文件由 `tools/coverage.py` 生成。**除原文与出处外，各字段均为程序自动推导**，",
           "> 未逐首人工校验，`核验状态` 一律标 AUTO。人工精读的 12 首见 `cards_manual.md`。",
           "> 原文取自 chinese-poetry 整理本，未与印本对勘；引用前须核底本。", ""]
    for i, x in enumerate(cards, 1):
        md2.append(f"## {i:03d}　{x['作者']}《{x['标题']}》")
        md2.append("")
        md2.append(f"- 朝代／体裁：{x['朝代']}／{x['体裁']}" + (f"（词牌 {x['词牌']}）" if x["词牌"] else ""))
        md2.append(f"- 字数：{x['字数']}")
        md2.append(f"- 来源：`{x['来源']}`　版本：{x['版本']}")
        md2.append(f"- 核验：{x['核验状态']}（自动标注，未复核）")
        md2.append("")
        md2.append(f"> {x['正文']}")
        md2.append("")
    with open(os.path.join(RES, "cards_auto.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md2) + "\n")

    print(f"覆盖率：{len(PERIODS)} 个时期，缺口 {len(cov['缺口'])} 个；名家缺口 {len(cov['名家缺口'])} 位")
    print(f"研究卡：{len(cards)} 首 → research/poetry_analysis/cards_auto.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
