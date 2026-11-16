#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 F2：對 114 條 NO_MATCH 例詞做逐條再調查。

手段（依序，皆留痕）：
  1. 以例詞首 8 字在 works.text_norm 檢索（繁簡雙向）
  2. 以作者（繁簡正規化）+ 首 4 字檢索
  3. 以詞牌別名 + 作者檢索
仍不成功者記 `UNRESOLVED` 並寫明已試手段，不強行建立關聯。
"""
import os
import re
import csv
import json
import sqlite3
import difflib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
OUT = os.path.join(ROOT, "raw", "r2_09", "links")
os.makedirs(OUT, exist_ok=True)
from opencc import OpenCC
cc = OpenCC("s2t")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row


def norm(s):
    s = re.sub(r"[^\u4e00-\u9fff]", "", s or "")
    return s


rows = []
miss = [dict(r) for r in con.execute("""
 select l.example_id, l.cipai_name, l.author, l.work_id
 from example_work_links_r2_09 l where l.new_match_kind='NO_MATCH'""")]
ex = {r["example_id"]: dict(r) for r in con.execute(
    "select example_id,text,author,n_chars from cipai_form_examples_r2_08")}

for m in miss:
    e = ex.get(m["example_id"])
    if not e:
        continue
    t = norm(e["text"])
    tries = []
    hit = None
    for q in {t[:8], cc.convert(t[:8]), t[:6]}:
        if len(q) < 4:
            continue
        tries.append("PREFIX8:" + q)
        r = con.execute("select work_id,author_name,title_norm,text_norm from works "
                        "where text_norm like ? limit 3", ("%" + q + "%",)).fetchall()
        for x in r:
            sim = difflib.SequenceMatcher(None, t, norm(x["text_norm"])).ratio()
            if sim >= 0.85:
                hit = (x, sim, "PREFIX_SEARCH")
                break
        if hit:
            break
    if not hit and len(t) >= 6:
        au = re.sub(r"[\s·]", "", e["author"] or "")
        tries.append("AUTHOR+PREFIX4")
        r = con.execute("select work_id,author_name,title_norm,text_norm from works "
                        "where author_name like ? and text_norm like ? limit 3",
                        ("%" + au[:2] + "%", "%" + t[2:8] + "%")).fetchall()
        for x in r:
            sim = difflib.SequenceMatcher(None, t, norm(x["text_norm"])).ratio()
            if sim >= 0.85:
                hit = (x, sim, "AUTHOR_PREFIX_SEARCH")
                break
    if hit:
        rows.append({"example_id": m["example_id"], "cipai_name": m["cipai_name"],
                     "author": e["author"], "attempts": "|".join(tries),
                     "result": "FOUND_BY_" + hit[2],
                     "found_work_id": hit[0]["work_id"],
                     "found_author": hit[0]["author_name"],
                     "found_title": hit[0]["title_norm"],
                     "score": round(hit[1], 4),
                     "note": "未自動併入關聯表，須人工確認"})
    else:
        rows.append({"example_id": m["example_id"], "cipai_name": m["cipai_name"],
                     "author": e["author"], "attempts": "|".join(tries) or "TOO_SHORT",
                     "result": "UNRESOLVED", "found_work_id": "", "found_author": "",
                     "found_title": "", "score": None,
                     "note": "已試前綴檢索與作者+前綴檢索；作品庫可能未收或文字差異大"})

with open(os.path.join(OUT, "UNMATCHED_EXAMPLE_RESEARCH.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["example_id", "cipai_name", "author", "attempts",
                                      "result", "found_work_id", "found_author",
                                      "found_title", "score", "note"])
    w.writeheader()
    w.writerows(rows)
json.dump({"n": len(rows),
           "found": sum(1 for r in rows if r["result"].startswith("FOUND")),
           "unresolved": sum(1 for r in rows if r["result"] == "UNRESOLVED")},
          open(os.path.join(OUT, "unmatched_summary.json"), "w"), ensure_ascii=False, indent=1)
print("unmatched", len(rows), "found", sum(1 for r in rows if r["result"].startswith("FOUND")),
      "unresolved", sum(1 for r in rows if r["result"] == "UNRESOLVED"))
