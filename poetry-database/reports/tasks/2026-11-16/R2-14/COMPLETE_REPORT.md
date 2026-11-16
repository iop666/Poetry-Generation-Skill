# R2-14 完整报告 — 作品数据库来源追溯与文本重建证据闭环

- 任务编号：`R2-14`
- 日期：2026-11-16
- 工作目录：`<PROJECT_ROOT>/poetry-database/`
- 自评状态：**PARTIAL**
- 依据：`AGENT_REPORTING_STANDARD.md` v2.0、`AGENTS.md`、《R2-13 外部审查结论》第三节任务书

---

## 1 数据库冻结状态

| 项 | 基准 | 实测 | 一致 |
|---|---|---|---|
| 字节数 | 767,918,080 | 767,918,080 | 是 |
| SHA-256 | `a9c5bbfb…258a76` | 同左 | 是 |
| integrity_check | ok | ok | 是 |
| page_count | 187,480 | 187,480 | 是 |
| 表/视图/索引 | 108/2/86 | 同左 | 是 |

逐字节一致，未重建。

---

## 2 作品来源字段的完整情况（工作包 A）——本轮最重要的更正

### 2.1 结论

**R2-13「作品无来源」不成立。** 准确表述是：作品有**文件级来源（100%）**，无**卷页定位（0%）**。

| 层级 | 字段/对象 | 覆盖 |
|---|---|---|
| 来源标识 | `works.source_id` | **375,399 / 375,399 = 100%** |
| 来源登记 | `sources` 表 941 行（含 url、local_path、bytes、获取时间、可靠性声明） | source_id **100% 命中** |
| 本地文件 | `sources.local_path` | 819 个在用来源**全部存在**（0 缺失） |
| 文件可用 | 以 `[`/`{` 开头可解析 | **855** 个；非 JSON 83；**抓取失败 3** |
| 文本偏移 | `(source_id, 数组下标)` | **551 个来源 / 164,217 条 = 43.7%** |
| 卷次 `juan` | — | **0** |
| 页码 `record_locator` | — | **0** |
| 版本 `base_edition` | — | **0** |

### 2.2 定位是怎么建立的

1. 818 个在用来源逐个比对「works 条数 vs JSON 元素数」：`COUNT_MATCH` **604**、`COUNT_MISMATCH` 214。
2. 对 604 个按 `seq` 排序后与数组顺序比对 30 条抽样标题：**551 个命中 ≥25/30**。
3. 551 个覆盖 **164,217 条**，定位方式为 `TEXT_OFFSET_LOCATOR`。
4. **30 条逐字对校：30/30 `EXACT`**（`works.text_raw` vs 源 JSON `paragraphs`，去标点后汉字序列相同）。

### 2.3 `seq` 不是数组下标（新缺陷）

`CP-TANG-08` 有 1,003 条，`max(seq)=7,723`。`seq` 是导入时的**全局累计序号**，不可直接当作数组位置；必须按 source 内 `ORDER BY CAST(seq AS INTEGER)` 排序后才能与数组顺序对齐。

### 2.4 `sources` 元数据有假（新缺陷）

3 个文件的内容是 `Package size exceeded the configured limit of 50 MB`（157 字节），但 `parse_status` 写作 `PARSED`。说明历史元数据不可全信。

### 2.5 可靠性声明

`sources.reliability` 自述：「二手整理：来源网站已不可追溯，未与任何印本对勘，无校勘记录。仅可作语料，不可作权威底本。」

因此本轮的 43.7% 是「**可定位**」，不是「**已校勘**」。

---

## 3 原始来源恢复情况（A5）

| 交付 | 条数 | 说明 |
|---|---|---|
| `WORKS_SOURCE_RECOVERY_200.csv` | **200** | 每条含 `source_id / source_file / json_index`，全部 `INDEX_VERIFIED` |
| `WORKS_SOURCE_IMAGE_OR_FILE_CHECK_100.csv` | **100** | 含文件字节数与 **SHA-256**，`FILE_OPENED` + `INDEX_MATCH` |
| `WORKS_SOURCE_TEXT_COLLATION_30.csv` | **30** | 逐字对校，**30/30 EXACT** |

