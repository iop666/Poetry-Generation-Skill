# D 组（作者身份独立复核）执行记录 — R2-14

工作目录：`<PROJECT_ROOT>/poetry-database`
数据库：`database/poetry.db`（SQLite，**只读**；本轮未执行任何 INSERT/UPDATE/DELETE/CREATE）
产出：`reports/tasks/2026-11-16/R2-14/`
角色：independent reviewer（对 R2-13 的 C 组结论做逐项复核，不沿用其分类）

---

## 0 前置核对

```sql
PRAGMA table_info(works);      -- 38 列，含 author_name / author_canonical / dynasty / era / collection / source_id
PRAGMA table_info(authors);    -- 8 列：author_id,name,dynasty,era,work_count,collections,auto_meta,note
PRAGMA table_info(author_alias); -- 5 列：raw_name,canonical,kind,evidence,auto

SELECT 'works',count(*) FROM works
UNION ALL SELECT 'authors',count(*) FROM authors
UNION ALL SELECT 'alias',count(*) FROM author_alias
UNION ALL SELECT 'distinct author_name',count(DISTINCT author_name) FROM works
UNION ALL SELECT 'distinct canonical',count(DISTINCT author_canonical) FROM works;
```

结果：works **375,399** / authors **20,809** / alias **20,809** /
distinct author_name **20,809** / distinct canonical **20,327**。

三项独立复算全部与 R2-13 一致。

```sql
SELECT kind,count(*) FROM author_alias GROUP BY 1;
-- SAME 11,382 / VARIANT_SIMP 9,389 / NOT_PERSON 18 / TEMPLE_NAME 11 / VARIANT_GLYPH 6 / STYLE_NAME 3
SELECT auto,count(*) FROM author_alias GROUP BY 1;   -- auto=1: 20,809（全部机器生成）
```

### 0.1 关键事实一：`authors.note` 20,809 行完全相同

```sql
SELECT note,count(*) FROM authors GROUP BY 1;
-- 作者朝代由所属集合先验推导，未与史传核对 | 20809
```

**这是本轮最重要的单条证据**：作者朝代无一经史传核对，全部由 `collection` 推出。
故 `dynasty` 在任何一对的判定中都不能算身份证据（R2-13 的 370 对因此不成立）。

### 0.2 关键事实二：R2-13 声称"未写库"，但库内留有 R2-13 后缀表

```sql
SELECT count(*) FROM work_author_variant_r2_13;   -- 476
```

`work_author_variant_r2_13`（476 行，字段与 `AUTHORS_442_VARIANT_PAIRS.csv` 完全对应）、
`work_text_revision_candidates_r2_13`、`yuanqu_text_audit_r2_13` 三张表存在于库内。
R2-13 的 `LOGS/C_notes.md` 第 7 节称"未修改 works/authors/author_alias 任何一行"，
严格说与事实不符（至少 C 组产物已物化为表）。**本轮仅登记，不改动。**

### 0.3 关键事实三：`authors.author_id` 是名字的哈希，不是身份 id

```python
sha1('佚名')[:10] -> '3fe1b0858b' == authors.author_id('A:3fe1b0858b')   # 20,809 行全部成立
```

```sql
SELECT count(*) FROM works WHERE author_id IS NULL OR author_id='';   -- 0
SELECT count(DISTINCT author_id) FROM works;                          -- 20,809
SELECT count(*) FROM works w LEFT JOIN authors a ON w.author_id=a.author_id
 WHERE a.author_id IS NULL;                                           -- 0
```

即 `author_id = 'A:' + sha1(name)[:10]`，**同名同 id，跨总集自动合并**。
这解释了为什么 20,809 = 20,809 = 20,809 三个数字完全相等：`authors` 表不是一个独立人物库，
而是 `works.author_name` 的哈希索引；`author_id` 里不含任何身份判断，**它只是名字的另一种写法**。
任何"按 author_id 聚合作者"的统计，实际都是"按名字字符串聚合"。
（此条由 general-purpose-1 提示、本轮独立验证；D6 因此另立 `AE-` 前缀的实体 id。）

