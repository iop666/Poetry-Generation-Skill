#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-11 工作包 A（第二阶段）：把小韵重认定结果写入 _r2_11 表并导出审计 CSV。
依赖 tools/r2_11_guangyun.py 的解析器。不修改任何历史表。
"""
import os, re, csv, json, sqlite3
from collections import Counter, defaultdict

import r2_11_guangyun as G

BASE = G.BASE
OUT = G.OUT
DB = G.DB
XIAO = ('CONFIRMED_XIAOYUN_HEAD', 'SUPPORTED_HEAD_NO_MARKER', 'HEAD_LOST_FANQIE', 'HEAD_WITH_DISPLACED_FANQIE')

DDL = [
    """DROP TABLE IF EXISTS guangyun_head_classification_r2_11""",
    """CREATE TABLE guangyun_head_classification_r2_11(
      entry_id TEXT PRIMARY KEY, volume INT, entry_no INT, yun_no INT, yun_name TEXT,
      xiaoyun_id TEXT, kind TEXT, head TEXT, marker INT, fanqie TEXT, declared_chars INT,
      count_actual INT, ann_head TEXT, ann_len INT, offset INT, review_status TEXT)""",
    """DROP TABLE IF EXISTS guangyun_xiaoyun_recount_r2_11""",
    """CREATE TABLE guangyun_xiaoyun_recount_r2_11(
      volume INT, tone TEXT, yun_no INT, yun_name TEXT, entries INT, xiaoyun_heads INT,
      head_lost INT, fragment_marker INT, alt_reading INT, sum_declared_chars INT,
      r2_10_heads INT, delta INT, interval_status TEXT, note TEXT)""",
    """DROP TABLE IF EXISTS guangyun_fanqie_validation_r2_11""",
    """CREATE TABLE guangyun_fanqie_validation_r2_11(
      entry_id TEXT PRIMARY KEY, volume INT, yun_no INT, head TEXT, fanqie TEXT,
      upper TEXT, lower TEXT, structure TEXT, r2_10_fanqie TEXT, r2_10_upper TEXT,
      r2_10_lower TEXT, comparison TEXT, note TEXT)""",
    """DROP TABLE IF EXISTS guangyun_rhyme_validation_r2_11""",
    """CREATE TABLE guangyun_rhyme_validation_r2_11(
      entry_id TEXT PRIMARY KEY, volume INT, entry_no INT, yun_no INT, yun_name TEXT,
      status TEXT, evidence TEXT)""",
]


def main():
    con = sqlite3.connect(DB)
    exp = G.expected_yun(con)
    allrows, matched, shas = [], [], {}
    for v in range(1, 6):
        r, m, sha = G.parse_volume(v, exp[v])
        allrows += r
        matched += m
        shas[v] = sha

    # ---- 小韵编号 ----
    seq = [r for r in allrows if r['kind'] != 'YUN_TAG']
    for r in allrows:
        r.setdefault('xiaoyun_id', '')
        r.setdefault('xiaoyun_seq', None)
    xid = 0
    for r in seq:
        if r['kind'] in XIAO:
            xid += 1
            r['xiaoyun_id'] = f'XY-{xid:05d}'
            r['xiaoyun_seq'] = xid

    # ---- 字数自校 ----
    for n, r in enumerate(seq):
        if r['kind'] not in XIAO:
            continue
        cnt, j = 1, n + 1
        while j < len(seq) and seq[j]['kind'] not in XIAO:
            cnt += 1
            j += 1
        r['count_actual'] = cnt

    # ---- 区间锚定：判断条目是否落在「跳过韵目」的空档内 ----
    anchors = defaultdict(list)
    for m in matched:
        anchors[m['volume']].append((m['offset'], m['yun_no'], m['via']))
    for v in anchors:
        anchors[v].sort()
    for r in allrows:
        r['yun_anchor'] = 'YUN_HEADER'
    for r in seq:
        a = anchors.get(r['volume'], [])
        nxt = None
        for off, no, via in a:
            if off >= r['offset']:
                nxt = (off, no, via)
                break
        if r['yun_no'] is None:
            r['yun_anchor'] = 'NO_ANCHOR'
        elif nxt and nxt[1] == r['yun_no'] + 1:
            r['yun_anchor'] = 'DIRECT'
        elif nxt and nxt[1] > r['yun_no'] + 1:
            r['yun_anchor'] = f'SPAN_SKIPS_{nxt[1] - r["yun_no"] - 1}'
        else:
            r['yun_anchor'] = 'DIRECT'

    # ---- 逐韵统计 ----
    per = defaultdict(lambda: dict(n_entries=0, n_head=0, n_head_lost=0, n_fragment=0,
                                    sum_num=0, n_alt=0, r2_10=None, delta=None,
                                    interval='MATCHED', note=''))
    for r in seq:
        p = per[(r['volume'], r['yun_no'])]
        p['n_entries'] += 1
        if r['kind'] in XIAO:
            p['n_head'] += 1
            p['sum_num'] += r['num'] or 0
            if r['kind'] == 'HEAD_LOST_FANQIE':
                p['n_head_lost'] += 1
        if r['kind'] == 'POSSIBLE_XIAOYUN_HEAD':
            p['n_fragment'] += 1
        if r['kind'] == 'ALTERNATIVE_READING':
            p['n_alt'] += 1
    for v, no, n, name in con.execute('SELECT volume, yun_no, n_xiaoyun, yun_name FROM guangyun_yunmu_repair_r2_10'):
        p = per.get((v, no))
        if p is not None:
            p['r2_10'] = n
            p['delta'] = p['n_head'] - n
    matched_pairs = {(m['volume'], m['yun_no']) for m in matched}
    for v in range(1, 6):
        for e in exp[v]:
            if (v, e['yun_no']) not in matched_pairs:
                per[(v, e['yun_no'])]['interval'] = 'ABSORBED_UPSTREAM'
                per[(v, e['yun_no'])]['note'] = '韵目行缺失，条目被上一韵吸收'

    # ---- 写库 ----
    cur = con.cursor()
    for ddl in DDL:
        cur.execute(ddl)
    con.commit()
    rows_by_id = {}
    for r in allrows:
        eid = f"GY11-{r['volume']}-{r['entry_no']:05d}"
        rows_by_id[eid] = r
        r['entry_id'] = eid
    cur.executemany('INSERT INTO guangyun_head_classification_r2_11 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', [
        (r['entry_id'], r['volume'], r['entry_no'], r['yun_no'], r['yun_name'], r['xiaoyun_id'],
         r['kind'], r['head'], r['marker'], r['fanqie'], r['num'], r.get('count_actual'),
         r['ann'][:40], len(r['ann']), r['offset'],
         'ASSIGNED' if r['yun_no'] is not None else 'UNRESOLVED_YUN')
        for r in allrows])
    for v in range(1, 6):
        for e in exp[v]:
            p = per[(v, e['yun_no'])]
            cur.execute('INSERT INTO guangyun_xiaoyun_recount_r2_11 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (v, e['tone'], e['yun_no'], e['name'], p['n_entries'], p['n_head'],
                         p['n_head_lost'], p['n_fragment'], p['n_alt'], p['sum_num'],
                         p['r2_10'], p['delta'], p['interval'], p['note']))
    # 反切终审
    r210 = {}
    for vol, head, fq, up, lo, kind in con.execute(
            'SELECT volume, head, fanqie, fanqie_upper, fanqie_lower, fanqie_kind FROM guangyun_fanqie_r2_10'):
        r210.setdefault((vol, head), []).append((fq, up, lo, kind))
    fq_rows = []
    for eid, r in rows_by_id.items():
        if r['kind'] not in XIAO:
            continue
        fq = r['fanqie']
        up = lo = ''
        m = re.match(r'^(.{1,2})(.{1,2})切$', fq) if fq else None
        if m and len(fq) == 3:
            up, lo = m.group(1), m.group(2)
            struct = 'TWO_CHAR'
        elif m:
            up, lo = m.group(1), m.group(2)
            struct = 'IRREGULAR_LONG'
        else:
            struct = 'NONE' if not fq else 'IRREGULAR'
        cand = r210.get((r['volume'], r['head']), [])
        cmp_, note = 'NOT_IN_R2_10', ''
        r10fq = r10up = r10lo = ''
        if cand:
            hit = [c for c in cand if c[0] == fq]
            c = hit[0] if hit else cand[0]
            r10fq, r10up, r10lo = c[0] or '', c[1] or '', c[2] or ''
            if hit and c[1] == up and c[2] == lo:
                cmp_ = 'MATCH'
            elif hit:
                cmp_ = 'FANQIE_MATCH_SPLIT_DIFF'
            else:
                cmp_ = 'FANQIE_ABSENT_IN_R2_10'
        elif not fq:
            cmp_ = 'NO_FANQIE'
        fq_rows.append((eid, r['volume'], r['yun_no'], r['head'], fq, up, lo, struct,
                        r10fq, r10up, r10lo, cmp_, note))
    cur.executemany('INSERT INTO guangyun_fanqie_validation_r2_11 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', fq_rows)
    # 韵目归属
    rv = []
    for eid, r in rows_by_id.items():
        if r['yun_no'] is None:
            st = 'UNRESOLVED'
        elif r['yun_anchor'] in ('DIRECT', 'YUN_HEADER'):
            st = 'VERIFIED_POSITION'
        else:
            st = 'SUPPORTED_POSITION'
        rv.append((eid, r['volume'], r['entry_no'], r['yun_no'], r['yun_name'], st, r['yun_anchor']))
    cur.executemany('INSERT INTO guangyun_rhyme_validation_r2_11 VALUES (?,?,?,?,?,?,?)', rv)
    con.commit()

    # ---- CSV ----
    with open(os.path.join(OUT, 'GUANGYUN_206_RHYME_COUNTS.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['volume', 'tone', 'yun_no', 'yun_name', 'entries', 'xiaoyun_heads', 'head_lost',
                    'fragment_marker', 'alt_reading', 'sum_declared_chars', 'r2_10_n_xiaoyun', 'delta',
                    'interval_status', 'note'])
        for v in range(1, 6):
            for e in exp[v]:
                p = per[(v, e['yun_no'])]
                w.writerow([v, e['tone'], e['yun_no'], e['name'], p['n_entries'], p['n_head'],
                            p['n_head_lost'], p['n_fragment'], p['n_alt'], p['sum_num'],
                            p['r2_10'] if p['r2_10'] is not None else '',
                            p['delta'] if p['delta'] is not None else '',
                            p['interval'], p['note']])
    with open(os.path.join(OUT, 'GUANGYUN_XIAOYUN_HEAD_AUDIT.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['entry_id', 'xiaoyun_id', 'volume', 'yun_no', 'yun_name', 'kind', 'head',
                    'fanqie', 'declared_chars', 'count_actual', 'marker', 'ann_head'])
        for eid, r in rows_by_id.items():
            if r['kind'] not in XIAO:
                continue
            w.writerow([eid, r['xiaoyun_id'], r['volume'], r['yun_no'], r['yun_name'], r['kind'],
                        r['head'], r['fanqie'], r['num'], r.get('count_actual'), r['marker'], r['ann'][:30]])
    with open(os.path.join(OUT, 'GUANGYUN_FANQIE_FINAL_AUDIT.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['entry_id', 'volume', 'yun_no', 'head', 'fanqie', 'upper', 'lower', 'structure',
                    'r2_10_fanqie', 'r2_10_upper', 'r2_10_lower', 'comparison', 'note'])
        w.writerows(fq_rows)
    not_direct = 0
    with open(os.path.join(OUT, 'GUANGYUN_447_UNRESOLVED.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['entry_id', 'volume', 'entry_no', 'head', 'yun_no_new', 'yun_name_new', 'status', 'evidence'])
        for eid, r in rows_by_id.items():
            st = 'UNRESOLVED' if r['yun_no'] is None else ('VERIFIED_POSITION' if r['yun_anchor'] in ('DIRECT', 'YUN_HEADER') else 'SUPPORTED_POSITION')
            if st != 'VERIFIED_POSITION':
                w.writerow([eid, r['volume'], r['entry_no'], r['head'], r['yun_no'], r['yun_name'], st, r['yun_anchor']])
                not_direct += 1

    summary = {
        'entries_total': len(allrows),
        'kinds': dict(Counter(r['kind'] for r in allrows)),
        'xiaoyun_total': xid,
        'yun_matched': len({(m['volume'], m['yun_no']) for m in matched}),
        'yun_absorbed': sum(1 for v in range(1, 6) for e in exp[v] if (v, e['yun_no']) not in matched_pairs),
        'numeral_check': {
            'agree': sum(1 for r in seq if r['kind'] in XIAO and r['num'] is not None and r.get('count_actual') == r['num']),
            'disagree': sum(1 for r in seq if r['kind'] in XIAO and r['num'] is not None and r.get('count_actual') != r['num']),
            'no_numeral': sum(1 for r in seq if r['kind'] in XIAO and r['num'] is None),
        },
        'fanqie_compare': dict(Counter(x[11] for x in fq_rows)),
        'fanqie_structure': dict(Counter(x[7] for x in fq_rows)),
        'rhyme_not_direct': not_direct,
        'vol_sha256': shas,
        'anchor_via': dict(Counter(m['via'] for m in matched)),
        'declared_sum': sum(p['sum_num'] for p in per.values()),
        'per_volume_xiaoyun': dict(Counter(r['volume'] for r in seq if r['kind'] in XIAO)),
    }
    json.dump(summary, open(os.path.join(OUT, 'LOGS/guangyun_summary.json'), 'w'), ensure_ascii=False, indent=1)
    con.close()
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
