# R2-15 完整报告 — SOURCE INTEGRITY & PHASE 0–2 BASELINE RECONCILIATION

- 任务编号：`R2-15`
- 日期：2026-11-20
- 工作目录：`<PROJECT_ROOT>`
- 最终状态：**PARTIAL**
- 依据：`AGENTS.md`、`AGENT_REPORTING_STANDARD.md` v2.0、2026-11-20 外部审核任务书

---

## 1 基线冻结

| 项 | 值 |
|---|---|
| GitHub `main` HEAD（执行前） | `f7b4b2eac5adfd0493842fe1eaee725041a72188` |
| 本地工作区 | 非 git 仓库；同步走独立暂存仓库（`<LOCAL_WORKBUDDY>/<日期>/.tmp/`） |
| 数据库路径 | `<PROJECT_ROOT>/poetry-database/database/poetry.db` |
| 数据库字节 | 767,918,080 |
| 数据库 SHA-256 | `a9c5bbfb72c0cc8784d080f3332f393e718c61a15d93d35b4114e3edb9258a76` |
| 与 R2-14 基线 | **逐字节一致** |
| 本轮写库 | **0**（全部只读 `mode=ro`） |

---

## 2 公开版权与同步审计（R2-15A，P0）

### 2.1 缺陷成立

外部审核所指属实，且比"声明不一致"更严重：**是实现层面的白名单过宽**。

`tools/github_sync.py` 的 `INCLUDE_FILES` 写的是目录 `poetry-database/raw/r2_04_evidence`，`collect()` 对其 `rglob("*")`，而 `EXCLUDE_PARTS` 未排除正文子目录。结果 34 个文件进入公开仓库：

| 目录 | 文件 | 字符 | 字节 | 性质 |
|---|---|---|---|---|
| `full/` | 17 | 107,351 | 290,894 | 完整章节正文（如 `A_027_诗律.md` 61,442 B） |
| `chapters/` | 17 | 47,436 | 129,806 | 每章约 15 KB 连续正文，仍属大段复制 |

### 2.2 已修复

| 措施 | 内容 |
|---|---|
| 白名单收窄 | 目录 → 单文件：只留 `manifest.json`、`README_CHARCOUNT.md` |
| 黑名单双保险 | 增加 `/r2_04_evidence/full/`、`/r2_04_evidence/chapters/` |
| 删除规则重写 | 原实现依赖旧清单且条件不成立，导致首次修复后远端仍留 37 个文件；改为「命中排除规则即删」，并输出删除计数 |
| 结果 | 远端 **867 → 833** 个文件；`full`/`chapters` 计数 **0/0** |

删除提交：`f7b4b2e`。复核方式：GitHub `git/trees/main?recursive=1`。

### 2.3 manifest 字符差 21,522 已查清

**不是数据丢失，也不是 manifest 过期。**

- `full_chars` = 逐页 `clean()` 后字符数之和，17 单元合计 **128,873**，按原脚本**复算差 0**；
- `full/*.md` 实际 **107,351** 字符；
- 差额来自 `paragraphs()` 丢弃 <12 字的短行（页眉、页码、图注、公式残片），以及段落化换行差异。

逐单元证据：`COPYRIGHT_CHARCOUNT_DIFF.csv`。已加 `raw/r2_04_evidence/README_CHARCOUNT.md` 说明两种口径，避免后人再误判。

### 2.4 Git 历史（未处置，需授权）

| 项 | 值 |
|---|---|
| 含正文的提交 | **8 个**（`0e3b0fc` 引入 … `490919e` 继承 … `f7b4b2e` 删除） |
| 去重 blob | 34（17 full + 17 chapters） |
| blob 总字节 | 420,700 |

方案 A（不改历史）/ B（filter-repo 重写 + force push）/ C（删库重建）的代价与前置条件见 `COPYRIGHT_HISTORY_IMPACT.md`。

**本轮未执行任何历史重写，未 force push。** 本地研究材料完整保留，未删任何本地文件。

### 2.5 表述修正

- R2-04 `SOURCE_AUDIT.md` 的"全文未进入交付材料"对**本地交付**成立、对**公开仓库**不成立，已加 `ERRATA_PUBLIC_SYNC.md`，不删改原文。
- `UPLOAD_REPORT.md` / `GITHUB_SYNC.md` 已改为"自 2026-11-20 起排除，历史遗留见影响分析"。

