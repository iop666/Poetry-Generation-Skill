#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-11 工作包 E（二）：跨页谱行拼接图 + 控制样本拼版图。
用 PyMuPDF 组合（无 PIL）：把命中块按 600dpi 裁出，纵向/网格拼到新页再出图。
"""
import os, csv, json, hashlib
import pymupdf as fitz

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'reports/tasks/2026-11-15/R2-11')
IMG = os.path.join(BASE, 'raw/r2_11/images')
PDF = '<PROJECT_ROOT>/books/唐宋词格律 (龙榆生) (z-library.sk, 1lib.sk, z-lib.sk).pdf'
DPI = 600


def blocks_with_symbols(page):
    out = []
    for b in page.get_text('blocks'):
        t = b[4]
        if ('－' in t or '｜' in t) and ('（' in t or '＋' in t):
            out.append(b)
    out.sort(key=lambda b: b[1])
    return out


def stack_images(items, path, pad=6):
    """items: [(png_bytes, w_px, h_px)] 纵向拼接。"""
    w = max(i[1] for i in items) + pad * 2
    h = sum(i[2] for i in items) + pad * (len(items) + 1)
    doc = fitz.open()
    page = doc.new_page(width=w * 72 / DPI, height=h * 72 / DPI)
    y = pad
    for png, iw, ih in items:
        page.insert_image(fitz.Rect(pad * 72 / DPI, y * 72 / DPI,
                                    (pad + iw) * 72 / DPI, (y + ih) * 72 / DPI), stream=png)
        y += ih + pad
    pm = page.get_pixmap(dpi=DPI)
    pm.save(path)
    doc.close()
    return pm.width, pm.height


def grid_images(items, path, cols=2, pad=10):
    rows = (len(items) + cols - 1) // cols
    cw = max(i[1] for i in items) + pad * 2
    ch = max(i[2] for i in items) + pad * 2
    doc = fitz.open()
    page = doc.new_page(width=cw * cols * 72 / DPI, height=ch * rows * 72 / DPI)
    for k, (png, iw, ih) in enumerate(items):
        r, c = divmod(k, cols)
        x = c * cw + pad
        y = r * ch + pad
        page.insert_image(fitz.Rect(x * 72 / DPI, y * 72 / DPI,
                                    (x + iw) * 72 / DPI, (y + ih) * 72 / DPI), stream=png)
    pm = page.get_pixmap(dpi=DPI)
    pm.save(path)
    doc.close()
    return pm.width, pm.height


def crop_png(page, clip):
    pm = page.get_pixmap(clip=clip, dpi=DPI)
    return pm.tobytes('png'), pm.width, pm.height


def main():
    rows = list(csv.DictReader(open(os.path.join(BASE, 'reports/tasks/2026-11-15/R2-10/CIPAI_60_SYMBOL_VERIFICATION.csv'), encoding='utf-8-sig')))
    frag = [r for r in rows if r['verdict'] == 'TEXTLAYER_FRAGMENTED']
    ok = [r for r in rows if r['verdict'] == 'MATCH']
    doc = fitz.open(PDF)
    meta = []
    # ---- 11 条残缺：本页 + 前后页谱行，纵向拼接 ----
    for i, r in enumerate(frag, 1):
        pno = int(r['pdf_page'])
        items = []
        pages_used = []
        for cand in (pno - 1, pno, pno + 1):
            if cand < 1 or cand > doc.page_count:
                continue
            page = doc[cand - 1]
            bs = blocks_with_symbols(page)
            if not bs:
                continue
            x0 = max(page.rect.x0, min(b[0] for b in bs) - 6)
            y0 = max(page.rect.y0, min(b[1] for b in bs) - 6)
            x1 = min(page.rect.x1, max(b[2] for b in bs) + 6)
            y1 = min(page.rect.y1, max(b[3] for b in bs) + 6)
            items.append(crop_png(page, fitz.Rect(x0, y0, x1, y1)))
            pages_used.append(cand)
        name = f'R2-11_cipaiF_{i:02d}_{r["form_id"]}_p{pno}_stack.png'
        path = os.path.join(IMG, name)
        w, h = stack_images(items, path)
        meta.append(dict(idx=i, form_id=r['form_id'], cipai=r['cipai_name'], pdf_page=pno,
                         pages_used=pages_used, png=name, w=w, h=h,
                         bytes=os.path.getsize(path),
                         sha256=hashlib.sha256(open(path, 'rb').read()).hexdigest(),
                         stored_lens=r['stored_lens'], tl_lens=r['tl_lens'],
                         stored_anns=r['stored_anns'], tl_anns=r['tl_anns']))
    # ---- 20 条控制样本：取 MATCH 中每 2 条一取，4 条一图 ----
    ctrl = ok[::2][:20]
    groups = [ctrl[k:k + 4] for k in range(0, len(ctrl), 4)]
    gmeta = []
    for gi, g in enumerate(groups, 1):
        items = []
        for r in g:
            pno = int(r['pdf_page'])
            page = doc[pno - 1]
            bs = blocks_with_symbols(page)
            if not bs:
                continue
            x0 = max(page.rect.x0, min(b[0] for b in bs) - 4)
            y0 = max(page.rect.y0, min(b[1] for b in bs) - 4)
            x1 = min(page.rect.x1, max(b[2] for b in bs) + 4)
            y1 = min(page.rect.y1, max(b[3] for b in bs) + 4)
            items.append(crop_png(page, fitz.Rect(x0, y0, x1, y1)))
        name = f'R2-11_cipaiCTRL_{gi:02d}.png'
        path = os.path.join(IMG, name)
        w, h = grid_images(items, path, cols=2)
        gmeta.append(dict(group=gi, forms=[r['form_id'] for r in g],
                          cipais=[r['cipai_name'] for r in g],
                          pdf_pages=[int(r['pdf_page']) for r in g],
                          png=name, w=w, h=h, bytes=os.path.getsize(path),
                          sha256=hashlib.sha256(open(path, 'rb').read()).hexdigest()))
    json.dump({'frag': meta, 'control_groups': gmeta}, open(os.path.join(OUT, 'LOGS/cipai_images.json'), 'w'),
              ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, 'CIPAI_11_HIGH_RES_IMAGES.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['idx', 'form_id', 'cipai', 'pdf_page', 'pages_rendered', 'png', 'width_px', 'height_px',
                    'bytes', 'sha256', 'dpi'])
        for m in meta:
            w.writerow([m['idx'], m['form_id'], m['cipai'], m['pdf_page'], '|'.join(map(str, m['pages_used'])),
                        m['png'], m['w'], m['h'], m['bytes'], m['sha256'], DPI])
    print(json.dumps({'frag': [{k: m[k] for k in ('idx', 'cipai', 'pages_used', 'w', 'h', 'bytes')} for m in meta],
                      'groups': [{k: g[k] for k in ('group', 'cipais', 'w', 'h', 'bytes')} for g in gmeta]},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
