#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-13 工作包 F：50 条规范化金样本 + 全库重复候选检测。"""
import os, re, csv, json, sqlite3, random
from collections import Counter, defaultdict
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-13')
HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
random.seed(20261116)

def han(s): return ''.join(HAN.findall(s or ''))

con = sqlite3.connect(DB); cur = con.cursor()
# 50 条金样本：按结构类型分层取真实记录
cats = {
    'BRACKET_VARIANT': "text_raw LIKE '%（%一作%' OR text_raw LIKE '%(一作%'",
    'NO_BRACKET_VARIANT': "text_raw LIKE '%一作%' AND text_raw NOT LIKE '%（%一作%' AND text_raw NOT LIKE '%(一作%'",
    'PREFACE_OR_TITLE_NOTE': "text_raw LIKE '%有序%' OR text_raw LIKE '%并序%' OR text_raw LIKE '%時年%'",
    'SELF_ANNOTATION': "text_raw LIKE '%自注%' OR text_raw LIKE '%余%' OR text_raw LIKE '%予%'",
    'CIPAI_NOTE': "text_raw LIKE '%詞牌%' OR text_raw LIKE '%調見%' OR text_raw LIKE '%一名%'",
    'EDITORIAL_MARK': "text_raw LIKE '%〖%' OR text_raw LIKE '%同前%'",
    'PAGE_OR_JUAN': "text_raw LIKE '%卷之%' OR text_raw LIKE '%頁%' OR record_locator LIKE '%卷%'",
    'LONG_WORK': "char_count >= 800",
}
rows = []
n = 0
for cat, where in cats.items():
    pool = list(cur.execute(f'SELECT work_id,title_raw,author_name,text_raw,text_norm,source_id,record_locator FROM works WHERE {where} ORDER BY RANDOM() LIMIT 8'))
    for r in pool[:7 if cat != 'LONG_WORK' else 6]:
        n += 1
        wid, title, au, raw, norm, sid, loc = r
        raw = raw or ''
        ideal = re.sub(r'[（(][^（）()]{0,300}[）)]', '', raw)
        rows.append([f'GN-{n:03d}', cat, wid, (title or '')[:30], (au or '')[:12],
                     len(han(raw)), len(han(norm)), len(han(ideal)),
                     raw[:120].replace('\n', '⏎'), norm[:120], ideal[:120].replace('\n', '⏎'),
                     sid or '', loc or '',
                     'body = text_raw 去全部括号结构；variants = 括号内含「一作/一本作/一云」者；'
                     'annotation = 其余括号与「同前。》《…」类编者语',
                     'BODY_MUST_KEEP_ALL_NON_BRACKET_CHARS'])
with open(os.path.join(OUT, 'TEXT_NORMALIZATION_GOLDEN_50.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['fixture_id', 'structure_type', 'work_id', 'title', 'author', 'raw_han_len', 'norm_han_len',
                'expected_body_han_len', 'raw_excerpt', 'old_norm_excerpt', 'expected_body_excerpt',
                'source_id', 'locator', 'normalization_rule', 'assertion'])
    w.writerows(rows)
print('golden', len(rows))

# ---------- 重复候选：全库前 20 字分组 ----------
g = defaultdict(list)
for wid, tn, tr, au, ti in cur.execute('SELECT work_id,text_norm,text_raw,author_name,title_raw FROM works'):
    k = han(tn)[:20] or han(tr)[:20]
    if len(k) < 12:
        continue
    if len(g[k]) < 6:
        g[k].append((wid, au or '', (ti or '')[:24]))
dups = [(k, v) for k, v in g.items() if len(v) > 1]
print('dup groups', len(dups))
with open(os.path.join(OUT, 'WORKS_DUPLICATE_CANDIDATES.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['group_id', 'n_members', 'key_head', 'member_work_ids', 'authors', 'titles', 'dup_type', 'note'])
    for i, (k, v) in enumerate(dups[:2000], 1):
        authors = {x[1] for x in v}
        dtyp = 'SAME_AUTHOR_DUP' if len(authors) == 1 else 'CROSS_AUTHOR_DUP'
        w.writerow([f'DG-{i:05d}', len(v), k, '|'.join(x[0] for x in v), '|'.join(sorted(authors))[:60],
                    '|'.join(x[2] for x in v)[:120], dtyp, '仅按前 20 字判定，须人工核版本差异'])
json.dump({'golden': len(rows), 'dup_groups': len(dups),
           'dup_members': sum(len(v) for _, v in dups)},
          open(os.path.join(OUT, 'LOGS/norm_dup.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps({'golden': len(rows), 'dup_groups': len(dups), 'dup_members': sum(len(v) for _, v in dups)}, ensure_ascii=False))
con.close()
