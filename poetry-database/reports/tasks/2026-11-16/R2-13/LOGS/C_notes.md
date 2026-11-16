# C 组（作者身份复核）执行记录 — R2-13

工作目录：`<PROJECT_ROOT>/poetry-database`
数据库：`database/poetry.db`（SQLite，只读，本轮**未执行任何写库操作**）
产出目录：`reports/tasks/2026-11-16/R2-13/`

---

## 0. 前置核对

```sql
PRAGMA table_info(works);
PRAGMA table_info(authors);
PRAGMA table_info(author_alias);

SELECT 'works',count(*) FROM works
UNION ALL SELECT 'authors',count(*) FROM authors
UNION ALL SELECT 'alias',count(*) FROM author_alias
UNION ALL SELECT 'distinct author_name',count(DISTINCT author_name) FROM works
UNION ALL SELECT 'distinct author_canonical',count(DISTINCT author_canonical) FROM works;
```

结果：works 375,399 / authors 20,809 / author_alias 20,809 / distinct author_name 20,809 / distinct author_canonical 20,327。

补充核对：

```sql
SELECT count(*) FROM works WHERE dynasty IS NULL OR dynasty='';      -- 0
SELECT count(*) FROM works WHERE era     IS NULL OR era='';          -- 0
SELECT count(*) FROM works WHERE author_canonical IS NULL OR author_canonical='';  -- 1,894
SELECT dynasty,count(*) FROM works GROUP BY 1 ORDER BY 2 DESC;       -- 12 个取值（含「未定」694）
SELECT era,count(*)     FROM works GROUP BY 1 ORDER BY 2 DESC;       -- 14 个取值（含「先秦至隋」6,159）
SELECT collection,count(*) FROM works GROUP BY 1 ORDER BY 2 DESC;    -- 18 个总集
```

字段确认：`works.work_id / title_raw / title_norm / author_name / author_canonical / dynasty / era / collection / genre / text_raw / text_norm / char_count / source_id / record_locator` 均存在；`record_locator` 实际大量为空，本轮改用 `source_id` 作为来源证据。

工具：Python 3 + `opencc.OpenCC('t2s')`（繁→简），`sqlite3` 标准库，`csv` 手写（环境无 pandas）。

---

## C1 繁简/异体双写对复核

### C1.1 方法（两条独立路径）

**路径 A（字符层，本轮主口径）**：对 `works` 中每个不同的 `author_name` 做 `t2s`，按转换结果分组，组内原字不同的两两成对。

```sql
SELECT author_name,count(*) FROM works GROUP BY 1;   -- 20,809 行
-- 逐名 opencc t2s，再在 Python 里按 t2s 结果聚合
```

**路径 B（工具表层，复现 R2-12 的 442）**：

```sql
SELECT a.raw_name, a.canonical FROM author_alias a
WHERE a.kind='VARIANT_SIMP' AND a.raw_name<>a.canonical
  AND a.raw_name IN (SELECT author_name FROM works)
  AND a.canonical IN (SELECT author_name FROM works);
```

### C1.2 结果

| 口径 | 名字组 | 配对数 | 涉及 author_name | 涉及作品 |
|---|---|---|---|---|
| A：t2s 分组（组内两两组合） | **474 组** | **478 对** | 950 | 101,841（去重） |
| A′：组内 n−1 配对（2 个三元组各取 2 对） | 474 组 | **476 对** | 950 | 102,045（含重复计） |
| B：alias `VARIANT_SIMP` 且两侧均在 works | — | **442 对** | 884 | — |

组大小分布：`{2: 472, 3: 2}`。两个三元组分别是
`吴龙翰 / 吳龍翰 / 吴龍翰`（145/28/1）与 `张榘 / 张矩 / 張榘`（50/12/59）。

**A ⊇ B，且 B 的 442 对全部落在 A 的 478 对之内；A 比 B 多 36 对，B 比 A 多 0 对。**

### C1.3 36 对差集的成因（这 36 对是真实缺陷）

