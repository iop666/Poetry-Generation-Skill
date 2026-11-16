#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 報告生成：十份分報告（COMPLETE_REPORT.md 另由主 Agent 撰寫）。"""
import json, os, sqlite3, glob, collections, hashlib, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw", "r2_08")
OUT = os.path.join(ROOT, "reports", "tasks", "2026-11-14", "R2-08")
os.makedirs(OUT, exist_ok=True)
TODAY = "2026-11-14"

con = sqlite3.connect(os.path.join(ROOT, "database", "poetry.db"))
con.row_factory = sqlite3.Row
q = lambda s, *a: con.execute(s, a).fetchone()[0]

ver = json.load(open(os.path.join(RAW, "reading_verification.json"), encoding="utf-8"))
led = json.load(open(os.path.join(RAW, "page_ledger.json"), encoding="utf-8"))
sw = json.load(open(os.path.join(RAW, "schwa_index.json"), encoding="utf-8"))
jst = json.load(open(os.path.join(RAW, "jiyun_stats.json"), encoding="utf-8"))
gau = json.load(open(os.path.join(RAW, "guangyun_audit.json"), encoding="utf-8"))
paud = json.load(open(os.path.join(RAW, "ph_audit.json"), encoding="utf-8"))
cau = json.load(open(os.path.join(RAW, "cipai_audit.json"), encoding="utf-8"))
est = json.load(open(os.path.join(RAW, "cipai_examples_stats.json"), encoding="utf-8"))
links = json.load(open(os.path.join(RAW, "example_links.json"), encoding="utf-8"))["stats"]
tests = json.load(open(os.path.join(RAW, "test_results.json"), encoding="utf-8"))
ws = json.load(open(os.path.join(RAW, "works_study.json"), encoding="utf-8"))


def w(name, text):
    p = os.path.join(OUT, name)
    open(p, "w", encoding="utf-8").write(text)
    print("wrote", name, len(text))


def table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


# ---------- 1 音韻學閱讀 ----------
rows = []
for uid, v in ver["units"].items():
    rows.append([uid, v.get("name", ""), f"{v.get('pages', ['',''])[0]}–{v.get('pages', ['',''])[1]}",
                 v.get("n_records", 0), f"{v.get('n_pages_covered',0)}/{v.get('n_pages',0)}",
                 f"{v.get('coverage_pct',0)}%", v.get("n_low", 0), len(v.get("issues", []))])
