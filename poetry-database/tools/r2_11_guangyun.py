#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-11 工作包 A：《广韵》小韵结构重认定、206 韵计数、反切终审、韵目归属复查。
底本：维基文库转录《欽定四庫全書》本《原本廣韻》（raw/books/guangyun/卷1..5.wikitext）。
原则：小韵首由原书结构判定（行内双全角空格＝原书圆圈，＋注文以反切起首，＋注末字数），
      不以「反切是否位于注文首位」单一条件代替结构判断。
"""
import re, os, json, csv, sqlite3, hashlib
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-15/R2-11')
CJK = r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002ffff□]'
ANN = re.compile(r'〈([^〈〉]*)〉')
HEADCH = re.compile(CJK)
NUMCH = '一二三四五六七八九十百'
# 韵目名的异体字归一（数据库用通行字，四库转录用本字/异体）
CANON = {'眞': '真', '㣲': '微', '㫖': '旨', '隠': '隱', '佷': '狠', '衺': '邪'}


def canon(ch):
    return CANON.get(ch, ch)

def cn2int(s):
    d = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
    s = s.strip()
    if not s: return None
    if s == '十': return 10
    if '十' in s:
        a, b = s.split('十', 1)
        if len(a) > 1 or len(b) > 1: return None
        return (d.get(a, 1) if a else 1) * 10 + (d.get(b, 0) if b else 0)
    if len(s) == 1: return d.get(s)
    return None

def trailing_num(txt):
    m = re.search(r'([%s]{1,3})$' % NUMCH, txt)
    return cn2int(m.group(1)) if m else None

def load_body(v):
    raw = open(os.path.join(BASE, f'raw/books/guangyun/卷{v}.wikitext'), encoding='utf-8').read()
    m = re.search(r'[^\s　]〈[^〉]{0,8}切', raw)
    body = raw[m.start():]
    body = re.sub(r'[ \u3000]*欽定四庫全書\n|[ \u3000]*原本廣韻卷[一二三四五]\n'
                  r'|[ \u3000]*[上下]平聲\n|[ \u3000]*上聲\n|[ \u3000]*去聲\n|[ \u3000]*入聲\n', '\n', body)
    return body, hashlib.sha256(raw.encode('utf-8')).hexdigest()

def expected_yun(con):
    d = defaultdict(list)
    for vol, no, name, label, tone in con.execute(
            'SELECT volume,yun_no,yun_name,label,tone FROM guangyun_yunmu_repair_r2_10 ORDER BY volume,yun_no'):
        d[vol].append(dict(volume=vol, yun_no=no, name=name, label=label, tone=tone))
    return d

def parse_volume(v, exp):
    body, sha = load_body(v)
    rows = []
    i = 1          # expected pointer（韵 1 以卷首韵目为锚，正文不重复）
    matched = [dict(exp[0], via='VOLUME_FIRST', offset=0)]   # 卷首韵：正文起点即其首小韵
    prev_end = 0
    cur = exp[0]
    for k, m in enumerate(ANN.finditer(body)):
        hr = body[prev_end:m.start()]
        prev_end = m.end()
        content = m.group(1).strip()
        has_marker = '\u3000\u3000' in hr
        chars = HEADCH.findall(hr)
        head = chars[-1] if chars else ''
        tag = None
        # (1) 独立韵目标签
        if re.fullmatch(r'[^\s，。]{0,10}(獨用|同用)', content) and '切' not in content:
            tag = ('STANDALONE', head, content)
        else:
            # (2) 韵目与首小韵同行/同块：head_region 末尾出现 「韵号+韵名」
            for j in range(i, min(i + 4, len(exp))):
                e = exp[j]
                names = {e['name'], *[k for k, v in CANON.items() if v == e['name']]}
                pat = r'([%s]{1,3})[　\s]*(%s)\s*$' % (NUMCH, '|'.join(re.escape(x) for x in names))
                mm = re.search(pat, hr)
                if mm and cn2int(mm.group(1)) == e['yun_no'] and canon(mm.group(2)) == canon(e['name']):
                    tag = ('MERGED', e['name'], f"第{e['yun_no']}韵")
                    i = j + 1
                    cur = e
                    matched.append(dict(e, via='MERGED', offset=m.start()))
                    break
            if tag is None and i < len(exp) and head and canon(head) == canon(exp[i]['name']):
                # 韵目行在转录中丢失，但韵名与首小韵代表字一致：以字定韵
                e = exp[i]; i += 1
                tag = ('MERGED', e['name'], f"第{e['yun_no']}韵")
                cur = e
                matched.append(dict(e, via='HEAD_CHAR', offset=m.start()))
        if tag is not None and tag[0] == 'STANDALONE':
            name = tag[1]
            for j in range(i, min(i + 6, len(exp))):
                if canon(exp[j]['name']) == canon(name):
                    cur = exp[j]; i = j + 1
                    matched.append(dict(exp[j], via='STANDALONE', offset=m.start()))
                    break
            rows.append(dict(volume=v, entry_no=k, kind='YUN_TAG', head='', yun_no=cur['yun_no'] if cur else None,
                             yun_name=cur['name'] if cur else None, ann=content, marker=int(has_marker),
                             fanqie='', offset=m.start(), num=None))
            continue
        fq = ''
        fm = re.match(r'^([^\s，。]{1,2})([^\s，。]{1,2})切', content)
        if fm:
            fq = fm.group(1) + fm.group(2) + '切'
        fq_any = re.search(r'([^\s，。]{1,4}切)', content[:16])
        is_fq_start = bool(fm) and not content.startswith('又')
        num = trailing_num(content)
        if has_marker and head and is_fq_start:
            kind = 'CONFIRMED_XIAOYUN_HEAD'
        elif head and is_fq_start and num is not None:
            kind = 'SUPPORTED_HEAD_NO_MARKER'
        elif has_marker and not head and is_fq_start:
            kind = 'HEAD_LOST_FANQIE'
        elif has_marker and head and not is_fq_start and not fq_any:
            kind = 'POSSIBLE_XIAOYUN_HEAD'
        elif has_marker and head and not is_fq_start and fq_any:
            kind = 'HEAD_WITH_DISPLACED_FANQIE'
        elif fq_any and not is_fq_start:
            kind = 'ALTERNATIVE_READING'
        else:
            kind = 'PLAIN_ENTRY'
        rows.append(dict(volume=v, entry_no=k, kind=kind, head=head,
                         yun_no=cur['yun_no'] if cur else None, yun_name=cur['name'] if cur else None,
                         ann=content, marker=int(has_marker), fanqie=fq, offset=m.start(), num=num))
    return rows, matched, sha

def main():
    con = sqlite3.connect(DB)
    exp = expected_yun(con)
    allrows, allmatched, shas = [], [], {}
    for v in range(1, 6):
        r, m, sha = parse_volume(v, exp[v])
        allrows += r; allmatched += m; shas[v] = sha
    con.close()
    kinds = Counter(r['kind'] for r in allrows)
    XIAO = ('CONFIRMED_XIAOYUN_HEAD', 'SUPPORTED_HEAD_NO_MARKER', 'HEAD_LOST_FANQIE', 'HEAD_WITH_DISPLACED_FANQIE')
    heads = [r for r in allrows if r['kind'] in XIAO]
    summary = {
        'entries_total': len(allrows),
        'kinds': dict(kinds),
        'candidates': {
            'C1_fanqie_start_all': sum(1 for r in allrows if re.match(r'^[^\s，。]{1,2}[^\s，。]{1,2}切', r['ann']) and not r['ann'].startswith('又')),
            'C2_fanqie_start_with_numeral': sum(1 for r in allrows if re.match(r'^[^\s，。]{1,2}[^\s，。]{1,2}切', r['ann']) and not r['ann'].startswith('又') and r['num'] is not None),
            'C3_marker_and_fanqie': sum(1 for r in allrows if r['marker'] and re.match(r'^[^\s，。]{1,2}[^\s，。]{1,2}切', r['ann']) and not r['ann'].startswith('又')),
            'C4_marker_only': sum(1 for r in allrows if r['marker']),
            'structural_union': len(heads),
        },
        'yun_matched': len(allmatched),
        'yun_expected': sum(len(v) for v in exp.values()),
        'unmatched_yun': [],
        'numeral_sum': sum(r['num'] or 0 for r in heads),
        'per_volume': {},
        'vol_sha256': shas,
    }
    for v in range(1, 6):
        summary['per_volume'][v] = {k: c for k, c in Counter(r['kind'] for r in allrows if r['volume'] == v).items()}
    matched_ids = {(m['yun_no']) for m in allmatched}
    for v in range(1, 6):
        vids = {(m['yun_no']) for m in allmatched if m.get('volume', v) == v}
        if not vids: vids = matched_ids
        for e in exp[v]:
            if e['yun_no'] not in vids:
                summary['unmatched_yun'].append(e)
    # 小韵序号 & 逐韵统计
    seq = [r for r in allrows if r['kind'] != 'YUN_TAG']
    for r in allrows:
        r.setdefault('xiaoyun_id', '')
        r.setdefault('xiaoyun_seq', None)
    xid = 0
    for n, r in enumerate(seq):
        if r['kind'] in XIAO:
            xid += 1
            r['xiaoyun_id'] = f'XY-{xid:05d}'
            r['xiaoyun_seq'] = xid
        else:
            r['xiaoyun_id'] = ''
            r['xiaoyun_seq'] = None
    # 字数自校
    good = bad = none = 0
    for n, r in enumerate(seq):
        if r['kind'] not in XIAO: continue
        if r['num'] is None: none += 1; continue
        cnt, j = 1, n + 1
        while j < len(seq) and seq[j]['kind'] not in XIAO:
            cnt += 1; j += 1
        if cnt == r['num']: good += 1
        else: bad += 1
        r['count_actual'] = cnt
    summary['numeral_check'] = {'agree': good, 'disagree': bad, 'no_numeral': none}
    per_yun = defaultdict(lambda: dict(n_entries=0, n_head=0, n_head_lost=0, n_fragment=0, sum_num=0, n_alt=0))
    for r in seq:
        key = (r['volume'], r['yun_no'])
        p = per_yun[key]
        p['n_entries'] += 1
        if r['kind'] in XIAO:
            p['n_head'] += 1
            p['sum_num'] += r['num'] or 0
            if r['kind'] == 'HEAD_LOST_FANQIE': p['n_head_lost'] += 1
        if r['kind'] == 'POSSIBLE_XIAOYUN_HEAD': p['n_fragment'] += 1
        if r['kind'] == 'ALTERNATIVE_READING': p['n_alt'] += 1
    json.dump(summary, open(os.path.join(OUT, 'LOGS/guangyun_recount.json'), 'w'), ensure_ascii=False, indent=1)
    json.dump([{k: r[k] for k in ('volume','entry_no','kind','head','yun_no','yun_name','marker','fanqie','num','xiaoyun_id')} for r in allrows],
              open(os.path.join(OUT, 'LOGS/guangyun_entries.json'), 'w'), ensure_ascii=False)
    print(json.dumps(summary, ensure_ascii=False, indent=1)[:3000])
    # 逐韵 CSV
    con = sqlite3.connect(DB)
    r2_10 = {(vol, no): (n, name) for vol, no, n, name in con.execute(
        'SELECT volume, yun_no, n_xiaoyun, yun_name FROM guangyun_yunmu_repair_r2_10')}
    con.close()
    with open(os.path.join(OUT, 'GUANGYUN_206_RHYME_COUNTS.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['volume','tone','yun_no','yun_name','entries','xiaoyun_heads','head_lost','fragment_marker','alt_reading','sum_declared_chars','r2_10_n_xiaoyun','delta','status'])
        for v in range(1, 6):
            for e in exp[v]:
                p = per_yun.get((v, e['yun_no']))
                if not p:
                    w.writerow([v, e['tone'], e['yun_no'], e['name'], 0,0,0,0,0,0, r2_10.get((v,e['yun_no']),(None,))[0], '', 'NO_ENTRIES_ALIGNED'])
                    continue
                old = r2_10.get((v, e['yun_no']), (None,))[0]
                delta = (p['n_head'] - old) if old is not None else ''
                w.writerow([v, e['tone'], e['yun_no'], e['name'], p['n_entries'], p['n_head'],
                            p['n_head_lost'], p['n_fragment'], p['n_alt'], p['sum_num'], old, delta, 'COUNTED'])
    json.dump({f'{k[0]}-{k[1]}': v for k, v in per_yun.items()},
              open(os.path.join(OUT, 'LOGS/per_yun.json'), 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
