#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-10 報告生成：把已有原始證據整理成報告目錄要求的檔名，並算出全部數字。

原則：任何沒有實際完成的項目，輸出「NOT_PERFORMED + 原因」，不寫空白檔、不編造資料。
"""
import collections
import csv
import glob
import hashlib
import json
import os
import re
import shutil
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
REP = os.path.join(ROOT, "reports", "tasks", "2026-11-15", "R2-10")
R10 = os.path.join(ROOT, "raw", "r2_10")
os.makedirs(REP, exist_ok=True)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row


def q(sql, args=()):
    r = con.execute(sql, args).fetchone()
    return r[0] if r else None


def rows(sql, args=()):
    return [dict(x) for x in con.execute(sql, args).fetchall()]


def wr(path, text):
    with open(os.path.join(REP, path), "w", encoding="utf-8") as f:
        f.write(text)


def wcsv(path, cols, data):
    with open(os.path.join(REP, path), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in data:
            w.writerow(r)


def cp(src, dst):
    s = os.path.join(ROOT, src)
    if os.path.exists(s):
        shutil.copy(s, os.path.join(REP, dst))
        return True
    return False


# ============ 事實匯總 ============
F = {}
st = json.load(open(os.path.join(R10, "preflight", "state.json"), encoding="utf-8"))
F["db_bytes"] = st["db_bytes"]
F["db_mib"] = st["db_mib"]
F["db_sha256"] = st["db_sha256"]
F["n_tables"] = st["n_tables"]
F["n_views"] = st["n_views"]
F["n_indexes"] = st["n_indexes"]
F["disk"] = st["disk_avail_gib"]
F["integrity"] = st["pragma"]["integrity_check"][0]
F["page_count"] = st["pragma"]["page_count"]
F["page_size"] = st["pragma"]["page_size"]

gy = json.load(open(os.path.join(R10, "guangyun", "rebuild_stats.json"), encoding="utf-8"))
F["gy_bound"] = gy["n_boundaries_found"]
F["gy_missing"] = gy["n_rhymes_missing_marker"]
F["gy_missing_list"] = gy["missing_marker"]
F["gy_heads"] = gy["n_xiaoyun_heads"]
F["gy_changed"] = gy["xiaoyun_yun_changed"]
F["gy_same"] = gy["xiaoyun_yun_same"]
F["gy_unres"] = gy["xiaoyun_unresolved"]
F["gy_unres_span"] = gy.get("xiaoyun_unresolved_span", 0)
F["gy_seg"] = gy["n_misattach_segments"]
F["gy_seg5"] = gy["n_misattach_segments_ge5"]
F["gy_fq"] = gy["fanqie_comparison"]
F["gy_strict"] = q("SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE head_kind='STRICT_HEAD'")
F["gy_youyin"] = q("SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE head_kind='YOUYIN_ENTRY'")
F["gy_nofq"] = q("SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE head_kind='NO_FANQIE'")

jy = json.load(open(os.path.join(R10, "jiyun", "jiyun_stats.json"), encoding="utf-8"))
F["jy_revid"] = jy["n_with_revid"]
F["jy_djvu"] = jy["n_with_djvu_locator"]
F["jy_marks"] = jy["sum_xiaoyun_marks"]
F["jy_stored"] = jy["stored_xiaoyun"]
F["jy_allwen"] = jy["sum_all_wen"]
F["jy_decl"] = jy["stored_declared"]
F["jy_est"] = jy["stored_est"]
F["jy_review120"] = jy["review120"]
jf = json.load(open(os.path.join(R10, "jiyun", "jiyun_fanqie_fix.json"), encoding="utf-8"))
F["jy_fq"] = jf["jiyun_fanqie_kinds"]
F["jy_upper_wrong"] = jf["jiyun_fanqie_kinds"].get("OLD_UPPER_WRONG", 0)

sy = json.load(open(os.path.join(R10, "symbols", "symbol_stats.json"), encoding="utf-8"))
F["sym"] = sy["counts"]
F["sym_n"] = sy["n"]

sm = json.load(open(os.path.join(R10, "semantics", "semantics.json"), encoding="utf-8"))
F["sem_total"] = sm["total_rows"]
F["sem_types"] = {x["data_type"]: x for x in sm["by_data_type"]}
F["sem_fill"] = sm["field_fill"]

bs = json.load(open(os.path.join(R10, "books", "six_systems.json"), encoding="utf-8"))
F["systems"] = bs["systems"]

qq = json.load(open(os.path.join(R10, "query", "query_stats.json"), encoding="utf-8"))
F["q_ok"] = qq["n_ok"]
F["q_n"] = len(qq["queries"])

tr = json.load(open(os.path.join(R10, "independent", "test_results_r2_10.json"), encoding="utf-8"))
F["test_n"] = len(tr)
F["test_pass"] = sum(1 for x in tr if x["result"] == "PASS")
F["test_fail"] = [x for x in tr if x["result"] == "FAIL"]

# 閱讀審查
g1 = list(csv.DictReader(open(os.path.join(R10, "reading", "READING_PARTIAL_FAIL_CLOSURE.csv"), encoding="utf-8-sig")))
F["g1_n"] = len(g1)
F["g1_fixed"] = sum(1 for r in g1 if r["new_status"] == "FIXED")
F["g1_undec"] = sum(1 for r in g1 if r["new_status"] == "UNDECIDABLE")
g2 = list(csv.DictReader(open(os.path.join(R10, "reading", "READING_NEW_60_SAMPLE_AUDIT.csv"), encoding="utf-8-sig")))
F["g2_n"] = len(g2)
F["g2"] = dict(collections.Counter(r["verdict"] for r in g2))

# 例詞
F["link"] = dict((r["new_match_kind"], r["n"]) for r in rows(
    "SELECT new_match_kind, count(*) n FROM example_work_links_r2_09 GROUP BY 1"))

# 上古音
an = list(csv.DictReader(open(os.path.join(R10, "ancient", "SHIJING_30_CASES_R2_10.csv"), encoding="utf-8-sig")))
anc = list(csv.DictReader(open(os.path.join(R10, "ancient", "CHUCI_10_CASES_R2_10.csv"), encoding="utf-8-sig")))
F["an_n"] = len(an) + len(anc)
F["an_status"] = dict(collections.Counter([r.get("case_status", "") for r in an + anc]))

# 獨立複核
ind = list(csv.DictReader(open(os.path.join(R10, "independent", "INDEPENDENT_REVIEW_R2_10_part.csv"), encoding="utf-8-sig")))
F["ind_n"] = len(ind)
F["ind_agree"] = sum(1 for r in ind if r["agreement"] == "AGREE")
F["ind_dis"] = sum(1 for r in ind if r["agreement"] == "DISAGREE")
F["ind_by_cat"] = dict(collections.Counter(r["category"] for r in ind))

json.dump(F, open(os.path.join(R10, "facts.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1, default=str)
print(json.dumps({k: F[k] for k in ["gy_bound", "gy_heads", "gy_changed", "gy_unres",
                                    "jy_marks", "jy_stored", "sym", "test_n", "test_pass",
                                    "ind_n", "ind_agree", "ind_dis", "g2_n"]},
                 ensure_ascii=False, indent=1, default=str))
con.close()
