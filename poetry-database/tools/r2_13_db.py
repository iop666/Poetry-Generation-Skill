#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-13 入库：把三张核心候选表写入 _r2_13（全部为候选，不改历史字段）。"""
import os, csv, sqlite3
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db'); OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-13')
con = sqlite3.connect(DB); cur = con.cursor()
cur.executescript('''
DROP TABLE IF EXISTS work_text_revision_candidates_r2_13;
CREATE TABLE work_text_revision_candidates_r2_13(
  work_id TEXT PRIMARY KEY, title TEXT, author TEXT, text_raw_original TEXT, old_text_norm TEXT,
  new_text_body TEXT, new_text_variants TEXT, new_text_annotation TEXT, normalization_method TEXT,
  change_reason TEXT, review_status TEXT, applied TEXT);
DROP TABLE IF EXISTS work_author_variant_r2_13;
CREATE TABLE work_author_variant_r2_13(
  pair_id TEXT PRIMARY KEY, simplified_name TEXT, traditional_name TEXT, n_works_simp INT, n_works_trad INT,
  dynasty_simp TEXT, dynasty_trad TEXT, canonical_values TEXT, text_overlap_evidence TEXT,
  verdict TEXT, evidence TEXT, note TEXT);
DROP TABLE IF EXISTS yuanqu_text_audit_r2_13;
CREATE TABLE yuanqu_text_audit_r2_13(
  work_id TEXT PRIMARY KEY, title_raw TEXT, author_name TEXT, collection TEXT, genre TEXT, source_id TEXT,
  chapter TEXT, section TEXT, char_count INT, line_count INT, has_qu_marker INT, has_dialogue_marker INT,
  ends_with_chang_marker INT, text_head_60 TEXT, text_tail_40 TEXT, status TEXT);
''')
def load(name, table, cols):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        print('skip', name); return 0
    rows = list(csv.DictReader(open(p, encoding='utf-8-sig')))
    ph = ','.join('?' * len(cols))
    n = 0
    for r in rows:
        vals = []
        for c in cols:
            v = r.get(c, '')
            vals.append(None if v == '' else v)
        try:
            cur.execute(f'INSERT OR REPLACE INTO {table} VALUES ({ph})', vals); n += 1
        except Exception:
            pass
    return n
n1 = load('WORKS_TEXT_REPAIR_CANDIDATES.csv', 'work_text_revision_candidates_r2_13',
          ['work_id','title','author','text_raw_original','old_text_norm','new_text_body','new_text_variants',
           'new_text_annotation','normalization_method','change_reason','review_status','applied'])
n2 = load('AUTHORS_442_VARIANT_PAIRS.csv', 'work_author_variant_r2_13',
          ['pair_id','simplified_name','traditional_name','n_works_simp','n_works_trad','dynasty_simp','dynasty_trad',
           'canonical_values','text_overlap_evidence','verdict','evidence','note'])
n3 = load('YUANQU_2447_MISSING_TEXT_AUDIT.csv', 'yuanqu_text_audit_r2_13',
          ['work_id','title_raw','author_name','collection','genre','source_id','chapter','section','char_count',
           'line_count','has_qu_marker','has_dialogue_marker','ends_with_chang_marker','text_head_60','text_tail_40','status'])
con.commit()
print('inserted', n1, n2, n3)
print([ (t, con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]) for t in
        ('work_text_revision_candidates_r2_13','work_author_variant_r2_13','yuanqu_text_audit_r2_13')])
con.close()