```sql
SELECT raw_name,canonical FROM author_alias WHERE raw_name IN ('张矩','張榘','曹勋','曹勛');
-- 张矩→张矩 / 張榘→張榘     （两侧各自被转成「另一个自己」，没并）
-- 曹勋→曹勋 / 曹勛→曹勛
```

alias 表的转换把这些异体字「只转了一半」，导致两侧 canonical 仍是两个值：

| 异体字对 | 例 | 说明 |
|---|---|---|
| 脩/修 | 张景修 / 張脩之→张脩之 | opencc 收 脩→修，alias 未收 |
| 榘/矩 | 张榘 / 张矩 | 同上 |
| 顔/颜 | 曾晞顔 / 曾晞颜 | 同上 |
| 虯/虬 | 東方虬 / 東方虯 | 同上 |
| 淩/凌 | 楊凌 / 楊淩 | 同上 |
| 藴/蕴、勛/勋、翬/翚、陞/升、皁/皂 | 曹希蕴/曹希藴、曹勋/曹勛、刘子翬/劉子翬、孫升/孫陞、劉皂/劉皁 | 同上 |

验证：

```sql
SELECT count(*) FROM (
  SELECT author_name, t2s_name FROM ... -- 21 对 canonical 未统一
);
```

C1 表中 `note` 列统计：**canonical 已统一 455 对，未统一 21 对**。这 21 对里就包含 `曹勋/曹勛`、`晁冲之/晁沖之`、`张景修/張脩之`、`王采/王寀`、`釋元淨/釋元凈`、`陳塤/陳壎` 等——同一位作者的作品被劈成两半，是本轮最实在的损害。

### C1.4 分类判定（规则与阈值）

判定顺序（先强证据，后弱证据）：

1. 文本重合 → `SAME_PERSON_CONFIRMED`
   取两侧 `text_norm` 前 30 字（并做 t2s）建集合求交，同时记录全文相同数、`title_norm` 相同数。
2. 一侧为 `无名氏/無名氏` → 按占位符处理。
3. 一侧朝代缺失或为「未定」→ `UNRESOLVED`。
4. 主导朝代相同 → `SAME_PERSON_SUPPORTED`。
5. 主导朝代相邻（先秦—汉魏—魏晋南北朝—隋—唐—五代—宋—金—元—明—清；宋—金、宋—元、金—元亦视为相邻）→ `SAME_PERSON_SUPPORTED`（跨代/遗民）。
6. 朝代互斥且相隔较远：
   - 少数侧 ≥3 条 → `DISTINCT_PERSON`
   - 少数侧 ≤2 条 → `UNRESOLVED`（无法区分同名异人与朝代误标）

### C1.5 分类计数

| verdict | 对数 | 说明 |
|---|---|---|
| `SAME_PERSON_CONFIRMED` | **33** | 有文本重合，例：`顾敻/顧敻` 13 条、`牛峤/牛嶠` 13 条、`韦庄/韋莊` 22 条、`孙光宪/孫光憲` 21 条、`温庭筠/溫庭筠` 20 条 |
| `SAME_PERSON_SUPPORTED` | **370** | 仅朝代一致/相邻 + 字符对应，无文本重合 |
| `DISTINCT_PERSON` | **7** | `张埴/張埴`、`李师中/李師中`、`吴栻/吳栻`、`吴山/吳山`、`王铎/王鐸`、`徐延寿/徐延壽`、`张元/張元`（两侧均 ≥3 条且朝代互斥） |
| `UNRESOLVED` | **66** | 朝代互斥但少数侧仅 1–2 条 |
| `COLLECTION_NAME` | 0 | 本轮配对中未出现类目名成对现象（类目名不参与繁简配对） |
| `NAME_VARIANT_ONLY` | 0 | 结构上不可能：能进配对的前提就是 t2s 同形，该档无独立判别力。差异字数分布：1 字 353 对、2 字 118 对、3 字 5 对（名字等长，无长度差） |

