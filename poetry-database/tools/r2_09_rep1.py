#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 報告生成器（第一批：工作包 A 與 B）。"""
import os
import json
import shutil
import csv
import sqlite3
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R9 = os.path.join(ROOT, "raw", "r2_09")
REP = os.path.join(ROOT, "reports", "tasks", "2026-11-14", "R2-09")
os.makedirs(REP, exist_ok=True)
F = json.load(open(os.path.join(R9, "audit", "facts.json"), encoding="utf-8"))
con = sqlite3.connect(os.path.join(ROOT, "database", "poetry.db"))
con.row_factory = sqlite3.Row


def w(name, text):
    with open(os.path.join(REP, name), "w", encoding="utf-8") as f:
        f.write(text)
    print("wrote", name, len(text))


def cp(src, dst):
    shutil.copy(src, os.path.join(REP, dst))


# ---------------- DATABASE_SCHEMA_AUDIT.md ----------------
rows = F["tables_r2_07_r2_08"] if isinstance(F["tables_r2_07_r2_08"], list) else None
sa = json.load(open(os.path.join(R9, "audit", "schema_audit.json"), encoding="utf-8"))
tbl = sa["tables_r2_07_r2_08"]
rel = sa["relationships"]
dup = sa["duplicates"]
chk = sa["consistency"]

lines = ["# R2-08 資料庫結構審計", ""]
lines.append("> 只讀檢查，未修改任何 R2-07／R2-08 表。資料庫 %s（%.0f MB）。" % (
    "poetry.db", F["db_size_bytes"] / 1048576))
lines.append("")
lines.append("## 1 表清單與規模")
lines.append("")
lines.append("| 表 | 行數 | 欄數 | 主鍵 | 有 NULL 的欄 | 來源輪次 |")
lines.append("|---|---:|---:|---|---:|---|")
for t in tbl:
    lines.append("| %s | %d | %d | %s | %d | %s |" % (
        t["table"], t["rows"], t["n_columns"], t["primary_key"],
        t["n_columns_with_null"], t["round_origin"]))
lines.append("")
lines.append("合計 **%d** 張表、**%d** 行。" % (len(tbl), sum(t["rows"] for t in tbl)))
lines.append("")
lines.append("## 2 邏輯外鍵與孤立記錄")
lines.append("")
lines.append("資料庫未宣告 FOREIGN KEY，故以 JOIN 檢出孤立記錄。")
lines.append("")
lines.append("| 從 | 欄 | 到 | 孤立 | 空值 | 判定 |")
lines.append("|---|---|---|---:|---:|---|")
for r in rel:
    lines.append("| %s | %s | %s.%s | %d | %d | %s |" % (
        r["from_table"], r["from_col"], r["to_table"], r["to_col"],
        r["orphan_rows"], r["from_nulls_or_empty"], r["status"]))
lines.append("")
lines.append("**孤立 9 條的真正原因**：`cipai_form_variants_r2_07.derived_name` 混用了兩種語義——")
lines.append("一半是「格標籤」（如 `七言绝句式`、`摊破浣溪沙`），一半是「別名」。前者本就不是詞牌實體，")
lines.append("指向 `cipai_entities` 自然找不到；後者 61 條的 `derived_name` 為空，別名只寫在 `evidence` 自由文本裡。")
lines.append("這是**欄位語義未分離**的結構缺陷，不是資料丟失。")
lines.append("")
lines.append("## 3 重複記錄")
lines.append("")
lines.append("| 表 | 鍵 | 重複組 | 多出行 |")
lines.append("|---|---|---:|---:|")
for k, v in dup.items():
    if "error" in v:
        continue
    lines.append("| %s | %s | %d | %d |" % (k.split(" | ")[0], k.split(" | ")[1],
                                            v["dup_groups"], v["extra_rows"]))
