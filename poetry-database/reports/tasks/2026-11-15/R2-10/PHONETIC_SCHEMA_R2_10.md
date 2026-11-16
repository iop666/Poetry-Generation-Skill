# R2-10/B 音韻資料欄位規範（建議）

本輪不重建總表，只給出後續建表時的欄位契約，並標明「本項目當前能不能填」。

| 欄位 | 含義 | 本項目現狀 |
|---|---|---|
| `character` | 字（繁體為正） | 有 |
| `character_variant` | 異體／簡體 | 有（`ph_variants_r2_08` 15,527） |
| `rhyme_system_id` | 體系識別（OLD_CHINESE／MIDDLE_CHINESE／REGULATED_VERSE／CI_RHYME／YUAN_QU／MODERN） | 部分（只在 `system` 欄，且中古兩書混一） |
| `rhyme_group_id` | 韻目/部，需穩定 ID（如 `CILIN_11`） | **缺**（詞韻部名「第11部／第十一部」兩種寫法並存，JOIN 會失敗） |
| `tone_category` | 平／上／去／入／陰平／陽平 | 有（`tone`） |
| `phonetic_value` | 音值（IPA） | **全缺，不得偽造** |
| `initial` / `final` | 聲母／韻母 | **全缺** |
| `fanqie_upper` / `fanqie_lower` | 反切上下字 | 廣韻、集韻已有（R2-10 修正後） |
| `source_id` / `source_page` / `source_locator` | 來源定位 | 部分（集韻有 djvu 葉碼；平水/詞林/中原缺紙本頁） |
| `evidence_level` | 見證據分級 | 有 |
| `extraction_method` | 轉錄／OCR／派生／推定 | 有（`evidence_level` 內含） |
| `verification_status` | VERIFIED／PARSED／UNVERIFIED | 有 |
| `review_note` | 複核註記 | 部分 |

## 空值必須四分

`NOT_APPLICABLE`（該體系無此欄，如平水韻無反切）／`NOT_EXTRACTED`（有但沒抽）／
`UNKNOWN`（來源本身不明）／`NOT_VERIFIED`（抽了但沒核）。
**現行資料表把這四種都寫成 NULL，這是必須修的。**

## 建議的穩定 ID 規則

- 平水韻：`PS_上平_01` … `PS_入_17`
- 詞林正韻：`CILIN_01` … `CILIN_19`（另存 `display_name`＝原書寫法、`source_name`＝轉錄寫法）
- 中原音韻：`ZY_01` … `ZY_19`
- 廣韻：`GY_V{卷}_{韻序}`，如 `GY_V1_01`
- 集韻：`JY_V{卷}_{韻序}`

舊資料不改，新表用新 ID，另建映射表。
