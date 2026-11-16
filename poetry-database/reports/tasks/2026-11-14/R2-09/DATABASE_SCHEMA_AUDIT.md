# R2-08 資料庫結構審計

> 只讀檢查，未修改任何 R2-07／R2-08 表。資料庫 poetry.db（672 MB）。

## 1 表清單與規模

| 表 | 行數 | 欄數 | 主鍵 | 有 NULL 的欄 | 來源輪次 |
|---|---:|---:|---|---:|---|
| cipai_audit2_r2_08 | 196 | 20 | form_id | 0 | R2-08 |
| cipai_audit_r2_07 | 196 | 15 | form_id | 0 | R2-07 |
| cipai_count_audit_r2_07 | 13 | 10 | form_id | 1 | R2-07 |
| cipai_entities_r2_07 | 153 | 19 | entity_id | 0 | R2-07 |
| cipai_form_examples_r2_08 | 310 | 19 | example_id | 2 | R2-08 |
| cipai_form_sources_r2_07 | 1392 | 5 | (none) | 0 | R2-07 |
| cipai_form_variants_r2_07 | 71 | 7 | (none) | 0 | R2-07 |
| cipai_forms_r2_07 | 196 | 39 | form_id | 3 | R2-07 |
| cipai_image_checks_r2_08 | 22 | 13 | form_id | 3 | R2-08 |
| cipai_rhyme_dual_r2_08 | 196 | 17 | form_id | 0 | R2-08 |
| cipai_source_differences_r2_07 | 15 | 9 | diff_id | 0 | R2-07 |
| cipai_special_cases_r2_07 | 12 | 7 | case_id | 0 | R2-07 |
| classical_works_study_r2_08 | 30 | 26 | card_no | 0 | R2-08 |
| example_work_links_r2_08 | 310 | 13 | example_id | 4 | R2-08 |
| ocr_image_checks_r2_07 | 6 | 8 | check_id | 0 | R2-07 |
| page_map_notes_r2_07 | 3 | 3 | pdf_page | 0 | R2-07 |
| ph_audit_r2_08 | 7 | 5 | (none) | 0 | R2-08 |
| ph_readings_r2_08 | 80652 | 13 | id | 6 | R2-08 |
| ph_rhyme_groups_r2_08 | 158 | 9 | (none) | 0 | R2-08 |
| ph_systems_r2_08 | 6 | 6 | system | 0 | R2-08 |
| ph_variants_r2_08 | 15527 | 6 | (none) | 0 | R2-08 |
| rhyme_mode_cases_r2_08 | 50 | 13 | case_id | 0 | R2-08 |

合計 **22** 張表、**99521** 行。

## 2 邏輯外鍵與孤立記錄

資料庫未宣告 FOREIGN KEY，故以 JOIN 檢出孤立記錄。

| 從 | 欄 | 到 | 孤立 | 空值 | 判定 |
|---|---|---|---:|---:|---|
| cipai_forms_r2_07 | cipai_id | cipai_entities_r2_07.entity_id | 0 | 0 | OK |
| cipai_form_sources_r2_07 | form_id | cipai_forms_r2_07.form_id | 0 | 0 | OK |
| cipai_form_variants_r2_07 | form_id | cipai_forms_r2_07.form_id | 0 | 62 | OK |
| cipai_form_variants_r2_07 | derived_name | cipai_entities_r2_07.cipai_name | 9 | 62 | ORPHANS |
| cipai_audit_r2_07 | form_id | cipai_forms_r2_07.form_id | 0 | 0 | OK |
| cipai_audit2_r2_08 | form_id | cipai_forms_r2_07.form_id | 0 | 0 | OK |
| cipai_count_audit_r2_07 | form_id | cipai_forms_r2_07.form_id | 0 | 0 | OK |
| cipai_rhyme_dual_r2_08 | form_id | cipai_forms_r2_07.form_id | 0 | 0 | OK |
| cipai_image_checks_r2_08 | form_id | cipai_forms_r2_07.form_id | 0 | 0 | OK |
| cipai_form_examples_r2_08 | form_id | cipai_forms_r2_07.form_id | 0 | 0 | OK |
| example_work_links_r2_08 | example_id | cipai_form_examples_r2_08.example_id | 0 | 0 | OK |
| example_work_links_r2_08 | work_id | works.work_id | 0 | 112 | OK |
| example_work_links_r2_08 | form_id | cipai_forms_r2_07.form_id | 0 | 0 | OK |
| rhyme_mode_cases_r2_08 | form_id | cipai_forms_r2_07.form_id | 0 | 0 | OK |
| rhyme_mode_cases_r2_08 | example_id | cipai_form_examples_r2_08.example_id | 0 | 0 | OK |
| classical_works_study_r2_08 | work_id | works.work_id | 0 | 0 | OK |
| cipai_source_differences_r2_07 | cipai_name | cipai_entities_r2_07.cipai_name | 0 | 0 | OK |
| cipai_special_cases_r2_07 | cipai_name | cipai_entities_r2_07.cipai_name | 0 | 0 | OK |
| page_map_notes_r2_07 | pdf_page | page_map_wangli.pdf_page | 0 | 0 | OK |

