#!/usr/bin/env python3
"""books_schema.py —— 为「书」建表并导入已解析的正文

设计原则（R2-03 §5）：
    每条理论结论必须能回到「书 → 版本 → 章节 → 页码 → 原文」。
    因此页码、引擎、置信度、修订记录都要独立成列，不得合并成一段文本。

表：
    book_items       已取得的实体书与处理状态（区别于旧表 books＝书目登记）
    book_pages       逐页正文（原生提取或 OCR），含 engine/conf
    book_chapters    章节切分（EPUB 与可从页码推出的书）
    ocr_runs         每次 OCR 运行的参数与覆盖页段
    reading_progress 逐章阅读状态
    reading_notes    阅读笔记（观点/引文/我的理解，分开存）
    theory_claims    理论条目（规则、适用范围、出处页码）
"""
from __future__ import annotations

import glob
import json
import os
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "database", "poetry.db")
NAT = os.path.join(BASE, "raw", "books_native")
OCR = os.path.join(BASE, "raw", "books_ocr")

META = {
    "long_yushsheng_cilv": ("唐宋词格律", "龙榆生", "上海古籍出版社（PDF 文字层）", "pdf", "native"),
    "long_cixue_shijiang": ("词学十讲", "龙榆生", "语文教师小丛书（EPUB）", "epub", "native"),
    "wangli_gudai_hanyu": ("古代汉语常识", "王力", "EPUB（版本页未标）", "epub", "native"),
    "wangli_shicilv": ("诗词格律·诗词格律概要", "王力", "王力全集（扫描本，OCR）", "pdf", "ocr"),
    "wangli_yinyunxue": ("汉语音韵学", "王力", "王力全集（扫描本，OCR）", "pdf", "ocr"),
    "wangli_tongyuan": ("同源字典", "王力", "王力全集（扫描本，OCR）", "pdf", "ocr"),
}

DDL = """
-- 注意：库里另有一张旧表 books（R2-01 建立的「书目登记」，13 条现代专著，无正文），
-- 与本表语义不同，不可混用，也不可覆盖。故本表命名为 book_items（已取得的实体书）。
CREATE TABLE IF NOT EXISTS book_items(
  book_id TEXT PRIMARY KEY, title TEXT, author TEXT, edition TEXT,
  fmt TEXT, method TEXT, pages INTEGER, chapters INTEGER,
  chars INTEGER, ocr_pages INTEGER, native_pages INTEGER,
  status TEXT, note TEXT);

CREATE TABLE IF NOT EXISTS book_pages(
  book_id TEXT, page INTEGER, chars INTEGER, text TEXT,
  engine TEXT, conf REAL, PRIMARY KEY(book_id, page));

CREATE TABLE IF NOT EXISTS book_chapters(
  book_id TEXT, idx INTEGER, title TEXT, href TEXT, chars INTEGER, text TEXT,
  PRIMARY KEY(book_id, idx));

CREATE TABLE IF NOT EXISTS ocr_runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, book_id TEXT, engine TEXT, dpi INTEGER,
  pages_done INTEGER, low_conf INTEGER, ts TEXT, note TEXT);

CREATE TABLE IF NOT EXISTS reading_progress(
  book_id TEXT, unit TEXT, status TEXT, ts TEXT, note TEXT,
  PRIMARY KEY(book_id, unit));

CREATE TABLE IF NOT EXISTS reading_notes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, book_id TEXT, unit TEXT, page_from INTEGER,
  page_to INTEGER, topic TEXT, author_view TEXT, quote TEXT, my_comment TEXT,
  created TEXT);

CREATE TABLE IF NOT EXISTS theory_claims(
  id INTEGER PRIMARY KEY AUTOINCREMENT, book_id TEXT, page INTEGER, topic TEXT,
  claim TEXT, quote TEXT, scope TEXT, status TEXT, note TEXT);

CREATE TABLE IF NOT EXISTS cipai_specs(
  name TEXT PRIMARY KEY, aliases TEXT, char_count INTEGER, pattern TEXT,
  rhyme_note TEXT, source_book TEXT, page INTEGER, raw TEXT, parse_status TEXT);
"""


def load_pages(book_id: str):
    """原生页优先；OCR 页补洞（同一本书只会走其中一条路）。"""
    p = os.path.join(NAT, book_id, "pages.jsonl")
    if os.path.exists(p):
        return [json.loads(l) for l in open(p, encoding="utf-8")], "native"
    p = os.path.join(OCR, book_id, "pages.jsonl")
    if os.path.exists(p):
        return [json.loads(l) for l in open(p, encoding="utf-8")], "ocr"
    return [], ""


def main() -> int:
    conn = sqlite3.connect(DB)
    conn.executescript(DDL)
    for book_id, (title, author, edition, fmt, method) in META.items():
        pages, got = load_pages(book_id)
        ch_path0 = os.path.join(NAT, book_id, "chapters.jsonl")
        if not pages and os.path.exists(ch_path0):
            # EPUB 走章节不走页：以 chapter 为单位入库，等量计入 pages 统计
            chs0 = [json.loads(l) for l in open(ch_path0, encoding="utf-8")]
            pages = [{"page": c["idx"], "text": c["text"], "chars": c["chars"],
                      "engine": "epub-xhtml"} for c in chs0]
        if not pages:
            print(f"{book_id}: 无正文，跳过")
            continue
        conn.execute("DELETE FROM book_pages WHERE book_id=?", (book_id,))
        conn.execute("DELETE FROM book_chapters WHERE book_id=?", (book_id,))
        conn.executemany(
            "INSERT OR REPLACE INTO book_pages VALUES (?,?,?,?,?,?)",
            [(book_id, p["page"], p.get("chars", len(p.get("text", ""))), p.get("text", ""),
              p.get("engine", "pdf-text-layer"), p.get("conf")) for p in pages])
        ch_path = os.path.join(NAT, book_id, "chapters.jsonl")
        chapters = []
        if os.path.exists(ch_path):
            chapters = [json.loads(l) for l in open(ch_path, encoding="utf-8")]
            conn.executemany(
                "INSERT OR REPLACE INTO book_chapters VALUES (?,?,?,?,?,?)",
                [(book_id, c["idx"], c["title"], c["href"], c["chars"], c["text"]) for c in chapters])
        total_chars = sum(p.get("chars") or len(p.get("text", "")) for p in pages)
        ocr_pages = sum(1 for p in pages if p.get("engine", "").startswith("macos-vision"))
        low = sum(1 for p in pages if (p.get("conf") or 1) < 0.85)
        conn.execute("INSERT OR REPLACE INTO book_items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (book_id, title, author, edition, fmt, method, len(pages), len(chapters),
                      total_chars, ocr_pages, len(pages) - ocr_pages, "PARSED",
                      "OCR 引擎为 macOS Vision rev2（非 PaddleOCR），详见 OCR_QUALITY_REPORT"))
        if ocr_pages:
            conn.execute("""INSERT INTO ocr_runs(book_id, engine, dpi, pages_done, low_conf, ts, note)
                            VALUES (?,?,?,?,?,datetime('now'),?)""",
                         (book_id, "macos-vision-rev2", 300, ocr_pages, low,
                          "rev3 会把「平」识成「瓜」，故锁 rev2"))
        print(f"{book_id}: {title} — {len(pages)} 页 / {len(chapters)} 章 / {total_chars:,} 字"
              f"（OCR 页 {ocr_pages}，低置信 {low}）")
    conn.commit()
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
