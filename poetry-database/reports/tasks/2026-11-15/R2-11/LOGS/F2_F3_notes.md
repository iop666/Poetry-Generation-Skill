# R2-11 / F2+F3 独立复核记录（例词关联 88 条 + 上古音 40 例来源链）

**执行**：独立复核者（general-purpose-2），本地 sqlite3 + 文件，未联网
**日期**：2026-11-15
**产出**
- `EXAMPLE_LINK_100_FINAL_AUDIT.csv`（88 行，任务 A；未链接者 `work_title` 显示检索到的候选，便于复查）
- `ANCIENT_RHYME_40_SOURCE_REVIEW.csv`（40 行，任务 B）
- `LOGS/f2_detail.json`（任务 A 逐条中间量，含分段、编辑距离、候选命中）
- 脚本：`tools/r2_11_example_recheck.py`、`tools/r2_11_example_csv.py`、`tools/r2_11_ancient_review.py`

**立场**：不假定 R2-09/R2-10 结论正确。凡本机查不到、或输入文件没给出的出处，一律记 `UNVERIFIABLE`／`MISSING_CITATION`，不补造书名页码。

---

# 第一部分 例词—作品关联（任务 A）

## A1. 母体与「历史累计」口径（先算清再抽样）

`example_work_links_r2_09` 与 `cipai_form_examples_r2_08` 均为 310 条，`example_id` 一对一。

R2-10 的 `EXAMPLE_100_INDEPENDENT_REVIEW.csv` **不是 100 条**：

| 项 | 数 | 说明 |
|---|---:|---|
| 文件总行 | 330 | |
| `review_type=INDEPENDENT_AGENT` | **20** | 真复核（EX-01…EX-20），17 AGREE / 3 DISAGREE |
| `review_type=NOT_REVIEWED` | 310 | 占位行，`agreement=UNDECIDABLE`，未复核 |

**口径校正**：R2-10 实际独立复核例词关联 = **20 条**（与 `INDEPENDENT_REVIEW_R2_10.md` 表「例詞關聯 310 / 20 / 17 AGREE / 3 DISAGREE / 85.0%」一致），不是 100 条。

这 20 行的 `item_id`（EX-01…EX-20）与库内 `example_id`（EX-0001…EX-0310）不同名，**不能按序号对齐**。本轮的映射办法：取每行 `evidence` 里「例詞「…」」的正文前 7 个汉字，去标点、繁转简后，与库内 310 条例词正文做子串匹配——20 行各**唯一命中 1 条**，无重复、无多解：

```
EX-01→EX-0122  EX-02→EX-0015  EX-03→EX-0157  EX-04→EX-0274  EX-05→EX-0271
EX-06→EX-0255  EX-07→EX-0242  EX-08→EX-0294  EX-09→EX-0234  EX-10→EX-0038
EX-11→EX-0115  EX-12→EX-0301  EX-13→EX-0096  EX-14→EX-0088  EX-15→EX-0220
EX-16→EX-0044  EX-17→EX-0307  EX-18→EX-0011  EX-19→EX-0076  EX-20→EX-0186
```

**累计 = 20（R2-10）+ 88（本轮）= 108 条**，达标（≥100）。本轮 88 条与上述 20 条**零交集**，脚本内有 `assert` 强制。

> 旁注：`INDEPENDENT_REVIEW_120.csv` 共 140 行，但类别为集韵小韵／广韵反切／阅读／词谱符号，不含例词关联，故不计入本口径。

## A2. 抽样方法（先抽样，后比对，避免按结果挑样）

分层系统抽样，层=`new_match_kind`，层内按 `example_id` 升序、固定步长取第 `floor(i*step)` 条。抽样在计算任何相似度**之前**完成，脚本 `sample_ids()` 与比对逻辑分离。

| 层 | 母体（扣除已复核 20 条后） | 抽样 | 步长 |
|---|---:|---:|---:|
| AUTHOR_CONFLICT | 4 | 4（全取） | 1.0 |
| TITLE_ONLY | 3 | 3（全取） | 1.0 |
| POSSIBLE_MATCH | 16 | 16（全取） | 1.0 |
| VERIFIED_VARIANT | 111 | 40 | 2.775 |
| NO_MATCH | 110 | 20 | 5.5 |
| VERIFIED_EXACT | 46 | 5（对照） | 9.2 |
| **合计** | **290** | **88** | |

