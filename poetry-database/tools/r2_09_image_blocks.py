#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 E2：以文字層「譜行線」定位整塊裁切。

原理：譜行行的組成幾乎全是 － ｜ ＋ （ ） 與少量「韵/句/豆/叶/换」字。
逐行取 bbox，把連續的譜行行合併成塊；塊前一行若是格標題（定格/变格/格一…）
則該塊歸此格。一頁只有一塊時直接採用。
"""
import json
import os
import re
import hashlib
import sqlite3
import pymupdf as fitz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(os.path.dirname(ROOT), "books",
                   "唐宋词格律 (龙榆生) (z-library.sk, 1lib.sk, z-lib.sk).pdf")
OUT = os.path.join(ROOT, "raw", "r2_09", "images")
man = json.load(open(os.path.join(OUT, "single_manifest.json"), encoding="utf-8"))

con = sqlite3.connect(os.path.join(ROOT, "database", "poetry.db"))
con.row_factory = sqlite3.Row
info = {r["form_id"]: dict(r) for r in con.execute(
    "select form_id,cipai_name,form_seq,pattern_label,sentence_count,ann_sequence,"
    "total_characters,rhyme_count,source_text from cipai_forms_r2_07")}

SYM = re.compile(r"^[\s－—–\-｜|│＋+○●△（）()韵韻句豆叶葉換换平仄叠疊再〇]*$")
GE = re.compile(r"^(定格|变格|變格|格[一二三四五六七八九]|又一體|又一体)")


def is_pattern_line(t):
    s = t.strip()
    if len(s) < 4:
        return False
    if not SYM.match(s):
        return False
    return (s.count("－") + s.count("-") + s.count("｜") + s.count("+")
            + s.count("＋") + s.count("|")) >= 3


doc = fitz.open(PDF)
recs = []
for k, it in enumerate(man, 1):
    pg = doc[it["pdf_page"] - 1]
    d = info[it["form_id"]]
    lines = []
    for b in pg.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            txt = "".join(s["text"] for s in l["spans"])
            lines.append((l["bbox"][1], l["bbox"][3], txt))
    lines.sort()
    blocks, cur = [], []
    for y0, y1, txt in lines:
        if is_pattern_line(txt):
            cur.append((y0, y1))
        else:
            if cur:
                blocks.append(cur)
                cur = []
    if cur:
        blocks.append(cur)

    # 選塊：前一行是格標題者為起點，取該標題以下所有譜行塊的聯集（可跨附註）
    start = None
    for b in blocks:
        top = b[0][0]
        prev = [l for l in lines if l[1] <= top + 2][-1:] or []
        if prev and GE.match(prev[0][2].replace(" ", "").replace("\u3000", "")):
            start = top
            break
    if start is not None:
        below = [b for b in blocks if b[-1][1] >= start]
        chosen = [(min(b[0][0] for b in below), max(b[-1][1] for b in below))]
    elif blocks:
        bb = max(blocks, key=lambda b: b[-1][1] - b[0][0])
        chosen = [(bb[0][0], bb[-1][1])]
    else:
        chosen = [(60, 240)]
    r = fitz.Rect(0, max(0, chosen[0][0] - 34), pg.rect.width,
                  min(pg.rect.height, chosen[-1][1] + 8))
    path = os.path.join(OUT, "b%02d_%s.png" % (k, it["form_id"].replace("-", "_")))
    pg.get_pixmap(dpi=300, clip=r).save(path)
    anns = re.findall(r"[（(]([^）)]*)[）)]", d["source_text"] or "")
    recs.append({
        "seq": k, "form_id": it["form_id"], "cipai_name": d["cipai_name"],
        "form_seq": d["form_seq"], "pattern_label": d["pattern_label"],
        "pdf_page": it["pdf_page"], "printed_page": it["printed_page"],
        "png": path, "png_bytes": os.path.getsize(path),
        "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest(),
        "crop": [round(x, 1) for x in r],
        "n_pattern_lines": len(chosen),
        "stored_sentence_count": d["sentence_count"],
        "stored_total_characters": d["total_characters"],
        "stored_rhyme_count": d["rhyme_count"],
        "stored_ann_seq": anns, "stored_n_ann": len(anns),
        "stored_pattern": d["source_text"],
    })
doc.close()
json.dump(recs, open(os.path.join(OUT, "block_manifest.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
bad = [r["form_id"] for r in recs if r["png_bytes"] < 8000]
print("items", len(recs), "suspect_small", bad)
for r in recs[:6]:
    print(r["form_id"], r["cipai_name"], "lines", r["n_pattern_lines"],
          "sent", r["stored_sentence_count"], "ann", r["stored_n_ann"], r["png_bytes"])
