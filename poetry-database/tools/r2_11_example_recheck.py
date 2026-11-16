#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-11 F2: 例词-作品关联独立复核（本地 sqlite，无联网）
抽样 -> 分段/文本比对 -> 规则判定 -> CSV + 明细 JSON
"""
import csv, json, os, re, sqlite3, sys
from difflib import SequenceMatcher
import opencc

BASE = '<PROJECT_ROOT>/poetry-database'
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-15/R2-11')
LOGS = os.path.join(OUT, 'LOGS')
T2S = opencc.OpenCC('t2s')
CJK = re.compile(r'[\u3400-\u9fff\uf900-\ufaff]')

REVIEWED_R2_10 = {
    'EX-01': 'EX-0122', 'EX-02': 'EX-0015', 'EX-03': 'EX-0157', 'EX-04': 'EX-0274',
    'EX-05': 'EX-0271', 'EX-06': 'EX-0255', 'EX-07': 'EX-0242', 'EX-08': 'EX-0294',
    'EX-09': 'EX-0234', 'EX-10': 'EX-0038', 'EX-11': 'EX-0115', 'EX-12': 'EX-0301',
    'EX-13': 'EX-0096', 'EX-14': 'EX-0088', 'EX-15': 'EX-0220', 'EX-16': 'EX-0044',
    'EX-17': 'EX-0307', 'EX-18': 'EX-0011', 'EX-19': 'EX-0076', 'EX-20': 'EX-0186',
}


def norm(s):
    if not s:
        return ''
    return T2S.convert(''.join(CJK.findall(s)))


def lev(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def ratio(a, b):
    return 1 - lev(a, b) / max(len(a), len(b), 1)


def lcsubstr(a, b):
    blk = SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b))
    return blk.size, a[blk.a:blk.a + blk.size]


def diffs(a, b, limit=8):
    sm = SequenceMatcher(None, a, b, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        out.append('%s[%s>%s]' % (tag, a[i1:i2] or '∅', b[j1:j2] or '∅'))
    return ';'.join(out[:limit]) + ('…' if len(out) > limit else ''), len(out)


def segments(raw):
    """例词正文常混入「例二/例三/格二」及「——作者（小注）」等编例文字，先按原文切段再规范化"""
    if not raw:
        return []
    parts = re.split(r'(?=例[二三四五六]|格[二三四五六])', raw)
    out = []
    for p in parts:
        p = p.split('——')[0]
        p = re.sub(r'^(例|格)[二三四五六]', '', p)
        n = norm(p)
        if len(n) >= 8:
            out.append(n)
    return sorted(set(out), key=len, reverse=True) or [norm(raw)]


def sample_ids(cur):
    rows = cur.execute("SELECT example_id,new_match_kind FROM example_work_links_r2_09 ORDER BY example_id").fetchall()
    excluded = set(REVIEWED_R2_10.values())
    by = {}
    for eid, k in rows:
        if eid in excluded:
            continue
        by.setdefault(k, []).append(eid)
    plan = {'AUTHOR_CONFLICT': 99, 'TITLE_ONLY': 99, 'POSSIBLE_MATCH': 99,
            'VERIFIED_VARIANT': 40, 'NO_MATCH': 20, 'VERIFIED_EXACT': 5}
    picked, meta = [], {}
    for k, n in plan.items():
        lst = by.get(k, [])
        if not lst:
            continue
        n = min(n, len(lst))
        step = len(lst) / n
        sel = [lst[int(i * step)] for i in range(n)]
        meta[k] = {'pool': len(lst), 'taken': len(sel), 'step': round(step, 3)}
        picked += sel
    return picked, meta, by


def windows(e, wlen=14):
    if len(e) <= wlen:
        return [e]
    pos = {0, (len(e) - wlen) // 2, len(e) - wlen}
    return [e[p:p + wlen] for p in sorted(pos)]


def search_corpus(e, corpus, exclude, topn=3):
    hits, seen = [], set()
    for win in windows(e):
        if len(win) < 6:
            continue
        for wid, ti, an, tx in corpus:
            if wid in seen or wid == exclude or win not in tx:
                continue
            seen.add(wid)
            contained = e in tx
            sc = 1.0 if contained else ratio(e, tx)
            hits.append((sc, wid, ti, an, len(tx), contained))
    hits.sort(key=lambda x: (-x[0], x[4]))
    return hits[:topn]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    picked, meta, by = sample_ids(cur)

    ex = {}
    for r in cur.execute("SELECT example_id,form_id,cipai_name,author,author_note,text,n_chars,pdf_page "
                         "FROM cipai_form_examples_r2_08"):
        ex[r[0]] = dict(form_id=r[1], cipai=r[2], author=r[3], note=r[4], text=r[5], n_chars=r[6], page=r[7])

    links = {}
    for r in cur.execute("""SELECT example_id,work_id,work_author,work_title,collection,old_match_kind,
                            new_match_kind,same_author,containment,ex_len,work_len,score
                            FROM example_work_links_r2_09"""):
        links[r[0]] = dict(work_id=r[1], work_author=r[2], work_title=r[3], collection=r[4],
                           old_kind=r[5], kind=r[6], same_author=r[7], containment=r[8],
                           ex_len=r[9], work_len=r[10], score=r[11])

    works = {}
    for wid, title, an, ac, coll, cipai, ts, tn, raw in cur.execute(
            "SELECT work_id,title_raw,author_name,author_canonical,collection,cipai,text_s,text_norm,text_raw FROM works"):
        works[wid] = dict(title=title or '', author=an or '', author_canon=ac or '', coll=coll or '',
                          cipai=cipai or '', text=ts or tn or raw or '', text_raw=raw or '')

    print('loading corpus...', file=sys.stderr)
    corpus = [(wid, w['title'], w['author'], norm(w['text'])) for wid, w in works.items() if w['text']]
    by_author, by_cipai = {}, {}
    for wid, w in works.items():
        if not w['text']:
            continue
        by_author.setdefault(norm(w['author']), []).append(wid)
        head = re.split(r'[・·\s（(]', w['title'])[0]
        if head:
            by_cipai.setdefault(head, []).append(wid)

    rows = []
    for eid in picked:
        L, E = links[eid], ex[eid]
        e = norm(E['text'])
        claim = L['kind']
        rec = dict(example_id=eid, form_id=E['form_id'], cipai=E['cipai'], author=E['author'],
                   note=E['note'], claim=claim, ex_text=E['text'], ex_norm=e,
                   work_id=L['work_id'] or '', work_title=L['work_title'] or '',
                   work_author=L['work_author'] or '', score=L['score'], old_kind=L['old_kind'],
                   collection=L['collection'] or '')
        W = works.get(L['work_id'])
        if W and norm(W['text']):
            w = norm(W['text'])
            rec['work_text'] = W['text']
            rec['work_text_raw'] = W['text_raw']
            rec['work_cipai'] = W['cipai']
            rec['work_author_canon'] = W['author_canon']
            rec['work_len_norm'] = len(w)
            segs = segments(E['text'])
            best = max(segs, key=lambda s: ratio(s, w))
            r = ratio(best, w)
            d = lev(best, w)
            lcs, lcs_s = lcsubstr(best, w)
            rec.update(seg_used=best, seg_len=len(best), lev=d, ratio=round(r, 4), lcs=lcs,
                       lcs_s=lcs_s, e_in_w=(best in w), w_in_e=(w in best),
                       n_seg=len(segs), whole_ratio=round(ratio(e, w), 4),
                       same_author_calc=int(norm(W['author']) == norm(E['author'])
                                           or norm(W['author_canon']) == norm(E['author'])))
            rec['dif'], rec['n_diff'] = diffs(best, w)
        else:
            rec.update(work_text='', work_text_raw='', work_cipai='', work_author_canon='',
                       work_len_norm=0, seg_used='', seg_len=0, lev=None, ratio=None, lcs=0,
                       lcs_s='', e_in_w=False, w_in_e=False, n_seg=0, whole_ratio=None,
                       same_author_calc=0, dif='', n_diff=0)

        found = []
        if claim in ('NO_MATCH', 'TITLE_ONLY') or rec['ratio'] is not None and rec['ratio'] < 0.60:
            if e:
                # A. 全库 instr 窗口检索
                seen = {}
                for seg in segments(E['text'])[:3]:
                    for hit in search_corpus(seg, corpus, L['work_id'], 1):
                        seen.setdefault(hit[1], dict(score=hit[0], wid=hit[1], title=hit[2],
                                                     author=hit[3], ln=hit[4], cont=hit[5], via='INSTR'))
                # B. 作者/词牌过滤后逐条比对
                cand = set(by_author.get(norm(E['author']), []))
                head = re.split(r'[・·\s]', E['cipai'])[0]
                cand |= set(by_cipai.get(head, []))
                for wid in cand:
                    if wid == L['work_id']:
                        continue
                    tx = norm(works[wid]['text'])
                    if not tx:
                        continue
                    sc = 1.0 if e in tx else ratio(e, tx)
                    if sc < 0.45:
                        continue
                    if wid in seen and seen[wid]['score'] >= sc:
                        if seen[wid]['via'] == 'INSTR':
                            seen[wid]['via'] = 'INSTR+AUTHOR_CIPAI'
                        continue
                    seen[wid] = dict(score=sc, wid=wid, title=works[wid]['title'],
                                     author=works[wid]['author'], ln=len(tx), cont=(e in tx),
                                     via='AUTHOR_CIPAI')
                found = sorted(seen.values(), key=lambda x: (-x['score'], x['ln']))[:3]
        rec['found'] = found
        rec['n_candidate_pool'] = len(by_author.get(norm(E['author']), []))
        rows.append(rec)
        print('done', eid, claim, rec['ratio'], file=sys.stderr)

    with open(os.path.join(LOGS, 'f2_detail.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(sample_meta=meta, pools={k: len(v) for k, v in by.items()},
                       reviewed_r2_10=REVIEWED_R2_10, n=len(rows), rows=rows), f,
                  ensure_ascii=False, indent=1)
    print('sampled %d' % len(rows))


if __name__ == '__main__':
    main()
