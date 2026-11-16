# R2-13 独立复核记录（general-purpose-3）

工作目录：`<PROJECT_ROOT>/poetry-database`
数据库：`database/poetry.db`（只读，未作任何写入；全部脚本仅执行 SELECT）
产出目录：`reports/tasks/2026-11-16/R2-13/`
全部 CSV：utf-8-sig。

---

## 一、G1 例词关联对账

### 1.1 表结构（用于确认字段语义）

```sql
.schema works
.schema cipai_form_examples_r2_08
.schema example_work_links_r2_09
```

关键字段：`works(work_id,title_raw,title_norm,author_name,author_canonical,dynasty,collection,
genre,cipai,text_raw,text_norm,char_count,volume,seq,record_locator,juan,base_edition,
crosscheck_status)`；`cipai_form_examples_r2_08(example_id,form_id,cipai_name,author,text,n_chars,...)`；
`example_work_links_r2_09(example_id,...,old_match_kind,new_match_kind,same_author,containment,ex_len,work_len,score,round)`。

### 1.2 总量与状态

```sql
SELECT COUNT(*) FROM works;                                  -- 375399
SELECT SUM(LENGTH(text_norm)) FROM works;                    -- 21387419（≈21.4M 汉字）
SELECT COUNT(*) FROM cipai_form_examples_r2_08;              -- 310
SELECT COUNT(*) FROM example_work_links_r2_09;               -- 310
SELECT COUNT(DISTINCT example_id) FROM example_work_links_r2_09;  -- 310
SELECT COUNT(DISTINCT form_id) FROM example_work_links_r2_09;     -- 168
SELECT new_match_kind,COUNT(*) FROM example_work_links_r2_09 GROUP BY 1;
-- VERIFIED_VARIANT 116 / NO_MATCH 114 / VERIFIED_EXACT 50 / POSSIBLE_MATCH 19 /
-- AUTHOR_CONFLICT 6 / TITLE_ONLY 5   （合计 310）
```

### 1.3 去重口径（本轮最关键的一处纠正）

**不能按 `item_id` / `link_id` / `example_id` 字串直接合并三批。**

R2-10 的 `EXAMPLE_100_INDEPENDENT_REVIEW.csv` 中 20 条真复核，其 `item_id` 是 `EX-01…EX-20`，
是**该轮的轮内序号，不是 example_id**。若把它补零成 `EX-0001…EX-0020` 后与 R2-11/R2-12 join：

```text
20+88+100=208 条原始记录，按 ID 串去重 → 192 条唯一，出现 16 条"重复"
实际这 16 条是假重合（EX-01 是张先《天仙子》，而 EX-0001 是蔡伸《十六字令》）
```

**采用的口径**：以 `cipai_form_examples_r2_08.example_id` 为唯一键，R2-10 的 20 条改用
"例词首 8 字（去标点）在全表 310 条例词中做子串匹配"反查真实 example_id。
匹配脚本内断言 `len(hits)==1`，20 条全部唯一命中：

| R2-10 序号 | 反查得 example_id | 词牌 / 作者 |
|---|---|---|
| EX-01 | EX-0122 | 天仙子 / 张先 |
| EX-02 | EX-0015 | 浪淘沙 / 李煜 |
| EX-03 | EX-0157 | 木兰花 / 吴文英（作品实为《木兰花慢》） |
| EX-04 | EX-0274 | 菩萨蛮 / 温庭筠 |
| EX-05 | EX-0271 | 昭君怨 / 万俟咏 |
| EX-06 | EX-0255 | 兰陵王 / 刘辰翁 |
| EX-07 | EX-0242 | 拜星月慢 / 周邦彦 |
| EX-08 | EX-0294 | 渡江云 / 张炎 |
| EX-09 | EX-0234 | 宴清都 / 吴文英 |
| EX-10 | EX-0038 | 采桑子 / 李清照 |
| EX-11 | EX-0115 | 六州歌头 / 贺铸 |
| EX-12 | EX-0301 | 诉衷情 / 温庭筠 |
| EX-13 | EX-0096 | 八声甘州 / 姜夔（作品张炎） |
| EX-14 | EX-0088 | 水调歌头 / 贺铸（作品苏轼） |
| EX-15 | EX-0220 | 绛都春 / 朱淑真 |
| EX-16 | EX-0044 | 朝中措 / 欧阳修 |
| EX-17 | EX-0307 | 定风波 / 欧阳炯 |
| EX-18 | EX-0011 | 捣练子 / 贺铸 |
| EX-19 | EX-0076 | 行香子 / 李清照 |
| EX-20 | EX-0186 | 御街行 / 范仲淹 |