---

## 3 Phase 0/1 文献目录与阅读记录（R2-15B）

### 3.1 书目登记

`BOOK_CATALOG_52.csv`：**52 行**（历史口径 52 种，全部可复核，未凑数）。

| 维度 | 分布 |
|---|---|
| `acquisition_status` | `ACQUIRED` 29 / `CHANNEL_IDENTIFIED` 23 |
| `reading_status` | `READ` 8 / `UNRESOLVED` 21 / `NOT_FOUND` 23 |
| 版权状态 | `PUBLIC_DOMAIN` 35 / `IN_COPYRIGHT` 16 / `UNKNOWN` 1 |

字段含 `book_id / 书名 / 作者 / 版本 / 资料类别 / 版权状态 / 合法获取渠道 / acquisition / parse / reading / extraction / reading_scope / source_gap / local_evidence_path / db_book_id`。

缺料清单 `MISSING_MATERIALS.csv`：**45 条**（未取得、未解析、缺页、版本不符）。

### 3.2 两处阅读声明核实

| 声明 | 报告声称 | 本次核实 | 判定 |
|---|---|---|---|
| 王力合订本 A/B/C/D | 31/31 READ、106,460 汉字 | 31 单元全部 `status=READ`、`gate_pass=1`；`chars_read` 合计 **106,460**，用 PaddleOCR 原文独立复算 **106,460** | **成立**，但是**章级**口径，不是逐字/逐节 |
| 《词学十讲》 | 9 讲 READ + 第 6 讲 `READ_WITH_SOURCE_GAP` | `reading_records_r2_06` 10 行：9 READ / 1 READ_WITH_SOURCE_GAP；合计 74,652 字；第 6 讲有笔记与 `source_gap` 双证 | **成立**，同为讲级口径 |

### 3.3 同时发现的 5 类问题（不影响两处声明，但影响登记表可信度）

1. **R1 的 READ 数自相矛盾**：`01` 报告称"实际阅读 8 项"，同表却标 10 项 READ；`03` 报告只列 7 种。
2. **《诗经》《楚辞》《唐诗三百首》的书级 READ 不成立**：只有单篇卡片，无 `read_log`、无逐篇笔记。
3. **`books` 表整体陈旧**：13 行仍为 `status=FOUND / reading_status=NOT_STARTED`，其中 9 部后来已取得或已读。
4. **版本错位**：《钦定词谱》《词律》《广韵》《集韵》《词林正韵》《中原音韵》取得的是**四库本维基转录**，不是 R1 登记的中华/上古校注影印本。
5. **《中华通韵》被《中华新韵》顶替**：库内 `zhonghua_xinyun_*` 是 2005 年十四韵，不是 2019 年十六韵。

结论：**"读过"成立，"读过某版本"不成立。** 版本级结论一律降级为 `UNRESOLVED`。

---

## 4 作品来源证据统计闭合（R2-15C1）

### 4.1 旧表 325 条不闭合的原因（已定位）

| 原因 | 数量 | 说明 |
|---|---|---|
| 重复计入 | +9 | 29 条 `DIGITAL_EDITION_VERIFIED` 中 9 条原属 `SUPPORTED_RECONSTRUCTION`，旧表仍按 243 全量计 |
| 整档漏计 | −23 | 43 条 `TEXT_STRUCTURE_CONFIRMED` 中 23 条来源下标未定，旧表无对应档 |

```
339 − 23 + 9 = 325   ← 与旧表完全吻合
```

### 4.2 重建后的完整分布（339 条全部有归属）

| evidence_status | 条数 |
|---|---|
| `DIGITAL_EDITION_VERIFIED` | **29**（9 + 20） |
| `STRUCTURE_SUPPORTED` | **234**（243 − 9） |
| `STRUCTURE_CONFIRMED_NO_SOURCE` | **23** |
| `HEURISTIC_ONLY` | **53** |
| 合计 | **339** |

逐行映射：`WORKS_339_EVIDENCE_CLOSURE.csv`（339 行）。说明：`WORKS_339_EVIDENCE_CLOSURE.md`。

### 4.3 43 条 `TEXT_STRUCTURE_CONFIRMED` 的证据边界

- 20 条：来源下标已定 + 逐字一致 → 可称 `DIGITAL_EDITION_VERIFIED`；
- 23 条：结构自洽但来源未定 → 只能到 `STRUCTURE_CONFIRMED_NO_SOURCE`。