五类（VARIANT/POSSIBLE/AUTHOR_CONFLICT/TITLE_ONLY/NO_MATCH）全部覆盖，且前三类与 TITLE_ONLY 为**全取**，不存在「只挑好核的」问题；`VERIFIED_EXACT` 5 条为对照组。

## A3. 比对方法

1. **取文**：例词 `cipai_form_examples_r2_08.text`；作品 `works.text_s`（缺则 `text_norm`／`text_raw`）。
2. **规范化**：只保留汉字（去掉 OCR 页码数字、标点、拉丁字母），OpenCC `t2s` 统一简体。GBK 之外的扩展字保留。
3. **切段**：例词正文常把书里的编例一起吞进来（`例二`／`例三`／`格二` 之后是另一首词或词谱符号，`——作者（小注）` 之后是题解）。按 `(?=例[二三四五六]|格[二三四五六])` 切段、各段截斷到 `——` 之前，逐段与作品比对，取最贴合段。**不切段则误判**：EX-0083 整段相似仅 0.409、EX-0308 仅 0.252，切段后分别为 0.968、0.968。
4. **度量**：Levenshtein 编辑距离 `lev`、相似度 `ratio = 1 - lev/max(len)`、最长公共子串、双向包含（`e in w` / `w in e`）、`SequenceMatcher` 逐处异文。
5. **作者**：例词 `author` 与 `works.author_name`／`author_canonical` 经同一规范化后比对（繁简、空格差异不算冲突）。
6. **NO_MATCH 双路检索**（只做一路会漏）：
   - A 路 `instr(text_s, 14字窗口)`，窗口取首／中／尾；
   - B 路 作者池（同名作者全部作品）+ 同词牌作品，逐条算相似度；
   - 两路合并去重，取 top3。仅当两路都无 ≥0.45 的候选，才判 `NO_MATCH` 成立。

## A4. 判定规则（写死在 `tools/r2_11_example_csv.py: decide()`）

文本档位：`T0` 全等（lev=0 且长度相同）｜`T1` ratio≥0.95｜`T2` 0.80–0.95｜`T3` 0.60–0.80｜`T4` <0.60。

| 原判 | 条件 | 终判 | verdict |
|---|---|---|---|
| VERIFIED_EXACT | T0 | 维持 | CONFIRMED |
| VERIFIED_EXACT | T1/T2 | 降 VERIFIED_VARIANT／POSSIBLE | CORRECTED_DOWN |
| VERIFIED_VARIANT | T0 | 升 VERIFIED_EXACT | CORRECTED_UP |
| VERIFIED_VARIANT | T1/T2 | 维持 | CONFIRMED |
| VERIFIED_VARIANT | T3/T4 | 降 POSSIBLE／TITLE_ONLY | CORRECTED_DOWN |
| POSSIBLE_MATCH | T0 | 升 EXACT | CORRECTED_UP |
| POSSIBLE_MATCH | T1/T2 且同作者 | 升 VARIANT | CORRECTED_UP |
| POSSIBLE_MATCH | 其余 | 维持 | CONFIRMED |
| AUTHOR_CONFLICT | 文本相符且作者不符 | 维持 | CONFIRMED |
| AUTHOR_CONFLICT | 作者其实相同 | 降 VARIANT | CORRECTED_DOWN |
| TITLE_ONLY | T0–T2 | 正文有实据：同作者→VARIANT，异作者→AUTHOR_CONFLICT | CORRECTED_UP |
| TITLE_ONLY | T3 | 升 POSSIBLE_MATCH | CORRECTED_UP |
| TITLE_ONLY | T4 | 维持 | CONFIRMED |
| NO_MATCH | 命中 ≥0.80 且同作者 | 升 VARIANT | CORRECTED_UP |
| NO_MATCH | 命中 ≥0.85 且异作者 | 升 AUTHOR_CONFLICT | CORRECTED_UP |
| NO_MATCH | 命中 0.60–0.80 且同作者 | 升 POSSIBLE_MATCH | CORRECTED_UP |
| NO_MATCH | 无 ≥0.45 候选 | 维持 | CONFIRMED |

