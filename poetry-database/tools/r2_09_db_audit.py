#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 A：R2-08 資料庫結構、關係與證據分級審計。

只讀 poetry.db，不改任何既有表；所有產出寫到 raw/r2_09/audit/。
"""
import os
import sqlite3
import json
import csv
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
OUT = os.path.join(ROOT, "raw", "r2_09", "audit")
os.makedirs(OUT, exist_ok=True)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

R208 = [r[0] for r in con.execute(
    "select name from sqlite_master where type='table' and name like '%r2_07%' "
    "or (type='table' and name like '%r2_08%') order by name")]
R208 = [n for n in R208 if not n.startswith("sqlite_")]


def cols(t):
    return [dict(r) for r in con.execute("PRAGMA table_info(%s)" % t)]


def count(t):
    return con.execute('select count(*) from "%s"' % t).fetchone()[0]


# ---------- 1. 表計數 ----------
rows_out = []
detail = {}
for t in R208:
    n = count(t)
    cl = cols(t)
    pk = [c["name"] for c in cl if c["pk"]]
    nnull = {}
    for c in cl:
        v = con.execute('select count(*) from "%s" where "%s" is null' % (t, c["name"])).fetchone()[0]
        if v:
            nnull[c["name"]] = v
    nchar = con.execute('select sum(length(cast("%s" as text))) from "%s"' % (cl[0]["name"], t)).fetchone()[0] or 0
    rows_out.append({
        "table": t, "rows": n, "n_columns": len(cl),
        "primary_key": ";".join(pk) or "(none)",
        "n_columns_with_null": len(nnull),
        "total_nulls": sum(nnull.values()),
        "declared_char_len_col1": nchar,
        "round_origin": "R2-07" if "r2_07" in t else "R2-08",
    })
    detail[t] = {"rows": n, "columns": [
        {"name": c["name"], "type": c["type"], "pk": bool(c["pk"]),
         "notnull": bool(c["notnull"]), "nulls": nnull.get(c["name"], 0)} for c in cl],
        "null_map": nnull}

with open(os.path.join(OUT, "DATABASE_TABLE_COUNTS.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
    w.writeheader()
    w.writerows(rows_out)

# ---------- 2. 邏輯外鍵審計 ----------
FK = [
    ("cipai_forms_r2_07", "cipai_id", "cipai_entities_r2_07", "entity_id"),
    ("cipai_form_sources_r2_07", "form_id", "cipai_forms_r2_07", "form_id"),
    ("cipai_form_variants_r2_07", "form_id", "cipai_forms_r2_07", "form_id"),
    ("cipai_form_variants_r2_07", "derived_name", "cipai_entities_r2_07", "cipai_name"),
    ("cipai_audit_r2_07", "form_id", "cipai_forms_r2_07", "form_id"),
    ("cipai_audit2_r2_08", "form_id", "cipai_forms_r2_07", "form_id"),
    ("cipai_count_audit_r2_07", "form_id", "cipai_forms_r2_07", "form_id"),
    ("cipai_rhyme_dual_r2_08", "form_id", "cipai_forms_r2_07", "form_id"),
    ("cipai_image_checks_r2_08", "form_id", "cipai_forms_r2_07", "form_id"),
    ("cipai_form_examples_r2_08", "form_id", "cipai_forms_r2_07", "form_id"),
    ("example_work_links_r2_08", "example_id", "cipai_form_examples_r2_08", "example_id"),
    ("example_work_links_r2_08", "work_id", "works", "work_id"),
    ("example_work_links_r2_08", "form_id", "cipai_forms_r2_07", "form_id"),
    ("rhyme_mode_cases_r2_08", "form_id", "cipai_forms_r2_07", "form_id"),
    ("rhyme_mode_cases_r2_08", "example_id", "cipai_form_examples_r2_08", "example_id"),
    ("classical_works_study_r2_08", "work_id", "works", "work_id"),
    ("cipai_source_differences_r2_07", "cipai_name", "cipai_entities_r2_07", "cipai_name"),
    ("cipai_special_cases_r2_07", "cipai_name", "cipai_entities_r2_07", "cipai_name"),
    ("page_map_notes_r2_07", "pdf_page", "page_map_wangli", "pdf_page"),
]
rel_out = []
for ft, fc, tt, tc in FK:
    try:
        n = con.execute('select count(*) from "%s"' % ft).fetchone()[0]
        nnull = con.execute('select count(*) from "%s" where "%s" is null or "%s"=\'\'' % (ft, fc, fc)).fetchone()[0]
        ndist = con.execute('select count(distinct "%s") from "%s"' % (fc, ft)).fetchone()[0]
        orph = con.execute(
            'select count(*) from "%s" a where a."%s" is not null and a."%s"<>\'\' and not exists '
            '(select 1 from "%s" b where b."%s"=a."%s")' % (ft, fc, fc, tt, tc, fc)).fetchone()[0]
        tdistinct = con.execute('select count(distinct "%s") from "%s"' % (tc, tt)).fetchone()[0]
        rel_out.append({"from_table": ft, "from_col": fc, "to_table": tt, "to_col": tc,
                        "from_rows": n, "from_nulls_or_empty": nnull,
                        "from_distinct_values": ndist, "to_distinct_values": tdistinct,
                        "orphan_rows": orph,
                        "status": "OK" if orph == 0 else "ORPHANS"})
    except Exception as e:
        rel_out.append({"from_table": ft, "from_col": fc, "to_table": tt, "to_col": tc,
                        "from_rows": -1, "from_nulls_or_empty": -1, "from_distinct_values": -1,
                        "to_distinct_values": -1, "orphan_rows": -1, "status": "ERROR:" + str(e)[:60]})

with open(os.path.join(OUT, "DATABASE_RELATIONSHIP_AUDIT.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rel_out[0].keys()))
    w.writeheader()
    w.writerows(rel_out)

# ---------- 3. 重複與一致性抽檢 ----------
dups = {}
tests = [
    ("ph_readings_r2_08", "system,charx,reading,rhyme_group,source_book,coalesce(volume,''),coalesce(page,'')"),
    ("ph_readings_r2_08", "system,charx,reading,rhyme_group"),
    ("cipai_form_sources_r2_07", "form_id,line_no"),
    ("cipai_forms_r2_07", "cipai_name,form_seq"),
    ("cipai_form_examples_r2_08", "form_id,example_seq"),
    ("cipai_image_checks_r2_08", "form_id"),
    ("ph_rhyme_groups_r2_08", "system,group_name"),
    ("ph_variants_r2_08", "trad"),
    ("cipai_entities_r2_07", "cipai_name"),
    ("classical_works_study_r2_08", "work_id"),
]
for t, k in tests:
    try:
        n = con.execute('select count(*) from (select %s,count(*) c from "%s" group by %s having c>1)' % (k, t, k)).fetchone()[0]
        extra = con.execute('select coalesce(sum(c-1),0) from (select count(*) c from "%s" group by %s having c>1)' % (t, k)).fetchone()[0]
        dups[t + " | " + k] = {"dup_groups": n, "extra_rows": extra}
    except Exception as e:
        dups[t + " | " + k] = {"error": str(e)[:80]}

# ---------- 4. 一對多與口徑矛盾 ----------
checks = {}
checks["forms_total"] = count("cipai_forms_r2_07")
checks["entities_total"] = count("cipai_entities_r2_07")
checks["forms_whose_cipai_id_missing"] = con.execute(
    "select count(*) from cipai_forms_r2_07 where cipai_id is null or cipai_id=''").fetchone()[0]
checks["sum_n_form_on_entities"] = con.execute(
    "select sum(n_form) from cipai_entities_r2_07").fetchone()[0]
checks["entities_with_multi_form"] = con.execute(
    "select count(*) from cipai_entities_r2_07 where n_form>1").fetchone()[0]
checks["examples_linked"] = con.execute(
    "select count(*) from example_work_links_r2_08 where work_id is not null").fetchone()[0]
checks["dual_conflicts"] = con.execute(
    "select count(*) from cipai_rhyme_dual_r2_08 where classification_conflict=1").fetchone()[0]
checks["dual_verified"] = con.execute(
    "select count(*) from cipai_rhyme_dual_r2_08 where same_rhyme_group_verified=1").fetchone()[0]
checks["forms_verified"] = con.execute(
    "select count(*) from cipai_forms_r2_07 where review_status='VERIFIED'").fetchone()[0]
checks["works_total"] = count("works")

# 平水韻字頭三種口徑
ps_chars = con.execute("select count(*),count(distinct charx) from ph_readings_r2_08 where system='regulated_verse'").fetchone()
checks["pingshui_rows"] = ps_chars[0]
checks["pingshui_distinct_chars"] = ps_chars[1]
checks["pingshui_sum_group_nchars"] = con.execute(
    "select sum(n_chars) from ph_rhyme_groups_r2_08 where system='regulated_verse'").fetchone()[0]

res = {
    "generated": "2026-11-14",
    "db_size_bytes": os.path.getsize(DB),
    "tables_r2_07_r2_08": rows_out,
    "column_detail": detail,
    "relationships": rel_out,
    "duplicates": dups,
    "consistency": checks,
}
json.dump(res, open(os.path.join(OUT, "schema_audit.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("tables:", len(R208))
print("total rows in r2_07/r2_08:", sum(r["rows"] for r in rows_out))
print("orphans:", [(r["from_table"], r["from_col"], r["orphan_rows"]) for r in rel_out if r["orphan_rows"]])
print("dup:", {k: v for k, v in dups.items() if v.get("extra_rows")})
print("consistency:", checks)
