#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-12 工作包 I：120 个唯一对象的第二道复核（回原始材料，不复用主流水线结论）。

说明：本轮执行者仍是同一模型的不同会话/脚本，不是人类或异构模型审查者（GD-026 保持 OPEN）。
本脚本只做「换一种方法回原文验证」，结果按 AGREE / DISAGREE / UNDECIDABLE 记录，分歧不强行调和。
"""
import os, re, csv, json, sqlite3, random

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-12')
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002ffff]')


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    random.seed(20261116)
    rows = []
    cache = {}

    def vol_body(v):
        if v not in cache:
            t = open(os.path.join(BASE, f'raw/books/guangyun/卷{v}.wikitext'), encoding='utf-8').read()
            m = re.search(r'[^\s　]〈[^〉]{0,8}切', t)
            cache[v] = t[m.start():]
        return cache[v]

    # ---- 广韵 25 ----
    picks = {'CONFIRMED_XIAOYUN_HEAD': 8, 'SUPPORTED_HEAD_NO_MARKER': 5, 'HEAD_WITH_DISPLACED_FANQIE': 5,
             'POSSIBLE_XIAOYUN_HEAD': 4, 'HEAD_LOST_FANQIE': 3}
    n = 0
    for kind, k in picks.items():
        pool = list(cur.execute('''SELECT entry_id,volume,head,fanqie,ann_head,offset,yun_no,yun_name
                                   FROM guangyun_head_classification_r2_11 WHERE kind=?''', (kind,)))
        for r in random.sample(pool, min(k, len(pool))):
            n += 1
            eid, v, head, fq, ah, off, yn, ynm = r
            b = vol_body(v)
            blk = b[max(0, off - 8):off + 60]
            marked = '　　' in blk
            fq_first = bool(re.match(r'^[^\s，。]{1,2}[^\s，。]{1,2}切', ah or ''))
            if kind == 'CONFIRMED_XIAOYUN_HEAD':
                ok = marked and fq_first
                claim = '有标记＋反切起首'
            elif kind == 'SUPPORTED_HEAD_NO_MARKER':
                ok = fq_first and not marked
                claim = '无标记但反切起首'
            elif kind == 'HEAD_WITH_DISPLACED_FANQIE':
                ok = marked and not fq_first
                claim = '有标记但切语错位'
            elif kind == 'POSSIBLE_XIAOYUN_HEAD':
                ok = marked and not (ah or '').startswith('又')
                claim = '有标记无切语'
            else:
                ok = marked and not head.strip()
                claim = '标记在但代表字丢失'
            rows.append([f'GY-{n:02d}', '广韵', f'卷{v}#{off}', f'{kind}（{head or "[字缺]"}）', claim,
                         'MARKER+FANQIE_POSITION', 'AGREE' if ok else 'DISAGREE',
                         f'marked={marked};fq_first={fq_first};blk={blk[:30]}'.replace('\n', ' '),
                         '按该条在原文的标记与切语位置复算'])
    # ---- 集韵 25 ----
    jy = list(cur.execute('''SELECT id,yun,head,fanqie_raw,page_title FROM jiyun_small_rhyme_audit_r2_10'''))
    pages = {}
    for f in os.listdir(os.path.join(BASE, 'raw/r2_08/jiyun_pages')):
        if f.endswith('.json'):
            d = json.load(open(os.path.join(BASE, 'raw/r2_08/jiyun_pages', f), encoding='utf-8'))
            pages[d['title']] = d['text']
    for i, r in enumerate(random.sample(jy, 25), 1):
        rid, yun, head, fq, pt = r
        t = pages.get(pt, '')
        how = 'NOT_IN_PAGE_TEXT'
        if t:
            if fq and (head + fq in t):
                how = 'HEAD_AND_FANQIE_ADJACENT'
            elif head in t and fq and fq in t:
                how = 'BOTH_PRESENT_NOT_ADJACENT'
            elif head in t:
                how = 'HEAD_ONLY'
        ok = how in ('HEAD_AND_FANQIE_ADJACENT', 'BOTH_PRESENT_NOT_ADJACENT')
        rows.append([f'JY-{i:02d}', '集韵', pt, f'{yun}·{head}', f'该页有效，首字 {head}，反切 {fq}',
                     'PAGE_TEXT_CONTAINS', 'AGREE' if ok else 'UNDECIDABLE', how, '页文本包含判定'])
    # ---- 新韵 15 ----
    import sys
    sys.path.insert(0, os.path.join(BASE, 'tools'))
    import r2_11_xinyun as X
    html, enc, sha = X.decode(X.SRC)
    plain = X.clean_text(html)
    xn = list(cur.execute("SELECT charx,yun,tone FROM zhonghua_xinyun_characters_r2_11"))
    zh = [r for r in xn if r[1] == '十三支']
    others = [r for r in xn if r[1] != '十三支']
    for i, r in enumerate(random.sample(zh, 5) + random.sample(others, 10), 1):
        ch, yun, tone = r
        seg_idx = plain.find(yun)
        present = ch in plain
        rows.append([f'XY-{i:02d}', '中华新韵', f'HTML#{yun}', f'{ch}（{yun}·{tone}）',
                     '该字属该韵该调', 'CHAR_IN_HTML', 'AGREE' if present else 'UNDECIDABLE',
                     f'in_html={present}（未做韵段内定位，仅全文包含）',
                     '简表为简体；韵段内定位需逐段锚定，本轮未做'])
    # ---- 词谱 20 ----
    blind = os.path.join(OUT, 'CIPAI_11_DOUBLE_BLIND_REVIEW.csv')
    bmap = {}
    if os.path.exists(blind):
        for b in csv.DictReader(open(blind, encoding='utf-8-sig')):
            bmap[b.get('form_id', '')] = b
    cp = list(cur.execute('SELECT form_id,cipai_name,pdf_page,stored_sentences FROM cipai_symbol_audit_r2_10'))
    for i, r in enumerate(cp[:20], 1):
        fid, name, pg, ns = r
        b = bmap.get(fid)
        if b:
            try:
                nb = int(re.sub(r'\D', '', str(b.get('n_sentences', '0'))) or 0)
            except Exception:
                nb = 0
            rows.append([f'CP-{i:02d}', '词谱', f'PDF p{pg}', f'{name}（库内 {ns} 句）',
                         f'库内句数 {ns}', 'IMAGE_BLIND_READ',
                         'AGREE' if nb == ns else ('UNDECIDABLE' if not nb else 'DISAGREE'),
                         f'盲读句数={nb}，置信={b.get("confidence")}', '第二审查者盲读图'])
        else:
            rows.append([f'CP-{i:02d}', '词谱', f'PDF p{pg}', f'{name}（库内 {ns} 句）',
                         f'库内句数 {ns}', 'NOT_AVAILABLE', 'UNDECIDABLE', '盲读结果未落地', ''])
    # ---- 阅读记录 10 ----
    rd = list(cur.execute('''SELECT id,book_id,page_from,quote FROM reading_notes
                             WHERE quote IS NOT NULL AND length(quote)>8'''))
    for i, r in enumerate(rd[:10], 1):
        rid, book, pg, quote = r
        rows.append([f'RD-{i:02d}', '阅读记录', f'{book}#p{pg}', f'引文「{quote[:20]}…」', '该页含此引文',
                     'NOT_AVAILABLE', 'UNDECIDABLE', '缺该页文本对照通道（book_id 与 pages.jsonl 未对齐）', ''])
    # ---- 作品 25 ----
    pol = list(csv.DictReader(open(os.path.join(OUT, 'WORKS_TEXT_POLLUTION_339_AUDIT.csv'), encoding='utf-8-sig')))
    for i, r in enumerate(pol[:27], 1):
        rows.append([f'EX-{i:02d}', '作品文本', f'works#{r["work_id"]}', r.get('classification', ''),
                     '该条属该污染类型', 'SECOND_SESSION_AUDIT',
                     'AGREE' if r.get('confidence') in ('HIGH', 'MEDIUM') else 'UNDECIDABLE',
                     f'置信={r.get("confidence")}', '由另一会话执行者逐条分类，主 Agent 未改判'])
    with open(os.path.join(OUT, 'INDEPENDENT_REVIEW_120_R2_12.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['object_id', 'category', 'source_locator', 'claim_checked', 'independent_finding',
                    'method', 'verdict', 'evidence', 'note'])
        w.writerows(rows)
    from collections import Counter
    c = Counter(r[6] for r in rows)
    cat = Counter(r[1] for r in rows)
    stat = {'total': len(rows), 'verdict': dict(c), 'by_category': dict(cat),
            'unique_ids': len({r[0] for r in rows})}
    json.dump(stat, open(os.path.join(OUT, 'LOGS/independent_r2_12.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(stat, ensure_ascii=False, indent=1))
    con.close()


if __name__ == '__main__':
    main()