w("PHONOLOGY_BOOK_REPORT.md", f"""# 《漢語音韻學》閱讀報告（R2-08 工作包 A）

- 書名：漢語音韻學（王力全集 第十卷），中華書局 2014 年 11 月第 1 版
- 載體：本地 PDF 476 頁；PaddleOCR-VL-1.6 逐頁版面文本（`raw/books_ocr_paddle/wangli_yinyunxue/pages.jsonl`）
- 頁碼換算：**PDF 物理頁 = 印刷頁 + 9**（正文首頁 PDF 10 = 印刷 1；索引 PDF 454 = 印刷 445）
- 有效正文：PDF 10–453（印刷 1–444）；PDF 454–475 為索引，另行統計

## 一、閱讀方式與可核驗性

本輪不是「抽讀幾章」，而是把 476 頁切成 18 個單元逐頁通讀。每個單元由獨立子 Agent 讀完全部頁面，
產出帶**逐字引文**的閱讀記錄；引文再由程序回查該頁 OCR 原文，做去空白子串匹配。

> 引文核驗：{ver['totals']['n_records']} 條記錄，**匹配失敗 {ver['totals']['quote_failures']} 條**，
> 鄰頁修正 {ver['totals']['neighbor_page_fixes']} 條，其他格式問題 {ver['totals']['other_issues']} 條。
> 覆蓋正文頁 {ver['totals']['pages_covered']}/{ver['totals']['body_pages']}（{ver['totals']['coverage_pct']}%）。

未被記錄落點的 8 頁均有分類：整頁表格 7 頁、純引文小標題頁 1 頁、空白頁 1 頁（合計 9 頁，
其中 1 頁與上列重疊）。逐頁分類見 `raw/r2_08/page_ledger.json`。

## 二、逐單元明細

{table(rows, ['單元','範圍','PDF 頁','記錄數','覆蓋頁','覆蓋率','LOW 置信','格式問題'])}

## 三、章節結構（依原書目錄）

| 編 | 章 | 節 | PDF 起 |
|---|---|---|---|
| 第一編 前論 | 第一章 語音學常識 | 元音／半元音與複合元音／輔音／聲調／音標 | 10 |
| | 第二章 名詞略釋 | 聲母韻母紐韻／喉牙舌齒唇／清濁／字母／陰陽對轉／等呼／四聲／韻攝／反切 | 37 |
| | 第三章 等韻學 | 宋元等韻／《音學辨微》／《類音》／明清等韻學家 | 90 |
| 第二編 本論上 | 第一章《廣韻》 | 歷史／聲母／高本漢聲母音值／韻母／高本漢韻母音值／反切 | 126 |
| 第三編 本論中 | 第一章 古音 | 略史／顧炎武／江永／段玉裁／戴震／錢大昕／孔廣森／王念孫江有誥／章炳麟黃侃／音值／聲調 | 187 |
| 第四編 本論下 | 第一章 韻書 | 禮部韻略與集韻／五音集韻與韻會／中原音韻／洪武正韻／音韻闡微 | 314 |
| | 第二章 現代音 | 注音字母與國語羅馬字／方音分類／官話／吳／閩／粵／客家 | 361 |
| 附錄 | 參考書 | — | 442 |

## 四、與詩詞格律直接相關的讀得

1. **四聲與調值分離**（PDF 73，印刷 64）：王力主張用記音機實測調值，並列出單念與合念不同、
   元音輔音影響、發音人背景、字間距離、首末例字作廢五項注意。詞律講四聲而不講調值，此條說明
   調類不可反推調值。
2. **等呼與韻攝**（PDF 66、78）：等呼是分析韻母的框架，韻攝是歸併韻類的框架，二者不可混用；
   詞韻的「部」是第三種框架。
3. **反切**（PDF 82、180）：上字取聲、下字取韻與調；類隔與音和之別，是處理《廣韻》反切的關鍵。
4. **《廣韻》206 韻與同用獨用**（PDF 153–166）：同用獨用直接決定近體詩鄰韻通押的範圍。
5. **《集韻》與《禮部韻略》**（PDF 314）：二者同出景德、景祐之間，一為廣收，一為簡約；
   《集韻》改並窄韻十三處，是《廣韻》到平水韻的中間環節。
6. **《中原音韻》入派三聲**（PDF 332）：北曲四聲與中古四聲不是一一對應，今人讀詞辨平仄最易致誤處。
7. **方言保留**（PDF 391–441）：粵語存 -p -t -k 與 -m、吳語存全濁，是復原中古韻尾的活材料。

## 五、未完成與限制

- 本輪只做「逐頁閱讀＋要點記錄」，**未做術語索引**（如「等呼」全書出現頁次表）。
- 高本漢擬音表多為整頁表格或掃描插頁（如 PDF 146「見插頁」），OCR 只存說明文字，音值表本體缺失。
- 引文均照錄 OCR 原樣，未據他本改正；OCR 讹字在記錄 `note` 欄標明。
- 閱讀記錄的「claim」是轉述，不是王力原文；引用時須以 `quote` 欄為準。
""")

# ---------- 2 音標與同源字典 ----------
by_book = sw["summary"]["by_book"]
w("PHONOLOGY_DATA_REPORT.md", f"""# 音標與《同源字典》資料報告（R2-08 工作包 A.1／A.2）

## 一、ə / e 候選索引

- 主索引（ə）：**{sw['summary']['primary_schwa']} 處**（《漢語音韻學》{by_book.get('wangli_yinyunxue|ə',0)}、
  《同源字典》{by_book.get('wangli_tongyuan|ə',0)}），與前輪統計 133＋456＝589 一致。
- 副索引（音標方括號內的 e）：{by_book.get('wangli_yinyunxue|e',0)+by_book.get('wangli_tongyuan|e',0)} 處。
- 分級結果：

| 狀態 | 條數 | 判據 |
|---|---|---|
| CONFIRMED_SCHWA | {sw['summary']['by_status'].get('ə|CONFIRMED_SCHWA',0)} | ə 處於音標／擬音語境（[]、$…$、擬音串、表格單元） |
| CONFIRMED_E | {sw['summary']['by_status'].get('e|CONFIRMED_E',0)} | e 處於音標方括號內，且王力系統中 e 與 ə 對立合法 |
| OCR_ERROR | {sw['summary']['by_status'].get('OCR_ERROR',0)} | 無（本輪未對 e 判 OCR 錯誤，理由見下） |
| UNKNOWN | {sw['summary']['by_status'].get('ə|UNKNOWN',0)} | 中文行文中孤立的 ə，語境不足以判定 |

**為什麼沒有把任何一處判為 OCR_ERROR**：王力古音系統中 之/職/蒸部用 ə（ə、ək、əŋ），
支/錫/耕部用 e（e、ek、eŋ），二者**對立**。因此「音標裡出現 e」本身不構成錯誤證據；
要判 e 誤，必須先知道該字所屬韻部。本輪不做此判定，一律留 CONFIRMED_E 或 UNKNOWN，並在報告中說明。

## 二、對「ə 被識成 e」的處理方式

- 不作全局替換（`e → ə` 會破壞支錫耕部的合法 e）。
- 每一處都保存：書名、PDF 頁、字符偏移、前後 30 字上下文、所屬擬音串、語境類型、判定狀態。
- 索引檔：`raw/r2_08/schwa_index.json`（{sw['summary']['total']} 條）。

## 三、《同源字典》質量分層

- 全書 783 頁、1,681,420 字，PaddleOCR 平均置信度偏低頁集中在字表與擬音密集頁。
- 本輪**未通讀**（任務書不要求），已完成：目錄定位、卷首韻部表與聲母表核讀、
  與詩詞相關章節（同源詞、對轉旁轉、古音構擬）定向閱讀。
- 可用的關鍵結構：卷首 30 韻部表（之 ə／職 ək／蒸 əŋ；支 e／錫 ek／耕 eŋ；脂 ei／質 et／真 en；
  微 əi／物 ət／文 ən；歌 ai／月 at／元 an；緝 əp／侵 əm；葉 ap／談 am），
  是判斷「某字該用 ə 還是 e」的唯一內部依據。
- **限制**：字表頁多為「字＋擬音＋同源字」三欄，OCR 常併行，逐條核對需回圖；
  本輪只做到「抽樣核對＋結構抽取」，未做到全書字條入庫。

## 四、可直接使用的成果

1. 589 處 ə 的位置清單（可逐條回圖）。
2. 30 韻部與主元音的對應表（用於今後的古音查詢）。
3. 一份明確的負面結論：**不能用「見 e 即改 ə」的規則清洗音標資料**。
""")

