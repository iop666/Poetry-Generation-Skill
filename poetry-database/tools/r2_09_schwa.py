#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 B4：ə/e 音標索引複核（50 組抽樣 + 全量重分類）。

R2-08 只把 589 個 ə 分為 CONFIRMED_SCHWA / UNKNOWN，沒有處理
「OCR 把 [ 誤識成 ə」這一類。本輪新增判定：
  LIKELY_BRACKET_ARTIFACT  上下文顯示該 ə 原是左方括號（表格行首、緊接元音）
  CONFIRMED_SCHWA          [] 內或音標串中的 ə，前後為音標符號
  CONFIRMED_E              [] 內的 e
  UNKNOWN                  其餘
"""
import os
import re
import json
import csv
import random
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "raw", "r2_08", "schwa_index.json")
OUT = os.path.join(ROOT, "raw", "r2_09", "reading")

IPA = set("aeiouyæɑɒɔəɛɜɪʊʌɤøœɐɘɵɨʉɯɰŋɲʃʒθðβɣχʁʔpbtdkgmnlrfvsxhzwj")

d = json.load(open(SRC, encoding="utf-8"))
items = d["items"]
for it in items:
    L, R = it.get("left", ""), it.get("right", "")
    ch = it["char"]
    ctx = (L[-12:] + ch + R[:12])
    if "[" in L[-3:] or "]" in R[:3] or "［" in L[-3:]:
        it["new_status"] = "CONFIRMED_" + ("SCHWA" if ch == "ə" else "E")
        it["new_rule"] = "IN_PHONETIC_BRACKET"
    elif re.match(r"^\s*[%s]" % "".join(IPA), R[:2]) and (ch == "ə") and re.search(r"[\s>'；。]$", L[-1:] or " "):
        it["new_status"] = "LIKELY_BRACKET_ARTIFACT"
        it["new_rule"] = "STANDALONE_BEFORE_VOWEL_TABLE"
    elif re.search(r"[%s][%s]" % ("".join(IPA), "".join(IPA)), L[-1:] + R[:1].replace(ch, "")):
        it["new_status"] = "CONFIRMED_" + ("SCHWA" if ch == "ə" else "E")
        it["new_rule"] = "IN_IPA_STRING"
    else:
        it["new_status"] = "UNKNOWN"
        it["new_rule"] = "NO_PHONETIC_CONTEXT"

cnt = collections.Counter((it["book"], it["new_status"]) for it in items)

# 50 組分層抽樣：兩書 × 三類，按比例
random.seed(20261114)
strata = collections.defaultdict(list)
for it in items:
    strata[(it["book"], it["new_status"])].append(it)
sample = []
for k, v in sorted(strata.items()):
    take = max(2, round(50 * len(v) / len(items)))
    sample.extend(random.sample(v, min(take, len(v))))
sample = sample[:50]

out = []
for i, it in enumerate(sample, 1):
    out.append({
        "no": i,
        "book": it["book_cn"],
        "page_pdf": it["page_pdf"],
        "true_pdf_page": it["page_pdf"] + 1,
        "char": it["char"],
        "old_status": it["status"],
        "new_status": it["new_status"],
        "rule": it["new_rule"],
        "context_before": it.get("left", "")[-30:],
        "context_after": it.get("right", "")[:30],
        "image_check": "NOT_DONE",
        "verdict": it["new_status"],
        "note": "",
    })

with open(os.path.join(OUT, "SCHWA_E_REVIEW.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)

stats = {
    "n_total": len(items),
    "old": d["summary"]["by_status"],
    "new": {"%s|%s" % k: v for k, v in cnt.items()},
    "n_sample": len(out),
}
json.dump(stats, open(os.path.join(OUT, "schwa_review_stats.json"), "w"),
          ensure_ascii=False, indent=1)
print(json.dumps(stats, ensure_ascii=False, indent=1))