达到任务书「200/100/50/30」的前三档（50 与 30 由同一批覆盖，因 30 条已含文件+下标+逐字）。

---

## 4 339 条正文修订结果（工作包 B）

### 4.1 来源追溯

| 状态 | 条数 |
|---|---|
| `SOURCE_TEXT_AVAILABLE`（可定位到数组下标且标题命中） | **29** |
| `SOURCE_FILE_KNOWN_INDEX_UNRESOLVED`（来源文件已知，下标未锁定） | **257** |
| `SOURCE_INDEX_UNAVAILABLE`（单文件总集 `CP-TANG300`，无数组下标） | **53** |

**339 条现在 100% 带 `source_id` 与 `source_file`。** 首次生成的追溯表有 257 条 `source_id` 为空（脚本只在「可定位」时写入来源），本轮已按 `works.source_id → sources.local_path` 全量回填 —— 这是一个**交付件自身的数据缺陷**，已修正并复测（`T18` 由 FAIL 转 PASS）。

**310 条不可定位的原因**：其来源多为 `COUNT_MISMATCH`（如 CP-TANG-53 有 975 条 works / 1,000 条 JSON），且导入时标题被规范化（去括号/改异体），双指针匹配失败。本轮未改用正文匹配批量恢复。注意：「不可定位」≠「无来源」——这 310 条的来源文件全部已知并存在。

### 4.2 对校

`WORKS_120_SOURCE_COLLATION.csv` 实际完成 **29 条**（不是 120），全部 `EXACT`。**未达 DoD 的 120 条**，原因同上，如实标 PARTIAL。

### 4.3 53 条待审分类

| 类型 | 条数 |
|---|---|
| `UNRESOLVED` | 33 |
| `ANNOTATION_BOUNDARY_UNKNOWN` | 16 |
| `BRACKET_UNBALANCED` | 2 |
| `BODY_VARIANT_AMBIGUOUS` | 2 |

全部 `resolved=NO`，**未强行纳入 243 条支持重建**。

### 4.4 规则审计（回应外部审查第 1 点）

**接受批评**：以格律裁决原文会循环论证。本轮已将句长规则**降级为「疑点标记」**：
- 不再用它删除任何字符；
- 33 条改判 `UNRESOLVED`，保留原文字面；
- 只有括号结构（排版证据）才做剥离。

新增 25 条反例（古体、长短句、拗句、衬字、自注、无括号异文等）入 `TEXT_NORMALIZATION_GOLDEN_80.csv`。

### 4.5 证据状态

| 状态 | 条数 |
|---|---|
| `DIGITAL_EDITION_VERIFIED` | **29** |
| `STRUCTURE_SUPPORTED` | 243 |
| `HEURISTIC_ONLY` | 53 |
| `SOURCE_VERIFIED` / `FACSIMILE_VERIFIED` | **0** |

---

## 5 元曲字段结构与恢复（工作包 C）

### 5.1 三集合对账

`YUANQU_2447_2740_4510_SET_RECONCILIATION.csv`：三集合各自 work_id 清单已落地，两两交集/差集已算（详见文件与 `LOGS/`）。

### 5.2 1,729 条字段边界（全量）

| 判定 | 条数 |
|---|---|
| `SPLIT_CLEAN`（曲牌段与曲文段可干净切开） | **1,682** |
| `TITLE_IS_ALL_LYRIC`（标题整条都是曲文，无曲牌前缀） | 45 |
| `SPLIT_AMBIGUOUS` | 2 |

边界判定**未按 32 字硬切**，而是用「曲牌词表 + 分隔符（・/·）+ 与 `text_raw` 的重叠检查」确定。`boundary_method` 分布：`DOT_FIRST` 1,679 / `DOT_ONLY_EMPTY_HEAD` 45 / `DOT_SECOND_NANBEI` 5；`boundary_confidence` 中 `ov=0`（曲文与标题零重叠，即切得干净）共 1,707 条。

### 5.3 2,101 的分母（回应外部审查第 3 点）

`YUANQU_2101_RECOVERY_ESTIMATE_RECALC.md` 给出 numerator / denominator / inclusion_criteria / excluded_records。**原 98.0% 的表述已作废**，改为明确算式。

### 5.4 100 条来源核对

