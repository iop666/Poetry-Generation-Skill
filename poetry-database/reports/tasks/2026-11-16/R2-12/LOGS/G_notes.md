# R2-12 独立复核对账笔记（G1–G4）

复核者：general-purpose-2　日期：2026-11-16
工作目录：`<PROJECT_ROOT>/poetry-database`
工具：本地 `sqlite3`（`database/poetry.db`）、Python 3（`difflib` / `opencc` / `pypinyin` 可用，`jieba` 不可用）。**全程未联网。**

本文件记录：所用 SQL 全文、抽样与排除方法、零交集断言的实现、各类计数、以及我不确定的地方。

---

## 1. 输入与产出对照

| 任务 | 输入 | 产出 | 条数 |
|---|---|---|---|
| G1 | `R2-10/THIRTY_CLOSE_READINGS.csv`（30 首） | `THIRTY_CLOSE_READINGS_FINAL_AUDIT.csv` | 180 行（165 判定 + 15 修订核验） |
| G2 | `R2-10/TEN_INDEPENDENT_TEXT_COLLATIONS.csv`（10 首） | `TEN_TEXT_COLLATIONS_SECOND_REVIEW.csv` | 5 行（no.6–10） |
| G3 | `R2-11/EXAMPLE_LINK_100_FINAL_AUDIT.csv`（88）、`R2-10/EXAMPLE_310_FINAL_STATUS.csv`（310）、`R2-10/EXAMPLE_100_INDEPENDENT_REVIEW.csv`（20） | `EXAMPLE_LINK_100_INDEPENDENT_VERIFICATION.csv` + `EXAMPLE_LINK_STATUS_RECONCILIATION.md` | 100 行 |
| G4 | `R2-11/ANCIENT_RHYME_40_SOURCE_REVIEW.csv`（40） | `ANCIENT_RHYME_40_EVIDENCE_FINAL.csv` | 40 行（22 条评分 + 18 条 NOT_APPLICABLE） |

脚本：`LOGS/gen_g1.py`（＋`gen_g1_part1.py`）、`LOGS/gen_g2.py`、`LOGS/gen_g3_v2.py`（`gen_g3.py`/`gen_g3_v1_backup.py` 为废弃中间版，保留以存过程）、`LOGS/gen_g4.py`。

---

## 2. G1：30 首精读卡第二轮

### 2.1 原文逐字比对（程序化，不依赖记忆）

关键点：**去标点时不能只用 `[\u4e00-\u9fff]`**。本次数据中出现 `㸔`(U+3F14, Ext-A)、`㸃`(U+3402 区)、`𠉀`(U+21009, Ext-B)，若用基本区正则会被静默删除，导致「源2 比库少 1 字」「异文数虚增」的假结论。正确范围：

```python
CJK = re.compile(r'[^\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0003ffff]')
def norm(s): return CJK.sub('', s or '')
```

比对用 `difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()`，取非 `equal` 的块与位次。

### 2.2 所用 SQL 全文

```sql
-- ① 取单首作品，核对作者/时代/体裁/字数/文本/校验状态
SELECT work_id, title_raw, author_name, author_canonical, dynasty, genre, collection,
       char_count, line_count, text_raw, text_norm, verify_status, dup_status,
       source_id, juan, record_locator
FROM works WHERE work_id = ?;

-- ② 韵脚字查库内平水韵表
SELECT tone, rhyme_group FROM ph_readings_r2_08
WHERE system = 'regulated_verse' AND charx = ?;

-- ③ 韵脚字查库内词林正韵表
SELECT tone, rhyme_group FROM ph_readings_r2_08
WHERE system = 'ci_rhyme' AND charx = ?;

-- ④ 韵脚字查库内广韵（交叉验证）
SELECT tone, rhyme_group FROM ph_readings_r2_08
WHERE system = 'middle_chinese' AND charx = ? AND source_book LIKE '廣韻%';

-- ⑤ 词牌句数/韵位（判「上片九句」「韵脚十处」一类说法）
SELECT cipai_name, form_seq, total_characters, sentence_count, sentence_lengths,
       rhyme_positions, rhyme_count, rhyme_tone, stanza_structure
FROM cipai_forms_r2_07
WHERE cipai_name IN ('雨霖铃','满江红','青玉案','钗头凤','浣溪沙','西江月','声声慢');

-- ⑥ 词谱说明（正名/异名/页码）
SELECT name, char_count, rhyme_note, source_book, page, parse_status
FROM cipai_specs WHERE name LIKE ? OR aliases LIKE ?;
```