**"43 条结构确认" ≠ "43 条来源验证"。** `SOURCE_VERIFIED` / `FACSIMILE_VERIFIED` 仍为 **0**。

120 条对校实际 **29 条**，本轮不补数、不改口径。

---

## 5 作者字段审计（R2-15C2）

### 5.1 口径更正：1,017 是「组」不是「条」

任务书写"1,017 条"，R2-14 原文（`LOGS/D2_notes.md`）记的是**组数**：

| 项 | R2-14 | 本轮复现 |
|---|---|---|
| 分组分母 | 1,678 组 / 3,418 条 | **1,678 / 3,418（差 0）** |
| `WRONG_AUTHOR_FIELD` | 1,017 组 | **1,032 组**（+15，+1.5%） |
| 组内作品 | 未公布 | **2,081 条** |

+15 组差异已逐项说明（同集同题异文并入、禅偈/联句归类、`IMPORT_DUPLICATE` 认定更严）。R2-14 的分类脚本未随报告保留，本轮以**可复算**的 1,032 为准。

### 5.2 更重要的结论：R2-14 的定性错误

R2-14 称"这批记录的 author 实际取自另一字段（题注/序/词牌）"。逐条回查 2,081 条后：

| 实际类型 | 条数 | 占比 |
|---|---|---|
| `PERSON`（就是人名，只是**同文异署**） | **1,831** | 88.0% |
| `ALIAS`（釋/僧 前缀、字号、异体） | 129 | 6.2% |
| `UNKNOWN`（佚名/无名氏/不详） | 66 | 3.2% |
| `HONORIFIC`（庙号/尊号/官称） | 40 | 1.9% |
| `COLLECTION_NAME`（郊廟朝會歌辭） | 14 | 0.7% |
| `WRONG_FIELD`（采蓮曲） | 1 | 0.05% |

**真实缺陷是"归属冲突"（同一文本挂两个人名），不是"字段取错"。**

若按 R2-14 的说法做批量修复，会**改坏 1,831 条本来正确的姓名**。本轮据此撤回该表述（见 `R2_14_ERRATA.md`），并只登记不修库。

可确证的字段污染另有全库口径 **376 条（11.0%）**：`ALIAS` 259、`HONORIFIC` 73、`WRONG_FIELD` 30、`COLLECTION_NAME` 14；其中 `金元好問編` 24 条是"编者当作者"的典型。

### 5.3 未处理

`TITLE_POLLUTION`（人名+书名黏连）在 1,678 组内为 0，但库内 6 个「人名《剧目》」署名共 1,614 条（高明 377、柯丹邱 340、施惠 277、徐田臣 276、刘唐卿 210、萧德祥 134），属另一任务。

---

## 6 元曲完整性（R2-15C4）

| 维度 | 结果 |
|---|---|
| 来源匹配 | **4,510 / 4,510 = 100% `SOURCE_EXACT`**（0 VARIANT、0 ABSENT） |
| 作品完整 | **仅 2,739 / 4,510 = 60.7% `COMPLETE`** |
| 标题占正文（`TITLE_ONLY`） | 1,727（38.3%） |
| 源截断（`TRUNCATED`） | 41（0.9%） |
| 无法判定（`AMBIGUOUS`） | 2（0.04%） |
| 仅对白（`DIALOGUE_ONLY`） | 1（0.02%） |
| 空正文（`EMPTY_BODY`） | 0 |

**因为 `match_level` 全部落在 `SOURCE_EXACT` 一个格子，它在这批数据上没有任何区分能力。** 真正有区分力的是 `completeness`：约 **39.3%（1,771/4,510）** 不是可用完整作品，而这个事实在"来源匹配 100%"的口径下被完全掩盖。

一句话：**匹配率证明导入管道没篡改，完整性评价的是上游数据本身残缺，两者不能互相担保。**

交付：`YUANQU_COMPLETENESS_4510.csv`、`YUANQU_COMPLETENESS_SUMMARY.md`、`YUANQU_TRUNCATION_RECHECK_20.csv`、`YUANQU_RECOVERY_TRIAD.csv`。

---

## 7 来源定位（R2-15C3）

214 个 `COUNT_MISMATCH` 来源已逐源比对完成，逐条结果在 `SOURCE_COUNT_MISMATCH_214.csv`。

### 7.1 原因分布

