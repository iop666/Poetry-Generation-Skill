#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-14 A5：为可精确定位的来源建立 work_id → (file, json_index) 映射，产出 200/100/30 级样本。"""
import os, json, csv, sqlite3, random, hashlib
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-14')
random.seed(20261116)

def han(s): return ''.join(c for c in (s or '') if '\u4e00' <= c <= '\u9fff')
def sha(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda: f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

con = sqlite3.connect(DB); cur = con.cursor()
_rows = list(csv.reader(open(os.path.join(OUT,'LOGS/seq2_verify.csv'), encoding='utf-8-sig')))[1:]
ok_src = [r[0] for r in _rows if len(r) > 6 and r[4] == 'COUNT_MATCH' and int(r[6] or 0) >= 25]
print('verified sources', len(ok_src))
cnt = dict(cur.execute('SELECT source_id,count(*) FROM works GROUP BY source_id'))
cov = sum(cnt.get(s,0) for s in ok_src)
print('works covered by verified sources', cov)

# 建立映射并抽样
pool = []
for sid in ok_src:
    lp = cur.execute('SELECT local_path FROM sources WHERE source_id=?', (sid,)).fetchone()
    if not lp: continue
    ws = list(cur.execute('SELECT work_id,seq,title_raw,text_raw FROM works WHERE source_id=? ORDER BY CAST(seq AS INTEGER)', (sid,)))
    if not ws: continue
    pool.append((sid, lp[0], ws))
print('pool sources', len(pool))
random.shuffle(pool)

rec, filechk, coll = [], [], []
n_rec = n_file = n_coll = 0
used_src = 0
for sid, lp, ws in pool:
    if n_coll >= 30 and n_file >= 100 and n_rec >= 200: break
    p = os.path.join(BASE, lp)
    try:
        d = json.load(open(p, encoding='utf-8'))
    except Exception:
        continue
    if not isinstance(d, list) or len(d) != len(ws):
        del d; continue
    fh = sha(p) if n_file < 100 else ''
    used_src += 1
    for i, (wid, seq, title, text) in enumerate(ws):
        if i >= len(d): break
        e = d[i]
        jt = e.get('title') or e.get('rhythmic') or ''
        hit = han(jt)[:6] and han(jt)[:6] == han(title)[:6]
        if not hit: continue
        if n_rec < 200:
            n_rec += 1
            rec.append([f'R{n_rec:03d}', wid, sid, lp, i, seq, title[:30], 'TEXT_OFFSET_LOCATOR', 'JSON_ARRAY_INDEX',
                         'INDEX_VERIFIED', ''])
        if n_file < 100:
            n_file += 1
            filechk.append([f'F{n_file:03d}', wid, sid, lp, os.path.getsize(p), fh, i, 'FILE_OPENED', 'INDEX_MATCH'])
        if n_coll < 30:
            jpar = ''.join(e.get('paragraphs') or [])
            same = han(jpar) == han(text)
            n_coll += 1
            coll.append([f'C{n_coll:03d}', wid, sid, lp, i, title[:24],
                         len(han(text)), len(han(jpar)), 'EXACT' if same else 'VARIANT',
                         han(jpar)[:60], han(text)[:60]])
    del d
    import gc; gc.collect()

with open(os.path.join(OUT,'WORKS_SOURCE_RECOVERY_200.csv'),'w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['sample_id','work_id','source_id','source_file','json_index','db_seq','title','locator_type','locator_method','locator_status','note']); w.writerows(rec)
with open(os.path.join(OUT,'WORKS_SOURCE_IMAGE_OR_FILE_CHECK_100.csv'),'w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['sample_id','work_id','source_id','source_file','file_bytes','file_sha256','json_index','open_status','index_match']); w.writerows(filechk)
with open(os.path.join(OUT,'WORKS_SOURCE_TEXT_COLLATION_30.csv'),'w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['sample_id','work_id','source_id','source_file','json_index','title','db_han_len','source_han_len','collation','source_head_60','db_head_60']); w.writerows(coll)
from collections import Counter
st = {'verified_sources':len(ok_src),'works_covered':cov,'pool_sources':len(pool),
      'recovery_200':len(rec),'file_check_100':len(filechk),'collation_30':len(coll),
      'collation_result':dict(Counter(x[8] for x in coll)),'sources_used':used_src}
json.dump(st, open(os.path.join(OUT,'LOGS/locator.json'),'w'), ensure_ascii=False, indent=1)
print(json.dumps(st, ensure_ascii=False, indent=1))
con.close()
