# AGENTS.md —— 诗词项目长期指令

本文件是执行 Agent 进入本项目后必须首先读取并遵守的长期指令。
它与 `AGENT_REPORTING_STANDARD.md` 共同构成项目规范，优先级高于任何单轮任务的临时交代。

---

## 1. 角色

| 角色 | 承担方 | 职责 |
|---|---|---|
| 执行 Agent | 本项目中的 AI | 实际建设、修改、测试、汇报 |
| 用户 | 项目所有者 | 向外部审核者转交材料、决定是否进入下一轮 |
| 外部审核者 | ChatGPT | 独立审核、发布整改要求、阶段门禁、最终验收 |

执行 Agent **不得自行认定成果合格**，也不得自行进入下一阶段。

## 2. 项目根目录

```
<PROJECT_ROOT>/
├── AGENTS.md                    本文件
├── AGENT_REPORTING_STANDARD.md  永久汇报制度（必读）
├── docs/                        项目原始方案与历史文档
├── 诗词格律引擎/                 工程实体
│   ├── engine/                  格律引擎与测试执行器
│   ├── tools/                   数据构建与审计脚本
│   ├── tests/                   独立测试集（样本先于结论存在）
│   ├── 诗歌知识库/               01 基础 / 02 作品 / 03 鉴赏 / 04 韵书 / 05 创作 / 06 迭代
│   ├── 计划/
│   └── reports/                 每轮汇报与审核材料
└── ...
```

> 历史交付快照位于 `<LOCAL_WORKBUDDY>/2026-11-09/诗词格律引擎/`（v1，已被本目录取代）。
> **当代有效根目录只有本目录下的 `诗词格律引擎/`。** 任何编辑都不得再写入历史快照。

## 3. 铁律

1. **每次任务结束必须写完整报告**，格式见 `AGENT_REPORTING_STANDARD.md` 第二章十三章。
2. **不得按格律反推读音。** 读音无法确定时输出 `UNKNOWN`，不得为让结论好看而选音。
3. **不得把无法判定的情况说成通过。** `UNKNOWN` 与 `PASS` 是两种状态，输出必须区分。
4. **不得虚构来源。** 规则必须有出处；没有出处的必须写 UNKNOWN 或标注为「工程政策」。
5. **不得修改黄金测试集来迁就引擎。** 若引擎与权威样本冲突，先查引擎，再查数据，最后才怀疑样本，并留下书面判断。
6. **不得删除失败日志。** 失败记录是审核材料的一部分。
7. **完成后停止。** 输出报告与下一步建议，等待用户转交外部审核。

## 4. 状态词表

| 状态 | 含义 |
|---|---|
| `PASS` | 固定位置，规则匹配 |
| `FLEXIBLE` | 可平可仄位置，不作违律判定 |
| `FLEXIBLE_READING` | 两读字按声明政策放宽，**不计为通过** |
| `FAIL` | 固定位置，平仄相反 |
| `UNKNOWN` | 读音或韵部无法确定，需人工判定 |
| `NOT_CHECKED` | 当前规则未执行检查 |

结果判定码（`判定` 字段）只有四个：`合格` / `待确认` / `违律` / `不适用`。
对外表述必须使用这四个词之一，禁止自创「基本合格」「大体通过」等说法。

## 5. 常用命令

```bash
cd 诗词格律引擎

# 校验一首诗 / 一首词
python3 engine/gedou.py --title "秋山" --text "山色苍茫暮雨收……"
python3 engine/gedou.py --cipai 浣溪沙 --ci "一曲离歌送客舟……"

# 重建韵书索引（改动了平水韵_全表_繁体.json 时）
python3 tools/build_lexicon.py

# 独立测试集（样本在先，期望值写死在 tests/*.json）
python3 engine/run_tests.py

# 六道验收题（自测，不能替代独立测试集）
python3 engine/run_acceptance.py

# 多音字待消歧清单
python3 tools/collect_polyphones.py

# 权威名篇探测（前后对照证据）
python3 tools/capture_probe.py --out reports/round-1-audit/logs/probe_after.txt
```

## 6. 每轮任务的最小交付

1. 代码与数据改动（可运行）。
2. `reports/execution-history/<日期>/<TASK-ID>/` 下的四件套 + LOGS。
3. `reports/<round>/` 下的专题审计报告。
4. 对话中的完整汇报正文。
5. 明确的下一步建议（只建议，不执行）。