**关于「不得仅凭相似度升级」的执行**：所有升级都同时满足三条——(a) 正文有具体异文清单（`evidence` 内逐处列出，多数为 1–4 字）；(b) 作者经规范化后相同，或明确记为 AUTHOR_CONFLICT；(c) 词牌/调名相符。只满足 (a) 的（EX-0184 作者字段被截断、EX-0275 仅 0.727、EX-0091 仅 0.758）**一律不升到 VERIFIED_VARIANT**。

## A5. 结果

### A5.1 总量

- verdict：CONFIRMED 51 ／ CORRECTED_UP 36 ／ CORRECTED_DOWN 0 ／ DATA_ERROR 1（=88）。其中 EX-0012 一条判 `DATA_ERROR`、终态记 `UNVERIFIABLE`。
- **抽样中没有任何一条被判「高判」**：40 条 VERIFIED_VARIANT、5 条 VERIFIED_EXACT 全部站得住（最低相似 0.936）。问题全部集中在「低判」与「NO_MATCH 漏检」。

### A5.2 迁移矩阵

| 原判 → 终判 | 条数 |
|---|---:|
| VERIFIED_EXACT → VERIFIED_EXACT | 5 |
| VERIFIED_VARIANT → VERIFIED_VARIANT | 33 |
| VERIFIED_VARIANT → VERIFIED_EXACT | 7 |
| POSSIBLE_MATCH → VERIFIED_VARIANT | 15 |
| POSSIBLE_MATCH → POSSIBLE_MATCH | 1 |
| TITLE_ONLY → AUTHOR_CONFLICT | 2 |
| TITLE_ONLY → POSSIBLE_MATCH | 1 |
| AUTHOR_CONFLICT → AUTHOR_CONFLICT | 4 |
| NO_MATCH → VERIFIED_VARIANT | 9 |
| NO_MATCH → AUTHOR_CONFLICT | 1 |
| NO_MATCH → POSSIBLE_MATCH | 1 |
| NO_MATCH → NO_MATCH | 8 |
| NO_MATCH → UNVERIFIABLE | 1 |

抽样内（不代表全量）终态分布：VERIFIED_VARIANT 57 ／ VERIFIED_EXACT 12 ／ AUTHOR_CONFLICT 7 ／ NO_MATCH 8 ／ POSSIBLE_MATCH 3 ／ UNVERIFIABLE 1。

按层看「原判被推翻的比例」：

| 层 | 抽样 | 被推翻 | 比例 |
|---|---:|---:|---:|
| NO_MATCH | 20 | 12（11 条漏检 + 1 条数据错误） | **60%** |
| TITLE_ONLY | 3 | 3 | 100% |
| POSSIBLE_MATCH | 16 | 15 | 94% |
| VERIFIED_VARIANT | 40 | 7 | 18%（仅「低判为 EXACT」） |
| VERIFIED_EXACT | 5 | 0 | 0% |
| AUTHOR_CONFLICT | 4 | 0 | 0% |

### A5.3 五个实质问题

**(1) NO_MATCH 漏检 11/20：在库内有同作者同调、相似 0.87–0.97 的作品**（另有 1 条 EX-0012 属数据错误，不算漏检）。

| 例 | 例词 | 库内命中 | 相似 |
|---|---|---|---:|
| EX-0002 | 张孝祥《十六字令》归！猎猎西风卷绣旗 | `songci:d7dc9da7354d`《苍梧谣·归字谣》张孝祥 | 0.875 |
| EX-0063 | 晏幾道《鹧鸪天》彩袖殷勤捧玉钟 | `songci:c8de09e9e6dd`《鹧鸪天》晏几道 | 0.945 |
| EX-0113 | 聂冠卿《多丽》想人生美景良辰堪惜 | `songci:c3a3fa039b2c`《多丽》聂冠卿 | 0.936 |
| EX-0124 | 贺铸《生查子》西津海鹘舟 | `songci:8fdc41724ee5`《陌上郎·生查子》贺铸 | 0.950 |
| EX-0160 | 周邦彦《夜游宫》叶下斜阳照水 | `songci:af39adcde45a`《夜游宫》周邦彦 | 0.965 |
| EX-0203 | 贺铸《天香》烟络横林 | `songci:fee5829d3c2c`《伴云来·天香》贺铸 | 0.969 |
| EX-0229 | 张元幹《石州慢》雨急云飞 | `songci:e4e0bc718440`《石州慢》张元干 | 0.941 |
| EX-0262 | 欧阳炯《南乡子》路入南中 | `tang:5cd6a4c59dd0`＋`huajianji:c7c244a8ebcf`（两处重复收录） | 0.964 |
| EX-0283 | 潘阆《忆馀杭》长忆西湖 | `songci:7537d9425bc8`《酒泉子》潘阆 | 0.959 |
| EX-0050 | 贺铸《柳梢青》子规啼血 | `songci:7af2569e9a47`《柳梢青》蔡伸 | 0.898（作者冲突） |
| EX-0275 | 王安石《菩萨蛮》数间茅屋闲临水 | `songci:7445d27504e0`《菩萨蛮》王安石 | 0.727（只升 POSSIBLE） |

