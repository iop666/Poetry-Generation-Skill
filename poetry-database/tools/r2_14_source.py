#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-14 工作包 A：作品来源追溯全量审计。

链条：works.source_id → sources.local_path → 原始文件 → (seq → 数组下标/行号)
关键问题：sources 记录的 local_path 是否真为有效语料文件，而非抓取失败页。
"""
import os, json, csv, sqlite3, hashlib
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-14')


def head_bytes(p, n=120):
    with open(p, 'rb') as f:
        return f.read(n)


def classify_file(p):
    if not os.path.exists(p):
        return 'FILE_MISSING', 0, ''
    size = os.path.getsize(p)
    try:
        h = head_bytes(p)
    except Exception:
        return 'FILE_UNREADABLE', size, ''
    s = h.lstrip(b'\xef\xbb\xbf').lstrip()
    if s[:1] in (b'[', b'{'):
        return 'JSON_LIKE', size, h[:80].decode('utf-8', 'replace')
    txt = h.decode('utf-8', 'replace').strip()
    if 'Package size exceeded' in txt or 'exceeded the configured limit' in txt:
        return 'FETCH_ERROR_PAGE', size, txt[:80]
    if txt.startswith('<'):
        return 'HTML_PAGE', size, txt[:80]
    return 'NON_JSON_TEXT', size, txt[:80]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    src = list(cur.execute('SELECT source_id,name,category,collection,url,local_path,bytes,format,acquired_at,parse_status,verified,reliability FROM sources'))
    rows = []
    stat = Counter()
    for (sid, name, cat, coll, url, lp, bts, fmt, acq, ps, ver, rel) in src:
        path = os.path.join(BASE, lp) if lp else ''
        cls, size, head = classify_file(path)
        stat[cls] += 1
        rows.append([sid, name, cat, coll, url, lp, bts, size, fmt, acq, ps, ver, cls, head.replace('\n', ' ')[:60],
                     'YES' if cls == 'JSON_LIKE' else 'NO'])
    with open(os.path.join(OUT, 'WORKS_SOURCE_FIELD_INVENTORY.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['source_id', 'name', 'category', 'collection', 'url', 'local_path', 'bytes_recorded',
                    'bytes_actual', 'format', 'acquired_at', 'parse_status', 'verified', 'file_check',
                    'head_excerpt', 'file_usable'])
        w.writerows(rows)
    print('file_check', dict(stat))

    # 每条 works 的来源状态
    works_stat = {}
    q = lambda s: cur.execute(s).fetchone()[0]
    works_stat['TOTAL_WORKS'] = q('SELECT count(*) FROM works')
    works_stat['SOURCE_ID_PRESENT'] = q("SELECT count(*) FROM works WHERE source_id IS NOT NULL AND source_id<>''")
    works_stat['SOURCE_ID_MISSING'] = works_stat['TOTAL_WORKS'] - works_stat['SOURCE_ID_PRESENT']
    works_stat['SOURCE_ID_IN_SOURCES'] = q("""SELECT count(*) FROM works w WHERE EXISTS
        (SELECT 1 FROM sources s WHERE s.source_id=w.source_id)""")
    works_stat['COLLECTION_PRESENT'] = q("SELECT count(*) FROM works WHERE collection IS NOT NULL AND collection<>''")
    works_stat['RECORD_LOCATOR_PRESENT'] = q("SELECT count(*) FROM works WHERE record_locator IS NOT NULL AND record_locator<>''")
    works_stat['JUAN_PRESENT'] = q("SELECT count(*) FROM works WHERE juan IS NOT NULL AND juan<>''")
    works_stat['BASE_EDITION_PRESENT'] = q("SELECT count(*) FROM works WHERE base_edition IS NOT NULL AND base_edition<>''")
    works_stat['SEQ_PRESENT'] = q("SELECT count(*) FROM works WHERE seq IS NOT NULL AND seq<>''")
    # 关联到「有效文件」的作品数
    good = {r[0] for r in rows if r[12] == 'JSON_LIKE'}
    bad = {r[0] for r in rows if r[12] != 'JSON_LIKE'}
    allsrc = defaultdict(int)
    for sid, n in cur.execute('SELECT source_id,count(*) FROM works GROUP BY source_id'):
        allsrc[sid] = n
    works_stat['WORKS_ON_USABLE_FILE'] = sum(n for s, n in allsrc.items() if s in good)
    works_stat['WORKS_ON_BROKEN_FILE'] = sum(n for s, n in allsrc.items() if s in bad)
    print(json.dumps(works_stat, ensure_ascii=False, indent=1))

    # 全量来源覆盖表（按 source_id 聚合）
    with open(os.path.join(OUT, 'WORKS_SOURCE_375399_COVERAGE.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['source_id', 'source_name', 'collection', 'n_works', 'file_check', 'local_path',
                    'locator_type', 'locator_status'])
        for sid, n in sorted(allsrc.items(), key=lambda x: -x[1]):
            r = next((x for x in rows if x[0] == sid), None)
            if not r:
                w.writerow([sid, '', '', n, 'NOT_IN_SOURCES', '', 'NO_LOCATOR', 'SOURCE_ID_UNMAPPED'])
                continue
            usable = r[12] == 'JSON_LIKE'
            w.writerow([sid, r[1], r[3], n, r[12], r[5],
                        'FILE_LOCATOR' if usable else 'BIBLIOGRAPHIC_LOCATOR',
                        'FILE_USABLE' if usable else 'FILE_BROKEN_BIBLIO_ONLY'])
    json.dump({'file_check': dict(stat), 'works': works_stat,
               'usable_sources': len(good), 'broken_sources': len(bad)},
              open(os.path.join(OUT, 'LOGS/source_audit.json'), 'w'), ensure_ascii=False, indent=1)
    con.close()


if __name__ == '__main__':
    main()
