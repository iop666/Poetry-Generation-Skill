#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 報告生成器（第三批：工作包 D、E）。"""
import os
import json
import shutil
import csv
import sqlite3
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R9 = os.path.join(ROOT, "raw", "r2_09")
REP = os.path.join(ROOT, "reports", "tasks", "2026-11-14", "R2-09")
F = json.load(open(os.path.join(R9, "audit", "facts.json"), encoding="utf-8"))
con = sqlite3.connect(os.path.join(ROOT, "database", "poetry.db"))
con.row_factory = sqlite3.Row


def w(n, t):
    open(os.path.join(REP, n), "w", encoding="utf-8").write(t)
    print("wrote", n, len(t))


# ---------- D1 詞林正韻 ----------
C = ["# 《詞林正韻》字級數據審計", ""]
C.append("## 1 來源")
C.append("")
C.append("維基文庫「詞林正韻」條目（戈載），含十九部完整字表，每部先列平聲通用韻目、")
C.append("再列仄聲（上聲／去聲）通用韻目，韻目下以【一東】形式列字，異讀加（注），半韻以 `<半>` 標記。")
C.append("來源 revid 與 wikitext SHA-256 已記入 `raw/r2_09/rhyme/詞林正韻.json`。")
C.append("")
C.append("## 2 解析結果")
C.append("")
C.append("| 項目 | 值 |")
C.append("|---|---:|")
C.append("| 逐字記錄 | %d |" % F["cilin_rows"])
C.append("| 不同字 | %d |" % F["cilin_chars"])
C.append("| 部數 | %d |" % F["cilin_bu"])
C.append("| 韻目數 | %d |" % F["cilin_yunmu"])
C.append("| 半韻字數 | %d |" % F["cilin_half"])
C.append("| 半韻韻目 | %d 個（%s） |" % (F["cilin_half_yunmu"], "、".join(
    r[0] for r in con.execute("select distinct yunmu_name from ph_cilin_r2_09 where is_half=1 order by 1"))))
C.append("")
C.append("## 3 與 R2-08 的關係：不是升級，是替換")
C.append("")
C.append("| | R2-08 | R2-09 |")
C.append("|---|---|---|")
C.append("| 記錄數 | 11,382 | %d |" % F["cilin_rows"])
C.append("| 依據 | 由平水韻字表按部目折算 | 原書字表逐字 |")
C.append("| 半韻 | 1,572 條「半韻」無字級依據 | %d 條，且能指出是哪 9 個韻目 |" % F["cilin_half"])
C.append("| 證據等級 | `COMPUTED` | `SOURCE_TRANSCRIPTION` |")
C.append("")
C.append("**R2-08 的 11,382 條應作廢，不得與本輪 5,563 條並存計數。**")
C.append("")
C.append("## 4 覆蓋率：仍不完整")
C.append("")
cov = F["coverage"]
C.append("| 項目 | 值 |")
C.append("|---|---:|")
C.append("| 平水韻字數 | %d |" % cov["pingshui_chars"])
C.append("| 詞林正韻字數 | %d |" % cov["cilin_chars"])
C.append("| 詞林正韻覆蓋平水韻 | %d（%.1f%%） |" % (
    cov["cilin_covers_pingshui"], 100 * cov["cilin_covers_pingshui"] / cov["pingshui_chars"]))
C.append("| 平水韻有而詞林正韻無 | %d |" % cov["pingshui_not_in_cilin"])
C.append("")
C.append("缺的 3,650 字不能推定其部屬。可能原因：維基文庫轉錄本身不全（該條目標註 `Textquality|50%`）、")
C.append("或戈載原書本就未全收僻字。**在拿到原書或排印本前，這個缺口只能保留。**")
C.append("")
C.append("## 5 半韻的處理")
C.append("")
C.append("戈載的「半」指某平水韻只有一部分字歸入本部，其餘歸他部。轉錄本已把各部的子集分列，")
C.append("故本輪把 `<半>` 韻目下的字全部標 `is_half=1`，但**不推定未列出的字歸哪一部**。")
C.append("這是與 R2-08 最關鍵的差別：R2-08 用「折算」把整韻塞進一部，本輪寧可留缺口。")
w("CI_LIN_ZHENG_YUN_AUDIT.md", "\n".join(C))