结论：**208 条原始记录 = 208 个真实唯一对象（去重后仍为 208）**；
而"192"是按 ID 串误 join 的产物，属假阴性/假阳性各 16 条，应废弃。

三批之间真实零重叠（R2-11 的 88 条与 R2-12 的 100 条、R2-10 的 20 条互不相交）。

### 1.4 `EXAMPLE_LINK_208_RECONCILIATION.csv`

208 行，`final_status` 只取七个允许值。折算规则（写入 `note`）：

- `NO_MATCH` → `SEARCHED_NO_RESULT`（语义等价：已检索、无结果）
- `UNVERIFIABLE` → `NOT_SEARCHED`（未取得可判定结果）
- 其余原样。

`final_status` 取"最晚一轮"的结论（R2-12 > R2-11 > R2-10）；因三批不重叠，实际无冲突。

**分布**：

| final_status | 条数 |
|---|---|
| VERIFIED_VARIANT | 99 |
| SEARCHED_NO_RESULT | 50 |
| VERIFIED_EXACT | 25 |
| POSSIBLE_MATCH | 22 |
| AUTHOR_CONFLICT | 11 |
| NOT_SEARCHED | 1（EX-0012，R2-11 判 UNVERIFIABLE） |

分轮：R2-10 20 条 / R2-11 88 条 / R2-12 100 条，合计覆盖 208 条。

R2-10 三条被推翻的原判已记入本表：

- EX-0096（原 TITLE_ONLY）→ AUTHOR_CONFLICT：例词正文完整含张炎《八声甘州》97 字，作品为例词子串。
- EX-0088（原 TITLE_ONLY）→ AUTHOR_CONFLICT：例词正文含苏轼《水调歌头》全篇，作者栏作贺铸。
- EX-0011（原 NO_MATCH）→ VERIFIED_VARIANT：复核检得 `songci:d9f5da07be28`《望书归・捣练子》贺铸，
  27 字对 32 字，异文 2 字（征人/征衣、唯/惟）。本轮已单独复查该作品存在：

```sql
SELECT work_id,title_raw,author_name,text_raw FROM works WHERE work_id='songci:d9f5da07be28';
-- 望书归・捣练子 | 贺铸 | 边堠远，置邮稀。附与征衣衬铁衣。连夜不妨频梦见，过年惟望得书归。
```

### 1.5 未复核 102 条：筛选口径

```text
done  = R2-10(20，内容反查) ∪ R2-11(88) ∪ R2-12(100)      → 208
remain= 310 − 208                                          → 102
```

状态分布（`new_match_kind`）：`VERIFIED_VARIANT 61 / VERIFIED_EXACT 41`。
**注意：这 102 条里没有一条原状态是 NO_MATCH**——310 条中的 114 条 NO_MATCH 已全部被前三轮覆盖
（R2-12 90 条、R2-11 20 条、R2-10 4 条）。所以本轮的 102 条不是"补漏升级"，
而是**对已判为"已核实"的阳性结论做独立重验**，性质不同，下文结论按此读。

### 1.6 检索方法（逐条真检索，非近似）

1. 一次性载入 375,399 条 `works`，对 `text_norm` 做 OpenCC `t2s` 转简体，
   以 `\u0001` 拼接为单一字符串，并维护 `starts[]` 前缀偏移数组。
