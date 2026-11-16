#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
query.py —— 数据库查询演示（命令行）

用法：
  python3 tools/query.py stats
  python3 tools/query.py author 杜甫
  python3 tools/query.py genre 七言律诗 --limit 5
  python3 tools/query.py search 落木 --limit 8
  python3 tools/query.py cipai 浣溪沙 --limit 5
  python3 tools/query.py source CP-TANG-07
  python3 tools/query.py coverage
  python3 tools/query.py sql "SELECT dynasty, COUNT(*) FROM works GROUP BY dynasty"
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "database", "poetry.db")


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def show(rows, text_key="text_norm", n=60):
    for r in rows:
        keys = r.keys()
        head = f"{r['work_id']:<20} {r['author_name'][:8]:<8} [{r['genre']}] {r['title_norm'][:22]}"
        print(head)
        if text_key in keys:
            t = r[text_key] or ""
            print(f"    {t[:n]}{'…' if len(t) > n else ''}")
            print(f"    来源 {r['source_id']}　朝代 {r['dynasty']}　{len(t)} 字　核验 {r['verify_status']}")
        print()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("arg", nargs="?", default="")
    ap.add_argument("--limit", type=int, default=10)
    a = ap.parse_args()
    c = conn()

    if a.cmd == "stats":
        for q, label in [
            ("SELECT COUNT(*) FROM works", "作品记录"),
            ("SELECT COUNT(*) FROM works WHERE dup_status!='DUPLICATE'", "去重后"),
            ("SELECT COUNT(*) FROM authors", "作者"),
            ("SELECT COUNT(*) FROM sources", "来源"),
            ("SELECT COUNT(*) FROM works WHERE verify_status='AUTO'", "自动标注（未核验）"),
            ("SELECT COUNT(*) FROM works WHERE variant_group!=''", "参与重复/异文组"),
        ]:
            print(f"{label:<18}{c.execute(q).fetchone()[0]:>8,}")
        print("\n按体裁：")
        for r in c.execute("SELECT genre, COUNT(*) n FROM works GROUP BY genre ORDER BY n DESC"):
            print(f"  {r['genre']:<10}{r['n']:>8,}")
        print("\n按朝代：")
        for r in c.execute("SELECT dynasty, COUNT(*) n FROM works GROUP BY dynasty ORDER BY n DESC"):
            print(f"  {r['dynasty']:<8}{r['n']:>8,}")
        return 0

    if a.cmd == "author":
        rows = c.execute("SELECT * FROM works WHERE author_name LIKE ? LIMIT ?",
                         (f"%{a.arg}%", a.limit)).fetchall()
        print(f"作者含「{a.arg}」的作品 {len(rows)} 条（显示上限 {a.limit}）\n")
        show(rows)
        return 0

    if a.cmd == "genre":
        rows = c.execute("SELECT * FROM works WHERE genre=? ORDER BY char_count DESC LIMIT ?",
                         (a.arg, a.limit)).fetchall()
        show(rows)
        return 0

    if a.cmd == "search":
        rows = c.execute("SELECT * FROM works WHERE text_norm LIKE ? LIMIT ?",
                         (f"%{a.arg}%", a.limit)).fetchall()
        print(f"含「{a.arg}」的作品 {len(rows)} 条\n")
        show(rows)
        return 0

    if a.cmd == "cipai":
        rows = c.execute("SELECT * FROM works WHERE cipai LIKE ? LIMIT ?",
                         (f"%{a.arg}%", a.limit)).fetchall()
        show(rows)
        return 0

    if a.cmd == "source":
        rows = c.execute("SELECT * FROM sources WHERE source_id=?", (a.arg,)).fetchall()
        for r in rows:
            print(f"{r['source_id']}　{r['name']}")
            print(f"  许可：{r['license']}")
            print(f"  可靠性：{r['reliability']}")
            print(f"  路径：{r['local_path']}　{dict(r).get('bytes')} 字节")
            print(f"  URL：{r['url']}")
        n = c.execute("SELECT COUNT(*) FROM works WHERE source_id=?", (a.arg,)).fetchone()[0]
        print(f"  收录作品：{n} 条")
        return 0

    if a.cmd == "coverage":
        print("朝代 × 体裁 覆盖：\n")
        rows = c.execute("""SELECT dynasty, genre, COUNT(*) n FROM works
                            GROUP BY dynasty, genre ORDER BY dynasty, n DESC""").fetchall()
        cur = None
        for r in rows:
            if r["dynasty"] != cur:
                cur = r["dynasty"]
                print(f"\n【{cur}】")
            print(f"  {r['genre']:<10}{r['n']:>7,}")
        return 0

    if a.cmd == "sql":
        try:
            rows = c.execute(a.arg).fetchall()
        except Exception as ex:  # noqa: BLE001
            print("SQL 错误：", ex)
            return 1
        for r in rows:
            print(dict(r))
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
