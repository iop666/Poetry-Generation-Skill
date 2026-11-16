#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 F：例詞—作品關聯質量審計。

R2-08 的 match_kind 只看「檢索命中方式」，不是證據等級。本輪重新以
  (1) 正規化後是否完全相等
  (2) 例詞是否為作品之子串（節錄）
  (3) 相似度與長度比
  (4) 作者是否一致
重新判級，並把「只靠標題」與「作者不同」的關聯一律降級。

輸出 example_work_links_r2_09 與 EXAMPLE_WORK_LINKS.csv。
"""
import os
import re
import json
import csv
import sqlite3
import difflib
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
OUT = os.path.join(ROOT, "raw", "r2_09", "links")
os.makedirs(OUT, exist_ok=True)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row


from opencc import OpenCC
_cc = OpenCC("s2t")


def auth_norm(a):
    if not a:
        return ""
    a = re.sub(r"[\s·・]", "", a)
    return _cc.convert(a)


def norm(s):
    if not s:
        return ""
    s = re.sub(r"[\s\u3000]", "", s)
    s = re.sub(r"[，。、；：？！,.;:?!「」『』（）()《》〈〉—－\-…·]", "", s)
    s = re.sub(r"\d+", "", s)          # OCR 夾入的頁碼殘留
    return s


ex = {r["example_id"]: dict(r) for r in con.execute(
    "select example_id,form_id,cipai_name,author,text,n_chars from cipai_form_examples_r2_08")}
lk = [dict(r) for r in con.execute("select * from example_work_links_r2_08")]
works = {}
for r in con.execute("select work_id,author_name,author_canonical,title_norm,text_norm,"
                     "text_punct,dynasty,collection from works"):
    works[r["work_id"]] = dict(r)

rows = []
for L in lk:
    e = ex.get(L["example_id"])
    if not e:
        continue
    et = norm(e["text"])
    w = works.get(L["work_id"]) if L["work_id"] else None
    wt = norm(w["text_norm"]) if w else ""
    same_author = 0
    if w:
        ea = auth_norm(e["author"])
        wa = auth_norm(w["author_name"])
        wc = auth_norm(w["author_canonical"])
        same_author = 1 if (ea and (ea == wa or ea == wc or ea in wa or wa in ea)) else 0
    if not w:
        kind, score = "NO_MATCH", None
        contain = 0
    else:
        contain = 1 if et and et in wt else 0
        if et == wt:
            kind, score = "VERIFIED_EXACT", 1.0
        elif contain and len(et) < len(wt):
            kind, score = "SUPPORTED_PARTIAL", round(len(et) / max(1, len(wt)), 4)
        elif wt and wt in et:
            kind, score = "EXAMPLE_CONTAINS_WORK", round(len(wt) / max(1, len(et)), 4)
        else:
            sc = difflib.SequenceMatcher(None, et, wt).ratio() if et and wt else 0
            score = round(sc, 4)
            if sc >= 0.95 and abs(len(et) - len(wt)) <= max(4, 0.05 * len(et)):
                kind = "VERIFIED_VARIANT"
            elif sc >= 0.80:
                kind = "POSSIBLE_MATCH"
            else:
                kind = "WEAK_OR_WRONG"
        if not same_author:
            # 作者不同：降級，除非完全相等（可能是作者欄異寫）
            if kind in ("VERIFIED_VARIANT", "POSSIBLE_MATCH"):
                kind = "AUTHOR_CONFLICT"
    # 只靠標題者一律不給高級別
    if L["match_kind"] == "TITLE_ONLY" and kind not in ("VERIFIED_EXACT", "SUPPORTED_PARTIAL"):
        # 標題不符但例詞整段見於該作品：屬「句子被借用」，不是同一首
        wn = re.sub(r"[\s・·]", "", w["title_norm"] or "")
        cn = re.sub(r"[\s・·]", "", e["cipai_name"] or "")
        if contain:
            kind = "TEXT_CONTAINED_TITLE_DIFF"
        elif cn and cn in wn:
            kind = "TITLE_ONLY"
        else:
            kind = "NO_MATCH"
    rows.append({
        "example_id": L["example_id"], "form_id": L["form_id"], "cipai_name": L["cipai_name"],
        "author": e["author"], "work_id": L["work_id"] or "",
        "work_author": w["author_name"] if w else "", "work_title": w["title_norm"] if w else "",
        "collection": w["collection"] if w else "",
        "old_match_kind": L["match_kind"], "new_match_kind": kind,
        "same_author": same_author, "containment": contain,
        "ex_len": len(et), "work_len": len(wt), "score": score,
    })

con.execute("DROP TABLE IF EXISTS example_work_links_r2_09_v1")
con.execute("DROP TABLE IF EXISTS example_work_links_r2_09")
con.execute("""CREATE TABLE example_work_links_r2_09(
 example_id TEXT PRIMARY KEY, form_id TEXT, cipai_name TEXT, author TEXT, work_id TEXT,
 work_author TEXT, work_title TEXT, collection TEXT, old_match_kind TEXT, new_match_kind TEXT,
 same_author INT, containment INT, ex_len INT, work_len INT, score REAL, round TEXT)""")
con.executemany("""INSERT INTO example_work_links_r2_09 VALUES
 (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, '2026-11-14')""",
    [(r["example_id"], r["form_id"], r["cipai_name"], r["author"], r["work_id"],
      r["work_author"], r["work_title"], r["collection"], r["old_match_kind"],
      r["new_match_kind"], r["same_author"], r["containment"], r["ex_len"],
      r["work_len"], r["score"]) for r in rows])
con.commit()

with open(os.path.join(OUT, "EXAMPLE_WORK_LINKS.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

cnt = collections.Counter(r["new_match_kind"] for r in rows)
old = collections.Counter(r["old_match_kind"] for r in rows)
summary = {"n": len(rows), "new": dict(cnt), "old": dict(old),
           "author_conflict": sum(1 for r in rows if r["same_author"] == 0 and r["work_id"]),
           "only_title_survived": cnt.get("TITLE_ONLY", 0)}
json.dump(summary, open(os.path.join(OUT, "link_audit_summary.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))
for r in rows[:5]:
    print(r["cipai_name"], r["author"], "->", r["work_title"], r["old_match_kind"], "=>", r["new_match_kind"], r["score"])