机制线索：这 11 行在原表里 `work_len=0`、`work_id` 为空——**候选根本没生成**，不是「生成了但被判低分」。可核的线索有两条，但都解释不全，故只作线索不作结论：

- 例词正文含 OCR 残留数字：11 条中 4 条（EX-0063「剩51把」、EX-0113「低88亸」、EX-0124「鸦98轧」、EX-0160「酸121风」）。若包含判断未剥离数字，整句永不相等。但另 7 条无数字，故此因至多解释 4/11。（参考：本轮 88 条样本中有 29 条正文含 ASCII 数字，是普遍现象。）
- 库内标题多为别名：苍梧谣（十六字令）、陌上郎（生查子）、伴云来（天香）、酒泉子（忆馀杭）；若按标题/词牌精确匹配会落空。但 EX-0063 的《鹧鸪天》、EX-0160 的《夜游宫》都是本名，故此因亦只解释一部分。

两条线索都不足以定位根因；**唯一确定的是这些行从未产生候选**，所以 `NO_MATCH` 在本表中只能读作「未检索到」，不能读作「已排除」。

对照：另 8 条 NO_MATCH 经双路检索确认库内确无（辛弃疾 257 篇无《破阵子》「醉里挑灯看剑」、无《贺新郎》「绿树听鹈鴂」；姜夔 196 篇无《扬州慢》《惜红衣》《翠楼吟》；全库无作者「程垓」）。**所以 NO_MATCH 既不能整体推翻，也不能整体采信。**

**(2) VERIFIED_VARIANT 里有 7 条其实是逐字全等（lev=0）**：EX-0010 李煜《捣练子令》、EX-0043 欧阳炯《三字令》、EX-0062 柳永《临江仙》、EX-0270 晁补之《调笑令》、EX-0295 柳永《曲玉管》、EX-0299 温庭筠《荷叶杯》、EX-0304 李煜《相见欢》——规范化后与作品一字不差，应为 `VERIFIED_EXACT`。占 VARIANT 层抽样 17.5%。

**(3) POSSIBLE_MATCH 层近乎全错（15/16）**：这些例子的相似度是 0.886–0.964、同作者同词牌、异文 1–7 字（如 EX-0216 苏轼《念奴娇》「崩云/穿空」「裂/拍」「樯橹/强虏」，EX-0134 苏轼《卜算子》「谁/时」「寂寞沙洲/枫落吴江」），按任何 0.80 门槛都该是 VARIANT。唯一维持的是 EX-0184：作品 `author_name` 被截断成「张」（应为张昇），作者无法比对。

**(4) TITLE_ONLY 3 条全错，且暴露出「合编块」污染**：EX-0083、EX-0308 的例词正文把下一首例子（例二／例三）和词谱符号一起吞进来；切段后首段与所链作品相似 0.968，正文其实有据——但例词作者栏分别标「秦观」「柳永」，而作品是「苏轼」，所以正确终态是 `AUTHOR_CONFLICT` 而非 TITLE_ONLY。EX-0091 李清照《凤凰台上忆吹箫》是同一阕的异文（0.758，23 处：慵自/人未、尘满/闲掩、离怀别苦/闲愁暗恨、新来/今年…），低于 0.80，只判 `POSSIBLE_MATCH`。

**(5) 数据质量问题（非状态问题，但会污染后续所有统计）**
- `works.author_name` 截断：`songci:8bec07f2c16e` 作者写作「张」，`author_canonical` 同为「张」（应「张昇／张昪」）。
- 例词正文混入编例与页码：「（增字）」「（"也"是衬字）」「不叶韵」「例二」「格二（仄韵长调）｜－－（豆）…」、数字「18／51／98／121／157／188／229／243／246」等；EX-0227 衍「乍」、EX-0239 衍「𬘘」。
- EX-0012 的「例词正文」根本不是词，是词谱说明（「用入声，原用入声韵者，亦常改作平韵）…《清真集》入"商调"…共一百三十三字」），无法作为核验对象 → `DATA_ERROR`／`UNVERIFIABLE`。
- EX-0021 例词首字「䴔䴖」OCR 丢失（作品 35 字、例词 33 字）。