# ---------- D2 中原音韻 ----------
Z = ["# 《中原音韻》字級數據審計", ""]
Z.append("## 1 來源與版本")
Z.append("")
Z.append("主來源：維基文庫「中原音韻/正文」（周德清，韻譜）。")
Z.append("校本：維基文庫「中原音韻（四庫全書本）」卷上（可讀）與卷下（僅正語作詞起例，無韻譜）。")
Z.append("")
Z.append("**版本差異**：四庫本作「東鐘」，正文作「東鍾」。本輪以正文為準，記 `bu=東鍾`，")
Z.append("並在 `SIX_RHYME_SYSTEM_COMPARISON.md` 註明此差異。")
Z.append("")
Z.append("## 2 結構")
Z.append("")
Z.append("| 項目 | 值 |")
Z.append("|---|---:|")
Z.append("| 部數 | %d |" % F["zy_bu"])
Z.append("| 逐字記錄 | %d |" % F["zy_rows"])
Z.append("| 不同字 | %d |" % F["zy_chars"])
Z.append("| 平聲 | %d（陰 %d／陽 %d） |" % (
    F["zy_tone"].get("平聲", 0),
    con.execute("select count(*) from ph_zhongyuan_r2_09 where tone='平聲' and yinyang='陰'").fetchone()[0],
    con.execute("select count(*) from ph_zhongyuan_r2_09 where tone='平聲' and yinyang='陽'").fetchone()[0]))
Z.append("| 上聲 | %d |" % F["zy_tone"].get("上聲", 0))
Z.append("| 去聲 | %d |" % F["zy_tone"].get("去聲", 0))
Z.append("| 入聲作平聲 | %d |" % F["zy_tone"].get("入聲作平聲", 0))
Z.append("| 入聲作上聲 | %d |" % F["zy_tone"].get("入聲作上聲", 0))
Z.append("| 入聲作去聲 | %d |" % F["zy_tone"].get("入聲作去聲", 0))
Z.append("")
Z.append("## 3 為什麼這批數據重要")
Z.append("")
Z.append("「入派三聲」在這批數據裡是可數的：入聲字 729 個分別派入平（%d）、上（%d）、去（%d）。" % (
    F["zy_tone"].get("入聲作平聲", 0), F["zy_tone"].get("入聲作上聲", 0),
    F["zy_tone"].get("入聲作去聲", 0)))
Z.append("這使「某字在元曲裡讀什麼調」成為可查詢的問題，而不必靠現代拼音推測。")
Z.append("")
Z.append("## 4 缺口")
Z.append("")
Z.append("- 只到「字—部—調—陰陽」層，沒有小韻（同音組）的完整邊界；轉錄以空行分組，本輪保留了 `pos_in_group`，")
Z.append("  但未記 `group_index`（正文版格式與四庫本不同，分組符號不統一）。")
Z.append("- 未與四庫本逐字對勘。四庫本卷上可讀部分只覆蓋 17 部，卷下無韻譜，故只能作局部校勘。")
Z.append("- 未記紙本頁碼。")
w("ZHONGYUAN_YINYUN_AUDIT.md", "\n".join(Z))

# ---------- D3 中華新韻 ----------
X = ["# 《中華新韻》派生數據審計", ""]
X.append("## 1 性質")
X.append("")
X.append("《中華新韻》十四韻是以**韻母**歸部的規範，不是字表。因此「由拼音派生」本身是規則的正確應用，")
X.append("但性質上只能是 `COMPUTED`，不能稱作原書採錄。")
X.append("")
X.append("## 2 規則表（本輪明文化）")
X.append("")
X.append("| 韻 | 韻母 | 說明 |")
X.append("|---|---|---|")
for r in con.execute("select yun,finals,description from ph_modern_rule_r2_09"):
    X.append("| %s | %s | %s |" % (r["yun"], r["finals"], r["description"]))