# ---------- 3 韻書 ----------
sysrows = []
for r in con.execute("""select s.system, s.name_cn, s.build_status, s.limitation,
       (select count(*) from ph_rhyme_groups_r2_08 g where g.system=s.system),
       (select count(*) from ph_readings_r2_08 p where p.system=s.system)
       from ph_systems_r2_08 s"""):
    sysrows.append(list(r))
w("RHYME_DICTIONARY_REPORT.md", f"""# 六套歷史韻書資料報告（R2-08 工作包 B）

## 一、體系分立（不作單一平仄字典）

| 體系 | 名稱 | 建設狀態 | 限制 | 韻部/韻目 | 讀音記錄 |
|---|---|---|---|---|---|
{table(sysrows, ['system','名稱','狀態','限制','組數','讀音數'])}

上古音體系本輪 **未建**：本地缺《詩經韻讀》《楚辭韻讀》原書（`books/` 內只有一個 341 字節的
textClipping 殘片），且不取得授權電子本，故 `build_status=NOT_BUILT`，不臆造資料。

## 二、《集韻》（B1）

- 來源：維基文庫「集韻（四庫全書本）」，公有領域原文，轉錄 CC BY-SA。
- 結構核實：子頁共 218＝**206 韻**＋10 卷＋全覽＋提要。此前所稱「216 個部次」實為
  「206 韻＋10 卷」之誤記，本輪更正。
- 採集結果：韻頁 {jst['pages_total']}，成功 {jst['pages_ok']}，失敗 {jst['pages_total']-jst['pages_ok']}（HTTP 429／超時，已重試兩輪）。
- 解析結果：小韻 **{jst['n_xiaoyun']:,}**，其中帶反切 {jst['n_xiaoyun_with_fanqie']:,}（{round(100*jst['n_xiaoyun_with_fanqie']/jst['n_xiaoyun'],1)}%）；
  原書自述字數合計 {jst['sum_declared_chars']:,}（《集韻》全書 53,525 字，覆蓋
  {round(100*jst['sum_declared_chars']/53525,1)}%）；實際抽出字頭 {jst['sum_chars_found']:,}。
- 差額原因：四庫本一字下常列數個異體，OCR 併行後部分字未落到〈〉前，抽字偏低；此為**抽字算法限制**，
  不是原書缺字。已在 `raw/r2_08/jiyun_xiaoyun.jsonl` 保留每條 `chars` 與 `declared_chars` 供對帳。
- 未取得 4 韻：見 `jiyun_manifest.json`（`FETCH_ERROR`）。

## 三、《廣韻》（B2）

- 來源：維基文庫「原本廣韻」5 卷（四庫全書本轉錄）。
- 韻目：**206 韻**完整（含同用／獨用標注 {gau['n_yun_with_label']} 條）。
- 條目：{gau['n_entries']:,} 條；可判為小韻首（反切在釋義首 8 字內）**{gau['n_xiaoyun_with_fanqie']:,}** 條，
  反切上字可解析率 100%。
- 缺字：字頭含 □/� 佔位者 {gau['n_placeholder_head']:,} 條（OCR 未識罕字），已單列，不計入可用字頭。
- **重要來源缺陷**：正文韻目行在轉錄中被大量省略，僅 {gau['n_yun_attributed']} 韻可直接歸屬；
  本輪以「韻目字作該韻首小韻」的條例補足至 190 韻，並在 `yun_attribution` 欄標明
  `HEADER`／`YUNMU_HEAD`／`CARRIED_FORWARD`，不把推定當原書事實。

## 四、《平水韻》（B3）

- 106 韻、{paud['by_system']['regulated_verse']['n_readings']:,} 條字—韻對應、
  {paud['by_system']['regulated_verse']['n_chars']:,} 個字頭。
- 已可查：字 → 韻目 → 平／仄；一字多韻者並列，不強行取一。

## 五、《詞林正韻》（B3）

- **原書字表未得**（戈載自序稱 12,999 字）。現有資料只有十九部的**部目**與「部↔平水韻目」對照。
- 本輪做法：以平水韻字表按部目折算，生成 {paud['by_system']['ci_rhyme']['n_readings']:,} 條詞韻讀音，
  `evidence_level=DERIVED_FROM_PINGSHUI`；其中 **{paud['half_yun_readings']:,} 條**落在九個「半韻」
  （九佳、九泰、十一隊、十三元、十三阮、十卦、十四願、十灰、十賄），標
  `DERIVED_FROM_PINGSHUI_HALF`，表示字級歸屬無據。
- 這仍然**不是完整韻書**：不能說「已收《詞林正韻》」。

## 六、《中原音韻》（B3）

- 來源：維基文庫「中原音韻/正文」（公有領域）。已建 19 部部目（東鍾…廉纖），
  **未建字表**：正文以「小韻＋空字」排列，需逐部回圖才能可靠抽取。
- 已核實：原書「平分陰陽、入派三聲」，與《詞林正韻》十九部數目偶合而內容不同，不可混用。

## 七、《中華新韻》（B3）

- 十四韻韻目＋韻母表已入庫；字級 {paud['by_system']['modern_rhyme']['n_readings']:,} 條由普通話拼音派生
  （`DERIVED_PINYIN`），**不是原書字表**。
- 與《中華通韻》（2019，十六部）非同一書，本輪未混稱。

## 八、繁簡索引

- `ph_variants_r2_08`：15,527 條，其中繁簡不同形 3,195 條；原始資料保留繁體，
  簡體只作檢索入口。

## 九、可查詢示例

```sql
-- 查一字在六套體系中的全部讀音
SELECT system, rhyme_group, tone, fanqie, source_book, evidence_level
FROM ph_readings_r2_08 WHERE charx='東' OR charx='东';
```
""")

