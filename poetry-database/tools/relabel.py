#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
relabel.py —— 质量标签修正（ROUND 2-01 五）

外部审核 R2 的两条更正，本脚本逐条落实：

1. 「377 组学术归属争议」→ 全部改标 `CROSS_AUTHOR_ATTRIBUTION_CANDIDATE`
   （跨作者归属冲突**候选**）。程序只能证明「同一正文被登记在不同作者名下」，
   可能真争议，也可能是误录／重出／共用诗句／整理错误。

2. 「4,793 组同名异文」→ 细分为五类候选：
      SERIES_POEM        同题组诗（其一／其二／三首…）
      TRUE_VARIANT       两版长度相近且差异极小 —— 真异文候选
      PARTIAL_DUPLICATE  一版是另一版的前缀（截断／残篇）
      DUPLICATE_DATA     归一化后完全相同（本应已被去重，残留者说明字段差异）
      UNKNOWN            程序无法判断，保持待人工

刻意不做的事：**不裁决哪一版正确**。归属与异文取舍属文献考据，程序只分类。
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import re
import sqlite3
from difflib import SequenceMatcher

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "database", "poetry.db")

SERIES_RE = re.compile(
    r"(其[一二三四五六七八九十]|[一二三四五六七八九十]首$|（[一二三四五六七八九十]）|\([一二三四五六七八九十]\))"
)
TITLE_TAIL_NUM = re.compile(r"[·・]?其[一二三四五六七八九十]$")


def classify(texts: list[str], title: str) -> tuple:
    """返回 (类别, 依据)。只做形态判断，不做学术判断。"""
    if SERIES_RE.search(title or ""):
        return "SERIES_POEM", "标题含「其N／N首／（N）」"
    uniq = sorted(set(texts))
    if len(uniq) == 1:
        return "DUPLICATE_DATA", "归一化后正文相同"
    for a in uniq:
        for b in uniq:
            if a != b and len(a) < len(b) and b.startswith(a):
                return "PARTIAL_DUPLICATE", f"短版是长版前缀（{len(a)}/{len(b)} 字）"
    if len(uniq) == 2:
        a, b = uniq
        if abs(len(a) - len(b)) <= max(2, int(0.06 * max(len(a), len(b)))):
            r = SequenceMatcher(None, a, b).ratio()
            if r >= 0.90:
                return "TRUE_VARIANT", f"长度相近、相似度 {r:.3f}"
    return "UNKNOWN", "形态不足以判断，保持待人工"


def main() -> int:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    conn.execute("DELETE FROM attribution_candidates")
    conn.execute("DELETE FROM variant_candidates")

    rows = conn.execute("""SELECT work_id, author_name, title_norm, text_norm, collection,
                                  source_id FROM works""").fetchall()
    byid = {r["work_id"]: r for r in rows}

    # ---------- 1. 跨作者归属冲突候选 ----------
    by_text = collections.defaultdict(list)
    for r in rows:
        by_text[r["text_norm"]].append(r)
    n_attr = 0
    for h, group in by_text.items():
        authors = {g["author_name"] for g in group}
        if len(authors) > 1:
            gid = "CA:" + hashlib.sha1(h.encode()).hexdigest()[:12]
            conn.execute("INSERT OR REPLACE INTO attribution_candidates VALUES (?,?,?,?,?,?,?,?,?)", (
                gid, hashlib.sha1(h.encode()).hexdigest()[:16],
                "CROSS_AUTHOR_ATTRIBUTION_CANDIDATE",
                "SAME_TEXT_DIFFERENT_AUTHOR",
                "／".join(sorted(authors)),
                "／".join(g["work_id"] for g in group),
                len(group),
                f"同一正文（{len(h)} 字）登记于 {len(authors)} 位作者名下；"
                f"涉及集合 {'、'.join(sorted({g['collection'] for g in group}))}",
                "UNRESOLVED"))
            n_attr += 1

    # ---------- 2. 异文候选分流 ----------
    by_name = collections.defaultdict(list)
    for r in rows:
        by_name[(r["author_name"], r["title_norm"])].append(r)
    stat = collections.Counter()
    n_var = 0
    for (author, title), group in by_name.items():
        texts = [g["text_norm"] for g in group]
        if len(texts) > 1 and len(set(texts)) > 1:
            cat, basis = classify(texts, title)
            gid = "VC:" + hashlib.sha1((author + "|" + title).encode()).hexdigest()[:12]
            conn.execute("INSERT INTO variant_candidates VALUES (?,?,?,?,?,?,?,?)", (
                gid, cat, author, title,
                "／".join(g["work_id"] for g in group), len(group),
                basis, "UNRESOLVED"))
            stat[cat] += 1
            n_var += 1

    conn.commit()
    print(f"[归属候选] {n_attr} 组（全部标 CROSS_AUTHOR_ATTRIBUTION_CANDIDATE）")
    print(f"[异文候选] {n_var} 组，分流如下：")
    for k, v in stat.most_common():
        print(f"    {k:18} {v}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
