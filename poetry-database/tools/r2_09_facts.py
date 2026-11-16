#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09：匯總全部可復算數字，供報告引用（避免報告數字與資料庫不一致）。"""
import os
import re
import json
import glob
import csv
import sqlite3
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
R9 = os.path.join(ROOT, "raw", "r2_09")
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
F = {}


def q(s, *a):
    return con.execute(s, a).fetchone()[0]


F["db_size_bytes"] = os.path.getsize(DB)
F["tables_r2_07_r2_08"] = q("select count(*) from sqlite_master where type='table' and (name like '%r2_07%' or name like '%r2_08%')")
F["tables_r2_09"] = q("select count(*) from sqlite_master where type='table' and name like '%r2_09%'")
F["views_r2_09"] = q("select count(*) from sqlite_master where type='view'")
F["r209_table_names"] = [r[0] for r in con.execute(
    "select name from sqlite_master where type='table' and name like '%r2_09%' order by name")]

F["works"] = q("select count(*) from works")
F["forms"] = q("select count(*) from cipai_forms_r2_07")
F["entities"] = q("select count(*) from cipai_entities_r2_07")

# 韻書
F["readings"] = q("select count(*) from ph_readings_r2_08")
F["evidence_new"] = {r[0]: r[1] for r in con.execute(
    "select new_evidence_level,count(*) from v_ph_records_r2_09 group by 1")}
F["placeholder_rows"] = q("select count(*) from ph_readings_r2_08 where charx like '%□%'")
F["null_reading"] = q("select count(*) from ph_readings_r2_08 where reading is null")
F["jiyun_pages_ok"] = sum(1 for f in glob.glob(os.path.join(ROOT, "raw", "r2_08", "jiyun_pages", "*.json"))
                          if json.load(open(f))["status"] == "OK")
F["jiyun_xiaoyun"] = q("select count(*) from ph_jiyun_r2_09")
F["jiyun_yun"] = q("select count(distinct yun) from ph_jiyun_r2_09")
F["jiyun_fanqie"] = q("select count(*) from ph_jiyun_r2_09 where fanqie<>''")
F["jiyun_declared"] = q("select sum(declared_chars) from ph_jiyun_r2_09")
F["jiyun_heads_est"] = q("select sum(n_heads_est) from ph_jiyun_r2_09")
F["guangyun_rows"] = q("select count(*) from ph_readings_r2_08 where source_book like '廣韻%'")
F["pingshui_rows"] = q("select count(*) from ph_readings_r2_08 where system='regulated_verse'")
F["pingshui_chars"] = q("select count(distinct charx) from ph_readings_r2_08 where system='regulated_verse'")
F["cilin_rows"] = q("select count(*) from ph_cilin_r2_09")
F["cilin_chars"] = q("select count(distinct charx) from ph_cilin_r2_09")
F["cilin_bu"] = q("select count(distinct bu) from ph_cilin_r2_09")
F["cilin_yunmu"] = q("select count(distinct yunmu) from ph_cilin_r2_09")
F["cilin_half"] = q("select count(*) from ph_cilin_r2_09 where is_half=1")
F["cilin_half_yunmu"] = q("select count(distinct yunmu_name) from ph_cilin_r2_09 where is_half=1")
F["zy_rows"] = q("select count(*) from ph_zhongyuan_r2_09")
F["zy_chars"] = q("select count(distinct charx) from ph_zhongyuan_r2_09")
F["zy_bu"] = q("select count(distinct bu) from ph_zhongyuan_r2_09")
F["zy_tone"] = {r[0]: r[1] for r in con.execute("select tone,count(*) from ph_zhongyuan_r2_09 group by 1")}
F["modern_rows"] = q("select count(*) from ph_modern_audit_r2_09")
cov = json.load(open(os.path.join(R9, "audit", "rhyme_coverage.json")))
F["coverage"] = cov

# 詞格
F["conflicts"] = q("select count(*) from cipai_rhyme_dual_r2_08 where classification_conflict=1")
F["conflict_verdicts"] = {r[0]: r[1] for r in con.execute(
    "select verdict,count(*) from cipai_conflict_verdict_r2_09 group by 1")}
F["brand_level"] = q("select count(*) from cipai_rhyme_fields_r2_09 where source_rhyme_label_scope='BRAND_LEVEL'")
F["example_observed"] = q("select count(*) from cipai_rhyme_fields_r2_09 where example_observed_rhyme_behavior is not null")
F["verified_forms"] = q("select count(*) from cipai_forms_r2_07 where review_status='VERIFIED'")
wc = list(con.execute("select cipai_name,form_seq,declared_num,scoreline_symbols,example_chars "
                      "from cipai_wordcount_r2_09 order by form_id"))
F["wordcount"] = [dict(r) for r in wc]

# 原圖
F["image_coverage"] = json.load(open(os.path.join(R9, "audit", "image_coverage.json")))
iv = list(csv.DictReader(open(os.path.join(R9, "images", "image_verify.csv"), encoding="utf-8-sig")))
F["image_this_round"] = collections.Counter(r["verdict"] for r in iv)
F["image_this_round"] = dict(F["image_this_round"])
F["image_n_this_round"] = len(iv)

# 例詞
F["examples"] = q("select count(*) from cipai_form_examples_r2_08")
F["link_new"] = {r[0]: r[1] for r in con.execute(
    "select new_match_kind,count(*) from example_work_links_r2_09 group by 1")}
F["link_old"] = {r[0]: r[1] for r in con.execute(
    "select match_kind,count(*) from example_work_links_r2_08 group by 1")}

# 閱讀
F["reading_records"] = 907
F["page_kinds"] = json.load(open(os.path.join(R9, "reading", "page_coverage_r2_09.json")))["kinds"]
F["page_unexplained"] = json.load(open(os.path.join(R9, "reading", "page_coverage_r2_09.json")))["n_unexplained"]
rd = []
for f in glob.glob(os.path.join(R9, "reading", "audit_batch_*.csv")):
    rd += list(csv.DictReader(open(f, encoding="utf-8-sig")))
F["reading_audit"] = dict(collections.Counter(r["verdict"] for r in rd))
F["reading_severity"] = dict(collections.Counter(r["severity"] for r in rd))
F["reading_issue"] = dict(collections.Counter(r["issue_type"] for r in rd))
F["schwa"] = json.load(open(os.path.join(R9, "reading", "schwa_review_stats.json")))

# 跨系統
F["polyphone"] = q("select count(*) from ph_polyphone_r2_09")
F["cross_cases"] = q("select count(*) from ph_cross_cases_r2_09")

# 測試
tr = json.load(open(os.path.join(ROOT, "reports", "tasks", "2026-11-14", "R2-09", "test_results.json")))
F["tests"] = len(tr)
F["tests_pass"] = sum(1 for x in tr if x["result"] == "PASS")
F["tests_fail"] = [x["id"] + ":" + x["desc"] for x in tr if x["result"] == "FAIL"]

os.makedirs(os.path.join(ROOT, "raw", "r2_09", "audit"), exist_ok=True)
json.dump(F, open(os.path.join(ROOT, "raw", "r2_09", "audit", "facts.json"), "w"),
          ensure_ascii=False, indent=1, default=str)
print(json.dumps({k: v for k, v in F.items() if not isinstance(v, (list, dict))}, ensure_ascii=False, indent=1))
print("max keys ok")