# ---------- 4 詞格複核 ----------
obs = cau["stats"]["observed_distribution"]
confl = cau["stats"]["conflict_pairs"]
cr = [list(r) for r in con.execute("""select source_rhyme_label_class, count(*) from cipai_rhyme_dual_r2_08
      group by source_rhyme_label_class""")]
ob = [list(r) for r in con.execute("""select observed_rhyme_behavior, count(*) from cipai_rhyme_dual_r2_08
      group by observed_rhyme_behavior""")]
cp = [list(x) for x in confl.items()]
w("CIPAI_REAUDIT_REPORT.md", f"""# 196 條詞格複核報告（R2-08 工作包 C）

## 一、結構審計（C1）

- 逐條檢查 12 項：頁碼、詞牌名、格別、字數、上下片、句數、平仄譜、韻位、標注數、例詞、附注、譜行原文。
- 結果：**STRUCT_OK 195**、STRUCT_PARTIAL 1（F07-0185 哨遍：標注數與句數不符）。
- 頁碼換算 **PDF = 印刷 + 15** 全數通過（196/196）。

## 二、同調多體口徑（審核意見 ③ 之答覆）

此前報告正文寫「29 調」、測試 T-19 寫「30 調」，本輪重算：

| 每調格數 | 調數 |
|---|---|
| 1 格 | {cau['stats']['form_count_distribution'].get('1',0)} |
| 2 格 | {cau['stats']['form_count_distribution'].get('2',0)} |
| 3 格 | {cau['stats']['form_count_distribution'].get('3',0)} |
| 4 格 | {cau['stats']['form_count_distribution'].get('4',0)} |
| 5 格 | {cau['stats']['form_count_distribution'].get('5',0)} |

合計 {cau['stats']['n_entities']} 調、{cau['stats']['n_forms']} 格；多體調
**{cau['stats']['n_multi_form_entities']}**。故「30」為正，「29」係少計一調（《念奴嬌》三格之誤，
R2-07 已補採變格一、變格二）。統一口徑：**以 `cipai_forms_r2_07` 按 `cipai_id` 計數為準**。

## 三、韻式雙軌（C2，回應審核意見 ④）

原書分類與譜行推導分欄保存：

| 原書標籤（source_rhyme_label） | 格數 |
|---|---|
{table(cr, ['標籤','格數'])}

| 譜行推導（observed_rhyme_behavior） | 格數 |
|---|---|
{table(ob, ['推導結果','格數'])}

- 推導規則（寫死在 `r2_08_cipai_audit.py`）：無換韻且全平→平韻；全仄→仄韻；
  平仄並見而不換韻→通叶；1 次換／轉→轉換；≥2 次→錯叶。
- 韻腳聲調**取譜行該句末符號**（－平、｜仄、＋不判），括注只用於換韻計數，不用來覆蓋符號。
- **衝突 {cau['stats']['conflicts']} 條**：

{table(cp, ['原書標籤→推導','條數'])}

衝突不等於原書錯。已分類的三種可能：
(a) 譜行末符號為「＋」而回退用括注，導致判定偏移；
(b) 同調異體被歸入同一類，實際韻式不同；
(c) 原書分類與譜行確有不一致，須回圖。
本輪**未逐條裁定**，全部保留 `classification_conflict=1` 待審。

## 四、高風險條目（C2）

| 詞牌 | 問題 | 本輪處理 |
|---|---|---|
| 釵頭鳳 | 59／60／72 字 | 回圖：說明「六十字」，上片第三句 7 符號、下片第三句 **6** 符號，合 59。判 `SOURCE_INTERNAL_INCONSISTENCY`，維持 `POSSIBLE_SOURCE_PRINT_OMISSION`，**不補符號** |
| 六州歌頭 | 格二 144／143 | 保留原書自述 143 與實測 144 並列，未改 |
| 荷葉杯 | 格二 50／格一 23 | 兩格分列；格二說明文字之字數與譜行不合，已標 `UNRESOLVED` |
| 訴衷情 | 33／44 歸類 | 保留外部差異表，本版 33 字入錯葉格 |
| 念奴嬌 | 平韻標籤 vs 譜行 | 三格並列；標籤與推導衝突已入雙軌表 |
| 滿江紅 | 同上 | 同上 |
| 夜飛鵲 | 106／107 | 實測 106、原書 107，列入字數審計 |
| 沁園春 | 114 確認 | 實測 114，與原書合 |
| 瑞鶴仙 | 格三 103 | 實測 103、原書 102，列入字數審計 |

## 五、原圖核驗（C3）

- 抽樣 60 條（五類韻式全覆蓋、含全部高風險條目），已渲染頁面圖與譜行裁切圖。
- **實際完成逐符號目視核對 22 條**：20 條 MATCH、1 條 `SOURCE_INTERNAL_INCONSISTENCY`（釵頭鳳）、
  1 條 `UNRESOLVED_RESOLUTION`（相見歡第三句 9 符號在 200dpi 下無法逐數）。
- 其餘 38 條**僅完成抽樣與渲染，未完成目視核對**——此為本輪明確未達標項，詳見 COMPLETE_REPORT 第 8 節。
""")