### 0.4 关键事实四：`authors.dynasty` 既非史传、亦非多数票，且生成逻辑不可完全复原

先确认两件确定的事：

1. **不是该行作品的多数朝代**（反例见下表）；
2. **不是史传值**（§0.1 的 note 已声明）。

能部分复现的经验规律：

```
「取 collections 字符串字典序首位总集的朝代」-> 20,809 行中成立 20,270（97.4%），例外 539
（例：songci,yuanqu→songci→宋；tang,tang300→tang→唐）
```

但**539 行连这条也不符**，其中前 400 例再查：只有 207 例等于其作品的多数朝代，**193 例连多数都不是**：

| 作者 | authors.dynasty | 作品朝代分布 | 说明 |
|---|---|---|---|
| 王珪 | **唐** | 宋 430 / 唐 2 | collections=`songshi,tang`，字典序首为 songshi 应得宋，实际得唐——**连经验规则也不符** |
| 王融 | **唐** | 魏晋南北朝 62 / 唐 1 | collections=`gushiji,tang`，同样不符 |
| 張齊賢 | **唐** | 宋 8 / 唐 2 | |
| 佚名 | 先秦 | 魏晋南北朝 1,798 / 未定 561 / 先秦 418 | 多数是魏晋南北朝，标先秦 |

**结论（三条都要保留，缺一条就会被反例推翻）**：
① 不是史传值；② 不是作品多数票；③ 与 collections 强相关（97.4% 可用"字典序首集"复现），
但 5.2% 的行连这条也不服从，**生成逻辑不可完全复原**。
因此 `authors.dynasty` 不能用于任何"某朝代有多少作者"的统计——那必须逐作品取 `works.dynasty`。

（此条由 general-purpose-3 提出"按 (name,dynasty) 计数"后查证；王珪作为"字典序规则反例"由其指出，
故本文不把规则写死为字典序。）

### 0.5 分析用缓存

`t2s` 转换需在 Python 侧完成，为免反复全表扫描，建了一份**库外**缓存
`/tmp/r214_cache.db`（`work_id,author_name,author_canonical,dynasty,collection,genre,title_raw,title_norm,source_id,seq,t30,tfull`，
375,399 行，77 秒）。原库只读打开，未写入。所有结论均可用下文 SQL 在原库复现。

---

## D1 476 对逐项复核

### D1.1 两个口径先复算

```python
# 路径 A：按 opencc t2s 结果分组
SELECT author_name,count(*) FROM works GROUP BY 1;   # 20,809
# 逐名 t2s 后聚合 -> 474 组，组大小 {2:472, 3:2}
#   组内两两组合 = 478 对；组内 n-1 = 476 对
```

```sql
-- 路径 B：复现 R2-12 的 442
SELECT raw_name,canonical FROM author_alias
WHERE kind='VARIANT_SIMP' AND raw_name<>canonical
  AND raw_name IN (SELECT author_name FROM works)
  AND canonical IN (SELECT author_name FROM works);   -- 442
```

复算结果：474 组 / 478 对 / n−1 = **476 对** / 别名口径 **442 对**，与 R2-13 完全一致。

### D1.2 33 条 `SAME_PERSON_CONFIRMED` 的重审方法

对每一对：

1. 取两侧全部 `work_id,title_raw,collection,genre,dynasty,source_id,text_norm`；
2. 以 `t2s(text_norm)[:30]` 为键求交，得到重合组数与具体作品对；
3. 对每个重合组判定三件事：
   - **是否同一首诗**：比较全文（t2s 后）是否逐字相同；结果 33 对的全部重合组都是同一首诗，
     **没有一组属于"前 30 字巧合"**；
   - **是否跨总集**：两侧 `collection` 是否不同；
   - **是否有第三作者争夺**：该 30 字正文是否同时出现在第三个 `author_canonical` 名下；
