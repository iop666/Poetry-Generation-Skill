# 韻式字段重構與 33 條衝突裁定

## 1 R2-08 的字段有什麼問題

R2-08 自承 `observed_rhyme_behavior` 不是獨立的觀察。本輪查清了它的真實來源：

`cipai_rhyme_dual_r2_08.rhyme_evidence_level` **196 條全部是 `PATTERN_ANNOTATION_DERIVED`**，
即「譜行符號＋括注」的混合推導，不是純粹從符號推出。把它叫 `observed` 是誇大。

## 2 七欄重構

| 欄位 | 內容 | 來源 |
|---|---|---|
| `source_rhyme_label` | 原書明言的韻式分類 | 詞牌說明文字 |
| `source_rhyme_label_scope` | 該標籤屬於詞牌還是該格 | 本輪比對 form 與 entity 的說明 |
| `scoreline_symbol_sequence` | 譜行符號序列（不刪任何符號） | `source_text` |
| `scoreline_end_tone_sequence` | 逐句末符號的聲調序列 | 本輪計算 |
| `source_annotation_features` | 括注特徵計數（韵／句／豆／换） | 本輪計算 |
| `notation_inferred_rhyme_behavior` | 結合括注與符號的推導 | 本輪計算 |
| `example_observed_rhyme_behavior` | 由例詞實際韻腳查《詞林正韻》得來 | 本輪計算，無例詞則 NULL |

## 3 決定性發現：所有標籤都是詞牌層級

比對 `cipai_forms_r2_07.declared_rhyme` 與 `cipai_entities_r2_07.declared_rhyme`：
**196 / 196 完全相同。** 也就是說，R2-07 把詞牌說明文字複製到了每個格上，
包括那些韻式完全不同的格（如念奴嬌的平韻體、滿江紅的平韻體）。

因此 33 條「衝突」裡，有相當一部分不是原書自相矛盾，而是**標籤誤植**。

## 4 33 條裁定

| 判定 | 條數 | 含義 |
|---|---:|---|
| `SOURCE_ENTITY_LABEL_INHERITED` | 14 | 該格沿用詞牌層級說明，與譜行不符；譜行為準 |
| `EXAMPLE_CONTRADICTION` | 12 | 例詞實際韻腳與譜行推導不符 |
| `SOURCE_SCORELINE_SUPPORTED` | 3 | 例詞與譜行一致 |
| `MULTIPLE_INTERPRETATIONS` | 2 | 標籤、譜行、例詞三者不完全一致 |
| `INSUFFICIENT_EVIDENCE` | 1 | 無可用例詞 |
| `TERM_CATEGORY_MISMATCH` | 1 | 三者屬不同名目（通叶／轉換／錯叶），不能二分 |

**沒有任何一條被強行歸零。** 14 條判定為「標籤誤植」，12 條判定為「例詞與譜行不符」，
其餘保留為多解、名目混用或證據不足。

## 5 仍不能下的結論

即使判定「標籤誤植」，也不能就此說某格的韻式已確定。因為：

1. 例詞的韻腳是按「譜行句長對齊正文」取的，遇襯字會錯位一至二字；
2. 《詞林正韻》字表只覆蓋平水韻 57%，查不到部的字被跳過，會影響平仄判定；
3. 通叶／轉換／錯叶三類在學界本身有不同用法，本輪只能沿用龍榆生的分節標題。