### C1.6 对 R2-12「442 对」的独立核实结论

**数字可复现，但不是真实对数，偏低 36 对。**

- 用 alias 表 `VARIANT_SIMP` 口径，确实得到 **442**（见 C1.1 路径 B），与 R2-12 一致。
- 但该口径依赖 alias 表自身的转换结果，而 alias 表对 10 类异体字（脩/修、榘/矩、顔/颜、虯/虬、淩/凌、藴/蕴、勛/勋、翬/翚、陞/升、皁/皂）只转了单边，导致 **36 对真实并存的写法没有进入 442**。
- 真实对数：**478 对 / 474 组 / 950 个 author_name / 约 101,841 条作品（占全库 27.1%）**。若按每组只取一条代表（n−1），为 **476 对**。
- 因此 R2-12 的结论「442 对」应改为「至少 478 对」，且其「已入表前 60 对」的抽样呈现方式会系统性漏掉混形条目（如 `张矩/張榘` 这类「简+繁混写」）。

### C1.7 根因：不是随机错字，是两套总集的字符规范不同

对 476 对逐一取两侧的主导 `collection`：

```sql
SELECT author_name,collection,count(*) FROM works GROUP BY 1,2;
-- 例：SELECT author_name,collection,count(*) FROM works WHERE author_name IN ('刘克庄','劉克莊') GROUP BY 1,2;
-- 刘克庄|songci|269    劉克莊|songshi|4553
```

结果：

| 配对形态 | 对数 |
|---|---|
| 两侧同属一个总集 | **21** |
| 两侧分属不同总集 | **455** |
| 其中 `songci ↔ songshi` | **343** |
| 其中 `wanqing ↔ songshi` | 30 |
| 其中 `wanqing ↔ mingshi` | 13 |

在 343 对 `songci ↔ songshi` 中，**340 对的简体形落在宋词一侧、繁体形落在宋诗一侧**（另 3 对是双侧均未变的异体字）。

结论：所谓「繁简双写」的主体，是**《全宋词》语料按简体入库、《全宋诗》语料按繁体入库**，同一位宋代作者在两套书里各出现一次。这不是抄录时的随机错字，而是**两个上游语料的字符规范冲突**。这条根因决定了两件事：

1. 这类配对**大概率真是同一人**（宋代作者往往诗词兼作），所以 R2-12 想合并的方向不算错；
2. 但**不能用字符规则去合并**——字符规则无法说明「为什么这 343 对的简体总在词一侧」，也无法排除 `张翰`（晋/清）这类同形异人。正确做法是回到「语料来源 + 身份证据」，即 C4 设计文档第 3 节的三条门槛。

这也解释了为什么 476 对里只有 33 对有文本重合：两侧多为**不同体裁**（词 vs 诗），作品本就不重叠，文本比对天然失效。

---

## C2 疑似非人名作者复核

### C2.1 方法

```sql
-- 1) 单字作者（同时供 C3 使用）
SELECT author_name,count(*) c FROM works WHERE length(author_name)<=1 GROUP BY 1 ORDER BY c DESC LIMIT 60;
SELECT count(*) FROM (SELECT DISTINCT author_name FROM works WHERE length(author_name)<=1);  -- 42

-- 2) 关键字符扫描
SELECT author_name,count(*) c FROM works
WHERE author_name LIKE '%歌辭%' OR author_name LIKE '%歌辞%' OR author_name LIKE '%曲辭%'
   OR author_name LIKE '%曲辞%' OR author_name LIKE '%諺%' OR author_name LIKE '%谣%'
   OR author_name LIKE '%謠%' OR author_name LIKE '%雜詩%' OR author_name LIKE '%杂诗%'
   OR author_name LIKE '%祠%' OR author_name LIKE '%鼓吹%'
   OR author_name LIKE '%無名%' OR author_name LIKE '%无名%' OR author_name LIKE '%闕名%'
   OR author_name LIKE '%佚名%' OR author_name LIKE '%失名%' OR author_name LIKE '%不詳%'
GROUP BY 1 ORDER BY c DESC;

-- 3) 总集/类目字段交叉
SELECT count(*) FROM works WHERE collection LIKE '%郊廟%';   -- 0
SELECT count(*) FROM works WHERE collection LIKE '%朝會%';   -- 0
SELECT count(*) FROM works WHERE collection LIKE '%歌辭%';   -- 0
SELECT count(*) FROM works WHERE title_raw LIKE '%郊廟%';    -- 477

-- 4) alias 表中的非人名标记
SELECT raw_name,canonical,kind,evidence FROM author_alias
WHERE kind IN ('NOT_PERSON','TEMPLE_NAME','STYLE_NAME');     -- 32 行

-- 5) 「名字同时是库内某作品标题」反查（用于发现诗题被当成作者）
SELECT DISTINCT title_norm FROM works WHERE title_norm<>'';
-- 在 Python 中对 len>=4 且 n_works>=3 的 author_name 做标题碰撞检测
```

