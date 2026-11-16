#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 B：分層抽取 120 條閱讀記錄，並輸出可核驗工作清單。

抽樣規則（非簡單隨機）：
  1. U01–U13 每個正文章節單元至少 5 條；
  2. 優先 ARGUMENT / DEFINITION（理論判斷與定義）與 HISTORY（歷史演變）；
  3. 短引文 + 長概括者提高權重（quote<40 字而 claim>60 字）；
  4. 8 條 UNKNOWN 音標上下文全部納入；
  5. 低信度（LOW）全數納入。
"""
import os
import json
import re
import collections
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "raw", "r2_09", "reading")
os.makedirs(OUT, exist_ok=True)

recs = [json.loads(l) for l in open(os.path.join(ROOT, "raw", "r2_08", "reading_records_all.jsonl"))]
pages = {json.loads(l)["page"]: json.loads(l)["text"]
         for l in open(os.path.join(ROOT, "raw", "books_ocr_paddle", "wangli_yinyunxue", "pages.jsonl"))}


def flat(t):
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\s+", "", t)


MAIN = [u for u in [f"U{i:02d}" for i in range(1, 14)]]
random.seed(20261114)

picked = []
seen = set()

def add(i, why):
    if i in seen:
        return
    seen.add(i)
    picked.append((i, why))

# 1) 每單元先取 LOW
for u in MAIN:
    for i, r in enumerate(recs):
        if r["unit_id"] == u and r["confidence"] == "LOW":
            add(i, "LOW_CONFIDENCE_ALL")

# 2) 每單元按優先級取 5 條
for u in MAIN:
    cand = [(i, r) for i, r in enumerate(recs) if r["unit_id"] == u]
    def score(item):
        i, r = item
        s = 0
        if r["quote_kind"] in ("ARGUMENT", "DEFINITION"):
            s -= 3
        if r["quote_kind"] == "HISTORY":
            s -= 2
        if len(r["quote"]) < 40 and len(r["claim"]) > 60:
            s -= 4
        if r["confidence"] == "MEDIUM":
            s -= 1
        return s
    cand.sort(key=score)
    n = sum(1 for i, _ in picked if recs[i]["unit_id"] == u)
    for i, r in cand:
        if n >= 5:
            break
        if i not in seen:
            add(i, "CHAPTER_MIN5")
            n += 1

# 3) 補到 120：按「短引長論」優先
rest = sorted([(i, r) for i, r in enumerate(recs) if i not in seen],
              key=lambda x: (len(x[1]["quote"]) - len(x[1]["claim"]), x[0]))
for i, r in rest:
    if len(picked) >= 120:
        break
    add(i, "SHORT_QUOTE_LONG_CLAIM")

# 4) 音標 UNKNOWN 上下文（若未入選則替換最後幾條）
schwa = json.load(open(os.path.join(ROOT, "raw", "r2_08", "schwa_index.json")))
unk = [x for x in schwa["items"] if x["status"] == "UNKNOWN" and x["book"] == "wangli_yinyunxue"]
unk_pages = sorted({x["page_pdf"] for x in unk})

items = []
for k, (i, why) in enumerate(picked[:120], 1):
    r = dict(recs[i])
    p = r["page_pdf"]
    txt = flat(pages.get(p, ""))
    items.append({
        "audit_id": "RA-%03d" % k,
        "rec_index": i,
        "unit_id": r["unit_id"],
        "section": r["section"],
        "page_pdf_labeled": p,
        "true_pdf_page": p + 1,
        "page_printed": r["page_printed"],
        "topic": r["topic"],
        "claim": r["claim"],
        "quote": r["quote"],
        "quote_kind": r["quote_kind"],
        "terms": r["terms"],
        "data_points": r["data_points"],
        "poetry_relevance": r["poetry_relevance"],
        "prior_confidence": r["confidence"],
        "note": r["note"],
        "why_sampled": why,
        "page_text": txt,
        "quote_in_page": 1 if flat(r["quote"]) in txt else 0,
        "schwa_contexts": [x for x in unk if x["page_pdf"] == p],
    })

json.dump({"n": len(items), "sampling_rules": [
    "U01-U13 每單元 >=5", "LOW 全取", "優先 ARGUMENT/DEFINITION/HISTORY",
    "短引文長概括加權", "含音標 UNKNOWN 上下文"],
    "unknown_schwa_pages": unk_pages,
    "items": items},
    open(os.path.join(OUT, "sample_120.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 分四包，便於並行
for b in range(4):
    part = items[b * 30:(b + 1) * 30]
    json.dump({"batch": b + 1, "n": len(part), "items": part},
              open(os.path.join(OUT, "batch_%d.json" % (b + 1)), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

print("sampled", len(items))
print("by unit:", collections.Counter(x["unit_id"] for x in items))
print("by kind:", collections.Counter(x["quote_kind"] for x in items))
print("quote_in_page=0:", sum(1 for x in items if not x["quote_in_page"]))
print("unknown schwa pages:", unk_pages)