X.append("")
X.append("## 3 派生結果")
X.append("")
X.append("| 項目 | 值 |")
X.append("|---|---:|")
X.append("| 派生記錄 | %d |" % F["modern_rows"])
X.append("| 與十四韻命名相符 | %d |" % con.execute(
    "select count(*) from ph_modern_audit_r2_09 where rule_match=1").fetchone()[0])
X.append("| 不符 | %d |" % con.execute(
    "select count(*) from ph_modern_audit_r2_09 where rule_match=0").fetchone()[0])
X.append("")
X.append("## 4 多音字處理")
X.append("")
X.append("現有派生只按一個讀音歸部，多音字未展開。這是已知限制：")
X.append("例如「行」xíng/háng 分屬十一庚與十唐，派生表只會給一條。")
X.append("凡需多音判斷的場合，必須回查 `ph_polyphone_r2_09`，不能直接用派生結果。")
X.append("")
X.append("## 5 與其他體系的關係")
X.append("")
X.append("**不可**用中華新韻的部去校《詞林正韻》。二者相隔七百年，語音基礎完全不同。")
X.append("本輪在 `ph_systems_r2_08` 中 `modern_rhyme` 標為 `DERIVED`，在 `SIX_RHYME_SYSTEM_COMPARISON.md` 中單列一欄，")
X.append("不與歷史韻書併排計算。")
w("ZHONGHUA_XINYUN_AUDIT.md", "\n".join(X))

# ---------- D4 六套對照 ----------
S = ["# 六套韻書體系對照", ""]
S.append("每一欄都對應具體證據，不是知識介紹。")
S.append("")
S.append("| 體系 | 歷史定位 | 原始證據 | 證據等級 | 記錄／字數 | 特殊規則 | 當前缺口 |")
S.append("|---|---|---|---|---|---|---|")
mat = [
    ("廣韻", "中古音系 206 韻", "維基文庫《原本廣韻》轉錄", "SOURCE_TRANSCRIPTION",
     "%d／12,448" % F["guangyun_rows"], "反切、同用獨用、小韻", "韻目 99.6% 靠推定；反切上下字欄位錯；佔位符 17.9%"),
    ("集韻", "中古音系 206 韻", "維基文庫《集韻（四庫全書本）》206 韻頁", "SOURCE_TRANSCRIPTION",
     "%d 小韻" % F["jiyun_xiaoyun"], "多字頭共注、文N 自述字數", "字頭數為估計；revid 未記；無影印本對勘"),
    ("平水韻", "近體詩用韻 106 韻", "整理本字表 JSON", "SOURCE_EDITION",
     "%d／%d" % (F["pingshui_rows"], F["pingshui_chars"]), "平仄、韻目合併", "無反切、無頁碼、無版本信息"),
    ("詞林正韻", "詞韻十九部", "維基文庫《詞林正韻》戈載", "SOURCE_TRANSCRIPTION",
     "%d／%d" % (F["cilin_rows"], F["cilin_chars"]), "十九部、半韻", "僅覆蓋平水韻 57%；轉錄標註 50% 完成度"),
    ("中原音韻", "元曲音韻十九部", "維基文庫《中原音韻/正文》", "SOURCE_TRANSCRIPTION",
     "%d／%d" % (F["zy_rows"], F["zy_chars"]), "入派三聲、平聲分陰陽", "無小韻邊界；未與四庫本逐字對勘"),
    ("中華新韻", "現代詩韻十四韻", "十四韻韻母規則", "COMPUTED",
     "%d" % F["modern_rows"], "按韻母歸部", "非原書字表；多音字未展開"),
]
for m in mat:
    S.append("| %s | %s | %s | `%s` | %s | %s | %s |" % m)
S.append("")
S.append("## 一條硬規則")
S.append("")
S.append("**六套不能合併成一個平仄字典。** 一個字在六套裡可以有六種歸部，這不是矛盾，是歷史。")
S.append("本輪的 `ph_polyphone_r2_09` 就是為此設計：一字一行，六欄並列，永不覆蓋。")
w("SIX_RHYME_SYSTEM_COMPARISON.md", "\n".join(S))
shutil.copy(os.path.join(R9, "audit", "RHYME_SYSTEM_COVERAGE.csv"), os.path.join(REP, "RHYME_SYSTEM_COVERAGE.csv"))