2. 以 `bisect` 把命中位置映射回 `work_id`。
3. 探针：例词正文（去标点、去括注）每 5 字取 1 个 6 字窗，最多 8 个窗；
   逐个窗在语料串中做子串查找，按命中票数排序取前 40 个候选，外加"原登记作品"。
4. 对候选做归一化（去标点、t2s）后算 Levenshtein 距离，`ratio = 1 − lev / max(len)`。
5. 异文清单用 `difflib.SequenceMatcher.get_opcodes()` 生成 `replace[x>y] / delete[x] / insert[x]`。

单条耗时约 0.6 s，102 条合计 60 s（含 21M 字载入与转换）。

**几个必须交代的方法学修正**：

- **例词正文夹括注**：310 条例词中有 21 条正文内含平仄/去声标注，如
  `EX-0139`「两行（去声）小槽双凤」、`EX-0183`「庾（去声）楼月」。不剔除会把"（去声）"算成 3 处异文。
  本轮比对前统一 `re.sub(r'[（(][^（）()]*[）)]','',s)`。**前三轮未见此处理说明，其相似度可能因此偏低。**
- **首句异文导致精确前缀检索落空**：3 条（EX-0154 画楼/画桥、EX-0167 伫立/伫倚、EX-0174 燎沉香/燎沈香）
  用"首句 6 字精确包含"检索时 `work_len=0`。这正是 `NOT_SEARCHED` 与 `SEARCHED_NO_RESULT` 必须区分的场合：
  它们**不是**没搜到，而是探针本身带异文；改用多探针后各命中 1 条，ratio 0.98 +。
  本表 `evidence` 列已逐条注明。
- **繁简层不计异文，但异体字计入**。故 `濛/蒙`（EX-0162）、`軿` 脱字（EX-0171）会使原判 VERIFIED_EXACT 降为 VERIFIED_VARIANT。
  这是判定口径差异而非新发现的错，已在 `evidence` 写清异文原字。

### 1.7 `EXAMPLE_LINK_UNSEARCHED_100_RESEARCH.csv`

102 行（≥100 的要求已满足）。

| new_status | 条数 |
|---|---|
| VERIFIED_EXACT | 53 |
| VERIFIED_VARIANT | 48 |
| AUTHOR_CONFLICT | 1 |

| verdict | 条数 |
|---|---|
| CONFIRMED_PRIOR（与原名目同类，含口径内的等价判定） | 84 |
| UPGRADED_TO_EXACT（原 VARIANT，本轮逐字全同） | 15 |
| DOWNGRADED（原 EXACT，实有异体/脱字） | 2（EX-0162、EX-0171） |
| CORRECTED_AUTHOR_CONFLICT | 1（EX-0046） |

`best_ratio` 分布：≥0.9999 者 54 条；0.95–0.9999 者 45 条；0.85–0.95 者 3 条；最低 0.942（EX-0077）。

**唯一一条作者冲突**：`EX-0046` 眼儿媚「杨柳丝丝弄轻柔」，例词栏作者**王雱**，
作品 `songci:f455929e65c4` 作者**无名氏**，文本 48/48 字全同（lev=0）。原判 VERIFIED_EXACT 只比了文本未比作者，
按本轮门槛（逐处异文 + 作者规范化后一致 + 同词牌）三条不同时成立，改判 AUTHOR_CONFLICT。
该词归属本有异说，不宜在库内径定作者。

**`work_len=0` 的条数：0**（102 条全部有候选）。故本轮不存在 `NOT_SEARCHED`；
若按"首句精确前缀"口径则会误报 3 条，已在 1.6 说明。

---

## 二、G2 30 首精读卡闭环

### 2.1 定位 5 首 NOT_REVISED 的 work_id（SQL 与命中）

