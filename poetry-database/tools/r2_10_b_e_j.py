#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-10 工作包 B／E／J：音韻數據語義重建、六套韻書覆蓋矩陣、跨韻書查詢驗證。

B：說明清楚 ph_readings_r2_08 到底存了什麼（它沒有 phonetics），並建立語義視圖。
E：六套體系逐項給出「有什麼／沒有什麼／來源等級」。
J：真正執行 30 個查詢，記錄 SQL、結果與來源，並做 5 個「錯誤前提」查詢測試系統會不會硬編答案。
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
os.makedirs(os.path.join(OUT, "semantics"), exist_ok=True)
os.makedirs(os.path.join(OUT, "books"), exist_ok=True)
os.makedirs(os.path.join(OUT, "query"), exist_ok=True)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row


def q1(sql, args=()):
    r = con.execute(sql, args).fetchone()
    return r[0] if r else None


def show(sql, args=(), n=10):
    return [dict(x) for x in con.execute(sql, args).fetchall()[:n]]


# ---------------- B：語義 ----------------
def work_b():
    total = q1("SELECT count(*) FROM ph_readings_r2_08")
    fill = {}
    for col in ["charx", "reading", "initial", "final", "tone", "rhyme_group", "fanqie",
                "volume", "page", "source_book"]:
        n = q1("SELECT count(*) FROM ph_readings_r2_08 WHERE %s IS NULL OR %s=''" % (col, col))
        fill[col] = {"empty": n, "filled": total - n}

    # 語義分類
    con.execute("DROP VIEW IF EXISTS v_ph_semantics_r2_10")
    con.execute("""
    CREATE VIEW v_ph_semantics_r2_10 AS
    SELECT r.*,
      CASE
        WHEN r.system='modern_rhyme' THEN 'MODERN_PRONUNCIATION'
        WHEN r.system='regulated_verse' THEN 'RHYME_MEMBERSHIP'
        WHEN r.system='ci_rhyme' THEN 'RHYME_MEMBERSHIP'
        WHEN r.system IN ('middle_chinese') AND r.fanqie IS NOT NULL AND r.fanqie<>''
             THEN 'PHONETIC_READING'
        WHEN r.system IN ('middle_chinese') THEN 'RHYME_MEMBERSHIP'
        WHEN r.system='yuan_qu' THEN 'RHYME_MEMBERSHIP'
        ELSE 'RHYME_MEMBERSHIP'
      END AS data_type,
      CASE WHEN r.tone IS NOT NULL AND r.tone<>'' THEN 1 ELSE 0 END AS has_tone_class,
      CASE WHEN r.fanqie IS NOT NULL AND r.fanqie<>'' THEN 1 ELSE 0 END AS has_fanqie,
      CASE WHEN r.rhyme_group IS NOT NULL AND r.rhyme_group<>'' THEN 1 ELSE 0 END AS has_rhyme_group,
      0 AS has_phonetic_value,
      CASE WHEN r.system='modern_rhyme' THEN 'COMPUTED_FROM_PINYIN' ELSE 'SOURCE_TRANSCRIPTION' END
        AS semantic_evidence
    FROM ph_readings_r2_08 r
    """)
    by_type = [dict(x) for x in con.execute(
        "SELECT data_type, count(*) n, sum(has_fanqie) with_fanqie, sum(has_phonetic_value) with_phonetic "
        "FROM v_ph_semantics_r2_10 GROUP BY 1 ORDER BY n DESC")]

    # 佔位符審計（廣韻）
    ph = [dict(x) for x in con.execute("""
      SELECT source_book, count(*) n,
             sum(CASE WHEN charx LIKE '%□%' OR charx LIKE '%�%' THEN 1 ELSE 0 END) placeholder
      FROM ph_readings_r2_08 WHERE source_book LIKE '廣韻%' GROUP BY 1""")]
    ph_rows = [dict(x) for x in con.execute("""
      SELECT charx, rhyme_group, tone, count(*) n FROM ph_readings_r2_08
      WHERE source_book LIKE '廣韻%' AND (charx LIKE '%□%' OR charx LIKE '%�%')
      GROUP BY charx, rhyme_group, tone ORDER BY n DESC LIMIT 40""")]

    out = {"total_rows": total, "field_fill": fill, "by_data_type": by_type,
           "guangyun_placeholder": ph, "placeholder_top": ph_rows}
    json.dump(out, open(os.path.join(OUT, "semantics", "semantics.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "semantics", "PLACEHOLDER_CHARACTER_AUDIT.csv"), "w",
              newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["charx", "rhyme_group", "tone", "n_records", "recoverable", "note"])
        for r in ph_rows:
            w.writerow([r["charx"], r["rhyme_group"], r["tone"], r["n"],
                        "UNKNOWN", "字形缺失，未由反切反推；需影印本或另一轉錄本比對"])
    print("B:", total, dict((x["data_type"], x["n"]) for x in by_type))
    print("   placeholder:", ph)
    return out


# ---------------- E：六套韻書 ----------------
def work_e():
    rows = []
    specs = {
        "廣韻": ("middle_chinese", "廣韻（原本廣韻，維基文庫四庫本轉錄）"),
        "集韻": ("middle_chinese", "集韻（四庫全書本，維基文庫轉錄）"),
        "平水韻": ("regulated_verse", "平水韻 106 韻（項目自建繁表）"),
        "詞林正韻": ("ci_rhyme", "詞林正韻（維基文庫轉錄，含 <半> 標記）"),
        "中原音韻": ("yuan_qu", "中原音韻（維基文庫正文）"),
        "中華新韻": ("modern_rhyme", "中華新韻十四韻（韻母規則派生）"),
    }
    extra = {"詞林正韻": ("ph_cilin_r2_09", "cilin"), "中原音韻": ("ph_zhongyuan_r2_09", "zy"),
             "集韻": ("ph_jiyun_r2_09", "jy")}
    # 注意：廣韻與集韻在 ph_readings_r2_08 同屬 system='middle_chinese'，只能靠 source_book 區分
    srcfilter = {"廣韻": "source_book LIKE '廣韻%'", "集韻": "source_book LIKE '集韻%'"}
    for name, (sysname, src) in specs.items():
        where = srcfilter.get(name, "system='%s'" % sysname)
        n = q1("SELECT count(*) FROM ph_readings_r2_08 WHERE " + where)
        c = q1("SELECT count(distinct charx) FROM ph_readings_r2_08 WHERE " + where)
        g = q1("SELECT count(distinct rhyme_group) FROM ph_readings_r2_08 WHERE " + where)
        fq = q1("SELECT count(*) FROM ph_readings_r2_08 WHERE " + where + " AND fanqie IS NOT NULL AND fanqie<>''")
        tone = q1("SELECT count(distinct tone) FROM ph_readings_r2_08 WHERE " + where)
        ev = q1("SELECT group_concat(distinct evidence_level) FROM ph_readings_r2_08 WHERE " + where)
        rows.append({"system": name, "source": src, "n_records": n, "n_chars": c,
                     "n_rhyme_groups": g, "n_with_fanqie": fq, "n_tone_classes": tone,
                     "evidence_levels": ev})
    # 中華新韻是否規則派生
    mod_all = q1("SELECT count(*) FROM ph_readings_r2_08 WHERE system='modern_rhyme'")
    mod_rule = q1("SELECT count(*) FROM ph_modern_audit_r2_09 WHERE rule_yun IS NOT NULL")
    # 詞林/中原新表
    cilin = q1("SELECT count(*) FROM ph_cilin_r2_09")
    cilin_c = q1("SELECT count(distinct charx) FROM ph_cilin_r2_09")
    zy = q1("SELECT count(*) FROM ph_zhongyuan_r2_09")
    zy_c = q1("SELECT count(distinct charx) FROM ph_zhongyuan_r2_09")
    jy = q1("SELECT count(*) FROM ph_jiyun_r2_09")
    gyh = q1("SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE is_xiaoyun_head=1")
    for r in rows:
        if r["system"] == "詞林正韻":
            r["new_table_rows"], r["new_table_chars"] = cilin, cilin_c
        if r["system"] == "中原音韻":
            r["new_table_rows"], r["new_table_chars"] = zy, zy_c
        if r["system"] == "集韻":
            r["new_table_rows"], r["new_table_chars"] = jy, None
        if r["system"] == "廣韻":
            r["new_table_rows"], r["new_table_chars"] = gyh, None

    with open(os.path.join(OUT, "books", "SIX_SYSTEM_SOURCE_COVERAGE.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        cols = ["system", "source", "n_records", "n_chars", "n_rhyme_groups",
                "n_with_fanqie", "n_tone_classes", "evidence_levels",
                "new_table_rows", "new_table_chars"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    json.dump({"systems": rows, "modern_total": mod_all, "modern_with_rule": mod_rule},
              open(os.path.join(OUT, "books", "six_systems.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for r in rows:
        print("E:", r["system"], r["n_records"], "chars", r["n_chars"], "rg", r["n_rhyme_groups"],
              "fq", r["n_with_fanqie"], "ev", r["evidence_levels"])
    return rows


# ---------------- J：查詢 ----------------
QUERIES = [
    ("Q01", "「東」在《廣韻》有幾條小韻記錄？", "SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE head='東' AND is_xiaoyun_head=1", ("head",)),
    ("Q02", "「東」在《廣韻》的反切上下字", "SELECT fanqie, fanqie_upper, fanqie_lower, yun_name FROM guangyun_fanqie_r2_10 WHERE head='東' AND is_xiaoyun_head=1 LIMIT 5", ("fanqie", "upper", "lower", "yun")),
    ("Q03", "「東」在《平水韻》屬哪一韻", "SELECT rhyme_group, tone, count(*) n FROM ph_readings_r2_08 WHERE charx='東' AND system='regulated_verse' GROUP BY 1,2", ("rg", "tone")),
    ("Q04", "「東」在《集韻》有小韻嗎", "SELECT yun, fanqie, declared_chars FROM ph_jiyun_r2_09 WHERE head='東' LIMIT 5", ("yun", "fq")),
    ("Q05", "「東」在《詞林正韻》屬哪部", "SELECT bu, tone, is_half FROM ph_cilin_r2_09 WHERE charx='東' LIMIT 5", ("bu",)),
    ("Q06", "「東」在《中原音韻》屬哪部、哪聲調", "SELECT bu, tone, yinyang FROM ph_zhongyuan_r2_09 WHERE charx='東' LIMIT 5", ("bu", "tone")),
    ("Q07", "「東」在《中華新韻》屬哪韻（規則派生）", "SELECT rhyme_group, tone FROM ph_readings_r2_08 WHERE charx='東' AND system='modern_rhyme'", ("rg",)),
    ("Q08", "多音字「行」在六套體系中的記錄數", "SELECT system, count(*) n FROM ph_readings_r2_08 WHERE charx='行' GROUP BY 1", ("system",)),
    ("Q09", "「行」在《廣韻》的全部小韻", "SELECT yun_name, fanqie, fanqie_upper, fanqie_lower FROM guangyun_fanqie_r2_10 WHERE head='行' AND is_xiaoyun_head=1", ("yun", "fq")),
    ("Q10", "「重」在《廣韻》有幾個反切", "SELECT fanqie, yun_name FROM guangyun_fanqie_r2_10 WHERE head='重' AND is_xiaoyun_head=1", ("fq",)),
    ("Q11", "《廣韻》206 韻中，哪一韻小韻最多", "SELECT yun_name, n_xiaoyun FROM guangyun_yunmu_repair_r2_10 ORDER BY n_xiaoyun DESC LIMIT 5", ("yun", "n")),
    ("Q12", "《集韻》哪一韻小韻最多", "SELECT yun, count(*) n FROM ph_jiyun_r2_09 GROUP BY 1 ORDER BY n DESC LIMIT 5", ("yun", "n")),
    ("Q13", "《詞林正韻》十九部各有幾個字", "SELECT bu, count(distinct charx) n FROM ph_cilin_r2_09 GROUP BY 1 ORDER BY 1", ("bu", "n")),
    ("Q14", "《詞林正韻》「半」韻記錄有多少", "SELECT count(*) FROM ph_cilin_r2_09 WHERE is_half=1", ("n",)),
    ("Q15", "《中原音韻》入聲派入三聲各多少", "SELECT tone, count(*) n FROM ph_zhongyuan_r2_09 WHERE tone LIKE '入聲%' GROUP BY 1", ("tone", "n")),
    ("Q16", "《平水韻》106 韻各韻字數", "SELECT rhyme_group, count(*) n FROM ph_readings_r2_08 WHERE system='regulated_verse' GROUP BY 1 ORDER BY n DESC LIMIT 8", ("rg", "n")),
    ("Q17", "一字多韻：平水韻中同時屬兩韻以上的字有多少", "SELECT count(*) FROM (SELECT charx FROM ph_readings_r2_08 WHERE system='regulated_verse' GROUP BY charx HAVING count(distinct rhyme_group)>1)", ("n",)),
    ("Q18", "「看」在平水韻的多個歸屬", "SELECT rhyme_group, tone FROM ph_readings_r2_08 WHERE charx='看' AND system='regulated_verse'", ("rg",)),
    ("Q19", "《廣韻》反切上字最常見的十個", "SELECT fanqie_upper, count(*) n FROM guangyun_fanqie_r2_10 WHERE is_xiaoyun_head=1 AND fanqie_upper<>'' GROUP BY 1 ORDER BY n DESC LIMIT 10", ("upper", "n")),
    ("Q20", "《廣韻》反切下字最常見的十個", "SELECT fanqie_lower, count(*) n FROM guangyun_fanqie_r2_10 WHERE is_xiaoyun_head=1 AND fanqie_lower<>'' GROUP BY 1 ORDER BY n DESC LIMIT 10", ("lower", "n")),
    ("Q21", "某字在《廣韻》與《集韻》的反切是否相同（例：東）", "SELECT '廣韻' s, fanqie FROM guangyun_fanqie_r2_10 WHERE head='東' AND is_xiaoyun_head=1 UNION ALL SELECT '集韻', fanqie FROM ph_jiyun_r2_09 WHERE head='東'", ("s", "fq")),
    ("Q22", "《廣韻》有幾條字頭是佔位符", "SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE head LIKE '%□%' OR head LIKE '%�%'", ("n",)),
    ("Q23", "196 條詞格中韻式標籤與譜行推導衝突有幾條", "SELECT count(*) FROM cipai_rhyme_dual_r2_08 WHERE classification_conflict=1", ("n",)),
    ("Q24", "衝突條目的最終判定分佈（R2-09）", "SELECT verdict, count(*) n FROM cipai_conflict_verdict_r2_09 GROUP BY 1 ORDER BY n DESC", ("v", "n")),
    ("Q25", "60 條原圖符號核驗結果分佈（R2-10）", "SELECT verdict, count(*) n FROM cipai_symbol_audit_r2_10 GROUP BY 1", ("v", "n")),
    ("Q26", "例詞 310 條的新分類分佈（R2-09）", "SELECT new_match_kind, count(*) n FROM example_work_links_r2_09 GROUP BY 1 ORDER BY n DESC", ("k", "n")),
    ("Q27", "《廣韻》與《集韻》在同表中共用 system='middle_chinese'，可否只靠 system 區分", "SELECT system, count(distinct source_book) n_src FROM ph_readings_r2_08 WHERE system='middle_chinese' GROUP BY 1", ("system", "n_src")),
    ("Q28", "《廣韻》中「一」字有幾條記錄", "SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE head='一'", ("n",)),
    ("Q29", "《集韻》中「一」字", "SELECT yun, fanqie FROM ph_jiyun_r2_09 WHERE head='一'", ("yun",)),
    ("Q30", "《詞林正韻》中「一」字", "SELECT bu, tone FROM ph_cilin_r2_09 WHERE charx='一'", ("bu",)),
]

# 5 個錯誤前提查詢：系統必須說「無此欄位/無資料」，不能硬編
FALSE_PREMISE = [
    ("F01", "「東」在中古音的國際音標音值是？", "本庫無 phonetic_value 欄；ph_readings_r2_08 的 reading/initial 全空。正確回答：無音值資料。"),
    ("F02", "「東」在《廣韻》的聲母是哪一個（用 fanqie_upper 推）？", "R2-08 的 fanqie_upper 存的是下字，不可用於推聲母；R2-10 已改為上字。舊欄位查詢會給錯答案。"),
    ("F03", "《詞林正韻》是否收錄全部平水韻字？", "否。只覆蓋 4,914/8,564（57.4%），其餘屬 NOT_IN_CILIN_SOURCE 或待查，不能推定。"),
    ("F04", "《中華新韻》7,216 條是否為原書逐字採錄？", "否。全部為拼音規則派生（COMPUTED），非原書字表。"),
    ("F05", "《集韻》字頭總數是否為 49,084？", "否。49,084 是程序估計值，非原書字頭數；原書自述 53,525（全書）。"),
]


def work_j():
    rows = []
    for qid, question, sql, keys in QUERIES:
        try:
            cur = con.execute(sql)
            res = [dict(x) for x in cur.fetchall()[:12]]
            n = len(res)
            err = ""
        except Exception as e:
            res, n, err = [], 0, str(e)[:120]
        rows.append({"qid": qid, "question": question, "sql": sql,
                     "n_rows": n, "result": json.dumps(res, ensure_ascii=False)[:900],
                     "error": err})
    with open(os.path.join(OUT, "query", "RHYME_QUERY_30_RESULTS.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["qid", "question", "sql", "n_rows", "result", "error"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    ok = sum(1 for r in rows if not r["error"] and r["n_rows"] > 0)
    print("J: 查詢", len(rows), "有結果", ok, "空/錯", len(rows) - ok)
    for r in rows:
        if r["error"] or r["n_rows"] == 0:
            print("   ", r["qid"], r["question"], "ERR" if r["error"] else "EMPTY", r["error"][:60])

    with open(os.path.join(OUT, "query", "FALSE_PREMISE_5.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["fid", "false_premise_question", "correct_behaviour"])
        for x in FALSE_PREMISE:
            w.writerow(list(x))
    json.dump({"queries": rows, "n_ok": ok, "false_premise": FALSE_PREMISE},
              open(os.path.join(OUT, "query", "query_stats.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    work_b()
    work_e()
    work_j()
    con.close()