## 7. 当前阶段

**项目路线：先建资料，再建规则。**

| Phase | 内容 | 状态 |
|---|---|---|
| Phase 0 | 文献搜集与来源调查 | PARTIAL（52 条书目，34 条未取得） |
| Phase 1 | 书籍与文献实际阅读 | **王力合订本 A/B/C/D 通读 106,460 字（31/31 READ）；《词学十讲》74,652 字（9 讲 READ ＋ 第六讲 READ_WITH_SOURCE_GAP）。R2-07 转做词律数据，未增阅读** |
| Phase 2 | 经典诗词作品数据库 | 375,399 条；辽代 0；本轮未扩充 |
| Phase 3 | 知识提炼与交叉研究 | **未授权，不得开工** |
| Phase 4 | 格律与韵书引擎 | **冻结** |
| Phase 5–7 | 创作体系／能力测试／Skill 封装 | **未授权** |

> 2026-11-13 更正：R2-03 曾错误结论「PaddleOCR-VL-1.6 在本环境不可用」。
> 该能力实为已接入的用户级 skill（公网 SaaS API 客户端），当时缺的只是 token。
> R2-03-R1 已补凭据并重跑；勘误见 `poetry-database/reports/tasks/2026-11-13/R2-03-R1/ERRATA.md`。
>
> **同轮更严重发现**：R2-03 的 macOS Vision OCR 结果有 **1,487/1,691 页为「每 16 页一批」的复制填充**，
> 三本实际只有 94/45/64 份不同文本，其「1,691 页 OCR / 140 万字」口径作废。
> `book_pages` 原样保留但**不得作为逐页原文引用**；逐页对照数据已标记 `baseline_valid=0`。
> 有效逐页文本改用 `book_pages_paddle`（1,691 行，engine=PaddleOCR-VL-1.6）。
> R2-03 的 16 条 `theory_claims` 引文页码须逐条回查后方可引用。
> **R2-05 已处理**：id=15 状态改为 `RETIRED_MISATTRIBUTED`（禁止进入有效检索），
> 并以 `theory_claims_v2` 的 `R05-CL-001` 重建；其余 15 条仅加复核注记，未升级。
>
> **R2-04 补充**：合订本实为**四部分**（《诗词格律》印刷1／《诗词格律概要》175／
> 《诗词格律十讲》339／附录与索引 399、407），印刷页 = PDF 物理页 − 8。
> 复核发现 `theory_claims` id=15「孤平」的出处、页码、引文三重错误：
> 「只限于平脚的句子」实出《诗词格律十讲》p374（印刷366），非《诗词格律》p42，
> 引文「我宿五松下」当时判为全书 0 命中（**R2-06 已推翻：该诗在 A p45、B p239、D p410 共 4 处出现，
> 原书索引 p427 直接给出 34,37,47,231,402；只有「只算拗句」四字不存在**）。
> 《唐宋词格律》重建为 135 定格＋9 变格＝144 条索引（`cipai_index`），仍是候选数据。
>
> **R2-06 更正**：`cipai_index` 的 135 定格经以原书目录 153 调为骨架重算，**仍为 135**（正确）；
> 但 R2-05 报的「定格 143、变格 27」是把关键词出现次数当条目数，实测为定格 135、变格 7。
> 词牌目录现为 `cipai_catalog_r2_06`（153 调）＋`cipai_ge_records_r2_06`（194 条格记录：
> 定格135／格一18／格二20／格三7／格四2／格五1／变格7／别格4），29 调含多格，0 调缺格记录。
> 三版计数对照见 `cipai_gap_r2_06`；仍属候选数据，**未逐调核谱**。
>
> **R2-06 阅读状态**：C《诗词格律十讲》12 单元 13,601 字、D 附录与索引 2 单元 4,665 字全部 READ；
> 所有页码三处互证后确定为「PDF＝印刷＋8」，逐页映射存 `page_map_wangli`（432 行）。
>
> **R2-07 更正**：R2-06 报《词学十讲》10/10 READ 不成立——第六讲 `gate_pass=0`（EPUB 失后半例词），
> 已改 `READ_WITH_SOURCE_GAP`，其余九讲 READ。合订本末页（物理 432＝索引 423）已核验并补注。
> 词格数由 R2-06 的 194 更正为 **196**（漏采《念奴娇》「变 格 一」「变 格 二」）；
> 新表 `cipai_entities_r2_07`(153)／`cipai_forms_r2_07`(196)／`cipai_form_sources_r2_07`(1,392 行) 等 10 表，
> 旧表 `cipai_specs`／`cipai_index`／`cipai_catalog_r2_06` 一律保留不动。
> `EDITION_VERIFIED` 仍为 **0**。
> 阅读进度严格区分 PARSED / EXTRACTED / READ，本轮无单元标 READ。