```sql
SELECT work_id,title_raw,author_name,dynasty,collection,char_count FROM works
 WHERE title_raw='靜夜思' AND author_name='李白';
-- tang300:c63fe4716683 靜夜思 李白 唐 tang300 20
-- tang:0573f42e54cb   靜夜思 李白 唐 tang   20   ← 库内重复本（宋本读法）

SELECT ... WHERE title_raw='題西林壁' AND author_name='蘇軾';
-- songshi:afc90d0ab2ec 題西林壁 蘇軾 宋 songshi 28

SELECT ... WHERE title_raw='題破山寺後禪院' AND author_name='常建';
-- tang300:bc187a889708 ... 40
-- tang:8cceeac1c254    ... 40   ← 库内重复本（竹逕/都寂/但餘）

SELECT ... WHERE title_raw='西塞山懷古' AND author_name='劉禹錫';
-- tang300:b06307c0c39a ... 56
-- tang:8750c12cc976    ... 56   ← 库内重复本（西晉/沈/旛/江流）

SELECT ... WHERE title_raw='声声慢' AND author_name='李清照';
-- songci:76d37f87f2f4 声声慢 李清照 宋 songci 97
```

5 首 work_id：C01 `tang300:c63fe4716683`、C07 `songshi:afc90d0ab2ec`、C12 `tang300:bc187a889708`、
C16 `tang300:b06307c0c39a`、C23 `songci:76d37f87f2f4`。全部唯一（C01/C12/C16 另有 tang 重复本，卡片均取 tang300 本）。

### 2.2 `THIRTY_CLOSE_READINGS_5_REVISION.csv`

15 行（= R2-12 对这 5 张卡开列的 15 条问题，逐条一行，不是逐卡一行）。
`revised` 全为 `NO`，`status` 全为 `NOT_REVISED`：**30 张卡片文件自 R2-10 生成后未再改动过一字**
核对：`reports/tasks/2026-11-15/R2-10/THIRTY_CLOSE_READINGS.csv` 与
`raw/r2_10/examples/THIRTY_CLOSE_READINGS.csv` 的 SHA-1 同为 `0d479c4cee3bd248f79c6e35eba229e389131f4c`，
mtime 同为 2026-11-15 21:28，即 R2-11/R2-12 只写了审计表，卡片本身未动。
每条 `required_fix` 给的是可直接替换的成句文字，不是"应补充某某"式的待办。

### 2.3 原文比对怎么做的（真实执行，含三处发现）

对每张卡：`text_full` 与 `works.text_raw` 均去标点后逐字比较，并另算"去括注"版本。

```text
30/30：去标点后与 works.text_raw 逐字全同（0 字异）。
```

但三张卡的正文列把 `text_raw` 里的校记括注原样抄了进去，导致与 `text_norm`/`char_count` 不合：

| 卡 | text_raw | text_norm | 去全部括注=正文 | works.char_count | text_norm 究竟删了什么 |
|---|---|---|---|---|---|
| C14 蜀相 | 62 | 58 | 56 | 58 | 仅删「一作頻繁」4 字 |
| C19 將進酒 | 212 | 196 | 176 | 196 | 仅删「一作側耳」「一作何足」「一作不願」「一作自古」共 16 字 |
| C20 夢遊天姥 | 294 | 290 | 285 | 290 | 仅删「萬一作一」4 字 |

即 `text_norm` 并非"纯正文"，而是"删掉异文、留下出校词"，故 `char_count` 也随之虚增。
C14 卡片 note 说"差额 2 系校记处理口径"，R2-12 已算出"校记实 6 字，若全计应为 62，差 4 非 2"；
本轮把三本字数一次列清，可确认 R2-12 的反驳成立，且差额来源是 `text_norm` 的删法（不是"口径不一致"）。

### 2.4 `THIRTY_CLOSE_READINGS_FINAL_R2_13.csv`（30 行）

