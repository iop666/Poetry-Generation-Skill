#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 B3：476 頁全頁賬本（每頁必有分類）。

修正 R2-08 的一個口徑錯誤：OCR pages.jsonl 的 page 是 0-based 索引，
真實 PDF 頁 = 索引 + 1；印刷頁 = 索引 − 9（已用六個目錄錨點驗證）。
R2-08 把索引直接叫作 page_pdf，故其「PDF 頁」比真實 PDF 頁小 1。
"""
import os
import re
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "raw", "r2_09", "reading")
os.makedirs(OUT, exist_ok=True)

pages = {json.loads(l)["page"]: json.loads(l)["text"]
         for l in open(os.path.join(ROOT, "raw", "books_ocr_paddle", "wangli_yinyunxue", "pages.jsonl"))}
led = {x["page_pdf"]: x for x in json.load(
    open(os.path.join(ROOT, "raw", "r2_08", "page_ledger.json")))["ledger"]}
recs = [json.loads(l) for l in open(os.path.join(ROOT, "raw", "r2_08", "reading_records_all.jsonl"))]
cnt = {}
for r in recs:
    cnt[r["page_pdf"]] = cnt.get(r["page_pdf"], 0) + 1


def cls(i, text):
    t = re.sub(r"<[^>]+>", "", text)
    n = len(re.sub(r"\s", "", t))
    if n == 0:
        return "BLANK"
    if i == 0:
        return "COVER_TITLE"
    if i in (1, 2, 3):
        return "COPYRIGHT_CIP"
    if i == 4:
        return "PUBLISHER_NOTE_COLLECTED"
    if i == 5:
        return "PUBLISHER_NOTE_VOLUME"
    if i == 6:
        return "FRONT_TABLE_OR_CHART"
    if i in (7, 8, 9):
        return "TOC"
    if i >= 454:
        return "INDEX"
    return None


rows = []
for i in range(476):
    txt = pages.get(i, "")
    k = cls(i, txt)
    note = ""
    if k is None:
        L = led.get(i)
        if L:
            k = {"CLAIM_RECORDED": "BODY_WITH_RECORD", "TABLE_ONLY": "BODY_TABLE_ONLY",
                 "QUOTATION": "BODY_QUOTATION", "EMPTY": "BODY_BLANK"}.get(L["kind"], "BODY_OTHER")
            note = "R2-08 記 %d 條" % L.get("n_records", 0)
        else:
            k = "BODY_NO_LEDGER"
    rows.append({
        "ocr_index": i, "true_pdf_page": i + 1,
        "printed_page": (i - 9) if 10 <= i <= 453 else None,
        "section": k, "chars": len(re.sub(r"\s", "", re.sub(r"<[^>]+>", "", txt))),
        "n_records_r2_08": cnt.get(i, 0), "note": note,
    })

kinds = {}
for r in rows:
    kinds[r["section"]] = kinds.get(r["section"], 0) + 1
unexplained = [r for r in rows if r["section"] == "BODY_NO_LEDGER"]

json.dump({"n_pages": len(rows), "kinds": kinds, "pages": rows,
           "n_unexplained": len(unexplained)},
          open(os.path.join(OUT, "page_coverage_r2_09.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

with open(os.path.join(OUT, "READING_PAGE_COVERAGE.csv"), "w", encoding="utf-8-sig") as f:
    f.write("ocr_index,true_pdf_page,printed_page,section,chars,n_records_r2_08,note\n")
    for r in rows:
        f.write("%d,%d,%s,%s,%d,%d,%s\n" % (
            r["ocr_index"], r["true_pdf_page"], r["printed_page"] or "", r["section"],
            r["chars"], r["n_records_r2_08"], r["note"]))

print("pages", len(rows), "kinds", kinds, "unexplained", len(unexplained))