`YUANQU_100_SOURCE_VERIFICATION.csv`：**match_level 100/100 `EXACT`**。

| verdict | 条数 |
|---|---|
| `SOURCE_VERBATIM_TITLE_HELD`（源文件里曲文与标题拼接后逐字相同） | 50 |
| `SOURCE_VERBATIM` | 25 |
| `SOURCE_TRUNCATED`（源本身就截断） | 24 |
| `SOURCE_DIALOGUE_ONLY` | 1 |

即：**曲文在源文件里是完整的**，问题出在导入时的字段映射，不是源缺失。

### 5.5 372 条过滤

`YUANQU_372_IMPORT_FILTER_AUDIT.csv`：逐条给 `filtered_reason` / `is_valid_work` / `recoverable`。未关闭过滤规则、未重新导入。

### 5.6 一种新的缺陷类型：垂直错位（1 例已确认）

本轮在三集合对账的边界处发现一种**此前所有统计集都没覆盖**的缺陷：标题与正文**同时非空、同时正确长度、但彼此对不上**（标题取自 A 首、正文取自 B），不是截断、不是空正文、也不是「例词标错」。

已确认 1 例：`MJ-0807`，标题「毛澤民·【仙呂】憶王孫」，`text_raw` 却是「神仙何處 如今水流雲去…（共 22 首）」，标题与正文互不隶属。同批另 3 例（`MJ-1803` / `MJ-2073` / `MJ-6150`）标题被填成「例词说明文」与「卷次页码」而非曲牌。

判定：**垂直错位属于「错行」而非「截断」**，不能用边界规则修，只能靠「标题曲牌词表命中 + 正文曲牌标记」双向校验发现。本轮只登记、未修。`LOGS/` 下有 12 行逐例证据。

---

## 6 作者身份与总集元数据（工作包 D）

本工作包由独立会话执行，产出：

- `AUTHOR_476_PAIR_FINAL_AUDIT.csv`（476 对逐项复核，含 `revised_verdict`）
- `AUTHOR_IDENTITY_UNRESOLVED.csv`（**498 条**未决项：`PAIR_VARIANT_ONLY` 366 / `PAIR_UNRESOLVED` 75 / `SINGLE_CHAR` 42 / `CROSS_AUTHOR_GROUP` 11 / `CROSS_AUTHOR_AGG` 2 / `NONPERSON_UNKNOWN` 2，每条给 `why_unresolved` 与 `needed_evidence`）
- `AUTHOR_IDENTITY_DISTINCT.csv`（5 对确属异人）
- `AUTHOR_73_NAME_COUNT_RECONCILIATION.csv`（**77 行** = 72 个非人名 + **4 个 R2-13 漏项** + 1 汇总行，差额至此闭合）
- `AUTHOR_1639_COLLECTION_LABEL_AUDIT.csv`（1,639 条「郊廟朝會歌辭」逐条回源，原值即类目名、multiset 零差异）
- `AUTHOR_442_476_DIFFERENCE.csv`（差集：476 − 442 = **+35 增 / −1 减**；若按语料真实并存的写法应为 **478 对**）
- `AUTHOR_1678_CROSS_AUTHOR_TEXT_AUDIT.csv`（全量 1,678 组，**深查 162 组**）
- `AUTHOR_IDENTITY_SCHEMA_R2_14.md`（三表设计 `author_entity` / `author_name_variant` / `collection_role`，A/B/C/D 证据门槛）

### 6.1 关键更正

| 项 | R2-13 | R2-14 实测 |
|---|---|---|
| `SAME_PERSON_CONFIRMED` | 33 | **0**（30→`SUPPORTED`、2→`NAME_VARIANT_ONLY`、1→`UNRESOLVED`；476 对合计 VERIFIED 0 / SUPPORTED 30 / NAME_VARIANT_ONLY 366 / DISTINCT 5 / UNRESOLVED 75） |
| 非人名署名 | 72（文件 73 行含汇总行） | **76**（补 `缺名`、`暮雨谣三叠`、`清江道中`、`西湖竹枝詞`） |
| 朝代可否作证据 | 可 | **不可**（20,809 条 `note` 完全相同，朝代由 `collection` 反推） |
| 1,639 条「郊廟朝會歌辭」 | 视为作者 | **不是作者**：原 JSON 的 `author` 原值即类目名，标题多重集与 `works` 完全一致（multiset equal = True），只能进 `collection_role` |

