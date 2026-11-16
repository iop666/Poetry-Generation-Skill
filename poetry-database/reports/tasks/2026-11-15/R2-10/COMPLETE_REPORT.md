# R2-10 完整報告：基礎數據關鍵缺陷閉環與原典證據重建

> 任務編號：R2-10
> 前置審核：R2-09 外部審查（PARTIAL，不批准進入 Phase 3）
> 執行日期：2026-11-15
> 工作目錄：`<PROJECT_ROOT>/`
> 資料庫：`poetry-database/database/poetry.db`
> 執行前：704,974,848 位元組（672.32 MiB），SHA-256 `3f858d9252ccc2c1f1045e7e7c4a843295bcf3ec82b6c8c9308f868733dd8f3a`
> 執行後：709,943,296 位元組（677.05 MiB），SHA-256 `cddcc659104730895daf51902b96c7e73cbf86d0d01f6d45734c195200b2a50a`
> 版本管理：無 Git；新增資料一律 `_r2_10` 後綴，R2-07／08／09 表未改

---

## 1 任務信息

本輪是「缺陷修復 + 原典對勘」的專項，不是擴充資料。九個工作包全部執行，結果如下表。

| 包 | 內容 | 狀態 |
|---|---|---|
| 0 | 執行前凍結：位元組、雜湊、頁數、完整性、WAL、磁碟 | 完成 |
| A | R2-07～R2-09 歷史數字對帳 | 完成（12 組，逐組給出「是否可復算」） |
| B | 音韻資料語義重建 | 完成（證實無音值，建語義視圖） |
| C | 廣韻反切與韻目修復 | 完成（4,658 條上下字修正；202/206 韻位置直證） |
| D | 集韻來源、小韻、字數對帳 | 完成（206/206 revid 與 djvu 葉碼；三個小韻數完全對帳） |
| E | 六套韻書來源與字級 | 完成（逐套列出缺口） |
| F | 60 條詞譜符號核驗 | 部分完成（49 條符號一致，11 條文字層殘缺） |
| G | 閱讀記錄與音標 | 部分完成（39 條缺陷全部處理；音標 50 組回圖未做） |
| H | 例詞、精讀、版本對勘 | 部分完成（30 首重寫、10 首對勘；100 條逐條複核未做） |
| I | 上古音 | 部分完成（40 例分類，22 例有依據） |
| J | 跨韻書查詢 | 完成（30/30 執行，5 個錯誤前提測試） |
| K | 獨立審查與測試 | 完成（70 條交叉複核；82 項新測試） |

**自我申報：`PARTIAL`。**

---

## 2 執行前狀態

- 資料庫 704,974,848 位元組，`integrity_check=ok`，`foreign_key_check` 無錯，
  `page_count×page_size` 與檔案大小完全相符，`freelist_count=0`，無 WAL／SHM 殘留。
- 表 79 張、視圖 1 個、索引 65 個；可用磁碟 57.63 GiB。
- R2-07／08／09 三代表共 36 張，全部保留未刪。

**關於「690／670／672 MB」**：R2-08 的「690 MB」無位元組、無雜湊、無測量方式，
且大於當前 672.32 MiB，而資料只增不減，故判 `UNVERIFIABLE`。
本輪只能以 `cddcc65910473089…` 作為此後唯一基準，**不聲稱歷史上發生或未發生過 VACUUM**。

---

## 3 各工作包結果

### 3.1 A 歷史數字對帳

12 組數字全部給出「統計對象／算法／頁集／可否復算」。核心結論：

- 《集韻》小韻 **4,344／4,432／4,169** 不是三次測量，而是「兩算法 × 兩頁集」。
  本輪找到乾淨基準：206 頁共 **4,442 個「○」標記**。
  `4,442 − 10（未成段） = 4,432`；`4,442 − 273（不足 6 字或缺首字） = 4,169`。
- **4,344 與 51,803 無法逐位復原**：那 4 個 HTTP 429 失敗頁已被補抓**原地覆蓋**，
  202 頁快照已不存在。這是資料治理教訓：失敗頁應保留失敗態快照，不應覆蓋。
- 《集韻》字數六值關係：`53,525（原書自述） ≈ 53,952（全頁文N求和，+0.8%）`；
  `52,983（舊法206頁）`、`51,803（舊法202頁）`、`50,132（首文N之和）`、`49,084（字頭估計）`。
- 平水韻五值：**8,564 = 繁體字頭**（唯一可稱「字頭」者）、10,662 = 記錄、8,361 = 簡體字頭、
  10,714 = 韻目累加（含重複）、8,116 = Phase 0 舊值（作廢）。
- 例詞 **196 = 310 − 114(NO_MATCH)**，是「有候選」不是「可信」；真正 VERIFIED 只有 **166**。