## A6. 局限（必须随结论一起读）

1. **只核了 88/310**。上表比例只能说明「该层有这类错误」，**不能外推为全量条数**，也**没有**据此改写 `example_work_links_r2_09` 或 `EXAMPLE_310_FINAL_STATUS.csv`（本轮只出复核表，不改库）。
2. 相似度只证明「同一段文本」，不证明「这是该词牌的标准范例」。词牌归属（`cipai` 与作品 `title_raw` 的别名关系）只做宽松比对，未逐条考订。
3. `works.text_s` 为简体转换结果，个别字（如「沈/沉」「翦/剪」）的差异在 `evidence` 中如实列出，未强行归并。
4. AUTHOR_CONFLICT 4 条只核「文本相符、作者不符」，**未考订谁才是真作者**（秦观/仲殊、朱淑真/欧阳修、宋祁/无名氏、秦观/无名氏 都是历代归属之争，非本轮可断）。

## A7. 复算

```bash
cd <PROJECT_ROOT>/poetry-database
python3 tools/r2_11_example_recheck.py   # 抽样+比对 -> LOGS/f2_detail.json（约 50s）
python3 tools/r2_11_example_csv.py       # 规则判定 -> EXAMPLE_LINK_100_FINAL_AUDIT.csv
```

关键 SQL（均为只读）：

```sql
-- 表结构确认
PRAGMA table_info(example_work_links_r2_09);
PRAGMA table_info(cipai_form_examples_r2_08);
PRAGMA table_info(works);

-- 母体与分层
SELECT example_id,new_match_kind FROM example_work_links_r2_09 ORDER BY example_id;

-- 取文
SELECT example_id,form_id,cipai_name,author,author_note,text,n_chars,pdf_page
  FROM cipai_form_examples_r2_08;
SELECT work_id,title_raw,author_name,author_canonical,collection,cipai,text_s,text_norm,text_raw
  FROM works;

-- NO_MATCH 的 A 路（窗口全库检索，14 字窗口，首/中/尾各一）
SELECT work_id,title_raw,author_name,text_s FROM works
 WHERE instr(text_s,'醉里挑灯看剑梦回吹角') > 0;

-- NO_MATCH 的 B 路（作者池 / 同词牌池）
SELECT work_id,title_raw,author_name,cipai,text_s FROM works WHERE author_name = ?;
SELECT work_id,title_raw,author_name,cipai,text_s FROM works
 WHERE title_raw LIKE '%'||?||'%' OR cipai LIKE '%'||?||'%';
```

输出指纹：

```
beae34bc1b770f4cf50cc9c59f4e83ae2cd4c2708ec99167280122448288f3a7  EXAMPLE_LINK_100_FINAL_AUDIT.csv
d0c3221b6b5b20331ccbc2057dc2b52c425859a9344fc65f75e026b7ae55fcc8  LOGS/f2_detail.json
```

---

# 第二部分 上古音 40 例来源链（任务 B）

## B1. 判定口径

任务给的降级标准针对「有学者无书名」。实测 40 例的问题形态更细，故把 `citation_status` 拆成五档，并在每一行 `note` 写明缺哪一项：

| 值 | 含义（四要素：学者/机构 · 著作 · 定位单元 · 载体可核） |
|---|---|
| `CONFIRMED_CITATION` | 四要素齐（有影印本／官网 PDF／出版社+ISBN／期刊名之一） |
| `PARTIAL_CITATION` | 有著作与链接，但缺作者、或出版信息、或页码 |
| `UNVERIFIED_CITATION` | 只到「某网站题解／某学者认为」一级，无学术责任人或无书名 |
| `UNSUPPORTED` | 声称有据但完全无出处 |
| `MISSING_CITATION` | 输入档未给任何出处（此档**不等于**虚假引用） |

不联网，**不补造书名与页码**；凡 ISBN、2019 点校本、sinoss/教育局 PDF 内容，本地均无法核验，一律写明「未核」。

## B2. 结果

