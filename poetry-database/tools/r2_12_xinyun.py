#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-12 工作包 D：《中华新韵》238 条规则不一致分类、繁简映射、多音字审计。

原则：
- 不改 norm_final() 去凑一致率；差异逐条归因，无法归因的留 UNRESOLVED。
- 繁简映射用 OpenCC 的字形映射（有来源的对照表），但**只作字形对应**，
  不据此推断繁体字的韵部；韵部仍须以简表原字记录或独立来源为准。
"""
import os, re, json, csv, sqlite3, sys
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-12')
sys.path.insert(0, os.path.join(BASE, 'tools'))
from r2_11_xinyun import rule_yun, norm_final, FINAL_TABLE  # 复用已固化的归部规则

import opencc
S2T = opencc.OpenCC('s2t')


def classify(ch, yun, tone, pinyin_list, per_reading):
    """对一条不一致给出归因。"""
    if any(r == yun for r in per_reading if r):
        return 'POLYPHONE_CASE', '某读音按规则可归本部，原实现只取首读'
    finals = [norm_final(p) for p in pinyin_list if p]
    if not finals:
        return 'PINYIN_NORMALIZATION_ERROR', '无可用拼音'
    # 同韵尾不同韵头（介音）导致的近邻误差
    targets = FINAL_TABLE.get(yun, set())
    near = [f for f in finals if f and any(t.endswith(f[-2:]) or f.endswith(t[-2:]) for t in targets)]
    if near:
        return 'RIME_NEAR_MISS', f'韵母 {near[0]} 与本部韵母 {sorted(targets)} 韵尾相同但介音/韵腹不同'
    if norm_final(pinyin_list[0]) is None:
        return 'PINYIN_NORMALIZATION_ERROR', '首读归一失败'
    # 声调
    if per_reading:
        return 'RHYME_MAPPING_ERROR', f'读音 {pinyin_list[0]} 归 {per_reading[0]}，原表归 {yun}'
    return 'UNRESOLVED', ''


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    rows = list(cur.execute('''SELECT id,charx,yun,tone,tone_class,note,source_order,pinyin,rule_yun,rule_match
                               FROM zhonghua_xinyun_characters_r2_11'''))
    from pypinyin import pinyin as py, Style
    mism = [r for r in rows if r[9] == 0]

    # ---------- D2 238 条分类 ----------
    out = []
    cnt = Counter()
    from pypinyin import pinyin as _py, Style as _St
    for (rid, ch, yun, tone, tcls, note, order, pystr, ry, rm) in mism:
        pys = [p for p in (pystr or '').split('/') if p]
        per = [rule_yun(p) for p in pys]
        cls, why = classify(ch, yun, tone, pys, per)
        if cls == 'RHYME_MAPPING_ERROR':
            # 用 heteronym 全读复核：拼音库若含可归本韵之读，属「索引缺读」而非原表错
            het = [x for x in (_py(ch, style=_St.TONE3, heteronym=True)[0] or [])]
            hper = [rule_yun(x) for x in het]
            if yun in hper:
                cls = 'POLYPHONE_MISSING_IN_INDEX'
                why = f'拼音库全读 {"/".join(het)} 中有读音归本部；索引只存了 {pystr}'
            elif any(f and any(t.endswith(f[-2:]) for t in FINAL_TABLE.get(yun, set())) for f in
                     [norm_final(x) for x in het] if f):
                cls = 'RIME_NEAR_MISS'
                why = f'全读 {"/".join(het)} 与本部韵母韵尾相同、介音或韵腹不同'
        cnt[cls] += 1
        out.append([rid, ch, yun, tone, tcls, note, pystr, ry, cls,
                    '|'.join(x or '' for x in per), why])
    with open(os.path.join(OUT, 'ZHONGHUA_XINYUN_238_DIFFERENCES.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', 'character', 'source_rhyme', 'source_tone', 'tone_class', 'note', 'pinyin',
                    'computed_rhyme_first_reading', 'difference_type', 'per_reading_rhyme', 'reason'])
        w.writerows(out)

    # ---------- D3 繁简映射 ----------
    chars = sorted({r[1] for r in rows})
    trad_of = {}
    for ch in chars:
        t = S2T.convert(ch)
        trad_of.setdefault(t, []).append(ch)
    trad_rows = []
    stat_t = Counter()
    for ch in chars:
        t = S2T.convert(ch)
        same = (t == ch)
        stat_t['SAME_FORM' if same else 'HAS_TRADITIONAL'] += 1
        trad_rows.append([ch, t, 'SAME_FORM' if same else 'DIFFERS',
                          'YES' if len(trad_of.get(t, [])) > 1 else 'NO',
                          'OpenCC s2t', 'NO',
                          '仅字形对应；韵部须以原字在简表中的记录为准，不得据字形推定音韵归属'])
    # 一简对多繁：同一简体在 OpenCC 里可能有多繁体？OpenCC s2t 单字为一对一；多对一用反向统计
    multi_s2t = {k: v for k, v in trad_of.items() if len(v) > 1}
    with open(os.path.join(OUT, 'ZHONGHUA_XINYUN_SIMPLIFIED_TRADITIONAL.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['simplified', 'opencc_traditional', 'form_relation', 'multi_simplified_share_one_traditional',
                    'mapping_source', 'phonological_equivalence_assumed', 'note'])
        w.writerows(trad_rows)

    # ---------- D4 多音字 ----------
    poly_rows = []
    for (rid, ch, yun, tone, tcls, note, order, pystr, ry, rm) in rows:
        pys = [p for p in (pystr or '').split('/') if p]
        if len(set(pys)) < 2:
            continue
        readings = []
        for p in pys:
            readings.append(f'{p}→{rule_yun(p) or "?"}')
        poly_rows.append([rid, ch, yun, tone, pystr, len(set(pys)), '|'.join(readings),
                          'YES' if yun in {rule_yun(p) for p in pys} else 'NO',
                          'MULTI_READING_RECORDED'])
    with open(os.path.join(OUT, 'ZHONGHUA_XINYUN_POLYPHONE_AUDIT.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', 'character', 'source_rhyme', 'source_tone', 'pinyin', 'n_readings',
                    'reading_to_rhyme', 'any_reading_matches_source', 'status'])
        w.writerows(poly_rows)

    stat = {'total': len(rows), 'mismatch': len(mism), 'diff_types': dict(cnt),
            'trad_stat': dict(stat_t), 'multi_shared': len(multi_s2t), 'polyphone_rows': len(poly_rows),
            'by_rhyme': dict(Counter(r[2] for r in mism))}
    json.dump(stat, open(os.path.join(OUT, 'LOGS/xinyun_r2_12.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(stat, ensure_ascii=False, indent=1))
    con.close()


if __name__ == '__main__':
    main()