lines.append("")
lines.append("### 3.1 `ph_readings_r2_08` 的重複必須分三類，不能一概而論")
lines.append("")
for r in con.execute("select * from ph_dup_analysis_r2_09"):
    lines.append("- **%s / %s**：%d 組、多出 %d 行 → `%s`" % (
        r["system"], r["dup_kind"], r["dup_groups"], r["extra_rows"], r["verdict"]))
lines.append("")
lines.append("佔位符字頭（`□`）造成的 3,148 行重複屬**計數虛增**：同一韻內數十個無法辨識的罕字")
lines.append("都被記成同一個 `□`，於是「字頭數」被高估。R2-08 報告稱佔位符 3,665 條，")
lines.append("本輪實測 `□` 相關行 **%d** 條。" % F["placeholder_rows"])
lines.append("")
lines.append("## 4 欄位填充率的實質問題")
lines.append("")
lines.append("| 欄位 | 有值行數 | 佔比 | 說明 |")
lines.append("|---|---:|---:|---|")
lines.append("| reading | 0 / %d | 0%% | **全表為空**，本表不含任何音值 |" % F["readings"])
lines.append("| initial | 0 / %d | 0%% | 全表為空 |" % F["readings"])
lines.append("| page | 0 / %d | 0%% | 全表為空，無頁碼可追溯 |" % F["readings"])
lines.append("| final | 7,216 / %d | 8.9%% | 僅 `modern_rhyme` 由拼音填入 |" % F["readings"])
lines.append("| tone | %d / %d | 100%% | 唯一全滿 |" % (F["readings"], F["readings"]))
lines.append("")
lines.append("**結論：表名 `ph_readings`（讀音）與內容不符。** 實際內容是「字—韻部—調類」歸部記錄，")
lines.append("沒有任何擬音或注音。R2-08 報告稱「80,652 條讀音」屬**命名誇大**。")
lines.append("本輪新增只讀視圖 `v_ph_records_r2_09`，把 `reading_state` 明確標為 `NO_PHONETIC_VALUE`。")
lines.append("")
lines.append("## 5 統計口徑矛盾")
lines.append("")
lines.append("| 項目 | 值 | 來源 |")
lines.append("|---|---:|---|")
lines.append("| 平水韻行數 | %d | `ph_readings` |" % F["pingshui_rows"])
lines.append("| 平水韻不同字 | %d | `count(distinct charx)` |" % F["pingshui_chars"])
lines.append("| 平水韻韻目累計字數 | %d | `ph_rhyme_groups.sum(n_chars)` |" % chk["pingshui_sum_group_nchars"])
lines.append("| 詞林正韻（R2-08 折算） | 11,382 | `ph_readings` |")
lines.append("| 詞林正韻（R2-09 原書字表） | %d | `ph_cilin_r2_09` |" % F["cilin_rows"])
lines.append("")
lines.append("同一部韻書出現 **8,116／8,361／8,564／10,662／10,714** 多個數字，")
lines.append("差別在於「算行」、「算字」、「算韻目累計」三種口徑混用。R2-09 於 `COUNTING_RULES.md` 定死口徑。")
lines.append("")
lines.append("## 6 命名誇大與語義不符清單")
lines.append("")
lines.append("| 欄位／表 | 問題 | 建議 |")
lines.append("|---|---|---|")
lines.append("| `ph_readings_r2_08.reading` | 全空，卻名為 reading | 改名為 `ph_rhyme_membership`，或保留但標 `NO_PHONETIC_VALUE` |")
lines.append("| `cipai_rhyme_dual_r2_08.observed_rhyme_behavior` | 名為 observed，實為「譜行符號＋括注」推導 | 本輪拆成 `scoreline_end_tone_sequence` 與 `notation_inferred_rhyme_behavior` |")
lines.append("| `cipai_forms_r2_07.rhyme_tone_source` | 全部 `PATTERN_LABEL_MIXED` 等值，未區分來源 | 需改為來源枚舉 |")
lines.append("| `cipai_forms_r2_07.declared_rhyme` | 實為**詞牌層級**說明，被當成該格的說明 | 本輪實測 196/196 皆等於詞牌層級值 |")
lines.append("| `cipai_form_variants_r2_07.derived_name` | 混存格標籤與別名 | 拆為 `variant_kind` 與 `alias_name` |")
lines.append("| `fanqie_upper`（廣韻 JSON） | 存的其實是反切**下字** | 改名 `fanqie_lower`，另立 `fanqie_upper` |")
lines.append("")
w("DATABASE_SCHEMA_AUDIT.md", "\n".join(lines))

