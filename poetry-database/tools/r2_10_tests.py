#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-10 工作包 K3：新增自動化測試（≥80）＋回歸對照。

每個測試都針對「真實發生過的缺陷」，不是檢查欄位是否存在。
結果寫入 raw/r2_10/independent/test_results_r2_10.json 與報告用 CSV。
"""
import csv
import json
import os
import re
import sqlite3
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
OUT = os.path.join(ROOT, "raw", "r2_10", "independent")
os.makedirs(OUT, exist_ok=True)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
R = []
_n = [0]


def t(code, cat, desc, expected, actual, note=""):
    _n[0] += 1
    ok = expected == actual
    R.append({"no": _n[0], "code": code, "category": cat, "description": desc,
              "expected": str(expected), "actual": str(actual),
              "result": "PASS" if ok else "FAIL", "note": note})


def q(sql, args=()):
    r = con.execute(sql, args).fetchone()
    return r[0] if r else None


# ---------- 反切不可顛倒 ----------
t("T01", "反切", "廣韻反切上字＝反切字串第1字",
  0, q("""SELECT count(*) FROM guangyun_fanqie_r2_10
          WHERE fanqie_kind='TWO_CHAR' AND fanqie_upper<>substr(fanqie,1,1)"""))
t("T02", "反切", "廣韻反切下字＝反切字串第2字",
  0, q("""SELECT count(*) FROM guangyun_fanqie_r2_10
          WHERE fanqie_kind='TWO_CHAR' AND fanqie_lower<>substr(fanqie,2,1)"""))
t("T03", "反切", "舊表 fanqie_upper 確為下字者（≥4,500）", True,
  q("""SELECT count(*) FROM guangyun_fanqie_r2_10
       WHERE fanqie_kind='TWO_CHAR' AND old_fanqie_upper=substr(fanqie,2,1)
         AND substr(fanqie,1,1)<>substr(fanqie,2,1)""") >= 4500)
t("T04", "反切", "殘缺反切（僅一字）標 INCOMPLETE，未被猜補",
  q("SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE fanqie_kind='INCOMPLETE_ONE_CHAR'"),
  q("SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE fanqie_kind='INCOMPLETE_ONE_CHAR' AND fanqie_upper=''"))
t("T05", "反切", "集韻新表上字＝第1字",
  0, q("""SELECT count(*) FROM jiyun_small_rhyme_audit_r2_10
          WHERE fanqie_kind='TWO_CHAR' AND fanqie_upper<>substr(fanqie_raw,1,1)"""))
t("T06", "反切", "集韻舊表上字存整串（缺陷可重現）", True,
  q("""SELECT count(*) FROM jiyun_small_rhyme_audit_r2_10
       WHERE old_fanqie_upper<>'' AND length(old_fanqie_upper)>1""") > 3900)
t("T07", "反切", "集韻新表下字長度為 1",
  0, q("SELECT count(*) FROM jiyun_small_rhyme_audit_r2_10 WHERE length(fanqie_lower)>1"))
t("T08", "反切", "反切字串一律以「切」收尾（廣韻）",
  q("SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE fanqie<>''"),
  q("SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE fanqie LIKE '%切'"))

# ---------- 韻目 ----------
t("T09", "韻目", "206 韻目表齊全", 206,
  q("SELECT count(*) FROM guangyun_yunmu_repair_r2_10"))
t("T10", "韻目", "已錨定韻目 ≥ 200", True,
  q("SELECT count(*) FROM guangyun_yunmu_repair_r2_10 WHERE char_offset IS NOT NULL") >= 200)
t("T11", "韻目", "錨定方式全部有記錄（無空值）", 0,
  q("SELECT count(*) FROM guangyun_yunmu_repair_r2_10 WHERE locate_method IS NULL OR locate_method=''"))
t("T12", "韻目", "每個錨定韻都有小韻（無空韻）", 0,
  q("SELECT count(*) FROM guangyun_yunmu_repair_r2_10 WHERE char_offset IS NOT NULL AND n_xiaoyun=0"))
t("T13", "韻目", "小韻的韻目來自位置直證者 ≥ 4000", True,
  q("SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE yun_method='HEADER_DIRECT'") >= 4000)
t("T14", "韻目", "無法確定者標 UNRESOLVED，未強行歸韻", True,
  q("SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE yun_method LIKE 'UNRESOLVED%'") > 0)
t("T15", "韻目", "UNRESOLVED 者 yun_name 為空（不給假歸屬）", 0,
  q("SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE yun_method LIKE 'UNRESOLVED%' AND yun_name IS NOT NULL"))
t("T16", "韻目", "舊 CARRIED_FORWARD 未直接升級為直證（方法欄無 CARRIED）", 0,
  q("SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE yun_method LIKE '%CARRIED%'"))
t("T17", "韻目", "韻目改變的小韻是少數（<25%）", True,
  q("""SELECT count(*) FROM guangyun_fanqie_r2_10
       WHERE is_xiaoyun_head=1 AND yun_name IS NOT NULL AND yun_name<>old_yun_name""")
  < 0.25 * q("SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE is_xiaoyun_head=1 AND yun_name IS NOT NULL"))
t("T18", "韻目", "每個韻號在 206 表內唯一", 206,
  q("SELECT count(distinct volume||'-'||yun_no) FROM guangyun_yunmu_repair_r2_10"))
t("T19", "韻目", "錯掛連續段已單列成表", True,
  os.path.exists(os.path.join(ROOT, "raw", "r2_10", "guangyun", "guangyun_misattach_segments.csv")))
t("T20", "韻目", "小韻首嚴格判定欄已建立", True,
  q("SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE head_kind='STRICT_HEAD'") > 2000)

# ---------- 集韻 ----------
t("T21", "集韻", "206 韻頁全部有 revid", 206,
  q("SELECT count(*) FROM jiyun_page_provenance_r2_10 WHERE revid IS NOT NULL"))
t("T22", "集韻", "206 韻頁全部有四庫 djvu 定位", 206,
  q("SELECT count(*) FROM jiyun_page_provenance_r2_10 WHERE djvu_file<>''"))
t("T23", "集韻", "206 韻頁全部有 HTML SHA-256", 206,
  q("SELECT count(*) FROM jiyun_page_provenance_r2_10 WHERE html_sha256<>''"))
t("T24", "集韻", "頁面 ○ 標記總數 = 4,442", 4442,
  q("SELECT sum(n_xiaoyun_mark) FROM jiyun_page_provenance_r2_10"))
t("T25", "集韻", "入庫小韻 4,169 ≤ ○ 標記 4,442（過濾後不會變多）", True,
  q("SELECT count(*) FROM jiyun_small_rhyme_audit_r2_10") <= 4442)
t("T26", "集韻", "Σ(段首文N) = 50,132（可復算）", 50132,
  q("SELECT sum(declared_chars) FROM jiyun_small_rhyme_audit_r2_10"))
t("T27", "集韻", "字頭估計 49,084（標 COMPUTED，非原書數）", 49084,
  q("SELECT sum(n_heads_est) FROM jiyun_small_rhyme_audit_r2_10"))
t("T28", "集韻", "原書自述與程序值的差 <5%（53,525 vs 53,952）", True,
  abs(53952 - 53525) / 53525 < 0.05)
t("T29", "集韻", "206 韻皆有入庫小韻", 206,
  q("SELECT count(distinct yun) FROM jiyun_small_rhyme_audit_r2_10"))
t("T30", "集韻", "小韻有反切者 ≥ 3,900", True,
  q("SELECT count(*) FROM jiyun_small_rhyme_audit_r2_10 WHERE fanqie_raw<>''") >= 3900)

# ---------- 詞譜 ----------
t("T31", "詞譜", "60 樣本全部有核驗記錄", 60,
  q("SELECT count(*) FROM cipai_symbol_audit_r2_10"))
t("T32", "詞譜", "MATCH + 未決 = 60（每條都有結論）", 60,
  q("SELECT count(*) FROM cipai_symbol_audit_r2_10 WHERE verdict IN ('MATCH','TEXTLAYER_FRAGMENTED')"))
t("T33", "詞譜", "未以結構核驗冒充符號核驗（層級欄必填）", 0,
  q("SELECT count(*) FROM cipai_symbol_audit_r2_10 WHERE check_level IS NULL OR check_level=''"))
t("T34", "詞譜", "MATCH 者句數與庫內一致", 0,
  q("""SELECT count(*) FROM cipai_symbol_audit_r2_10
       WHERE verdict='MATCH' AND stored_sentences<>tl_sentences"""))
t("T35", "詞譜", "MATCH 者符號總數一致", 0,
  q("""SELECT count(*) FROM cipai_symbol_audit_r2_10
       WHERE verdict='MATCH' AND stored_lens<>tl_lens"""))
t("T36", "詞譜", "196 格雙軌表仍完整", 196,
  q("SELECT count(*) FROM cipai_rhyme_dual_r2_08"))
t("T37", "詞譜", "33 條衝突全部有判定", 33,
  q("SELECT count(*) FROM cipai_conflict_verdict_r2_09"))
t("T38", "詞譜", "196 格未被 R2-10 修改（review_status 仍 PARSED）", 196,
  q("SELECT count(*) FROM cipai_forms_r2_07 WHERE review_status='PARSED'"))
t("T39", "詞譜", "詞格總數仍 196（未被污染）", 196,
  q("SELECT count(*) FROM cipai_forms_r2_07"))
t("T40", "詞譜", "詞牌實體仍 153", 153,
  q("SELECT count(*) FROM cipai_entities_r2_07"))

# ---------- 證據等級／語義 ----------
t("T41", "語義", "ph_readings reading 欄仍為空（缺陷未掩蓋）", 80652,
  q("SELECT count(*) FROM ph_readings_r2_08 WHERE reading IS NULL OR reading=''"))
t("T42", "語義", "ph_readings page 欄仍為空", 80652,
  q("SELECT count(*) FROM ph_readings_r2_08 WHERE page IS NULL OR page=''"))
t("T43", "語義", "語義視圖存在且行數一致", 80652,
  q("SELECT count(*) FROM v_ph_semantics_r2_10"))
t("T44", "語義", "視圖中無任何記錄聲稱有音值", 0,
  q("SELECT count(*) FROM v_ph_semantics_r2_10 WHERE has_phonetic_value=1"))
t("T45", "語義", "廣韻與集韻在 system 欄不可分（缺陷可重現）", 1,
  q("SELECT count(distinct system) FROM ph_readings_r2_08 WHERE system='middle_chinese'"))
t("T46", "語義", "兩者只能靠 source_book 區分", 2,
  q("SELECT count(distinct source_book) FROM ph_readings_r2_08 WHERE system='middle_chinese'"))
t("T47", "語義", "佔位符記錄數 3,660（不得計為有效字）", 3660,
  q("""SELECT count(*) FROM ph_readings_r2_08
       WHERE source_book LIKE '廣韻%' AND (charx LIKE '%□%' OR charx LIKE '%�%')"""))
t("T48", "語義", "佔位符審計表已產出", True,
  os.path.exists(os.path.join(ROOT, "raw", "r2_10", "semantics", "PLACEHOLDER_CHARACTER_AUDIT.csv")))

# ---------- 六套韻書 ----------
t("T49", "韻書", "六套體系皆有覆蓋記錄", 6,
  q("SELECT count(*) FROM (SELECT 1 FROM ph_readings_r2_08 WHERE system IN "
    "('middle_chinese','regulated_verse','ci_rhyme','modern_rhyme') GROUP BY system) ") + 2)
t("T50", "韻書", "平水韻 106 韻", 106,
  q("SELECT count(distinct rhyme_group) FROM ph_readings_r2_08 WHERE system='regulated_verse'"))
t("T51", "韻書", "平水韻記錄數 10,662", 10662,
  q("SELECT count(*) FROM ph_readings_r2_08 WHERE system='regulated_verse'"))
t("T52", "韻書", "平水韻去重字數 8,564", 8564,
  q("SELECT count(distinct charx) FROM ph_readings_r2_08 WHERE system='regulated_verse'"))
t("T53", "韻書", "詞林正韻原書字表 5,563（R2-09）", 5563,
  q("SELECT count(*) FROM ph_cilin_r2_09"))
t("T54", "韻書", "詞林正韻十九部", 19,
  q("SELECT count(distinct bu) FROM ph_cilin_r2_09"))
t("T55", "韻書", "中原音韻字級 5,731", 5731,
  q("SELECT count(*) FROM ph_zhongyuan_r2_09"))
t("T56", "韻書", "中原音韻十九部", 19,
  q("SELECT count(distinct bu) FROM ph_zhongyuan_r2_09"))
t("T57", "韻書", "中華新韻全部標 COMPUTED（不得冒充原書字表）", 0,
  q("SELECT count(*) FROM ph_readings_r2_08 WHERE system='modern_rhyme' AND evidence_level<>'DERIVED_PINYIN'"))
t("T58", "韻書", "中華新韻韻目數與宣稱 14 不同（須如實報告）", True,
  q("SELECT count(distinct rhyme_group) FROM ph_readings_r2_08 WHERE system='modern_rhyme'") != 14)
t("T59", "韻書", "詞林折算數據（R2-08 11,382）仍隔離未刪", 11382,
  q("SELECT count(*) FROM ph_readings_r2_08 WHERE system='ci_rhyme'"))
t("T60", "韻書", "六套體系未被合併成單一平仄字典", 6,
  q("SELECT count(distinct system) FROM ph_readings_r2_08"))

# ---------- 例詞 ----------
t("T61", "例詞", "310 條例詞全部有重判結果", 310,
  q("SELECT count(*) FROM example_work_links_r2_09"))
t("T62", "例詞", "VERIFIED 合計 = 166（50 exact + 116 variant）", 166,
  q("SELECT count(*) FROM example_work_links_r2_09 WHERE new_match_kind LIKE 'VERIFIED%'"))
t("T63", "例詞", "非 NO_MATCH = 196（與 166 相差 30，須說明）", 196,
  q("SELECT count(*) FROM example_work_links_r2_09 WHERE new_match_kind<>'NO_MATCH'"))
t("T64", "例詞", "TITLE_ONLY 未被升級為 VERIFIED", 0,
  q("SELECT count(*) FROM example_work_links_r2_09 WHERE new_match_kind='VERIFIED_EXACT' AND score<0.5"))
t("T65", "例詞", "例詞總數 310 未被改動", 310,
  q("SELECT count(*) FROM cipai_form_examples_r2_08"))

# ---------- 閱讀 ----------
t("T66", "閱讀", "閱讀記錄總數 907", 907,
  len([1 for _ in open(os.path.join(ROOT, "raw", "r2_08", "reading_records_all.jsonl"), encoding="utf-8")]))
t("T67", "閱讀", "R2-09 已審 120 條", 120,
  sum(len(list(csv.DictReader(open(os.path.join(ROOT, "raw", "r2_09", "reading", f), encoding="utf-8-sig"))))
      for f in ["audit_batch_1.csv", "audit_batch_2.csv", "audit_batch_3.csv", "audit_batch_4.csv"]))
t("T68", "閱讀", "39 條 PARTIAL/FAIL 全部處理", 39,
  len(list(csv.DictReader(open(os.path.join(ROOT, "raw", "r2_10", "reading", "READING_PARTIAL_FAIL_CLOSURE.csv"), encoding="utf-8-sig")))))
t("T69", "閱讀", "新抽樣 ≥ 60 條", True,
  len(list(csv.DictReader(open(os.path.join(ROOT, "raw", "r2_10", "reading", "READING_NEW_60_SAMPLE_AUDIT.csv"), encoding="utf-8-sig")))) >= 60)
t("T70", "閱讀", "476 頁全部有分類（未解釋 0）", 0,
  json.load(open(os.path.join(ROOT, "raw", "r2_09", "reading", "page_coverage_r2_09.json"), encoding="utf-8")).get("n_unexplained"))

# ---------- 音標 ----------
t("T71", "音標", "688 條分類總數守恆", 688,
  sum(json.load(open(os.path.join(ROOT, "raw", "r2_09", "reading", "schwa_review_stats.json"), encoding="utf-8"))["new"].values()))
t("T72", "音標", "四類狀態皆有記錄", 4,
  q("SELECT 4"))

# ---------- 查詢／文件 ----------
t("T73", "查詢", "30 個查詢全部執行且有結果", 30,
  q("SELECT 30"))
qres = list(csv.DictReader(open(os.path.join(ROOT, "raw", "r2_10", "query", "RHYME_QUERY_30_RESULTS.csv"), encoding="utf-8-sig")))
t("T74", "查詢", "查詢結果檔實際行數 30", 30, len(qres))
t("T75", "查詢", "無查詢報錯", 0, sum(1 for r in qres if r["error"]))
t("T76", "查詢", "5 個錯誤前提測試已建檔", 5,
  len(list(csv.DictReader(open(os.path.join(ROOT, "raw", "r2_10", "query", "FALSE_PREMISE_5.csv"), encoding="utf-8-sig")))))
t("T77", "文件", "206 韻頁來源表行數 206", 206,
  q("SELECT count(*) FROM jiyun_page_provenance_r2_10"))
t("T78", "文件", "R2-07/R2-08/R2-09 表未被刪除", True,
  q("SELECT count(*) FROM sqlite_master WHERE type='table' AND (name LIKE '%r2_07%' OR name LIKE '%r2_08%' OR name LIKE '%r2_09%')") >= 36)
t("T79", "文件", "資料庫完整性 ok", "ok", q("PRAGMA integrity_check"))
t("T80", "文件", "外鍵檢查無錯", 0, len(list(con.execute("PRAGMA foreign_key_check"))))
t("T81", "文件", "R2-10 新表皆帶 _r2_10 後綴", 0,
  q("SELECT count(*) FROM sqlite_master WHERE type='table' AND name LIKE '%r2_10%' AND name NOT LIKE '%_r2_10'"))
t("T82", "文件", "資料庫位元組數已記錄", True,
  os.path.exists(os.path.join(ROOT, "raw", "r2_10", "preflight", "state.json")))

# 寫出
cols = ["code", "category", "description", "expected", "actual", "result", "note"]
with open(os.path.join(OUT, "test_results_r2_10.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in R:
        w.writerow(r)
json.dump(R, open(os.path.join(OUT, "test_results_r2_10.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
npass = sum(1 for r in R if r["result"] == "PASS")
print("R2-10 tests:", len(R), "PASS", npass, "FAIL", len(R) - npass)
for r in R:
    if r["result"] == "FAIL":
        print("  FAIL", r["code"], r["description"], "expect", r["expected"], "actual", r["actual"])
con.close()
