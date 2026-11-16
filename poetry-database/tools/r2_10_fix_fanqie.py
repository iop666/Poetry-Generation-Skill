#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-10 修正：集韻反切上下字、廣韻「小韻首」嚴格判定。

由獨立複核發現的兩處缺陷：
1. `ph_jiyun_r2_09.fanqie_upper` 存的是「反切整串（去切字）」，不是上字；
   `fanqie_lower` 則是「去首字後的殘串」。→ 建新表 `jiyun_small_rhyme_audit_r2_10` 改正。
2. `guangyun_fanqie_r2_10.is_xiaoyun_head` 沿用 R2-08 的「注文含切」判定，
   把「又某某切」的又音條目也算成小韻首（獨立複核抽樣 34.7% 屬此類）。
   → 增加 `head_kind`：STRICT_HEAD / YOUYIN_ENTRY / NO_FANQIE，並給出嚴格口徑計數。
"""
import collections
import csv
import json
import os
import re
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
OUT = os.path.join(ROOT, "raw", "r2_10")
CJK = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

# ---------- 1. 集韻 ----------
con.execute("DROP TABLE IF EXISTS jiyun_small_rhyme_audit_r2_10")
con.execute("""CREATE TABLE jiyun_small_rhyme_audit_r2_10(
  id INTEGER PRIMARY KEY AUTOINCREMENT, yun TEXT, volume INT, seq INT, head TEXT,
  fanqie_raw TEXT, fanqie_upper TEXT, fanqie_lower TEXT, fanqie_kind TEXT,
  old_fanqie_upper TEXT, old_fanqie_lower TEXT, declared_chars INT, n_heads_est INT,
  page_title TEXT, html_sha256 TEXT, evidence_level TEXT, round TEXT)""")

rows = [dict(r) for r in con.execute("SELECT * FROM ph_jiyun_r2_09")]
recs, st = [], collections.Counter()
for r in rows:
    raw = (r["fanqie"] or "").strip()
    fc = raw[:-1] if raw.endswith("切") else raw
    if len(fc) >= 2:
        up, lo, kind = fc[0], fc[1], ("TWO_CHAR" if len(fc) == 2 else "LONGER")
    elif len(fc) == 1:
        up, lo, kind = "", "", "INCOMPLETE_ONE_CHAR"
    else:
        up, lo, kind = "", "", "NO_FANQIE"
    st[kind] += 1
    if r["fanqie_upper"] and r["fanqie_upper"] != up:
        st["OLD_UPPER_WRONG"] += 1
    recs.append((r["yun"], r["volume"], r["seq"], r["head"], raw, up, lo, kind,
                 r["fanqie_upper"] or "", r["fanqie_lower"] or "", r["declared_chars"],
                 r["n_heads_est"], r["page_title"], r["html_sha256"],
                 "SOURCE_TRANSCRIPTION", "2026-11-15"))
con.executemany("""INSERT INTO jiyun_small_rhyme_audit_r2_10
  (yun,volume,seq,head,fanqie_raw,fanqie_upper,fanqie_lower,fanqie_kind,
   old_fanqie_upper,old_fanqie_lower,declared_chars,n_heads_est,page_title,html_sha256,
   evidence_level,round) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", recs)
print("集韻新表:", len(recs), dict(st))

# ---------- 2. 廣韻 小韻首嚴格判定 ----------
heads = [dict(r) for r in con.execute(
    "SELECT rowid, * FROM guangyun_fanqie_r2_10 WHERE is_xiaoyun_head=1")]
kinds = collections.Counter()
upd = []
for r in heads:
    ev = r["evidence"] or ""
    fq = r["fanqie"] or ""
    hidx = max(ev.rfind(r["head"][-1]), 0) if r["head"] else 0
    i = ev.find("〈", hidx)
    kind = "NO_FANQIE"
    if i >= 0 and fq:
        seg = ev[i + 1:]
        j = seg.find(fq)
        if j >= 0:
            kind = "STRICT_HEAD" if j <= 6 else "YOUYIN_ENTRY"
        else:
            # 反切被截斷在 evidence 之外，仍屬首位
            kind = "STRICT_HEAD" if seg.find(fq[:-1]) in (0, 1, 2) else "YOUYIN_ENTRY"
    kinds[kind] += 1
    upd.append((kind, r["entry_id"]))
con.executemany("UPDATE guangyun_fanqie_r2_10 SET comparison=comparison WHERE entry_id=?", [])
# 加欄位
cols = [c[1] for c in con.execute("PRAGMA table_info(guangyun_fanqie_r2_10)")]
if "head_kind" not in cols:
    con.execute("ALTER TABLE guangyun_fanqie_r2_10 ADD COLUMN head_kind TEXT")
con.executemany("UPDATE guangyun_fanqie_r2_10 SET head_kind=? WHERE entry_id=?", upd)
con.commit()
print("廣韻小韻首判定:", dict(kinds))

strict = con.execute(
    "SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE head_kind='STRICT_HEAD'").fetchone()[0]
n_yun = con.execute(
    "SELECT count(distinct volume||'-'||yun_no) FROM guangyun_fanqie_r2_10 WHERE head_kind='STRICT_HEAD'").fetchone()[0]

# CSV
with open(os.path.join(OUT, "guangyun", "guangyun_head_kind.csv"), "w", newline="",
          encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["head_kind", "n"])
    for k, v in kinds.most_common():
        w.writerow([k, v])

json.dump({"jiyun_fanqie_kinds": dict(st), "n_jiyun_rows": len(recs),
           "guangyun_head_kinds": dict(kinds), "n_strict_head": strict,
           "n_yun_with_strict_head": n_yun},
          open(os.path.join(OUT, "jiyun", "jiyun_fanqie_fix.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("嚴格小韻首:", strict, "覆蓋韻數:", n_yun)
con.close()
