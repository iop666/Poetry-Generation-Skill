#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_books.py —— 维基文库 wikitext → 可读纯文本

只做「去标记」，不动字：
  · 去掉 {{模板}}、[[链接|显示]]→显示、'''粗体'''、<ref>…</ref>、分类、__NOEDITSECTION__
  · 保留标题层级（== 标题 == → 【标题】）
  · 保留标点与分行

原始 wikitext 永不改动，仍在 raw/books/。
输出：normalized/books/<source_id>.txt，首行写入来源与许可，便于单独流通时仍带出处。
"""

from __future__ import annotations

import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(BASE, "sources", "manifest.json")
OUTDIR = os.path.join(BASE, "normalized", "books")



def _tpl_repl(m):
    """
    模板处理：{{ProperNoun|唐}} → 唐；{{參|辨|一作「辯」}} → 辨；{{PD-old}} / {{header|title=..}} → 删。
    只保留第一个位置参数；第一个参数若形如 k=v（具名参数，属版式模板）则整体删除。
    """
    inner = m.group(1)
    parts = inner.split("|")
    if len(parts) < 2:
        return ""
    first = parts[1].strip()
    if "=" in first:
        return ""
    return first


def _reduce_templates(s: str) -> str:
    # 由内向外反复消解，最多 5 层
    for _ in range(5):
        new = re.sub(r"\{\{([^{}]*)\}\}", _tpl_repl, s)
        if new == s:
            break
        s = new
    return s


def strip_wiki(s: str) -> str:
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"__[A-Z]+__", "", s)
    s = re.sub(r"\[\[Category:[^\]]*\]\]", "", s)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)      # [[a|b]] → b
    s = _reduce_templates(s)
    s = s.replace("'''", "").replace("''", "")
    s = re.sub(r"^[*#:;]+\s*", "", s, flags=re.M)                 # 列表符
    s = re.sub(r"^-{4,}.*$", "", s, flags=re.M)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def main() -> int:
    man = json.load(open(MANIFEST, encoding="utf-8"))
    os.makedirs(OUTDIR, exist_ok=True)
    n = 0
    for e in man["poetry_sources"]:
        if e.get("format") == "json":
            continue
        src = os.path.join(BASE, e["local"])
        if not os.path.exists(src):
            print(f"[MISS] {e['source_id']}  {e['local']}")
            continue
        raw = open(src, encoding="utf-8", errors="replace").read()
        body = strip_wiki(raw)
        # 标题行：== X == → 【X】
        body = re.sub(r"^={2,}\s*(.+?)\s*={2,}$", r"【\1】", body, flags=re.M)
        hdr = (f"# {e['name']}\n"
               f"> 来源：{e['url']}\n"
               f"> 维护：{e['maintainer']}\n"
               f"> 许可：{e['license']}\n"
               f"> 可靠性：{e['reliability']}\n"
               f"> 说明：{e.get('note','')}\n"
               f"> 本文件由 tools/convert_books.py 从 raw/books/{os.path.basename(e['local'])} 去标记生成；"
               f"原始 wikitext 保留未改。\n\n")
        dst = os.path.join(OUTDIR, e["source_id"].lower() + ".txt")
        with open(dst, "w", encoding="utf-8") as f:
            f.write(hdr + body + "\n")
        n += 1
        print(f"[BOOK] {e['source_id']:<18} {len(body):>7,} 字  → {os.path.basename(dst)}")
    print(f"\n共转换 {n} 种文献 → normalized/books/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