### 3.2 B 音韻資料語義

- `ph_readings_r2_08` 共 80,652 行，`reading`／`initial`／`page` **三欄 100% 為空**。
  該表記錄的是「字—韻部—調類」，**無任何音值**。R2-08 稱「80,652 條讀音記錄」屬命名誇大。
- 分類：韻部歸屬 38,247 行、
  帶反切 35,189 行、拼音派生 7,216 行。
- 新發現：**廣韻與集韻共用 `system='middle_chinese'`**，只能靠 `source_book` 區分（T45/T46 守住）。
- 佔位符 3,660 條（17.8%），僅統計隔離，**未由反切反推字形**。
- 建視圖 `v_ph_semantics_r2_10`（80,652 行），舊表未改。

### 3.3 C 廣韻反切與韻目

**反切**：
- 舊 `fanqie_upper` 在 4,658/4,771 條存的是**下字**；本輪按定義重拆（上字＝第 1 字，下字＝第 2 字），
  逐條保留 `evidence` 與 `char_offset`，舊值存 `old_fanqie_upper`。
- 113 條反切本身只有 1 字（`偽切`），標 `INCOMPLETE_ONE_CHAR`，不猜不補。
- **沒有做「全部對調」**：先重建再比對，避免把原本正確的 113 條也弄錯。

**韻目**：
- 以「卷內韻序 + 韻名」在正文中逐一定位，得 **202/206** 個韻目的字符偏移；
  4 個未錨定（添／㫖／狠／𠋫，字形為異體罕字）。
- 每條小韻的韻目由**所在位置**決定（`HEADER_DIRECT`），不再用 `CARRIED_FORWARD` 推定。
- 結果：4,122 條韻目不變、**202 條改變**、447 條 `UNRESOLVED`
  （其中 211 條落在「中間有未錨定韻」的區段，236 條字頭定位失敗）。
- 錯掛呈**連續段**形式 147 段，≥5 條者僅 2 段。
  **R2-09 所稱「16 個韻整段錯掛」未獲系統證實，降級為抽樣觀察。**

**更嚴重的一個發現**：舊判據「注文含切即小韻首」把又音條目也算進來。
嚴格判定（反切須在注文最前端且不以「又」起頭）得 **2,907** 條，
又音條目 1,416 條，無反切 448 條。**「4,771 小韻」作廢。**

### 3.4 D 集韻

- **206/206** 韻頁取得 MediaWiki `revid`（R2-09 為 0/206），
  且 206/206 有四庫全書 djvu 定位（冊號＋葉碼區間），例如「文淵閣四庫全書_0236冊.djvu，葉1825a續–1837b」。
- 小韻：頁面「○」4,442 → 舊法 4,432 → 新法 4,169，完全對帳。
- 字數：全頁「文N」求和 53,952，與原書自述 53,525 相差 0.8%；
  首文N之和 50,132；字頭估計 49,084（`COMPUTED`，非原書數）。
- **R2-09 的集韻反切也被寫錯**：`fanqie_upper` 存整串（如「徳紅」），4,169 條中 3,967 條如此。
  本輪建 `jiyun_small_rhyme_audit_r2_10` 修正。
- 120 條人工複核沿用：OK 93／PARTIAL 13／FAIL 14；其中 111 條可回填到 4,169 條表。

### 3.5 E 六套韻書

| 體系 | 記錄 | 去重字 | 韻目/部 | 反切 | 證據等級 |
|---|---:|---:|---:|---:|---|
| 廣韻 | 20,530 | 12,448 | 190 | 5,011 | `SOURCE_TRANSCRIPTION` |
| 集韻 | 30,862 | 14,740 | 202 | 30,178 | `SOURCE_TRANSCRIPTION` |
| 平水韻 | 10,662 | 8,564 | 106 | 0 | `SOURCE_EDITION` |
| 詞林正韻 | 5,563（新）／11,382（舊折算） | 5,048 | 19 | 0 | `SOURCE_TRANSCRIPTION` |
| 中原音韻 | 5,731 | 5,183 | 19 | 0 | `SOURCE_TRANSCRIPTION` |
| 中華新韻 | 7,216 | 7,216 | **13**（規則 14） | 0 | `COMPUTED` |

- **中華新韻「十四韻」實為 13 韻**：「十三支」0 條，因支韻為整體認讀音節，韻母規則無法生成。
- 詞林正韻「半」426 條（9 個半韻目），與 R2-08 的 1,572 條折算不是同一概念。
- 詞林正韻覆蓋平水韻字 57.4%，**不把「補到 95%」當指標**。

### 3.6 F 詞譜符號核驗