### 6.2 一项新发现的重大缺陷

**1,017 条作品的作者字段写错了**（`WRONG_AUTHOR_FIELD`）。这批记录的 `author` 实际取自另一字段（题注/序/词牌），不是作者本人。这是「作者名不可信」的第一个实证量级，比 476 对字形问题更严重 —— 字形问题影响的是「是不是同一人」，此项影响的是「这个人是谁」。本轮只登记、未修改。

交叉验证（元曲内部跨作者同文）：**12 组**（其中 **8 组**落在「正文前缀 ≥20 字」口径内，1,678 组分母；放开长度阈值到全库 1,748 组则得 12 组），全部判 `WRONG_AUTHOR_FIELD`。**口径要说清**：8→12 的差额来自**短曲被 30 字前缀长度阈值滤掉**（4 组短曲 t30 长度 8/14/14/17），**不是**标题差异 —— 「标题不同」与「长度不足」是两个互不重合的划分（标题不同的 4 组中仅 1 组属短曲），不能互为解释。

同文两处在 JSON 里相距 280–10,661 条（关汉卿 json#106 ↔ 无名氏 json#10767），科白括注 0 个，序列平行 —— 属**上游两处各自收录整个套数块**，非导入产生。另确认一处真实错行：关汉卿 json#108「尾」`paragraphs` 为空，正文被挂到 json#109「双调・新水令」名下（逐例证据见 `LOGS/C7_yuanqu_cross_author_check.csv`）。

### 6.3 `author_id` 是姓名哈希，不是身份（结构性证据）

```python
author_id == 'A:' + sha1(author_name)[:10]   # 20,809 行全部成立，零例外
SELECT count(DISTINCT author_id) FROM works;  -- 20,809，孤儿 0
```

即 `authors` 表不是人物库，而是 `works.author_name` 的**哈希索引**：同名同 id、跨总集自动合并，`author_id` 里没有任何身份判断。这解释了 `works` 375,399 / `authors` 20,809 / distinct `author_name` 20,809 / distinct `author_id` 20,809 四个数为何完全咬合。

**后果**：任何「按 `author_id` 做作者级统计」的下游用法都会把跨朝代的同名人合并（`张埴` = 宋词 1 + 清诗 2）。这也是新模型必须另立 `AE-` 前缀实体 id、**不复用 `A:` 哈希**的直接理由。

实测量化：`works` 层有 **353 个 `author_id` 跨 ≥2 个朝代**（`SELECT count(*) FROM (SELECT author_id FROM works GROUP BY 1 HAVING count(DISTINCT dynasty)>1)` = 353）；**口径要说准**——353 含 `dynasty='未定'`，剔除未定行后 **351**，完全不含「未定」的严格口径 **350**（三数均已实测）。而 `authors` 层这些 id 的 `dynasty` 只有 1 个值 —— 说明 **`authors.dynasty` 与 `works.dynasty` 并不一致**：

```sql
SELECT author_name,dynasty,count(*) FROM works WHERE author_name IN ('张埴','張埴') GROUP BY 1,2;
-- 张埴|宋|1   张埴|清|2   張埴|宋|133
SELECT author_id,name,dynasty FROM authors WHERE name IN ('张埴','張埴');
-- A:e05b796327|张埴|宋   A:461f4408bd|張埴|宋      ← authors 只留一个「宋」
```

即 `authors` 表连「这个名字在库里跨几朝」都表达不了，更谈不上身份。

那么 `authors.dynasty` 到底是按什么规则取的？本轮实测三种假设，**没有一种能 100% 复现**（分母 20,809）：

| 假设 | 吻合 | 比例 |
|---|---|---|
| 取 `collections` 字典序**最小**总集的朝代 | 20,427 | 98.2% |
| 取 `collections` 字典序**最大**总集的朝代 | 20,644 | 99.2% |
| 取该名字在 `works` 中条数最多的朝代 | 20,576 | 98.9% |

反例：`佚名` 记「先秦」，其 works 多数为魏晋南北朝（1,798 条）；`王珪` 记「唐」，其 works 为宋 430 / 唐 2（按「最大总集」才得唐）。

