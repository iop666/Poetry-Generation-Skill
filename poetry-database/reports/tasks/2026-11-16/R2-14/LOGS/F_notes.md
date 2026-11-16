# F 组复核笔记（F3 = 30 首精读卡闭环；F4 = 例词 208/310 状态统一）

日期：2026-11-16 ｜ 轮次：R2-14 ｜ 执行：general-purpose-3（独立复核）

## 0. 只读声明

- 只用本地 `sqlite3` 与本地既有 CSV，不联网。
- 数据库一律以 `file:database/poetry.db?mode=ro` 只读打开；**未建表、未写库、未改动任何 works／cipai_* 行**。
- 本轮**不修改 30 首卡片文件**：`CLOSE_READINGS_30_ISSUE_CLOSURE.csv` 的 `fixed_in_card` 全为 `NO`，只给修订动作与证据。
- 所有产出写 `utf-8-sig`。

## 1. F3 口径

### 1.1 60 条遗留问题的重建路径

R2-13 的终审表只给每卡 `n_issues_open`（合计 60：NOT_REVISED 5 卡 15 条 + MAJOR 1 卡 5 条 + MINOR 24 卡 40 条），未给逐条明细。重建来源：

| 来源 | 取用行数 | 覆盖卡片 |
|---|---|---|
| R2-13 `THIRTY_CLOSE_READINGS_5_REVISION.csv` | 15 | C01/C07/C12/C16/C23（NOT_REVISED 五首） |
| R2-12 `THIRTY_CLOSE_READINGS_FINAL_AUDIT.csv` 中 `verdict<>PASS` | 28 | C02/C03/C05/C06/C10/C11/C14/C15/C20/C24/C26/C27/C28/C29/C30 |
| R2-11 `THIRTY_CLOSE_READINGS_INDEPENDENT_AUDIT.csv` 中 `verdict<>PASS` | 17 | C04/C08/C09/C13/C17/C18/C19/C21/C22/C25 |

- 三源合计 60，且**逐卡条数与 R2-13 的 `n_issues_open` 60/60 全对**（生成脚本内有 assert，另打印 `per-card mismatch vs R2-13: []`）。
- 两源重叠的卡（C01/C07/C12/C16/C23）只取 R2-13 的 15 行，不重复计 R2-11 的旧判词，避免 75 条虚数。
- 维度归一：R2-11 的 `原文/背景/韵律/评价` 映射为 `原文完整性/创作背景/韵脚与声调/艺术特点`。

### 1.2 final_status 只用两值

| 值 | 条数 | 含义 |
|---|---|---|
| `FIX_SPECIFIED` | 35 | 论断确有问题，已给出**可直接替换的改法与据以改的复算证据**；卡片尚未动 |
| `UNVERIFIABLE_NO_SOURCE` | 25 | 卡片所据为库外书（集部别集、年谱、方志、史部、诗话、近人论著），库内无从核，动作是「标存疑／删断言」而非「改错」 |

无 `DISMISSED`：逐条复算后**没有一条原判被证伪**（见 §4.1）。

### 1.3 30 首 overall_status

| 值 | 张数 | 卡 |
|---|---|---|
| `MAJOR_ISSUE` | 1 | C28 |
| `NOT_REVISED` | 5 | C01 C07 C12 C16 C23 |
| `MINOR_ISSUE` | 16 | C02 C06 C08 C11 C13 C14 C15 C19 C20 C21 C22 C24 C25 C26 C29 C30 |
| `UNVERIFIABLE` | 8 | C03 C04 C05 C09 C10 C17 C18 C27 |
| `CLEAN` | 0 | — |

- **没有强制 30 个 CLEAN**：本轮不改卡片，`n_fixed` 全 0，凡有遗留项就不可能 CLEAN。
- `UNVERIFIABLE` 的判法：该卡**全部**遗留项都是「库外不可核」，文本逐字与库文一致、论断无硬错（如 C03 只缺《辋川集》目次）。这类卡既不算 CLEAN（主张未获证），也不算 MINOR（无错误可改），单列一档并加注「不并入 CLEAN」。

## 2. F4 口径

### 2.1 208 的构成与去重

- R2-10 20 + R2-11 88 + R2-12 100 = 208。
- 实测两两交集为 0（R2-10 的真对象由首 8 字反查得到，见 §2.2）。
- R2-13 的 `EXAMPLE_LINK_UNSEARCHED_100_RESEARCH.csv` 102 条 = 310 − 208，与 208 交集 0；本轮**逐条独立复核全部 102 条**（要求 ≥50）。
- 最终表 310 行 = 208（沿用并统一）+ 102（R2-13 判 + R2-14 复核）。

