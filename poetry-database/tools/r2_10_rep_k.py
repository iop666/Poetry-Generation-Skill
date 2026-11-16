#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-10 K 段報告 + 完整報告 + 檔案清單。"""
import hashlib
import json
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REP = os.path.join(ROOT, "reports", "tasks", "2026-11-15", "R2-10")
F = json.load(open(os.path.join(ROOT, "raw", "r2_10", "facts.json"), encoding="utf-8"))
con = sqlite3.connect(os.path.join(ROOT, "database", "poetry.db"))
q = lambda s: con.execute(s).fetchone()[0]


def wr(name, text):
    with open(os.path.join(REP, name), "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


T = {}


def t(name, sql):
    T[name] = q(sql)


t("guangyun_fanqie_r2_10", "SELECT count(*) FROM guangyun_fanqie_r2_10")
t("guangyun_yunmu_repair_r2_10", "SELECT count(*) FROM guangyun_yunmu_repair_r2_10")
t("jiyun_page_provenance_r2_10", "SELECT count(*) FROM jiyun_page_provenance_r2_10")
t("jiyun_small_rhyme_audit_r2_10", "SELECT count(*) FROM jiyun_small_rhyme_audit_r2_10")
t("cipai_symbol_audit_r2_10", "SELECT count(*) FROM cipai_symbol_audit_r2_10")
t("v_ph_semantics_r2_10", "SELECT count(*) FROM v_ph_semantics_r2_10")
t("strict_head", "SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE head_kind='STRICT_HEAD'")
t("youyin", "SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE head_kind='YOUYIN_ENTRY'")
t("nofq", "SELECT count(*) FROM guangyun_fanqie_r2_10 WHERE head_kind='NO_FANQIE'")
t("db_bytes_now", "SELECT 0")
print(T)

# ---------------- K ----------------
wr("INDEPENDENT_REVIEW_R2_10.md", f"""# R2-10/K 獨立審查

## 1 設計（與前幾輪的差別）

前幾輪的問題是「主 Agent 處理 → 同一主 Agent 再檢查」。本輪改成：
- 抽樣由**獨立子 Agent**自行執行（固定種子 20261115），主 Agent 只提供母體與欄位說明；
- 子 Agent 必須回到原始檔案（`raw/books/guangyun/卷*.wikitext`、`raw/r2_08/jiyun_pages/*.json`、`works` 表）自行判斷；
- 結論不一致時**不得**默認採用主 Agent 的說法。

## 2 樣本與一致率

| 類 | 母體 | 樣本 | AGREE | DISAGREE | UNDECIDABLE | 一致率 |
|---|---|---:|---:|---:|---:|---:|
| 集韻小韻 | 4,169 | 25 | 0 | 25 | 0 | 0.0% |
| 廣韻反切 | 4,771 | 25 | 15 | 9 | 1 | 60.0% |
| 例詞關聯 | 310 | 20 | 17 | 3 | 0 | 85.0% |
| **合計** | — | **70** | **32** | **37** | **1** | **45.7%** |

另合併 65 條閱讀複核與 20 條詞譜符號複核，`INDEPENDENT_REVIEW_120.csv` 共 **140 行**（超過要求的 120）。

## 3 最重要的三條爭議

### 3.1 集韻 `fanqie_upper` 存整串（25/25 全錯）

獨立 Agent 直接讀 `tools/r2_09_jiyun_loader.py:77`，指出 `fanqie_upper` 取的是 `fq.group(1)`（兩字），
不是 `fq.group(1)[0]`。**主 Agent 在 R2-09 曾宣稱「集韻反切已按正確定義拆分」，此說法錯誤。**
本輪已建新表修正（`jiyun_small_rhyme_audit_r2_10`，{F['jy_upper_wrong']:,} 條受影響）。

這條爭議的價值在於：**它揭露了「自我檢查」的盲區**——主 Agent 寫的測試只檢查「欄位非空」，
沒有檢查「欄位定義是否正確」，所以 71 項測試全過卻仍有系統性錯誤。

### 3.2 廣韻「小韻首」把又音條目算進來（9/25）

抽樣中 7 條屬「又某某切」的又音條目，被舊判據當成小韻首。
本輪加 `head_kind`，嚴格判定 {T['strict_head']:,} 條，又音 {T['youyin']:,} 條，無反切 {T['nofq']:,} 條。
**「4,771 小韻」這個數字作廢。**

### 3.3 例詞關聯 3 條不一致

主要出現在 `POSSIBLE_MATCH`：主 Agent 按字串相似度判為可能匹配，獨立 Agent 對照後認為是
「同詞牌不同作品」，應降為 `TITLE_ONLY` 或 `NO_MATCH`。

## 4 獨立性聲明（必須如實）

- 集韻與廣韻的複核，獨立 Agent 與主 Agent **共用同一份轉錄文本**（維基文庫）。
  它驗證的是「主 Agent 對文本的處理是否正確」，**不能**發現「轉錄本身錯字」。
- 例詞複核用的是同一個 `works` 二手庫，因此也無法發現「庫本身錯字」。
- 唯一真正獨立的是詞譜符號核驗：主 Agent 用文字層、獨立 Agent 若用圖像，才算兩個來源。
  本輪該項因工具限制未做到圖像級。

## 5 對主 Agent 結論的處置

| 主 Agent 原結論 | 處置 |
|---|---|
| 集韻反切已正確拆分 | **撤回**，改為「R2-09 存整串，本輪修正」 |
| 廣韻 4,771 小韻 | **降級**為「4,771 條候選，其中嚴格 {T['strict_head']:,}」 |
| 16 個韻整段錯掛 | **降級**為「抽樣觀察，未系統證實」；本輪實測為 {F['gy_seg']} 段連續錯掛，≥5 條者 {F['gy_seg5']} 段 |
| 60/60 符號核驗 | **改正**為「49 條逐符號一致，11 條文字層殘缺未決」 |
| 196 條可信例詞關聯 | **改正**為「166 條 VERIFIED，另 30 條僅為候選」 |
""")

wr("REGRESSION_COMPARISON.md", f"""# R2-10/K 回歸對照（舊 71 項 vs 新 82 項）

## 1 舊測試（R2-09 的 71 項）

原樣保留 `tools/r2_09_tests.py`，**未改動任何期望值**，本輪重跑：

```
tests 71 PASS 71 FAIL 0
```

結論：R2-10 的新增表與修正**沒有破壞 R2-09 的既有斷言**。

## 2 新測試（R2-10 的 82 項）

`tools/r2_10_tests.py`，結果 `TEST_RESULTS_R2_10.csv`：

| 項 | 值 |
|---|---:|
| 總數 | {F['test_n']} |
| 通過 | {F['test_pass']} |
| 失敗 | {F['test_n'] - F['test_pass']} |

## 3 兩個失敗是「真實缺陷」，不是腳本錯誤

| 代號 | 描述 | 期望 | 實測 | 說明 |
|---|---|---|---|---|
| T12 | 每個已錨定韻都應有小韻 | 0 個空韻 | 4 個空韻 | 有 4 個韻的韻目已錨定，但其下小韻因字頭定位失敗全部落空。這是真問題，保留 FAIL |
| T60 | 六套體系未被合併成單一字典 | 6 | 4 | `ph_readings_r2_08` 只有 4 個 `system` 值（廣韻集韻共用 `middle_chinese`，中原音韻不在本表）。「六套分立」之說不成立 |

**沒有為了讓 82/82 通過而修改期望值。** 這兩個 FAIL 寫進報告，供審核方判斷。

## 4 與 R2-09 的期望值變動對照

R2-09 曾兩次「隨實測調整期望值」（T-51/52/54），本輪**未重複該做法**。
若某項新測試的期望值與實測不符，一律保留 FAIL 並在報告中說明原因，見 `TEST_EXPECTATION_CHANGELOG.md`。
""")

wr("TEST_EXPECTATION_CHANGELOG.md", f"""# R2-10 測試期望值變更記錄

本輪共 82 項新測試，**期望值一經寫定即未修改**。以下是唯一需要說明的兩處。

| 代號 | 期望值來源 | 是否調整 | 說明 |
|---|---|---|---|
| T12 | 「錨定的韻應有小韻」——由 R2-09 的 `n_xiaoyun=0` 審計推出 | 否 | 實測 4 個空韻，判 FAIL，如實保留 |
| T60 | 「六套體系分立」——由 R2-08／R2-09 報告的措辭推出 | 否 | 實測 4 個 system 值，判 FAIL，如實保留 |

其餘 80 項的期望值來自：
- 資料庫實測（如 206、4,169、20,530）——這類是「口徑斷言」，通過只表示資料自洽；
- 檔案存在性（如 `PLACEHOLDER_CHARACTER_AUDIT.csv`）；
- 缺陷可重現性（如 T03「舊 upper 確為下字 ≥4,500」，通過表示缺陷仍可被證明，不是「修好了」）。

**須聲明**：82 項測試中，約 30 項屬於「用自己的口徑量自己的資料」，
其通過不構成獨立驗證。真正的獨立驗證只有 K1 的 70 條交叉複核。
""")

wr("REVIEW_SUMMARY.md", f"""# R2-10 審閱摘要（供外部審核用）

## 一 本輪做了什麼

| 包 | 內容 | 結果 |
|---|---|---|
| 0 | 資料庫凍結與狀態固定 | 位元組 {F['db_bytes']:,}、SHA-256 `{F['db_sha256'][:16]}…`、integrity ok、無 WAL |
| A | R2-07～R2-09 歷史數字對帳 | 12 組數字逐一分類；《集韻》三個小韻數與六個字數全部可解釋 |
| B | 音韻資料語義重建 | 證實 80,652 條**無任何音值**；建語義視圖；發現廣韻集韻共用 system |
| C | 廣韻反切與韻目修復 | 4,658 條上下字顛倒已修；202/206 韻位置直證；「4,771 小韻」降級為 2,907 嚴格小韻首 |
| D | 集韻來源與字數 | 206/206 取得 revid 與四庫 djvu 葉碼；4,442 ○ → 4,432 → 4,169 完全對帳 |
| E | 六套韻書覆蓋 | 逐套給出來源、字數、缺口；中華新韻「十四韻」實為 13 |
| F | 60 條詞譜符號核驗 | 49 條逐符號一致，11 條文字層殘缺 |
| G | 閱讀複核 | 39 條 PARTIAL/FAIL 全部處理（37 改寫、2 未決）；新抽 65 條（57 PASS／8 PARTIAL） |
| H | 例詞與精讀 | 310 條重判；30 首精讀重寫；10 首找到獨立版本對勘 |
| I | 上古音 | 40 例重新分類（22 例有學術依據）；書目 36 條 |
| J | 查詢驗證 | 30/30 有結果；5 個錯誤前提測試 |
| K | 獨立審查與測試 | 70 條交叉複核（一致率 45.7%）；82 項新測試（80 通過）；舊 71 項全通過 |

## 二 三件最重要的事

1. **《廣韻》反切上下字確實全反**（4,658/4,771），且「4,771 小韻」的基數本身錯誤（含 1,416 又音條目）。
   凡是拿舊 `fanqie_upper` 推過聲母的分析，結論一律作廢。
2. **集韻反切在 R2-09 也被寫錯**（上字存整串），這是「自我檢查」沒抓到的系統性錯誤，
   由獨立複核發現。已建新表修正。
3. **「80,652 條讀音」必須改稱「韻部歸屬」**。本庫沒有任何音值，這是能力邊界，不是缺陷。

## 三 仍然沒做到的

| 項 | 狀態 | 原因 |
|---|---|---|
| 11 條詞譜符號核驗 | 未決 | PDF 文字層缺符號；目視轉寫在本環境不可靠（＋易被拆成｜－） |
| 集韻 4,169 條全部人工複核 | 僅 111 條 | 時間 |
| 詞林正韻補足 3,650 字 | 未做 | 兩體系收字範圍不同，不以平水韻反推 |
| 中原音韻 150 字抽檢 | 未做 | 時間 |
| 中華新韻 200 字抽檢 | 未做 | 時間 |
| 音標 50 組回圖 | 未做 | 時間與工具 |
| 30 首精讀中 10 首版本對照 | 完成 | 但另 20 首未對照 |
| 上古音歸部 | 22/40 有依據 | 其餘 `UNATTRIBUTED` |

## 四 結論

**SELF_STATUS：PARTIAL。**

理由：核心缺陷（廣韻反切、集韻字數、詞譜符號層級、音韻語義）已查清並修復到可查證的程度；
但「逐條人工核驗」與「獨立版本對勘」的覆蓋率仍低，且 2 項測試如實失敗。
不以降低證據標準換取 PASS。
""")

print("K 段完成")
con.close()
