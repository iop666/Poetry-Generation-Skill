#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-14 A5b：按 (source_id) 内 seq 排序 + 数组顺序一一对应，验证可定位性。"""
import os, json, csv, sqlite3, re
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-14')

def han(s): return ''.join(c for c in (s or '') if '\u4e00' <= c <= '\u9fff')

con = sqlite3.connect(DB); cur = con.cursor()
cnt = dict(cur.execute('SELECT source_id,count(*) FROM works GROUP BY source_id'))
srcs = [r for r in cur.execute('SELECT s.source_id,s.local_path FROM sources s WHERE s.source_id IN (SELECT source_id FROM works)')]
srcs.sort(key=lambda x: -cnt.get(x[0], 0))
rows = []
checked_src = 0
for sid, lp in srcs:
    p = os.path.join(BASE, lp or '')
    if not os.path.exists(p):
        continue
    try:
        d = json.load(open(p, encoding='utf-8'))
    except Exception:
        continue
    if not isinstance(d, list):
        continue
    n_works = cnt.get(sid, 0)
    n_json = len(d)
    if n_works != n_json:
        rows.append([sid, lp, n_works, len(d), 'COUNT_MISMATCH', '', 0])
        continue
    ws = list(cur.execute('SELECT work_id,seq,title_raw FROM works WHERE source_id=? ORDER BY CAST(seq AS INTEGER) LIMIT 30', (sid,)))
    hit = 0
    for i, (wid, seq, title) in enumerate(ws):
        jt = (d[i].get('title') or d[i].get('rhythmic') or '') if i < len(d) else ''
        if han(jt)[:6] and han(jt)[:6] == han(title)[:6]:
            hit += 1
    rows.append([sid, lp, n_works, len(d), 'COUNT_MATCH', f'{hit}/30', hit])
    checked_src += 1
    if checked_src <= 25:
        print(sid, n_works, n_json, 'hit', hit, '/30')
    del d
    import gc; gc.collect()
cnt = [r for r in rows if r[4] == 'COUNT_MATCH']
ok = [r for r in cnt if r[6] >= 25]
print('sources count-match', len(cnt), 'position-verified(>=25/30)', len(ok), 'total checked', len(rows))
with open(os.path.join(OUT, 'LOGS/seq2_verify.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['source_id','local_path','n_works','json_len','verdict','title_hit_30','hits']); w.writerows(rows)
con.close()