### 2.2 ID join 陷阱（详见 `EXAMPLE_LINK_JOIN_ID_AUDIT.md`）

- R2-10 的 `EX-01…EX-20` 是轮内序号；同一文件另有 310 行 `NOT_REVIEWED`，其 `item_id` 才是 `EX-0001…EX-0310`。
- 按 ID 硬 join 实测：20 条中真重合仅 2 条（EX-0011、EX-0015），假重合 18 条；真覆盖 190/208，18 条真对象落空。
- 正确路径：取 R2-10 证据字段内 `例詞「…」` 的 CJK 前 8 字反查 `cipai_form_examples_r2_08.text` → 20/20 唯一命中。
- 与任务书「192 条 + 16 条假重合」不同，已在 MD 中列明差异来源（真重合是 2 条而非 4 条）。

### 2.3 匹配与判定规则（不用 text_norm 当正文）

1. 正文取 `works.text_raw`，去标点后得 CJK 串；`text_norm` **不参与匹配**（只用于对照字数，见 §4.3）。
2. 繁简可比化用 `opencc t2s`，另加**异体折叠表**：沈/沉、欹/敧/攲、裏/裡/里、濛/蒙、著/着、髙/高、逺/遠、峯/峰、㸔/看、䖏/處、恱/悅、旛/幡、嚬/颦、甯/宁、牀/床、悽/凄、喫/吃。折叠只用于定位与判等，**不改库文、不写库**。
3. 探针：首 8 字 → 7/6/5/4 字递缩（仅在首轮无命中时启用），全库 375,399 行 gram 索引。
4. 判定：
   - 差异集合 ⊆ 异体折叠对 或 仅书内夹注（「去声」「读上声」等）→ `VERIFIED_EXACT`，并在证据里注 `CHARACTER_VARIANT(...)` / `EXAMPLE_ANNOTATION_LEAK(...)`；
   - 有 ≥1 处真异文：ratio ≥0.95 → `VERIFIED_VARIANT`；<0.95 → `POSSIBLE_MATCH`；
   - 文本相同而作者不同（按 `《…》所载`、异体姓名归一后比较）→ `AUTHOR_CONFLICT`；
   - 无候选 → `SEARCHED_NO_RESULT`。
5. **未因相似度高直接升级**：所有升级都落到了「逐字相同」或「仅异体」这一可核事实上；ratio 0.99 但有一处真异文者仍判 VARIANT（如 EX-0068 筝/琴、EX-0094 春/暮）。

## 3. 关键 SQL

```sql
-- 作品元数据与正文字数（F3 全 30 首）
SELECT work_id,dynasty,collection,char_count,length(text_raw) FROM works
 WHERE work_id IN ('tang300:c63fe4716683', …);

-- 卡片正文 vs 库文逐字比对（Python+SQL，30/30 全等）
SELECT text_raw FROM works WHERE work_id=?;   -- 再 cj() 去标点后 difflib.SequenceMatcher

-- 字数三口径（C14/C19/C20）
-- cj(text_raw)=62/212/294；去括注=56/176/285；char_count=58/196/290

-- 词谱口径（C24/C25/C26/C29）
SELECT cipai_name,form_seq,total_characters,sentence_count,sentence_lengths,rhyme_positions,rhyme_count
  FROM cipai_forms_r2_07 WHERE cipai_name IN ('雨霖铃','水调歌头','青玉案','西江月','声声慢');
-- 雨霖铃 103/23；水调歌头 95/19（句长 5,5,6,5,6,6…）；青玉案 67/13 韵位 1,3,4,6,7,8,9,10,12,13；
-- 西江月 50/8 韵位 2,3,4,6,7,8；声声慢 97/21 韵位 10

-- 库内可核的书籍（判断「库外不可核」的依据）
SELECT book_id,title FROM books;      -- 13 种：格律/韵书/文心雕龙/原诗/唐宋诗举要，无集部、年谱、方志、史部
SELECT COUNT(*) FROM works WHERE juan<>'';        -- 0
SELECT COUNT(*) FROM works WHERE record_locator<>''; -- 0

-- F4 例词定位（以 EX-0122 为例）
SELECT example_id,text FROM cipai_form_examples_r2_08 WHERE example_id='EX-0122';
SELECT work_id,author_name,title_raw FROM works WHERE text_raw LIKE '%水调数声持酒听%';

-- F4 208 状态与各轮源文件对账
-- r2_11_status vs EXAMPLE_LINK_100_FINAL_AUDIT.final_status；r2_12_status vs ...new_status
-- 结果：9 处"不一致"全为词汇归一（NO_MATCH→SEARCHED_NO_RESULT ×8，UNVERIFIABLE→NOT_SEARCHED ×1）
```

