#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 E2：為「尚未核驗」的樣本重建高分辨率裁切帶。

與 R2-08 的差別：
- 只做未核驗的 34 條（R2-08 已做 22，R2-07 另 5 條）
- 1 條 1 圖的兩兩拼合，寬度保留全頁（避免右側截斷）
- dpi 340，裁切帶以譜行文字層為錨，記錄 crop 坐標與圖檔 SHA-256
"""
import json
import os
import hashlib
import sqlite3
import pymupdf as fitz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(os.path.dirname(ROOT), "books",
                   "唐宋词格律 (龙榆生) (z-library.sk, 1lib.sk, z-lib.sk).pdf")
OUT = os.path.join(ROOT, "raw", "r2_09", "images")
os.makedirs(OUT, exist_ok=True)

cov = json.load(open(os.path.join(ROOT, "raw", "r2_09", "audit", "image_coverage.json"),
                     encoding="utf-8"))
samp = json.load(open(os.path.join(ROOT, "raw", "r2_08", "image_sample.json"),
                      encoding="utf-8"))["items"]
by_id = {x["form_id"]: x for x in samp}
todo = [by_id[f] for f in cov["remaining"]]

con = sqlite3.connect(os.path.join(ROOT, "database", "poetry.db"))
con.row_factory = sqlite3.Row
tex = {r["form_id"]: r["source_text"] for r in con.execute(
    "select form_id,source_text from cipai_forms_r2_07")}


def band_rect(page):
    for needle in ("＋", "－", "｜"):
        hits = page.search_for(needle)
        if hits:
            y0 = min(h.y0 for h in hits)
            y1 = max(h.y1 for h in hits)
            y1 = min(y1, y0 + 210)
            r = fitz.Rect(0, max(0, y0 - 46), page.rect.width,
                          min(page.rect.height, y1 + 16))
            if r.height > 20:
                return r
    return fitz.Rect(0, 50, page.rect.width, min(page.rect.height, 300))


doc = fitz.open(PDF)
groups = [todo[i:i + 2] for i in range(0, len(todo), 2)]
manifest = []
for gi, grp in enumerate(groups, 1):
    bands = [(it, band_rect(doc[it["pdf_page"] - 1])) for it in grp]
    W = doc[0].rect.width
    GAP = 18.0
    H = sum(r.height for _, r in bands) + GAP * (len(bands) - 1)
    out_doc = fitz.open()
    pg = out_doc.new_page(width=W, height=H)
    y = 0.0
    for it, r in bands:
        pg.show_pdf_page(fitz.Rect(0, y, W, y + r.height), doc, it["pdf_page"] - 1, clip=r)
        y += r.height + GAP
    out = os.path.join(OUT, "v_%02d.png" % gi)
    pg.get_pixmap(dpi=340).save(out)
    manifest.append({
        "group": gi, "png": out,
        "sha256": hashlib.sha256(open(out, "rb").read()).hexdigest(),
        "items": [{"form_id": it["form_id"], "cipai_name": it["cipai_name"],
                   "form_seq": it["form_seq"], "section": it["section"],
                   "pdf_page": it["pdf_page"], "printed_page": it["printed_page"],
                   "crop": [round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1)],
                   "stored_pattern": tex.get(it["form_id"], "")} for it, r in bands],
    })
    out_doc.close()
doc.close()

json.dump({"n_groups": len(manifest), "n_items": len(todo), "items": manifest},
          open(os.path.join(ROOT, "raw", "r2_09", "images", "verify_manifest.json"),
               "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("groups", len(manifest), "items", len(todo))
for m in manifest:
    print(m["group"], [i["form_id"] + " " + i["cipai_name"] for i in m["items"]])