### 汇报制度

自 2026-11-12 起按 `AGENT_REPORTING_STANDARD.md` **v2.0** 执行：
每个独立任务必须产出 `reports/tasks/YYYY-MM-DD/TASK-ID/COMPLETE_REPORT.md`（十三章），
并在对话中直接输出完整汇报。质量等级词表（RAW→PARSED→SOURCE_TRACEABLE→TEXT_CROSSCHECKED→EDITION_VERIFIED→SCHOLARLY_REVIEWED）与术语规范见该文件第 6、7 节。

### 硬性边界

- 现代版权著作（王力、龙榆生等）不得抓取全文，只能登记书目与合法渠道。
- 未经外部审核批准，不得进入 Phase 3、不得改格律引擎、不得封装 Skill。
- **公开仓库只放报告、代码、元数据与样本。** `database/`、`normalized/`、`books/`、
  `raw/r2_04_evidence/full|chapters`（现代版权著作章节正文）一律不得进入公开仓库；
  同步后必须复核远端这些路径计数为 0。历史遗留见 `COPYRIGHT_HISTORY_IMPACT.md`。
- 每轮任务完成，先执行 `python3 poetry-database/tools/github_sync.py` 并复核远端，
  再输出带上传结果的完整报告。

- 当前轮次成果：`poetry-database/reports/tasks/2026-11-20/R2-15/`（公开同步版权整改、Phase 0–2 基线核对、数据质量治理）
- R2-14 成果：`poetry-database/reports/tasks/2026-11-16/R2-14/`（来源追溯与文本重建证据闭环）
- R2-13 成果：`poetry-database/reports/tasks/2026-11-16/R2-13/`（重复与元曲文本审计）
- R2-12 成果：`poetry-database/reports/tasks/2026-11-16/R2-12/`（广韵、集韵、新韵与作品库复核）
- R2-11 成果：`poetry-database/reports/tasks/2026-11-15/R2-11/`（词谱影印与例词核验）
- R2-10 成果：`poetry-database/reports/tasks/2026-11-15/R2-10/`（三十首精读卡与抽样质量）
- R2-09 成果：`poetry-database/reports/tasks/2026-11-14/R2-09/`（词谱逐符号核验）
- R2-08 成果：`poetry-database/reports/tasks/2026-11-14/R2-08/`（例词关联与词牌实体）
- R2-07 成果：`poetry-database/reports/tasks/2026-11-14/R2-07/`（196 条词格逐项核验与词牌数据库）
- 每轮报告直链索引：仓库根 `REPORTS_INDEX.md`
- R2-06 成果：`poetry-database/reports/tasks/2026-11-13/R2-06/`（C/D 通读、词牌目录盘点）
- R2-05 成果：`poetry-database/reports/tasks/2026-11-13/R2-05/`（A/B 两书完整阅读与理论提取）
- R2-04 成果：`poetry-database/reports/tasks/2026-11-13/R2-04/`（章节索引与局部精读）
- R2-03-R1 成果：`poetry-database/reports/tasks/2026-11-13/R2-03-R1/`（OCR 重跑与勘误）
- R2-03 成果：`poetry-database/reports/tasks/2026-11-13/R2-03/`（已加勘误告示）
- 引擎整改成果：`诗词格律引擎/reports/round-1-audit/`，**代码冻结，仅作研究工具**
- 下一阶段（Phase 3 知识体系）**未获授权，不得开工**。

### 重要约束（继承自 ROUND 1）

1. **不得再用「凭已有知识整理规则」的方式写格律规则。** 任何规则须有文献出处，否则标 UNKNOWN。
2. **数据库只能统计，不能引用。** 语料为二手整理，已证存在错字。
3. **异文不择优、归属不裁决。** 多源并列，由文献学解决。
4. **不得为凑覆盖使用 OCR 残本或无来源数据。** 宁可留空。