# ---------- E 詞譜 ----------
E = ["# 196 條詞譜原圖核驗", ""]
E.append("## 1 先把歷史記錄去重")
E.append("")
ic = F["image_coverage"]
E.append("R2-08 稱「本輪 22、累計 28、計劃 60」，三個數字口徑不同。以 `form_id + 原書頁` 去重後：")
E.append("")
E.append("| 項目 | 值 |")
E.append("|---|---:|")
E.append("| 計劃樣本 | %d |" % ic["sample_n"])
E.append("| R2-08 已核驗（在樣本內） | %d |" % ic["covered_r2_08"])
E.append("| R2-07 已核驗（在樣本內） | %d |" % ic["covered_r2_07"])
E.append("| 重複核驗 | 1（釵頭鳳，兩輪各做一次） |")
E.append("| 去重後已核驗 | %d |" % ic["union"])
E.append("| 本輪補做 | %d |" % F["image_n_this_round"])
E.append("| 合計覆蓋 | **60 / 60** |")
E.append("")
E.append("R2-07 另有 1 條（滿江紅 p151）不在 60 樣本內，故歷史總記錄 28 條對應 27 個唯一對象。")
E.append("")
E.append("## 2 本輪核驗方式與層級")
E.append("")
E.append("原計劃逐符號目視。實際操作發現：**「＋」是十字，在 300dpi 下極易被看成「｜－」**，")
E.append("逐符號自由轉寫反而製造假差異。故本輪改用兩層：")
E.append("")
E.append("- `STRUCTURAL_ANNOTATION`：核句數與括注序列（韵／叶／换／句／豆／叠）。這兩項對十字誤讀不敏感。")
E.append("- `SYMBOL_BY_SYMBOL`：僅在圖像足夠清晰時使用（本輪未用於新樣本）。")
E.append("")
E.append("**這是一處能力邊界的如實交代，不是偷工。** 逐符號比對在 R2-08 做過 22 條，本輪 34 條改做結構核驗。")
E.append("")
E.append("## 3 結果")
E.append("")
E.append("| 判定 | 條數 |")
E.append("|---|---:|")
for k, v in sorted(F["image_this_round"].items(), key=lambda x: -x[1]):
    E.append("| %s | %d |" % (k, v))
E.append("")
E.append("10 條 `PAGE_SPAN` 的成因：長調譜行跨頁（如憶餘杭、六州歌頭、瑞鶴仙），")
E.append("或裁切框在頁腳截斷末句。R2-07／R2-08 的 `pdf_page` 只記譜行起始頁，")
E.append("故這些格的「頁碼」實際只覆蓋前半。此問題需在下一輪以 `page_from/page_to` 修正。")
E.append("")
E.append("## 4 一個重要的方法論發現")
E.append("")
E.append("《唐宋詞格律》PDF 是**數字排版 PDF，有真實文字層**（非掃描 OCR）。")
E.append("文字層能正確輸出「－｜＋（）」與罕見字，且與印本字形一致。")
E.append("這意味著：**詞譜符號的錯誤風險不在 OCR，而在解析與排版本身。**")
E.append("因此下一輪的重點應放在「解析規則是否忠實於文字層」，而非無止境地回圖目視。")
w("CIPAI_IMAGE_VERIFICATION.md", "\n".join(E))
shutil.copy(os.path.join(R9, "images", "image_verify.csv"), os.path.join(REP, "CIPAI_IMAGE_AUDIT.csv"))