- `text_match_with_text_raw`：30/30 `MATCH(0字異)`。
- `n_issues_open` 合计 **60**；`n_issues_fixed` 合计 **0**（30 张卡无一修订）。
- `overall_status`：`NOT_REVISED 5 / MAJOR_ISSUE 1（C28，5 条）/ MINOR_ISSUE 24 / CLEAN 0 / UNVERIFIABLE 0`。
- 判定阈值（自定，已写入本文件）：5 张 R2-12 明确复核为 NOT_REVISED 的卡单独标 `NOT_REVISED`；
  其余按未闭问题数：ISSUE 级 ≥3 → MAJOR，1–2 或仅 UNVERIFIABLE → MINOR，0 → CLEAN。

**一条跨组交叉证**：G1 的 102 条重搜里，`EX-0204` 是词谱所录《声声慢》同篇（李清照，97 字，ratio 0.9794），
其文本作「有誰**堪**摘」，异文仅 堪/忺、着/著。这独立印证了 C23 的「忺/堪」异文确实存在，
且库文「忺」属孤读——卡片的 note 只记「忺」而不提「堪」与源2，仍是不全。已写入该条的 `evidence`。

**为什么没有 CLEAN**：30 张卡每张至少有一条"背景/创作背景"维度落在 UNVERIFIABLE
（库内无年谱、无地志、无集部原书）。这是**结构性的**：`works` 只有文本与 `collection/dynasty/genre`，
`record_locator/juan/base_edition/crosscheck_result` 在这 30 条上全部为 NULL，
任何系年、本事、寺址、台址都无从核起。故"UNVERIFIABLE"不等于卡片有错，见 2.5 的分级说明。

**朝代字段两处不合**（`dynasty_from_db` vs `dynasty_in_card`）：

- C21 菩萨蛮（温庭筠）：库作「五代」，卡片作「唐」。库按 `collection=huajianji` 赋朝代，与作者实际时代错位；
  应改库，不是改卡。
- C29 西江月（欧阳炯）：库作「唐」，卡片作「五代」。同上，库侧错。
  卡片在 C21 判"与库冲突"（R2-11 C21 背景 ISSUE 即指此），本轮认为**冲突责任在库**：
  温庭筠卒于唐末、欧阳炯仕后蜀，卡片所标才对。建议记入 `KNOWN_DATA_DEFECTS`，勿据库字段改卡。

### 2.5 不确定项（G2）

1. 5 张卡的"创作背景"类问题（C07/C12/C16/C23 各 1 条）判 UNVERIFIABLE，本轮的 `required_fix` 只能给
   "降级为存疑"的改写措辞，无法给"正确系年"——因为库内确实没有可据之书。这一条不算解决，只算止损。
2. C23 韵脚"句数"一条：R2-12 说库谱 21 句、钦定 10+8；本轮未重数库谱句长（`cipai_forms_r2_07` 在另一表，
   与本卡口径的对应关系需先确认），只沿用 R2-12 计数并把它写成"须标明口径"的建议。属未独立复核项。

---

## 三、G3 10 首版本对勘定位修复

### 3.1 库内定位字段的实际情况（先查再说）

```sql
SELECT work_id,volume,seq,collection,record_locator,juan,base_edition,crosscheck_result
  FROM works WHERE work_id IN (10 个 work_id);
```

结果：**`record_locator` / `juan` / `base_edition` / `crosscheck_result` 10/10 全为 NULL**；
`volume` 仅 `tao:77027e30b095` 有值「卷三」；其余 volume 为空串。

```sql
SELECT work_id,title,source_a,source_b,result,status FROM text_crosscheck
 WHERE work_id IN (10 个 work_id);
```

仅 3 条有记录（no.2 早發白帝城、no.4 題破山寺、no.5 西塞山），且 `source_b` 一律是
`zh.wikisource:唐詩三百首`——**不是**对勘表所用的四庫本。即：R2-10 引入的"第二版本（四庫本）"
在库内没有任何登记，`source2_revid` 也无本地留档（`raw/` 下无四庫本页面缓存）。这是本轮必须说明的
**可追溯性缺口**：revid 只能作为外部标识引用，库内无法自证。