> **必须注意**：`ph_readings_r2_08` 的 `charx` 存繁体字形（如 `樓`/`響`/`間`），用简体直接查会全部落空。本次一律先 `opencc.s2t` 再查。另外「征」经 s2t 会变成「徵」（下平十蒸），这是检索假象，不是卡片错误——C11 的韵部结论已按「征行」之征（清韵，平水八庚）判。

### 2.3 判定口径

- **PASS**：判断可在库内文本/韵表/词谱中复核且无误。
- **ISSUE**：判断与文本或库内数据矛盾、内部自相抵牾、或为无据的评价/影响论。
- **UNVERIFIABLE**：卡片所举系年、本事、书目、学术史等，库内无对应字段或原书，无法核。**这不是错误**，只是不可核。
- 「创作背景」不因「无系年」自动扣分；若卡片主动不作断言（如 C15、C30），判 PASS。

### 2.4 计数

165 条判定：**PASS 137 / ISSUE 16 / UNVERIFIABLE 12**。

| 维度 | PASS | ISSUE | UNVERIFIABLE |
|---|---|---|---|
| 原文完整性 | 13 | 2（C14、C20） | 0 |
| 作者与时代 | 15 | 0 | 0 |
| 题目 | 14 | 1（C28） | 0 |
| 创作背景 | 3 | 0 | 12 |
| 章法 | 14 | 1（C02） | 0 |
| 意象 | 14 | 1（C28） | 0 |
| 炼字 | 15 | 0 | 0 |
| 用典 | 14 | 1（C28） | 0 |
| 语言风格 | 13 | 2（C06、C29） | 0 |
| 韵脚与声调 | 9 | 6（C11、C20、C24、C26、C28、C29） | 0 |
| 艺术特点 | 13 | 2（C15、C30） | 0 |

- **有实质 ISSUE 的：11/15**（C02、C06、C11、C14、C15、C20、C24、C26、C28、C29、C30）。
- **仅「背景不可核」、无实质错误的：4/15**（C03、C05、C10、C27）。
- 问题最集中的维度：**韵脚与声调 6 条**（全部可拿库内韵表/词谱/原文对死），其次原文 2、语言风格 2、艺术特点 2。

### 2.5 五首旧卡的修订核验

文件 `R2-10/THIRTY_CLOSE_READINGS.csv` 的 mtime 为 `2026-11-15 21:28:01`，md5 `7e59f96f94f4718fbe542d5e0b97c156`；R2-11 的审核文件生成于 `23:14:56`，此后**没有任何新版本精读卡文件**（`find reports -name "*THIRTY*" -newermt "2026-11-15 21:30"` 只命中 R2-11 的审核表）。

对 C01/C07/C12/C16/C23 逐句回看现文件：15 项旧问题**全部原样保留**，`revised_check` 一律记 `NOT_REVISED`。举证方式是在 `evidence` 栏逐字引出现文件原句，例如：

- C01 prosody 仍作「第三字当平面用仄（月）」；
- C07 note 仍只记「通行本多作各不同」，全篇无「無一同」；
- C12 note 仍全句只有「字数 40，与库一致。」；
- C16 note 仍全句只有「字数 56，与库一致。」；
- C23 imagery 仍作「全篇几乎无色彩」。

### 2.6 G1 中我不确定的地方

