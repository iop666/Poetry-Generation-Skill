# 資料字典（R2-09 候選研究層）

本輪新增 14 張表與 1 個視圖，全部以 `_r2_09` 後綴隔離，不覆蓋 R2-07／R2-08 任何表。

| 表 | 用途 | 主鍵 | 關鍵欄位 |
|---|---|---|---|
| `cipai_conflict_verdict_r2_09` | 33 條衝突逐條判定 | form_id | verdict, evidence |
| `cipai_rhyme_fields_r2_09` | 韻式七欄重構 | form_id | source_rhyme_label, source_rhyme_label_scope, scoreline_end_tone_sequence, example_observed_rhyme_behavior |
| `cipai_wordcount_r2_09` | 13 條字數五方對帳 | form_id | declared_num, scoreline_symbols, example_chars, recomputed_minus_declared |
| `example_work_links_r2_09` | 例詞關聯重判 | example_id | old_match_kind, new_match_kind, same_author, containment, score |
| `ph_cilin_r2_09` | 詞林正韻十九部逐字 | id | bu, tone, yunmu, is_half, charx, revision |
| `ph_cross_cases_r2_09` | 跨韻書差異 100 字 | charx | mc_group, rv_group, ci_bu, yq_bu |
| `ph_dup_analysis_r2_09` | 重複成因分類 | system+dup_kind | dup_groups, extra_rows, verdict |
| `ph_evidence_map_r2_09` | 舊 evidence_level → 新八級證據分級 | old_evidence_level | new_evidence_level, source_type, traceable_to_page |
| `ph_jiyun_r2_09` | 集韻 206 韻小韻（重建） | id | yun, head, fanqie_upper, fanqie_lower, declared_chars, html_sha256 |
| `ph_modern_audit_r2_09` | 拼音派生記錄與規則符合度 | id | rhyme_group, rule_yun, rule_match |
| `ph_modern_rule_r2_09` | 中華新韻十四韻韻母規則 | yun | finals, description |
| `ph_polyphone_r2_09` | 多音字跨體系對照 200 字 | charx | n_systems, middle_chinese, regulated_verse, ci_rhyme, yuan_qu |
| `ph_reading_stats_r2_09` | 每體系逐字段填充率與口徑 | system | rows_total, null_reading, distinct_chars, counting_note |
| `ph_zhongyuan_r2_09` | 中原音韻十九部逐字 | id | bu, tone, yinyang, charx |

## 視圖 `v_ph_records_r2_09`

把 `ph_readings_r2_08` 與新證據分級連接，並補三個誠實欄位：
`is_placeholder`（是否佔位符字頭）、`reading_state`（有無音值）、`is_derived`（是否程序推導）。

## 每個讀音記錄可追溯的欄位

| 需求 | 現況 |
|---|---|
| 書籍 | `source_book` |
| 版本 | 見 `source_book` 括注（如「四庫全書本·維基文庫轉錄」） |
| 卷次 | `volume`（僅中古音有；詞韻、新韻為空） |
| 韻目 | `rhyme_group` |
| 原始頁碼 | **空**（`page` 全表無值） |
| 具體記錄 | 集韻可回 `ph_jiyun_r2_09.html_sha256`；詞林正韻／中原音韻可回 `revision` |

**缺口**：`page` 全空，故沒有一條韻書記錄能直接指到紙本頁碼。這是本輪未能解決的硬缺口。