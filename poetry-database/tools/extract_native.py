#!/usr/bin/env python3
"""extract_native.py —— 对「有文字层」的 PDF 与 EPUB 做原生提取（不 OCR）

分工（对应 R2-03 §3.1/3.2）：
    PDF：先检测文字层。有则原生提取；无则交给 ocr_pdf.py（Vision rev2）。
    EPUB：直接解析内部 XHTML，保留目录、章节、段落与注释，不做 OCR。

产出统一到 raw/books_native/<book_id>/：
    pages.jsonl      （PDF）page / text / chars
    chapters.jsonl   （EPUB）idx / title / href / text / chars
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from pypdf import PdfReader

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(BASE)
OUT = os.path.join(BASE, "raw", "books_native")

BOOKS = {
    "long_yushsheng_cilv": ("pdf", "books/唐宋词格律 (龙榆生) (z-library.sk, 1lib.sk, z-lib.sk).pdf"),
    "long_cixue_shijiang": ("epub", "books/词学十讲 (龙榆生) (z-library.sk, 1lib.sk, z-lib.sk)(1).epub"),
    "wangli_gudai_hanyu": ("epub", "books/古代汉语常识(语言学大师王力专力编写,古代汉语初学者入_ (z-library.sk, 1lib.sk, z-lib.sk).epub"),
}


def clean(t: str) -> str:
    t = t.replace("\u3000", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def do_pdf(bid: str, path: str) -> None:
    outdir = os.path.join(OUT, bid)
    os.makedirs(outdir, exist_ok=True)
    r = PdfReader(path)
    pages, empty = [], 0
    for i, pg in enumerate(r.pages):
        try:
            t = pg.extract_text() or ""
        except Exception:
            t = ""
        if not t.strip():
            empty += 1
        pages.append({"page": i + 1, "text": clean(t), "chars": len(t.strip())})
    with open(os.path.join(outdir, "pages.jsonl"), "w", encoding="utf-8") as f:
        for p in pages:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    total = sum(p["chars"] for p in pages)
    print(f"{bid}: {len(pages)} 页，空页 {empty}，共 {total:,} 字，"
          f"均 {total // max(1, len(pages))} 字/页")


def _spine(z: zipfile.ZipFile, names: list) -> list:
    """按 OPF spine 给出阅读顺序；拿不到就退回文件名排序。"""
    html = sorted(n for n in names if n.lower().endswith((".xhtml", ".html", ".htm")))
    opf = [n for n in names if n.lower().endswith(".opf")]
    if not opf:
        return html
    try:
        root = ET.fromstring(z.read(opf[0]))
    except Exception:
        return html
    ns = {"o": "http://www.idpf.org/2007/opf"}
    items = root.findall(".//o:manifest/o:item", ns) or root.findall(".//manifest/item")
    refs = root.findall(".//o:spine/o:itemref", ns) or root.findall(".//spine/itemref")
    base = os.path.dirname(opf[0])
    idmap = {it.get("id"): it.get("href") for it in items}
    order = []
    for ref in refs:
        href = idmap.get(ref.get("idref"))
        if href:
            order.append(os.path.normpath(os.path.join(base, href)))
    order = [n for n in order if n in names]
    return order or html


def do_epub(bid: str, path: str) -> None:
    outdir = os.path.join(OUT, bid)
    os.makedirs(outdir, exist_ok=True)
    z = zipfile.ZipFile(path)
    names = z.namelist()
    chapters = []
    for n in _spine(z, names):
        try:
            soup = BeautifulSoup(z.read(n), "html.parser")
        except Exception:
            continue
        for t in soup(["script", "style"]):
            t.decompose()
        h = soup.find(["h1", "h2", "h3"])
        title = h.get_text(strip=True) if h else ""
        body = clean(soup.get_text("\n"))
        if len(body) < 50:
            continue
        title = title or body.split("\n")[0][:40]
        chapters.append({"idx": len(chapters), "title": title, "href": n,
                         "text": body, "chars": len(body)})
    with open(os.path.join(outdir, "chapters.jsonl"), "w", encoding="utf-8") as f:
        for c in chapters:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    total = sum(c["chars"] for c in chapters)
    print(f"{bid}: {len(chapters)} 章，{total:,} 字")
    for c in chapters[:8]:
        print(f"    [{c['idx']:>2}] {c['chars']:>6} 字  {c['title'][:40]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default="all")
    args = ap.parse_args()
    for bid, (kind, rel) in BOOKS.items():
        if args.book not in ("all", bid):
            continue
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            print("缺文件:", bid, path)
            continue
        (do_pdf if kind == "pdf" else do_epub)(bid, path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
