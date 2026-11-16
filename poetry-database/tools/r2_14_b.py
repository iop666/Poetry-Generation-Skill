#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-14 工作包 B：339 条正文候选的来源追溯与 120 条对校。"""
import os, json, csv, sqlite3
from collections import defaultdict, Counter
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-14')

def han(s): return ''.join(c for c in (s or '') if '\u4e00' <= c <= '\u9fff')

_rows = list(csv.reader(open(os.path.join(OUT,'LOGS/seq2_verify.csv'), encoding='utf-8-sig')))[1:]
ver = {r[0]: r for r in _rows if len(r) > 6}
con = sqlite3.connect(DB); cur = con.cursor()

cand = list(csv.DictReader(open(os.path.join(BASE,'reports/tasks/2026-11-16/R2-13/WORKS_TEXT_REPAIR_CANDIDATES.csv'), encoding='utf-8-sig')))
ids = [r['work_id'] for r in cand]
q = ','.join('?' * len(ids))
w = {r[0]: r for r in cur.execute(f'SELECT work_id,source_id,seq,title_raw,text_raw,text_norm FROM works WHERE work_id IN ({q})', ids)}
by_src = defaultdict(list)
for wid in ids:
    if wid in w:
        by_src[w[wid][1]].append(wid)

loc = {}
for sid, wids in by_src.items():
    v = ver.get(sid)
    lp = cur.execute('SELECT local_path FROM sources WHERE source_id=?', (sid,)).fetchone()
    if not lp or not v:
        for wid in wids: loc[wid] = (sid, lp[0] if lp else '', None, 'SOURCE_NOT_INDEXABLE')
        continue
    p = os.path.join(BASE, lp[0])
    try:
        d = json.load(open(p, encoding='utf-8'))
    except Exception:
        for wid in wids: loc[wid] = (sid, lp[0], None, 'FILE_PARSE_FAIL')
        continue
    ws = list(cur.execute('SELECT work_id FROM works WHERE source_id=? ORDER BY CAST(seq AS INTEGER)', (sid,)))
    if v[4] == 'COUNT_MATCH':
        idx = {x[0]: i for i, x in enumerate(ws)}
        for wid in wids:
            i = idx.get(wid)
            ok = False
            if i is not None and i < len(d):
                jt = d[i].get('title') or ''
                ok = han(jt)[:6] and han(jt)[:6] == han(w[wid][3])[:6]
            loc[wid] = (sid, lp[0], i, 'INDEX_VERIFIED' if ok else 'INDEX_UNVERIFIED')
    else:
        # 双指针顺序搜索：works 是 json 的有序子集
        pos = 0
        for wid in ws:
            t = han(w[wid][3])[:4] if wid in w else ''
            found = None
            for j in range(pos, min(len(d), pos + 40)):
                jt = han(d[j].get('title') or '')[:4]
                if t and jt == t:
                    found = j; pos = j + 1; break
            if wid in wids:
                loc[wid] = (sid, lp[0], found, 'INDEX_SEARCHED' if found is not None else 'INDEX_NOT_FOUND')
    del d
    import gc; gc.collect()

rows = []
for r in cand:
    wid = r['work_id']
    sid, lp, i, stt = loc.get(wid, ('', '', None, 'NOT_FOUND'))
    rows.append([wid, r['title'][:30], r['author'][:12], sid, lp, i,
                 'TEXT_OFFSET_LOCATOR' if stt in ('INDEX_VERIFIED','INDEX_SEARCHED') else 'FILE_LOCATOR',
                 stt, r['review_status'],
                 'SOURCE_TEXT_AVAILABLE' if stt in ('INDEX_VERIFIED','INDEX_SEARCHED') else 'SOURCE_INDEX_UNAVAILABLE'])
with open(os.path.join(OUT,'WORKS_339_SOURCE_TRACE.csv'),'w',encoding='utf-8-sig',newline='') as f:
    wtr=csv.writer(f); wtr.writerow(['work_id','title','author','source_id','source_file','json_index','locator_type','locator_status','rebuild_status','source_state']); wtr.writerows(rows)
st = Counter(x[7] for x in rows)
print('339 trace', dict(st))

# 120 条对校：按分层从可定位者中取
from collections import defaultdict as dd
strat = dd(list)
for r in cand:
    imp = r['normalization_method']
    if 'BODY_DELETED' in (r['review_status'] or '') or True:
        pass
    strat[r['review_status']].append(r)
pick = []
targets = [('SUPPORTED_RECONSTRUCTION',60),('NEEDS_REVIEW',25),('TEXT_STRUCTURE_CONFIRMED',35)]
for k,n in targets:
    pick += [r for r in strat.get(k,[]) if loc.get(r['work_id'],('','',None,''))[3] in ('INDEX_VERIFIED','INDEX_SEARCHED')][:n]
pick = pick[:120]
coll=[]
for r in pick:
    wid=r['work_id']; sid,lp,i,stt=loc[wid]
    d=json.load(open(os.path.join(BASE,lp),encoding='utf-8')) if lp else []
    jpar=''.join(d[i].get('paragraphs') or []) if i is not None and i<len(d) else ''
    db=w[wid][4] or ''
    res='EXACT' if han(jpar)==han(db) else ('VARIANT' if han(jpar) and han(db) else 'ABSENT')
    coll.append([f'B{len(coll)+1:03d}',wid,r['title'][:24],sid,lp,i,len(han(db)),len(han(jpar)),res,
                 r['review_status'],r['new_text_body'][:50].replace('\n',' ')])
    del d
with open(os.path.join(OUT,'WORKS_120_SOURCE_COLLATION.csv'),'w',encoding='utf-8-sig',newline='') as f:
    wtr=csv.writer(f); wtr.writerow(['sample_id','work_id','title','source_id','source_file','json_index','db_han_len','source_han_len','collation','rebuild_status','candidate_body_head']); wtr.writerows(coll)
print('120 collation', len(coll), dict(Counter(x[8] for x in coll)))
# 53 条 NEEDS_REVIEW 分类
nr=[r for r in cand if r['review_status']=='NEEDS_REVIEW']
cls=[]
for r in nr:
    raw=r['text_raw_original']; body=r['new_text_body']
    if raw.count('（')+raw.count('(')!=raw.count('）')+raw.count(')'):
        c='BRACKET_UNBALANCED'
    elif '〖' in raw:
        c='ANNOTATION_BOUNDARY_UNKNOWN'
    elif not body:
        c='SOURCE_TEXT_MISSING'
    elif '一作' in body:
        c='BODY_VARIANT_AMBIGUOUS'
    else:
        c='UNRESOLVED'
    cls.append([r['work_id'],r['title'][:26],c,r['review_status'],'NO','需回原书核对括号与按语边界',
                loc.get(r['work_id'],('','',None,''))[3]])
with open(os.path.join(OUT,'WORKS_53_NEEDS_REVIEW_FINAL.csv'),'w',encoding='utf-8-sig',newline='') as f:
    wtr=csv.writer(f); wtr.writerow(['work_id','title','failure_type','current_status','resolved','reason','locator_status']); wtr.writerows(cls)
print('53 needs_review', dict(Counter(x[2] for x in cls)))
json.dump({'trace':dict(st),'collation':dict(Counter(x[8] for x in coll)),'n53':dict(Counter(x[2] for x in cls))},
          open(os.path.join(OUT,'LOGS/b.json'),'w'), ensure_ascii=False, indent=1)
con.close()
