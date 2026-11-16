#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-13 工作包 E：1000 条分层质量抽检（固定种子；唯一 work_id；一次扫描取池）。"""
import os, re, csv, json, sqlite3, random
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-13')
HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
TRAD = re.compile(r'[國學詩書萬與為無來時說東門風雲龍鳳歸還這]')
SEED = 20261116
BODY_FLAGS = {'BODY_PARTIAL', 'TITLE_REPEAT', 'ANNOTATION_MIXED', 'BODY_DELETED', 'BODY_EXPANDED',
              'DUPLICATE_SUSPECTED', 'AUTHOR_IN_BODY'}
COLS = ('work_id,title_raw,author_name,author_canonical,dynasty,era,collection,genre,'
        'text_raw,text_norm,char_count,record_locator,variant_group,crosscheck_status')
QUOTA = {'先秦两汉韵文': 100, '六朝作品': 100, '唐诗': 150, '宋诗': 150, '宋词': 150,
         '元曲': 150, '明清诗词': 100, '长篇作品': 40, '带注释或校记作品': 30, '复杂多版本作品': 30}


def han(s):
    return ''.join(HAN.findall(s or ''))


def match(v, name):
    (wid, title, author, canon, dyn, era, coll, genre, raw, norm, cc, loc, vg, ccs) = v
    dyn, era, coll, genre, raw, norm = dyn or '', era or '', coll or '', genre or '', raw or '', norm or ''
    if name == '先秦两汉韵文':
        return coll in ('shijing', 'chuci', 'wenxuan') or '先秦' in era or '汉' in era or '漢' in era
    if name == '六朝作品':
        return any(k in era for k in ('魏', '晋', '晉', '南北朝', '陈', '陳', '齐', '齊', '梁', '北朝')) or '南朝' in dyn
    if name == '唐诗':
        return '唐' in dyn
    if name == '宋诗':
        return '宋' in dyn and ('词' not in genre and '詞' not in genre)
    if name == '宋词':
        return '宋' in dyn and ('词' in genre or '詞' in genre or '词' in coll)
    if name == '元曲':
        return '元' in dyn or '曲' in genre
    if name == '明清诗词':
        return '明' in dyn or '清' in dyn
    if name == '长篇作品':
        return (cc or 0) >= 500
    if name == '带注释或校记作品':
        return ('一作' in raw) or ('注' in raw)
    if name == '复杂多版本作品':
        return bool(vg) or bool(ccs)
    return False


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    random.seed(SEED)
    rows_all = list(cur.execute(f'SELECT {COLS} FROM works WHERE rowid % 13 = 0'))
    random.shuffle(rows_all)
    print('pool', len(rows_all))
    picked, used, layer_of = [], set(), defaultdict(list)
    for name in QUOTA:
        take = 0
        for v in rows_all:
            if take >= QUOTA[name]:
                break
            if v[0] in used:
                continue
            if match(v, name):
                used.add(v[0]); picked.append(v); layer_of[v[0]].append(name); take += 1
    gaps = {n: QUOTA[n] - sum(1 for v in picked if n in layer_of[v[0]]) for n in QUOTA}
    # 缺口层：从全库补齐（不走 1/13 池，避免小类被池稀释）
    for name, gap in list(gaps.items()):
        if gap <= 0:
            continue
        pool = list(cur.execute(f'SELECT {COLS} FROM works'))
        random.shuffle(pool)
        taken = 0
        for v in pool:
            if taken >= gap:
                break
            if v[0] in used:
                continue
            if match(v, name):
                used.add(v[0]); picked.append(v); layer_of[v[0]].append(name); taken += 1
        gaps[name] = gap - taken
    print('picked', len(picked), 'gaps', {k: v for k, v in gaps.items() if v})

    keys = {}
    for v in picked:
        k = han(v[9])[:20]
        if k:
            keys[k] = 0
    for (t,) in cur.execute('SELECT text_norm FROM works'):
        k = han(t)[:20]
        if k in keys:
            keys[k] += 1

    out, stat = [], Counter()
    for v in picked:
        (wid, title, author, canon, dyn, era, coll, genre, raw, norm, cc, loc, vg, ccs) = v
        rh, nh = han(raw), han(norm)
        flags = []
        if not (rh and (raw.rstrip()[-1:] in '。！？；」』）' or len(rh) >= 20)):
            flags.append('BODY_PARTIAL')
        if author and canon and author != canon:
            flags.append('AUTHOR_CANON_DIFF')
        if not canon:
            flags.append('AUTHOR_UNVERIFIED')
        t6 = han(title)[:6]
        if t6 and t6 in rh[:30]:
            flags.append('TITLE_REPEAT')
        if re.search(r'一作|一本作|一云', norm or ''):
            flags.append('ANNOTATION_MIXED')
        if len(rh) and len(nh) < len(rh) * 0.95:
            flags.append('BODY_DELETED')
        if len(rh) and len(nh) > len(rh) * 1.05:
            flags.append('BODY_EXPANDED')
        if re.search(r'[0-9]{3,}', raw or ''):
            flags.append('PAGE_NUMBER')
        if TRAD.search(raw or ''):
            flags.append('TRAD_CHARS')
        if re.search(r'一作|一本作|或作', raw or ''):
            flags.append('HAS_VARIANT')
        if not loc:
            flags.append('NO_LOCATOR')
        if not (dyn or era):
            flags.append('NO_DYNASTY')
        if not genre:
            flags.append('NO_GENRE')
        if author and author in rh[:20]:
            flags.append('AUTHOR_IN_BODY')
        dup = keys.get(han(norm)[:20], 0)
        if dup > 1:
            flags.append('DUPLICATE_SUSPECTED')
        for f in flags:
            stat[f] += 1
        out.append([f'W{len(out)+1:04d}', '|'.join(layer_of[wid]), wid, title, author, canon, dyn, era, coll, genre,
                    len(rh), len(nh), len(nh) - len(rh), dup, '|'.join(flags) if flags else 'OK',
                    (raw or '')[:40].replace('\n', ' '), loc or ''])
    with open(os.path.join(OUT, 'WORKS_1000_STRATIFIED_SAMPLE.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['sample_id', 'stratum', 'work_id', 'title', 'author', 'author_canonical', 'dynasty', 'era',
                    'collection', 'genre', 'raw_han_len', 'norm_han_len', 'len_delta', 'dup_count', 'flags',
                    'raw_head', 'locator'])
        w.writerows(out)
    with open(os.path.join(OUT, 'WORKS_1000_QUALITY_AUDIT.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['work_id', 'stratum', 'check_item', 'result', 'detail'])
        for r in out:
            fl = r[14]
            for item, ok, detail in [
                ('正文完整', 'BODY_PARTIAL' not in fl, ''),
                ('作者一致', 'AUTHOR_CANON_DIFF' not in fl and 'AUTHOR_UNVERIFIED' not in fl, r[5] or ''),
                ('题目未混入正文', 'TITLE_REPEAT' not in fl, ''),
                ('校记未混入', 'ANNOTATION_MIXED' not in fl, ''),
                ('正文未被删', 'BODY_DELETED' not in fl, 'len_delta=%d' % r[12]),
                ('正文未膨胀', 'BODY_EXPANDED' not in fl, ''),
                ('页码未混入', 'PAGE_NUMBER' not in fl, ''),
                ('来源可定位', 'NO_LOCATOR' not in fl, (r[16] or '')[:30]),
                ('朝代可判', 'NO_DYNASTY' not in fl, '%s/%s' % (r[6] or '', r[7] or '')),
                ('体裁可判', 'NO_GENRE' not in fl, r[9] or ''),
                ('非重复', 'DUPLICATE_SUSPECTED' not in fl, 'dup=%d' % r[13]),
            ]:
                w.writerow([r[2], r[1], item, 'PASS' if ok else 'FAIL', detail])
    summary = {'n': len(out), 'unique': len({r[2] for r in out}), 'seed': SEED,
               'flags': dict(stat), 'gaps': {k: x for k, x in gaps.items() if x},
               'layers': dict(Counter(x for r in out for x in r[1].split('|'))),
               'multi_layer': sum(1 for r in out if '|' in r[1]),
               'ok_rows': sum(1 for r in out if not (set(r[14].split('|')) & BODY_FLAGS))}
    summary['body_clean'] = summary.pop('ok_rows')
    json.dump(summary, open(os.path.join(OUT, 'LOGS/sample1000.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    con.close()


if __name__ == '__main__':
    main()
