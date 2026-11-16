#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 WP-A：《汉语音韵学》逐页阅读台账 + 引文索引。

目的：把 PDF 10–453（印刷 1–444）每一页归类，避免用「有记录的页」冒充「读过的页」。
- 有 claim 级阅读记录的页 → CLAIM_RECORDED
- 「参考资料」引文页（OCR 中带【…】专题小标题）→ QUOTATION（并抽出标题与署名）
- 整页表格 → TABLE_ONLY；整页图像占位 → IMAGE_ONLY；近空白 → EMPTY
- 其余仍有成段正文 → TEXT_NO_RECORD（须复核，不得静默）
"""
import json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "raw", "books_ocr_paddle", "wangli_yinyunxue", "pages.jsonl")
REC = os.path.join(ROOT, "raw", "r2_08", "reading_records_all.jsonl")
OUT = os.path.join(ROOT, "raw", "r2_08", "page_ledger.json")

rows = {json.loads(l)["page"]: json.loads(l) for l in open(SRC, encoding="utf-8")}
recs = [json.loads(l) for l in open(REC, encoding="utf-8")]
has_rec = collections.Counter(r["page_pdf"] for r in recs)
nrec_by_page = dict(has_rec)

TAG = re.compile(r"【([^】]{3,40})】")
AUTHOR_HINT = re.compile(r"——\s*([\u4e00-\u9fa5]{2,4})")


def plain(t):
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\s", "", t)


ledger = []
for p in range(10, 454):
    t = rows[p]["text"]
    pt = plain(t)
    n = len(pt)
    nimg = len(re.findall(r"<img", t))
    ntab = len(re.findall(r"<table", t))
    tags = TAG.findall(t)
    has_ref = "参考资料" in t or "參考資料" in t
    kind = None
    if has_rec.get(p):
        kind = "CLAIM_RECORDED"
    elif n < 60:
        kind = "EMPTY"
    elif nimg >= 4 and n < 300:
        kind = "IMAGE_ONLY"
    elif ntab >= 1 and n < 400:
        kind = "TABLE_ONLY"
    elif tags and (has_ref or len(tags) >= 2):
        kind = "QUOTATION"
    elif n < 400:
        kind = "SHORT_TEXT"
    else:
        kind = "TEXT_NO_RECORD"
    ledger.append({
        "page_pdf": p, "page_printed": p - 9, "chars": n,
        "n_img": nimg, "n_table": ntab, "kind": kind,
        "n_records": nrec_by_page.get(p, 0),
        "ref_section": has_ref,
        "quotations": tags,
        "quotation_authors": AUTHOR_HINT.findall(t),
        "head": pt[:24],
    })

cnt = collections.Counter(x["kind"] for x in ledger)
# 引文索引
qidx = []
for x in ledger:
    for t in x["quotations"]:
        qidx.append({"page_pdf": x["page_pdf"], "page_printed": x["page_printed"],
                     "heading": t, "authors": x["quotation_authors"]})

json.dump({"generated_pages": len(ledger), "kinds": dict(cnt),
           "ledger": ledger, "quotation_index": qidx},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(dict(cnt), ensure_ascii=False, indent=1))
print("quotation headings:", len(qidx))
print("TEXT_NO_RECORD pages:", [x["page_pdf"] for x in ledger if x["kind"] == "TEXT_NO_RECORD"][:50])