1. **C14 / C20 的字数口径**：库 `char_count` 为 58 / 290，而正文 56 / 285、含校记 62 / 294。58 与 290 无法由任何一致口径推出（58=56+2，但校记是 6 字；290=285+5，但校记是 9 字）。我判 ISSUE 的依据是「卡片给出的解释在算术上不成立」，而不是「我认定库的 58/290 是错」——库的计数函数我没有找到定义，无法判断它本意计什么。
2. **C03「上」字上/去两读**：库表两收（上声二十二养、去声二十三漾）。「青苔上」义为「之上」，语义上当读去声，但韵书确收上声一读。我判 PASS 并注明此点，若审稿人取严，可改判 ISSUE。
3. **C02「一横一纵」**：我据「白日西沉与黄河东流同为东西向」判 ISSUE。这是修辞层面的判读，若作者本意是「横＝西、纵＝东」的借代，则可争议——但卡片原文用的字是「横/纵」，不是「西/东」。
4. **词律句数依何谱**：C24（17 句）与 C27（8+10 句）都合《钦定词谱》而与库谱（23 句 / 22 句）不合。我只在 C24 判 ISSUE（因其字数 102 与库谱 103 也不合），C27 判 PASS（字数 93 与库谱一致）。**这项区分是我的裁量**，不是硬规则。
5. **「背景」一律 UNVERIFIABLE**：库内无集部/史部原书，这是库的边界。若日后接入年谱/方志，这 12 条应重判，而不是维持「不可核」。

---

## 3. G2：版本对勘第二次复核（no.6–10）

### 3.1 方法

同一套 `norm()` 去标点（含 ExtA/ExtB）→ 等长则逐位比较 → 再用 `opencc.t2s` 把两侧都转简，剩余差异即「非繁简层」（异文/异体/脱字/衍字）。不等长时用 `difflib` 对齐并报 `delete/insert`。

位次一律 1-based、按去标点后的序列计，且与 claim 的「第 N 句第 M 字」互相换算核对。

### 3.2 结果

| no | 篇 | db/源2 字数 | 原始差异位次 | 非繁简层 | claim 复现 | 判定 |
|---|---|---|---|---|---|---|
| 6 | 題西林壁 | 28/28 | 7 | 5（2 异文＋3 字形…共 5） | EXACT | LOCATOR_SUFFICIENT |
| 7 | 飲酒·其五 | 50/49 | 2 | 2（1 字形＋1 脱字） | PARTIAL（位次差一位） | LOCATOR_SUFFICIENT |
| 8 | 虞美人 | 56/56 | 13 | 3 | PARTIAL（note 称「仅一字」不成立） | LOCATOR_SUFFICIENT |
| 9 | 声声慢 | 97/97 | 37 | 11 | EXACT | LOCATOR_SUFFICIENT |
| 10 | 水调歌头 | 95/95 | 30 | 2 | PARTIAL（多列「宫/宮」） | LOCATOR_SUFFICIENT |

### 3.3 三条具体发现

1. **no.7 位次错一位**：claim 称脱字在「第 6 句第 5 字」，实为第 4 字（位次 29）。第 6 句「悠然見南山」自第 26 字起：悠26 然27 見28 南29 山30。
2. **no.8 完备性夸大**：note 断言「剔除繁简後實際差異僅『欄／闌』一字」，实际另有「往/徃」（位次 8）、「几/㡬」（位次 45）两处异体/旧字形。异文事实无误，完备性结论错。
3. **no.10 多列一项**：claim ② 列「宫/宮」为字形差，实际两本此字均作「宫」（U+5BAB），无一处作「宮」。

### 3.4 定位是否充分

5/5 可复现，但**严格含卷次/页码的只有 3/5**：no.6（卷13）、no.7（卷3）、no.8（卷889）有卷次；no.9《漱玉詞》、no.10《東坡詞》四库本均**一卷不分卷**，locator 只能用「正文第2闋」「又〈丙辰中秋…〉條」，无卷次亦无葉次。我判 SUFFICIENT 的理由是「在指定底本内可唯一确定该篇」，并在 note 中写明「严格按含卷次/页码的标准不合格，建议补葉次」。

### 3.5 不确定处

- 「繁简层」的划分依赖 OpenCC。OpenCC 不处理某些异体（如「徃」「㡬」「戸」「乆」），故它们落在「字形层」而非「繁简层」。这个归类是技术性的，不影响「是否同一文本」的判断，但会影响「n_diff_positions」的口径。
- 两本不同不等于其中一本错。本表只记差异与位次，**未做优劣判断**。

