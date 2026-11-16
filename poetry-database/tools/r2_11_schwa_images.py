#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-11 工作包 E（三）：把 50 条音标出现处按 600dpi 裁成条带，编号后拼成两幅长图供盲读。"""
import os, json, csv, hashlib
import pymupdf as fitz

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'reports/tasks/2026-11-15/R2-11')
IMG = os.path.join(BASE, 'raw/r2_11/images')
PDFS = {
    'wangli_yinyunxue': '<PROJECT_ROOT>/books/王力全集 汉语音韵学 (王力) (z-library.sk, 1lib.sk, z-lib.sk)(1).pdf',
    'wangli_tongyuan': '<PROJECT_ROOT>/books/王力全集 同源字典 (王力) (z-library.sk, 1lib.sk, z-lib.sk)(1).pdf',
}
DPI = 600


def main():
    idx = json.load(open(os.path.join(BASE, 'raw/r2_08/schwa_index.json'), encoding='utf-8'))
    items = idx['items']
    unknown = [i for i in items if i['status'] == 'UNKNOWN'][:12]
    br_e = [i for i in items if i['status'] == 'CONFIRMED_E']
    br_s = [i for i in items if i['status'] == 'CONFIRMED_SCHWA']
    sel = unknown + br_e[:30] + br_s[:60]
    # 去重同页同位置
    seen = set()
    picked = []
    for it in sel:
        k = (it['book'], it['page_pdf'], it['offset'])
        if k in seen:
            continue
        seen.add(k)
        picked.append(it)
    picked = picked[:50]
    docs = {k: fitz.open(v) for k, v in PDFS.items()}
    rows = []
    strips = []
    for n, it in enumerate(picked, 1):
        doc = docs.get(it['book'])
        if doc is None:
            continue
        pno = int(it['page_pdf'])
        page = doc[pno - 1]
        # 定位策略：OCR 文本含标记符号，无法直接 search_for；按字符偏移比例估计纵向位置，
        # 再裁一条横带（-45pt..+45pt）。定位不准者如实记 UNLOCATED。
        ptext = page.get_text()
        ratio = min(1.0, max(0.0, float(it.get('offset') or 0) / max(1, len(ptext))))
        top, bot = page.rect.y0 + 40, page.rect.y1 - 40
        y = top + ratio * (bot - top)
        clip = fitz.Rect(page.rect.x0 + 15, max(page.rect.y0, y - 45),
                         page.rect.x1 - 15, min(page.rect.y1, y + 45))
        pm = page.get_pixmap(clip=clip, dpi=DPI)
        png = pm.tobytes('png')
        strips.append((n, png, pm.width, pm.height))
        rows.append(dict(idx=n, book=it['book'], page=pno, char=it['char'], status=it['status'],
                         context_type=it['context_type'], located=1,
                         token=it.get('token'), left=(it.get('left') or '')[-30:],
                         right=(it.get('right') or '')[:30],
                         clip=f'[{clip.x0:.0f},{clip.y0:.0f},{clip.x1:.0f},{clip.y1:.0f}]'))
    # 拼两幅（每幅 25 条）
    def make(chunk, path):
        pad, lblw = 8, 70
        w = max(s[2] for s in chunk) + pad * 2 + lblw
        h = sum(s[3] for s in chunk) + pad * (len(chunk) + 1)
        doc = fitz.open()
        page = doc.new_page(width=w * 72 / DPI, height=h * 72 / DPI)
        y = pad
        for n, png, iw, ih in chunk:
            page.insert_text(fitz.Point(10 * 72 / DPI, (y + ih / 2) * 72 / DPI), f'#{n:02d}',
                             fontsize=40 * 72 / DPI, fontname='helv')
            page.insert_image(fitz.Rect((lblw + pad) * 72 / DPI, y * 72 / DPI,
                                        (lblw + pad + iw) * 72 / DPI, (y + ih) * 72 / DPI), stream=png)
            y += ih + pad
        pm = page.get_pixmap(dpi=DPI)
        pm.save(path)
        doc.close()
        return os.path.getsize(path), hashlib.sha256(open(path, 'rb').read()).hexdigest()
    outs = []
    for gi, chunk in enumerate([strips[:25], strips[25:50]], 1):
        if not chunk:
            continue
        p = os.path.join(IMG, f'R2-11_schwa_{gi:02d}.png')
        b, sha = make(chunk, p)
        outs.append(dict(group=gi, n=len(chunk), png=p, bytes=b, sha256=sha))
    json.dump({'items': rows, 'composites': outs}, open(os.path.join(OUT, 'LOGS/schwa_images.json'), 'w'),
              ensure_ascii=False, indent=1)
    print(json.dumps({'located': sum(1 for r in rows if r['located']), 'total': len(rows), 'composites': outs},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
