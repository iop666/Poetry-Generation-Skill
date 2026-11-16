#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-11 工作包 E（一）：把 11 条文字层残缺的词谱页按 600dpi 裁切成图，供盲读核对。"""
import os, csv, json, hashlib
import pymupdf as fitz

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'reports/tasks/2026-11-15/R2-11')
IMG = os.path.join(BASE, 'raw/r2_11/images')
PDF = '<PROJECT_ROOT>/books/唐宋词格律 (龙榆生) (z-library.sk, 1lib.sk, z-lib.sk).pdf'


def main():
    rows = list(csv.DictReader(open(os.path.join(BASE, 'reports/tasks/2026-11-15/R2-10/CIPAI_60_SYMBOL_VERIFICATION.csv'), encoding='utf-8-sig')))
    frag = [r for r in rows if r['verdict'] == 'TEXTLAYER_FRAGMENTED']
    doc = fitz.open(PDF)
    meta = []
    for i, r in enumerate(frag, 1):
        page_no = int(r['pdf_page'])
        page = doc[page_no - 1]
        blocks = page.get_text('blocks')
        hit = [b for b in blocks if ('－' in b[4] or '｜' in b[4]) and '（' in b[4]]
        if not hit:
            hit = [b for b in blocks if '－' in b[4] or '｜' in b[4]]
        if hit:
            x0 = min(b[0] for b in hit) - 8
            y0 = min(b[1] for b in hit) - 8
            x1 = max(b[2] for b in hit) + 8
            y1 = max(b[3] for b in hit) + 8
        else:
            x0, y0, x1, y1 = page.rect.x0, page.rect.y0 + 60, page.rect.x1, page.rect.y1 - 40
        clip = fitz.Rect(max(page.rect.x0, x0), max(page.rect.y0, y0), min(page.rect.x1, x1), min(page.rect.y1, y1))
        pm = page.get_pixmap(clip=clip, dpi=600)
        name = f'R2-11_cipai_{i:02d}_{r["form_id"]}_p{page_no}.png'
        path = os.path.join(IMG, name)
        pm.save(path)
        full = page.get_pixmap(dpi=200)
        fname = f'R2-11_cipai_{i:02d}_{r["form_id"]}_p{page_no}_full200.png'
        full.save(os.path.join(IMG, fname))
        meta.append(dict(idx=i, form_id=r['form_id'], cipai=r['cipai_name'], form_seq=r['form_seq'],
                         pdf_page=page_no, printed_page=r['printed_page'],
                         stored_lens=r['stored_lens'], tl_lens=r['tl_lens'],
                         stored_anns=r['stored_anns'], tl_anns=r['tl_anns'],
                         crop=f'[{x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}]',
                         png=name, png_bytes=os.path.getsize(path),
                         png_sha256=hashlib.sha256(open(path, 'rb').read()).hexdigest(),
                         full=fname))
    json.dump(meta, open(os.path.join(OUT, 'LOGS/cipai11_images.json'), 'w'), ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, 'CIPAI_11_HIGH_RES_IMAGES.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['idx', 'form_id', 'cipai', 'form_seq', 'pdf_page', 'printed_page', 'crop_rect',
                    'png', 'bytes', 'sha256', 'full_page_png'])
        for m in meta:
            w.writerow([m['idx'], m['form_id'], m['cipai'], m['form_seq'], m['pdf_page'], m['printed_page'],
                        m['crop'], m['png'], m['png_bytes'], m['png_sha256'], m['full']])
    print(json.dumps([{k: m[k] for k in ('idx', 'form_id', 'cipai', 'pdf_page', 'png_bytes', 'crop')} for m in meta],
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