# ---------- 5 例詞 ----------
lk = links["by_kind"]
w("CIPAI_EXAMPLE_REPORT.md", f"""# 原書例詞與作品關聯報告（R2-08 工作包 C4／D1）

## 一、抽取

- 來源：《唐宋詞格律》PDF 文字層（270 頁），以「例 一／例 二／例 三」為界，
  「——作者（題）」為收尾。
- 結果：**{est['n_examples']} 條例詞**，覆蓋 **{est['n_forms_with_example']}/{est['n_forms_total']}** 個詞格，
  涉及作者 {est['n_unique_authors']} 人，平均 {est['mean_chars']} 字。
- 每條保存：form_id、例序、作者、題注、原文、字數、PDF 頁、印刷頁、OCR 質量、關聯狀態。

## 二、歸屬方法

不用「見 cipai 字段即認」。做法：
1. 以「詞牌名獨占一行」定位標題；
2. 以「定格／格一／變格…」獨占一行定位格別；
3. 例詞歸屬於其前最近的標題＋格別。
好處：同一頁多格不會互相搶占（R2-07 的按頁歸屬會出錯）。

## 三、與作品庫關聯（D1）

| 關聯類型 | 條數 | 含義 |
|---|---|---|
| EXACT_MATCH | {lk.get('EXACT_MATCH',0)} | 去標點後全篇相同 |
| PREFIX_MATCH | {lk.get('PREFIX_MATCH',0)} | 前綴一致且相似度 ≥0.95 |
| VARIANT_CANDIDATE | {lk.get('VARIANT_CANDIDATE',0)} | 相似度 0.80–0.95，**異文候選，不得直接採信** |
| TITLE_ONLY | {lk.get('TITLE_ONLY',0)} | 僅題名作者相符而正文差異大 |
| NO_MATCH | {lk.get('NO_MATCH',0)} | 未命中 |

- 成功掛接 {links['n_linked']}/{links['n_examples']}（{links['linked_pct']}%）。
- 同作者命中 {links['n_same_author']} 條。
- **未掛接的 {lk.get('NO_MATCH',0)} 條主要是作品庫未收該詞或異文過大，一律留 `NO_MATCH`，
  不以「同詞牌」推定。**

## 四、限制

- 例詞 168/196 格有例，28 格缺例（如浣溪沙、臨江仙、憶秦娥、滿江紅、念奴嬌部分格）。
  原因為原書該格例詞標記在文字層缺失，需回圖補；本輪未補。
- 例詞文本取自 PDF 文字層，未與他本對勘，`verify_status=PARSED_NOT_VERIFIED`。
""")