### C2.2 关键核实：1,639 条到底是什么

```sql
SELECT author_name,count(*) FROM works
WHERE author_name LIKE '%郊%' OR author_name LIKE '%廟%' OR author_name LIKE '%朝會%' OR author_name LIKE '%歌辭%'
GROUP BY 1 ORDER BY 2 DESC;
-- 郊廟朝會歌辭 | 1639
-- 孟郊 | 534
-- 出郊抵東屯 | 22 ...

SELECT count(*) FROM works WHERE author_name='郊廟朝會歌辭';                       -- 1639
SELECT genre,count(*) FROM works WHERE author_name='郊廟朝會歌辭' GROUP BY 1;       -- 古体诗 1595 / 五律 38 / 七绝 4 / 五排 1 / 七律 1
SELECT title_raw FROM works WHERE author_name='郊廟朝會歌辭' LIMIT 3;
-- 建隆郊祀八首 降神用《高安》。 / 皇帝升降用《隆安》。 / 奠玉幣用《嘉安》。
SELECT source_id,count(*) FROM works WHERE author_name='郊廟朝會歌辭' GROUP BY 1;
-- CP-SONGSHI-250(276) / -251(1000) / -252(363)
```

**「1,639 条」作为条数是准确的；「被切成郊/廟/朝/會/歌/辭」是不成立的。**

- `author_name` 只有**一个值**：`郊廟朝會歌辭`（7 字全串），不是 6 个单字。
- 42 个单字作者的完整清单里**不含**郊、廟、朝、會、歌、辭任何一个（见 C3 表）。
- `collection` 字段里也**没有**「郊廟/朝會/歌辭」字样（各 0 条），作品全部来自 `songshi`（宋诗）的郊祀/朝会乐章卷。

因此 `GD-031` 的表述需修正为：「`author_name` 混入 1 个乐府类目字符串 `郊廟朝會歌辭`（1,639 条，来自宋诗郊庙乐章），并非单字切分」。

### C2.3 分类结果（`AUTHORS_1639_SUSPECTED_NONPERSON.csv`）

| classification | author_name 数 | 作品数 | 主要内容 |
|---|---|---|---|
| `ANONYMOUS` | 34 | 9,220 | 佚名 3,974 / 无名氏 3,254 / 無名氏 747 / 不詳 731（四种写法合计 8,706）；谚谣出处 42+23+15+14+4+3+2+1+1+1+1+1；祠庙 15+13+4+3+2+1+1+1；佚名＋剧名 304+48 |
| `COLLECTION` | 27 | 2,093 | 郊廟朝會歌辭 1,639、雜詩 133、鼔吹曲辭 44、昭徳凱容樂 43、鼓吹曲辭 35、月重輪行 27、清商曲辭 24、出郊抵東屯 22、斋中读书 17、歸田雜詠 17、紫騮馬歌 14、秋日雜詠 14、自君之出矣 13 等 |
| `PERSON` | 9 | 1,676 | 南戏署名黏连 6 种（高明《蔡伯喈琵琶记》377、柯丹邱《荆钗记》340、施惠《幽闺记》277、徐田臣《杀狗记》276、刘唐卿《白兔记》210、萧德祥《小孙屠》134）；帝号式 陳思王植 31、昭明太子 30；張祠部 1 |
| `UNKNOWN` | 2 | 17 | 《靖康小雅》作者 14（书名＋“作者”，本名失载）、上元夫人 3（传说人物名） |
| **合计** | **72** | **13,006** | 另有 `#TOTAL#` 汇总行 |