---

## 4. G3：例词关联 100 条

### 4.1 抽样与排除（零交集如何实现）

```python
# 上一轮 88 条：直接取 link_id（实测即 example_id，形如 EX-0049，88 个全不重复）
p88 = {r['link_id'] for r in csv.DictReader(open('R2-11/EXAMPLE_LINK_100_FINAL_AUDIT.csv'))}

# 上一轮 20 条：其 item_id 是 EX-01…EX-0310 的序号，与 example_id 不同名，
# 故按任务要求用 evidence 首句定位：正则取「例詞「…」」的前 12/10/8 字，
# 在 cipai_form_examples_r2_08.text 的归一化首 12 字索引里查
ag = [r for r in rows if r['review_type'] == 'INDEPENDENT_AGENT']
for r in ag:
    q = norm(re.search(r'例詞[「『]([^」』]+)', r['evidence']).group(1))
    hit = first(ex_id whose norm(text)[:12] == q[:L]) for L in (12,10,8)

# 断言（脚本内真断言，不是事后声明）
assert len(p20) == 20
assert not (p88 & p20)
assert len(remaining) == 202          # 310 - 108
assert not (set(sel) & (p88 | p20))   # ← 零交集
assert len(set(sel)) == 100
```

映射结果：20 条全部一次命中，无歧义；88 与 20 本体无交集；剩余池 202 条。

**剩余池中 AUTHOR_CONFLICT、TITLE_ONLY 均为 0**（6＋5 条已全部落在上一轮 88 条里），故「优先复核这三类」实际只落到 `NO_MATCH` 90 条；再按 example_id 序取 `VERIFIED_VARIANT` 10 条补足 100。

### 4.2 检索（真的重新检索，不继承相似度）

- 检索词级联：首句前 **10 → 8 → 6** 字 → 中段 8 字（1/3 处）→ 中段 8 字（2/3 处）。
- 检索位置：`works.text_norm` 与 `works.text_raw` **两列都查**，繁体底本另检其繁体形式。
- 为什么不用 SQL `LIKE`：单次 `LIKE '%…%'` 全表扫 375,399 行约 3.3 s，100 条 × 5 级 × 2 列 ≈ 11 分钟。改为一次取回 `work_id/text_norm/text_raw/...` 在内存做子串匹配，**语义等价**。已抽样验证等价性：

```
西塞山前白鹭: SQL norm=2 raw(trad)=2 | PY norm=2 raw(trad)=2
东风夜放花千树: SQL norm=0 raw(trad)=0 | PY norm=0 raw(trad)=0
大江东去:   SQL norm=23 raw(trad)=8 | PY norm=23 raw(trad)=8
```

- `work_len` = 该条最终命中候选数；**`work_len=0` 一律判 `SEARCHED_NO_RESULT`，并把五级检索词全写进 `search_terms`**（例：`首句前10字「天上月遥望似似是衬字」／首句前8字…／（全部落空）`），没有一条判成笼统的 `NO_MATCH`。

### 4.3 判态与门槛

```
sim = 1 - Σ编辑差异字数 / max(len(例词), len(作品))
lcs_ratio = 最长公共子串长度 / len(例词)   ← 按任务要求逐条报，写入 evidence
```

- `sim = 1.000` 且 0 异文 且 作者一致 且 同词牌 → `VERIFIED_EXACT`
- `0.95 ≤ sim < 1` 且异文清单完整 且 作者一致 且 同词牌 → `VERIFIED_VARIANT`
- `sim ≥ 0.95` 但作者不一致 → `AUTHOR_CONFLICT`
- `0.5 ≤ sim < 0.95` → `POSSIBLE_MATCH`
- 仅词牌/题名相合 → `TITLE_ONLY`
- 无候选（或候选全为无关命中）→ `SEARCHED_NO_RESULT`

**为什么不用 LCS 判态**：LCS 是连续子串，一处散点异文就把串切断。EX-0018（133 字，4 处异文）LCS 只有 53 字 = 0.40，而 sim = 0.9699；EX-0059 文本完全相同，若不转简 LCS 只有 0.552。LCS 仍逐条报出，但只作指标，不作判据。