4. 查独立证据：`authors.note`（全同，无）、`author_alias.kind/evidence`（均为"繁简归并"）、
   别集字段（`sources.collection` 里 `nalan/caocao/tao` 三个别集）、题署、编者注（库内无此字段）。

### D1.3 重审结论：33 → 0

| 原判 | 复审核定 | 对数 | 依据 |
|---|---|---|---|
| `SAME_PERSON_CONFIRMED` | `SAME_PERSON_SUPPORTED` | **30** | 文本重合成立，但**都是同一首诗被两个总集各收一次**；无 A/B 级文献证据 |
| `SAME_PERSON_CONFIRMED` | `NAME_VARIANT_ONLY` | **2** | 重合文本被第三位作者争夺，不能独立指向本对 |
| `SAME_PERSON_CONFIRMED` | `UNRESOLVED` | **1** | 两侧都是佚名占位，不是人 |
| `SAME_PERSON_VERIFIED` | — | **0** | 无一对满足"史传/别集题署"或"编者注" |

**为什么"同一首诗在两总集重复收录"不能算身份证据**：
该重复本身就是产生 476 对的同一条流水线造成的——《全宋词》按简体入库、《全宋诗》按繁体入库，
同一首诗在两库各存一份。用"两库同诗"证明"两名同人"，等于用同一条流水线的两段输出互证。
故 33 对全部降级，只保留 C 级（跨总集同文）描述。

**两对降为 `NAME_VARIANT_ONLY` 的实证**：

```sql
-- 王谌/王諶：重合的渔父词同时署在薛嵎名下
SELECT author_name,title_raw,collection FROM works WHERE text_norm LIKE '%渔父%' AND author_name IN ('王谌','王諶','薛嵎');
-- 王諶|嘉熙戊戌季春一日畫溪吟客王子信爲亞愚詩禪上人作漁父詞七首  其五|songshi
-- 薛嵎|漁父詞七首  其五|songshi
-- 王谌|渔父词・渔父|songci

-- 劉皂/劉皁：長門怨同时署在齊澣名下
SELECT author_name,title_raw,collection FROM works WHERE title_raw LIKE '%長門怨%' AND author_name IN ('劉皂','劉皁','齊澣');
-- 劉皁|相和歌辭 長門怨|tang   劉皂|長門怨三首 二|tang   齊澣|長門怨|tang
```

**两对同集重出（非跨总集）**：`韩愈/韓愈`（相和歌辭 猛虎行 vs 猛虎行，同在 tang，
来源片 CP-TANG-02 / CP-TANG-19）、`東方虬/東方虯`（昭君怨三首 三 vs 相和歌辭 王昭君三首 三，
同在 tang，CP-TANG-06 / CP-TANG-02）。这两对的重合发生在**同一部《全唐诗》内部**
（乐府类卷与诗人卷重出），比跨总集更弱，只能算"同一本书用了两种写法"。

### D1.4 476 对全量改判规则（写入 CSV 的 `reason`）

判定顺序（前一条命中即止）：

| # | 条件 | revised_verdict |
|---|---|---|
| 1 | 任一侧为佚名占位（佚名/无名氏/無名氏/不詳/缺名/失名） | `UNRESOLVED`（NOT_A_PERSON） |
| 2 | 任一侧以"姓+氏"结尾（张氏/刘氏…） | `UNRESOLVED`（家族通称，非一人） |
| 3 | 有文本重合且**有第三作者争夺** | `NAME_VARIANT_ONLY` |
| 4 | 有文本重合、无第三作者 | `SAME_PERSON_SUPPORTED`（注明跨总集/同集重出） |
| 5 | 无文本重合；小样本侧内部混朝代且与对侧主导朝代重叠 | `UNRESOLVED`（raw_name 已混人） |
| 6 | 无文本重合；两侧时代互斥且各 ≥3 条 | `DISTINCT_PERSON`（意为"不可合并"） |
| 7 | 无文本重合；两侧时代互斥但少数侧 <3 条 | `UNRESOLVED` |
| 8 | 其余（时代一致或相邻） | `NAME_VARIANT_ONLY`（朝代是推导值，仅余字形） |