`INSTITUTIONAL` 未单独使用：本轮没有任何「机构/乐署」作为署名主体的实例（郊庙乐章虽属官方制作，但库内以类目名出现，故归 `COLLECTION`）。

### C2.4 R2-12 的「1,639 条」与「20 个 / 2,042 条」核实

- 「1,639 条」成立，但指向单一字符串 `郊廟朝會歌辭`（见 C2.2）。
- R2-12 列出的 20 个非人名值，本轮用 SQL 逐条复算合计 **2,042 条**，与该文一致（此前正文的加总核对无误）。
- 本轮把范围扩到 72 个值 / 13,006 条，是因为增加了四类 R2-12 未列入的对象：**南戏「人名＋剧名」黏连（8 个写法 / 1,966 条：具名 6 种 1,614 条 + 无名氏 2 种 352 条）**、**诗题/乐府旧题当作者（20 个写法 / 174 条）**、**帝号式署名（2 个 / 61 条）**、**祠庙名（8 个 / 40 条）**。

### C2.5 新发现（R2-12 未记）

1. **南戏署名黏连**：`高明《蔡伯喈琵琶记》`、`柯丹邱《荆钗记》` 等 8 种（含 2 种无名氏），共 1,966 条，`genre` 多为词/曲，来自同一批戏文。作者名与剧名之间无分隔符，任何按名字聚合都会把它们当成 8 个「人」。
2. **诗题当作者**：`出郊抵東屯`(22)、`月重輪行`(27)、`紫騮馬歌`(14)、`自君之出矣`(13)、`斋中读书`(17)、`舟中夜坐`(8) 等，标题与作者字段互换。
3. **`==…==` 标注包裹**：**287 个 author_name、2,607 条作品**（`SELECT count(DISTINCT author_name) FROM works WHERE author_name LIKE '==%=='`）。其中 11 个裸名同时独立存在（`==张度==`/`张度`、`==朱琦==`/`朱琦` 等），形成同一人被拆成两条。
4. **金元诗「姓＋官＋名」署名**：`蔡太常珪`(44)、`髙内翰士談`(28)、`馮内翰延登`(16)、`李承㫖晏`(5)、`孟内翰宗獻`(4)、`趙内翰可`(3)、`王先生予可`(5) 等。这些**是人名**，只是官衔夹在中间，不能按非人名清理。

---

## C3 42 个单字作者逐条审查

### C3.1 方法

1. 取全部单字 `author_name`（42 个）。
2. 对每个字 X，找出库内所有以 X 起首、长度 2–4 的候选全名。
3. **排除高频题名**（跨作者文档频率 ≥50，如 `句`1714、`句其一`667、`偈`279、`水调歌头`193 及各类词牌）后再比对题名，避免词牌造成的假重合。
4. 对候选做两项比对：`title_norm` 交集、`text_norm` 前 30 字交集。
5. 判定阈值：文本重合 >0，或题名重合 ≥3 且占候选侧 ≥30% → `TRUNCATED_SUSPECTED`；否则按情况落 `SURNAME_ONLY` / `UNRESOLVED` / `OCR_LOSS`。

### C3.2 结果

