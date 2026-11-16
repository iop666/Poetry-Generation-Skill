#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F4 第二轮：对首轮无命中/低分者用 4-6 字探针与异体折叠重搜。只读库。"""
import sqlite3, csv, json, re, difflib
from opencc import OpenCC

DB='database/poetry.db'; OUT='reports/tasks/2026-11-16/R2-14/LOGS'
cc=OpenCC('t2s'); CJK=re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
cjk=lambda s: ''.join(CJK.findall(s or ''))
FOLD=str.maketrans({'沈':'沉','攲':'欹','敧':'欹','裏':'里','裡':'里','濛':'蒙','著':'着','甯':'宁','牀':'床','悽':'凄','喫':'吃'})
def key(s): return cc.convert(cjk(s)).translate(FOLD)

con=sqlite3.connect(f'file:{DB}?mode=ro',uri=True); cur=con.cursor()
rows=cur.execute("SELECT work_id,author_name,title_raw,text_raw,cipai FROM works").fetchall()
W=[(r[0],r[1] or '',r[2] or '',cjk(r[3]),key(r[3]),r[4] or '') for r in rows]
ex={r[0]:r for r in cur.execute("SELECT example_id,cipai_name,author,text FROM cipai_form_examples_r2_08").fetchall()}
raw={r['example_id']:r for r in json.load(open(f'{OUT}/f4_search_raw.json'))}

def ratio(a,b): return difflib.SequenceMatcher(None,a,b,autojunk=False).ratio()
def ops(a,b):
    sm=difflib.SequenceMatcher(None,a,b,autojunk=False)
    return [[t,a[i1:i2],b[j1:j2]] for t,i1,i2,j1,j2 in sm.get_opcodes() if t!='equal']

retry=[e for e,r in raw.items() if r['best_ratio']<0.99]
print('retry',len(retry))
out={}
for eid in retry:
    _,cp,au,text=ex[eid]; s=key(text)
    best=[]
    for k in (7,6,5,4):
        if len(s)<k: continue
        for start in (0,):
            probe=s[start:start+k]
            for i,w in enumerate(W):
                if probe and probe in w[4]:
                    best.append((ratio(s,w[4]),i,k))
    seen={}
    for r,i,k in sorted(best,reverse=True):
        if W[i][0] not in seen: seen[W[i][0]]=(r,i,k)
    top=sorted(seen.values(),reverse=True)[:5]
    out[eid]=dict(example_id=eid,cipai=cp,author=au,ex_key=s[:30],hits=len(seen),
                  cands=[(round(r,4),W[i][0],W[i][1],W[i][2],W[i][3][:60],k) for r,i,k in top],
                  diffs=[[t,a,b] for t,a,b in ops(s,W[top[0][1]][4])[:15]] if top else [])
    print(eid, round(top[0][0],4) if top else 0, W[top[0][1]][2][:10] if top else '', W[top[0][1]][1] if top else '', out[eid]['diffs'][:3])
json.dump(out,open(f'{OUT}/f4_search_retry.json','w'),ensure_ascii=False,indent=1)