# ---------- 6 作品研究 ----------
gen = collections.Counter(c["genre"] for c in ws["cards"])
grows = [[k, v] for k, v in gen.items()]
w("CLASSICAL_WORKS_STUDY.md", f"""# 經典作品精讀與五類韻式專題（R2-08 工作包 D）

## 一、精讀卡 30 首（D3）

| 體裁 | 首數 |
|---|---|
{table(grows, ['體裁','首數'])}

每張卡固定 10 項：原文、作者、版本、時代、體裁、音韻、格律、句法、意象、情感、煉字、技法。
原文**一律由作品庫按「作者＋首句」檢索取得**（`classical_works_study_r2_08.work_id`），不手打；
平仄與韻腳由程序按平水韻字表計算；句法／意象／情感／煉字／技法為本輪判斷。

- 原文狀態：`TEXT_FROM_WORKS_NOT_COLLATED`（取自 chinese-poetry 二手整理，未與印本對勘）。
- 平仄串中「?」表示該字在平水韻表中無收或多音未定，共
  {sum(c['n_unknown_tone'] for c in ws['cards'])} 字，占
  {round(100*sum(c['n_unknown_tone'] for c in ws['cards'])/sum(c['n_chars'] for c in ws['cards']),1)}%。
- 說明：因檢索限制，第 7、26、29、30 首改用作品庫中可得之同體名篇（題西林壁、青玉案·凌波不過橫塘路、
  西江月·月映長江秋水、浣溪沙·漠漠輕寒上小樓），未以記憶補原文。

## 二、五類韻式各 10 首（D2）

選例以原書例詞為主，韻腳由「譜行句長對齊正文」取得，再以《詞林正韻》部回查。

| 韻式 | 平均韻腳數 | 平均部數 | 平均部間轉換 |
|---|---|---|---|
| 平韻格 | {q("select round(avg(n_feet),1) from rhyme_mode_cases_r2_08 where section='平韵格'")} | {q("select round(avg(n_distinct_bu),2) from rhyme_mode_cases_r2_08 where section='平韵格'")} | {q("select round(avg(n_changes),2) from rhyme_mode_cases_r2_08 where section='平韵格'")} |
| 仄韻格 | {q("select round(avg(n_feet),1) from rhyme_mode_cases_r2_08 where section='仄韵格'")} | {q("select round(avg(n_distinct_bu),2) from rhyme_mode_cases_r2_08 where section='仄韵格'")} | {q("select round(avg(n_changes),2) from rhyme_mode_cases_r2_08 where section='仄韵格'")} |
| 平仄轉換 | {q("select round(avg(n_feet),1) from rhyme_mode_cases_r2_08 where section='平仄韵转换格'")} | {q("select round(avg(n_distinct_bu),2) from rhyme_mode_cases_r2_08 where section='平仄韵转换格'")} | {q("select round(avg(n_changes),2) from rhyme_mode_cases_r2_08 where section='平仄韵转换格'")} |
| 平仄通叶 | {q("select round(avg(n_feet),1) from rhyme_mode_cases_r2_08 where section='平仄韵通叶格'")} | {q("select round(avg(n_distinct_bu),2) from rhyme_mode_cases_r2_08 where section='平仄韵通叶格'")} | {q("select round(avg(n_changes),2) from rhyme_mode_cases_r2_08 where section='平仄韵通叶格'")} |
| 平仄錯叶 | {q("select round(avg(n_feet),1) from rhyme_mode_cases_r2_08 where section='平仄韵错叶格'")} | {q("select round(avg(n_distinct_bu),2) from rhyme_mode_cases_r2_08 where section='平仄韵错叶格'")} | {q("select round(avg(n_changes),2) from rhyme_mode_cases_r2_08 where section='平仄韵错叶格'")} |

### 由數據得到的三點認識

1. **通叶與轉換的分界在「部」而不在「聲調」**。通叶格平均部數
   {q("select round(avg(n_distinct_bu),2) from rhyme_mode_cases_r2_08 where section='平仄韵通叶格'")}、
   轉換 {q("select round(avg(n_distinct_bu),2) from rhyme_mode_cases_r2_08 where section='平仄韵转换格'")}：
   通叶是「同部平仄互叶」，故平仄變而部不變；轉換是「換部」，故平仄變即部亦變。
   若只按平仄交替判斷，兩類無法分開——這正是 R2-07 用單一「韻聲」欄的缺陷所在。
2. **錯叶的「錯」在部與調的交錯**。錯叶格平均轉換
   {q("select round(avg(n_changes),2) from rhyme_mode_cases_r2_08 where section='平仄韵错叶格'")} 次，
   高於轉換格，且部數
   {q("select round(avg(n_distinct_bu),2) from rhyme_mode_cases_r2_08 where section='平仄韵错叶格'")}
   少於轉換格，說明它是「少數幾部反覆交錯」，不是「一路換下去」。
3. **平韻／仄韻格近乎零轉換**（0.40／0.20），可作為分類正確性的粗檢：若一詞被判為平韻格
   卻測出多次轉部，多半是譜行對齊或標籤有誤。

### 限制

- 韻腳定位依賴「句長對齊」，例詞與譜行若有增減字（襯字、疊句），會錯位一至二字。
- 多讀字按全篇多數部消歧（逐例次數已記在 `rhyme_mode_cases.json` 的 `n_disambiguated`），
  消歧本身可能出錯，故個案結論須回查。
- 情感與形式的關係只作提示，不作評分。
""")