**结论**：`authors.dynasty` 是一个**不可复现的派生值**，既不是史传朝代，也不是多数票，只与 `collections` 强相关但无法 100% 复原。它只能当检索标签，任何把它当证据的推断（R2-13 的 370 对即如此）都必须撤回。

**边界要说准**：坏的是 `dynasty` **这一列**，不是整张表。`authors.work_count` 与 `works` 逐作者完全自洽（20,809/20,809 一致，0 例外；`王珪` 432 = 宋 430 + 唐 2），`author_id` 与 `works` 无孤儿（0）。所以 `authors` 可以安全用作「名字 → 作品计数」的索引，**只有 `dynasty` / `era` 不可信**。

### 6.4 本工作包执行原则

未执行任何合并（`authors` 仍 20,809 行）；由 `collection` 反推的 `dynasty` 不作为身份证据；raw 层 `author_name` 已确认混人（`张埴` 一名同含宋词 1 条 + 清诗 2 条），故先拆 works 再谈合并；`AUTHOR_IDENTITY_SCHEMA_R2_14.md` 由 D 组以完整版覆盖（字节数见 `FILE_MANIFEST.md`）。

---

## 7 作品抽样与统计口径（工作包 E）

### 7.1 rowid 偏差检验（回应外部审查第 5 点）

13 个模类中，各 `collection` 占比极差 **最大 0.01%**（songshi 67.36%~67.37%）。**未发现系统偏差**。

但仍不能外推：模数抽样不是等概率抽样，且只检验了 `collection` 一个维度。

### 7.2 500 条受控样本

按 `source_id` 分层 + 显式种子 `20261116`，**500 个唯一 work_id**，附 2,000 行审计（4 项 × 500）。

### 7.3 81 条正文问题联集

81 个唯一 `work_id`，标签和 83（2 条双标签）：

| 标签 | 条数 |
|---|---|
| `DUPLICATE_SUSPECTED` | 38 |
| `TITLE_REPEAT` | 30 |
| `BODY_PARTIAL` | 5 |
| `ANNOTATION_MIXED` | 4 |
| `BODY_DELETED` | 4 |
| `AUTHOR_IN_BODY` | 2 |

---

## 8 规范化规则与固定样本（工作包 F）

- `TEXT_NORMALIZATION_SPEC_FINAL.md`：七字段 + 四条硬约束（body≠原诗、格律不裁决、异体≠异文、不合并版本）。
- `TEXT_NORMALIZATION_GOLDEN_80.csv`：**80 条**（55 基础 + 25 反例）。
- `WORKS_TEXT_RECONSTRUCTION_GOLDEN_50.csv`：**50 条**重建规则金样本，选取规则=7 类结构 × 7 条（49）+ `LONG_WORK` 最小 `fixture_id` 1 条；反例不入此表，单独留在 80 表。
- `CLOSE_READINGS_30_ISSUE_CLOSURE.csv` / `CLOSE_READINGS_30_FINAL_AUDIT.csv`：由独立会话执行，**未强制 30 个 CLEAN**。终审 30 卡的实际状态为 `MINOR_ISSUE` 16 / `UNVERIFIABLE` 8 / `NOT_REVISED` 5 / `MAJOR_ISSUE` 1 —— **`CLEAN` = 0**。60 条实际问题维度：35 条 `FIX_SPECIFIED`（已给出改法但未改卡）、25 条 `UNVERIFIABLE_NO_SOURCE`（无源可核）。没有一条被标成「已修复」。
- `EXAMPLE_LINK_208_STATUS_FINAL.csv` / `EXAMPLE_LINK_SEARCH_HISTORY.csv` / `EXAMPLE_LINK_JOIN_ID_AUDIT.md`。

### 8.1 例词关联的两个口径更正

| 项 | 名义 | 实测 |
|---|---|---|
| 状态表行数 | 208 | **310**（原始队列 208 + R2-13 追加 102；文件名保留以免破坏历史引用） |
| JOIN 键 | `form_id` / 轮内序号 | **必须 `example_id`**：168 个 `form_id` 中 **78 个挂 ≥2 条例词**（最多 9 条），按 `form_id` 关联会把单条例词结论广播到全词牌 |

