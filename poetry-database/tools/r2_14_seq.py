#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-14 A5：验证 works.seq 是否为原始 JSON 数组下标（决定能否建立 TEXT_OFFSET_LOCATOR）。"""
import os, json, csv, sqlite3, random
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-14')
random.seed(20261116)


def han(s):
    return ''.join(c for c in (s or '') if '\u4e00' <= c <= '\u9fff')


con = sqlite3.connect(DB)
cur = con.cursor()
# 选 12 个覆盖不同总集的 source_id
cands = [r[0] for r in cur.execute("""SELECT source_id FROM works GROUP BY source_id
                                      ORDER BY count(*) DESC LIMIT 6""")]
cands += [r[0] for r in cur.execute("""SELECT source_id FROM works WHERE source_id LIKE 'CP-TANG%'
                                       GROUP BY source_id LIMIT 3""")]
cands += [r[0] for r in cur.execute("""SELECT source_id FROM works WHERE source_id LIKE 'CP-SONGSHI%'
                                       GROUP BY source_id LIMIT 3""")]
cands = list(dict.fromkeys(cands))[:12]
rows = []
for sid in cands:
    lp = cur.execute('SELECT local_path FROM sources WHERE source_id=?', (sid,)).fetchone()
    if not lp:
        continue
    p = os.path.join(BASE, lp[0])
    try:
        d = json.load(open(p, encoding='utf-8'))
    except Exception as e:
        rows.append([sid, lp[0], 'JSON_PARSE_FAIL', 0, 0, '', '', '', str(e)[:60]])
        continue
    n = len(d) if isinstance(d, list) else -1
    ws = list(cur.execute('SELECT work_id,seq,title_raw FROM works WHERE source_id=? LIMIT 5', (sid,)))
    seqs = [int(w[1]) for w in ws if str(w[1]).isdigit()]
    maxseq = max(seqs) if seqs else -1
    hit = 0
    for wid, seq, title in ws:
        try:
            e = d[int(seq)]
        except Exception:
            continue
        jt = e.get('title') or e.get('rhythmic') or ''
        if han(jt)[:6] and han(jt)[:6] == han(title)[:6]:
            hit += 1
    rows.append([sid, lp[0], 'OK' if isinstance(d, list) else 'NOT_LIST', n, len(ws), f'{hit}/{len(ws)}',
                 maxseq, 'SEQ_IS_INDEX' if n > 0 and maxseq < n else 'SEQ_OUT_OF_RANGE', ''])
    print(sid, 'len', n, 'hit', hit, '/', len(ws), 'maxseq', maxseq)
with open(os.path.join(OUT, 'LOGS/seq_verify.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['source_id', 'local_path', 'parse', 'json_len', 'checked', 'title_hit', 'max_seq', 'verdict', 'note'])
    w.writerows(rows)
ok = sum(1 for r in rows if r[7] == 'SEQ_IS_INDEX')
print('SEQ_IS_INDEX', ok, '/', len(rows))
con.close()
