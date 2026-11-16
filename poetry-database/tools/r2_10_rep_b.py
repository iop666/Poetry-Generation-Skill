#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-10 報告正文生成（B/C/D/E/F/G/H/I/J/K 段）。"""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REP = os.path.join(ROOT, "reports", "tasks", "2026-11-15", "R2-10")
F = json.load(open(os.path.join(ROOT, "raw", "r2_10", "facts.json"), encoding="utf-8"))


def wr(name, text):
    with open(os.path.join(REP, name), "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def cp(src, dst):
    s = os.path.join(ROOT, src)
    if os.path.exists(s):
        shutil.copyfile(s, os.path.join(REP, dst))
        return True
    print("MISSING", src)
    return False


# ---------------- B ----------------
wr("PHONETIC_DATA_SEMANTICS.md", f"""# R2-10/B 歷史音韻資料的語義重建

## 1 問題：名字叫「讀音」，內容不是讀音

`ph_readings_r2_08` 共 **{F['sem_total']:,}** 行。逐欄填充率實測：

| 欄位 | 空值行數 | 填充率 |
|---|---:|---:|
| `charx`（字） | {F['sem_fill']['charx']['empty']:,} | 100% |
| `reading`（實際讀音） | **{F['sem_fill']['reading']['empty']:,}** | **0%** |
| `initial`（聲母） | **{F['sem_fill']['initial']['empty']:,}** | **0%** |
| `final`（韻母） | {F['sem_fill']['final']['empty']:,} | {'0%' if F['sem_fill']['final']['empty'] == F['sem_total'] else '部分'} |
| `tone`（調類） | {F['sem_fill']['tone']['empty']:,} | {'0%' if F['sem_fill']['tone']['empty'] == F['sem_total'] else '部分'} |
| `rhyme_group`（韻目/部） | {F['sem_fill']['rhyme_group']['empty']:,} | {'0%' if F['sem_fill']['rhyme_group']['empty'] == F['sem_total'] else '部分'} |
| `fanqie`（反切） | {F['sem_fill']['fanqie']['empty']:,} | 部分 |
| `page`（紙本頁碼） | **{F['sem_fill']['page']['empty']:,}** | **0%** |

**結論**：該表沒有一條記錄含實際音值。它記錄的是「某字在某韻書中屬於哪個韻目／哪個調類」。
因此 R2-08 報告所稱「80,652 條讀音記錄」是**命名誇大**，正確稱法是
**80,652 條韻部歸屬記錄**（其中 35,189 條另帶反切，但反切未拆為上下字時也不等於可用的聲韻母）。

## 2 四類資料必須分開

| 類型 | 本項目對應 | 行數 |
|---|---|---:|
| `RHYME_MEMBERSHIP` 韻部歸屬 | 平水／詞林／中原／廣韻集韻的部分記錄 | {F['sem_types']['RHYME_MEMBERSHIP']['n']:,} |
| `PHONETIC_READING` 帶反切的記錄 | 廣韻＋集韻（反切可拆上下字） | {F['sem_types']['PHONETIC_READING']['n']:,} |
| `TONE_CLASSIFICATION` 調類 | 與上兩類重疊，不獨立計數 | — |
| `MODERN_PRONUNCIATION` 現代音 | 中華新韻（拼音規則派生） | {F['sem_types']['MODERN_PRONUNCIATION']['n']:,} |

「某字屬上平聲東韻」**不等於**「知道它在《廣韻》裡怎麼讀」。
本項目**沒有任何一條記錄含國際音標音值**，視圖中 `has_phonetic_value` 全為 0（測試 T44 守住）。

## 3 語義視圖

`v_ph_semantics_r2_10`（80,652 行）為每行標註：`data_type`、`has_tone_class`、`has_fanqie`、
`has_rhyme_group`、`has_phonetic_value`（恆 0）、`semantic_evidence`（`SOURCE_TRANSCRIPTION`
或 `COMPUTED_FROM_PINYIN`）。舊表未改動。

## 4 兩個結構缺陷（本輪新發現）

1. **《廣韻》與《集韻》共用 `system='middle_chinese'`**。按 `system` 統計會把兩者相加
   （誤得 51,392）。只能用 `source_book` 區分。
2. **`system` 只有 4 個值**（middle_chinese／regulated_verse／ci_rhyme／modern_rhyme），
   中原音韻在此表中為 0 行（另存 `ph_zhongyuan_r2_09` 5,731 行）。
   所謂「六套體系分立」在這一張表上**並不成立**，測試 T60 因此判 FAIL。

## 5 佔位符

《廣韻》20,530 條中有 **3,660** 條字頭為 `□`／`�`（17.8%），來自維基文庫轉錄缺字。
本輪只做統計與隔離（`PLACEHOLDER_CHARACTER_AUDIT.csv`），**沒有**由反切反推字形。
理由：反切只能推出音類，推不出字形；強推等於偽造。
""")

wr("PHONETIC_SCHEMA_R2_10.md", f"""# R2-10/B 音韻資料欄位規範（建議）

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
- 廣韻：`GY_V{{卷}}_{{韻序}}`，如 `GY_V1_01`
- 集韻：`JY_V{{卷}}_{{韻序}}`

舊資料不改，新表用新 ID，另建映射表。
""")

# ---------------- C ----------------
wr("GUANGYUN_FANQIE_REPAIR.md", f"""# R2-10/C 《廣韻》反切上下字修復

## 1 缺陷確認

R2-08 的 `fanqie_upper` 在 4,771 條「小韻首」中，**4,658 條存的是反切下字**。
本輪逐條複算（`tools/r2_10_guangyun_align.py`）：

| 情形 | 條數 |
|---|---:|
| 舊值＝反切第 2 字（下字） | **{F['gy_fq'].get('OLD_STORED_LOWER', 0):,}** |
| 舊值＝反切第 1 字（上字） | {F['gy_fq'].get('OLD_STORED_UPPER', 0):,} |
| 舊值為 1 字殘缺反切（`X切`，只有一字） | 113 |

那個「113 條上字」是誤讀：它們的反切本身只有 2 字（`偽切`），無法分上下，不是「正確保存了上字」。

## 2 修復方法（不是簡單對調）

1. 由既有 `fanqie` 字串重拆：上字＝第 1 字、下字＝第 2 字；只有 1 字者標
   `INCOMPLETE_ONE_CHAR`，`upper`/`lower` 留空。
2. 逐條保留 `evidence`（原文字頭前後 36 字）與 `char_offset`（在該卷 wikitext 中的字符位置），可回溯。
3. 舊值不刪，存 `old_fanqie_upper`，並用 `comparison` 標明差異類型。

## 3 結果

| 項 | 條數 |
|---|---:|
| 條目總數 | 20,530 |
| 標為 `is_xiaoyun_head=1`（舊判據） | 4,771 |
| 反切類型 `TWO_CHAR` | 4,658 |
| 反切類型 `INCOMPLETE_ONE_CHAR` | 113 |
| 上字＝第 1 字且下字＝第 2 字（新表） | 4,658（T01/T02 測試守住） |

## 4 另一個更嚴重的問題：4,771 這個數本身不可靠

獨立複核抽 25 條後指出：舊判據「注文含『切』即小韻首」把**又音條目**也算進來了。
本輪加做嚴格判定（反切須出現在注文最前端，且不以「又」起頭）：

| `head_kind` | 條數 |
|---|---:|
| `STRICT_HEAD`（真小韻首） | **{F['gy_strict']:,}** |
| `YOUYIN_ENTRY`（又音條目，非小韻首） | {F['gy_youyin']:,} |
| `NO_FANQIE` | {F['gy_nofq']:,} |

**因此「《廣韻》4,771 小韻」這個數字不能再引用。**
可引用的是：嚴格判定 {F['gy_strict']:,} 條，覆蓋 196 個已錨定韻中的 190 個。
嚴格判定本身仍有誤差（例如注文被截斷時會誤判），所以還不能等同於原書小韻數。

## 5 對下游的影響

凡是用舊 `fanqie_upper` 推過中古聲母的分析，**結論全部作廢**，必須用新表重做。
本項目尚未做過這類聲母分析，故無需回滾具體結論，但需在文件層面標記該欄位為 QUARANTINED。
""")

wr("GUANGYUN_INDEPENDENT_CHECK.md", f"""# R2-10/C 《廣韻》獨立複核

## 1 複核方式

由獨立子 Agent 抽 25 條，**自行**打開 `raw/books/guangyun/卷*.wikitext` 與新舊兩表對照，
不採用主 Agent 的判斷。明細見 `raw/r2_10/independent/INDEPENDENT_REVIEW_R2_10_part.csv`（category=`GUANGYUN_FANQIE`）。

## 2 結果

| 項 | 結果 |
|---|---|
| 抽樣 | 25 條 |
| 一致 | 15 條（60%） |
| 不一致 | 9 條（36%） |
| 無法判斷 | 1 條 |

## 3 不一致的主要類型

1. **「小韻首」誤判（9 條中 7 條）**：被抽到的條目其實是「又某某切」的又音條目，
   舊表卻標為小韻首。這是本輪新增 `head_kind` 欄位的直接原因。
2. **`char_offset` 回溯失敗（2 條）**：因字頭為 `□` 佔位符，`字頭〈反切` 的定位字串在原文中不唯一。

## 4 對主 Agent 結論的影響

- 「4,771 條全部重審」這句話**成立但需限定**：4,771 條確實逐條重算了反切與韻目，
  但其中 1,416 條經嚴格判定並非小韻首，所以「4,771 個小韻」不成立。
- 「16 個韻整段錯掛」這句話**未獲證實**：本輪以位置直證重判後，錯掛以「連續段」形式出現
  （{F['gy_seg']} 段，其中 ≥5 條者僅 {F['gy_seg5']} 段），沒有找到「16 個整韻」的證據。
  R2-09 的「16」應降級為「抽樣觀察，未系統證實」。
""")

# ---------------- D ----------------
wr("JIYUN_SMALL_RHYME_AUDIT.md", f"""# R2-10/D 《集韻》小韻審計

## 1 來源追溯（本輪主要進展）

206 個韻頁**全部**取得：
- MediaWiki `revid`：**{F['jy_revid']}/206**（R2-09 為 0/206，本輪以 API 補齊）
- 四庫全書 djvu 定位：**{F['jy_djvu']}/206**（如「文淵閣四庫全書_0236冊.djvu，葉1825a續–1837b」）
- HTML SHA-256：206/206

這意味著每一頁都能指到「哪一冊、哪一葉」，比「維基文庫某頁」精確得多。

## 2 小韻結構

| 項 | 值 |
|---|---:|
| 頁面「○」標記總數 | {F['jy_marks']:,} |
| 入庫小韻（新解析器） | {F['jy_stored']:,} |
| 有反切 | {F['jy_fq'].get('TWO_CHAR', 0) + F['jy_fq'].get('LONGER', 0):,} |
| 無反切 | {F['jy_fq'].get('NO_FANQIE', 0):,} |
| 反切僅 1 字（殘缺） | {F['jy_fq'].get('INCOMPLETE_ONE_CHAR', 0):,} |

## 3 反切上下字：R2-09 的同一類缺陷

`ph_jiyun_r2_09.fanqie_upper` 存的不是上字，而是**整串反切（去「切」字）**，
例如「徳紅切」存成 `徳紅`；`fanqie_lower` 存 `紅`。
4,169 條中 **{F['jy_upper_wrong']:,} 條**如此。

本輪不改舊表，另建 `jiyun_small_rhyme_audit_r2_10`，按正確定義重拆：
上字＝第 1 字、下字＝第 2 字。測試 T05/T07 守住新表。

## 4 120 條人工複核（沿用 R2-09）

| 判定 | 條數 |
|---|---:|
| OK | {F['jy_review120'].get('OK', 0)} |
| PARTIAL | {F['jy_review120'].get('PARTIAL', 0)} |
| FAIL | {F['jy_review120'].get('FAIL', 0)} |

FAIL 的主要成因（R2-09 已定性，本輪逐條比對後確認）：
1. 《說文》「十升也」被讀成「文十」→ 字數記錯；
2. 缺 `○` 導致相鄰兩小韻被合併；
3. 字頭為異體罕字時首字定位偏移。

本輪把 120 條結論按 `yun + seq` 回填到 4,169 條表（`JIYUN_4169_REVIEW.csv`），
可對上者 **{F.get('jy_manual_reviewed', 0)}** 條；其餘 4,058 條仍為 `NOT_REVIEWED`。

## 5 未完成

- 未做影印本圖像逐字核對（`JIYUN_SAMPLE_IMAGE_AUDIT.csv` 只記「文本結構已核」，不冒充圖像核驗）。
- 4 個韻（添／㫖／狠／𠋫）在《廣韻》側未錨定，集韻側不受影響。
""")

wr("JIYUN_CHARACTER_COUNT_RECONCILIATION.md", f"""# R2-10/D 《集韻》字數對帳（31,043 → 49,084 這條線的完整交代）

## 1 六個數字的關係

```
原書自述全書字數              53,525   （四庫提要，文獻記載）
206 頁全部「文N」求和          53,952   （本輪實測，差 +0.8%）
舊解析器 206 頁 Σ文N           52,983   （可復算）
舊解析器 202 頁 Σ文N           51,803   （頁集已失，不可復算）
每小韻首個文N 求和             50,132   （R2-09 口徑，可復算）
〈〉前緊鄰漢字估計字頭          49,084   （程序估計，非原書數）
────────────────────────────────────────
R2-08 最初報告的抽取字數        31,043   （算法缺陷：只取每個〈〉前最後 1–3 字）
```

## 2 31,043 為什麼是錯的

R2-08 的抽字規則只看「〈〉前最後 1–3 個漢字」，而四庫本《集韻》一個小韻下常列
2–4 個異體字共用一條注（`字字字〈注〉`）。只取最後 1–3 字會漏掉前面共用的字頭，
於是每個小韻平均少算約 40%。

R2-09 改為「〈〉前緊鄰的連續漢字全計」，得到 49,084。**這是修正，不是新資料。**

## 3 49,084 仍然只是估計

它假設「〈〉前連續漢字即字頭」。兩種情況會失真：
- OCR 丟掉 `〉` 時，前一條注文的末字會被當成字頭（多算）；
- 字頭被吞進注文時（少算）。

所以它與 50,132 的差 1,048 不能解釋為「原書少字」，只能說「兩種算法差 2.1%」。

## 4 可以下的結論與不能下的結論

可以下：
- 原書自述 53,525，與「全部文N求和」53,952 相差 0.8%，**同一量級，可互相印證**。
- R2-08 的 31,043 是算法缺陷，**不是原書缺字**。

不能下：
- 「《集韻》字頭數是 49,084」——這是估計值。
- 「51,803 與 50,132 差 1,671 是轉錄缺失」——兩者是不同算法，差額不可歸因。
""")

print("B/C/D 完成")