- 改用 PyMuPDF 直接讀 PDF 文字層，抽「符號＋括注」連續片段，按括注切句，
  與 `sentence_lengths`／`ann_sequence` **逐句符號比對**。
- **49 條 MATCH**（句數、每句符號數、括注序列全對）；**11 條 `TEXTLAYER_FRAGMENTED`**（文字層缺符號）。
- 11 條的具體原因已逐條記錄：如西江月本頁只有 3 句、其餘在次頁仍不完整；渡江雲缺前 9 句。
- **不能說「60/60 完成」**。可說：「60 條全部有結論，49 條逐符號一致，11 條未決。」
- 限度必須聲明：本輪是「解析器 vs 文字層」，不是「文字層 vs 印本字形」。

### 3.7 G 閱讀與音標

- 39 條 PARTIAL/FAIL 全部處理：**37 條改寫 claim**、**2 條 `UNDECIDABLE`**（頁文截斷）。
- 新抽 **65 條**未審記錄：PASS 57／PARTIAL 8／FAIL 0，S1 僅 1 條。
- 476 頁全部有分類，未解釋頁 0。
- 音標 688 條四類守恆（430＋29＋130＋99），**但 50 組回圖核驗未做**，如實標 `NOT_PERFORMED`。
- 頁碼標準：`pdf_page = ocr_index + 1`、`printed_page = ocr_index − 9`，六個目錄錨點全驗。

### 3.8 H 例詞與精讀

- 310 條重判：VERIFIED_EXACT 50 ＋ VERIFIED_VARIANT 116 = **166**；
  NO_MATCH 114；POSSIBLE 19；AUTHOR_CONFLICT 6；TITLE_ONLY 5。
- 30 首精讀卡**重寫**（12 項內容：章法、意象、煉字、用典、韻律、藝術特點），
  另指出舊卡 20 處錯誤（11 處誤判、9 處未發現的庫內錯字）。
- **10 首找到獨立版本對勘**：2 首完全一致、3 首小異、5 首顯著異文。
  最重要的兩處：〈靜夜思〉四庫本作「牀前看月光…舉頭望山月」；
  〈聲聲慢〉四庫《漱玉詞》作「曉來風急」而非「晚來風急」。
- 100 條逐條複核未做（僅 20 條由獨立 Agent 複核）。

### 3.9 I 上古音

- 40 例重新分類：22 例 `SCHOLAR_IDENTIFIED_RHYME`（有可查依據）、13 例 `POSSIBLE_RHYME_POSITION`、
  5 例 `LINE_END_CANDIDATE`、0 例 `SOURCE_VERIFIED`。
- 舊記錄最大錯誤是「兮前找韻」與「剝掉天問的『之』」，已在報告舉 5 例說明。
- 書目 36 條（CONFIRMED 13／LIKELY 20／NOT_FOUND 3）。
- 《詩經韻讀》《楚辭韻讀》仍無合法全文，**未建任何上古字音記錄**。

### 3.10 J 查詢

- 30 個查詢全部實際執行，30/30 有結果，0 報錯，SQL 與結果逐條存檔。
- 5 個「錯誤前提」測試（如問中古音音值），確認系統不會把韻部歸屬冒充音值。
- 已寫明能力邊界：**能答「屬哪韻、哪調、反切是什麼」，不能答「怎麼讀」。**

### 3.11 K 獨立審查與測試

- 70 條交叉複核：AGREE 32／DISAGREE 37／UNDECIDABLE 1，一致率 **45.7%**。
  集韻 0%（同一欄位缺陷乘 25 次）、廣韻 60%、例詞 85%。
- **獨立審查發現主 Agent 一個系統性錯誤**：R2-09 宣稱「集韻反切已按正確定義拆分」，
  實際 `fanqie_upper` 存整串。本輪已修。
- 82 項新測試：**80 通過、2 失敗**（T12 有 4 個錨定韻下無小韻；T60 只有 4 個 system 值）。
- 舊 71 項測試原樣重跑：**71 全通過**，無回歸破壞。

---

## 4 歷史數字對帳匯總

| 指標 | 舊值 | 本輪 | 狀態 |
|---|---|---|---|
| 集韻小韻 | 4,344／4,432／4,169 | 4,442（○）→4,432→4,169 | 全部可解釋 |
| 集韻字數 | 31,043／51,803／49,084 | 53,952／52,983／50,132／49,084 | 六值關係已明 |
| 平水韻字頭 | 8,116／8,361／8,564 | **8,564（繁）** | 8,116 作廢 |
| 廣韻小韻 | 4,771 | **2,907 嚴格**（另 1,416 又音） | 4,771 作廢 |
| 廣韻韻目歸屬 | CARRIED_FORWARD 20,451 | HEADER_DIRECT 4,324／UNRESOLVED 447 | 推定改為直證 |
| 例詞可信關聯 | 196 | **166** | 標籤誤用已糾 |
| 詞譜符號核驗 | 60/60 | **49 MATCH／11 未決** | 誇大已糾 |
| 音標 | 688 | 688（四類守恆） | 一致 |