| probable_cause | 来源数 | 含义 | 建议匹配规则 |
|---|---|---|---|
| `IMPORT_FILTER` | 126 | 导入时按「重复标题/空段落」过滤 | `title_raw` 精确匹配，缺口计为未入库 |
| `IMPORT_FILTER_EDGE` | 80 | 少量过滤（空正文、非诗记录） | `title_raw` 精确匹配即可对齐 |
| `SHARD_OVERLAP_OR_SPLIT` | 8 | 跨分片重叠或分片切分 | `(title_raw, author)` 联合键去重后对齐 |

### 7.2 结论

- **绝大多数差额是「上游过滤」，不是「记录错位」**：206/214 个来源的缺口可由导入过滤解释；
- 只有 8 个来源涉及分片重叠，需要联合键去重；
- 因此"214 个来源全部可恢复下标"不成立——被过滤掉的记录根本不在 `works` 里，恢复下标只能覆盖已入库部分。

### 7.3 定位级别（不变）

| 指标 | 值 |
|---|---|
| 来源记录 / 在用文件 | 941 / 819 |
| 可下标定位来源 | 551 |
| 覆盖作品 | 164,217（43.7%） |
| `juan` / `page` / `base_edition` | 0 / 0 / 0 |

不把"有 `source_id`"说成"能定位到卷页版本"；本轮未写入任何定位结果。

## 8 细读卡与词谱（R2-15C5）

- 30 张卡片状态不变：`MINOR_ISSUE` 16 / `UNVERIFIABLE` 8 / `NOT_REVISED` 5 / `MAJOR_ISSUE` 1，**`CLEAN` = 0**，不标为范例。
- 词谱 11 个区域映射保留为图像定位成果，`GRADE_UNCONFIRMED` **不升级**。
- 本轮未据此扩规则、未改引擎。

---

## 9 测试有效性整改（R2-15D）

四项无效断言已修，**期望值除下述外一律未改**：

| 编号 | 原问题 | 新断言 |
|---|---|---|
| T21 | `all([])` 空过 | 断言恰 29 行且全 `EXACT` |
| T26 | `if False` 死分支 | 解析 Markdown，断言 `SOURCE_VERIFIED = 0` |
| T74 | `>= 0` 恒真 | 断言 `_r2_14` 表数 `== 0` |
| T75 | 硬编码 `True` | 整库 SHA 与 R2-14 基线比对 |

测试分层：`tools/r2_15_tests.py` 分 A 组（公开归档，12 项，不需 DB）与 B 组（本地 DB，8 项，缺库标 `NOT RUN`），支持 `--db` 与 `POETRY_DB`。

---

## 10 文档统一（R2-15E）

| 文件 | 变更 |
|---|---|
| `README.md` | 重写：如实定位为"文献研究仓库 + 冻结引擎原型，**不是已发布 Skill**"；统计改为 375,399 / 20,809 作者记录 / 941 来源 / 732 MB / 108 表；补"数据库不在仓库 + 如何接入"；列出 E01/E02 已知缺陷；补阶段门禁与许可 |
| `poetry-database/README.md` | 统计从 90,279 / 5,286 / 128 / 95 MB / 7 表更新为实测值；说明作者记录≠人物数 |
| `AGENTS.md` | 补"公开仓库只放报告代码元数据样本"与"每轮先同步再报告"两条硬性边界；轮次成果更新至 R2-15 |
| `LICENSE` | 新增 MIT |
| `docs/README_ORIGINAL.md` | 旧 README 备份（工具不再覆盖 README） |
| `REPORTS_INDEX.md` | 同步工具自动生成，15 轮直链 |
| `UPLOAD_REPORT.md` / `GITHUB_SYNC.md` | 补版权正文排除项与历史遗留链接 |

---

## 11 测试结果

| 套件 | 结果 |
|---|---|
| `r2_15_a_tests.py`（版权排除） | **10 / 10 PASS** |
| `r2_15_tests.py`（归档 + DB 分层） | **20 / 20 PASS**，0 NOT RUN |
| `r2_14_tests.py`（四项已修） | **80 / 80 PASS** |
| `r2_09` ~ `r2_13` 回归 | 71/71、**79/80（T60 历史失败）**、68/68、68/68、80/80 |
| 引擎独立测试 | **33 / 33 PASS** |
| 引擎验收 | **6 / 6 PASS** |