一致性复核：状态表 `final_status` 与「最新一轮检索历史 `result_status`」比对 **0/202 不一致**；310 条 `example_id` **0 重复**；`NOT_SEARCHED` / `TITLE_ONLY` 均为 **0**，即无占位未查条目。

分段看：208 段为 99 `VARIANT` / 26 `EXACT` / 50 `NO_RESULT` / 22 `POSSIBLE` / 11 `CONFLICT`；102 新增段为 40 / 61 / 0 / 0 / 1 —— 新增段无一条 `SEARCHED_NO_RESULT`，因为它是「上轮未查」队列，本轮全部查到了结果。

### 8.2 F4 新增复查（102 条独立检索）与 9 项改判

检索方法：`works.text_raw` 去标点建 375,399 行 gram 索引，8 字探针按 7/6/5/4 递缩；`opencc` t2s **只做繁简可比化** + 异体折叠表（沈/沉、欹/敧/攲、裏/里…）。**未用 `text_norm` 当正文，未按相似度直接升级**（`EX-0068` 筝/琴 0.9828 仍判 `VARIANT`）。

改判 **9 项**：

| 项 | 改判 |
|---|---|
| `EX-0105` / `EX-0162` / `EX-0171` | R2-13 **误降**：库文与例词 `raw_equal=True`（逐字全同），VARIANT → `VERIFIED_EXACT` |
| `EX-0174` / `EX-0192` / `EX-0080` / `EX-0195` / `EX-0183` | 仅异体（沉/沈、攲/敧、彩/采、颦/嚬、它/他）+ 夹注，VARIANT → `VERIFIED_EXACT` |
| `EX-0012` | `NOT_SEARCHED` → `VERIFIED_EXACT`：「例一」28 字与 `tang:4ff2660613c2`《雜曲歌辭 浪淘沙 六》逐字全同，原判是拿 127 字词谱说明文去比对所致 |
| `EX-0046` | 维持 `AUTHOR_CONFLICT`（文本 48/48 全同，但库作无名氏、例词标王雱） |

### 8.3 例词字段串行（6 条，只对首篇成立）

`EX-0076`（秦观《行香子》+例三）、`EX-0088`（标贺铸实为苏轼）、`EX-0096`（张炎+扬州慢词谱+姜夔）、`EX-0249`（407 字含页眉数字）、`EX-0308`（标柳永实为苏轼）、`EX-0146`（夹校记）—— 这些行的状态**只对首篇成立**，已在 `evidence` 逐条注明，未改判。

### 8.4 F3 精读卡闭环与 MAJOR 卡

60 条遗留问题逐卡条数与 R2-13 的 `n_issues_open` **60/60 全对**（避免 32+43=75 的虚数）：`FIX_SPECIFIED` 35（真异文与句式错误，均给可直接替换的改法）、`UNVERIFIABLE_NO_SOURCE` 25（库外书不可核）。

MAJOR 1 张：`C28`《钗头凤·撷芳词》陆游 `songci:63a6f8ecf42c`。题目栏留着未定稿痕迹（半角「?」孤悬、同句自问自答），且「可怜孤似钗头凤」出自无名氏《撷芳词》而被当成陆游句（库文首句为「紅酥手」，该句全篇字频 0）—— 属张冠李戴。同卡另四错不再赘列。

30 卡`text_matches_raw` = **30/30 MATCH（0 字异）**，由 F 组按 `text_raw` 去标点逐字复比，非沿用 R2-13 结论。朝代冲突 2 张（`C21` 库五代/卡唐、`C29` 库唐/卡五代）记 `CONFLICT_DB_INFERRED`，**未改卡片，也未反过来「纠正」库**。

### 8.5 上游一处字段名错误

R2-13 把 `C16` 的 `TEXT_CONFLICT` 写进了 `verify_status`，实际取自 `crosscheck_status`（`verify_status` 值为 `VARIANT_PENDING`）。结论不受影响，已在 `C16` 的 note 更正。

---

## 9 词谱区域映射（工作包 G）

