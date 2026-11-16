#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-10 工作包 F：為指定詞格裁高分辨率譜行圖（供視覺核驗）。

按 PDF 文字層中的平仄符號位置定位譜行塊邊界（只用作裁切定位，不作為判斷依據），
輸出 500dpi 整塊圖，並記錄裁切坐標與 SHA-256。
"""
import csv
import hashlib
import json
import os
import re

import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(os.path.dirname(ROOT), "books",
                   "唐宋词格律 (龙榆生) (z-library.sk, 1lib.sk, z-lib.sk).pdf")
OUT = os.path.join(ROOT, "raw", "r2_10", "symbols", "img")
os.makedirs(OUT, exist_ok=True)
SYM = "－｜＋"


def score_rows(page):
    """回傳含平仄符號的行（按 y 排序）及其 bbox。"""
    rows = []
    d = page.get_text("dict")
    for blk in d.get("blocks", []):
        for ln in blk.get("lines", []):
            txt = "".join(sp.get("text", "") for sp in ln.get("spans", []))
            n = sum(1 for ch in txt if ch in SYM)
            if n >= 3:
                rows.append({"bbox": ln["bbox"], "text": txt, "n_sym": n})
    rows.sort(key=lambda r: r["bbox"][1])
    return rows


def main(list_path, prefix=""):
    items = json.load(open(list_path, encoding="utf-8"))
    doc = pymupdf.open(PDF)
    out = []
    for i, it in enumerate(items, 1):
        pno = it["pdf_page"] - 1
        page = doc[pno]
        rows = score_rows(page)
        # 也看下一页首幾行（跨頁譜行）
        nxt = doc[pno + 1] if pno + 1 < doc.page_count else None
        rows2 = score_rows(nxt) if nxt is not None else []
        if not rows and not rows2:
            out.append({**it, "png": None, "reason": "NO_SYMBOL_LINE"})
            continue
        y0 = rows[0]["bbox"][1] if rows else rows2[0]["bbox"][1]
        if rows:
            y1 = max(rows[-1]["bbox"][3], y0 + 220)
            clip = pymupdf.Rect(0, max(0, y0 - 16), page.rect.width, min(page.rect.height, y1 + 10))
            img = page.get_pixmap(dpi=500, clip=clip)
            png = os.path.join(OUT, "%s%02d_%s_p%d.png" % (prefix, i, it["form_id"].replace("-", "_"), it["pdf_page"]))
            img.save(png)
            out.append({**it, "png": png, "clip": [clip.x0, clip.y0, clip.x1, clip.y1],
                        "page": it["pdf_page"], "n_symbol_lines": len(rows),
                        "sha256": hashlib.sha256(open(png, "rb").read()).hexdigest(),
                        "page2_png": None})
        else:
            out.append({**it, "png": None, "reason": "ONLY_NEXT_PAGE"})
        # 若本頁最後一行接近頁底，另存下一頁頂部
        if rows and rows[-1]["bbox"][3] > page.rect.height * 0.82 and rows2:
            y1n = max(rows2[-1]["bbox"][3], rows2[0]["bbox"][1] + 220)
            clip2 = pymupdf.Rect(0, max(0, rows2[0]["bbox"][1] - 12), nxt.rect.width,
                                 min(nxt.rect.height, y1n + 12))
            png2 = os.path.join(OUT, "%s%02d_%s_p%d_next.png" % (prefix, i, it["form_id"].replace("-", "_"), it["pdf_page"] + 1))
            nxt.get_pixmap(dpi=500, clip=clip2).save(png2)
            out[-1]["page2_png"] = png2
            out[-1]["page2_sha256"] = hashlib.sha256(open(png2, "rb").read()).hexdigest()
            out[-1]["page2"] = it["pdf_page"] + 1
    _mf = os.path.join(OUT, "crop_manifest_%s.json" % (prefix or "x"))
    json.dump(out, open(_mf, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("裁切", len([x for x in out if x.get("png")]), "/", len(items))
    for x in out:
        print("  ", x["form_id"], x["cipai_name"], "p%d" % x["pdf_page"],
              "lines=%s" % x.get("n_symbol_lines"), x.get("page2_png") and "has_next")
    doc.close()


if __name__ == "__main__":
    import sys
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
