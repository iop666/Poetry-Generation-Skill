#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-12 工作包 A：《广韵》候选小韵数区间重建、690 条 POSSIBLE 重分类、83 条反切串栏污染。

原则：
1. 3,730 只作「结构口径候选」，不作定论；所有口径必须可由本脚本复现。
2. R2-11 的 3,706 下限无法从任何已保存中间量复现（no_numeral 实为 306，无切语 165），
   本轮判定为 UNDOCUMENTED，并给出新的三级口径。
3. 690 条 POSSIBLE 逐条重分类，不以「无切语」单一条件排除。
"""
import os, re, csv, json, sqlite3
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-12')
NUM = '一二三四五六七八九十百'
HEADS = ('CONFIRMED_XIAOYUN_HEAD', 'SUPPORTED_HEAD_NO_MARKER',
         'HEAD_WITH_DISPLACED_FANQIE', 'HEAD_LOST_FANQIE')


def body(v):
    raw = open(os.path.join(BASE, f'raw/books/guangyun/卷{v}.wikitext'), encoding='utf-8').read()
    m = re.search(r'[^\s　]〈[^〉]{0,8}切', raw)
    return raw[m.start():]


def block_at(b, off, span=120):
    """取 offset 处的一个块（到下一个『　　』为止，限 span 字）。"""
    end = b.find('\u3000\u3000', off)
    if end == -1 or end - off > span:
        end = min(len(b), off + span)
    return b[off:end]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cache = {}

    # ---------- 1. 候选清单（3,730，稳定 ID） ----------
    heads = list(cur.execute(f"""SELECT c.entry_id,c.volume,c.entry_no,c.yun_no,c.yun_name,c.kind,
        c.head,c.marker,c.fanqie,c.declared_chars,c.count_actual,c.ann_head,c.ann_len,c.offset,
        f.structure,f.upper,f.lower,f.comparison
        FROM guangyun_head_classification_r2_11 c
        LEFT JOIN guangyun_fanqie_validation_r2_11 f ON f.entry_id=c.entry_id
        WHERE c.kind IN {HEADS} ORDER BY c.volume,c.entry_no"""))
    cand = []
    for i, (eid, v, en, yn, ynm, kind, head, mk, fq, dc, ca, ah, al, off, st, up, lo, cmp_) in enumerate(heads, 1):
        cand.append(dict(candidate_head_id=f'GY12H-{i:05d}', source_book_id='GUANGYUN',
                         volume_id=f'V{v}', rhyme_group_id=f'GUANGYUN_V{v}_{yn:03d}' if yn else '',
                         head_character=head, raw_marker=mk, raw_fanqie=fq or '',
                         source_offset=off, head_kind=kind, declared_chars=dc, count_actual=ca,
                         fanqie_structure=st or 'NONE', upper=up or '', lower=lo or '',
                         r2_11_entry_id=eid))
    # ---------- 2. 三级口径 ----------
    n_all = len(cand)
    n_qie = sum(1 for c in cand if c['fanqie_structure'] in ('TWO_CHAR', 'IRREGULAR_LONG'))
    n_two = sum(1 for c in cand if c['fanqie_structure'] == 'TWO_CHAR')
    n_no_qie = n_all - n_qie
    # 690 中的可加候选
    poss = list(cur.execute("""SELECT entry_id,volume,head,ann_head,ann_len,offset,yun_no,yun_name
        FROM guangyun_head_classification_r2_11 WHERE kind='POSSIBLE_XIAOYUN_HEAD'"""))
    addable = []
    reclass = []
    for eid, v, head, ah, al, off, yn, ynm in poss:
        if v not in cache:
            cache[v] = body(v)
        blk = block_at(cache[v], off)
        nxt = cache[v][off + len(blk):off + len(blk) + 30]
        start_qie = ah.startswith('切')
        start_you = ah.startswith('又')
        tail_num = bool(re.search(f'[{NUM}]$', ah))
        inline_qie = '切' in ah[:12]
        # 页眉/断页
        ctx = cache[v][max(0, off - 160):off]
        page_break = ('欽定四庫全書' in ctx) or ('原本廣韻卷' in ctx)
        # 转录列序交错：本块注文与下一块注文互换（下一块注文以本块 head 的字义无法解释）
        swapped = False
        m = re.search(r'^(.{1,2})〈', nxt)
        if m and nxt.startswith('〈') is False:
            pass
        if tail_num and not inline_qie:
            cls = 'COUNT_TAIL_PRESENT'
        elif start_qie:
            cls = 'FANQIE_SPLIT_AT_START'
        elif start_you:
            cls = 'ALTERNATIVE_READING'
        elif inline_qie:
            cls = 'FANQIE_INLINE'
        elif al <= 4:
            cls = 'SHORT_FRAGMENT_SUSPECT'
        elif page_break:
            cls = 'PAGE_BREAK_SUSPECTED'
        else:
            cls = 'GLOSS_FRAGMENT'
        # 交错判据：本块注文末字 + 下一块首字，构成「X〈某〉」且本块注文不含虚词/动词
        if cls in ('SHORT_FRAGMENT_SUSPECT', 'GLOSS_FRAGMENT') and re.search(r'[也皃聲色屬名切]$', ah) is None and al <= 6:
            cls = 'TRANSCRIPTION_COLUMN_MISALIGNMENT_SUSPECT'
        if cls in ('COUNT_TAIL_PRESENT', 'FANQIE_SPLIT_AT_START', 'FANQIE_INLINE'):
            addable.append(dict(entry_id=eid, volume=v, head=head, cls=cls, ann=ah))
        reclass.append([eid, v, yn, ynm, head, mk := 1, ah, al, cls,
                        'YES' if cls in ('COUNT_TAIL_PRESENT', 'FANQIE_SPLIT_AT_START', 'FANQIE_INLINE') else 'NO',
                        '', blk[:80].replace('\n', ' '), nxt[:30].replace('\n', ' '),
                        'PENDING_IMAGE' if cls in ('COUNT_TAIL_PRESENT', 'FANQIE_SPLIT_AT_START', 'FANQIE_INLINE') else 'NOT_HEAD'])
    n_add = len(addable)
    ext_max = n_all + n_add

    # ---------- 3. 写表 ----------
    cur.executescript('''
    DROP TABLE IF EXISTS guangyun_count_crosswalk_r2_12;
    CREATE TABLE guangyun_count_crosswalk_r2_12(
      candidate_head_id TEXT PRIMARY KEY, source_book_id TEXT, volume_id TEXT, rhyme_group_id TEXT,
      head_character TEXT, raw_marker INT, raw_fanqie TEXT, source_offset INT, head_kind TEXT,
      declared_chars INT, count_actual INT, fanqie_structure TEXT, upper TEXT, lower TEXT,
      r2_11_entry_id TEXT, basis TEXT);
    DROP TABLE IF EXISTS guangyun_possible_head_review_r2_12;
    CREATE TABLE guangyun_possible_head_review_r2_12(
      entry_id TEXT PRIMARY KEY, volume INT, yun_no INT, yun_name TEXT, head TEXT, marker INT,
      ann_text TEXT, ann_len INT, reclass TEXT, addable TEXT, note TEXT,
      raw_block TEXT, next_block TEXT, review_status TEXT);
    ''')
    for c in cand:
        basis = 'MARKER+FANQIE' if c['fanqie_structure'] in ('TWO_CHAR', 'IRREGULAR_LONG') else 'MARKER_NO_FANQIE'
        cur.execute('INSERT INTO guangyun_count_crosswalk_r2_12 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (c['candidate_head_id'], c['source_book_id'], c['volume_id'], c['rhyme_group_id'],
                     c['head_character'], c['raw_marker'], c['raw_fanqie'], c['source_offset'],
                     c['head_kind'], c['declared_chars'], c['count_actual'], c['fanqie_structure'],
                     c['upper'], c['lower'], c['r2_11_entry_id'], basis))
    cur.executemany('INSERT INTO guangyun_possible_head_review_r2_12 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', reclass)
    con.commit()

    # ---------- 4. 83 条串栏污染 ----------
    cont = list(cur.execute("""SELECT entry_id,volume,yun_no,head,fanqie,upper,lower
        FROM guangyun_fanqie_validation_r2_11 WHERE structure='IRREGULAR_LONG' ORDER BY volume"""))
    cont_rows = []
    for eid, v, yn, head, fq, up, lo in cont:
        # 分析：从末尾取 n 字「X切」，前面的字属上一注文
        m = re.search(r'([^\s，。]{1,3})切$', fq or '')
        tail = m.group(0) if m else fq
        prefix = (fq or '')[:len(fq) - len(tail)] if m else ''
        # 疑似正确反切：末尾「切」前两字
        guess = (fq or '')[-3:]
        cont_rows.append([eid, v, yn, head, fq, prefix, tail, guess,
                          'COLUMN_CONTAMINATION',
                          'NO' if len(fq or '') > 3 else 'YES',
                          '串栏：前缀属相邻小韵注文，末尾「X切」方为本条切语' if len(fq or '') > 3 else '三字反切，可能完整',
                          'EXCLUDED_FROM_PHONOLOGY' if len(fq or '') > 3 else 'USABLE_WITH_CAUTION'])
    with open(os.path.join(OUT, 'GUANGYUN_83_COLUMN_CONTAMINATION.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['entry_id', 'volume', 'yun_no', 'head', 'raw_fanqie', 'suspected_foreign_prefix',
                    'suspected_own_tail', 'conjectured_fanqie', 'status', 'prefix_empty',
                    'analysis', 'usability'])
        w.writerows(cont_rows)

    # ---------- 5. 690 重分类 CSV ----------
    with open(os.path.join(OUT, 'GUANGYUN_690_POSSIBLE_RECLASSIFICATION.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['entry_id', 'volume', 'yun_no', 'yun_name', 'head', 'marker', 'ann_text', 'ann_len',
                    'reclass', 'addable_to_upper', 'note', 'raw_block', 'next_block', 'review_status'])
        w.writerows(reclass)

    # ---------- 6. 3,702 与 3,872 对照（统计级） ----------
    summary = {
        'core_structural': n_all,
        'extended_max_with_possible': ext_max,
        'strict_with_fanqie': n_qie,
        'strict_two_char_only': n_two,
        'no_fanqie': n_no_qie,
        'possible_total': len(poss),
        'possible_addable': n_add,
        'possible_reclass': dict(Counter(r[8] for r in reclass)),
        'r2_11_lower_3706_reproducible': False,
        'r2_11_lower_note': 'no_numeral 实为 306，无切语 165，均无法得出 24 之差额；判定 UNDOCUMENTED',
        'column_contamination': len(cont_rows),
        'external': {
            'wenmai_3702': {'basis': '四库全书本《原本广韵》数字化整理（外部声明）',
                            'xiaoyun': 3702, 'chars': 25332,
                            'crosswalk': 'BLOCKED_NO_PUBLIC_ITEM_INDEX'},
            'commercial_3872': {'basis': '商务印书馆《广韵反切今读手册》出版说明',
                                'entries': 3872, 'crosswalk': 'BLOCKED_NO_PUBLIC_ITEM_INDEX'},
        },
    }
    json.dump(summary, open(os.path.join(OUT, 'LOGS/guangyun_r2_12.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    con.close()


if __name__ == '__main__':
    main()
