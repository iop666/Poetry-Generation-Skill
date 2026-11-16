#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-10 工作包 G：为阅读复核准备输入。

产出：
  g1_partial_fail.json   39 条（38 PARTIAL + 1 FAIL）待处理记录，含原页全文与旧审查意见
  g2_new60.json          60 条此前未审记录，13 单元全覆盖
"""
import csv
import glob
import json
import os
import random
import re
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R9 = os.path.join(ROOT, "raw", "r2_09", "reading")
OUT = os.path.join(ROOT, "raw", "r2_10", "reading")
os.makedirs(OUT, exist_ok=True)

recs = [json.loads(l) for l in open(os.path.join(ROOT, "raw", "r2_08", "reading_records_all.jsonl"), encoding="utf-8")]
pages = {}
for l in open(os.path.join(ROOT, "raw", "books_ocr_paddle", "wangli_yinyunxue", "pages.jsonl"), encoding="utf-8"):
    d = json.loads(l)
    pages[d["page"]] = d["text"]


def flat(t):
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\s+", "", t)


# 120 条审计结果
audits = {}
for f in sorted(glob.glob(os.path.join(R9, "audit_batch_*.csv"))):
    for r in csv.DictReader(open(f, encoding="utf-8-sig")):
        audits[r["audit_id"]] = r

sample = json.load(open(os.path.join(R9, "sample_120.json"), encoding="utf-8"))["items"]
by_aid = {}
for i, r in enumerate(recs):
    # audit_id 形如 B001
    pass

# sample_120 里已有 audit_id 与原始字段，需重新映射到 recs 索引
# sample 的构造是 picked 顺序 -> B001..；直接按顺序对应 picked
# 这里用 quote+page 反查唯一记录
key2idx = collections.defaultdict(list)
for i, r in enumerate(recs):
    key2idx[(r["page_pdf"], r["quote"][:30])].append(i)

pending = []
for it in sample:
    a = audits.get(it["audit_id"])
    if not a:
        continue
    if a["verdict"] not in ("PARTIAL", "FAIL"):
        continue
    cand = key2idx.get((it["page_pdf_labeled"], it["quote"][:30]), [])
    idx = cand[0] if cand else None
    pending.append({
        "audit_id": it["audit_id"],
        "rec_index": idx,
        "unit_id": recs[idx]["unit_id"] if idx is not None else it.get("unit"),
        "section": it["section"],
        "page_pdf_labeled": it["page_pdf_labeled"],
        "true_pdf_page": it["true_pdf_page"],
        "page_printed": it["page_printed"],
        "quote": it["quote"],
        "claim": it["claim"],
        "data_points": recs[idx].get("data_points", []) if idx is not None else it.get("data_points"),
        "note": recs[idx].get("note", "") if idx is not None else "",
        "old_verdict": a["verdict"],
        "old_severity": a["severity"],
        "old_issue_type": a["issue_type"],
        "old_evidence_snippet": a["evidence_snippet"],
        "old_revised_claim": a.get("revised_claim", ""),
        "old_review_note": a.get("note", ""),
        "page_text": flat(pages.get(it["page_pdf_labeled"], "")),
    })

json.dump({"n": len(pending), "items": pending},
          open(os.path.join(OUT, "g1_partial_fail.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# 60 条新样本：排除已审 120
audited_idx = {p["rec_index"] for p in pending}
audited_all = set()
for it in sample:
    cand = key2idx.get((it["page_pdf_labeled"], it["quote"][:30]), [])
    if cand:
        audited_all.add(cand[0])

MAIN = [f"U{i:02d}" for i in range(1, 14)]
random.seed(20261115)
pool = [i for i in range(len(recs)) if i not in audited_all]
by_unit = collections.defaultdict(list)
for i in pool:
    by_unit[recs[i]["unit_id"]].append(i)

picked = []


def score(i):
    r = recs[i]
    s = 0
    if r["quote_kind"] in ("ARGUMENT", "DEFINITION"):
        s -= 3
    if r["quote_kind"] == "HISTORY":
        s -= 2
    if re.search(r"演變|演变|條例|条例|規律|规律|分化|合流|變為|变为|來源|来源", r["claim"]):
        s -= 2
    if re.search(r"反切|韻部|韵部|聲母|声母|韻母|韵母|聲調|声调", r["claim"]):
        s -= 1
    if len(r["quote"]) < 40 and len(r["claim"]) > 60:
        s -= 3
    return s


for u in MAIN:
    cand = sorted(by_unit.get(u, []), key=score)
    for i in cand[:5]:
        if i not in picked:
            picked.append(i)
# 补足到 60，按全局优先级
rest = sorted([i for i in pool if i not in picked], key=score)
for i in rest:
    if len(picked) >= 60:
        break
    picked.append(i)

items = []
for k, i in enumerate(picked, 1):
    r = recs[i]
    items.append({
        "audit_id": "N%03d" % k,
        "rec_index": i,
        "unit_id": r["unit_id"],
        "section": r["section"],
        "page_pdf_labeled": r["page_pdf"],
        "true_pdf_page": r["page_pdf"] + 1,
        "page_printed": r["page_pdf"] - 9,
        "quote": r["quote"],
        "claim": r["claim"],
        "data_points": r.get("data_points", []),
        "note": r.get("note", ""),
        "quote_kind": r["quote_kind"],
        "confidence": r["confidence"],
        "page_text": flat(pages.get(r["page_pdf"], "")),
    })

json.dump({"n": len(items), "sampling_rules": [
    "排除 R2-09 已审 120 条",
    "13 个正文章节单元各至少 5 条",
    "优先 ARGUMENT/DEFINITION/HISTORY",
    "优先含演变/条例/规律/分化等理论判断词者",
    "优先 quote 短而 claim 长者",
], "items": items},
    open(os.path.join(OUT, "g2_new60.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("g1", len(pending), collections.Counter(p["old_verdict"] for p in pending))
print("g2", len(items), collections.Counter(i["unit_id"] for i in items))
