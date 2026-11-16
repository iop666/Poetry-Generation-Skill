#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-14 工作包 G：词谱页面的区域级映射（标题 bbox + 谱行范围 → form_id）。"""
import os, re, csv, json
import pymupdf as fitz
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-14')
PDF = os.path.join(BASE, '../books/唐宋词格律 (龙榆生) (z-library.sk, 1lib.sk, z-lib.sk).pdf')

def regions(doc, pno):
    """返回该页的 (标题块, 谱行块) 及其 bbox。"""
    if not (1 <= pno <= doc.page_count): return [], []
    pg = doc[pno-1]
    titles, scores = [], []
    for b in pg.get_text('blocks'):
        x0,y0,x1,y1,txt = b[0],b[1],b[2],b[3],b[4]
        s = txt.strip()
        if not s: continue
        if re.search(r'[－｜＋]', s) and '（' in s:
            scores.append((round(x0),round(y0),round(x1),round(y1), s.replace('\n','')[:40]))
        elif re.fullmatch(r'[\u4e00-\u9fff]{2,6}', s) or re.fullmatch(r'定格|格[一二三四五六]|又一体', s):
            titles.append((round(x0),round(y0),round(x1),round(y1), s))
    return titles, scores

doc = fitz.open(PDF)
m = list(csv.DictReader(open(os.path.join(BASE,'reports/tasks/2026-11-16/R2-13/CIPAI_IMAGE_11_MAPPING_REPAIR.csv'), encoding='utf-8-sig')))
idx_rows, reg_rows, rep_rows, bind_rows = [], [], [], []
for r in m:
    pno = int(r['pdf_page'] or 0)
    for p in (pno-1, pno, pno+1):
        t, s = regions(doc, p)
        idx_rows.append([f'P{p}', p, len(t), len(s),
                         ' / '.join(x[4] for x in t)[:80],
                         ' / '.join(x[4] for x in s)[:60],
                         round(doc[p-1].rect.width), round(doc[p-1].rect.height)])
    t, s = regions(doc, pno)
    # 为每个标题生成一个 region（标题 y 到下个标题 y 之间）
    ts = sorted(t, key=lambda x: x[1])
    for i, (x0,y0,x1,y1,name) in enumerate(ts):
        y_end = ts[i+1][1] if i+1 < len(ts) else (max([z[3] for z in s]) if s else y1)
        rid = f'R{pno}-{i+1}'
        lines = [z for z in s if y0-5 <= z[1] <= y_end]
        reg_rows.append([rid, f'P{pno}', pno, x0, y0, x1, y_end, name,
                         lines[0][4][:30] if lines else '', lines[-1][4][:30] if lines else '', len(lines)])
    # stack 图修复：一页两调 → 必须按标题 y 切成两个裁切区
    names = [x[4] for x in ts]
    rep_rows.append([r['idx'], r['form_id'], pno, '|'.join(names),
                     'SPLIT_BY_TITLE_REQUIRED' if len(names) > 1 else 'SINGLE_FORM_OK',
                     f'裁切 y 边界：' + ' / '.join(f'{x[4]}@{x[1]}' for x in ts)])
    bind_rows.append([r['idx'], r['form_id'], r['r2_10_cipai'], r['blind_cipai'], pno,
                      'AMBIGUOUS_MULTI_FORM' if len(names) > 1 else 'BOUND_OK',
                      r['titles_on_page'][:50], ''])
def dump(name, cols, rows):
    with open(os.path.join(OUT,name),'w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f); w.writerow(cols); w.writerows(rows)
dump('CIPAI_PAGE_REGION_INDEX.csv',['page_id','pdf_page','n_title_blocks','n_scoreline_blocks','titles','scorelines_head','page_w','page_h'],idx_rows)
dump('CIPAI_11_REGION_MAPPING.csv',['region_id','page_id','pdf_page','x0','y0','x1','y1','visible_title','first_scoreline','last_scoreline','n_scorelines'],reg_rows)
dump('CIPAI_STACK_IMAGE_REPAIR.csv',['idx','form_id','pdf_page','titles_on_page','repair_action','crop_evidence'],rep_rows)
dump('CIPAI_FORM_ID_BINDING_AUDIT.csv',['idx','form_id','db_cipai','blind_cipai','pdf_page','binding_status','page_titles','note'],bind_rows)
from collections import Counter
st={'regions':len(reg_rows),'split_required':sum(1 for x in rep_rows if x[4]=='SPLIT_BY_TITLE_REQUIRED'),
    'single':sum(1 for x in rep_rows if x[4]=='SINGLE_FORM_OK')}
json.dump(st, open(os.path.join(OUT,'LOGS/g.json'),'w'), ensure_ascii=False, indent=1)
print(json.dumps(st, ensure_ascii=False))
for x in rep_rows[:6]: print(x[0], x[2], x[3][:40], x[4])
doc.close()