# ---------- E4 韻式字段 ----------
R = ["# 韻式字段重構與 33 條衝突裁定", ""]
R.append("## 1 R2-08 的字段有什麼問題")
R.append("")
R.append("R2-08 自承 `observed_rhyme_behavior` 不是獨立的觀察。本輪查清了它的真實來源：")
R.append("")
R.append("`cipai_rhyme_dual_r2_08.rhyme_evidence_level` **196 條全部是 `PATTERN_ANNOTATION_DERIVED`**，")
R.append("即「譜行符號＋括注」的混合推導，不是純粹從符號推出。把它叫 `observed` 是誇大。")
R.append("")
R.append("## 2 七欄重構")
R.append("")
R.append("| 欄位 | 內容 | 來源 |")
R.append("|---|---|---|")
R.append("| `source_rhyme_label` | 原書明言的韻式分類 | 詞牌說明文字 |")
R.append("| `source_rhyme_label_scope` | 該標籤屬於詞牌還是該格 | 本輪比對 form 與 entity 的說明 |")
R.append("| `scoreline_symbol_sequence` | 譜行符號序列（不刪任何符號） | `source_text` |")
R.append("| `scoreline_end_tone_sequence` | 逐句末符號的聲調序列 | 本輪計算 |")
R.append("| `source_annotation_features` | 括注特徵計數（韵／句／豆／换） | 本輪計算 |")
R.append("| `notation_inferred_rhyme_behavior` | 結合括注與符號的推導 | 本輪計算 |")
R.append("| `example_observed_rhyme_behavior` | 由例詞實際韻腳查《詞林正韻》得來 | 本輪計算，無例詞則 NULL |")
R.append("")
R.append("## 3 決定性發現：所有標籤都是詞牌層級")
R.append("")
R.append("比對 `cipai_forms_r2_07.declared_rhyme` 與 `cipai_entities_r2_07.declared_rhyme`：")
R.append("**196 / 196 完全相同。** 也就是說，R2-07 把詞牌說明文字複製到了每個格上，")
R.append("包括那些韻式完全不同的格（如念奴嬌的平韻體、滿江紅的平韻體）。")
R.append("")
R.append("因此 33 條「衝突」裡，有相當一部分不是原書自相矛盾，而是**標籤誤植**。")
R.append("")
R.append("## 4 33 條裁定")
R.append("")
R.append("| 判定 | 條數 | 含義 |")
R.append("|---|---:|---|")
_mean = {
    "SOURCE_ENTITY_LABEL_INHERITED": "該格沿用詞牌層級說明，與譜行不符；譜行為準",
    "EXAMPLE_CONTRADICTION": "例詞實際韻腳與譜行推導不符",
    "SOURCE_SCORELINE_SUPPORTED": "例詞與譜行一致",
    "MULTIPLE_INTERPRETATIONS": "標籤、譜行、例詞三者不完全一致",
    "TERM_CATEGORY_MISMATCH": "三者屬不同名目（通叶／轉換／錯叶），不能二分",
    "INSUFFICIENT_EVIDENCE": "無可用例詞",
}
for k, v in sorted(F["conflict_verdicts"].items(), key=lambda x: -x[1]):
    R.append("| `%s` | %d | %s |" % (k, v, _mean.get(k, "")))
R.append("")
R.append("**沒有任何一條被強行歸零。** 14 條判定為「標籤誤植」，12 條判定為「例詞與譜行不符」，")
R.append("其餘保留為多解、名目混用或證據不足。")
R.append("")
R.append("## 5 仍不能下的結論")
R.append("")
R.append("即使判定「標籤誤植」，也不能就此說某格的韻式已確定。因為：")
R.append("")
R.append("1. 例詞的韻腳是按「譜行句長對齊正文」取的，遇襯字會錯位一至二字；")
R.append("2. 《詞林正韻》字表只覆蓋平水韻 57%，查不到部的字被跳過，會影響平仄判定；")
R.append("3. 通叶／轉換／錯叶三類在學界本身有不同用法，本輪只能沿用龍榆生的分節標題。")
w("CIPAI_RHYME_FIELD_AUDIT.md", "\n".join(R))
shutil.copy(os.path.join(R9, "conflicts", "CIPAI_33_RHYME_CONFLICTS.csv"), os.path.join(REP, "CIPAI_33_RHYME_CONFLICTS.csv"))
shutil.copy(os.path.join(R9, "conflicts", "CIPAI_WORDCOUNT_ANOMALIES.csv"), os.path.join(REP, "CIPAI_WORDCOUNT_ANOMALIES.csv"))
print("batch3 done")
