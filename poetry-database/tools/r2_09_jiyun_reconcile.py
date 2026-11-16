#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 C2：《集韻》字數差額逐韻對帳（v3，可審計口徑）。

口徑說明
--------
集韻轉錄體例：`○首字〈反切＋釋義＋文N〉字〈注〉字字〈注〉…`
- 「○」= 小韻界
- 「〈…〉」= 一條注；緊接在注前的 1–4 個漢字共用此注
- 「文N」= 該小韻自述字數

三個可獨立復算的量：
  n_xiaoyun  = ○ 的個數
  n_blocks   = 〈 的個數（注塊數，略小於字頭數，因數字共注）
  declared   = Σ 文N（原書自述字數）

本輪結論建立在「n_blocks 與 declared 的差」上，而不是在
易受正則影響的「抽字數」上——因為抽字數會隨解析規則浮動，
而注塊數與自述數都是原文可直接數出來的。
"""
import os
import json
import re
import glob
import csv
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "raw", "r2_08", "jiyun_pages")
OUT = os.path.join(ROOT, "raw", "r2_09", "c_pages")
os.makedirs(OUT, exist_ok=True)

CJK = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
      "八": 8, "九": 9, "十": 10, "百": 100, "零": 0, "〇": 0}


def cn2int(s):
    if not s:
        return None
    tot = cur = 0
    for ch in s:
        v = CN.get(ch)
        if v is None:
            return None
        if v == 10:
            cur = (cur or 1) * 10
        elif v == 100:
            tot += (cur or 1) * 100
            cur = 0
        else:
            cur += v
    return tot + cur


BLOCK = re.compile(r"([%s]{0,5})[〈<]([^〉>]{0,400})[〉>]" % CJK)
TAIL = re.compile(r"([%s]{1,4})$" % CJK)
FQ = re.compile(r"([%s]{1,3})切" % CJK)
WEN = re.compile(r"文([一二三四五六七八九十百零〇]{1,4})(?![一二三四五六七八九十百零〇])")


def clean(t):
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\[\[[^\]]*\]\]", "", t)
    return re.sub(r"\s+", "", t)


rows = []
pages = []
for f in sorted(glob.glob(os.path.join(SRC, "*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    title = d["title"]
    m = re.search(r"卷(\d+)/(.+)", title)
    vol = int(m.group(1)) if m else None
    yun = m.group(2) if m else title
    t = clean(d.get("text", ""))

    n_circ = t.count("○") + t.count("〇")
    blocks = list(BLOCK.finditer(t))
    n_blocks = len(blocks)

    # 逐注塊取字頭
    heads = []
    declared_per_xy = []
    cur_declared = None
    for b in blocks:
        tail = b.group(1)
        tm = TAIL.search(tail)
        hs = tm.group(1) if tm else ""
        body = b.group(2)
        fq = FQ.search(body)
        wm = WEN.search(body)
        if fq and wm:
            declared_per_xy.append(cn2int(wm.group(1)))
        heads.append({"chars": hs, "fanqie": fq.group(1) if fq else None,
                      "declared": cn2int(wm.group(1)) if wm else None})
    declared = sum(x for x in declared_per_xy if x)
    # 每個注塊的字頭數（0 表示 OCR 把字頭吞進注裡）
    n_head_chars = sum(len(h["chars"]) for h in heads)
    n_zero_head = sum(1 for h in heads if not h["chars"])
    n_multi_head = sum(1 for h in heads if len(h["chars"]) > 1)

    pages.append({
        "title": title, "volume": vol, "yun": yun,
        "status": d.get("status"), "revid": d.get("revid"),
        "html_sha256": d.get("html_sha256"),
        "text_len": len(t),
        "n_xiaoyun": n_circ, "n_blocks": n_blocks,
        "n_head_chars": n_head_chars,
        "n_block_zero_head": n_zero_head,
        "n_block_multi_head": n_multi_head,
        "declared": declared,
        "delta_block_vs_declared": n_blocks - declared if declared else None,
        "ratio_blocks_declared": round(n_blocks / declared, 3) if declared else None,
    })
    for i, h in enumerate(heads):
        rows.append({"page_title": title, "volume": vol, "yun": yun,
                     "seq": i + 1, **h})

with open(os.path.join(OUT, "jiyun_blocks_v3.jsonl"), "w", encoding="utf-8") as fh:
    for r in rows:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")

S = {
    "n_pages": len(pages),
    "n_xiaoyun": sum(p["n_xiaoyun"] for p in pages),
    "n_blocks": sum(p["n_blocks"] for p in pages),
    "n_head_chars": sum(p["n_head_chars"] for p in pages),
    "n_block_zero_head": sum(p["n_block_zero_head"] for p in pages),
    "n_block_multi_head": sum(p["n_block_multi_head"] for p in pages),
    "declared": sum(p["declared"] for p in pages),
    "gap_blocks": sum(p["n_blocks"] for p in pages) - sum(p["declared"] for p in pages),
    "n_pages_declared": sum(1 for p in pages if p["declared"]),
}
S["ratio"] = round(S["n_blocks"] / S["declared"], 4)
S["gap_pct"] = round(100.0 * S["gap_blocks"] / S["declared"], 2)

# 分頁差額分類
cls = collections.Counter()
for p in pages:
    if not p["declared"]:
        cls["NO_DECLARED"] += 1
        continue
    r = p["ratio_blocks_declared"]
    if 0.97 <= r <= 1.03:
        cls["BALANCED"] += 1
    elif r < 0.97:
        cls["BLOCKS_FEWER"] += 1
    else:
        cls["BLOCKS_MORE"] += 1
S["page_classes"] = dict(cls)

# 30 頁對照樣本：按聲調分層 + 頁長分層
def tone_of(yun):
    return "UNKNOWN"

sample = []
by_len = sorted(pages, key=lambda p: p["text_len"])
n = len(by_len)
idx = [int(n * k / 30) for k in range(30)]
for i in idx:
    p = by_len[min(i, n - 1)]
    if p not in sample:
        sample.append(p)
while len(sample) < 30:
    for p in pages:
        if p not in sample:
            sample.append(p)
            break
S["sample_30"] = [p["yun"] for p in sample]

json.dump({"summary": S, "pages": pages},
          open(os.path.join(OUT, "jiyun_reconcile_v3.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

with open(os.path.join(OUT, "jiyun_sample30.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["韻目", "卷", "頁長", "小韻數(○)", "注塊數(〈)", "字頭實取", "零字頭塊",
                "多字頭塊", "原書自述(Σ文N)", "注塊-自述", "比值", "判定"])
    for p in sample:
        w.writerow([p["yun"], p["volume"], p["text_len"], p["n_xiaoyun"], p["n_blocks"],
                    p["n_head_chars"], p["n_block_zero_head"], p["n_block_multi_head"],
                    p["declared"], p["delta_block_vs_declared"],
                    p["ratio_blocks_declared"],
                    "BALANCED" if p["ratio_blocks_declared"] and 0.97 <= p["ratio_blocks_declared"] <= 1.03
                    else ("BLOCKS_FEWER" if p["ratio_blocks_declared"] and p["ratio_blocks_declared"] < 0.97 else "BLOCKS_MORE")])

print(json.dumps({k: v for k, v in S.items() if k != "sample_30"}, ensure_ascii=False, indent=1))
print("sample30:", S["sample_30"][:10], "...")
