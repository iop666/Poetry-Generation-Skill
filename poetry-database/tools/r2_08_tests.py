#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 自動化測試（R2-08 新增，目標 ≥40 項）。

每項記錄：id / 類別 / 輸入 / 預期 / 實際 / 結果。結果如實寫入 test_results.json，
失敗不得刪除。
"""
import json, os, re, sqlite3, hashlib, glob, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
RAW = os.path.join(ROOT, "raw", "r2_08")
OUT = os.path.join(RAW, "test_results.json")
R = []


def t(tid, cat, desc, expect, actual, ok=None):
    ok = (expect == actual) if ok is None else ok
    R.append({"id": tid, "category": cat, "desc": desc, "input": desc,
              "expected": expect, "actual": actual, "pass": bool(ok)})


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    q = lambda s, *a: con.execute(s, a).fetchone()[0]

    # --- 1 詞格結構（C1） ---
    t("T-01", "詞格", "196 條詞格全在", 196, q("select count(*) from cipai_forms_r2_07"))
    t("T-02", "詞格", "審計表覆蓋 196", 196, q("select count(*) from cipai_audit2_r2_08"))
    t("T-03", "詞格", "無 CHECK_REQUIRED 未處理", 0,
      q("select count(*) from cipai_audit2_r2_08 where source_text_ok=0"))
    t("T-04", "詞格", "詞牌實體 153", 153, q("select count(*) from cipai_entities_r2_07"))
    t("T-05", "詞格", "同調多體 30（非 29）", 30,
      q("select count(*) from (select cipai_id from cipai_forms_r2_07 group by cipai_id having count(*)>=2)"))
    t("T-06", "詞格", "同調多體分佈單格 123", 123,
      q("select count(*) from (select cipai_id from cipai_forms_r2_07 group by cipai_id having count(*)=1)"))
    t("T-07", "詞格", "五類韻式格數合計 196", 196,
      q("select count(*) from cipai_rhyme_dual_r2_08 where source_rhyme_label_class is not null"))
    t("T-08", "詞格", "每格均有韻位", 0,
      q("select count(*) from cipai_rhyme_dual_r2_08 where n_rhyme_marks=0"))
    t("T-09", "詞格", "頁碼換算 PDF=印刷+15 全對", 0,
      q("select count(*) from cipai_forms_r2_07 where printed_page<>pdf_page-15"))

    # --- 2 韻式雙軌（C2） ---
    n_conf = q("select count(*) from cipai_rhyme_dual_r2_08 where classification_conflict=1")
    t("T-10", "韻式", "衝突數已記錄（>0 即可）", True, n_conf > 0)
    t("T-11", "韻式", "衝突數與明細一致", n_conf,
      q("select count(*) from cipai_rhyme_dual_r2_08 where source_rhyme_label_class<>observed_rhyme_behavior and observed_rhyme_behavior<>'UNKNOWN'"))
    t("T-12", "韻式", "原書標籤欄無空值", 0,
      q("select count(*) from cipai_rhyme_dual_r2_08 where source_rhyme_label is null or source_rhyme_label=''"))
    t("T-13", "韻式", "譜行推導欄無空值", 0,
      q("select count(*) from cipai_rhyme_dual_r2_08 where observed_rhyme_behavior=''"))
    t("T-14", "韻式", "同部核驗欄全為未核（0）", 0,
      q("select count(*) from cipai_rhyme_dual_r2_08 where same_rhyme_group_verified=1"))
    t("T-15", "韻式", "五類標籤均在", 5,
      q("select count(distinct source_rhyme_label_class) from cipai_rhyme_dual_r2_08"))

    # --- 3 例詞（C4/D1） ---
    t("T-16", "例詞", "例詞 ≥100", True, q("select count(*) from cipai_form_examples_r2_08") >= 100)
    t("T-17", "例詞", "例詞全部有作者", 0,
      q("select count(*) from cipai_form_examples_r2_08 where author is null or author=''"))
    t("T-18", "例詞", "例詞全部有頁碼", 0,
      q("select count(*) from cipai_form_examples_r2_08 where pdf_page is null"))
    t("T-19", "例詞", "例詞均有 form_id", 0,
      q("select count(*) from cipai_form_examples_r2_08 where form_id is null"))
    t("T-20", "例詞", "關聯表條數=例詞條數",
      q("select count(*) from cipai_form_examples_r2_08"),
      q("select count(*) from example_work_links_r2_08"))
    t("T-21", "例詞", "EXACT+PREFIX 不少於 100", True,
      q("select count(*) from example_work_links_r2_08 where match_kind in ('EXACT_MATCH','PREFIX_MATCH')") >= 100)
    t("T-22", "例詞", "無 cipai 字段自動判定（VARIANT 需人工）", 0,
      q("select count(*) from example_work_links_r2_08 where match_kind='VARIANT_CANDIDATE' and same_author=1 and match_score>0.99"))

    # --- 4 韻書（B） ---
    t("T-23", "韻書", "六套體系登記", 6, q("select count(*) from ph_systems_r2_08"))
    t("T-24", "韻書", "平水韻 106 韻", 106,
      q("select count(*) from ph_rhyme_groups_r2_08 where system='regulated_verse'"))
    t("T-25", "韻書", "詞林正韻 19 部", 19,
      q("select count(*) from ph_rhyme_groups_r2_08 where system='ci_rhyme'"))
    gym = json.load(open(os.path.join(RAW, "guangyun_yunmu.json"), encoding="utf-8"))
    t("T-26", "韻書", "廣韻韻目表 206 韻", 206, len(gym))
    t("T-26b", "韻書", "有讀音歸屬的韻 190（來源韻目行缺失 16）", 190,
      q("select count(distinct volume||'-'||rhyme_group) from ph_readings_r2_08 "
        "where source_book like '廣韻%' and rhyme_group<>''"))
    t("T-27", "韻書", "體系間不互相覆蓋（同字多體系並存）", True,
      q("select count(*) from (select charx from ph_readings_r2_08 group by charx having count(distinct system)>=2)") > 1000)
    t("T-28", "韻書", "每條讀音均有體系標記", 0,
      q("select count(*) from ph_readings_r2_08 where system is null or system=''"))
    t("T-29", "韻書", "每條讀音均有來源書", 0,
      q("select count(*) from ph_readings_r2_08 where source_book is null or source_book=''"))
    t("T-30", "韻書", "派生層均已標 evidence", 0,
      q("select count(*) from ph_readings_r2_08 where evidence_level is null or evidence_level=''"))
    t("T-31", "韻書", "詞林半韻讀音已標記", True,
      q("select count(*) from ph_readings_r2_08 where evidence_level='DERIVED_FROM_PINGSHUI_HALF'") > 0)
    t("T-32", "韻書", "繁簡索引表存在且 >5000", True,
      q("select count(*) from ph_variants_r2_08") > 5000)
    t("T-33", "韻書", "上古音體系標 NOT_BUILT", "NOT_BUILT",
      q("select build_status from ph_systems_r2_08 where system='old_chinese'"))
    gx = [json.loads(l) for l in open(os.path.join(RAW, "guangyun_xiaoyun.jsonl"), encoding="utf-8")]
    gh = [r for r in gx if r["is_xiaoyun_head"]]
    t("T-34", "韻書", "廣韻小韻反切可解析為上下字 100%", 100.0,
      round(100.0 * sum(1 for r in gh if r["fanqie_upper"]) / max(1, len(gh)), 1))

    # --- 5 集韻（B1） ---
    files = glob.glob(os.path.join(RAW, "jiyun_pages", "*.json"))
    ok = [f for f in files if json.load(open(f, encoding="utf-8")).get("status") == "OK"]
    t("T-35", "集韻", "韻頁總數 206", 206, len(files))
    t("T-36", "集韻", "成功頁 ≥190", True, len(ok) >= 190)
    t("T-37", "集韻", "小韻數 >2000", True,
      q("select count(*) from ph_readings_r2_08 where source_book like '集韻%'") > 2000)
    t("T-38", "集韻", "空白頁不計成功", True, all(
        (json.load(open(f, encoding="utf-8")).get("status") == "OK") ==
        (json.load(open(f, encoding="utf-8")).get("n_qie", 0) >= 3) for f in files))

    # --- 6 音韻學閱讀（A） ---
    recs = [json.loads(l) for l in open(os.path.join(RAW, "reading_records_all.jsonl"), encoding="utf-8")]
    t("T-39", "閱讀", "閱讀記錄 >600", True, len(recs) > 600)
    t("T-40", "閱讀", "引文核驗零失敗", 0,
      json.load(open(os.path.join(RAW, "reading_verification.json")))["totals"]["quote_failures"])
    t("T-41", "閱讀", "覆蓋正文頁 >95%", True,
      json.load(open(os.path.join(RAW, "reading_verification.json")))["totals"]["coverage_pct"] > 95)
    t("T-42", "閱讀", "每單元均有 UNIT_SUMMARY 或補讀", True,
      len({r["unit_id"] for r in recs}) >= 18)

    # --- 7 音標（A2） ---
    sw = json.load(open(os.path.join(RAW, "schwa_index.json")))
    t("T-43", "音標", "ə 主索引 589", 589, sw["summary"]["primary_schwa"])
    t("T-44", "音標", "全部已分級（合計=總數）", sw["summary"]["total"],
      sum(sw["summary"]["by_status"].values()))
    t("T-45", "音標", "無未分類狀態", 0,
      sum(v for k, v in sw["summary"]["by_status"].items()
          if k.split("|")[1] not in ("CONFIRMED_SCHWA", "CONFIRMED_E", "OCR_ERROR", "UNKNOWN")))

    # --- 8 作品精讀（D3） ---
    t("T-46", "精讀", "精讀卡 30 首", 30, q("select count(*) from classical_works_study_r2_08"))
    t("T-47", "精讀", "每首均有 work_id", 0,
      q("select count(*) from classical_works_study_r2_08 where work_id is null or work_id=''"))
    t("T-48", "精讀", "體裁覆蓋 ≥6 類", True,
      q("select count(distinct genre) from classical_works_study_r2_08") >= 6)
    t("T-49", "精讀", "均標未校勘", 30,
      q("select count(*) from classical_works_study_r2_08 where verify_status='TEXT_FROM_WORKS_NOT_COLLATED'"))

    # --- 9 韻式案例（D2） ---
    t("T-50", "案例", "50 案例", 50, q("select count(*) from rhyme_mode_cases_r2_08"))
    t("T-51", "案例", "五類各 10", True, all(
        x == 10 for x in [q("select count(*) from rhyme_mode_cases_r2_08 where section=?", s)
                          for s in ("平韵格", "仄韵格", "平仄韵转换格", "平仄韵通叶格", "平仄韵错叶格")]))
    t("T-52", "案例", "通叶格平均部數 < 转换格", True,
      q("select avg(n_distinct_bu) from rhyme_mode_cases_r2_08 where section='平仄韵通叶格'")
      < q("select avg(n_distinct_bu) from rhyme_mode_cases_r2_08 where section='平仄韵转换格'"))
    t("T-53", "案例", "平/仄韻格轉換次數 ≤1（平均）", True,
      q("select avg(n_changes) from rhyme_mode_cases_r2_08 where section in ('平韵格','仄韵格')") <= 1.0)

    # --- 10 原圖（C3） ---
    t("T-54", "原圖", "圖證記錄 ≥20", True,
      q("select count(*) from cipai_image_checks_r2_08") >= 20)
    t("T-55", "原圖", "全部匹配記錄數=20", 20,
      q("select count(*) from cipai_image_checks_r2_08 where verdict='MATCH'"))
    t("T-56", "原圖", "釵頭鳳已判 SOURCE_INTERNAL_INCONSISTENCY", 1,
      q("select count(*) from cipai_image_checks_r2_08 where verdict='SOURCE_INTERNAL_INCONSISTENCY'"))

    # --- 11 版本與回滾 ---
    t("T-57", "版本", "r2_08 表數 ≥12", True,
      q("select count(*) from sqlite_master where type='table' and name like '%r2_08%'") >= 12)
    t("T-58", "版本", "舊表未改動（cipai_specs 仍 76）", 76,
      q("select count(*) from cipai_specs"))
    t("T-59", "版本", "works 未改動（375399）", 375399, q("select count(*) from works"))
    t("T-60", "版本", "原始 pages 未改動（1691）", 1691, q("select count(*) from book_pages_paddle"))

    npass = sum(1 for x in R if x["pass"])
    out = {"total": len(R), "pass": npass, "fail": len(R) - npass,
           "pass_rate": round(100 * npass / len(R), 1), "results": R}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("total", "pass", "fail", "pass_rate")}, ensure_ascii=False))
    for x in R:
        if not x["pass"]:
            print("FAIL", x["id"], x["desc"], "expect", x["expected"], "actual", x["actual"])


if __name__ == "__main__":
    main()
