#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 WP-C3：把 60 條樣本的「譜行帶」裁切後三條拼一圖，供逐條回圖核驗。

為什麼要裁切：整頁圖 300dpi 約 0.2–0.8MB，60 張逐一目視成本過高；
譜行只佔頁面一小帶，裁切後三條拼一圖，既保留符號細節又便於批量核對。
裁切定位：以 PDF 文字層中含「＋」的行為錨點（譜行必含 ＋ 或 －｜），
上下各留 34pt，左 60pt 至右 540pt。
"""
import json, os, sqlite3
import pymupdf as fitz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw", "r2_08")
PDF = os.path.join(os.path.dirname(ROOT), "books",
                   "唐宋词格律 (龙榆生) (z-library.sk, 1lib.sk, z-lib.sk).pdf")
OUT = os.path.join(RAW, "bands")
os.makedirs(OUT, exist_ok=True)


def band_rect(page, text_fallback=""):
    """找譜行所在帶：優先含＋的行，其次含－｜的行。"""
    for needle in ("＋", "－", "｜"):
        hits = page.search_for(needle)
        if hits:
            y0 = min(h.y0 for h in hits)
            y1 = max(h.y1 for h in hits)
            # 譜行通常只佔一兩行，限制帶高
            y1 = min(y1, y0 + 190)
            r = fitz.Rect(0, max(0, y0 - 44), page.rect.width, min(page.rect.height, y1 + 14))
            if r.height > 20:
                return r
    return fitz.Rect(0, 60, page.rect.width, min(page.rect.height, 300))


def main():
    samp = json.load(open(os.path.join(RAW, "image_sample.json"), encoding="utf-8"))["items"]
    doc = fitz.open(PDF)
    groups = [samp[i:i + 2] for i in range(0, len(samp), 2)]
    manifest = []
    for gi, grp in enumerate(groups, 1):
        bands = []
        for it in grp:
            page = doc[it["pdf_page"] - 1]
            bands.append((it, band_rect(page)))
        W = doc[0].rect.width
        GAP = 16.0
        H = sum(r.height for _, r in bands) + GAP * (len(bands) - 1)
        out_doc = fitz.open()
        pg = out_doc.new_page(width=W, height=H)
        y = 0.0
        for it, r in bands:
            tgt = fitz.Rect(0, y, W, y + r.height)
            pg.show_pdf_page(tgt, doc, it["pdf_page"] - 1, clip=r)
            y += r.height + GAP
        out = os.path.join(OUT, "band_%02d.png" % gi)
        pg.get_pixmap(dpi=200).save(out)
        manifest.append({"group": gi, "png": out,
                         "items": [{"form_id": it["form_id"], "cipai_name": it["cipai_name"],
                                    "form_seq": it["form_seq"], "pdf_page": it["pdf_page"],
                                    "printed_page": it["printed_page"]} for it, _ in bands]})
        out_doc.close()
    doc.close()
    json.dump(manifest, open(os.path.join(RAW, "band_manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("groups", len(manifest), "images", len(os.listdir(OUT)))


if __name__ == "__main__":
    main()