### D1.5 全量结果

| revised_verdict | 对数 |
|---|---|
| `SAME_PERSON_VERIFIED` | **0** |
| `SAME_PERSON_SUPPORTED` | **30**（28 跨总集 + 2 同集重出） |
| `NAME_VARIANT_ONLY` | **366** |
| `DISTINCT_PERSON` | **5** |
| `UNRESOLVED` | **75**（64 样本过少 + 8 某氏 + 2 侧内混人 + 1 佚名） |

改判矩阵（R2-13 → R2-14）：

```
CONFIRMED 33  → SUPPORTED 30 / VARIANT_ONLY 2 / UNRESOLVED 1
SUPPORTED 370 → VARIANT_ONLY 364 / UNRESOLVED 6
DISTINCT   7  → DISTINCT 5 / UNRESOLVED 2
UNRESOLVED 66 → UNRESOLVED 66
```

`DISTINCT_PERSON` 的 7 → 5，减掉的两对是 `张埴/張埴`、`李师中/李師中`：

```sql
SELECT author_name,dynasty,collection,count(*) FROM works WHERE author_name='张埴' GROUP BY 1,2,3;
-- 张埴|宋|songci|1    张埴|清|wanqing|2      <- 一个 raw_name 里混了两个人
```

即：这两对不是"两个人"，而是**一个 raw_name 已被两个时代的人污染**，故不能判 DISTINCT，
只能记 UNRESOLVED 并标注"需先拆 works"。

### D1.6 由此新增的结构性发现

476 对里有 **73 对**（75 − 2 混人）是"简体侧在晚清诗、繁体侧在唐宋诗"，
本质是**同名异人**而非写法差异。这说明 `t2s` 分组产出的是"字形候选"，不是"同人候选"。
此点已写入 D6 设计文档第 1.2 节。

### D1.7 库内其实有 20 条带外部证据的别名记录，但一条也不覆盖 476 对

```sql
SELECT raw_name,canonical,kind,evidence FROM author_alias
WHERE kind IN ('VARIANT_GLYPH','STYLE_NAME','TEMPLE_NAME');
-- TEMPLE_NAME 11 / VARIANT_GLYPH 6 / STYLE_NAME 3  = 20 条
```

其中 `楊皇后→杨桂枝` 注明"据《宋史·后妃传》"、`張茂先→张华` / `陳思王植→曹植` /
`陶淵明→陶潜` 注明"据李善注／本传归姓名"，属真正的 A 级证据。
但这 20 条覆盖的名字（傅𤣥、呉均、王襃、荀㫤、髙帝、鮑照、陶淵明、陳思王植、張茂先、
元帝、則天皇后、太宗皇帝、宣宗章皇帝、德宗皇帝、明皇帝、昭明太子、楊皇后、武帝、簡文帝、高宗皇帝）
**没有一个落在 476 对之内**——因为 476 对全是"同形/近形"对，而这些人靠的是"异名"（字号、帝号）。

这恰说明：现有 alias 表里"有证据的那一小撮"和"需要判断的那一大片"是**两个不相交的集合**。
476 对的判定不能从 alias 表借证据。

---

## D2 73 与 72 的差额

### D2.1 复算

```python
rows = csv.DictReader('AUTHORS_1639_SUSPECTED_NONPERSON.csv')   # 73 行
Counter(r['classification']) = {ANONYMOUS:34, COLLECTION:27, PERSON:9, UNKNOWN:2, '':1}
```

第 73 行的 `author_name` 是 `#TOTAL#`，`n_works=13006`，`classification` 为空。

```python
sum(n_works for 72 names) == 13006 == #TOTAL#.n_works    # True
```