| verdict | 个数 | 代表 |
|---|---|---|
| `SURNAME_ONLY` | **31** | `向`(38)、`徐`(16)、`曾`(14)、`汪`(13)、`柳`(10)、`顧`(8)、`王`(7)、`韩`(6)、`景`(5)、`洽`(5)、`莫`(5)… |
| `TRUNCATED_SUSPECTED` | **5** | `洽`、`含`、`良`、`梵`、`紹`——**这 5 个字不是汉姓**，库内也没有以它们起首的完整人名，作品题名/文本与任何候选均无重合，判断为首字被截断或小传串位 |
| `UNRESOLVED` | **5** | `张`、`何`、`陳`、`黄`、`劉`（样本 1–2 条，无任何可比对候选） |
| `OCR_LOSS` | **1** | `□`（作者字段即缺字符号） |
| `GENUINE_SINGLE_CHAR_NAME` | **0** | 无一个能确证为真实单字名 |
| `SURNAME_ONLY` 以外的「姓氏＋官署」 | — | `張祠部` 不在单字表内，已归 C2 的 `PERSON` |

### C3.3 「张」的处置（按要求未改判）

```sql
SELECT author_name,count(*) FROM works WHERE author_name LIKE '张%' AND length(author_name)<=2;
SELECT author_name,count(*) FROM works WHERE author_name IN ('张昇','张昪','張昇','張昪');  -- 0 行
```

- 库内**不存在** `张昇/张昪/張昇/張昪`，R2-12 已否定「张→张昇」，本轮**维持 `UNRESOLVED`**，不改判。
- 新增证据：C5 抽检发现 `张` 名下《水调歌头》的 `text_norm` 前 30 字与 `朱熹` 名下作品**完全相同**，说明该条是他人作品误挂；但 4 条作品全部为词、题名仅词牌，无法据此反推本名，仍不足以给出全名。
- 结论：**42 个单字作者中，0 个能确证截断**，与 R2-12 一致；但 `洽/含/良/梵/紹` 5 例应升级为「极可能截断」，只是缺原始影像，不能定名。

---

## C5 200 作者 / 1000 作品关联抽检

### C5.1 抽样方法（随机种子 20261116）

```python
random.seed(20261116)
```

分层与池实际大小（互斥，按顺序抽取，后层排除前层已选）：

| 层 | 规则（SQL/条件） | 目标 | 实际 |
|---|---|---|---|
| 唐宋重要作者 | `dynasty ∈ {唐,宋}` 且 `work_count ≥ 20`，非单字、非 C2 非人名 | 60 | 60 |
| 同名跨代 | `DISTINCT dynasty ≥ 2`（排除「未定」）且 `work_count ≥ 3` | 20 | 20 |
| 有别名者 | `author_alias.kind <> 'SAME'`（VARIANT_SIMP/GLYPH/STYLE/TEMPLE）或名字带数字后缀 | 30 | 30 |
| 单字/疑似非人名 | C2 的 63 个非 PERSON 值 + 42 个单字 | 30 | 30 |
| 女性作者 | 名字含 `氏/女/妻/妾/夫人/皇后/妃/姬/媛/姝/娘/姑/妇` | 10 | 10 |
| 其余随机 | 上述之外随机 | 50 | 50 |
| **合计** | | **200** | **200** |

每作者按 `work_id` 排序后随机取 5 条：

```sql
SELECT work_id,title_raw,title_norm,author_canonical,dynasty,era,collection,genre,text_norm,source_id
FROM works WHERE author_name=? ORDER BY work_id;
```

**短供情况（如实记录）**：200 个作者中有 **88 个**作品数 <5（集中在单字/疑似非人名层，多数只有 1–3 条），初次抽取得 715 条；为达到 1,000 条唯一 `work_id`，按作者权重（作品多者优先）**补偿抽 285 条**，补偿行在 `audit_id` 序列中不与原行区分，但抽样方法在此备案。最终 **1,000 条、1,000 个唯一 work_id**。

### C5.2 检查项与判定

