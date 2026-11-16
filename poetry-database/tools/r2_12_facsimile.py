#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-12 工作包 B 工具：从维基共享资源按页取公共领域影印页，裁半叶，记录哈希。

底本（广韵）：File:SBL015 廣韻.pdf —— 大宋重修廣韻 5 卷，宋孝宗朝初期刊，靜嘉堂文庫藏（扫描件来源见
  Commons 文件页；本项目仅使用其公有领域扫描图作对校，不转载）。
底本（集韵）：File:NLC892-412000002841-17473 集韻 第1冊.pdf —— 中国国家图书馆藏。
"""
import os, sys, json, hashlib, urllib.request, urllib.parse

UA = 'PoetryDatabank/1.0 (academic collation; contact researcher@example.org)'
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(BASE, 'raw/r2_12/facsimile')
FILES = {
    'GUANGYUN': 'File:SBL015 廣韻.pdf',
    'JIYUN': 'File:NLC892-412000002841-17473 集韻 第1冊.pdf',
}


def thumb_url(title, page, width=2560):
    q = urllib.parse.urlencode({'action': 'query', 'titles': title, 'prop': 'imageinfo',
                                'iiprop': 'url', 'iiurlwidth': width, 'format': 'json', 'formatversion': '2'})
    r = urllib.request.Request('https://commons.wikimedia.org/w/api.php?' + q, headers={'User-Agent': UA})
    d = json.load(urllib.request.urlopen(r, timeout=60))
    u = d['query']['pages'][0]['imageinfo'][0]['thumburl']
    return u.replace('page1-', f'page{page}-')


def fetch(book, page, width=2560):
    os.makedirs(IMG, exist_ok=True)
    name = f'{book}_p{page:03d}.jpg'
    path = os.path.join(IMG, name)
    if not os.path.exists(path) or os.path.getsize(path) < 10000:
        u = thumb_url(FILES[book], page, width)
        data = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=120).read()
        open(path, 'wb').write(data)
    return path


def halves(path, book, page):
    """裁左右半叶（古籍扫描常见一图两半叶）。用 PyMuPDF 处理位图，无需 PIL。"""
    import pymupdf as fitz
    doc = fitz.open(path)
    pg = doc[0]
    r = pg.rect
    out = []
    boxes = [fitz.Rect(r.x0 + r.width * 0.03, r.y0 + r.height * 0.04, r.x0 + r.width * 0.52, r.y0 + r.height * 0.97),
             fitz.Rect(r.x0 + r.width * 0.48, r.y0 + r.height * 0.04, r.x0 + r.width * 0.98, r.y0 + r.height * 0.97)]
    for i, box in enumerate(boxes):
        pix = pg.get_pixmap(clip=box, matrix=fitz.Matrix(1.6, 1.6))
        p = os.path.join(IMG, f'{book}_p{page:03d}_{"LR"[i]}.png')
        pix.save(p)
        out.append(p)
    doc.close()
    return out


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


if __name__ == '__main__':
    book = sys.argv[1] if len(sys.argv) > 1 else 'GUANGYUN'
    pages = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else [11]
    rec = []
    for p in pages:
        f = fetch(book, p)
        hs = halves(f, book, p)
        rec.append(dict(book=book, page=p, file=f, bytes=os.path.getsize(f), sha256=sha(f),
                        halves=[dict(path=h, bytes=os.path.getsize(h), sha256=sha(h)) for h in hs]))
        print(json.dumps(rec[-1], ensure_ascii=False))
    log = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-12/LOGS/facsimile_fetch.json')
    old = []
    if os.path.exists(log):
        old = json.load(open(log))
    json.dump(old + rec, open(log, 'w'), ensure_ascii=False, indent=1)
