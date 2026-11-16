#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-13 执行前冻结：与 R2-12 基准逐项比对，并登记作品库/作者表规模。"""
import hashlib, os, sqlite3, json, subprocess, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-13')
BASE_BYTES = 765222912
BASE_SHA = 'e4053f6ee9bcd73755876d840fe6a35acb9181ba2118766e5ea388daad33ac27'


def sha256(p, bs=1 << 20):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(bs), b''):
            h.update(b)
    return h.hexdigest()


def main():
    st = os.stat(DB)
    h = sha256(DB)
    con = sqlite3.connect(DB)
    q = lambda s: con.execute(s).fetchall()
    q1 = lambda s: con.execute(s).fetchone()[0]
    info = {
        'frozen_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'bytes': st.st_size, 'sha256': h,
        'bytes_match': st.st_size == BASE_BYTES, 'sha_match': h == BASE_SHA,
        'integrity_check': q1('PRAGMA integrity_check'),
        'foreign_key_check_rows': len(q('PRAGMA foreign_key_check')),
        'page_count': q1('PRAGMA page_count'), 'page_size': q1('PRAGMA page_size'),
        'journal_mode': q1('PRAGMA journal_mode'), 'freelist_count': q1('PRAGMA freelist_count'),
        'objects': dict(q("SELECT type,count(*) FROM sqlite_master GROUP BY type")),
        'wal_shm': {s: os.path.exists(DB + s) for s in ('-wal', '-shm')},
        'works_rows': q1('SELECT count(*) FROM works'),
        'works_distinct_author': q1('SELECT count(DISTINCT author_name) FROM works'),
        'works_distinct_author_canonical': q1('SELECT count(DISTINCT author_canonical) FROM works'),
        'authors_rows': q1('SELECT count(*) FROM authors'),
        'author_alias_rows': q1('SELECT count(*) FROM author_alias'),
        'works_with_bianwen': q1('SELECT count(*) FROM works WHERE text_raw IS NULL OR text_raw=""'),
    }
    # 逐表行数
    rows = []
    for (name,) in q("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        try:
            n = con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
        except Exception:
            n = -1
        rows.append((name, n))
    with open(os.path.join(OUT, 'LOGS/table_snapshot.csv'), 'w', encoding='utf-8') as f:
        f.write('table,rows\n')
        for n, c in rows:
            f.write(f'{n},{c}\n')
    info['r2_12_tables'] = {n: c for n, c in rows if '_r2_12' in n}
    df = subprocess.run(['df', '-k', BASE], capture_output=True, text=True).stdout.strip().splitlines()
    info['disk'] = df[-1]
    json.dump(info, open(os.path.join(OUT, 'LOGS/preflight.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(info, ensure_ascii=False, indent=1))

    # R2-12 交付文件哈希（抽样关键件）
    r12 = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-12')
    keys = ['WORKS_TEXT_POLLUTION_339_AUDIT.csv', 'WORKS_TEXT_REVISIONS_R2_12.csv',
            'WORKS_TEXT_500_SAMPLE_AUDIT.csv', 'WORKS_AUTHOR_CORRECTIONS.csv',
            'CIPAI_11_DOUBLE_BLIND_REVIEW.csv', 'COMPLETE_REPORT.md']
    with open(os.path.join(OUT, 'LOGS/r2_12_hashes.csv'), 'w', encoding='utf-8') as f:
        f.write('file,bytes,sha256\n')
        for k in keys:
            p = os.path.join(r12, k)
            if os.path.exists(p):
                f.write(f'{k},{os.path.getsize(p)},{sha256(p)}\n')
    con.close()


if __name__ == '__main__':
    main()
