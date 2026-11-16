#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 A：建立統一證據等級映射、統計口徑表與去重分析。

新增（全部 _r2_09 後綴，不改舊表）：
  ph_evidence_map_r2_09      舊 evidence_level → 新八級
  ph_reading_stats_r2_09     每體系逐字段填充率與口徑
  ph_dup_analysis_r2_09      重複成因分類
並建立只讀視圖 v_ph_records_r2_09（誠實命名）。
"""
import os
import sqlite3
import json
import csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
OUT = os.path.join(ROOT, "raw", "r2_09", "audit")
os.makedirs(OUT, exist_ok=True)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

# ---------- 1. 證據等級映射 ----------
MAP = [
    # (舊值, 新等級, 來源類型, 是否可追到原書頁, 說明)
    ("JIYUN_SMALL_RHYME", "SOURCE_TRANSCRIPTION", "維基文庫《集韻（四庫全書本）》轉錄", 1,
     "四庫本電子轉錄，非影印；每韻頁有 revid 與 HTML SHA-256，可回查；未與影印本對勘"),
    ("GUANGYUN_ENTRY", "SOURCE_TRANSCRIPTION", "維基文庫《原本廣韻》轉錄", 1,
     "同上；韻目歸屬大量依 CARRIED_FORWARD 推定，非逐條原書明載"),
    ("PINGSHUI_TABLE", "SOURCE_EDITION", "《平水韻》通行排印本字表", 0,
     "來源為整理本 JSON，非原書影印；無版本頁碼，僅有韻目與字表"),
    ("DERIVED_FROM_PINGSHUI", "COMPUTED", "由平水韻字表按《詞林正韻》部目折算", 0,
     "十九部歸併規則推定，字級非原書字表；誤差風險最高"),
    ("DERIVED_FROM_PINGSHUI_HALF", "COMPUTED", "半韻折算", 0,
     "所謂「半韻」1,572 條無原書字級依據，須隔離"),
    ("DERIVED_PINYIN", "COMPUTED", "由現代漢語拼音派生", 0,
     "依《中華新韻》十四韻規則由拼音映射，非原書字表；不代表歷史音"),
]
con.execute("DROP TABLE IF EXISTS ph_evidence_map_r2_09")
con.execute("""CREATE TABLE ph_evidence_map_r2_09(
 old_evidence_level TEXT PRIMARY KEY, new_evidence_level TEXT, source_type TEXT,
 traceable_to_page INT, note TEXT, round TEXT)""")
con.executemany("INSERT INTO ph_evidence_map_r2_09 VALUES(?,?,?,?,?,'2026-11-14')", MAP)

# ---------- 2. 每體系統計口徑 ----------
con.execute("DROP TABLE IF EXISTS ph_reading_stats_r2_09")
con.execute("""CREATE TABLE ph_reading_stats_r2_09(
 system TEXT, rows_total INT, rows_placeholder INT, rows_null_reading INT,
 rows_with_fanqie INT, rows_with_initial INT, rows_with_final INT, rows_with_page INT,
 distinct_chars INT, distinct_rhyme_groups INT, distinct_tone_values TEXT,
 new_evidence_levels TEXT, counting_note TEXT)""")
rows = []
NOTE = {
    "middle_chinese": "廣韻條目＋集韻小韻；reading/initial/page 全空，不得稱「讀音」",
    "regulated_verse": "平水韻字表；無反切、無頁碼，屬排印本字表",
    "ci_rhyme": "由平水韻折算，非原書字表；含 1,572 條半韻",
    "modern_rhyme": "拼音派生；final 由拼音填，其餘音韻字段空",
}
for r in con.execute("select system,count(*) n from ph_readings_r2_08 group by 1"):
    s = r["system"]
    def cnt(cond):
        return con.execute("select count(*) from ph_readings_r2_08 where system=? and " + cond, (s,)).fetchone()[0]
    tones = [x[0] for x in con.execute(
        "select distinct tone from ph_readings_r2_08 where system=? order by 1", (s,))]
    lev = [x[0] for x in con.execute(
        "select distinct evidence_level from ph_readings_r2_08 where system=? order by 1", (s,))]
    rows.append((s, r["n"],
                 cnt("charx like '%□%'"),
                 cnt("reading is null"),
                 cnt("fanqie is not null and fanqie<>''"),
                 cnt("initial is not null and initial<>''"),
                 cnt("final is not null and final<>''"),
                 cnt("page is not null and page<>''"),
                 cnt("1=1") and con.execute(
                     "select count(distinct charx) from ph_readings_r2_08 where system=?", (s,)).fetchone()[0],
                 con.execute("select count(distinct rhyme_group) from ph_readings_r2_08 where system=?", (s,)).fetchone()[0],
                 "/".join(tones), "/".join(lev), NOTE.get(s, "")))
con.executemany("INSERT INTO ph_reading_stats_r2_09 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

# ---------- 3. 重複成因 ----------
con.execute("DROP TABLE IF EXISTS ph_dup_analysis_r2_09")
con.execute("""CREATE TABLE ph_dup_analysis_r2_09(
 system TEXT, dup_kind TEXT, dup_groups INT, extra_rows INT, verdict TEXT, note TEXT)""")
dup = []
for r in con.execute("""
    select system, case when charx like '%□%' then 'PLACEHOLDER_HEAD'
                        when fanqie is not null and fanqie<>'' then 'SAME_XIAOYUN_MULTI_ENTRY'
                        else 'SAME_CHAR_SAME_GROUP' end k,
           count(*) g, sum(c-1) e
    from (select system,charx,fanqie,count(*) c from ph_readings_r2_08
          group by system,charx,fanqie,rhyme_group having count(*)>1)
    group by 1,2"""):
    verdict = {"PLACEHOLDER_HEAD": "DEFECT_PLACEHOLDER_INFLATES_COUNT",
               "SAME_XIAOYUN_MULTI_ENTRY": "ACCEPTABLE_MULTI_ENTRY",
               "SAME_CHAR_SAME_GROUP": "ACCEPTABLE_DISTINCT_READING"}[r["k"]]
    dup.append((r["system"], r["k"], r["g"], r["e"], verdict,
                "同一字同一韻部出現多條；若無反切區分則屬重複計數"))
con.executemany("INSERT INTO ph_dup_analysis_r2_09 VALUES(?,?,?,?,?,?)", dup)

# ---------- 4. 誠實視圖 ----------
con.execute("DROP VIEW IF EXISTS v_ph_records_r2_09")
con.execute("""
CREATE VIEW v_ph_records_r2_09 as
select r.id, r.system,
       case r.system when 'middle_chinese' then '中古音'
            when 'regulated_verse' then '近體詩韻' when 'ci_rhyme' then '詞韻'
            when 'modern_rhyme' then '現代詩韻' else r.system end system_cn,
       r.charx, r.rhyme_group, r.tone, r.fanqie, r.source_book, r.volume,
       r.evidence_level old_evidence_level, m.new_evidence_level,
       case when r.charx like '%□%' then 1 else 0 end is_placeholder,
       case when r.reading is null then 'NO_PHONETIC_VALUE' else 'HAS_READING' end reading_state,
       case when m.new_evidence_level in ('COMPUTED','INFERRED') then 1 else 0 end is_derived