---

## 5 資料庫結構變化

新增 5 張表與 1 個視圖，全部 `_r2_10` 後綴；**未修改任何 R2-07／08／09 表**。

| 物件 | 行數 | 用途 |
|---|---:|---|
| `guangyun_fanqie_r2_10` | 20,530 | 廣韻條目、反切上下字、韻目位置直證、`head_kind` |
| `guangyun_yunmu_repair_r2_10` | 206 | 206 韻目錨定與定位方式 |
| `jiyun_page_provenance_r2_10` | 206 | 集韻每頁 revid、djvu 葉碼、SHA-256 |
| `jiyun_small_rhyme_audit_r2_10` | 4,169 | 集韻小韻，反切上下字修正版 |
| `cipai_symbol_audit_r2_10` | 60 | 詞譜符號級核驗 |
| `v_ph_semantics_r2_10`（視圖） | 80,652 | 音韻資料語義分類 |

未建立規格書中列出的其餘建議表（如 `reading_claim_revisions_r2_10`、`cross_system_query_r2_10`），
因為對應資料已由 CSV 承载，**不建空表充數**。

---

## 6 資料變更明細

| 項 | 本輪新增 | 歷史累計 | 上一輪 | 增量 |
|---|---:|---:|---:|---|
| 廣韻條目重算 | 20,530 | 20,530 | 20,530 | 全量重算（非新增） |
| 廣韻反切修正 | 4,658 | 4,658 | 0 | +4,658 |
| 廣韻韻目位置直證 | 4,324 | 4,324 | 0（全部推定） | +4,324 |
| 集韻頁來源（revid+djvu） | 206 | 206 | 0 | +206 |
| 集韻小韻修正 | 4,169 | 4,169 | 4,169 | 全量重算 |
| 詞譜符號核驗 | 60 | 60 | 0（僅結構） | +60 |
| 閱讀 claim 改寫 | 39 | 159（120+39） | 120 | +39 |
| 閱讀新抽樣 | 65 | 65 | 0 | +65 |
| 精讀卡重寫 | 30 | 30 | 30（未重評） | 全量重寫 |
| 獨立版本對勘 | 10 | 10 | 0 | +10 |
| 上古韻例分類 | 40 | 40 | 40（未分類） | 全量重分類 |
| 查詢樣例 | 30 | 60 | 30 | +30 |
| 新增表 | 5＋1 視圖 | 41 表 | 14 | +5 |
| 自動化測試 | 82 | 153 | 71 | +82 |

資料庫大小：704,974,848 → 709,943,296 位元組（+4,968,448）。

---

## 7 真實來源與證據等級變化

| 等級 | 本輪之前 | 本輪之後 |
|---|---|---|
| `SOURCE_PRIMARY`（原書影印直接證據） | 0 | **0**（未取得任何影印本原件） |
| `SOURCE_EDITION` | 10,662 | 10,662 |
| `SOURCE_TRANSCRIPTION` | 51,392 | 51,392 |
| 新增：帶 djvu 葉碼定位的轉錄 | 0 | **206 頁**（集韻） |
| `COMPUTED` | 18,598 | 18,598 |

**`SOURCE_PRIMARY` 仍為 0** 是本項目最重要的證據邊界：所有韻書資料都來自數字轉錄，
無一條與影印本逐字對勘。

---

## 8 實際執行命令

```
python3 tools/r2_10_preflight.py
python3 tools/r2_10_guangyun_align.py
python3 tools/r2_10_fix_fanqie.py
python3 tools/r2_10_jiyun.py
python3 tools/r2_10_symbol_verify.py
python3 tools/r2_10_crop.py raw/r2_10/symbols/fragmented15.json fr
python3 tools/r2_10_b_e_j.py
python3 tools/r2_10_g_input.py
python3 tools/r2_10_facts.py
python3 tools/r2_10_reports_csv.py
python3 tools/r2_10_tests.py
python3 tools/r2_09_tests.py        # 回歸
```

---

## 9 測試結果

```
R2-10 tests: 82 PASS 80 FAIL 2
  FAIL T12 每個錨定韻都有小韻（無空韻） expect 0 actual 4
  FAIL T60 六套體系未被合併成單一平仄字典 expect 6 actual 4
```

舊測試回歸：

```
tests 71 PASS 71 FAIL 0
```

**兩個 FAIL 是真实缺陷，未修改期望值以換取通過。**
T12：4 個已錨定韻下小韻全部定位失敗；T60：`ph_readings_r2_08` 只有 4 個 `system` 值。