`r2_10` 的 T60 期望"六套体系未被合并"=6，实测 4，属历史失败，期望值未改；R2-14 记录的 T12 本轮已通过，与旧记录不一致，如实登记，不追溯改旧报告。

副作用登记：运行 `run_acceptance.py` 写入 12 个产物文件（创作库 8、验收记录 2、日志 2），属测试产物。

---

## 12 修改文件清单

**代码/工具**

- `poetry-database/tools/github_sync.py`（白名单收窄、黑名单、删除规则重写、README 不覆盖、REPORTS_INDEX）
- `poetry-database/tools/r2_14_tests.py`（T21/T26/T74/T75）
- `poetry-database/tools/r2_15_a_tests.py`（新增）
- `poetry-database/tools/r2_15_tests.py`（新增）

**文档**

- `README.md`（重写）、`LICENSE`（新增）、`AGENTS.md`、`poetry-database/README.md`
- `raw/r2_04_evidence/README_CHARCOUNT.md`（新增）
- `reports/tasks/2026-11-13/R2-04/ERRATA_PUBLIC_SYNC.md`（新增）
- `reports/tasks/2026-11-16/R2-14/R2_14_ERRATA.md`（新增，更正 1,017 定性）

**R2-15 交付**

`COPYRIGHT_HISTORY_IMPACT.md`、`COPYRIGHT_SYNC_AUDIT.md`、`COPYRIGHT_CHARCOUNT_DIFF.csv`、`BOOK_CATALOG_52.csv`、`READING_RECORD_AUDIT.md`、`MISSING_MATERIALS.csv`、`WORKS_339_EVIDENCE_CLOSURE.csv/.md`、`AUTHOR_WRONG_FIELD_1017.csv`、`AUTHOR_WRONG_FIELD_GROUPS.csv`、`AUTHOR_WRONG_FIELD_SUMMARY.md`、`AUTHOR_FIELD_POLLUTION_UNIVERSE.csv`、`YUANQU_COMPLETENESS_4510.csv`、`YUANQU_COMPLETENESS_SUMMARY.md`、`YUANQU_TRUNCATION_RECHECK_20.csv`、`YUANQU_RECOVERY_TRIAD.csv`、`TEST_RESULTS_R2_15.md`、`TEST_EXPECTATION_CHANGELOG_R2_15.md`

**未改**：`works` / `authors` / `sources` 任何字段；R2-13 三表；格律引擎代码；`tests/06_cipai.json` 期望值。

---

## 13 未解决问题

| 项 | 状态 | 原因 |
|---|---|---|
| Git 历史重写 | **待授权** | 需用户选 A/B/C，未擅自 force push |
| 214 个 `COUNT_MISMATCH` 来源的**逐条**下标恢复 | 未做 | 原因已分类，恢复需逐源实现，本轮只给规则不写结果 |
| 1,017 vs 1,032 完全对齐 | **不做** | R2-14 分类脚本未保留，以可复算值为准 |
| `books` 表陈旧（13 行） | 未改 | 涉及表结构变更，需单独授权 |
| 版本错位（四库本 vs 校注本） | 登记 | 需获取合法版本，非本轮范围 |
| E01/E02 引擎缺陷 | 未修 | Phase 4 冻结，且 C05 期望值需一并修正 |
| 1,831 条同文异署归属 | 只登记 | 需别集校勘 |

---

## 14 下一轮建议（R2-16）

1. **先定 Git 历史处置**（A/B/C），否则版权问题始终留一个尾巴。
2. **C3 补完**：214 个来源逐源设计匹配规则，只允许唯一定位写入候选表。
3. **作者字段分两路**：376 条可确证污染可按类型修（`COLLECTION_NAME`、庙号 `HONORIFIC`）；1,831 条归属冲突只登记不自动改。
4. **文献版本级核对**：把"读过"升级为"读过某版本"，需先取得合法校注本。
5. **元曲**：1,727 条 `TITLE_ONLY` 的边界修复要单独做，且必须与完整性评价分开报告。

---

## 15 阶段边界

本轮只做 Phase 0–2 的资料质量与同步治理：

- 未进入 Phase 3 知识体系；
- 未改格律引擎（E01/E02 只记录）；
- 未做 Phase 5–7 任何工作；
- 未宣布任何阶段获授权。

**最终状态：PARTIAL。** 未完成项已列入 §13，不隐藏。