**结论：不存在"少一个名字"。** 73 = 72 个名字 + 1 行合计。R2-13 的分类合计 72 本身就是对的，
差额来自"把汇总行也当成了一条记录"。72 个名字的作品数之和 13,006 与汇总行完全吻合，逐名复算
`SELECT count(*) FROM works WHERE author_name=?` **0 处不符**。

### D2.2 但 R2-13 的 72 个名字本身漏了 4 个

用关键词全库扫描（`諺|謠|谣|谚|廟|庙|祠|歌辭|曲辭|樂章|《|雜詩|雜詠|無名|佚名|失名|不詳|缺名`）：

```sql
SELECT author_name,count(*) FROM works WHERE author_name IN ('缺名','暮雨谣三叠','清江道中','西湖竹枝詞') GROUP BY 1;
-- 缺名|39  暮雨谣三叠|6  清江道中|2  西湖竹枝詞|2
```

| 名字 | 条数 | 分类 | 判定依据 |
|---|---|---|---|
| `缺名` | 39 | ANONYMOUS | 与"不詳/失名"同义的佚名占位，全在 全唐诗（五言白话诗等）；R2-13 的 4 个佚名写法清单里没有它 |
| `暮雨谣三叠` | 6 | COLLECTION | 晚清诗源把集名/书名写进 author；名下是龚自珍《汉朝儒生行》《咏史》《寒月吟》 |
| `清江道中` | 2 | COLLECTION | 晚清诗源同类缺陷（早行有感、汾州道中） |
| `西湖竹枝詞` | 2 | COLLECTION | 明诗源同类缺陷（題水仙花、春曉） |

故真实非人名 raw_name 数为 **76**，不是 72。R2-13 的 13,006 条也应修正为 13,055 条。

### D2.3 另外两个低置信候选（未计入 76）

`SELECT ... WHERE length(author_name)>=4 AND author_name IN (SELECT DISTINCT title_norm FROM works)` 命中 25 个，
其中 11 个不在 72 内。逐条看，9 个是人名（`蔡太常珪`、`髙内翰士談`、`馮内翰延登`、`李承㫖晏`、
`孟内翰宗獻`、`趙内翰可`、`王先生予可`、`司馬相如`、`洞庭老人`），
另 2 个 `清江道中`、`西湖竹枝詞` 已计入。故标题碰撞法未再增加候选。

---

## D3 1,639 条「郊廟朝會歌辭」

### D3.1 原始 JSON 逐条回查

```python
# sources.local_path: raw/poetry/songshi/poet.song.{249000,250000,251000}.json
# 命中 author=='郊廟朝會歌辭' 的条目 = 1,639
# 标题多重集 Counter(raw titles) == Counter(works.title_raw)   -> True
# 只在库内 / 只在原始文件 的标题数 = 0 / 0
```

**A. 该值的上游原貌**：原始 JSON 的 `author` 字段**原值就是 `郊廟朝會歌辭`**（七个字整串），
不是导入时拼出来的，不是从标题切的，也不是某位编者。
（另核对：全库 25 万条宋诗原始记录的 author 里，长度≥5 且含"辭/樂章/頌/曲"的值**只有这一个**，
说明它不是散见的脏值，而是一个成块的类目。）

**B. 位置与连续性**：249000 片第 724 条开始，250000 整片 1,000 条，251000 片第 0–362 条，
**连续 1,639 条无间断**，前后分别是 `宋恭宗`（在燕京作/鸚鵡）与 `元符…` 类乐章。这是《全宋诗》
"郊廟朝會歌辭"这一乐府类目整节被写进 `author` 的结果。

**C. 字段语义 = 总集类目名（COLLECTION label），不是人名、不是编者、不是匿名**：

- 标题一律为"<年号/行礼场合> <N>首 <仪节>用《<曲名>安》。"，如
  `建隆郊祀八首 降神用《高安》。`、`紹興親享明堂二十六首 太宗位酌獻用《韶安》。`；