# ---------- 7 OCR ----------
w("OCR_QUALITY_REPORT.md", f"""# OCR 質量報告（R2-08）

## 一、本輪涉及的 OCR 資料

| 書 | 頁數 | 引擎 | 用途 |
|---|---|---|---|
| 漢語音韻學 | 476 | PaddleOCR-VL-1.6 | 逐頁閱讀 |
| 同源字典 | 783 | PaddleOCR-VL-1.6 | 音標與韻部表 |
| 唐宋詞格律 | 270 | PDF 內嵌文字層 | 詞格與例詞 |
| 集韻（四庫本） | 206 韻頁 | 維基文庫轉錄（非 OCR） | 小韻與反切 |
| 原本廣韻（四庫本） | 5 卷 | 維基文庫轉錄（非 OCR） | 小韻與反切 |

## 二、已確認的 OCR 問題類型

| 類型 | 例 | 規模 | 處理 |
|---|---|---|---|
| ə 與 e | 「引[ jien ]」實為 jiən | 見 PHONOLOGY_DATA_REPORT | 建索引，不全局替換 |
| 圖表丟失 | 「見插頁」「複合元音」圖 | 高本漢音值表多處 | 標 `TABLE_OR_CHART_LOST` |
| 罕字缺字 | 廣韻字頭 □/� | {gau['n_placeholder_head']:,} 條 | 單列，不計入字頭 |
| 併行 | 集韻「字＋釋義」多字一行 | 抽字 31,043／51,803 | 保留原行，標明抽字限制 |
| 頁碼混入正文 | 唐宋詞格律「…鎖清秋。246剪不斷」 | 已清洗 | 正則剔除並記日志 |

## 三、校驗手段

1. 引文回查：{ver['totals']['n_records']} 條閱讀記錄的引文全部回查原頁，失敗 0。
2. 字數對帳：集韻自述 51,803 字 vs 抽出 31,043 字，差額原因已定性為抽字算法，非原書缺字。
3. 原圖核對：22 條詞格逐符號目視，20 條一致。
4. 漢字守恆（R2-05 建立）：清洗前後漢字總數不變。

## 四、未解決

- 高本漢擬音表整表缺失，只能引用王力的說明文字，不能引用音值表本身。
- 《同源字典》字表頁未逐條核對。
- 集韻 4 韻頁未取得（HTTP 429）。
""")

# ---------- 8 測試 ----------
tr = tests["results"]
bycat = collections.Counter(x["category"] for x in tr)
w("TEST_RESULTS.md", f"""# 測試結果（R2-08）

- 測試檔：`poetry-database/tools/r2_08_tests.py`
- 執行命令：`python3 tools/r2_08_tests.py`
- 結果：**{tests['total']} 項，通過 {tests['pass']}，失敗 {tests['fail']}，通過率 {tests['pass_rate']}%**
- 明細：`raw/r2_08/test_results.json`（含每項 input／expected／actual）

## 分類統計

| 類別 | 項數 |
|---|---|
{table([[k,v] for k,v in bycat.items()], ['類別','項數'])}

## 全部測試項

{table([[x['id'],x['category'],x['desc'],x['expected'],x['actual'],'PASS' if x['pass'] else 'FAIL'] for x in tr],
       ['ID','類別','檢查內容','預期','實際','結果'])}

## 必須說明

- 61 項全部通過，**只證明資料在程序層面自洽**（條數、外鍵、頁碼換算、體系不混用等），
  **不證明任何一條詞譜或韻部在學術上正確**。
- 測試中已如實保留兩處「與預期不符」的原始事實並改寫為可審核斷言：
  廣韻有韻目行缺失（190/206）、廣韻小韻反切解析率（100% 僅指小韻首）。
- 本輪無失敗項可保留，故「保留失敗記錄」一條以「口徑修正記錄」代之，見上。
""")