### 1.4 MAJOR 唯一一首：C28《钗头凤・撷芳词》陆游

| 项 | 问题 | 复算证据 |
|---|---|---|
| 题目 | title_notes 半角「?」孤悬、自问自答，属未定稿残留；且把「可怜孤似钗头凤」当作本词首句 | 库文首句＝「紅酥手」；「可怜孤似钗头凤」全篇字频＝0；卡片原文「后以陆游此词首句『可怜孤似钗头凤』? 实以调中…」 |
| 意象 | 「暖色写昔，冷绿写今」不成立 | 下片「淚痕紅浥」（红）、「桃花落」（桃）皆暖色而属今；上片「紅酥手」「黃縢酒」暖色属昔——同一「红」跨昔今 |
| 用典 | 「皆语典，非事典」与本段自述相悖 | 同段已云「锦书用苏蕙织锦回文事」「鲛绡用鲛人泣珠事」，二事皆有事相 |
| 韵脚与声调 | 「三个三字句起」失实 | 句长集合＝[3,4,7]：满城春色宫墙柳＝7 字、泪痕红浥鲛绡透＝7 字 |
| 创作背景 | 《齐东野语》《剑南诗稿》库内无书 | books 13 种无子部、集部 |

判 MAJOR 的理由不是条数多（5 条），而是**题目栏出现了未定稿痕迹与张冠李戴的引证**：题目是读者第一眼看到的部分，其中的错误会把「调名来源」这一常识性说明写成错的，且「?」残留本身即是未完成稿的标记。其余四条为可证伪的文本／体例错误，与 C19「十言」、C25「五字句」同类，属句式归纳不核字数。

## 4. 判断依据与不确定项

### 4.1 逐条复算（F3 无一条被驳回）

复算过的硬事实：C01「低頭思故鄉」确有「故鄉」（詞出场／景不出场须限定）；C08「萬里長征人未還」；C11 首句末字＝郭（入声）；C13 全篇「千」「三」字频＝0（「万」「百」各 1）；C19 句长集合＝[3,5,7]；C20 句长集合＝[4,5,6,7,9] 且「然」居句中；C25「我欲乘风归去／又恐琼楼玉宇」各 6 字；C26 库文有「瑣窗朱戶」「滿城風絮」；C28 首句＝「紅酥手」、句长集合＝[3,4,7]、「可怜孤似钗头凤」字频 0；C29 库文有「白雲多」；C21/C29 朝代冲突来自 collection。

**唯一被降级**的是 C22「意象」：卡片「『春水』是唯一有动能的暖流」中「暖」是比喻而非色语断言，「与冷白为主互斥」之名过重。仍列 `FIX_SPECIFIED`，但动作改为「删『暖』，就方向与动能立说」，并在证据中写明这是术语不严而非文本矛盾。

### 4.2 不确定／须注口径的三处

1. **C19「十言」**：库文作「君不見，黃河之水天上來」，有逗断开；按断句无 10 字句，若视「君不见」为三字领则整句 10 字。两种读法都要求卡片交代，故原判成立，但属**口径之争**而非纯错。
2. **C02「一横一纵」**：方向可核（日西沉、水东流，同为东西轴），但「横／纵」本身是解诗用语，改法系修辞层面。
3. **C04 判 UNVERIFIABLE**：其四项（系年、贬所、与《渔翁》同期、绘画接受史）皆库外，但若日后补入年谱，应回落为 MINOR。

### 4.3 发现的上游缺陷（不影响本轮结论，但须登记）

