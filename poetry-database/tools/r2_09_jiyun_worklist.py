#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 C2/C3：生成《集韻》人工複核工作清單。

- 30 個韻頁（按頁長分層）的完整性記錄
- 120 條小韻（跨 30 頁）的逐條複核材料：原文切片 + 程序解析值
供子 Agent 對照原文逐條判定，不預設答案。
"""
import os
import json
import re
import glob
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "raw", "r2_08", "jiyun_pages")
OUT = os.path.join(ROOT, "raw", "r2_09", "c_pages")

rec = json.load(open(os.path.join(OUT, "jiyun_reconcile_v3.json"), encoding="utf-8"))
pages = rec["pages"]
sample30 = [p for p in pages if p["yun"] in set(rec["summary"]["sample_30"])][:30]
if len(sample30) < 30:
    for p in pages:
        if p not in sample30:
            sample30.append(p)
        if len(sample30) == 30:
            break

texts = {}
for p in sample30:
    d = json.load(open(os.path.join(SRC, p["title"].replace("/", "_") + ".json")
                       if os.path.exists(os.path.join(SRC, p["title"].replace("/", "_") + ".json"))
                       else os.path.join(SRC, "*"), encoding="utf-8")) if False else None

# 直接按 title 查檔
by_title = {}
for f in glob.glob(os.path.join(SRC, "*.json")):
    d = json.load(open(f, encoding="utf-8"))
    by_title[d["title"]] = d["text"]


def clean(t):
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\[\[[^\]]*\]\]", "", t)
    return re.sub(r"\s+", "", t)


CJK = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
blocks_all = [json.loads(l) for l in open(os.path.join(OUT, "jiyun_blocks_v3.jsonl"), encoding="utf-8")]

random.seed(20261114)
items = []
for p in sample30:
    t = clean(by_title.get(p["title"], ""))
    # 切成 ○ 段，保留原文
    t2 = re.sub(r"^.*?(?=[○〇])", "", t)  # 去掉頁首導航
    segs = re.split(r"(?=[○〇])", t2)
    segs = [s for s in segs if s.strip() and "切" in s and len(s) > 12]
    # 每頁抽 4 條（頭、中、尾）
    n = len(segs)
    picks = sorted(set([0, n // 3, 2 * n // 3, n - 1])) if n >= 4 else list(range(n))
    for k in picks[:4]:
        seg = segs[k]
        body = seg[1:]
        m = re.match(r"([%s]{1,3})" % CJK, body)
        head = m.group(1) if m else ""
        gm = re.search(r"[〈<]([^〉>]{0,60})[〉>]", body)
        gloss = gm.group(1) if gm else ""
        fq = re.search(r"([%s]{1,3})切" % CJK, body)
        wm = re.search(r"文([一二三四五六七八九十百零〇]{1,4})(?![一二三四五六七八九十百零〇])", body)
        items.append({
            "item_id": "JY-%03d" % (len(items) + 1),
            "yun": p["yun"], "volume": p["volume"],
            "title": p["title"], "seg_index": k + 1, "n_seg": n,
            "head_first3": head,
            "gloss_head40": gloss,
            "program_fanqie": fq.group(0) if fq else None,
            "program_declared": wm.group(1) if wm else None,
            "raw_seg": seg[:90],
        })

json.dump({"n_item": len(items), "n_pages": 30,
           "pages": [p["yun"] for p in sample30], "items": items},
          open(os.path.join(OUT, "jiyun_manual_120.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("items:", len(items), "pages:", len(sample30))
print("first:", json.dumps(items[0], ensure_ascii=False)[:300])