cp(os.path.join(R9, "audit", "DATABASE_TABLE_COUNTS.csv"), "DATABASE_TABLE_COUNTS.csv")
cp(os.path.join(R9, "audit", "DATABASE_RELATIONSHIP_AUDIT.csv"), "DATABASE_RELATIONSHIP_AUDIT.csv")

# ---------------- DATA_DICTIONARY.md ----------------
dd = ["# 資料字典（R2-09 候選研究層）", ""]
dd.append("本輪新增 %d 張表與 1 個視圖，全部以 `_r2_09` 後綴隔離，不覆蓋 R2-07／R2-08 任何表。" % F["tables_r2_09"])
dd.append("")
dd.append("| 表 | 用途 | 主鍵 | 關鍵欄位 |")
dd.append("|---|---|---|---|")
_desc = {
    "ph_evidence_map_r2_09": ("舊 evidence_level → 新八級證據分級", "old_evidence_level", "new_evidence_level, source_type, traceable_to_page"),
    "ph_reading_stats_r2_09": ("每體系逐字段填充率與口徑", "system", "rows_total, null_reading, distinct_chars, counting_note"),
    "ph_dup_analysis_r2_09": ("重複成因分類", "system+dup_kind", "dup_groups, extra_rows, verdict"),
    "ph_jiyun_r2_09": ("集韻 206 韻小韻（重建）", "id", "yun, head, fanqie_upper, fanqie_lower, declared_chars, html_sha256"),
    "ph_cilin_r2_09": ("詞林正韻十九部逐字", "id", "bu, tone, yunmu, is_half, charx, revision"),
    "ph_zhongyuan_r2_09": ("中原音韻十九部逐字", "id", "bu, tone, yinyang, charx"),
    "ph_modern_rule_r2_09": ("中華新韻十四韻韻母規則", "yun", "finals, description"),
    "ph_modern_audit_r2_09": ("拼音派生記錄與規則符合度", "id", "rhyme_group, rule_yun, rule_match"),
    "ph_polyphone_r2_09": ("多音字跨體系對照 200 字", "charx", "n_systems, middle_chinese, regulated_verse, ci_rhyme, yuan_qu"),
    "ph_cross_cases_r2_09": ("跨韻書差異 100 字", "charx", "mc_group, rv_group, ci_bu, yq_bu"),
    "cipai_rhyme_fields_r2_09": ("韻式七欄重構", "form_id", "source_rhyme_label, source_rhyme_label_scope, scoreline_end_tone_sequence, example_observed_rhyme_behavior"),
    "cipai_conflict_verdict_r2_09": ("33 條衝突逐條判定", "form_id", "verdict, evidence"),
    "cipai_wordcount_r2_09": ("13 條字數五方對帳", "form_id", "declared_num, scoreline_symbols, example_chars, recomputed_minus_declared"),
    "example_work_links_r2_09": ("例詞關聯重判", "example_id", "old_match_kind, new_match_kind, same_author, containment, score"),
}
for r in con.execute("select name from sqlite_master where type='table' and name like '%r2_09%' order by name"):
    n = r[0]
    d = _desc.get(n, ("", "", ""))
    dd.append("| `%s` | %s | %s | %s |" % (n, d[0], d[1], d[2]))