- 1,234 条标题含"用《…》"，其余 405 条为同节的"降壇/還位/再詣盥洗"等仪节名，同属乐章；
- 标题中的 `建隆/紹興/熙寧/淳化` 是**年号**（标乐章的年代），`寧宗/高宗` 是**庙号**（标行礼之君），
  都不是署名人；
- 1,639 条全部来自 songshi，`genre` 以古体诗为主（1,595），与"乐章"体裁相符。

### D3.2 不得改成编者

《全宋诗》该节的编纂者无个体署名，库内也无任何编者字段。把它改挂到任何一位编者（如馆臣）
都是凭空造作者。正确处置是 `collection_role.role_type='COLLECTION'`，
`section_label='郊廟朝會歌辭'`，`target_collection='songshi'`。

### D3.3 输出

`AUTHOR_1639_COLLECTION_LABEL_AUDIT.csv`，1,639 行，逐条给出
`work_id/title_raw/collection/genre/dynasty/source_id/source_url/is_ritual_ode/real_author_in_title/author_field_semantics/verdict`。
`is_ritual_ode` 全 TRUE；`real_author_in_title` 全 NO（并标出命中的年号/庙号）；
`verdict` 全 `NOT_A_PERSON:COLLECTION_SECTION_LABEL`。

### D3.4 顺带发现的溯源缺陷（不在本轮修）

```sql
SELECT source_id,url FROM sources WHERE source_id='CP-SONGSHI-250';
-- https://…/chinese-poetry@master/全唐诗/poet.song.249000.json
```

`collection='songshi'` 的 `sources.url` 路径段写的是 `全唐诗`（上游仓目录名如此）。
URL 可用，但**路径标签与内容不符**，任何按 URL 判断总集的下游逻辑都会误判。已在报告中登记。

---

## D4 442 与 476 的差

### D4.1 集合运算

```python
set476 = {frozenset((simplified_name, traditional_name)) for CSV 476 行}   # 476
set442 = {frozenset(p) for alias VARIANT_SIMP 且两侧都在 works}            # 442
len(set476 - set442) = 35      # 476 独有
len(set442 - set476) = 1       # 442 独有
净差 = 35 - 1 = 34             # 正好是 476 - 442
```

### D4.2 35 对"476 独有"的成因（异体字转换单边）

按两侧 `author_alias.kind` 分布：

| kind 组合 | 对数 | 含义 |
|---|---|---|
| VARIANT_SIMP / VARIANT_SIMP，但 canonical 不同 | 20 | 两侧各自被转成不同 canonical（`張鎡→张镃`、`张鎡→张镃` 看似同，但 `歐陽炯→欧阳炯`、`欧陽炯→欧陽炯` 不同） |
| SAME / SAME | 10 | alias 判定"原样、无需转换"，实为异体（`曹勋/曹勛`、`晁冲之/晁沖之`、`王寀/王采`） |
| SAME / VARIANT_SIMP | 4 | 一侧未转、一侧转了，未对齐 |
| VARIANT_SIMP / SAME | 1 | 同上，反向 |

异体字类：`脩/修`、`榘/矩`、`顔/颜`、`虯/虬`、`淩/凌`、`藴/蕴`、`勛/勋`、`翬/翚`、`陞/升`、`皁/皂`，
另加混形（`歐/欧`、`張/张` 只转半边）。这些对**真实存在两种写法**，R2-12 的 alias 口径漏掉了它们。

### D4.3 1 对"442 独有"的成因（n−1 去重副作用）

```
吴龍翰(28) 吴龙翰(1) 吳龍翰(145)   -> t2s 后同组三元组，3 对只取 2 对
被舍弃的是 吴龍翰/吴龙翰(28/1)
（另一组 张榘(50)/张矩(12)/張榘(59) 同理，舍弃 张榘/张矩）
```

