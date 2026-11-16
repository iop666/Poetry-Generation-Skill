#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-11 执行前冻结：数据库字节数、SHA-256、完整性、表/视图/索引快照、磁盘。"""
import hashlib, os, sqlite3, json, subprocess, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-15/R2-11')

def sha256(p, bs=1 << 20):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(bs), b''):
            h.update(b)
    return h.hexdigest()

def main():
    st = os.stat(DB)
    info = {
        'frozen_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'db_path': os.path.relpath(DB, BASE),
        'bytes': st.st_size,
        'sha256': sha256(DB),
        'mtime': datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds'),
    }
    con = sqlite3.connect(DB)
    q = lambda s: con.execute(s).fetchall()
    info['integrity_check'] = q('PRAGMA integrity_check')[0][0]
    info['foreign_key_check_n'] = len(q('PRAGMA foreign_key_check'))
    info['page_count'] = q('PRAGMA page_count')[0][0]
    info['page_size'] = q('PRAGMA page_size')[0][0]
    info['journal_mode'] = q('PRAGMA journal_mode')[0][0]
    info['freelist_count'] = q('PRAGMA freelist_count')[0][0]
    info['objects'] = dict(q("SELECT type, count(*) FROM sqlite_master GROUP BY type"))
    info['wal_shm'] = {p: os.path.exists(DB + p) for p in ('-wal', '-shm')}
    for suffix in ('-wal', '-shm'):
        if os.path.exists(DB + suffix):
            info['wal_shm_size_' + suffix] = os.path.getsize(DB + suffix)
    # 逐表行数
    rows = []
    for (name,) in q("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        try:
            n = con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
        except Exception as e:
            n = -1
        rows.append((name, n))
    with open(os.path.join(OUT, 'PREFLIGHT_TABLE_SNAPSHOT.csv'), 'w', encoding='utf-8') as f:
        f.write('table,rows\n')
        for n, c in rows:
            f.write(f'{n},{c}\n')
    # R2-10 对象存在性
    want = ['guangyun_fanqie_r2_10', 'guangyun_yunmu_repair_r2_10', 'jiyun_page_provenance_r2_10',
            'jiyun_small_rhyme_audit_r2_10', 'cipai_symbol_audit_r2_10', 'v_ph_semantics_r2_10']
    info['r2_10_objects'] = {w: bool(q(f"SELECT 1 FROM sqlite_master WHERE name='{w}'")) for w in want}
    info['r2_10_rowcounts'] = {w: (con.execute(f'SELECT count(*) FROM "{w}"').fetchone()[0]
                                  if info['r2_10_objects'][w] else None) for w in want}
    con.close()
    # 磁盘
    df = subprocess.run(['df', '-k', BASE], capture_output=True, text=True).stdout.strip().splitlines()
    info['disk_df'] = df[-1]
    json.dump(info, open(os.path.join(OUT, 'LOGS/preflight.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in info.items() if k != 'r2_10_rowcounts'}, ensure_ascii=False, indent=1))
    print('r2_10_rowcounts', info['r2_10_rowcounts'])
    # 文件哈希（原始资料）
    with open(os.path.join(OUT, 'PREFLIGHT_FILE_HASHES.csv'), 'w', encoding='utf-8') as f:
        f.write('relpath,bytes,sha256\n')
        for rel in ['raw/books/guangyun/卷1.wikitext', 'raw/books/guangyun/卷2.wikitext',
                    'raw/books/guangyun/卷3.wikitext', 'raw/books/guangyun/卷4.wikitext',
                    'raw/books/guangyun/卷5.wikitext', 'raw/books_native/long_yushsheng_cilv/pages.jsonl',
                    'raw/books_ocr_paddle/wangli_yinyunxue/pages.jsonl', 'raw/books_ocr_paddle/wangli_tongyuan/pages.jsonl']:
            p = os.path.join(BASE, rel)
            if os.path.exists(p):
                f.write(f'{rel},{os.path.getsize(p)},{sha256(p)}\n')

if __name__ == '__main__':
    main()
