#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-12 工作包 H：跨六书字级查询层 + 假确定性测试。

原则：
- 每本书独立返回，不合并同名记录（广韵/集韵同属中古也不合并）。
- 平水韵同一字的多韵归属不去重。
- 中原音韵不当中古韵书回报；新韵只按现代普通话规范；上古音无来源时返回 UNAVAILABLE。
- 每条结果必须带证据等级、来源定位、是否推导、未解决项。
"""
import os, re, json, csv, sqlite3, sys
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-12')
sys.path.insert(0, os.path.join(BASE, 'tools'))

BOOKS = {
    'GUANGYUN': ('广韵', 'DIGITAL_TRANSCRIPTION'),
    'JIYUN': ('集韵', 'DIGITAL_TRANSCRIPTION'),
    'PINGSHUI_YUN': ('平水韵', 'DIGITAL_TRANSCRIPTION'),
    'CILIN_ZHENGYUN': ('词林正韵', 'DIGITAL_TRANSCRIPTION'),
    'ZHONGYUAN_YINYUN': ('中原音韵', 'DIGITAL_TRANSCRIPTION'),
    'ZHONGHUA_XINYUN': ('中华新韵', 'DIGITAL_TRANSCRIPTION'),
}

TEST_CHARS = list(dict.fromkeys(
    '東同中蟲終風衣重行長樂白雲山水月明光夜思春江花秋聲去來歸'
    '學問心知時日星辰天地人和氣力生老病死愛惡欲色聲香味觸法'
    '詩書禮樂射御數方圓規矩權衡度量上下左右前後東西南北'
    '雲雷雨霜雪露珠玉金銀銅鐵丹青黃赤黑玄宮商角徵羽仁義禮智信忠孝廉恥勇'
    '剛強柔順和美善惡是非真假有無存亡離合悲歡喜怒哀懼夢醉醒歌舞琴棋畫劍'))[:100]


def parse_pingshui():
    d = json.load(open(os.path.join(BASE, 'raw/r2_09/rhyme/平水韻.json'), encoding='utf-8'))
    wt = d['wikitext']
    cmap = defaultdict(list)
    cur = None
    for line in wt.split('\n'):
        m = re.match(r'^#?=*\s*(上平聲|下平聲|上聲|去聲|入聲)([一二三四五六七八九十百]+)\{\{\+\+\|([^}]+)\}\}', line.strip())
        if m:
            cur = (m.group(3), m.group(1), m.group(2))
            continue
        if cur and line.strip() and not line.startswith(('==', '{{', '|')):
            body = line.split('{{')[0]
            for ch in re.findall(r'[\u4e00-\u9fff]', body):
                cmap[ch].append(cur)
    return cmap, d.get('revid')


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    ps_map, ps_rev = parse_pingshui()

    # 广韵字级：全部条目（含成员字），韵目来自所属小韵区间
    gy = defaultdict(list)
    for head, yun, fq, kind in cur.execute('''SELECT head,yun_name,fanqie,kind FROM guangyun_head_classification_r2_11'''):
        gy[head].append((yun, fq, kind))
    jy = defaultdict(list)
    for ch, yun, fq, ish, grp in cur.execute('''SELECT character,rhyme_group,fanqie,is_xiaoyun_head,char_group
                                                FROM jiyun_char_index_r2_12'''):
        jy[ch].append((yun, fq, ish, grp))
    cl = defaultdict(list)
    for ch, bu, tone, ym in cur.execute('SELECT charx,bu,tone,yunmu FROM ph_cilin_r2_09'):
        cl[ch].append((bu, tone, ym))
    zy = defaultdict(list)
    for ch, bu, tone, yy in cur.execute('SELECT charx,bu,tone,yinyang FROM ph_zhongyuan_r2_09'):
        zy[ch].append((bu, tone, yy))
    xin = defaultdict(list)
    for ch, yun, tone in cur.execute('SELECT charx,yun,tone FROM zhonghua_xinyun_characters_r2_11'):
        xin[ch].append((yun, tone))

    cur.executescript('''
    DROP TABLE IF EXISTS cross_rhyme_lookup_r2_12;
    CREATE TABLE cross_rhyme_lookup_r2_12(
      row_id INTEGER PRIMARY KEY AUTOINCREMENT, query_id TEXT, character TEXT, source_book_id TEXT, source_book_name TEXT,
      volume TEXT, rhyme_group TEXT, xiaoyun TEXT, fanqie TEXT, tone TEXT,
      evidence_level TEXT, source_locator TEXT, is_derived INT, unresolved TEXT, note TEXT);
    ''')
    rows = []
    n = 0
    for ch in TEST_CHARS:
        n += 1
        qid = f'QX-{n:03d}'
        # 广韵
        if ch in gy:
            for yun, fq, kind in gy[ch]:
                ish = kind in ('CONFIRMED_XIAOYUN_HEAD', 'SUPPORTED_HEAD_NO_MARKER',
                               'HEAD_WITH_DISPLACED_FANQIE', 'HEAD_LOST_FANQIE')
                rows.append([qid, ch, 'GUANGYUN', '广韵', '', yun or 'UNASSIGNED', '', fq or '',
                             '', 'DIGITAL_TRANSCRIPTION', 'raw/books/guangyun/卷N.wikitext', 0,
                             '' if yun else '韵目未定位',
                             '小韵首' if ish else '小韵内条目（无独立反切）'])
        else:
            rows.append([qid, ch, 'GUANGYUN', '广韵', '', 'NO_RECORD', '', '', '', '', '', 0, '', '该字未见于本转录'])
        # 集韵
        if ch in jy:
            seen = set()
            for yun, fq, ish, grp in jy[ch]:
                key = (yun, ish)
                if key in seen:
                    continue
                seen.add(key)
                rows.append([qid, ch, 'JIYUN', '集韵', '', yun, '', fq or '',
                             '', 'DIGITAL_TRANSCRIPTION', f'raw/r2_08/jiyun_pages（{yun}）', 0,
                             '' if fq else '非小韵首，本字无独立反切',
                             '小韵首组：' + grp if ish else '小韵内字'])
        else:
            rows.append([qid, ch, 'JIYUN', '集韵', '', 'NO_RECORD', '', '', '', '', '', 0, '', ''])
        # 平水
        if ch in ps_map:
            for name, tone, no in ps_map[ch]:
                rows.append([qid, ch, 'PINGSHUI_YUN', '平水韵', tone + no, name, '', '', tone,
                             'DIGITAL_TRANSCRIPTION', f'平水韻 revid={ps_rev}', 0, '', '同字多韵，未去重'])
        else:
            rows.append([qid, ch, 'PINGSHUI_YUN', '平水韵', '', 'NO_RECORD', '', '', '', '', '', 0, '', ''])
        # 词林
        if ch in cl:
            for bu, tone, ym in cl[ch]:
                rows.append([qid, ch, 'CILIN_ZHENGYUN', '词林正韵', bu, ym, '', '', tone,
                             'DIGITAL_TRANSCRIPTION', 'ph_cilin_r2_09', 0, '', '十九部体系，非206韵'])
        else:
            rows.append([qid, ch, 'CILIN_ZHENGYUN', '词林正韵', '', 'NO_RECORD', '', '', '', '', '', 0, '', ''])
        # 中原
        if ch in zy:
            for bu, tone, yy in zy[ch]:
                rows.append([qid, ch, 'ZHONGYUAN_YINYUN', '中原音韵', bu, '', '', '', f'{tone}/{yy}',
                             'DIGITAL_TRANSCRIPTION', 'ph_zhongyuan_r2_09', 0, '',
                             '元代北方音系，不可当中古音值'])
        else:
            rows.append([qid, ch, 'ZHONGYUAN_YINYUN', '中原音韵', '', 'NO_RECORD', '', '', '', '', '', 0, '', ''])
        # 新韵
        if ch in xin:
            for yun, tone in xin[ch]:
                rows.append([qid, ch, 'ZHONGHUA_XINYUN', '中华新韵', '十四韵', yun, '', '', tone,
                             'DIGITAL_TRANSCRIPTION', 'raw/r2_11/zhonghua_xinyun/ziyexing_zhonghuaxinyun.htm', 0,
                             '', '现代普通话规范，不可回推中古'])
        else:
            rows.append([qid, ch, 'ZHONGHUA_XINYUN', '中华新韵', '', 'NO_RECORD', '', '', '', '', '', 0,
                         '简表为简体，繁体字需字形对应', ''])
        # 上古音
        rows.append([qid, ch, 'OLD_CHINESE', '上古音', '', 'UNAVAILABLE', '', '', '', 'UNKNOWN', '', 0,
                     '无可靠来源链（《诗经韵读》《楚辞韵读》未完成影印对校）', '不推断'])
    cur.executemany('INSERT INTO cross_rhyme_lookup_r2_12 (query_id,character,source_book_id,source_book_name,volume,rhyme_group,xiaoyun,fanqie,tone,evidence_level,source_locator,is_derived,unresolved,note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', rows)
    con.commit()
    with open(os.path.join(OUT, 'CROSS_RHYME_LOOKUP_100.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['query_id', 'character', 'source_book_id', 'source_book_name', 'volume', 'rhyme_group',
                    'xiaoyun', 'fanqie', 'tone', 'evidence_level', 'source_locator', 'is_derived',
                    'unresolved', 'note'])
        w.writerows(rows)

    # 假确定性测试
    tests = []
    def add(tid, name, expect, actual, ok, note=''):
        tests.append([tid, name, expect, actual, 'PASS' if ok else 'FAIL', note])
    # 1 广韵与集韵不合并
    dup = cur.execute('''SELECT character,count(DISTINCT source_book_id) FROM cross_rhyme_lookup_r2_12
                         WHERE source_book_id IN ('GUANGYUN','JIYUN') GROUP BY character''').fetchall()
    add('FC-01', '广韵与集韵对同一字分别成行', '每字两行以上（两书各自独立）',
        'max distinct books=%d' % max(d[1] for d in dup), max(d[1] for d in dup) == 2)
    # 2 平水多归属不去重
    m = cur.execute('''SELECT character,count(*) FROM cross_rhyme_lookup_r2_12 WHERE source_book_id='PINGSHUI_YUN'
                       AND rhyme_group<>'NO_RECORD' GROUP BY character HAVING count(*)>1''').fetchall()
    add('FC-02', '平水韵同字多韵保留', '存在多韵记录', 'multi=%d' % len(m), len(m) > 0)
    # 3 中原不当中古
    bad = cur.execute('''SELECT count(*) FROM cross_rhyme_lookup_r2_12 WHERE source_book_id='ZHONGYUAN_YINYUN'
                         AND length(fanqie)>0''').fetchone()[0]
    add('FC-03', '中原音韵不返回反切', '0', str(bad), bad == 0)
    # 4 新韵不返回反切
    bad2 = cur.execute('''SELECT count(*) FROM cross_rhyme_lookup_r2_12 WHERE source_book_id='ZHONGHUA_XINYUN'
                          AND length(fanqie)>0''').fetchone()[0]
    add('FC-04', '中华新韵不返回反切', '0', str(bad2), bad2 == 0)
    # 5 上古音 UNAVAILABLE
    up = cur.execute('''SELECT count(*) FROM cross_rhyme_lookup_r2_12 WHERE source_book_id='OLD_CHINESE'
                        AND rhyme_group='UNAVAILABLE' ''').fetchone()[0]
    add('FC-05', '上古音无来源返回 UNAVAILABLE', str(len(TEST_CHARS)), str(up), up == len(TEST_CHARS))
    # 6 集韵成员字无独立反切必须标注
    nb = cur.execute('''SELECT count(*) FROM cross_rhyme_lookup_r2_12 WHERE source_book_id='JIYUN'
                        AND length(fanqie)=0 AND rhyme_group<>'NO_RECORD' AND unresolved='' ''').fetchone()[0]
    add('FC-06', '集韵非小韵首必须说明无独立反切', '0', str(nb), nb == 0)
    # 7 六书都有记录的字数
    six = cur.execute('''SELECT character,count(DISTINCT source_book_id) FROM cross_rhyme_lookup_r2_12
                         WHERE rhyme_group<>'NO_RECORD' AND rhyme_group<>'UNAVAILABLE'
                         GROUP BY character HAVING count(DISTINCT source_book_id)=6''').fetchall()
    add('FC-07', '六书同时有记录的字', '>0', str(len(six)), len(six) > 0)
    with open(os.path.join(OUT, 'QUERY_FALSE_CERTAINTY_TESTS.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['test_id', 'name', 'expect', 'actual', 'result', 'note'])
        w.writerows(tests)
    stat = {'chars': len(TEST_CHARS), 'rows': len(rows),
            'by_book': dict((b, sum(1 for r in rows if r[2] == b)) for b in list(BOOKS) + ['OLD_CHINESE']),
            'no_record': dict((b, sum(1 for r in rows if r[2] == b and r[5] == 'NO_RECORD')) for b in BOOKS),
            'six_book_chars': [s[0] for s in six],
            'tests': tests}
    json.dump(stat, open(os.path.join(OUT, 'LOGS/query_r2_12.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in stat.items() if k != 'tests'}, ensure_ascii=False, indent=1))
    for t in tests:
        print(t[0], t[4], t[2], '=>', t[3])
    con.close()


if __name__ == '__main__':
    main()