---

## 10 獨立審查結果

| 類 | 樣本 | 一致 | 爭議 |
|---|---:|---:|---:|
| 集韻小韻 | 25 | 0 | 25 |
| 廣韻反切 | 25 | 15 | 9 |
| 例詞關聯 | 20 | 17 | 3 |
| 合計 | 70 | 32 | 37 |

爭議全部逐條記錄於 `INDEPENDENT_REVIEW_R2_10.csv`（含閱讀與詞譜共 140 行）與
`raw/r2_10/independent/INDEPENDENT_REVIEW_R2_10_part.md`。
本輪據其意見修正三處：集韻反切、廣韻小韻首判定、韻式衝突判定用語。

**獨立性限制**：集韻與廣韻複核與主 Agent 共用同一份轉錄文本，只能驗「處理是否正確」，
不能驗「轉錄本身是否正確」。

---

## 11 未完成與阻塞

| 項 | 狀態 | 原因 |
|---|---|---|
| 11 條詞譜符號核驗 | `UNDECIDABLE` | PDF 文字層缺符號；目視轉寫在本環境不可靠 |
| 集韻 4,169 條全人工複核 | 111/4,169 | 時間 |
| 廣韻 150 條人工抽檢 | 25/150（獨立 Agent） | 時間 |
| 詞林正韻 150 字回原書 | 0 | 無影印本 |
| 中原音韻 150 字抽檢 | 0 | 時間 |
| 中華新韻 200 字抽檢 | 0 | 時間 |
| 音標 50 組回圖 | 0 | 時間與工具 |
| 例詞 100 條逐條複核 | 20 | 時間 |
| 30 首精讀全部版本對照 | 10/30 | 其餘 20 首未找到獨立版本 |
| 上古音歸部 | 22/40 | 缺《詩經韻讀》《楚辭韻讀》 |

---

## 12 本輪發現的新問題

1. **集韻反切上字存整串**（R2-09 的自我宣稱錯誤），3,967/4,169 條受影響。
2. **廣韻「小韻首」含又音條目**，基數 4,771 虛高，嚴格判定 2,907。
3. **廣韻與集韻共用 `system='middle_chinese'`**，按體系統計必然串書。
4. **中華新韻「十四韻」實為 13 韻**，十三支為 0。
5. **PDF 文字層對部分譜行不完整**（11/60），這解釋了為何 R2-09 的目視核驗會「看起來對不上」。
6. **失敗頁原地覆蓋**導致 202 頁快照不可復原，是資料治理缺陷。
7. **例詞抽取把詞牌說明吞進正文**（浪淘沙格一 127 字），影響字數判斷。

---

## 13 自我審計

1. **「202/206 韻錨定」是我用啟發式定位得到的，不是原書逐頁核對。** 4 個未錨定韻之外，
   其餘 202 個的邊界仍可能有 ±1 條的偏移，我沒有逐個驗。
2. **447 條 `UNRESOLVED` 我沒有再想辦法救。** 其中 236 條是字頭為 `□` 導致定位失敗，
   本可用上下文推測，但推測就是猜，我選擇留空。
3. **60 條詞譜的「符號級」是對文字層，不是對印本。** 我一度想用視覺模型補足，
   但它在 200dpi 上把「＋」拆成「｜－」，這種「核驗」會製造假差異，所以放棄。
4. **獨立審查只有 70 條，佔母體不到 2%。** 且它與我共用轉錄文本，獨立性有限。
5. **82 項測試裡約 30 項是「用自己的口徑量自己的資料」**，通過不構成外部驗證。
6. **30 首精讀卡的韻部判斷有多處 `UNKNOWN`**，我沒有為了填滿欄位而硬判。
7. **我沒有解決「詞林正韻 3,650 字缺口」**，且我認為不該用平水韻反推——這是判斷，不是能力不足。
8. **兩個測試 FAIL 我沒有修。** T12 的 4 個空韻本可補，但補了就是掩蓋；T60 是結構問題，非一輪能改。

---

## 14 下一輪建議

| 建議 | 目標 | 驗收 | 風險 |
|---|---|---|---|
| R2-10-R1 | 詞譜 11 條未決改以 600dpi 單行圖＋人工判讀 | 11 條全部有符號級結論 | 需人工，不能自動化 |
| R2-10-R2 | 廣韻 `□` 字頭 3,660 條與影印本對照恢復字形 | 恢復率 ≥50% | 需四庫影印本 |
| R2-10-R3 | 集韻 4,169 條全量人工複核（現 111） | 100% 有 `OK/PARTIAL/FAIL` | 工時大 |
| R2-10-R4 | 建立穩定 `rhyme_group_id`（CILIN_11 等）並重寫跨書查詢 | 跨書 JOIN 不再失敗 | 需改寫查詢層 |
| R2-10-R5 | 詞林正韻、中原音韻、中華新韻各 150–200 字回原書抽檢 | 三套各有抽檢記錄 | 需原書 |
| R2-11 | 文學理論與審美（意境、章法、煉字、用典） | 依審核方針 | — |