**孤立 9 條的真正原因**：`cipai_form_variants_r2_07.derived_name` 混用了兩種語義——
一半是「格標籤」（如 `七言绝句式`、`摊破浣溪沙`），一半是「別名」。前者本就不是詞牌實體，
指向 `cipai_entities` 自然找不到；後者 61 條的 `derived_name` 為空，別名只寫在 `evidence` 自由文本裡。
這是**欄位語義未分離**的結構缺陷，不是資料丟失。

## 3 重複記錄

| 表 | 鍵 | 重複組 | 多出行 |
|---|---|---:|---:|
| ph_readings_r2_08 | system,charx,reading,rhyme_group,source_book,coalesce(volume,''),coalesce(page,'') | 5980 | 10038 |
| ph_readings_r2_08 | system,charx,reading,rhyme_group | 14820 | 21741 |
| cipai_form_sources_r2_07 | form_id,line_no | 0 | 0 |
| cipai_forms_r2_07 | cipai_name,form_seq | 0 | 0 |
| cipai_form_examples_r2_08 | form_id,example_seq | 1 | 1 |
| cipai_image_checks_r2_08 | form_id | 0 | 0 |
| ph_rhyme_groups_r2_08 | system,group_name | 0 | 0 |
| ph_variants_r2_08 | trad | 0 | 0 |
| cipai_entities_r2_07 | cipai_name | 0 | 0 |
| classical_works_study_r2_08 | work_id | 0 | 0 |

### 3.1 `ph_readings_r2_08` 的重複必須分三類，不能一概而論

- **ci_rhyme / SAME_CHAR_SAME_GROUP**：1338 組、多出 1462 行 → `ACCEPTABLE_DISTINCT_READING`
- **middle_chinese / PLACEHOLDER_HEAD**：185 組、多出 3148 行 → `DEFECT_PLACEHOLDER_INFLATES_COUNT`
- **middle_chinese / SAME_CHAR_SAME_GROUP**：596 組、多出 633 行 → `ACCEPTABLE_DISTINCT_READING`
- **middle_chinese / SAME_XIAOYUN_MULTI_ENTRY**：649 組、多出 655 行 → `ACCEPTABLE_MULTI_ENTRY`

佔位符字頭（`□`）造成的 3,148 行重複屬**計數虛增**：同一韻內數十個無法辨識的罕字
都被記成同一個 `□`，於是「字頭數」被高估。R2-08 報告稱佔位符 3,665 條，
本輪實測 `□` 相關行 **3660** 條。

## 4 欄位填充率的實質問題

| 欄位 | 有值行數 | 佔比 | 說明 |
|---|---:|---:|---|
| reading | 0 / 80652 | 0% | **全表為空**，本表不含任何音值 |
| initial | 0 / 80652 | 0% | 全表為空 |
| page | 0 / 80652 | 0% | 全表為空，無頁碼可追溯 |
| final | 7,216 / 80652 | 8.9% | 僅 `modern_rhyme` 由拼音填入 |
| tone | 80652 / 80652 | 100% | 唯一全滿 |

**結論：表名 `ph_readings`（讀音）與內容不符。** 實際內容是「字—韻部—調類」歸部記錄，
沒有任何擬音或注音。R2-08 報告稱「80,652 條讀音」屬**命名誇大**。
本輪新增只讀視圖 `v_ph_records_r2_09`，把 `reading_state` 明確標為 `NO_PHONETIC_VALUE`。

## 5 統計口徑矛盾

| 項目 | 值 | 來源 |
|---|---:|---|
| 平水韻行數 | 10662 | `ph_readings` |
| 平水韻不同字 | 8564 | `count(distinct charx)` |
| 平水韻韻目累計字數 | 10714 | `ph_rhyme_groups.sum(n_chars)` |
| 詞林正韻（R2-08 折算） | 11,382 | `ph_readings` |
| 詞林正韻（R2-09 原書字表） | 5563 | `ph_cilin_r2_09` |

同一部韻書出現 **8,116／8,361／8,564／10,662／10,714** 多個數字，
差別在於「算行」、「算字」、「算韻目累計」三種口徑混用。R2-09 於 `COUNTING_RULES.md` 定死口徑。

## 6 命名誇大與語義不符清單

| 欄位／表 | 問題 | 建議 |
|---|---|---|
| `ph_readings_r2_08.reading` | 全空，卻名為 reading | 改名為 `ph_rhyme_membership`，或保留但標 `NO_PHONETIC_VALUE` |
| `cipai_rhyme_dual_r2_08.observed_rhyme_behavior` | 名為 observed，實為「譜行符號＋括注」推導 | 本輪拆成 `scoreline_end_tone_sequence` 與 `notation_inferred_rhyme_behavior` |
| `cipai_forms_r2_07.rhyme_tone_source` | 全部 `PATTERN_LABEL_MIXED` 等值，未區分來源 | 需改為來源枚舉 |
| `cipai_forms_r2_07.declared_rhyme` | 實為**詞牌層級**說明，被當成該格的說明 | 本輪實測 196/196 皆等於詞牌層級值 |
| `cipai_form_variants_r2_07.derived_name` | 混存格標籤與別名 | 拆為 `variant_kind` 與 `alias_name` |
| `fanqie_upper`（廣韻 JSON） | 存的其實是反切**下字** | 改名 `fanqie_lower`，另立 `fanqie_upper` |
