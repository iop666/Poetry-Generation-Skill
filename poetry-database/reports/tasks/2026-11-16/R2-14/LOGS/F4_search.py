#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F4 例词复核：以 works.text_raw 为匹配正文（opencc t2s 仅作繁简可比化），
独立检索 208 条之外的 102 条例词。只读数据库。"""
import sqlite3, csv, json, re, sys, difflib, unicodedata
from opencc import OpenCC

DB = 'database/poetry.db'
OUT = 'reports/tasks/2026-11-16/R2-14/LOGS'
cc = OpenCC('t2s')

CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')

def cjk(s):
    return ''.join(CJK.findall(s or ''))

con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
cur = con.cursor()

print('loading works ...', flush=True)
rows = cur.execute("SELECT work_id,author_name,title_raw,text_raw,cipai,collection,dynasty FROM works").fetchall()
print('works', len(rows), flush=True)

W = []
for wid, au, ti, tr, cp, col, dyn in rows:
    key = cjk(tr)
    W.append((wid, au or '', ti or '', key, cc.convert(key), cp or '', col or '', dyn or ''))
# index: 8-gram -> work idx (only for first-line probes of targets)
print('building gram index ...', flush=True)
GRAM = {}
for i, w in enumerate(W):
    s = w[4]
    for j in range(0, max(0, len(s) - 7)):
        g = s[j:j + 8]
        GRAM.setdefault(g, []).append(i)

print('grams', len(GRAM), flush=True)

def probe(example_text, k=8):
    s = cc.convert(cjk(example_text))
    if len(s) < k:
        k = len(s)
    g = s[:k]
    return s, GRAM.get(g, [])

ex = cur.execute("SELECT example_id,form_id,cipai_name,author,text,n_chars FROM cipai_form_examples_r2_08").fetchall()
EX = {r[0]: r for r in ex}
print('examples', len(EX), flush=True)

status208 = set()
with open('reports/tasks/2026-11-16/R2-13/EXAMPLE_LINK_208_RECONCILIATION.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        status208.add(r['example_id'])

targets = [e[0] for e in ex if e[0] not in status208]
print('targets', len(targets), flush=True)

def ratio(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()

def diffops(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != 'equal':
            out.append((tag, a[i1:i2], b[j1:j2]))
    return out

res = []
for eid in targets:
    _, fid, cp, au, text, n = EX[eid]
    s, cands = probe(text, 8)
    k = 8
    while not cands and k > 4:
        k -= 1
        s, cands = probe(text, k)
    best = []
    for i in cands:
        w = W[i]
        if not w[4]:
            continue
        r = ratio(s, w[4])
        best.append((r, i))
    best.sort(reverse=True)
    top = best[:8]
    if top:
        r0, i0 = top[0]
        w0 = W[i0]
        ops = diffops(s, w0[4])
        # 判定：例词是否被作品完整包含（子串）
        contained = s in w0[4] or w0[4] in s
        res.append(dict(example_id=eid, form_id=fid, cipai=cp, author=au, probe_k=k,
                        probe=s[:20], n_cand=len(cands), n_uniq=len({W[i][0] for _, i in best}),
                        best_ratio=round(r0, 4), best_work_id=w0[0], best_author=w0[1],
                        best_title=w0[2], best_text=w0[3][:120], best_cipai=w0[5],
                        best_col=w0[6], best_dyn=w0[7], contained=contained,
                        ops=[[t, a, b] for t, a, b in ops[:20]],
                        runners=[(round(r, 4), W[i][0], W[i][1]) for r, i in top[1:4]],
                        ex_len=len(s), work_len=len(w0[4])))
    else:
        res.append(dict(example_id=eid, form_id=fid, cipai=cp, author=au, probe_k=0,
                        probe=s[:20], n_cand=0, n_uniq=0, best_ratio=0, best_work_id='',
                        best_author='', best_title='', best_text='', best_cipai='', best_col='',
                        best_dyn='', contained=False, ops=[], runners=[], ex_len=len(s), work_len=0))

json.dump(res, open(f'{OUT}/f4_search_raw.json', 'w'), ensure_ascii=False, indent=1)
print('done', len(res))
for r in res[:10]:
    print(r['example_id'], r['best_ratio'], r['best_work_id'], r['best_author'], r['ops'][:2])