### 3.2 能补的定位（不是编的，逐条有出处）

1. **锚点**：`raw/books/t300_ws/*.wikitext` 里存有指向全唐詩卷页的跨页链接，且带条目锚点：

```text
靜夜思.wikitext        notes = … ↑[[全唐詩/卷165#靜夜思|全唐詩·卷165]] ↑[[李太白文集_(四庫全書本)/卷05#静夜思|…]]
山居秋暝.wikitext      [[全唐詩/卷126#山居秋暝]]
題破山寺後禪院.wikitext [[全唐詩/卷144#題破山寺後禪院]]
下江陵.wikitext         ↑[[全唐詩/卷181#早發白帝城|全唐詩·卷181]]（并注「《唐詩三百首》中詩題作『下江陵』」）
西塞山懷古.wikitext     from = 劉賓客文集 (四庫全書本)/卷24 … from3 = 全唐詩/卷359（无锚点）
```

这 5 条把"卷 + 条目名"由单源变成**库内本地文件可核**，并可补一条第三版本定位（no.5 劉賓客文集卷24）。

2. **库内同源复本可复现源2 读法**（这条最有价值）：库内 `collection=tang` 的重复本保留的是全唐詩系统读法，
   与对勘所称四库本读法一致，等于给了第二个独立见证：

```sql
SELECT work_id,text_raw FROM works WHERE work_id IN
 ('tang:0573f42e54cb','tang:8adb6c013532','tang:8ec5444ad3db','tang:8cceeac1c254','tang:8750c12cc976','tang:608ae8c92705');
```

| 作品 | 库内 tang 复本读法 | 对应对勘条目 |
|---|---|---|
| tang:0573f42e54cb | 牀前看月光…舉頭望山月 | no.1（宋本系统，卡片 title_notes 已提及） |
| tang:8adb6c013532 | 兩岸猨聲啼不盡 | no.2 |
| tang:8ec5444ad3db | 明月**松**間照 | no.3（证 tang300 本「鬆」为繁化误字，非版本异文） |
| tang:8cceeac1c254 | 竹逕通幽處…萬籟此都寂，但餘鐘磬音 | no.4 |
| tang:8750c12cc976 | 西晉樓船…沈江底…降旛…枕江流 | no.5 |
| tang:608ae8c92705 | 雕闌玉砌應猶在…恰似一江春水，向東流（作者栏「後主煜」） | no.8 |

3. **no.7 饮酒**：`works.volume='卷三'` + `sources/tao_index.json` 中〈飲酒二十首〉一项作 `["三","飲酒二十首"]`，
   双重佐证卷次；`raw/books/tao/飲酒二十首.wikitext` 以 `===其五===` 分首，可核"其五"之序。
   但该文件 `from=陶淵明集`，**与 source2 的「箋註陶淵明集（四部叢刊本）」不是同一版本**，只可核卷次结构，不可作同版对勘。

4. **no.6 题西林壁**：库内无东坡全集转录本、无同源复本，卷13 与"紧接〈贈東林總長老〉之后"仅见于 R2-10 记录，
   属**单一来源**定位。仍判 JUAN_ONLY（卷+卷内相邻序位足以定位），但 `evidence` 已明写"无本地二次佐证"。

### 3.3 定位等级与结果

| 等级 | 条数 | 条目 |
|---|---|---|
| JUAN_PAGE | 0 | — |
| JUAN_ONLY | 8 | no.1–8 |
| ITEM_ORDER | 2 | no.9 漱玉詞、no.10 東坡詞 |
| NONE | 0 | — |

`can_locate`：`YES 8 / PARTIAL 2 / NO 0`。**已超过"至少 5 首可定位"的目标。**

### 3.4 为什么 no.9 / no.10 升不上去（缺什么，写清楚）