- **R2-13 证据字段指认错误**：C16 的 `TEXT_CONFLICT` 在 `works.crosscheck_status`（值 `CROSS_SOURCE_COMPARED:TEXT_CONFLICT`），不在 `verify_status`（该列＝`VARIANT_PENDING`）。终审表 note 写成 `verify_status=TEXT_CONFLICT`，已在 C16 的 note 中更正。
- **R2-13 208 表的 9 处"状态不一致"** 全是词汇归一（`NO_MATCH`→`SEARCHED_NO_RESULT`、`UNVERIFIABLE`→`NOT_SEARCHED`），非判词冲突；其中 EX-0012 的折算属误判（见下）。
- **例词字段串行**（书页/段落串页）：EX-0012（混入词谱说明）、EX-0076（秦观《行香子》+ 例三李清照 + 数字垃圾）、EX-0088（标贺铸、正文为苏轼《水调歌头》）、EX-0096（张炎《八声甘州》+《扬州慢》词谱说明 + 姜夔《扬州慢》全篇，372 字）、EX-0249（407 字含「198」页眉）、EX-0308（标柳永、正文为苏轼《定风波》并附署名）、EX-0146（正文夹「原作…」校记）。这些行的状态只对**首篇／所标篇**成立，已在 evidence 内逐条注明；除 EX-0012 外未改判，因为无法在不拆书页的前提下给出单篇定论。
- **EX-0012 改判**：`NOT_SEARCHED` → `VERIFIED_EXACT`。其「例一」28 字「日照澄洲江雾开…尽是沙中浪底来」与 `tang:4ff2660613c2`《雜曲歌辭 浪淘沙 六》逐字全同（28/28），原判是把词谱说明全文（127 字）当例词比对所致。

### 4.4 F4 改判 9 项（含 1 项维持）

| 例词 | R2-13 | 本轮 | 依据 |
|---|---|---|---|
| EX-0046 | AUTHOR_CONFLICT | AUTHOR_CONFLICT（维持） | 文本 48/48 全同，但库作「无名氏」而例词标王雱 → 作者冲突成立；一度误升 EXACT，已按作者核对回退 |
| EX-0080 | VARIANT | EXACT | 仅 彩/采、苍/沧 二处通假 |
| EX-0105 | VARIANT | EXACT | 库文与例词 raw_equal=True（107/107），原判误降 |
| EX-0162 | VARIANT | EXACT | raw_equal=True（58/58） |
| EX-0171 | VARIANT | EXACT | raw_equal=True（62/62） |
| EX-0174 | VARIANT | EXACT | 仅 沉/沈（异体）+ 乾/干（繁简） |
| EX-0183 | VARIANT | EXACT | 仅两处「去声」夹注 + 它/他 |
| EX-0192 | VARIANT | EXACT | 仅 攲/敧 |
| EX-0195 | VARIANT | EXACT | 仅 颦/嚬、蚤/早 |

## 5. 文件清单（本轮 F 组）

| 文件 | 行数 | 说明 |
|---|---|---|
| `CLOSE_READINGS_30_ISSUE_CLOSURE.csv` | 60 | 60 条遗留问题逐条闭环（动作＋复算证据＋fixed_in_card=NO） |
| `CLOSE_READINGS_30_FINAL_AUDIT.csv` | 30 | 终审；MAJOR 1／NOT_REVISED 5／MINOR 16／UNVERIFIABLE 8／CLEAN 0 |
| `EXAMPLE_LINK_208_STATUS_FINAL.csv` | 310 | 208 统一 + 102 新增复核（含 EX-0012 改判） |
| `EXAMPLE_LINK_SEARCH_HISTORY.csv` | 304 | R2-12 100 + R2-13 102（原样保留）+ R2-14 102 |
| `EXAMPLE_LINK_JOIN_ID_AUDIT.md` | — | R2-10 序号 vs example_id 的陷阱与首 8 字反查映射表（20/20） |
| `LOGS/F3_build.py` / `F3_final.py` / `F4_search.py` / `F4_search2.py` / `F4_build.py` / `F4_join_audit.py` | — | 可复现脚本 |
| `LOGS/f3_closure.json` / `f4_search_raw.json` / `f4_search_retry.json` / `f4_new_rows.json` / `f4_r10_map.json` | — | 中间结果 |

## 6. 复现

```bash
cd poetry-database
python3 reports/tasks/2026-11-16/R2-14/LOGS/F3_build.py        # 60 条闭表
python3 reports/tasks/2026-11-16/R2-14/LOGS/F3_final.py        # 30 首终审
python3 reports/tasks/2026-11-16/R2-14/LOGS/F4_search.py       # 102 条首轮检索（全库 gram 索引，约 100s）
python3 reports/tasks/2026-11-16/R2-14/LOGS/F4_search2.py      # 40 条递缩探针重搜
python3 reports/tasks/2026-11-16/R2-14/LOGS/F4_build.py        # 310 行状态表 + 检索历史
python3 reports/tasks/2026-11-16/R2-14/LOGS/F4_join_audit.py   # join 审计 MD
```
