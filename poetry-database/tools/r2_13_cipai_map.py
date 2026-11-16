#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-13 工作包 H：词谱 11 张图的真实词牌映射（回 PDF 文字层核对，不靠文件名）。"""
import os, re, csv, json
import pymupdf as fitz

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-13')
PDF = os.path.join(BASE, '../books/唐宋词格律 (龙榆生) (z-library.sk, 1lib.sk, z-lib.sk).pdf')


def titles_on(doc, pno):
    """取某页上形如「词牌名」的独立短行与「定格/格一」标记。"""
    if not (1 <= pno <= doc.page_count):
        return []
    txt = doc[pno - 1].get_text()
    out = []
    for line in txt.split('\n'):
        s = line.strip()
        if not s:
            continue
        if re.fullmatch(r'[\u4e00-\u9fff]{2,6}', s) and not re.search(r'[－｜＋（）]', s):
            out.append(('TITLE_MAYBE', s))
        if re.fullmatch(r'定格|格[一二三四五六]|又一体', s):
            out.append(('GE', s))
    return out


def main():
    doc = fitz.open(PDF)
    rows = list(csv.DictReader(open(os.path.join(BASE, 'reports/tasks/2026-11-16/R2-12/CIPAI_11_DOUBLE_BLIND_REVIEW.csv'), encoding='utf-8-sig')))
    r10 = {r['form_id']: r for r in csv.DictReader(open(os.path.join(BASE, 'reports/tasks/2026-11-15/R2-10/CIPAI_60_SYMBOL_VERIFICATION.csv'), encoding='utf-8-sig'))}
    old = {r['form_id']: r for r in csv.DictReader(open(os.path.join(BASE, 'reports/tasks/2026-11-15/R2-11/CIPAI_11_HIGH_RES_IMAGES.csv'), encoding='utf-8-sig'))}
    out = []
    for i, r in enumerate(rows, 1):
        m = re.match(r'R2-11_cipaiF_\d+_(F07-\d+)_p(\d+)', r['image_file'])
        fid, pno = (m.group(1), int(m.group(2))) if m else ('?', 0)
        base = r10.get(fid, {})
        cand = []
        for p in (pno - 1, pno, pno + 1):
            for kind, s in titles_on(doc, p):
                cand.append((p, kind, s))
        titles = [c[2] for c in cand if c[1] == 'TITLE_MAYBE']
        ge = [c[2] for c in cand if c[1] == 'GE']
        # 判定：PDF 页文字层里是否出现 R2-10 记录的词牌名 / 盲读的词牌名
        db_name, blind_name = (base.get('cipai_name') or ''), (r['cipai'] or '')
        hit_db = db_name and any(db_name in t or t in db_name for t in titles)
        hit_blind = blind_name and any(blind_name in t or t in blind_name for t in titles)
        if hit_db and hit_blind:
            verd = 'BOTH_IN_PAGE_TEXT'
        elif hit_db:
            verd = 'DB_NAME_IN_TEXT_BLIND_NOT'
        elif hit_blind:
            verd = 'BLIND_NAME_IN_TEXT_DB_NOT'
        else:
            verd = 'NEITHER_IN_TEXT_LAYER'
        out.append([i, fid, pno, db_name, blind_name, r.get('n_sentences', ''), base.get('stored_sentences', ''),
                    '/'.join(sorted(set(titles)))[:80], '/'.join(sorted(set(ge)))[:30],
                    verd, 'TEXT_LAYER_CHECK', ''])
    with open(os.path.join(OUT, 'CIPAI_IMAGE_11_MAPPING_REPAIR.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['idx', 'form_id', 'pdf_page', 'r2_10_cipai', 'blind_cipai', 'blind_sentences', 'db_sentences',
                    'titles_on_page', 'ge_marks', 'verdict', 'method', 'note'])
        w.writerows(out)
    summ = {}
    for r in out:
        summ[r[9]] = summ.get(r[9], 0) + 1
    json.dump(summ, open(os.path.join(OUT, 'LOGS/cipai_map.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    for r in out:
        print(r[0], r[1], 'p%d' % r[2], '| db:', r[3], '| blind:', r[4], '|', r[9], '|', r[7][:50])
    doc.close()


if __name__ == '__main__':
    main()