alias 表把 `吴龍翰→吴龙翰` 判为 VARIANT_SIMP，故 442 里有这一对；但 476 采用"每三元组只留 2 对"，
把它舍掉了。**这不是数据差异，是配对去重规则差异。**

### D4.4 结论

`AUTHOR_442_476_DIFFERENCE.csv` 36 行 = 35 对"476 独有" + 1 对"442 独有"，
`direction` 列标 +1/−1，`net_delta_if_summed` 求和 = +34，与 476−442 相符。
两个数字都对，但**口径不同**：442 是"别名字典生效的对"，476 是"字形分组的去重对"。
若以"真实并存的写法"为准，应为 **478 对**（474 组两两组合），442 与 476 都是它的子集/压缩。

---

## D5 1,678 组跨作者同文（深查 162 组）

### D5.1 口径复现（含阈值敏感性）

```sql
-- 以 t2s(text_norm) 前 30 字为组键，要求组内 canonical 数 ≥2
SELECT t30,count(*) n,count(DISTINCT author_canonical) na
FROM w WHERE length(t30)>=20 GROUP BY t30 HAVING na>=2;
-- 1,678 组 / 3,418 条   ← 与 R2-13 一致
```

**注意：1,678 依赖一个未写明的长度阈值 20。**

| 阈值 `length(t30)>=` | 组数 | 条数 |
|---|---|---|
| 10 | 1,747 | 3,557 |
| 16 | 1,688 | 3,439 |
| 18 | 1,679 | 3,420 |
| **20** | **1,678** | **3,418** |
| 22 | 1,495 | 3,034 |

即该数字对阈值敏感（≥10 时多 69 组），R2-13 未记录阈值。本轮沿用 20 并在文件头注明。

### D5.2 分类定义（本轮自定，写入 CSV `evidence`）

| hypothesis | 判定条件 |
|---|---|
| `WRONG_AUTHOR_FIELD` | 含非人名署名；或作者名恰为他条标题；或**同一总集**内同文全文一致却系于不同作者（至少一条错）；或禅偈互见（≥3 僧同署） |
| `SAME_WORK_MULTI_COLLECTION` | **跨总集**、全文逐字一致 |
| `VARIANT_TEXT` | 跨总集或同总集，相似度 0.75–0.999（异文） |
| `IMPORT_DUPLICATE` | 联句按联署人各建一条；或库内已知别名（于鄴/于武陵）同文重出 |
| `SAME_TITLE_DIFF_TEXT` | 同题但全文相似度 <0.75（两首不同作品） |
| `UNKNOWN` | 异题且相似度 <0.75；无法归类 |

相似度用 `difflib.SequenceMatcher(None,t1,t2).ratio()`，多成员取最大两两相似度。

### D5.3 全量分布与抽样

| hypothesis | 全量 1,678 组 | 抽样 162 组 |
|---|---|---|
| `WRONG_AUTHOR_FIELD` | **1,017**（60.6%） | 40 |
| `VARIANT_TEXT` | **436**（26.0%） | 40 |
| `SAME_WORK_MULTI_COLLECTION` | **183**（10.9%） | 40 |
| `IMPORT_DUPLICATE` | **26**（1.5%，全为联句/已知别名） | 26 |
| `UNKNOWN` | **11**（0.7%） | 11 |
| `SAME_TITLE_DIFF_TEXT` | **5**（0.3%） | 5 |

抽样方法：按 hypothesis 分层，每层最多 40 组，层内等距取；`IMPORT_DUPLICATE`/`UNKNOWN`/
`SAME_TITLE_DIFF_TEXT` 三层全取。共 **162 组** ≥ 要求的 100 组。

### D5.4 深查结论

1. **这批组本质上不是"导入重复"，而是"归属冲突"。** 因为分组条件已要求
   `count(DISTINCT author_canonical)>=2`，所以"同一作者的作品被导入两次"在结构上不会进入本表
   （同 canonical 已被 HAVING 排除）。进入本表的每一条，都是**同一文本被挂在两个不同人名下**。