---

## 15 最終結論

**SELF_STATUS：`PARTIAL`。**

本輪實質完成了四件事：

1. **止損**：《廣韻》反切上下字全反已修正（4,658 條），並發現「4,771 小韻」基數本身錯誤
   （嚴格 2,907）；舊 `fanqie_upper` 一律標為不可用於聲母推導。
2. **對帳**：《集韻》三個小韻數、六個字數全部給出可復算的關係；
   206 頁取得 revid 與四庫 djvu 葉碼，來源可指到「哪一冊哪一葉」。
3. **語義**：證實「80,652 條讀音」實為韻部歸屬，本庫無任何音值；建語義視圖以防誤用。
4. **原典**：60 條詞譜中 49 條逐符號一致、11 條如實標未決；30 首精讀重寫、10 首找到獨立版本並發現 5 首顯著異文。

同時明確未達標：詞譜 11 條未決、集韻人工複核僅 111 條、音標回圖 0 組、
`SOURCE_PRIMARY` 仍為 0、2 項測試如實失敗。

**不進入 Phase 3，不改 `gedou.py`，不封裝 Skill，等待外部審核。**

---

## 附錄 C：交付文件清單（絕對路徑、位元組、SHA-256）

目錄：`<PROJECT_ROOT>/poetry-database/reports/tasks/2026-11-15/R2-10`

`COMPLETE_REPORT.md` 自身雜湊另存 `COMPLETE_REPORT.sha256`（檔案不能包含自身雜湊）。

