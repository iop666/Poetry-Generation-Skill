#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-14 执行前冻结与比对。"""
import hashlib, os, sqlite3, json, subprocess, datetime
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE,'database/poetry.db'); OUT = os.path.join(BASE,'reports/tasks/2026-11-16/R2-14')
BASE_BYTES = 767918080
BASE_SHA = 'a9c5bbfb72c0cc8784d080f3332f393e718c61a15d93d35b4114e3edb9258a76'
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
st=os.stat(DB); h=sha(DB)
con=sqlite3.connect(DB); q=lambda s: con.execute(s).fetchall(); q1=lambda s: con.execute(s).fetchone()[0]
info={'frozen_at':datetime.datetime.now().isoformat(timespec='seconds'),'bytes':st.st_size,'sha256':h,
      'bytes_match':st.st_size==BASE_BYTES,'sha_match':h==BASE_SHA,
      'integrity_check':q1('PRAGMA integrity_check'),'foreign_key_check_rows':len(q('PRAGMA foreign_key_check')),
      'page_count':q1('PRAGMA page_count'),'page_size':q1('PRAGMA page_size'),
      'journal_mode':q1('PRAGMA journal_mode'),'objects':dict(q("SELECT type,count(*) FROM sqlite_master GROUP BY type")),
      'wal_shm':{s:os.path.exists(DB+s) for s in ('-wal','-shm')},
      'works':q1('SELECT count(*) FROM works'),'authors':q1('SELECT count(*) FROM authors'),
      'author_alias':q1('SELECT count(*) FROM author_alias'),'sources':q1('SELECT count(*) FROM sources'),
      'r2_13_tables':{t:q1(f'SELECT count(*) FROM "{t}"') for (t,) in q("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_r2_13'")}}
info['disk']=subprocess.run(['df','-k',BASE],capture_output=True,text=True).stdout.strip().splitlines()[-1]
json.dump(info, open(os.path.join(OUT,'LOGS/preflight.json'),'w'), ensure_ascii=False, indent=1)
print(json.dumps(info, ensure_ascii=False, indent=1))
con.close()