案件状态分布（与 `ANCIENT_RHYME_40_REAUDIT.md` 表一致）：`SCHOLAR_IDENTIFIED_RHYME` 22／`POSSIBLE_RHYME_POSITION` 13／`LINE_END_CANDIDATE` 5／`SOURCE_VERIFIED_RHYME` 0。

引用状态分布：

| citation_status | 条数 | 对应 claim_status |
|---|---:|---|
| CONFIRMED_CITATION | 12 | SCHOLAR 12 |
| PARTIAL_CITATION | 9 | SCHOLAR 9 |
| UNVERIFIED_CITATION | 2 | SCHOLAR 1（SJ-11）＋ LINE_END 1（CC-03） |
| MISSING_CITATION | 17 | POSSIBLE 13 ＋ LINE_END 4 |
| UNSUPPORTED | 0 | — |
| **合计** | **40** | |

也就是说：**22 条「学者认定」里，只有 12 条四要素齐全；9 条缺作者或页码；1 条（SJ-11 蒹葭）的「学者」其实是诗词网站题解。**

四要素齐全的 12 条：
- 关雎 SJ-01（香港教育局教材，机构+文件+PDF+逐字韵脚）；
- 载芟 SJ-27、良耜 SJ-28（刘师培《毛诗正韵》卷四＋Wikimedia 影印 PDF，**载体最硬**）；
- 楚辞 9 条 CC-01/02/04/05/06/07/08/09/10（蒋骥《山带阁注楚辞》卷首《楚辞说韵》＋上海古籍 2019 点校本＋ISBN＋篇条）。

## B3. 六个实质问题

**(1) 引文覆盖不到全篇韵位，但状态写的是全篇。** 把 `attribution_source` 的「…」引文与 `rhyme_chars` 逐字比对（规范化后）：

| 例 | 表列韵位 | 引文可核 | 缺口 | 说明 |
|---|---:|---:|---:|---|
| SJ-08 氓 | 34 | 5 | 29 | 引文只具体列首章，其余 29 位是自增 |
| CC-01 离骚 | 188 | 4 | 184 | 引文以「……」节引，中段全不可核 |
| CC-02 天问 | 201 | 20 | 181 | 同上 |
| CC-04 招魂 | 160 | 27 | 133 | 同上 |
| CC-06 涉江 | 35 | 26 | 9 | 无节引却缺螭、寿、皋、皇、鹊、夷、御、位、傺 |
| CC-07 惜诵 | 44 | 30 | 14 | 缺者 12 为「也」 |
| CC-08 怀沙 | 43 | 23 | 20 | 缺者 6 为「也」 |
| CC-09 湘君 | 38 | 24 | 14 | 缺洲、修、波、绸、湲、中、劳、长、闲、皋、上、若、得 |
| CC-10 山鬼 | 27 | 18 | 9 | 缺狸、衡、天、上、晦、归、闲、冥（表已声明「不代为解释」） |
| SJ-30 閟宫 | 75 | 6 | 69 | 表已标「仅首章可考」，未外推，处理诚实 |
| SJ-14 采薇 | 28 | 8 | 20 | 表已标「仅第三章可考」，处理诚实 |

结论：`SCHOLAR_IDENTIFIED_RHYME` 应理解为「**该例的韵段框架由某学者确定**」，而不是「每一个韵位都有学者背书」。CC-01/02/04 用「……」节引却支撑 160–201 个韵位，缺口最大；建议在这三条的 `note` 里加一句「仅首尾可核」。

**(2) 与自订通例冲突：CC-07 惜诵、CC-08 怀沙大量取「也」入韵。** 二例分别有 12、6 个「也」被列为韵脚，而蒋骥韵段不含「也」；同时 `ANCIENT_RHYME_40_REAUDIT.md` §5.1 自订「SJ-07 剥也、SJ-08 剥也矣」。同一份表里，对《诗经》剥「也」、对《楚辞》留「也」，规则不统一，需逐位交代依据。

**(3) `SCHOLAR_IDENTIFIED_RHYME` 与 `UNATTRIBUTED` 并存的语义冲突。** 楚辞 9 条的 `rhyme_group_attribution` 全为 `UNATTRIBUTED（蔣驥只列韻段，未標部名）`——即**韵部一个都没定**，却挂着「RHYME 已由学者认定」的状态名。字面读会误以为韵部已考定。建议把该状态在表头定义为「韵段/韵脚位置由学者韵谱确定，韵部另计」，或改名 `SCHOLAR_IDENTIFIED_RHYME_SEGMENT`。全表 27 例韵部为 `UNATTRIBUTED`（17 例诗经 + 10 例楚辞），这一点 R2-10 报告已如实写明，不算隐瞒。