### 4.4 计数

| 新状态 | 条数 |
|---|---|
| VERIFIED_EXACT | 9 |
| VERIFIED_VARIANT | 36 |
| POSSIBLE_MATCH | 16 |
| SEARCHED_NO_RESULT | 39 |
| TITLE_ONLY / AUTHOR_CONFLICT / NOT_SEARCHED | 0 |

转移：原 `NO_MATCH` 90 → EXACT 6 / VARIANT 29 / POSSIBLE 16 / NO_RESULT 39；原 `VERIFIED_VARIANT` 10 → EXACT 3 / VARIANT 7（10 条全部复现，无一被推翻）。

**原 NO_MATCH 被证实「未检索」的**：114 条 `NO_MATCH` 中 112 条 `work_id` 为空、`work_len=0`、无 score。本轮抽到的 90 条里，51 条（56.7%）实际能检索到高度一致文本，其中 35 条达 `VERIFIED_*`。

### 4.5 不确定处

1. **阈值 0.95 是保守选择**：16 条 `POSSIBLE_MATCH` 中 12 条 sim ≥ 0.90。若降到 0.90，`VERIFIED_VARIANT` 会增至 46。我不调阈值，避免把「像」写成「是」。
2. **2 条 sim = 1.000 却止于 POSSIBLE**：EX-0267、EX-0268，文本逐字全同，仅题名作「雜曲歌辭 宮中調笑」而例词词牌为「调笑令」，`cipai_specs` 无「调笑令」条，异名对不上。真实状态几乎必然是 EXACT，但我不凭记忆补词牌异名。
3. **同人合并只做了一例**：李煜/後主煜（库内两个 author_id）。这是人工判断，已在脚本 `SAME_PERSON` 显式声明。
4. **未复核 210 条**：其中原 `VERIFIED_EXACT` 50 条一条没抽，因此不能证明「逐字全同」这一档没有高估。
5. **例词文本自身有污染**：100 条中 25 条夹入 OCR 页码数字，8 条夹入「衬字/作平/去声」一类谱注（EX-0007 即因「衬字」二字污染检索词而五级全落空）。数字在归一化时被剔除，汉字注记则会影响检索——这类条目的 `SEARCHED_NO_RESULT` 不能简单读作「库内无文」。

---

## 5. G4：上古音 40 例证据审查

### 5.1 评分口径（7 要素，逐条只依输入文件已有信息）

| 要素 | 判 1 的条件 |
|---|---|
| E1 学者姓名 | `scholar` 有负责主体（个人，或署名的机构） |
| E2 著作/论文名 | `work_title` 具体可识 |
| E3 出版信息 | 出现「出版社＋年份」或「刊名＋年期」；只有刊名无年期记 0 |
| E4 页码/段落位置 | `locator` 给出 页/卷/条/章/段 等可定位单位；仅 URL 或明言「缺」记 0 |
| E5 对应诗句 | 引文标注篇/章名，或直接引原诗句；**只列韵脚字而不注所出篇记 0** |
| E6 韵脚字 | 具体列出韵脚字（非仅位置编号） |
| E7 韵部判断 | 引文给出古韵部名（幽部/阳部/之部…）；无部名记 0 |

门槛：≥5 → `CITATION_COMPLETE`；3–4 → `CITATION_PARTIAL`；≤2 → `UNVERIFIED_CITATION`。
语义标记：`claim_status=SCHOLAR_IDENTIFIED_RHYME` 而 E7=0 → `STATUS_SEMANTIC_CONFLICT`。

### 5.2 计数（22 条学者认定韵）

| 结果 | 条数 | 案号 |
|---|---|---|
| CITATION_COMPLETE | 14 | SJ-01、SJ-14、SJ-27、SJ-28、SJ-30、CC-01、CC-02、CC-04～CC-10 |
| CITATION_PARTIAL | 8 | SJ-03、SJ-04、SJ-06、SJ-07、SJ-08、SJ-09、SJ-10、SJ-11 |
| UNVERIFIED_CITATION | 0 | — |
| `STATUS_SEMANTIC_CONFLICT` | **9** | CC-01、CC-02、CC-04、CC-05、CC-06、CC-07、CC-08、CC-09、CC-10 |