| 檔案 | 位元組 | SHA-256 |
|---|---:|---|
| `ANCIENT_PHONOLOGY_SOURCE_INDEX.csv` | 19,476 | `95b890213ff790c9164b9bdfd039e36b965eb886070ffa65d799e9017ded3158` |
| `ANCIENT_PHONOLOGY_UNRESOLVED.md` | 9,116 | `d7791ad50ec8d4ecd7d041f8a66270232c7d58cec79fea0afbacfe0d997cc0ed` |
| `ANCIENT_RHYME_40_REAUDIT.md` | 16,515 | `623f328511a07a754d9b9c9a44d71cbc2d4953e0320a951e004726b521146c9d` |
| `CHUCI_10_CASES_R2_10.csv` | 15,938 | `ecca9a244be66f7a2861fbdf2059b341248a2e817b439b1865216c5019ac58ee` |
| `CILIN_5563_AUDIT.md` | 1,630 | `f9bccb6e1eb13e6f47c3666b0eee5cfba963fbd1a00f51e0aa4ca73fdd35ac6e` |
| `CIPAI_10_CROSS_PAGE_RECHECK.csv` | 6,313 | `caa47a3a2fa6f4f0a4a62a57087f169950433fe137e0f874165731fc455c0adc` |
| `CIPAI_13_WORDCOUNT_FINAL_AUDIT.csv` | 1,440 | `aa03a1420f5b06b43ce8315db5a89eef4c4986a2e72c52173e099990ad1f18bf` |
| `CIPAI_33_CONFLICT_REAUDIT.csv` | 9,284 | `3986501e41e9f8102f269c8a5cccd56b008b05b3910a0501fc1d5b777680597c` |
| `CIPAI_60_SYMBOL_LEVEL_AUDIT.md` | 1,969 | `e5885f845e3636470eab8c6bbab6e6bd2400bb9f92580ce66efc73d8fba0beb3` |
| `CIPAI_60_SYMBOL_VERIFICATION.csv` | 38,952 | `2e6e2390e075ca6fd16984c1b1670b57bb29f83c96545771d7dd60743a0d3355` |
| `CIPAI_SOURCE_TEXT_BOUNDARIES.csv` | 283 | `43f7410574f5c39d5c4b6f0a418ee6755867367c3ffafa895b2622db515610fa` |
| `CROSS_ROUND_METRIC_RECONCILIATION.csv` | 3,163 | `0d88be1a5a3d0391911e6b57ceea11a9910874b39a08c6b9cde75f7e6ff702be` |
| `CROSS_ROUND_METRIC_RECONCILIATION.md` | 5,692 | `a4f610e0d6c197e53e45ad4d0186683f389fa50ba8350af3f7e74393b479b909` |
| `CROSS_SYSTEM_100_FINAL_AUDIT.csv` | 13,109 | `a4b59f5856389838a2c003fb702cdc0da10f1934e20e715a5f2dd340d4c88689` |
| `CROSS_SYSTEM_QUERY_LIMITATIONS.md` | 1,388 | `9f20c4a4c84f1f41776011e43a9bef3cc10bc83214e0cbe7c7e46afa0203cd1d` |
| `EXAMPLE_100_INDEPENDENT_REVIEW.csv` | 50,623 | `117b7f51ba9f20864b67165b90caf6d811835f832c98a6b1c66707936f69a2d9` |
| `EXAMPLE_310_FINAL_STATUS.csv` | 37,674 | `e79f5c603c9f3307cbaa397d9e9d448bf2ab766f8d25035ae18bcb8f062b830c` |
| `GUANGYUN_206_RHYME_AUDIT.csv` | 48,449 | `ed15caa051a0b35447458be748f92eb11f4cf7f2c73f17a35ed8ce43ee63c466` |
| `GUANGYUN_FANQIE_REPAIR.csv` | 937,787 | `70c66b11c893845005c9038ce5cd7e4c2768e1542a2f89a25dd67cd2a3e91794` |
| `GUANGYUN_FANQIE_REPAIR.md` | 2,245 | `db8a77413475eccb00a359feaf615f6237fabbacb388159f6d7d4dcc99c16390` |
| `GUANGYUN_INDEPENDENT_CHECK.md` | 1,344 | `4ae64a9bd84bf7194930e83cf117b0265fee494c4bd5a846459bce3082629af9` |
| `GUANGYUN_RHYME_ASSIGNMENT_REPAIR.csv` | 4,918 | `641298f5d79ae4a3dfc22fafbd0b34f5d8ca21eec75102580c9f457364c8ac83` |
| `HAN_YU_PAGE_INDEX_STANDARD.md` | 1,317 | `86c9436a76be71fa928b82ea4774e44033d37cc6ddf149fae2c1501951362f24` |
| `HISTORICAL_COUNTING_DICTIONARY.md` | 2,493 | `a77d34809cf94696a30779e54d6bddb652c5e1e04fcd9da9d551acc405c6e8ec` |
| `INDEPENDENT_REVIEW_120.csv` | 23,794 | `3e566026fafa686381370089f514a70992ae27a05b8b1f714dbcf1f7ecf78366` |
| `INDEPENDENT_REVIEW_R2_10.md` | 3,225 | `0a7c291c36d91598e5cb464dc9e88439e7421ef72ff40e6da8e0401dab955919` |
| `JIYUN_206_PAGE_PROVENANCE.csv` | 53,964 | `6d311303d741597acf9ee021602312656d10ce20204aa523019ae8c86fa61b79` |
| `JIYUN_4169_REVIEW.csv` | 774,385 | `f2316a6997c6200a3dfcb1fc7d49ef077797cd6c8e633bd846e03f5ef8177df5` |
| `JIYUN_CHARACTER_COUNT_RECONCILIATION.md` | 1,988 | `20b76415eaa88c1d0c85b5d6bc0a0b0e1ec839a6bcc736986c78c0952ff7b082` |
| `JIYUN_COUNT_RECONCILIATION.csv` | 2,121 | `42c8162206b32ada9510b29e7dca87b3f7e25d1e2aebc78733b966b7d2065a36` |
| `JIYUN_SAMPLE_IMAGE_AUDIT.csv` | 5,894 | `65ada21b7b8136e107cb6b41c37c82e8e2387ce20fc1a49ce63da61c06c512e6` |
| `JIYUN_SMALL_RHYME_AUDIT.md` | 1,818 | `1881dac42375ded8ca88d78477ce513050a0e4614fd4ee4689c01b9f83f55a5e` |
| `PHONETIC_DATA_SEMANTICS.md` | 2,678 | `4134b23a61e7d831067735dc33da993266c07456f873b9f3e10f86c841528916` |
| `PHONETIC_SCHEMA_R2_10.md` | 1,998 | `14f9c56858e4307e96d7966744ce14f80e8e531277ac62f75fb5278222e955c4` |
| `PINGSHUI_COUNT_AUDIT.md` | 1,085 | `2a1f8d2a95cf74abd6ab18537abb1aa91e737673303f565a31b874d8a3b11c7d` |
| `PLACEHOLDER_CHARACTER_AUDIT.csv` | 4,109 | `3aaf9c587372ba72f82d40fcd43820c61a83740166ad0cd5b8b5ea989fe4545e` |
| `POLYPHONE_200_FINAL_AUDIT.csv` | 69,301 | `19f874fa47ce7ffa4cd169fd5e0361bbbc53a72955c6ee92ae00c939a1150243` |
| `PREFLIGHT_DATABASE_STATE.md` | 2,171 | `df716553e2292e60691f69d763747edd8b1111252465ce95405b7dbec142dd13` |
| `PREFLIGHT_FILE_HASHES.csv` | 7,796 | `0ccc34400790c28d526fe30319a5c8ccde45a6c57fbfe3703ae3a6c9659633b3` |
| `PREFLIGHT_TABLE_SNAPSHOT.csv` | 8,369 | `1cb7faca6c3ce565a063d1d174f50a4f6b840d35d86802bf20bc967c6acd3342` |
| `READING_CLAIM_REWRITE.md` | 15,474 | `35ca0afc94004c94d0b1d3a79326f15459158b1c597514ce96ee42f98f635c3a` |
| `READING_NEW_60_SAMPLE_AUDIT.csv` | 18,178 | `2d723fc8d6833a204f2ab56724cb17bee19a4510dc966266e0bcb435cd0304a2` |
| `READING_PARTIAL_FAIL_CLOSURE.csv` | 39,891 | `ebe4160e6d75debd8376618ad1ed1b44c05d2e5d0007e278be3f9930a9cf8ccc` |
| `REGRESSION_COMPARISON.md` | 1,370 | `0c5e875648a179e5c6eff3494ed69f7b63edd0fdbc7bee096dca480f887aab67` |
| `REVIEW_SUMMARY.md` | 2,932 | `2c94503cd7db65027e9f792cfbf4e245d5cc3b330ccdeda3bde11cd68149b95e` |
| `RHYME_QUERY_30_EXECUTION.md` | 1,684 | `81eefac2050daf045b3053bd6f9d4257853184de84e9a5988b44a9847e90cd18` |
| `RHYME_QUERY_30_RESULTS.csv` | 8,979 | `36db189e2c3a2dfd01cfc455cf2ddbd4861c7f8fc373f6897905f60ebb9154b0` |
| `SCHWA_50_IMAGE_VERIFICATION.csv` | 221 | `1c1f0d05ed92689cee63cc9c22009ea77ca5e6a6ba6b41f031941e43750c382a` |
| `SCHWA_688_FINAL_AUDIT.csv` | 845 | `14f44b8301d3ef01f762ebf0328e2ff4e66e72ebcfb326b30be55be33f898e12` |
| `SHIJING_30_CASES_R2_10.csv` | 23,643 | `cab953f2d7dae0cb1c2e3c8450323c090b8e3993c61f0771ad28323784d4b44d` |
| `SIX_SYSTEM_SOURCE_COVERAGE.csv` | 743 | `ec496c78495a2079c25a123b57a719c5813e2f6cc73bab50af30af9700cb80bf` |
| `SIX_SYSTEM_SOURCE_COVERAGE.md` | 2,215 | `68d45b7679c383b260accd13f255f11ee7ebccd62d0b21c26e9d2552f8c52b6e` |
| `TEN_INDEPENDENT_TEXT_COLLATIONS.csv` | 13,563 | `900cadf72521ffed3d39ba2b1960f1badb0ff56964ff9cfd37b258b3d030c903` |
| `TEST_EXPECTATION_CHANGELOG.md` | 1,030 | `d641743be045c0dd88e289b50e716688a39a5f54dd065f4480a1560b0c2c78ee` |
| `TEST_RESULTS_R2_10.csv` | 5,215 | `9ed0395a35af2dffbfa1862cf5c0e2607945c9e2af8bfb633cc4b5e032943a15` |
| `TEST_RESULTS_R2_10.md` | 7,570 | `4d22d4b69cd56c865e255aeff496546c88bb0cd5500bd995aced0c9722e8dd99` |
| `THIRTY_CLOSE_READINGS.csv` | 105,261 | `b61880ad28a7b36b5c8a28f64e2ed7dbfcfc0bdae986294e38f8850c5e076eec` |
| `THIRTY_CLOSE_READINGS_REWRITTEN.md` | 23,298 | `8611564624930c0344683459c9e34d06ffccd629af5fbe56f1bc24fbdaced78a` |
| `UNMATCHED_22_CANDIDATES.csv` | 25,643 | `b31327f0de871183ac4b3bfa6ceaa6848e324a6a5be1d92b1fdf2f086c052422` |
| `ZHONGHUA_14_RULE_AUDIT.md` | 1,441 | `3e1827a5d6468c55fd1bb873348019156a7e34762f5ff58a15a724182229c1c5` |
| `ZHONGYUAN_5731_AUDIT.md` | 1,143 | `1649a464720b6060f100a4c3c70ff1a35f38d9b7254955d034168eb5a3935539` |

完整清單（含 COMPLETE_REPORT.md 自身）另見 `FILE_MANIFEST.md` 與 `COMPLETE_REPORT.sha256`。
