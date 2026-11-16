#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 E5：13 個字數異常詞格五方對帳。

五個獨立來源分列，不合併：
  declared   原書說明文字寫的字數（如「六十字」）
  scoreline  譜行符號數
  example    原書例詞字數
  db_total   R2-07 存進 total_characters 的值
  recomputed 本輪由 source_text 重算的符號數
"""
import os
import re
import json
import csv
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
OUT = os.path.join(ROOT, "raw", "r2_09", "conflicts")
os.makedirs(OUT, exist_ok=True)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row


def syms(text):
    t = re.sub(r"[（(][^）)]*[）)]", "", text or "")
    return len([c for c in t if c in "－｜＋"])


def exlen(fid):
    e = con.execute("select text from cipai_form_examples_r2_08 where form_id=? "
                    "and text is not null order by example_id limit 1", (fid,)).fetchone()
    if not e:
        return None
    return len(re.sub(r"[^\u4e00-\u9fff]", "", e["text"] or ""))


rows = []
for r in con.execute("""select f.form_id,f.cipai_name,f.form_seq,f.pattern_label,
 f.total_characters,f.declared_chars,f.sentence_count,f.source_text,f.pdf_page,f.printed_page,
 a.computed,a.declared,a.delta,a.verdict,a.evidence
 from cipai_count_audit_r2_07 a join cipai_forms_r2_07 f on f.form_id=a.form_id
 order by f.form_id"""):
    s = syms(r["source_text"])
    e = exlen(r["form_id"])
    decl = r["declared_chars"]
    dnum = None
    if decl:
        m = re.findall(r"\d+", decl)
        dnum = int(m[0]) if m else None
    verdict = r["verdict"] or ""
    note = ""
    if dnum and s:
        if s == dnum:
            note = "譜行與說明一致"
        elif e and abs(e - dnum) <= 3 and abs(s - dnum) > 3:
            note = "例詞字數近於說明，譜行多%d，疑譜行含襯字或村入符號" % (s - dnum)
        elif e and abs(e - s) <= 3:
            note = "例詞近於譜行，說明數字疑為承前格"
        elif abs(s - dnum) <= 3:
            note = "譜行與說明差 %d，屬近值" % (s - dnum)
        else:
            note = "三者皆不合，須回原書"
    rows.append({
        "form_id": r["form_id"], "cipai_name": r["cipai_name"], "form_seq": r["form_seq"],
        "pattern_label": r["pattern_label"],
        "declared_text": decl or "", "declared_num": dnum,
        "scoreline_symbols": s, "example_chars": e,
        "db_total_characters": r["total_characters"],
        "old_computed": r["computed"], "old_delta": r["delta"],
        "old_verdict": verdict,
        "recomputed_minus_declared": (s - dnum) if dnum else None,
        "note": note,
        "pdf_page": r["pdf_page"], "printed_page": r["printed_page"],
    })

with open(os.path.join(OUT, "CIPAI_WORDCOUNT_ANOMALIES.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

con.execute("DROP TABLE IF EXISTS cipai_wordcount_r2_09")
con.execute("""CREATE TABLE cipai_wordcount_r2_09(
 form_id TEXT PRIMARY KEY, cipai_name TEXT, form_seq INT, pattern_label TEXT,
 declared_text TEXT, declared_num INT, scoreline_symbols INT, example_chars INT,
 db_total_characters INT, recomputed_minus_declared INT, note TEXT, round TEXT)""")
con.executemany("""INSERT INTO cipai_wordcount_r2_09 VALUES
 (?,?,?,?,?,?,?,?,?,?,?, '2026-11-14')""",
    [(r["form_id"], r["cipai_name"], r["form_seq"], r["pattern_label"], r["declared_text"],
      r["declared_num"], r["scoreline_symbols"], r["example_chars"],
      r["db_total_characters"], r["recomputed_minus_declared"], r["note"]) for r in rows])
con.commit()

print("rows", len(rows))
for r in rows:
    print("%-10s %-6s %-4s decl=%-4s sym=%-4d ex=%-4s db=%-4s diff=%s | %s" % (
        r["form_id"], r["cipai_name"], r["form_seq"], r["declared_num"], r["scoreline_symbols"],
        r["example_chars"], r["db_total_characters"], r["recomputed_minus_declared"], r["note"]))