要素分布：6/7 者 10 条、5/7 者 4 条、4/7 者 2 条、3/7 者 6 条。

### 5.3 与输入 `citation_status` 的差异

- **SJ-08、SJ-14、SJ-30 由 PARTIAL 升为 COMPLETE**：三者都是 5/7（SJ-08/14/30 均在「学者/书名/定位/韵脚/韵部」上齐，缺出版信息与页码）。按 5/7 门槛即为 COMPLETE，但实质可核性仍有限——SJ-08 表列 34 位只有 5 位在引文内，SJ-14 是 28 位中 8 位，SJ-30 是 75 位中 6 位。**这三条属「门槛判 COMPLETE、实质仍不足」，我在 note 中逐条写明。**
- **SJ-11 由 UNVERIFIED 升为 PARTIAL**：按要素计 4/7（有篇名、韵脚字、韵部，缺学者/出版/页码）。但它是「网站题解、无责任作者」，作为 `SCHOLAR_IDENTIFIED_RHYME` 的「学者」要件实质不成立。这一条是**门槛与语义打架**的典型，note 中已注明「若按 status 语义应另降」。
- **9 条 CC（蒋骥）全部 COMPLETE 但带语义冲突**：版本、ISBN、篇条、韵脚字、诗句定位俱在（6/7），唯一缺的是「韵部」——蒋骥《楚辞说韵》只分**韵段**（何字与何字相叶），不出古韵部名。把这种证据标成 `SCHOLAR_IDENTIFIED_RHYME`（韵部归属），是把「韵段位置」当成了「韵部判断」，属层级错置。

### 5.4 不确定处

1. **E5 的口径会改变结果**：我把「只列韵脚字、不注篇名」一律记 0。若审稿人认为「韵脚序列本身足以定位」，则 SJ-03/04/06/07/09/10 各加 1 分，其中 SJ-07（3→4）、SJ-09（3→4）仍在 PARTIAL，SJ-08 会由 4 升 5 变 COMPLETE——**SJ-08 是最敏感的一条**。
2. **出版信息的判定**：SJ-01 是政府教育局教材，只有机构名与 PDF 地址，无出版社/年期，我记 0。若把「教育局課程發展處」视同出版者，则 7/7。
3. **`publication` 栏**：输入文件没有这一列，我只能从 `source_text`/`note` 里已有的字串抄出（如「上海古籍出版社 2019 于淑娟点校本，ISBN 9787532591381」），**没有补造任何书名、刊名、年份、页码**。缺者一律写「（缺）」并注明缺什么。
4. **18 条非学者认定项**（13 条 POSSIBLE_RHYME_POSITION、5 条 LINE_END_CANDIDATE）记 `NOT_APPLICABLE`：它们从未宣称有学者依据，套 7 要素门槛会得出「0 分 = UNVERIFIED」的假严重性。CC-03 虽提及蒋骥，但 claim 是 LINE_END_CANDIDATE，同样记 NOT_APPLICABLE，并在 note 给出「若强行计分 2/7」的备查值。

---

## 6. 复现命令

```bash
cd <PROJECT_ROOT>/poetry-database
python3 reports/tasks/2026-11-16/R2-12/LOGS/gen_g1.py      # G1，约 2s
python3 reports/tasks/2026-11-16/R2-12/LOGS/gen_g2.py      # G2，约 1s
python3 reports/tasks/2026-11-16/R2-12/LOGS/gen_g3_v2.py   # G3，约 25s（载入 37.5 万条 works）
python3 reports/tasks/2026-11-16/R2-12/LOGS/gen_g4.py      # G4，纯读 CSV，<1s
```

四个脚本都不写数据库（只读 `works`/`ph_readings_r2_08`/`cipai_forms_r2_07`/`cipai_specs`/`author_alias`/`cipai_form_examples_r2_08`），不联网，输出固定 UTF-8-SIG CSV。