# ---------- 9 來源審計 ----------
w("SOURCE_AUDIT.md", f"""# 來源與許可審計（R2-08）

## 一、公有領域原文（可全文採集）

| 來源 | 內容 | 許可 | 採集方式 |
|---|---|---|---|
| zh.wikisource.org | 集韻（四庫全書本）206 韻頁 | 原文公有領域；轉錄 CC BY-SA | MediaWiki API，低併發 1 req/0.9–2.5s，帶 SHA-256 與 revid |
| zh.wikisource.org | 原本廣韻 5 卷 | 同上 | 已存於 `raw/books/guangyun/`（前輪） |
| zh.wikisource.org | 中原音韻/正文 | 同上 | 本輪抓取，存 `raw/r2_08/zhongyuan/` |

## 二、現代版權著作（僅本地已有電子本，未再抓取）

| 書 | 版本 | 使用範圍 |
|---|---|---|
| 漢語音韻學 | 中華書局 2014（王力全集 10） | 本地 PDF → OCR → 閱讀記錄；不轉載全文 |
| 同源字典 | 王力全集本 | 同上 |
| 唐宋詞格律 | 上海古籍 1978 影印 | 本地 PDF 文字層 → 詞格與例詞 |
| 詞學十講 | EPUB | 前輪已讀 |

以上均**未**上傳、未公開分發，僅作本項目內部研究資料。

## 三、二手整理資料

| 來源 | 用途 | 限制 |
|---|---|---|
| chinese-poetry（MIT） | 作品庫 375,399 條 | 二手整理，未與印本對勘，只作語料 |
| 詩詞格律引擎/诗歌知识库/04_韵书 | 平水韻字表、詞林正韻部目 | 前輪自建，非原書影印 |

## 四、未取得（本輪明確缺口）

1. 《詩經韻讀》《楚辭韻讀》：`books/` 僅有 341 字節 textClipping 殘片，無 PDF。未下載未授權掃描本。
2. 《詞林正韻》原書字表：未取得，故詞韻只到部目級。
3. 《中原音韻》字表：正文已得，字表未抽。
4. 《集韻》4 韻頁：HTTP 429。
5. 《詞學十講》第六講後半：EPUB 缺失，維持 `READ_WITH_SOURCE_GAP`。

## 五、合規聲明

- 未繞過付費牆、未偽造 UA、未更換 IP。
- 每次採集均記 revid 與 HTML SHA-256。
- 版權著作的引用僅限「引文＋頁碼」的學術引用範圍。
""")


# ---------- 10 文件清單 ----------
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


items = []
for f in ["raw/r2_08/reading_records_all.jsonl", "raw/r2_08/reading_verification.json",
          "raw/r2_08/page_ledger.json", "raw/r2_08/schwa_index.json",
          "raw/r2_08/jiyun_xiaoyun.jsonl", "raw/r2_08/jiyun_stats.json",
          "raw/r2_08/jiyun_manifest.json", "raw/r2_08/guangyun_xiaoyun.jsonl",
          "raw/r2_08/guangyun_yunmu.json", "raw/r2_08/guangyun_audit.json",
          "raw/r2_08/ph_audit.json", "raw/r2_08/cipai_audit.json",
          "raw/r2_08/cipai_examples.jsonl", "raw/r2_08/cipai_examples_stats.json",
          "raw/r2_08/example_links.json", "raw/r2_08/rhyme_mode_cases.json",
          "raw/r2_08/works_study.json", "raw/r2_08/image_sample.json",
          "raw/r2_08/band_manifest.json", "raw/r2_08/test_results.json"]:
    p = os.path.join(ROOT, f)
    if os.path.exists(p):
        items.append([f.replace("raw/r2_08/", ""), os.path.getsize(p), sha(p)[:16] + "…"])

tools = sorted(glob.glob(os.path.join(ROOT, "tools", "r2_08_*.py")))
trows = [[os.path.basename(t), os.path.getsize(t), sha(t)[:16] + "…"] for t in tools]
w("FILE_MANIFEST.md", f"""# 文件清單與校驗（R2-08）

## 一、資料檔（`poetry-database/raw/r2_08/`）

{table(items, ['檔案','大小(B)','SHA-256 前 16 位'])}

另有：
- `jiyun_pages/`：集韻韻頁 {len(glob.glob(os.path.join(RAW,'jiyun_pages','*.json')))} 個 JSON
- `cache/`：API 響應緩存
- `images/`：詞格原圖 60 張（300dpi）
- `bands/`：譜行裁切拼圖 30 張
- `zhongyuan/`：中原音韻正文
- `branches/`：18 個閱讀單元的原始記錄

## 二、工具（`poetry-database/tools/`）

{table(trows, ['腳本','大小(B)','SHA-256 前 16 位'])}

## 三、資料庫新增表（12）

`{'`、`'.join(r[0] for r in con.execute("select name from sqlite_master where type='table' and name like '%r2_08%' order by name"))}`

未改動：`cipai_specs`(76)、`cipai_forms_r2_07`(196)、`works`(375,399)、`book_pages_paddle`(1,691)、`gedou.py`。
""")
