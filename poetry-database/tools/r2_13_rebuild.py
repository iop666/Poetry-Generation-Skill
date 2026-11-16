#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-13 工作包 B：339 条正文与校记混杂记录逐条重建（只出候选，不写库）。

重建思路（从 text_raw 出发，不从 text_norm 出发）：
1. 括号结构：`（…一作…）` 归 variants；不含校记标记的括号归 annotation。
2. 正文 = 删去全部括号结构后的文字。
3. 无括号「X一作Y」：用「句长格律」判定——删「一作Y」后若句长落入常见格律（4/5/6/7）而原长不落入，则 Y 为异文应删；
   若原长落入而删后不落入，则「一作」属正文，保留。
4. 明显的编者按语（〖1〗、同前。、按…）归 annotation，不进正文。
"""
import os, re, csv, json, sqlite3
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-13')
HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
MARK = re.compile(r'一作|一本作|一云|或作|說作')
SENT_SPLIT = re.compile(r'[，。；！？、\n]')
# 编者按语 / 出处说明的典型开头
EDITORIAL_HEAD = re.compile(r'^(同前|按|〖|【|見|出|載|據|以上|右|此詩|詩見)')


def han(s):
    return ''.join(HAN.findall(s or ''))


def strip_brackets(raw):
    """返回 (body, variants[], annotations[])，处理一层括号；嵌套者标 NESTED。"""
    variants, anns = [], []
    nested = bool(re.search(r'[（(][^（）()]*[（(]', raw))
    body = raw
    for m in re.finditer(r'[（(]([^（）()]{0,300})[）)]', raw):
        inner = m.group(1).strip()
        if not inner:
            continue
        if MARK.search(inner):
            variants.append(inner)
        else:
            anns.append(inner)
    body = re.sub(r'[（(][^（）()]{0,300}[）)]', '', raw)
    return body, variants, anns, nested


def fix_no_bracket(body):
    """处理无括号的「X一作Y」，返回 (new_body, fixed[], unresolved[])。"""
    fixed, unresolved = [], []
    out = body
    for m in re.finditer(r'([^\s，。；！？、（(]{0,6})一作([：:]?)([^\s，。；！？、）)]{1,6})', body):
        pre, colon, post = m.group(1), m.group(2), m.group(3)
        # 所在句
        start = max(body.rfind('，', 0, m.start()), body.rfind('。', 0, m.start()),
                    body.rfind('；', 0, m.start()), body.rfind('\n', 0, m.start())) + 1
        ends = [body.find(c, m.end()) for c in '，。；！？\n']
        ends = [e for e in ends if e != -1]
        end = min(ends) if ends else len(body)
        sent = body[start:end]
        n_full = len(han(sent))
        cand = han(sent).replace('一作', '').replace(han(post), '', 1) if han(post) in han(sent) else None
        n_del = len(cand) if cand is not None else -1
        GRID = {4, 5, 6, 7}
        if n_full in GRID and n_del not in GRID:
            unresolved.append(sent[:40])  # 保留「一作」为正文
        elif n_full not in GRID and n_del in GRID:
            out = out.replace(m.group(0), pre, 1)
            fixed.append(f'{m.group(0)} → {pre}')
        else:
            unresolved.append(sent[:40])
    return out, fixed, unresolved


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    aud = list(csv.DictReader(open(os.path.join(OUT, 'LOGS/works_339_two_dimensions.csv'), encoding='utf-8-sig')))
    ids = [r['work_id'] for r in aud]
    q = ','.join('?' * len(ids))
    w = {r[0]: r for r in cur.execute(
        f'SELECT work_id,title_raw,author_name,text_raw,text_norm,char_count,source_id,record_locator,collection,genre FROM works WHERE work_id IN ({q})', ids)}

    seg_rows, repair_rows, stat = [], [], Counter()
    per_class = {}
    for a in aud:
        wid = a['work_id']
        t = w[wid]
        title, author, raw, norm = t[1], t[2], (t[3] or ''), (t[4] or '')
        # 括号配平检查：不配平者（常见于「（同前。）（〖1〗按…」）整块按语不可靠
        n_open = raw.count('（') + raw.count('(')
        n_close = raw.count('）') + raw.count(')')
        unbalanced = (n_open != n_close) or ('）（' in raw) or ('）(' in raw) or bool(re.search(r'（\s*〖\d+〗\s*按', raw))
        if unbalanced:
            cut = min([i for i in (raw.find('（'), raw.find('(')) if i >= 0] or [len(raw)])
            head_txt = raw[:cut]
            body, variants, anns, nested = head_txt, [], [raw[cut:]], True
        else:
            body, variants, anns, nested = strip_brackets(raw)
        body2, fixed, unresolved = fix_no_bracket(body)
        # 编者按语行剥离
        kept, editorial = [], []
        for line in body2.split('\n'):
            s = line.strip()
            if not s:
                continue
            if EDITORIAL_HEAD.match(s) and len(han(s)) > len(han(s)) * 0 + 8:
                editorial.append(s)
            else:
                kept.append(s)
        body3 = '\n'.join(kept)
        body_final = body3.strip()
        # 状态
        body_unchanged = han(body_final) == han(re.sub(r'[（(][^（）()]{0,300}[）)]', '', raw))
        if not body_final:
            st = 'UNRESOLVED'
        elif unbalanced:
            st = 'NEEDS_REVIEW'
        elif nested:
            st = 'NEEDS_REVIEW'
        elif unresolved and not fixed and not body_unchanged:
            st = 'NEEDS_REVIEW'
        elif unresolved and body_unchanged:
            st = 'TEXT_STRUCTURE_CONFIRMED'
        elif fixed or variants or editorial:
            st = 'SUPPORTED_RECONSTRUCTION'
        else:
            st = 'TEXT_STRUCTURE_CONFIRMED'
        stat[st] += 1
        seg_rows.append([wid, title[:40], author[:20], a['class_r2_12'], a['normalization_impact'],
                         len(han(raw)), len(han(norm)), len(han(body_final)),
                         len(variants), len(anns), len(editorial), len(fixed), len(unresolved),
                         'YES' if nested else 'NO', st, body_final[:60].replace('\n', ' ')])
        repair_rows.append([wid, title[:40], author[:20], raw, norm, body_final,
                            ' | '.join(variants)[:400], ' | '.join(anns + editorial)[:300],
                            'STRIP_BRACKET_NOTE' + ('+FIX_NO_BRACKET' if fixed else '') + ('+STRIP_EDITORIAL' if editorial else ''),
                            '; '.join(fixed)[:200], st, 'NO'])
        per_class.setdefault(a['class_r2_12'], []).append(a)
    with open(os.path.join(OUT, 'WORKS_339_FINAL_SEGMENTATION.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        wtr = csv.writer(f)
        wtr.writerow(['work_id', 'title', 'author', 'class_r2_12', 'normalization_impact', 'raw_han_len',
                      'norm_han_len', 'body_han_len', 'n_variants', 'n_annotations', 'n_editorial',
                      'n_no_bracket_fixed', 'n_unresolved', 'nested_brackets', 'segment_status', 'body_head'])
        wtr.writerows(seg_rows)
    with open(os.path.join(OUT, 'WORKS_TEXT_REPAIR_CANDIDATES.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        wtr = csv.writer(f)
        wtr.writerow(['work_id', 'title', 'author', 'text_raw_original', 'old_text_norm', 'new_text_body',
                      'new_text_variants', 'new_text_annotation', 'normalization_method', 'change_reason',
                      'review_status', 'applied'])
        wtr.writerows(repair_rows)
    # 分项表
    def dump(name, cols, pred):
        rows = [r for r in seg_rows if pred(r)]
        with open(os.path.join(OUT, name), 'w', encoding='utf-8-sig', newline='') as f:
            wtr = csv.writer(f)
            wtr.writerow(cols)
            wtr.writerows(rows)
        return len(rows)
    n184 = dump('WORKS_184_BODY_RECOVERY.csv',
                ['work_id', 'title', 'author', 'class_r2_12', 'normalization_impact', 'raw_han_len', 'norm_han_len',
                 'body_han_len', 'n_variants', 'n_annotations', 'n_editorial', 'n_no_bracket_fixed',
                 'n_unresolved', 'nested_brackets', 'segment_status', 'body_head'],
                lambda r: 'BODY_DELETED' in r[4])
    n116 = dump('WORKS_116_TEXT_EXPANSION_AUDIT.csv',
                ['work_id', 'title', 'author', 'class_r2_12', 'normalization_impact', 'raw_han_len', 'norm_han_len',
                 'body_han_len', 'n_variants', 'n_annotations', 'n_editorial', 'n_no_bracket_fixed',
                 'n_unresolved', 'nested_brackets', 'segment_status', 'body_head'],
                lambda r: 'BODY_EXPANDED' in r[4])
    n42 = dump('WORKS_42_BODY_PROTECTION.csv',
               ['work_id', 'title', 'author', 'class_r2_12', 'normalization_impact', 'raw_han_len', 'norm_han_len',
                'body_han_len', 'n_variants', 'n_annotations', 'n_editorial', 'n_no_bracket_fixed',
                'n_unresolved', 'nested_brackets', 'segment_status', 'body_head'],
               lambda r: r[3] == 'POEM_BODY')
    n141 = dump('WORKS_141_MIXED_SEGMENTATION.csv',
                ['work_id', 'title', 'author', 'class_r2_12', 'normalization_impact', 'raw_han_len', 'norm_han_len',
                 'body_han_len', 'n_variants', 'n_annotations', 'n_editorial', 'n_no_bracket_fixed',
                 'n_unresolved', 'nested_brackets', 'segment_status', 'body_head'],
                lambda r: r[3] == 'MIXED_BODY_AND_NOTE')
    out = {'n_total': len(seg_rows), 'status': dict(stat), 'body_deleted': n184, 'body_expanded': n116,
           'poem_body': n42, 'mixed': n141,
           'with_variants': sum(1 for r in seg_rows if r[8] > 0),
           'with_editorial': sum(1 for r in seg_rows if r[10] > 0),
           'nested': sum(1 for r in seg_rows if r[13] == 'YES'),
           'needs_review': sum(1 for r in seg_rows if r[14] == 'NEEDS_REVIEW')}
    json.dump(out, open(os.path.join(OUT, 'LOGS/rebuild.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    con.close()


if __name__ == '__main__':
    main()