| 字段 | 判据 |
|---|---|
| `check_author_consistent` | `author_canonical` 为空→`FAIL_EMPTY`；等于 `t2s(author_name)`→`OK`；否则查 alias，有映射→`OK_VIA_ALIAS`，无→`FAIL_MISMATCH` |
| `check_title_in_body` | `title_norm`（≥4 字）原样出现在 `text_norm`→`FAIL_TITLE_IN_BODY`；作者名（≥2 字）出现在正文→`WARN_AUTHOR_IN_BODY` |
| `check_dynasty_match` | `era` 归并到朝代族后与 `dynasty` 比较；`先秦至隋/先秦至梁` 记为 `OK_BROAD_ERA` |
| `check_collection_match` | 总集→应属朝代映射（songshi→宋、tang→唐、wanqing→清、songci→宋、yuanqu→元、mingshi→明、gushiji→先秦/汉魏/魏晋南北朝/隋、zhongzhou→金、huajianji→唐/五代、wenxuan→宽、tang300→唐、shijing→先秦、nalan→清、tao→魏晋南北朝、chuci→先秦、nantang→五代、caocao→汉魏） |
| 附加 | `dynasty=未定`、作者名含标点/序号、标题 >40 字、标题含句读、同文本前 30 字出现在**其他 canonical** 名下、`genre=词` 无题 |

### C5.3 结果

| verdict | 条数 |
|---|---|
| `OK` | **945** |
| `ISSUE` | **32** |
| `REVIEW` | **23** |
| 合计 | 1,000 |

标记分布：

| flag | 条数 | 性质 |
|---|---|---|
| `EMPTY_CANON` | 15 | 全库 1,894 条 `author_canonical` 为空，抽样命中 15 条（谚谣/祠庙类为主） |
| `TEXT_DUP_OTHER` | **12** | **同一文本挂在不同 canonical 名下**，详见 C5.4 |
| `TITLE_PUNCT` | 9 | 标题含句读，题/文边界不清 |
| `TITLE_TOO_LONG` | 4 | 标题 49–103 字，明显是正文被当成标题 |
| `AUTHOR_IN_BODY` | 3 | 作者名出现在正文（小传串入） |
| `TITLE_IN_BODY` | 1 | 标题原样出现在正文 |
| `BROAD_ERA` | 18 | `era` 为「先秦至隋」等宽口径，非错误但不能用于朝代判定 |
| `FAIL_COLLECTION_DYNASTY` | **0** | 见 C5.5 的重要限制 |

### C5.4 抽检发现的主要问题类型

1. **跨作者同文重复 / 误挂（最严重）**
   `于鄴` 名下 4 首（王將軍宅夜聽歌、友人亭松、感懷、遊中梁山）与 `于武陵` 名下文本完全相同——二人实为同一人（于武陵名邺），库内未登记别名。
   `米芾`《太白江油尉廳詩》与 `李白` 名下同文；`孟貫`《冬日登江樓》与 `曹松` 同文；`鄭性之`《梅花》与 `刘克庄` 同文；`白元鑒`《藥圃》与 `白珽` 同文；`张`（单字）《水调歌头》与 `朱熹` 同文。
   **全库量化**：`text_norm` 前 30 字分组后，**1,678 组、3,418 条作品**的同一文本出现在 ≥2 个 canonical 名下（占全库 0.91%）。这是身份归并之外的一条独立污染线。
2. **多人合署被当成单人**
   `杜衍`《聯句》同文亦见 `韩维/谢绛/韩绛`；`魏徵`《享太廟樂章 肅和》同文亦见 `魏征、褚亮`。
3. **标题/正文边界失效**
   `程俱` 标题 51 字、`杜衍` 标题 103 字、`趙若琚` 标题 49 字——正文首句被并进标题。
4. **`author_canonical` 空缺**
   1,894 条无 canonical，集中在谚谣、祠庙、类目类署名，与 C2 的 `ANONYMOUS` 高度重叠。
5. **单字作者确认是「他人作品误挂」而非本人**
   见 C3.3 的 `张`↔`朱熹`。

### C5.5 重要限制：`check_collection_match` 近乎恒真

