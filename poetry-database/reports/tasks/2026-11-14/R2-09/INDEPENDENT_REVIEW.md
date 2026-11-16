# 獨立審查結果摘要

## 1 抽樣

由獨立子 Agent 在不知情主 Agent 結論的情況下自選樣本，六類共 135 條：

| 類別 | 條數 | AGREE | DISAGREE | 一致率 |
|---|---:|---:|---:|---:|
| B_reading | 30 | 27 | 3 | 90.0% |
| C1_jiyun | 30 | 30 | 0 | 100.0% |
| C2_guangyun | 30 | 29 | 1 | 96.7% |
| E1_image | 15 | 15 | 0 | 100.0% |
| E2_conflict | 10 | 8 | 2 | 80.0% |
| F_link | 20 | 13 | 7 | 65.0% |

**總一致率 90.4%，爭議 13 條。**

## 2 爭議清單（完整）

| 類別 | 對象 | 審查方 | 主 Agent | 爭點 |
|---|---|---|---|---|
| B_reading | RA-006 | PASS | PARTIAL | claim 十韻音值與表列一一相符：真 iěn、諄 iuěn、臻 iɛn、文 iuən、欣 iən、元 iən、魂 uən、痕 ən、寒 an、桓 uan。主 Agent 因 qu |
| B_reading | RA-012 | PASS | FAIL | 聲調表明列平清→陰平、平濁→陽平、上全濁→去、上清次濁→上、去→去、入全濁→陽平、入次濁→去、入清→陰陽上去，claim 全合。主 Agent 自承「claim 無誤」，僅因 qu |
| B_reading | RA-084 | PARTIAL | PASS | 引文與頁文逐字相合，但前頁僅列錢玄同為數人會成員（true_pdf_page 367），未署此段 G.R. 說明；同類無署名歸屬 RA-013 主 Agent 判 PARTIAL， |
| C2_guangyun | GY-004276 | FAIL | PARTIAL | 此條注文實含「崇𤣥切……文一」，是有反切、有字數的小韻首，程式未從 meaning 解析；主 Agent 記「無反切（非小韻首）」與原文不符，應由 PARTIAL 升為 FAIL（ |
| E2_conflict | F07-0171 | UNDECIDABLE | EXAMPLE_CONTRADICTION | 譜行明作 仄韵→换平韵→再换仄韵→再换平韵，是四換韻，主 Agent 推導為「平仄錯葉」已偏；又稱「例詞實際為平仄通葉，與原書標籤平仄轉換相符」，然通葉（同部平仄通押）與轉換（換韻 |
| E2_conflict | F07-0187 | UNDECIDABLE | EXAMPLE_CONTRADICTION | 譜行為 仄韵→叶仄→平韵→换仄韵→叶仄→叶平，主 Agent 推導為「平仄轉換」，而 section 標籤為「平仄錯葉」；又稱例詞「平仄通葉」與標籤「錯葉」相符，實則通葉與錯葉有別 |
| F_link | EX-0003 | VERIFIED_VARIANT | POSSIBLE_MATCH | 例詞與作品僅「晚/遠」一處實詞異文，及「陽/阳」繁簡異寫，其餘 24 字全同；作者張泌、title 南詞子・柳色遮樓暗完全對應。應判 VERIFIED_VARIANT，POSSIB |
| F_link | EX-0004 | VERIFIED_VARIANT | POSSIBLE_MATCH | 例詞與作品僅「原/元」一處異文，其餘 51 字全同，作者呂本中、title 南歌子；CSV 记 ex_len 56 係夾入「18」OCR 雜訊。應判 VERIFIED_VARIAN |
| F_link | EX-0010 | VERIFIED_EXACT | POSSIBLE_MATCH | 例詞去標點及 OCR 雜訊「21」後與作品 27 字全同（ratio 1.0），作者李煜、title 搗練子令・深院靜；舊判亦為 EXACT_MATCH。降為 POSSIBLE 無 |
| F_link | EX-0005 | NO_MATCH | TITLE_ONLY | 例詞為張志和《漁歌子》27 字；所指作品為徐俯《浣溪沙》42 字，僅嵌入例詞句子並增「一波才動萬波隨」「黃帽豈如」等，調名、作者、全文均不同。既非同名，應判 NO_MATCH（可註 |
| F_link | EX-0019 | VERIFIED_VARIANT | AUTHOR_CONFLICT | 例詞作者「寇準」、作品作者「寇准」僅繁簡異寫，實同一人，same_author 卻記 0；文字僅「斷/遠」「蘋/苹」二處。應判 VERIFIED_VARIANT，AUTHOR_CO |
| F_link | EX-0025 | VERIFIED_VARIANT | AUTHOR_CONFLICT | 例詞作者「晏幾道」、作品「晏几道」僅繁簡異寫，實同一人，same_author 記 0；文字僅「與/似」一字。應判 VERIFIED_VARIANT，AUTHOR_CONFLICT |
| F_link | EX-0006 | VERIFIED_VARIANT | NO_MATCH | 劉禹錫《憶江南》「春去也！多謝洛城人……」27 字，works 中 tang:c5c080df1b73《憶江南 一》劉禹錫全篇即此詞，僅顰/嚬異寫，卻記 NO_MATCH、work |

## 3 已據此修正的三處

獨立審查不是走過場，本輪據其意見實質改了程式：

1. 例詞關聯的作者比對加入 OpenCC 繁簡正規化（修 5 條假 AUTHOR_CONFLICT）。
2. 例詞文本先剔除 OCR 頁碼再比對（VERIFIED_VARIANT 由 90 升至 116）。
3. 韻式裁定新增 `TERM_CATEGORY_MISMATCH`，不再把通叶／轉換／錯叶混稱「相符」。

## 4 未採納的爭議

RA-012、RA-006 兩條，審查方認為應判 PASS，理由是我方代理人只憑引文取錯位置就判 FAIL。
我方保留原判，理由：記錄的問題不只是引文位置，而是 `claim` 與引文不匹配——
引文講紐表，claim 講聲調，即使 claim 本身對，這條記錄也不能算合格。
兩說並存，列入爭議，由外部審核裁決。