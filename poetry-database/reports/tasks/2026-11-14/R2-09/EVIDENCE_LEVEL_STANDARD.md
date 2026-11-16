# 證據等級標準

## 1 八級定義

| 等級 | 含義 | 本輪是否出現 |
|---|---|---|
| `SOURCE_PRIMARY` | 原始文獻或可靠原書影印本直接證據 | **否（0 條）** |
| `SOURCE_EDITION` | 有明確版本信息的整理本或排印本 | 是（平水韻字表 10,662） |
| `SOURCE_TRANSCRIPTION` | 有明確出處的數字文本轉錄 | 是（廣韻 20,530／集韻 30,862／詞林正韻 5,563／中原音韻 5,731） |
| `OCR_DERIVED` | 從掃描圖像 OCR 得到，尚未逐項核實 | 是（王力兩書 1,167 頁） |
| `SECONDARY` | 後人研究、論文、字典或注釋資料 | 是（上古音書目 25 條） |
| `COMPUTED` | 程序根據其他數據推導 | 是（18,598 條） |
| `INFERRED` | 根據結構、上下文或規則推定 | 是（廣韻 20,451 條韻目歸屬） |
| `UNKNOWN` | 來源或結論無法確定 | 是（音標 130 處、例詞 114 條） |

## 2 關鍵判例

**`SOURCE_PRIMARY` 本輪為 0，這是刻意的。** 六套韻書全部來自維基文庫轉錄，
沒有一套與影印本逐頁對勘過。轉錄再忠實，也只是 `SOURCE_TRANSCRIPTION`。
只有當某一頁能同時出示「影印本圖」與「轉錄文字」且二者一致時，才可升為 `SOURCE_PRIMARY`。

**`INFERRED` 與 `SOURCE_TRANSCRIPTION` 必須分開。** 廣韻 20,530 條中，
只有 79 條的韻目來自韻目字本身（`YUNMU_HEAD`），其餘 20,451 條是「沿用前一條」（`CARRIED_FORWARD`）。
載體是轉錄文本，但**韻目歸屬是推定**，故 `yun_attribution` 記 `CARRIED_FORWARD` 而非直接來源。

**`COMPUTED` 不得冒充採錄。** 中華新韻 7,216 條由拼音按十四韻規則映射，
規則本身有依據（韻母歸部），但字表不是原書字表。凡此一律 `COMPUTED`。

## 3 映射結果

| 新等級 | 條數 | 佔比 |
|---|---:|---:|
| `SOURCE_TRANSCRIPTION` | 51392 | 63.7% |
| `COMPUTED` | 18598 | 23.1% |
| `SOURCE_EDITION` | 10662 | 13.2% |

## 4 每條記錄應帶的來源欄位

`source_id`、`source_title`、`source_author`、`source_edition`、`source_year`、
`source_page`、`source_locator`、`source_url`、`source_revision`、`original_text`、
`normalized_text`、`evidence_level`、`extraction_method`、`verification_status`、`review_note`。

現況：`source_revision` 在集韻為**空**（未記錄 revid，只有 HTML SHA-256）；
`source_page` 在六套韻書全為空。這兩項是本輪明確的不足。