from ph_readings_r2_08 r left join ph_evidence_map_r2_09 m
  on m.old_evidence_level=r.evidence_level""")
con.commit()

# ---------- 5. 匯出 ----------
with open(os.path.join(OUT, "EVIDENCE_MAP.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["old_evidence_level", "new_evidence_level", "source_type",
                "traceable_to_page", "rows", "note"])
    for m in MAP:
        n = con.execute("select count(*) from ph_readings_r2_08 where evidence_level=?",
                        (m[0],)).fetchone()[0]
        w.writerow(list(m) + [n, m[4]])

with open(os.path.join(OUT, "READING_STATS.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["system", "rows_total", "placeholder", "null_reading", "fanqie",
                "initial", "final", "page", "distinct_chars", "distinct_groups",
                "tones", "evidence_levels", "note"])
    w.writerows(rows)

print("evidence map:", con.execute("select count(*) from ph_evidence_map_r2_09").fetchone()[0])
print("stats:", con.execute("select count(*) from ph_reading_stats_r2_09").fetchone()[0])
print("dup:", con.execute("select count(*) from ph_dup_analysis_r2_09").fetchone()[0])
for r in con.execute("select * from ph_dup_analysis_r2_09"):
    print("  ", tuple(r))
print("view rows:", con.execute("select count(*) from v_ph_records_r2_09").fetchone()[0])
for r in con.execute("select new_evidence_level,count(*) from v_ph_records_r2_09 group by 1 order by 2 desc"):
    print("  ", tuple(r))