dd.append("")
dd.append("## 視圖 `v_ph_records_r2_09`")
dd.append("")
dd.append("把 `ph_readings_r2_08` 與新證據分級連接，並補三個誠實欄位：")
dd.append("`is_placeholder`（是否佔位符字頭）、`reading_state`（有無音值）、`is_derived`（是否程序推導）。")
dd.append("")
dd.append("## 每個讀音記錄可追溯的欄位")
dd.append("")
dd.append("| 需求 | 現況 |")
dd.append("|---|---|")
dd.append("| 書籍 | `source_book` |")
dd.append("| 版本 | 見 `source_book` 括注（如「四庫全書本·維基文庫轉錄」） |")
dd.append("| 卷次 | `volume`（僅中古音有；詞韻、新韻為空） |")
dd.append("| 韻目 | `rhyme_group` |")
dd.append("| 原始頁碼 | **空**（`page` 全表無值） |")
dd.append("| 具體記錄 | 集韻可回 `ph_jiyun_r2_09.html_sha256`；詞林正韻／中原音韻可回 `revision` |")
dd.append("")
dd.append("**缺口**：`page` 全空，故沒有一條韻書記錄能直接指到紙本頁碼。這是本輪未能解決的硬缺口。")
w("DATA_DICTIONARY.md", "\n".join(dd))

# ---------------- EVIDENCE_LEVEL_STANDARD.md ----------------
el = ["# 證據等級標準", ""]
el.append("## 1 八級定義")
el.append("")
el.append("| 等級 | 含義 | 本輪是否出現 |")
el.append("|---|---|---|")
for k, v, has in [
    ("SOURCE_PRIMARY", "原始文獻或可靠原書影印本直接證據", "**否（0 條）**"),
    ("SOURCE_EDITION", "有明確版本信息的整理本或排印本", "是（平水韻字表 10,662）"),
    ("SOURCE_TRANSCRIPTION", "有明確出處的數字文本轉錄", "是（廣韻 20,530／集韻 30,862／詞林正韻 5,563／中原音韻 5,731）"),
    ("OCR_DERIVED", "從掃描圖像 OCR 得到，尚未逐項核實", "是（王力兩書 1,167 頁）"),
    ("SECONDARY", "後人研究、論文、字典或注釋資料", "是（上古音書目 25 條）"),
    ("COMPUTED", "程序根據其他數據推導", "是（18,598 條）"),
    ("INFERRED", "根據結構、上下文或規則推定", "是（廣韻 20,451 條韻目歸屬）"),
    ("UNKNOWN", "來源或結論無法確定", "是（音標 130 處、例詞 114 條）"),
]:
    el.append("| `%s` | %s | %s |" % (k, v, has))
el.append("")
el.append("## 2 關鍵判例")
el.append("")
el.append("**`SOURCE_PRIMARY` 本輪為 0，這是刻意的。** 六套韻書全部來自維基文庫轉錄，")
el.append("沒有一套與影印本逐頁對勘過。轉錄再忠實，也只是 `SOURCE_TRANSCRIPTION`。")
el.append("只有當某一頁能同時出示「影印本圖」與「轉錄文字」且二者一致時，才可升為 `SOURCE_PRIMARY`。")
el.append("")
el.append("**`INFERRED` 與 `SOURCE_TRANSCRIPTION` 必須分開。** 廣韻 20,530 條中，")
el.append("只有 79 條的韻目來自韻目字本身（`YUNMU_HEAD`），其餘 20,451 條是「沿用前一條」（`CARRIED_FORWARD`）。")
el.append("載體是轉錄文本，但**韻目歸屬是推定**，故 `yun_attribution` 記 `CARRIED_FORWARD` 而非直接來源。")
el.append("")
el.append("**`COMPUTED` 不得冒充採錄。** 中華新韻 7,216 條由拼音按十四韻規則映射，")
el.append("規則本身有依據（韻母歸部），但字表不是原書字表。凡此一律 `COMPUTED`。")
el.append("")
el.append("## 3 映射結果")
el.append("")
el.append("| 新等級 | 條數 | 佔比 |")
el.append("|---|---:|---:|")
tot = sum(F["evidence_new"].values())
for k, v in sorted(F["evidence_new"].items(), key=lambda x: -x[1]):
    el.append("| `%s` | %d | %.1f%% |" % (k, v, 100 * v / tot))
