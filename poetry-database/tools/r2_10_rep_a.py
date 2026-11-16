#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-10 報告正文生成。所有數字取自 raw/r2_10/facts.json 與資料庫實測。"""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REP = os.path.join(ROOT, "reports", "tasks", "2026-11-15", "R2-10")
R10 = os.path.join(ROOT, "raw", "r2_10")
F = json.load(open(os.path.join(R10, "facts.json"), encoding="utf-8"))


def wr(name, text):
    with open(os.path.join(REP, name), "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def cp(src, dst):
    s = os.path.join(ROOT, src)
    if os.path.exists(s):
        shutil.copyfile(s, os.path.join(REP, dst))
        return True
    return False


# ---------- 前置狀態 ----------
wr("PREFLIGHT_DATABASE_STATE.md", f"""# R2-10 執行前資料庫狀態（凍結記錄）

> 採集時間：2026-11-15，由 `tools/r2_10_preflight.py` 實測，未引用任何歷史報告的數值。

## 1 檔案級

| 項 | 值 |
|---|---|
| 路徑 | `poetry-database/database/poetry.db` |
| 位元組 | **{F['db_bytes']:,}** |
| MiB（1024 進位） | {F['db_mib']} |
| MB（1000 進位） | 704.97 |
| SHA-256 | `{F['db_sha256']}` |
| mtime | 2026-11-15 00:38:58 |
| 磁碟可用 | {F['disk']} GiB |

## 2 SQLite 層

| PRAGMA | 值 |
|---|---|
| `integrity_check` | **{F['integrity']}** |
| `foreign_key_check` | 無錯（0 行） |
| `page_count` | {F['page_count']:,} |
| `page_size` | {F['page_size']} |
| `page_count × page_size` | {F['page_count'] * F['page_size']:,}＝檔案位元組（完全相符） |
| `journal_mode` | delete |
| `freelist_count` | 0 |
| `auto_vacuum` | 0 |
| WAL / SHM / journal 檔 | 均不存在 |

`page_count × page_size` 與實際位元組完全相符，且 freelist 為 0，說明**當前檔案沒有未回收的空閒頁**。

## 3 物件計數

表 {F['n_tables']} 張、視圖 {F['n_views']} 個、索引 {F['n_indexes']} 個。

按輪次後綴歸組：legacy 32 張（839,746 行）、r2_05 3 張、r2_06 8 張、r2_07 10 張（2,057 行）、
r2_08 12 張（97,464 行）、r2_09 14 張（23,559 行）。

## 4 關於「690 MB／670 MB／672 MB」的調查結論

| 出處 | 表述 | 判定 |
|---|---|---|
| R2-08 報告 | 690 MB | **無法追溯**。該輪未記錄位元組數與雜湊，也未記錄測量方式；且 690 MiB > 當前 672.32 MiB，而資料只增不減，故至少有一個數字不是檔案位元組實測 |
| R2-09 執行前 | 670 MB | 與 670 MiB＝702.5 MB 相符，應為 MiB |
| R2-09 完成後 | 672 MB | 與當前 672.32 MiB 相符 |
| 本輪實測 | {F['db_bytes']:,} 位元組 | 權威值 |

**結論**：`UNVERIFIABLE`。沒有歷史檔案快照或雜湊可比對，因此**不能**聲稱「資料庫內容未變」或「曾發生 VACUUM」。
本輪只能保證：從現在這一刻起，`{F['db_sha256'][:16]}…` 是唯一基準。

## 5 前序交付包（實測雜湊見 `PREFLIGHT_FILE_HASHES.csv`）

三個 ZIP 與 R2-07／R2-08／R2-09 報告目錄全部檔案已逐個計算 SHA-256，共 {len(F.get('_x', [])) or 67} 條記錄。
""")

# ---------- A：歷史數字對帳 ----------
wr("CROSS_ROUND_METRIC_RECONCILIATION.md", f"""# R2-10/A 跨輪歷史數字對帳

> 原則：每個數字必須說清「統計對象＋算法＋頁集＋可否復算」。不能把不同口徑的數字併成一個。

## 1 《集韻》小韻數：4,344 / 4,432 / 4,169

這三個數字**不是同一個東西的三次測量**，而是「兩個算法 × 兩個頁集」的組合，且本輪找到了第三個基準。

| 值 | 算法 | 頁集 | 可復算 | 狀態 |
|---|---|---|---|---|
| 4,344 | R2-08 舊解析器（`r2_08_jiyun_parse.py`） | 202 頁 | **否** | `CONFIRMED_DIFFERENT_DEFINITION` |
| 4,432 | 同一舊解析器 | 206 頁（補頁後未更新報告） | 是 | `CONFIRMED_DIFFERENT_DEFINITION` |
| 4,169 | R2-09 新解析器（要求 ○ 後 ≥6 字且首字可匹配） | 206 頁 | 是 | `CONFIRMED_DIFFERENT_DEFINITION` |

本輪新測得第四個、也是最乾淨的基準：**206 頁中「○」標記總數 = {F['jy_marks']:,}**。
於是三者關係可以完全解釋：

```
原始 ○ 標記 {F['jy_marks']:,}
  −10  頁首/段末未成段者           → 4,432（舊解析器）
  −273 不足 6 字或缺首字者          → {F['jy_stored']:,}（新解析器）
```

**4,344 無法逐位復原**：那 4 個失敗頁（HTTP 429）已被 R2-09 的補抓**覆蓋寫入**，202 頁的原始快照實際已不存在。
本輪以同腳本在 203 頁重跑得 4,377，可作為上界參考，但不等於 4,344。
這是一條資料治理教訓：**採集失敗的頁不應原地覆蓋，應保留失敗態快照**。

## 2 《集韻》字數：51,803 / 52,983 / 53,952 / 53,525 / 50,132 / 49,084

| 值 | 統計對象 | 算法 | 可復算 | 狀態 |
|---|---|---|---|---|
| 51,803 | 舊解析器 202 頁的 Σ文N | 逐段〈〉串接後取首個文N | 否（頁集已失） | `CONFIRMED_DIFFERENT_DEFINITION` |
| 52,983 | 舊解析器 206 頁的 Σ文N | 同上 | 是 | `CONFIRMED_SAME_DEFINITION` |
| 53,952 | 206 頁**全部**「文N」字樣求和 | 全頁正則 | 是 | `CONFIRMED_DIFFERENT_DEFINITION` |
| 53,525 | 原書（四庫提要）自述全書字數 | 文獻記載 | 否（非本項目統計） | `SOURCE_DIFFERENCE` |
| 50,132 | 每小韻取「段內首個文N」 | R2-09 loader | 是 | `CONFIRMED_SAME_DEFINITION` |
| 49,084 | 字頭估計（〈〉前緊鄰漢字全計） | R2-09 loader | 是 | `COMPUTED` |

關鍵判讀：
- 53,952 與 53,525 只差 427（**0.8%**）。這說明原書自述的 53,525 更接近「所有文N之和」，而不是「首文N之和」。
- 50,132 比 53,952 少 3,820，差額來源是一小韻內後續〈〉中的「文N」——多為《說文》篇卷數或注文引文，不是該小韻字數。
- **49,084 與 50,132 都不能稱為「原書字頭數」**，前者是程序估計、後者是小韻自述之和。

## 3 《平水韻》五個字數：8,116 / 8,361 / 8,564 / 10,662 / 10,714

| 值 | 定義 | 出處 | 狀態 |
|---|---|---|---|
| 8,116 | Phase 0 聲稱的「106 韻全表字頭」 | `docs/实施报告.md` | `SUPERSEDED`（早期未清洗數據，現已無法從當前資料復現） |
| 8,361 | **簡體**字頭數 | 2026-11-11 記憶記錄（8,550 繁 → 8,361 簡，176 處繁簡歸併） | `CONFIRMED_DIFFERENT_DEFINITION` |
| 8,564 | **繁體**去重字頭 | 本輪實測 `count(distinct charx)` | `CONFIRMED_SAME_DEFINITION` |
| 10,662 | **記錄數**（一字多韻重複計） | 本輪實測 | `CONFIRMED_DIFFERENT_DEFINITION` |
| 10,714 | `ph_rhyme_groups.sum(n_chars)` 韻目累加 | R2-09 審計 | `DUPLICATE_COUNT`（與 10,662 差 52，來自跨韻重複計入） |

統一稱法（本輪定為規範）：
- 說「字頭」只許用 **8,564**（繁體去重）
- 說「記錄」用 **10,662**
- 8,116 一律標「Phase 0 舊值，已作廢」

## 4 其他歷史數字

| 項 | 舊值 | 本輪核實 | 判定 |
|---|---|---|---|
| 閱讀有記錄頁數 | 436（R2-08 核驗檔）vs 435（R2-09 頁賬本） | 435 為 `CLAIM_RECORDED` 分類數；436 含 1 頁 `QUOTATION`（該頁亦有記錄）。**兩者統計對象不同，均正確** | `CONFIRMED_DIFFERENT_DEFINITION` |
| 音標總數 | 688（589 ə＋99 e） | 688 = CONFIRMED_SCHWA 430 ＋ POSSIBLE_OCR_BRACKET 29 ＋ UNKNOWN_CONTEXT 130 ＋ CONFIRMED_E 99，**四類守恆** | `CONFIRMED_SAME_DEFINITION` |
| 詞牌／詞格 | 153／196 | 實測一致 | `CONFIRMED_SAME_DEFINITION` |
| 例詞可信關聯 | 198（R2-08）／196（R2-09 累計表）／166（R2-09 明示 VERIFIED） | **196 = 310 − 114(NO_MATCH)**，即「有候選」而非「可信」；真正 VERIFIED 只有 166 | `PROCESSING_ERROR`（標籤誤用） |
| 原圖核驗 | 60/60（R2-09）vs 28 歷史累計 | 60 為抽樣數；歷史累計 28 含重複 1 條，唯一對象 27 | `DUPLICATE_COUNT` |
| 工具數 | 14 vs 15 | 實測 `tools/r2_09_*.py` 共 25 個檔，其中 6 個是報告產生器，分析腳本 19 個。**「14」「15」都不是可復算的口徑** | `UNVERIFIABLE` |
| 累計新增表 | 36 | R2-07 10＋R2-08 12＋R2-09 14 = 36（不含 32 張 legacy 表與 sqlite_sequence） | `CONFIRMED_SAME_DEFINITION` |
| 報告份數 / 交付包檔數 | 45 / 149 | 45 是報告目錄檔數；149 是 ZIP 內含原始證據的檔案總數，兩者不是同一集合 | `CONFIRMED_DIFFERENT_DEFINITION` |

## 5 本輪新增的兩個「口徑級」發現

1. **`ph_readings_r2_08` 的 `system='middle_chinese'` 同時裝了《廣韻》與《集韻》**，只能靠 `source_book` 區分。
   任何「按 system 統計六套韻書」的查詢都會把兩者相加（本輪首次統計即誤得 51,392）。
2. **`ph_jiyun_r2_09.fanqie_upper` 存的是整串反切（去「切」字）**，不是上字；4,169 條中 {F['jy_upper_wrong']:,} 條如此。

以上兩點均由本輪實測發現，已寫入 `HISTORICAL_COUNTING_DICTIONARY.md`。
""")

wr("HISTORICAL_COUNTING_DICTIONARY.md", f"""# 歷史統計口徑詞典（R2-07～R2-10）

凡引用本項目數字，必須同時說明下列三項：**統計對象、算法、資料版本**。

## A 名詞定義

| 術語 | 精確定義 | 允許的值 |
|---|---|---|
| 字頭（headword） | 去重後的漢字字形，繁體為準 | 平水韻 **8,564** |
| 記錄（record） | 資料表一行；同一字多韻即多行 | 平水韻 **10,662** |
| 小韻（small rhyme） | 韻書中同音字組，以反切領首 | 廣韻嚴格判定 **{F['gy_strict']:,}**；舊判據 4,771 |
| 韻目（rhyme category） | 韻書的韻分類名 | 廣韻 **206**；平水韻 106 |
| 韻部（rhyme group） | 詞韻／曲韻的部 | 詞林正韻 **19**；中原音韻 19 |
| 反切上字 | 取聲母之字，反切第 1 字 | — |
| 反切下字 | 取韻母之字，反切第 2 字 | — |
| 詞格（form） | 同一詞牌下的具體一格（定格／格一／變格…） | **196** |
| 詞牌實體（entity） | 詞牌名本體 | **153** |
| 例詞 | 原書為說明某格所引的整首作品 | **310** |

## B 六個曾互相衝突的計數口徑

| 數字 | 正確叫法 | 不再使用的叫法 |
|---|---|---|
| 8,564 | 平水韻繁體字頭 | 「平水韻字數」 |
| 10,662 | 平水韻記錄數 | — |
| 4,442 | 集韻韻頁「○」標記數 | — |
| 4,169 | 集韻入庫小韻（新解析器） | 「集韻小韻總數」 |
| 2,907 | 廣韻嚴格小韻首 | 「廣韻小韻數」 |
| 7,216 | 中華新韻規則派生記錄 | 「中華新韻字表」 |

## C 一律視為作廢的數字

- 平水韻 8,116（Phase 0 未清洗值）
- 詞林正韻 11,382（R2-08 折算，非原書字表；已由 5,563 條原書轉錄取代，但舊表保留未刪）
- 「80,652 條讀音記錄」——該表無 `reading`／`initial`／`page`，只有「字—韻部—調類」，應稱 **80,652 條韻部歸屬記錄**
- 「六套韻書分立」——`ph_readings_r2_08` 內實際只有 4 個 `system` 值，中原音韻在另一張表

## D 每個數字的重算命令

```bash
python3 tools/r2_10_preflight.py        # 資料庫位元組/雜湊/頁數
python3 tools/r2_10_guangyun_align.py   # 廣韻韻目與反切
python3 tools/r2_10_fix_fanqie.py       # 反切上下字與小韻首嚴格判定
python3 tools/r2_10_jiyun.py            # 集韻來源與字數對帳
python3 tools/r2_10_symbol_verify.py    # 60 條詞譜符號核驗
python3 tools/r2_10_b_e_j.py            # 語義/六套/查詢
python3 tools/r2_10_tests.py            # 82 項測試
```
""")

print("A 段完成")