- 二者 `source2_name` 是**整部词集**（漱玉詞、東坡詞），`source2_locator` 只给到"第 2 闋 / 某词题"，
  **没有卷次**。词集是否分卷，库内无记载（`raw/` 无此二书转录本，`works` 无对应记录）。
- 缺的是：《四庫全書總目》词曲类该二书的著录条（若著录"一卷"，可补卷1而升 JUAN_ONLY）。
  本轮无此书，**不作推定**——虽则宋人词集多为一卷本，但"多为一卷"不能替代"确实一卷"。
- 即便补到卷，仍不能到 JUAN_PAGE：JUAN_PAGE 需四库扫描的叶次（如"卷165第12叶"），
  库内无任何影印叶码（`raw/r2_12/facsimile/` 只有广韵 3 叶），10 首全部止于卷级，这是硬约束。

---

## 四、跨组计数一览

| 项 | 数 |
|---|---|
| 例词总数（`cipai_form_examples_r2_08`） | 310 |
| 前三轮已复核（去重后） | 208（= 20 + 88 + 100，真实零重叠） |
| 本轮重搜 | 102 |
| 全程覆盖 | 310 / 310 |
| 208 表 final_status：VARIANT / NO_RESULT / EXACT / POSSIBLE / AUTHOR_CONFLICT / NOT_SEARCHED | 99 / 50 / 25 / 22 / 11 / 1 |
| 102 重搜：EXACT / VARIANT / AUTHOR_CONFLICT | 53 / 48 / 1 |
| 102 重搜 verdict：CONFIRMED / UPGRADED / DOWNGRADED / CORRECTED_AUTHOR | 84 / 15 / 2 / 1 |
| 30 卡未闭问题 | 60（每卡 1–5 条） |
| 30 卡已修订 | 0 |
| 10 首定位：JUAN_ONLY / ITEM_ORDER / JUAN_PAGE / NONE | 8 / 2 / 0 / 0 |

---

## 五、不确定项与需下游决定的事项

1. **R2-10 的 item_id 是轮内序号**。R2-11/R2-12 的说明文件若仍按 `EX-01..EX-20` 与 `EX-0001..` 对等引用，
   会持续产生 16 条假重合。建议在 `KNOWN_DATA_DEFECTS` 记一条，并以下表（1.3）为正式映射。
2. **`text_norm` 不是纯正文**：它删异文而留出校词，导致 `char_count` 虚增（C14/C19/C20 已量化）。
   这是库级缺陷，影响一切以 `char_count` 为准的校验（含词谱字数比对），非本卡之误。
3. **C21/C29 朝代冲突责任在库**（collection 赋朝代法），不宜据库改卡。
4. **`source2_revid` 无本地留档**：10/10 的四库本 revid 在库内无对应缓存，`raw/` 亦无。
   revid 只能作外部引用。若下游要求"库内自证版本"，现有材料不够，需一次补抓（本轮不联网）。
5. **102 条重搜的判定口径**：异体字（濛/蒙、沈/沉、旛/幡）计为异文，故两条原 EXACT 降为 VARIANT。
   若下游采用"异体等同"口径，应把 EX-0162、EX-0171 改回 EXACT，并在表内调 `verdict`。
6. **C23 库谱句数（21 句 vs 10+8）未独立重数**，沿用 R2-12。
7. 本轮所有相似度均为**全篇 Levenshtein**（长度差异计入），与前三轮"最长公共子串覆盖"口径不同，
   故同一对文本的数值不可直接跨轮比较（结论可比较，数值不可比较）。

---

## 六、本轮未做（防越界）

- 未修改数据库（全部只读 SELECT）。
- 未联网：未重新抓取维基文库页面，故未新增/核对任何 revid；引用的 revid 均为 R2-10 既有记录。
- 未用记忆中的"通行本原文"替代库内文本；所有比对基准为 `works.text_raw` / `text_norm`。
- 未据相似度直接升级状态：每条升级都同时给出异文清单 + 作者规范化比对 + 词牌比对三项。