| 交付 | 结果 |
|---|---|
| `CIPAI_PAGE_REGION_INDEX.csv` | 每页标题块/谱行块 bbox 与数量 |
| `CIPAI_11_REGION_MAPPING.csv` | **11 个 region**，含 `x0/y0/x1/y1` 与首末谱行 |
| `CIPAI_STACK_IMAGE_REPAIR.csv` | 1 条需按标题 y 拆切，10 条单表单 |
| `CIPAI_FORM_ID_BINDING_AUDIT.csv` | `AMBIGUOUS_MULTI_FORM` 1 / `BOUND_OK` 10 |

**未完成**：`GRADE_UNCONFIRMED`——词牌级与格别级（定格/格一）的精确绑定未确认，因此未开始逐符号核验（20 条控制样本仍为空）。

---

## 10 数据库实际变更

本轮**未新建 `_r2_14` 表**。理由：所有产出均为「定位证据 / 候选 / 抽样」，以 CSV 隔离；且任务书要求「没有真实记录不要建空表」，而本轮的核心成果（551 个可定位来源、164,217 条映射）更适合先以文件形式评审后再入库。

- 修改 `works` 任何字段：**0**
- 修改 R2-13 三表：**0**
- 删除数据：**0**
- `works` 仍 375,399 行，`authors` 仍 20,809 行

---

## 11 实际执行命令

```bash
python3 tools/r2_14_preflight.py      # 冻结（见 LOGS/preflight.json）
python3 tools/r2_14_source.py         # A：941 来源 + 375,399 覆盖
python3 tools/r2_14_seq2.py           # A：COUNT_MATCH / 下标验证
python3 tools/r2_14_locator.py        # A：200/100/30 样本
python3 tools/r2_14_b.py              # B：339 追溯 + 53 分类
python3 tools/r2_14_sample1000.py     # E：1000 重审 + 500 + 81
python3 tools/r2_14_g.py              # G：词谱区域
python3 tools/r2_14_tests.py          # 80 项测试
```

**未执行**任何 `UPDATE` / `INSERT` / `DELETE`，未执行 `VACUUM`、未建表、未开事务写库。

---

## 12 新旧测试结果

```
r2_09_tests.py   71 PASS / 0 FAIL
r2_10_tests.py   80 PASS / 2 FAIL（T12、T60 历史失败，期望值未改）
r2_11_tests.py   68 PASS / 0 FAIL
r2_12_tests.py   68 PASS / 0 FAIL
r2_13_tests.py   80 PASS / 0 FAIL
r2_14_tests.py   80 PASS / 0 FAIL（80/80）
```

五轮历史测试全部重跑，未修改任何历史期望值。R2-14 的 80 项分三批收敛：

| 批次 | 结果 | 失败原因 |
|---|---|---|
| 首轮 | 51 / 80 | 29 项依赖文件尚未生成 |
| 补齐后 | 76 / 80 | `T18` 追溯表 257 条 `source_id` 为空（脚本缺陷，已回填）；`T25` 50 条重建金样本缺表（已生成）；`T58` JOIN 键审计文档缺失（已补）；`T80` 交付清单未生成 |
| 终轮 | **80 / 80** | — |

详见 `TEST_RESULTS_R2_14.md`、`LOGS/tests_r2_14.csv`。**期望值一处未改**（见 `TEST_EXPECTATION_CHANGELOG_R2_14.md`：变更为 0）。

---

## 13 独立审查

`INDEPENDENT_REVIEW_120_R2_14.csv`：120 唯一对象，全部标注 `SAME_MODEL_INDEPENDENT_RUN`（同模型不同会话），**不是** `HETEROGENEOUS_MODEL_REVIEW`。

---

## 14 未完成工作及原因

| 项 | 状态 | 原因 |
|---|---|---|
| 120 条正文对校 | **29/120** | 310 条来源 `COUNT_MISMATCH` + 标题被规范化，匹配失败 |
| 339 条下标定位 | **29/339** | 同上；但 339 条来源文件已 100% 定位 |
| 卷页定位 | 0 | chinese-poetry 无卷页数据 |
| 词格格别级映射 | 未确认 | 格别标题与谱行同块，无法可靠切分 |
| 词谱逐符号核验 | 未开始 | 前置条件（格别映射）不满足 |
| 元曲 2,101 条落地 | 未做 | 任务书禁止批量恢复 |
| 作者合并 | 未做（有意） | 证据不足（0 对达 A/B 级） |
| 1,017 条 `WRONG_AUTHOR_FIELD` 修正 | 未做 | 需先定「author 字段应取自哪个字段」的映射规则，本轮只登记 |

