#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-12 执行前冻结：与 R2-11 基准逐项比对。"""
import hashlib, os, sqlite3, json, subprocess, datetime
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-12')
BASE_BYTES = 715800576
BASE_SHA = '25c7d92c273f8e82de11d4bd3b0ec6feccf37cfb5eceea373165ad0c507e621e'

def sha256(p, bs=1 << 20):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(bs), b''):
            h.update(b)
    return h.hexdigest()

def main():
    st = os.stat(DB)
    con = sqlite3.connect(DB)
    q = lambda s: con.execute(s).fetchall()
    info = {
        'frozen_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'bytes': st.st_size, 'sha256': sha256(DB),
        'bytes_match_r2_11': st.st_size == BASE_BYTES,
        'sha_match_r2_11': sha256(DB) == BASE_SHA,
        'integrity_check': q('PRAGMA integrity_check')[0][0],
        'foreign_key_check_rows': len(q('PRAGMA foreign_key_check')),
        'page_count': q('PRAGMA page_count')[0][0],
        'page_size': q('PRAGMA page_size')[0][0],
        'journal_mode': q('PRAGMA journal_mode')[0][0],
        'freelist_count': q('PRAGMA freelist_count')[0][0],
        'objects': dict(q("SELECT type,count(*) FROM sqlite_master GROUP BY type")),
        'wal_shm': {s: os.path.exists(DB + s) for s in ('-wal', '-shm')},
    }
    rows = []
    for (name,) in q("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        try: n = con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
        except Exception: n = -1
        rows.append((name, n))
    with open(os.path.join(OUT, 'LOGS/table_snapshot.csv'), 'w', encoding='utf-8') as f:
        f.write('table,rows\n')
        for n, c in rows: f.write(f'{n},{c}\n')
    r211 = {n: c for n, c in rows if '_r2_11' in n}
    info['r2_11_tables'] = r211
    info['r2_11_table_count'] = len(r211)
    df = subprocess.run(['df', '-k', BASE], capture_output=True, text=True).stdout.strip().splitlines()
    info['disk'] = df[-1]
    json.dump(info, open(os.path.join(OUT, 'LOGS/preflight.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(info, ensure_ascii=False, indent=1))

if __name__ == '__main__':
    main()