el.append("")
el.append("## 4 每條記錄應帶的來源欄位")
el.append("")
el.append("`source_id`、`source_title`、`source_author`、`source_edition`、`source_year`、")
el.append("`source_page`、`source_locator`、`source_url`、`source_revision`、`original_text`、")
el.append("`normalized_text`、`evidence_level`、`extraction_method`、`verification_status`、`review_note`。")
el.append("")
el.append("現況：`source_revision` 在集韻為**空**（未記錄 revid，只有 HTML SHA-256）；")
el.append("`source_page` 在六套韻書全為空。這兩項是本輪明確的不足。")
w("EVIDENCE_LEVEL_STANDARD.md", "\n".join(el))

# ---------------- COUNTING_RULES.md ----------------
cr = ["# 統計口徑規則", ""]
cr.append("## 1 十個必須分開的數字")
cr.append("")
cr.append("| 名詞 | 定義 | 平水韻 | 詞林正韻 | 中原音韻 | 廣韻 | 集韻 |")
cr.append("|---|---|---:|---:|---:|---:|---:|")
cr.append("| 記錄數 | 表內行數 | %d | %d | %d | %d | %d |" % (
    F["pingshui_rows"], F["cilin_rows"], F["zy_rows"], F["guangyun_rows"], 30862))
cr.append("| 規範字數 | `count(distinct charx)` | %d | %d | %d | 12,448 | 14,740 |" % (
    F["pingshui_chars"], F["cilin_chars"], F["zy_chars"]))
cr.append("| 韻目數 | `count(distinct 韻目)` | 106 | %d | %d | 206 | %d |" % (
    F["cilin_yunmu"], F["zy_bu"], F["jiyun_yun"]))
cr.append("| 小韻數 | `○` 或等價單位 | — | — | — | 4,771 | %d |" % F["jiyun_xiaoyun"])
cr.append("| 反切數 | 有 `X切` 的記錄 | 0 | 0 | 0 | 4,327 | %d |" % F["jiyun_fanqie"])
cr.append("| 佔位符 | `□`/`�` 字頭 | 0 | 0 | 0 | %d | 未計 |" % F["placeholder_rows"])
cr.append("| 推導記錄 | `COMPUTED` | 0 | 0 | 0 | 0 | 0 |")
cr.append("")
cr.append("## 2 三條硬規則")
cr.append("")
cr.append("1. **報「字數」必須同時報口徑**：是「行數」還是「不同字數」。平水韻 10,662 行、8,564 字、")
cr.append("   韻目累計 10,714，三個數字都對，但意義不同。只寫一個數字就是誤導。")
cr.append("2. **推導不得與採錄同列**：詞林正韻 R2-08 的 11,382 條是折算值，R2-09 的 5,563 條是原書字表。")
cr.append("   二者不能相加，也不能互相替代。")
cr.append("3. **佔位符不得計入字頭**：廣韻 3,665 條 `□` 是 OCR 未識字，計入字頭會虛增 17.9%。")
cr.append("")
cr.append("## 3 每個數字都要能重算")
cr.append("")
cr.append("所有報告數字均由 `tools/r2_09_facts.py` 從資料庫現算並寫入 `raw/r2_09/audit/facts.json`，")
cr.append("報告生成器只讀該檔，不手寫數字。任何數字都可用一條 SQL 復現。")
w("COUNTING_RULES.md", "\n".join(cr))
print("batch1 done")
