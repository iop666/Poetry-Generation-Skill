#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-11 工作包 C：六套韵书三维标识体系 + 稳定韵目 ID + 六系统查询复核。
三维：source_book_id（韵书）/ rhyme_system_id（该书的分类规范）/ phonological_family_id（历史音系大类）。
"""
import os, re, json, csv, sqlite3, hashlib
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-15/R2-11')

BOOKS = [
    # id, 简称, 全名, 时代, 底本/依据, 本地来源, 韵数, 条目数, 字数, 证据等级, 限制
    ('GUANGYUN', '广韵', '《大宋重修广韵》', '北宋 1008', '钦定四库全书本《原本广韵》（维基文库转录）',
     'raw/books/guangyun/卷1..5.wikitext', 206, 3730, 25619, 'SOURCE_TRANSCRIPTION',
     '小韵首以结构标记重认（R2-11），未与影印本对校'),
    ('JIYUN', '集韵', '《集韵》', '北宋 1039', '文渊阁四库全书本（维基文库转录，附 DJVU 叶码）',
     'raw/r2_08/jiyun_pages/*.json', 206, 4169, None, 'SOURCE_TRANSCRIPTION',
     '小韵数 4,169 为算法筛选结果，非人工验证总数；4 个韵未定位小韵'),
    ('PINGSHUI_YUN', '平水韵', '《平水新刊韵略》系 106 韵', '金 1229', '维基文库《平水韻》',
     'raw/r2_09/rhyme/平水韻.json', 106, None, None, 'SOURCE_TRANSCRIPTION',
     '属诗韵分类，非韵书原书；字表为后世通行本'),
    ('CILIN_ZHENGYUN', '词林正韵', '《词林正韵》十九部', '清 道光', '维基文库转录',
     'ph_cilin_r2_09', 19, 5563, None, 'SOURCE_TRANSCRIPTION',
     '以部/声调/韵目组织，非小韵结构；与前四书体系不同'),
    ('ZHONGYUAN_YINYUN', '中原音韵', '《中原音韵》十九部', '元 1324', '维基文库转录',
     'ph_zhongyuan_r2_09', 19, 5731, None, 'SOURCE_TRANSCRIPTION',
     '分十九部、四声、每声分阴阳；入声派入三声'),
    ('ZHONGHUA_XINYUN', '中华新韵', '《中华新韵（十四韵）》', '2005-05 中华诗词学会颁布',
     '子夜星网站转录常用字简表（与靖边人大、微信公号文本互校）',
     'raw/r2_11/zhonghua_xinyun/ziyexing_zhonghuaxinyun.htm', 14, 7597, 7597, 'SOURCE_TRANSCRIPTION',
     '现代普通话韵部；十三支为零韵母类；非历史音系'),
]

SYSTEM = [
    # source_book_id, rhyme_system_id, family, tone_scheme, note
    ('GUANGYUN', 'GY_206', 'MIDDLE_CHINESE', '四声（平上去入）206 韵，平声分上下', '与集韵同属中古音系，但为独立韵书'),
    ('JIYUN', 'JY_206', 'MIDDLE_CHINESE', '四声 206 韵，韵目次序与广韵不同', '合并统计会破坏两书独立性'),
    ('PINGSHUI_YUN', 'PS_106', 'TRADITIONAL_POETIC_RHYME', '四声 106 韵（平30/上29/去30/入17）', '作诗用韵分类'),
    ('CILIN_ZHENGYUN', 'CL_19', 'TRADITIONAL_POETIC_RHYME', '十九部，每部辖平上去入', '填词用韵分类，与平水韵不同层'),
    ('ZHONGYUAN_YINYUN', 'ZY_19', 'YUAN_DYNASTY_NORTHERN_CHINESE', '十九部，四声，平声分阴阳，入派三声', '元代北方官话'),
    ('ZHONGHUA_XINYUN', 'XY_14', 'MODERN_MANDARIN', '十四韵，四声（阴平/阳平/上声/去声）', '现代普通话，入声已派入四声'),
]


def parse_pingshui():
    d = json.load(open(os.path.join(BASE, 'raw/r2_09/rhyme/平水韻.json'), encoding='utf-8'))
    wt = d['wikitext']
    groups = []
    tone = None
    for line in wt.split('\n'):
        m = re.match(r'==\s*(\S+?聲)部\s*==', line)
        if m:
            tone = m.group(1)
            continue
        m2 = re.match(r'^(\S+?聲)([一二三四五六七八九十百]+)\{\{\+\+\|([^}]+)\}\}', line)
        if m2 and tone:
            groups.append((tone, m2.group(2), m2.group(3)))
    # 字符数：每个韵目后第一段非空行
    charcount = 0
    blocks = re.split(r'^(\S+?聲)([一二三四五六七八九十百]+)\{\{\+\+\|([^}]+)\}\}', wt, flags=re.M)
    for i in range(1, len(blocks), 4):
        body = blocks[i + 3] if i + 3 < len(blocks) else ''
        first = next((l for l in body.split('\n') if l.strip() and not l.startswith('==')), '')
        chars = re.findall(r'[\u4e00-\u9fff]', first.split('【')[0])
        charcount += len(chars)
    cmap = {}
    for i in range(1, len(blocks), 4):
        tone, no, name = blocks[i], blocks[i + 1], blocks[i + 2]
        body = blocks[i + 3] if i + 3 < len(blocks) else ''
        first = next((l for l in body.split('\n') if l.strip() and not l.startswith('==')), '')
        for ch in re.findall(r'[\u4e00-\u9fff]', first.split('【')[0]):
            cmap.setdefault(ch, []).append((name, tone))
    return groups, charcount, cmap


def id_for(book, group_no):
    pre = {'GUANGYUN': 'GUANGYUN', 'JIYUN': 'JIYUN', 'PINGSHUI_YUN': 'PINGSHUI',
           'CILIN_ZHENGYUN': 'CILIN', 'ZHONGYUAN_YINYUN': 'ZHONGYUAN',
           'ZHONGHUA_XINYUN': 'XINYUN'}[book]
    return f'{pre}_{int(group_no):03d}'


def id_for_gy(volume, group_no):
    return f'GUANGYUN_V{volume}_{int(group_no):03d}'


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    ps_groups, ps_chars, ps_map = parse_pingshui()
    # 广韵 206
    gy = list(cur.execute('SELECT volume,yun_no,yun_name,tone,xiaoyun_heads,entries FROM guangyun_xiaoyun_recount_r2_11 ORDER BY volume,yun_no'))
    gy = [((r[0],), tuple(r[1:])) for r in gy]
    # 集韵 206
    jy = list(cur.execute('SELECT yun, count(*), max(volume) FROM jiyun_small_rhyme_audit_r2_10 GROUP BY yun ORDER BY min(rowid)'))
    # 词林 19 部
    cl = list(cur.execute('SELECT bu, count(*) FROM ph_cilin_r2_09 GROUP BY bu ORDER BY min(rowid)'))
    # 中原 19 部
    zy = list(cur.execute('SELECT bu, count(*) FROM ph_zhongyuan_r2_09 GROUP BY bu ORDER BY min(rowid)'))
    # 新韵 14
    xy = list(cur.execute('SELECT yun, count(*) FROM zhonghua_xinyun_characters_r2_11 GROUP BY yun'))
    order = ['一麻', '二波', '三皆', '四开', '五微', '六豪', '七尤', '八寒', '九文', '十唐', '十一庚', '十二齐', '十三支', '十四姑']
    xy.sort(key=lambda r: order.index(r[0]))

    cur.executescript('''
    DROP TABLE IF EXISTS rhyme_source_books_r2_11;
    CREATE TABLE rhyme_source_books_r2_11(
      source_book_id TEXT PRIMARY KEY, name_cn TEXT, name_full TEXT, era TEXT, base_edition TEXT,
      local_source TEXT, n_yun INT, n_entries INT, n_chars INT, evidence_level TEXT, limitation TEXT);
    DROP TABLE IF EXISTS rhyme_system_identity_r2_11;
    CREATE TABLE rhyme_system_identity_r2_11(
      source_book_id TEXT PRIMARY KEY, rhyme_system_id TEXT, phonological_family_id TEXT,
      tone_scheme TEXT, yun_count INT, char_count INT, db_tables TEXT, verify_level TEXT, note TEXT);
    DROP TABLE IF EXISTS rhyme_group_identity_r2_11;
    CREATE TABLE rhyme_group_identity_r2_11(
      group_id TEXT PRIMARY KEY, source_book_id TEXT, group_no INT, display_name TEXT,
      source_name TEXT, normalized_aliases TEXT, tone TEXT, n_chars INT);
    DROP TABLE IF EXISTS rhyme_identity_mapping_r2_11;
    CREATE TABLE rhyme_identity_mapping_r2_11(
      legacy_value TEXT, legacy_scope TEXT, source_book_id TEXT, rhyme_system_id TEXT,
      phonological_family_id TEXT, n_rows INT, note TEXT);
    ''')
    for b in BOOKS:
        cur.execute('INSERT INTO rhyme_source_books_r2_11 VALUES (?,?,?,?,?,?,?,?,?,?,?)', b)
    book_map = {b[0]: b for b in BOOKS}
    for s in SYSTEM:
        b = book_map[s[0]]
        cur.execute('INSERT INTO rhyme_system_identity_r2_11 VALUES (?,?,?,?,?,?,?,?,?)',
                    (s[0], s[1], s[2], s[3], b[6], b[8], b[5], b[9], s[4]))
    # 韵目 ID
    rows = []
    for vol_no, (no, name, tone, xy_n, ent) in gy:
        rows.append((id_for_gy(vol_no[0], no), 'GUANGYUN', no, name, name, '', tone, ent))
    seen = set()
    for no, name, tone in ps_groups:
        gid = id_for('PINGSHUI_YUN', len([r for r in rows if r[1] == 'PINGSHUI_YUN']) + 1)
        rows.append((gid, 'PINGSHUI_YUN', len([r for r in rows if r[1] == 'PINGSHUI_YUN']) + 1, name, name, '', tone, None))
    for i, (bu, n) in enumerate(cl, 1):
        rows.append((id_for('CILIN_ZHENGYUN', i), 'CILIN_ZHENGYUN', i, bu, bu, bu.replace('第', '').replace('部', ''), '', n))
    for i, (bu, n) in enumerate(zy, 1):
        rows.append((id_for('ZHONGYUAN_YINYUN', i), 'ZHONGYUAN_YINYUN', i, bu, bu, bu.replace('第', '').replace('部', ''), '', n))
    for i, (yun, n) in enumerate(xy, 1):
        rows.append((id_for('ZHONGHUA_XINYUN', i), 'ZHONGHUA_XINYUN', i, yun, yun, '', '', n))
    for i, (yun, n, vol) in enumerate(jy, 1):
        rows.append((id_for('JIYUN', i), 'JIYUN', i, yun, yun, '', '', n))
    cur.executemany('INSERT OR REPLACE INTO rhyme_group_identity_r2_11 VALUES (?,?,?,?,?,?,?,?)', rows)
    # legacy 映射
    legacy = [
        ('middle_chinese', 'ph_readings_r2_08.system', 'GUANGYUN', 'GY_206', 'MIDDLE_CHINESE', 51392,
         '该值把广韵与集韵合并，51,392 行无法区分来源书；须按 source_book 字段拆分'),
        ('middle_chinese', 'ph_readings_r2_08.system', 'JIYUN', 'JY_206', 'MIDDLE_CHINESE', 51392,
         '同上；集韵具体行数须按 source_book 统计'),
        ('regulated_verse', 'ph_readings_r2_08.system', 'PINGSHUI_YUN', 'PS_106', 'TRADITIONAL_POETIC_RHYME', 10662, '诗韵'),
        ('ci_rhyme', 'ph_readings_r2_08.system', 'CILIN_ZHENGYUN', 'CL_19', 'TRADITIONAL_POETIC_RHYME', 11382, '词韵'),
        ('modern_rhyme', 'ph_readings_r2_08.system', 'ZHONGHUA_XINYUN', 'XY_14', 'MODERN_MANDARIN', 7216,
         '派生记录，缺十三支 173 条'),
        ('yuan_qu', 'ph_readings_r2_08.system', 'ZHONGYUAN_YINYUN', 'ZY_19', 'YUAN_DYNASTY_NORTHERN_CHINESE', 0,
         'ph_readings 中 0 行；实际字表在 ph_zhongyuan_r2_09（5,731 行），未并入统一 readings'),
        ('old_chinese', 'ph_readings_r2_08.system', None, None, 'ANCIENT_CHINESE', 0, '未建（NOT_BUILT）'),
    ]
    cur.executemany('INSERT INTO rhyme_identity_mapping_r2_11 VALUES (?,?,?,?,?,?,?)', legacy)
    # 源书实际行数校正
    for bs, n in cur.execute("SELECT source_book, count(*) FROM ph_readings_r2_08 WHERE system='middle_chinese' GROUP BY source_book"):
        cur.execute('UPDATE rhyme_identity_mapping_r2_11 SET n_rows=? , note=note||? WHERE legacy_value="middle_chinese" AND source_book_id=?',
                    (n, f'；source_book={bs} 实际 {n} 行', 'GUANGYUN' if '廣' in (bs or '') or '广' in (bs or '') else 'JIYUN'))
    con.commit()

    # ---- 六系统查询 ----
    chars = ['東', '風', '月', '雪', '人', '山', '水', '花', '白', '石', '竹', '去']
    qrows = []
    gy_head = {}
    for head, yun, fq, kind in cur.execute('SELECT head, yun_name, fanqie, kind FROM guangyun_head_classification_r2_11'):
        gy_head.setdefault(head, []).append((yun, fq, kind))
    jy_head = {}
    for head, yun, fq in cur.execute('SELECT head, yun, fanqie FROM ph_jiyun_r2_09'):
        jy_head.setdefault(head, []).append((yun, fq))
    cl_map = defaultdict(list)
    for yunmu, ch, tone in cur.execute('SELECT yunmu_name, charx, tone FROM ph_cilin_r2_09'):
        cl_map[ch].append((yunmu, tone))
    zy_map = defaultdict(list)
    for bu, ch, tone, yy in cur.execute('SELECT bu, charx, tone, yinyang FROM ph_zhongyuan_r2_09'):
        zy_map[ch].append((bu, tone + (yy or '')))
    xy_map = defaultdict(list)
    for ch, yun, tone in cur.execute('SELECT charx, yun, tone FROM zhonghua_xinyun_characters_r2_11'):
        xy_map[ch].append((yun, tone))
    ps_chars_map = defaultdict(list)
    for tone, no, name in ps_groups:
        pass
    for ch in chars:
        for (yun, fq, kind) in gy_head.get(ch, [])[:1]:
            rt = 'XIAOYUN_HEAD' if kind in ('CONFIRMED_XIAOYUN_HEAD', 'SUPPORTED_HEAD_NO_MARKER', 'HEAD_LOST_FANQIE', 'HEAD_WITH_DISPLACED_FANQIE') else 'NON_HEAD_ENTRY'
            qrows.append((ch, 'GUANGYUN', '广韵', yun, '', fq, 'SOURCE_TRANSCRIPTION', rt, 0))
        if ch not in gy_head:
            qrows.append((ch, 'GUANGYUN', '广韵', 'NO_RECORD', '', '', '', 'NOT_AS_XIAOYUN_HEAD', 0))
        for (yun, fq) in jy_head.get(ch, [])[:1]:
            qrows.append((ch, 'JIYUN', '集韵', yun, '', fq, 'SOURCE_TRANSCRIPTION', 'PRIMARY_BOOK', 0))
        if ch not in jy_head:
            qrows.append((ch, 'JIYUN', '集韵', 'NO_RECORD', '', '', '', 'NOT_AS_XIAOYUN_HEAD', 0))
        for (yun, tone) in cl_map.get(ch, [])[:2]:
            qrows.append((ch, 'CILIN_ZHENGYUN', '词林正韵', yun, tone, '', 'SOURCE_TRANSCRIPTION', 'PRIMARY_BOOK', 0))
        if ch not in cl_map:
            qrows.append((ch, 'CILIN_ZHENGYUN', '词林正韵', 'NO_RECORD', '', '', '', 'NOT_IN_SOURCE', 0))
        for (bu, tone) in zy_map.get(ch, [])[:2]:
            qrows.append((ch, 'ZHONGYUAN_YINYUN', '中原音韵', bu, tone, '', 'SOURCE_TRANSCRIPTION', 'PRIMARY_BOOK', 0))
        if ch not in zy_map:
            qrows.append((ch, 'ZHONGYUAN_YINYUN', '中原音韵', 'NO_RECORD', '', '', '', 'NOT_IN_SOURCE', 0))
        for (yun, tone) in xy_map.get(ch, [])[:2]:
            qrows.append((ch, 'ZHONGHUA_XINYUN', '中华新韵', yun, tone, '', 'SOURCE_TRANSCRIPTION', 'DERIVED_RULE', 1))
        if ch not in xy_map:
            qrows.append((ch, 'ZHONGHUA_XINYUN', '中华新韵', 'NO_RECORD', '', '', '', 'NOT_IN_JIANBIAO', 1))
        for (yun, tone) in ps_map.get(ch, [])[:2]:
            qrows.append((ch, 'PINGSHUI_YUN', '平水韵', yun, tone, '', 'SOURCE_TRANSCRIPTION', 'PRIMARY_BOOK', 0))
        if ch not in ps_map:
            qrows.append((ch, 'PINGSHUI_YUN', '平水韵', 'NO_RECORD', '', '', '', 'NOT_IN_SOURCE', 0))
        qrows.append((ch, 'GUANGYUN/JIYUN', '上古音', 'NO_DATA', '', '', 'UNKNOWN', 'NOT_BUILT', 0))
    with open(os.path.join(OUT, 'LOGS/six_system_query.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['char', 'source_book_id', 'book_cn', 'rhyme_group', 'tone', 'fanqie', 'evidence_level', 'record_type', 'derived'])
        w.writerows(qrows)
    stat = Counter((r[1], r[7]) for r in qrows)
    summary = {'pingshui_groups': len(ps_groups), 'pingshui_chars_first_line': ps_chars,
               'guangyun_yun': len(gy), 'jiyun_yun': len(jy), 'cilin_bu': len(cl), 'zhongyuan_bu': len(zy),
               'xinyun_yun': len(xy), 'group_ids': len(rows), 'query_rows': len(qrows),
               'query_stat': {f'{k[0]}|{k[1]}': v for k, v in stat.items()}}
    json.dump(summary, open(os.path.join(OUT, 'LOGS/identity_summary.json'), 'w'), ensure_ascii=False, indent=1)
    con.close()
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
