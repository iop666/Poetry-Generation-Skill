# 《漢語音韻學》閱讀質量複核

## 1 為什麼要複核

R2-08 的 907 條記錄只驗證了「引文出現在該頁」，沒有驗證「概括是否忠實」。
本輪抽 120 條（U01–U13 每單元 ≥5，LOW 全取，優先 ARGUMENT／DEFINITION／HISTORY 與
「短引文長概括」者），由四個獨立子 Agent 逐條重讀原頁後給五項評價。

## 2 結果

| 判定 | 條數 | 佔比 |
|---|---:|---:|
| PASS | 81 | 67.5% |
| PARTIAL | 38 | 31.7% |
| FAIL | 1 | 0.8% |
| UNDECIDABLE | 0 | 0.0% |

嚴重度：S1（實質誤導）**2** 條、S2（表述不嚴）**19** 條、S3（無問題）**99** 條。

問題類型分佈：

| 類型 | 條數 |
|---|---:|
| ADDED_CONTENT | 10 |
| OVER_GENERALIZED | 7 |
| MISREAD | 6 |
| QUOTE_TRUNCATED | 5 |
| HYPOTHESIS_AS_FACT | 4 |
| OCR_GAP | 3 |
| SCOPE_DRIFT | 3 |
| TERM_CONFUSED | 1 |

## 3 三個最典型的錯誤

1. **把「有人說」寫成王力的定論**（`HYPOTHESIS_AS_FACT`）。例：記高本漢二等韻有後元音，
   卻漏掉王力緊接的「高氏後來已修正」按語。
2. **把一家之說當通說**（`OVER_GENERALIZED`）。例：漏「除 4、5 兩特徵外」的限定，
   把有條件的結論寫成「韻母近北方」。
3. **引文截斷抹掉否定**（`QUOTE_TRUNCATED`）。例：引文停在「雙聲假借之說更與」，
   恰好切掉王力接下來的否定。

## 4 「引文可核驗」與「觀點已複核」必須分開

| 層次 | 數量 | 狀態 |
|---|---:|---|
| 引文可在該頁定位 | 907 / 907 | 已驗證 |
| 觀點經人工複核 | 120 / 907（13.2%） | 本輪完成 |
| 複核通過 | 81 | PASS |
| 需修訂 | 39 | PARTIAL/FAIL |

**因此不得再用單一 `READ` 狀態代表全書已讀懂。** 建議狀態改為：
`EXTRACTED`（僅抽句）→ `QUOTE_VERIFIED`（引文已核）→ `CLAIM_REVIEWED`（觀點已核）→ `READ`（通讀並理解）。
本輪 907 條全部只到 `QUOTE_VERIFIED`，其中 120 條到達 `CLAIM_REVIEWED`，
其中 81 條通過、39 條需修訂。

## 5 頁碼體系的更正

R2-08 把 OCR `pages.jsonl` 的 `page` 直接標為 `page_pdf`。實際該欄是 **0-based 索引**，
真實 PDF 頁 = 索引 + 1。本輪用六個目錄錨點驗證：

| 目錄印刷頁 | OCR 索引 | 真實 PDF 頁 | 索引 − 9 = 印刷頁 |
|---|---:|---:|---|
| 1 | 10 | 11 | 1 ✓ |
| 81 | 90 | 91 | 81 ✓ |
| 117 | 126 | 127 | 117 ✓ |
| 352 | 361 | 362 | 352 ✓ |
| 25 | 34 | 35 | 25 ✓ |

故：**印刷頁 = 索引 − 9（正確）；真實 PDF 頁 = 索引 + 1（R2-08 少算 1）。**
所有引文的印刷頁引用不受影響，但「PDF 第 N 頁」的說法需 +1 才是真的 PDF 頁。

## 6 476 頁全頁賬本

| 區段 | 頁數 |
|---|---:|
| COVER_TITLE | 1 |
| COPYRIGHT_CIP | 3 |
| PUBLISHER_NOTE_COLLECTED | 1 |
| PUBLISHER_NOTE_VOLUME | 1 |
| FRONT_TABLE_OR_CHART | 1 |
| TOC | 3 |
| BODY_WITH_RECORD | 435 |
| BODY_TABLE_ONLY | 7 |
| BODY_QUOTATION | 1 |
| BLANK | 1 |
| INDEX | 22 |

未被解釋的頁：**%d**。R2-08 只統計了正文 444 頁（索引 10–453），
遺漏了卷首 10 頁與索引 22 頁，本輪已逐頁歸類（未解釋頁 0）。

## 7 音標複核

原索引 688 條（ə 589、e 99）。本輪新增一類判定 `LIKELY_BRACKET_ARTIFACT`：
部分 ə 實為 OCR 把左方括號 `[` 識成了 ə（表格行首、緊接元音處）。重分類結果：

| 書 | 新判定 | 條數 |
|---|---|---:|
| wangli_tongyuan | CONFIRMED_E | 62 |
| wangli_tongyuan | CONFIRMED_SCHWA | 366 |
| wangli_tongyuan | UNKNOWN | 90 |
| wangli_yinyunxue | CONFIRMED_E | 37 |
| wangli_yinyunxue | CONFIRMED_SCHWA | 64 |
| wangli_yinyunxue | LIKELY_BRACKET_ARTIFACT | 29 |
| wangli_yinyunxue | UNKNOWN | 40 |

**R2-08 稱 581 條 `CONFIRMED_SCHWA`，本輪只有 430 條能在音標語境中確認，
29 條疑似方括號誤識，130 條無音標語境可判。** 這是本輪對 R2-08 的一處實質修正。

## 8 未完成

50 組音標圖像目視只完成了規則分級，未逐組回原圖；120 條中 38 條 PARTIAL 尚未改寫 `claim`。