#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-11 工作包 A：《广韵》小韵结构重认定
不依赖「反切是否在注文首位」判定小韵首，改用原书结构标记：
双全角空格（　　 ，四库本行内小韵起首标记，对应原书圆圈）＋ 韵目行 ＋ 页码断行合并。
输出：逐条分类、206 韵小韵计数、与 R2-10 的 2,907 口径对照、字数自校。
"""
import re, json, csv, sqlite3, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJK = r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002ffff□]'
ANN = re.compile(r'〈([^〈〉]*)〉')
HEADCH = re.compile(CJK)
NUMCH = '一二三四五六七八九十百'

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

def load_volume(v):
    raw = open(os.path.join(BASE, f'raw/books/guangyun/卷{v}.wikitext'), encoding='utf-8').read()
    m = re.search(r'[^\s　]〈[^〉]{0,8}切', raw)
    body = raw[m.start():]
    # 去掉版心页眉（每页重复）与卷题
    body = re.sub(r'[ \u3000]*欽定四庫全書\n|[ \u3000]*原本廣韻卷[一二三四五]\n'
                  r'|[ \u3000]*[上下]平聲\n|[ \u3000]*上聲\n|[ \u3000]*去聲\n|[ \u3000]*入聲\n', '\n', body)
    return body

def parse_volume(v):
    body = load_volume(v)
    rows = []
    cur_yun = None
    prev_end = 0
    idx = 0
    for m in ANN.finditer(body):
        head_region = body[prev_end:m.start()]
        prev_end = m.end()
        content = m.group(1).strip()
        has_marker = '\u3000\u3000' in head_region
        chars = HEADCH.findall(head_region)
        head = chars[-1] if chars else ''
        # 韵目标签：形如 「一東〈獨用〉」「二冬〈鍾同用〉」，且不含反切
        if re.fullmatch(r'[^\s，。]{0,10}(獨用|同用)', content) and '切' not in content:
            # 韵号取自 head_region 末尾数字串
            mm = re.search(r'([%s]{1,3})[　\s]*%s?$' % (NUMCH, re.escape(head) if head else ''), head_region)
            no = cn2int(mm.group(1)) if mm else None
            cur_yun = {'yun_no': no, 'yun_name': head, 'label': content}
            rows.append(dict(volume=v, entry_no=idx, kind='YUN_TAG', head='', yun_no=no,
                             yun_name=head, ann=content, marker=1, fanqie='', offset=m.start()))
            idx += 1
            continue
        fq = ''
        fqm = re.search(r'([^\s，。]{1,4}切)', content[:14])
        if fqm: fq = fqm.group(1)
        if has_marker and head:
            kind = 'CONFIRMED_XIAOYUN_HEAD' if fq else 'POSSIBLE_XIAOYUN_HEAD'
        elif has_marker and not head:
            kind = 'HEAD_LOST_FANQIE' if fq else 'FRAGMENT_HEAD_LOST'
        elif head:
            kind = 'ALTERNATIVE_READING' if fq else ('PLAIN_ENTRY' if content else 'PLAIN_EMPTY_ANN')
        else:
            kind = 'ORPHAN_NO_HEAD'
        rows.append(dict(volume=v, entry_no=idx, kind=kind, head=head,
                         yun_no=cur_yun['yun_no'] if cur_yun else None,
                         yun_name=cur_yun['yun_name'] if cur_yun else None,
                         ann=content, marker=int(has_marker), fanqie=fq, offset=m.start()))
        idx += 1
    return rows

def main():
    allrows = []
    for v in range(1, 6):
        allrows += parse_volume(v)
    # 统计
    from collections import Counter, defaultdict
    c = Counter(r['kind'] for r in allrows)
    print('条目分类：', dict(c))
    xy = [r for r in allrows if r['kind'] in ('CONFIRMED_XIAOYUN_HEAD', 'HEAD_LOST_FANQIE', 'POSSIBLE_XIAOYUN_HEAD')]
    print('小韵合计：', len(xy), '（其中缺字头者', sum(1 for r in xy if r['kind']=='HEAD_LOST_FANQIE'), '）')
    per_vol = Counter(r['volume'] for r in xy)
    print('逐卷：', dict(per_vol))
    # 字数自校：每个小韵首注末尾的汉字数字 vs 实际条目数
    seq = [r for r in allrows if r['kind'] != 'YUN_TAG']
    good = bad = none = 0
    diffs = []
    for i, r in enumerate(seq):
        if r['kind'] not in ('CONFIRMED_XIAOYUN_HEAD', 'HEAD_LOST_FANQIE', 'POSSIBLE_XIAOYUN_HEAD'):
            continue
        n = trailing_num(r['ann'])
        if n is None:
            none += 1; continue
        # 该小韵条目数 = 到下一小韵首之前
        j = i + 1
        cnt = 1
        while j < len(seq) and seq[j]['kind'] not in ('CONFIRMED_XIAOYUN_HEAD','HEAD_LOST_FANQIE','POSSIBLE_XIAOYUN_HEAD'):
            cnt += 1; j += 1
        if cnt == n: good += 1
        else:
            bad += 1
            diffs.append((r['volume'], r['yun_name'], r['head'], n, cnt))
    print('字数自校：一致', good, '不一致', bad, '无字数', none)
    print('前 15 处不一致：')
    for d in diffs[:15]: print('   ', d)
    json.dump({'counts': dict(c), 'xiaoyun': len(xy), 'per_vol': dict(per_vol),
               'numcheck': {'good': good, 'bad': bad, 'none': none},
               'diffs': diffs[:200]}, open('/tmp/gy_recount.json','w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