**(4) 部分引文本身有讹字。** SJ-04 芣苡引文作「采、友，之部」，而《芣苡》全文无「友」字、表列亦作「有」——引文与正文不合。R2-10 已在 `dispute` 自承「当是采、有之误」，但 `attribution_source` 原文仍是「友」，属未清理的引文错误。

**(5) 载体与所标版本不一致（楚辞 9 条）。** 引文标注「上海古籍出版社 2019 于淑娟点校本，ISBN 9787532591381」，但给出的链接是 `zhonghuadiancang.com` 的电子本。二者不是同一载体，**本地无法确认所引字句出自所标点校本**；ISBN 亦无从核验（本地无馆藏、不联网）。不因此降级（版本信息本身是完整的），但须在引用时注明「据网络电子本，未核原书」。

**(6) 转引未落地。** CC-01 里「王力《古代汉语》以庸、降为东冬合韵（转引自公开课件）」——有书名、无页码、来源是「公开课件」。按本轮口径，这一句本身只能算 `UNVERIFIED`，不应与蒋骥的直接引文并列；蒋骥条不受影响。

## B4. 机械一致性核查（全部通过，可作为「文本层没坏」的证据）

| 检查 | 结果 |
|---|---|
| 40 例 `work_id` 是否都能在 `works` 取到正文 | 40/40 命中 |
| `rhyme_positions` 个数 = `rhyme_chars` 字数 | 40/40 相等（合计 1706 位 / 1706 字） |
| 韵位有无重复 | 无 |
| 每个韵字是否真的出现在对应作品正文中（繁转简后比对） | 1706/1706 全部出现，0 缺字 |
| `rhyme_positions` 合计是否等于报告所称 1706 | 相等 |

即：**文本层与位置层自洽**，本轮的质疑集中在「出处要素」与「引文覆盖」，不在「字是否抄错」。

## B5. 局限

1. 不联网，蒋骥点校本、刘师培影印本、sinoss 论文、教育局 PDF 的**内容**均未打开核对，只核「引用要素是否齐全、引文与表列是否自洽」。「CONFIRMED_CITATION」只表示**引注形式完整**，不表示**内容已被独立验证**——这也是本轮没有一例敢标 `SOURCE_VERIFIED_RHYME` 的原因，与 R2-10 的判断一致。
2. 未考订各家分部（王力三十部／江有诰廿一部／刘师培自成分部）的对错，只记录表内是否绑定体系。
3. `rhyme_position` 列对长例（离骚 188 位、天问 201 位）做了截断显示（前 12 位 + 总数），完整值仍在两个 R2-10 CSV 中。

## B6. 复算

```bash
python3 tools/r2_11_ancient_review.py   # -> ANCIENT_RHYME_40_SOURCE_REVIEW.csv
```

一致性核查用的 SQL 仅一条：

```sql
SELECT text_norm FROM works WHERE work_id = ?;   -- 逐例取文后与 rhyme_chars 比对
```

指纹：

```
f9b9c794d6361c4b219351b6f5bf88c42acfe854150d6fcaa34e77d98ac59e0c  ANCIENT_RHYME_40_SOURCE_REVIEW.csv
```

---

# 第三部分 给主 Agent 的三条提醒

1. **不要把 `NO_MATCH` 当「已排除」用**：抽样 20 条里 11 条在库内有同作者同调、相似 0.87–0.97 的作品，且这些行 `work_len=0`（从未产生候选）。建议对 110 条 NO_MATCH 全量重跑一次双路检索，成本很低（本轮 88 条含全库扫描约 50 秒）。
2. **`work_len=0` 应作为硬性告警**：凡 NO_MATCH 且 `work_len=0`，就说明「没搜过」而非「搜过没有」，二者不能共用同一状态。
3. **上古音 40 例的 22 条「学者认定」需分层呈现**：12 条四要素齐全、9 条缺作者或页码、1 条只是网站题解。尤其 CC-01/02/04 用「……」节引撑起 160–201 个韵位，读者会高估依据密度。
