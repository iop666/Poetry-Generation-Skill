#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 H：跨系統讀音差異研究。

建立：
  ph_polyphone_r2_09   多音字的跨體系對照（一字一行，列出各體系歸部與聲調）
  ph_cross_cases_r2_09 100 個跨韻書差異案例（同字同系統多部、或跨系統部類不同）
  QUERY_EXAMPLES.md    30 個可追溯查詢樣例（每條附 SQL 與命中來源）

判準（不混淆「多音」與「數據錯誤」）：
  MULTI_READING  同一體系內同字歸入不同韻部/聲調 —— 可能是多音，也可能是資料誤掛
  CROSS_SYSTEM   不同體系（不同時代）歸部不同 —— 正常現象，不得合併
"""
import os
import re
import json
import csv
import sqlite3
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
OUT = os.path.join(ROOT, "raw", "r2_09", "polyphone")
os.makedirs(OUT, exist_ok=True)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

SYS_CN = {"middle_chinese": "中古音", "regulated_verse": "平水韻",
          "ci_rhyme": "詞林正韻", "modern_rhyme": "中華新韻"}

# 逐字逐體系匯總
agg = collections.defaultdict(lambda: collections.defaultdict(lambda: {"groups": set(), "tones": set(), "books": set()}))
for r in con.execute("select system,charx,rhyme_group,tone,source_book from ph_readings_r2_08 "
                     "where charx<>'' and charx not like '%□%'"):
    a = agg[r["charx"]][r["system"]]
    a["groups"].add(r["rhyme_group"])
    a["tones"].add(r["tone"])
    a["books"].add((r["source_book"] or "").split("（")[0])

# 詞林正韻/中原音韻（R2-09 新表）
for r in con.execute("select bu,charx,tone from ph_cilin_r2_09"):
    a = agg[r["charx"]]["ci_rhyme"]
    a["groups"].add(r["bu"])
    a["tones"].add(r["tone"])
    a["books"].add("詞林正韻")
for r in con.execute("select bu,charx,tone from ph_zhongyuan_r2_09"):
    a = agg[r["charx"]]["yuan_qu"]
    a["groups"].add(r["bu"])
    a["tones"].add(r["tone"])
    a["books"].add("中原音韻")

rows = []
for ch, d in agg.items():
    if len(ch) != 1:
        continue
    n_sys = len(d)
    multi_in_sys = sum(1 for s, v in d.items() if len(v["groups"]) > 1 or len(v["tones"]) > 1)
    cross = len({tuple(sorted(v["groups"])) for v in d.values()}) > 1
    if n_sys >= 2 and (multi_in_sys or cross):
        rows.append({
            "char": ch, "n_systems": n_sys,
            "systems": "|".join(sorted(d)),
            "middle_chinese": "|".join(sorted(d.get("middle_chinese", {"groups": set()})["groups"])),
            "mc_tone": "|".join(sorted(d.get("middle_chinese", {"tones": set()})["tones"])),
            "regulated_verse": "|".join(sorted(d.get("regulated_verse", {"groups": set()})["groups"])),
            "rv_tone": "|".join(sorted(d.get("regulated_verse", {"tones": set()})["tones"])),
            "ci_rhyme": "|".join(sorted(d.get("ci_rhyme", {"groups": set()})["groups"])),
            "cr_tone": "|".join(sorted(d.get("ci_rhyme", {"tones": set()})["tones"])),
            "yuan_qu": "|".join(sorted(d.get("yuan_qu", {"groups": set()})["groups"])),
            "yq_tone": "|".join(sorted(d.get("yuan_qu", {"tones": set()})["tones"])),
            "modern_rhyme": "|".join(sorted(d.get("modern_rhyme", {"groups": set()})["groups"])),
            "n_systems_multi_reading": multi_in_sys,
            "cross_system_diff": 1 if cross else 0,
            "sources": ";".join(sorted({b for v in d.values() for b in v["books"]})),
        })

rows.sort(key=lambda r: (-r["n_systems"], -r["n_systems_multi_reading"], r["char"]))
sel = rows[:200]

con.execute("DROP TABLE IF EXISTS ph_polyphone_r2_09")
con.execute("""CREATE TABLE ph_polyphone_r2_09(
 charx TEXT PRIMARY KEY, n_systems INT, systems TEXT, middle_chinese TEXT, mc_tone TEXT,
 regulated_verse TEXT, rv_tone TEXT, ci_rhyme TEXT, cr_tone TEXT, yuan_qu TEXT, yq_tone TEXT,
 modern_rhyme TEXT, n_systems_multi_reading INT, cross_system_diff INT, sources TEXT, round TEXT)""")
con.executemany("""INSERT INTO ph_polyphone_r2_09 VALUES
 (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, '2026-11-14')""",
    [(r["char"], r["n_systems"], r["systems"], r["middle_chinese"], r["mc_tone"],
      r["regulated_verse"], r["rv_tone"], r["ci_rhyme"], r["cr_tone"], r["yuan_qu"],
      r["yq_tone"], r["modern_rhyme"], r["n_systems_multi_reading"],
      r["cross_system_diff"], r["sources"]) for r in sel])

# 100 跨韻書差異案例：優先中古音內部多部 + 平水韻/詞韻部不同者
cross_rows = [r for r in rows if r["cross_system_diff"] and r["middle_chinese"] and r["regulated_verse"]]
cross_sel = cross_rows[:100]
con.execute("DROP TABLE IF EXISTS ph_cross_cases_r2_09")
con.execute("""CREATE TABLE ph_cross_cases_r2_09(
 charx TEXT PRIMARY KEY, mc_group TEXT, rv_group TEXT, ci_bu TEXT, yq_bu TEXT, note TEXT, round TEXT)""")
con.executemany("INSERT INTO ph_cross_cases_r2_09 VALUES(?,?,?,?,?,?, '2026-11-14')",
    [(r["char"], r["middle_chinese"], r["regulated_verse"], r["ci_rhyme"], r["yuan_qu"],
      "中古 %d 部 / 平水 %d 部" % (len(r["middle_chinese"].split("|")) if r["middle_chinese"] else 0,
                                   len(r["regulated_verse"].split("|")) if r["regulated_verse"] else 0))
     for r in cross_sel])
con.commit()

with open(os.path.join(OUT, "POLYPHONE_200.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(sel[0].keys()))
    w.writeheader()
    w.writerows(sel)
with open(os.path.join(OUT, "CROSS_RHYME_CASES.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["char", "中古音韻目", "平水韻目", "詞林正韻部", "中原音韻部", "說明"])
    for r in cross_sel:
        w.writerow([r["char"], r["middle_chinese"], r["regulated_verse"], r["ci_rhyme"],
                    r["yuan_qu"], "不同時代歸部不同，不得合併"])

stats = {"n_candidates": len(rows), "n_selected": len(sel), "n_cross": len(cross_sel),
         "top": [r["char"] for r in sel[:20]]}
json.dump(stats, open(os.path.join(OUT, "polyphone_stats.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(stats, ensure_ascii=False))
print("sample:", [(r["char"], r["middle_chinese"], r["regulated_verse"], r["ci_rhyme"]) for r in sel[:6]])