```sql
SELECT collection,dynasty,count(*) FROM works GROUP BY 1,2 ORDER BY 1,3 DESC;
-- songshi→宋(252,884)、tang→唐(55,308)、wanqing→清(19,864)、songci→宋(18,794)、
-- yuanqu→元(10,685)、mingshi→明(7,641)、zhongzhou→金(2,066)、shijing→先秦(305) …
```

18 个 `collection` 与 `dynasty` 基本一一对应（仅 `gushiji` 跨先秦/汉魏/魏晋南北朝/隋/未定，`wenxuan` 跨先秦/汉魏/魏晋南北朝/未定）。**这说明 `works.dynasty` 极可能就是从总集推出来的，不是独立证据。** 因此 `check_collection_match` 通过率高**不能**当成「朝代正确」的证据，同理 C1 里以 dynasty 为依据的 370 对 `SUPPORTED` 也只能算弱证据。这一点已写入 C4 设计文档的证据门槛（第 2 条注明「朝代不得是从 collection 反推的」）。

---

## 6. 无法判定的条目与原因（汇总）

| 位置 | 条数 | 原因 | 处置 |
|---|---|---|---|
| C1 `UNRESOLVED` | 66 对 | 朝代互斥但少数侧仅 1–2 条，分不清「同名异人」与「朝代误标」 | 保持原样，不合并 |
| C1 `DISTINCT_PERSON` | 7 对 | 两侧均 ≥3 条且朝代远隔 | 明确不合并 |
| C1 canonical 未统一 | 21 对 | alias 转换不完整 | 登记为候选，不落地 |
| C2 `UNKNOWN` | 2 个 / 17 条 | `《靖康小雅》作者`、`上元夫人` 无身份线索 | 待原始书页 |
| C3 `UNRESOLVED` | 5 个 | 样本 1–2 条，无任何比对候选 | 待原始影像 |
| C3 `TRUNCATED_SUSPECTED` | 5 个 | 非汉姓单字，疑首字被截断 | 待原始影像定名 |
| C5 `EMPTY_CANON` | 15 条（全库 1,894） | 无 canonical 可比 | 需先定 `NOT_A_PERSON` |
| C5 `TEXT_DUP_OTHER` | 12 条（全库 3,418） | 同文多挂，无法在库内判定谁是原作者 | 需外部别集/总集校勘 |

合计无法定论：**C1 66 对 + C3 10 个作者 + C2 2 个 + 19 个数字后缀作者 + 5 组合署**。这些一律记为未决，**没有为了凑数改判**。

---

## 7. 本轮未做的事

- 未修改 `works` / `authors` / `author_alias` 任何一行（全部操作只读）。
- 未执行任何 canonical 回写、未合并任何 identity。
- 未把 `DISTINCT_PERSON` 的名字做拆分（那需要拆 works，属于写操作）。
- 未处理 `record_locator` 为空的溯源问题（属 D 组范围）。

---

## 8. 产出文件清单

| 文件 | 行数 | 内容 |
|---|---|---|
| `AUTHORS_442_VARIANT_PAIRS.csv` | 476 | 繁简/异体双写对，含文本重合与 canonical 状态 |
| `AUTHORS_1639_SUSPECTED_NONPERSON.csv` | 72 + 1 汇总行 | 非人名/匿名/类目署名 |
| `AUTHORS_42_SINGLE_NAME_AUDIT.csv` | 42 | 单字作者逐条审查 |
| `AUTHORS_CANONICAL_IDENTITY_DESIGN.md` | — | 身份模型与合并门槛 |
| `AUTHORS_200_PERSON_1000_WORK_AUDIT.csv` | 1,000 | 200×1000 关联抽检 |
| `AUTHORS_IDENTITY_MAPPING_R2_13.csv` | 900 | 身份映射候选（全部 `CANDIDATE`，不落地） |
| `AUTHORS_UNRESOLVED_IDENTITIES.csv` | 101 | 未决身份与所需证据 |
| `LOGS/C_notes.md` | — | 本文 |

全部 CSV 使用 `utf-8-sig` 编码。