2. `SAME_WORK_MULTI_COLLECTION` 只有 183 组（10.9%），且**两侧署名不同**——跨总集同文同时意味着
   两总集对该作品的归属有分歧（例：`朱斌/王之渙` 登鸛雀樓、`張佖/張泌/許棠` 洞庭阻風）。
3. `IMPORT_DUPLICATE` 仅 26 组：联句按联署人各建一条（如 `來燕堂聯句` 5 人各一条），
   属**建模缺陷**（应为一条多作者）而非文本错；`于鄴/于武陵` 属已知别名。
4. 1,678 组中**同集 1,352 组 / 跨集 326 组**。同集组里 songshi 829、tang 454、songci 48、
   gushiji 8、yuanqu 8、mingshi 3、wanqing 2；很大一部分是《全唐诗》乐府类卷与诗人卷重出、
   以及《全宋诗》同一首诗被系于两位宋人。
5. **无法在库内判定谁对**：1,017 组 `WRONG_AUTHOR_FIELD` 只能确定"至少一条错"，
   不能确定错的是哪一条，需别集校勘。

---

## D6 身份规范

- `AUTHOR_IDENTITY_SCHEMA_R2_14.md`：三层（`author_entity` / `author_name_variant` / `collection_role`）
  + A/B/C/D 证据分级 + 四条硬禁止 + 四类非个人作者 + 6 条验收 SQL + 与 R2-13 的 8 项差异。
  相对 R2-13 的关键改动：名字唯一键改 `(raw_name,entity_id)`、朝代拆 verified/derived、
  新增 `MIXED_SCRIPT`/`KINSHIP_PLACEHOLDER`、非人名 72→76、`PERSON` 移出非人名表。
- `AUTHOR_IDENTITY_UNRESOLVED.csv`：498 行 = 366 仅字形对 + 75 未决对 + 42 单字 + 11 未归类同文组
  + 2 非人名未定 + 2 汇总行（1,017 / 436）。

---

## 7 无法判定的条目与原因

| 位置 | 数量 | 原因 | 处置 |
|---|---|---|---|
| D1 `UNRESOLVED` | 75 对 | 64 对少数侧 1–2 条；8 对为"某氏"通称；2 对 raw_name 已混人；1 对佚名 | 保持两条，不合并 |
| D1 `NAME_VARIANT_ONLY` | 366 对 | 无文本重合，朝代是推导值 | 登记 CANDIDATE，永不据此合并 |
| D2 `UNKNOWN` | 2 个 / 17 条 | 《靖康小雅》作者、上元夫人 | 待原书目录 |
| D2 新增非人名 | 4 个 / 49 条 | R2-13 漏列 | 已补，建议下轮挂 role |
| D3 | 1,639 条 | 上游即类目名 | 挂 COLLECTION，不改编者 |
| D5 `WRONG_AUTHOR_FIELD` | 1,017 组 | 只能定"至少一条错" | 需别集校勘，禁止按文本改作者 |
| D5 `VARIANT_TEXT` | 436 组 | 异文 + 异署 | 需校本 |
| D5 `UNKNOWN` | 11 组 | 相似度 <0.75 且异题 | 保留 |
| 单字作者 | 42 个 | 31 姓氏孤立、5 疑截断（洽/含/良/梵/紹）、5 样本 1–2 条、1 缺字符 | 待影像 |

---

## 8 本轮未做的事

- 未修改 `works`/`authors`/`author_alias` 任何一行，未建表，未合并任何身份。
- 未把 `DISTINCT_PERSON` 的名字拆分（拆 works 属写操作）。
- 未对 `t2s` 之外的字形规则做扩展（异体字典需外部数据支撑，本轮只用 opencc）。
- 未处理 `record_locator` 为空（属 E 组范围）。
- 未把 35 对混形（`歐陽炯/欧陽炯`）写回 alias——那需要一次可回滚的批量写。