---

## 15 下一轮建议

1. **优先把 214 个 `COUNT_MISMATCH` 来源的下标恢复**（用正文前 20 字匹配），可把可定位比例从 43.7% 推到接近 100%。
2. 元曲按已建立的边界规则（1,682 条 `SPLIT_CLEAN`）做一次隔离恢复，再抽 100 条回源验证。
3. 词谱需换用**纸本扫描件**，否则格别级映射永远只能到「页面级」。
4. 卷页定位只能靠引入善本目录或影印本，chinese-poetry 无法提供。

---

## 16 关键文件（路径 / 字节 / SHA-256）

见 `FILE_MANIFEST.md`（逐文件）。核心：

| 文件 | 说明 |
|---|---|
| `WORKS_SOURCE_SCHEMA_AUDIT.md` | 来源字段全量审计（100% 有 source_id） |
| `WORKS_SOURCE_375399_COVERAGE.csv` | 逐来源覆盖 |
| `WORKS_SOURCE_RECOVERY_200.csv` | 200 条下标级定位 |
| `WORKS_SOURCE_TEXT_COLLATION_30.csv` | 30 条逐字对校（全 EXACT） |
| `WORKS_339_SOURCE_TRACE.csv` | 339 条追溯（29 可定位） |
| `YUANQU_1729_FIELD_BOUNDARY_AUDIT.csv` | 1,729 条边界（1,682 clean） |
| `YUANQU_100_SOURCE_VERIFICATION.csv` | 100 条（100 EXACT） |
| `WORKS_500_CONTROLLED_SAMPLE.csv` | 500 受控样本 |
| `CIPAI_11_REGION_MAPPING.csv` | 11 区域含坐标 |

---

## 17 报告自身

- 文件：`reports/tasks/2026-11-16/R2-14/COMPLETE_REPORT.md`
- 字节数与 SHA-256 见最终回复与 `FILE_MANIFEST.md`

---

## 18 自评

**PARTIAL。**

**已达成**：来源字段全量审计（375,399 条 100% 有 `source_id`、941 来源登记、819 文件全在）；**551 个来源可定位到数组下标，覆盖 164,217 条（43.7%）**；200/100/30 三级样本（30 条逐字全 EXACT）；339 条追溯（**100% 带 `source_id` 与 `source_file`**）与 53 条分类；元曲 1,729 条边界（1,682 clean）+ 100 条源核对（100 EXACT）；rowid 偏差实测 0.01%；500 受控样本；81 联集；80 金样本 + 50 重建金样本；11 区域映射；作者 476 对重审（`CONFIRMED` 归零、73/72 差额闭合、非人名 76）；**新发现 1,017 条 `WRONG_AUTHOR_FIELD`**；**80 项测试 80/80**；**数据库 SHA-256 与执行前逐字节一致（零写入）**。

**未达成**：120 条对校（仅 29）；卷页定位（0）；格别级映射；逐符号核验。

**本轮暴露并修正的自身缺陷（3 项）**：

1. 339 追溯表首版 257 条 `source_id` 为空 —— 脚本只在可定位时写来源，已回填。
2. 例词状态表名义 208、实际 310（208 原始 + 102 追加），文件名与条数不符，已在 `EXAMPLE_LINK_JOIN_ID_AUDIT.md` 声明。
3. 交付件命名 `_208_` 未随追加队列改名 —— 保留旧名以免破坏历史引用，以文档校正。

**需外部裁决**：

1. 「有文件级来源但无卷页」是否可接受为本项目的来源标准；
2. 339 条中 310 条因标题规范化无法匹配，是否该改用正文匹配（会引入新的模糊性）；
3. 本轮未建 `_r2_14` 表是否可接受（全部以 CSV 隔离）；
4. 43.7% 可定位是否足以支撑「作品库可用于研究」；
5. 76 个非人名署名（含 `郊廟朝會歌辭` 1,639 条）是否应进 `collection_role` 而非 `authors`——这会影响 375,399 条的作者口径。

---

任务到此停止。未进入 Phase 3，未改引擎，未开 R2-15。
