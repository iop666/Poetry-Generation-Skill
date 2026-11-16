#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-14 工作包 E：1000 抽样重审（rowid 偏差）+ 500 受控样本 + 81 联集。"""
import os, re, csv, json, sqlite3, random
from collections import Counter, defaultdict
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-14')
R13 = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-13')
HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
def han(s): return ''.join(HAN.findall(s or ''))
con = sqlite3.connect(DB); cur = con.cursor()

# ---------- E1 rowid 偏差 ----------
rows = list(csv.DictReader(open(os.path.join(R13,'WORKS_1000_STRATIFIED_SAMPLE.csv'), encoding='utf-8-sig')))
q = ','.join('?'*len(rows))
info = {r[0]: r for r in cur.execute(f'SELECT work_id,rowid,collection,dynasty,source_id FROM works WHERE work_id IN ({q})', [r['work_id'] for r in rows])}
buckets = defaultdict(Counter)
for wid, rw, coll, dyn, sid in cur.execute('SELECT work_id,rowid,collection,dynasty,source_id FROM works'):
    if rw is None: continue
    buckets[rw % 13][coll or '(null)'] += 1
out = []
for r in rows:
    i = info.get(r['work_id'])
    out.append([r['sample_id'], r['work_id'], i[1] if i else '', r['stratum'], r['collection'], r['dynasty'],
                i[4] if i else '', r['flags']])
with open(os.path.join(OUT,'WORKS_1000_ROWID_SAMPLE_REAUDIT.csv'),'w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['sample_id','work_id','rowid','stratum','collection','dynasty','source_id','flags']); w.writerows(out)
# 偏差检验：各模类中 collection 分布差异
import statistics
dist = {k: v for k, v in buckets.items()}
allc = Counter()
for v in dist.values(): allc.update(v)
top = [c for c,_ in allc.most_common(6)]
tab = []
for c in top:
    tot = allc[c]
    shares = [dist[k].get(c,0)/max(1,sum(dist[k].values())) for k in sorted(dist)]
    tab.append([c, tot, round(min(shares)*100,2), round(max(shares)*100,2), round((max(shares)-min(shares))*100,2)])
maxdev = max(x[4] for x in tab) if tab else 0
json.dump({'mod_classes': len(dist), 'top_collections': tab, 'max_share_deviation_pct': maxdev},
          open(os.path.join(OUT,'LOGS/rowid_bias.json'),'w'), ensure_ascii=False, indent=1)
print('rowid bias', json.dumps(tab[:4], ensure_ascii=False), 'maxdev', maxdev)

# ---------- E2 500 受控样本（分层随机 + 显式种子） ----------
random.seed(20261116)
# 按 source_id 分层，每层随机取，保证唯一
cnt = list(cur.execute('SELECT source_id,count(*) FROM works GROUP BY source_id ORDER BY 2 DESC'))
picked, used = [], set()
per = max(1, 500 // max(1, min(len(cnt), 60)))
for sid, n in cnt[:60]:
    ws = [x[0] for x in cur.execute('SELECT work_id FROM works WHERE source_id=? ORDER BY RANDOM() LIMIT ?', (sid, per*2))]
    for w in ws:
        if len(picked) >= 500: break
        if w in used: continue
        used.add(w); picked.append((w, sid))
    if len(picked) >= 500: break
# 不足则全库随机补
while len(picked) < 500:
    w = cur.execute('SELECT work_id FROM works ORDER BY RANDOM() LIMIT 1').fetchone()[0]
    if w in used: continue
    used.add(w); picked.append((w, ''))
det = {r[0]: r for r in cur.execute(f"SELECT work_id,title_raw,author_name,collection,genre,char_count,text_raw,text_norm,record_locator,source_id FROM works WHERE work_id IN ({','.join('?'*len(picked))})", [p[0] for p in picked])}
srows, qrows = [], []
for i,(wid,sid) in enumerate(picked,1):
    d = det.get(wid)
    if not d: continue
    rh, nh = han(d[6]), han(d[7])
    flags = []
    if len(rh) and len(nh) < len(rh)*0.95: flags.append('BODY_DELETED')
    if len(rh) and len(nh) > len(rh)*1.05: flags.append('BODY_EXPANDED')
    if re.search(r'一作|一本作', d[7] or ''): flags.append('ANNOTATION_MIXED')
    if not d[8]: flags.append('NO_LOCATOR')
    srows.append([f'S{i:04d}', wid, d[9], d[3], d[4], d[5], len(rh), len(nh), len(nh)-len(rh), '|'.join(flags) or 'OK'])
    for item, ok in [('正文未被删','BODY_DELETED' not in flags),('正文未膨胀','BODY_EXPANDED' not in flags),
                     ('校记未混入','ANNOTATION_MIXED' not in flags),('来源定位','NO_LOCATOR' not in flags)]:
        qrows.append([f'S{i:04d}', wid, item, 'PASS' if ok else 'FAIL'])
with open(os.path.join(OUT,'WORKS_500_CONTROLLED_SAMPLE.csv'),'w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['sample_id','work_id','source_id','collection','genre','char_count','raw_han_len','norm_han_len','len_delta','flags']); w.writerows(srows)
with open(os.path.join(OUT,'WORKS_500_QUALITY_AUDIT.csv'),'w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['sample_id','work_id','check_item','result']); w.writerows(qrows)
print('500 sample', len(srows), 'audit rows', len(qrows))

# ---------- E3 81 条正文问题联集 ----------
body_flags = {'BODY_PARTIAL','TITLE_REPEAT','ANNOTATION_MIXED','BODY_DELETED','BODY_EXPANDED','DUPLICATE_SUSPECTED','AUTHOR_IN_BODY'}
issue = [r for r in rows if set(r['flags'].split('|')) & body_flags]
matrix = []
for r in issue:
    fs = set(r['flags'].split('|')) & body_flags
    matrix.append([r['work_id'], r['title'][:30], len(fs), '|'.join(sorted(fs))])
lab = Counter()
for r in issue:
    for f in set(r['flags'].split('|')) & body_flags: lab[f] += 1
with open(os.path.join(OUT,'WORKS_81_BODY_ISSUE_RECONCILIATION.csv'),'w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['work_id','title','n_labels','labels']); w.writerows(matrix)
print('81 set', len(issue), dict(lab))
json.dump({'n_issue': len(issue), 'label_sum': sum(lab.values()), 'labels': dict(lab),
           'n500': len(srows), 'n500_audit': len(qrows)},
          open(os.path.join(OUT,'LOGS/e.json'),'w'), ensure_ascii=False, indent=1)
con.close()
