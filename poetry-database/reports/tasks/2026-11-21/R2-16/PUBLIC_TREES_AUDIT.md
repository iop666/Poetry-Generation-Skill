# PUBLIC_TREES_AUDIT —— 八棵公开目录树文件级审计（R2-16C 第二轮）

- 日期：2026-11-21
- 审计依据：外部审核要求「对八棵目录树全部进行公开文件清单核对；优先逐文件白名单；未来新增文件默认不公开」
- 审计对象：原 `INCLUDE_TREES` 八棵树在本地项目的全部文件（818 个）
- 审计方法：
  1. 全量枚举（路径/字节/扩展名，含最大文件核查）；
  2. 全量文本风险扫描（本机路径/手机号/API 凭据/邮箱，脚本 `tree_risk_scan.py`，日志 `LOGS/tree_risk_scan.log`）；
  3. 二进制与非常规扩展名逐个定位检查；
  4. 高风险区抽样精读（知识库、数据 JSONL、书目、文档）。
- 审计结论：**842 个文件登记进逐文件白名单 `poetry-database/tools/public_files.txt`；3 个文件排除**。
  排除项全部记录在案；风险扫描零实质命中。

## 1. 逐树审计结果

### docs/（5 文件，42,834 字节）——全部登记

| 文件 | 性质 | 分类 | 决定 |
|---|---|---|---|
| README.md | 项目自述 | ORIGINAL_RESEARCH_SUMMARY | 登记 |
| README_ORIGINAL.md | 原 README 备份（工具恢复源） | 同上 | 登记 |
| 实施报告.md | 建设期文档 | 同上 | 登记 |
| 实施汇报.html | 建设期汇报 | 同上 | 登记 |
| 验收测试记录.md | 验收记录 | 同上 | 登记 |

### 诗词格律引擎/（70 文件，1,365,641 字节）——登记 69，排除 1

| 区块 | 文件数 | 性质 | 分类 | 决定 |
|---|---:|---|---|---|
| engine/ | 若干 .py | 格律引擎代码（冻结） | ENGINEERING | 登记 |
| tools/ | .py | 数据构建/审计脚本 | ENGINEERING | 登记 |
| tests/ | .json | 独立测试集（样本先于结论） | DATA | 登记 |
| reports/round-1-audit/ | md/log/err | 整改报告与日志 | PROJECT_DOCUMENTATION | 登记（含空文件 probe_after.err，保留审计痕迹） |
| 诗歌知识库/01_基础库 | 4 md | 典故/对仗/意象/格律规则——**已精读**：原创整理，无逐字现代版权文本 | ORIGINAL_RESEARCH_SUMMARY | 登记 |
| 诗歌知识库/02_作品库 | 1 json | 唐诗精选标注（**精读头部**：唐诗正文＋原创标注；唐诗为公有领域） | PD_DATA | 登记 |
| 诗歌知识库/03_鉴赏库 | 1 md | 诗话摘录——**已全文精读**：全部引自古典诗话（王国维卒 1927、严羽/欧阳修/苏轼/姜夔/叶燮/沈德潜均公有领域）＋原创「用法」栏 | PD_QUOTATION＋ORIGINAL | 登记 |
| 诗歌知识库/04_韵书 | 6 json/md | 平水韵/词林正韵/中华新韵——韵书事实数据 | FACTUAL_METADATA | 登记 |
| 诗歌知识库/05_创作库 | 8 md | 项目原创诗稿（秋山、浣溪沙等） | ORIGINAL_WORKS | 登记 |
| 诗歌知识库/06_迭代记录 | 2 | 验收测试记录 | PROJECT_DOCUMENTATION | 登记 |
| **__pycache__/github_sync.cpython-314.pyc** | 1 | Python 编译缓存 | NOISE | **排除**（不登记，默认拒绝） |
| 计划/、报告/ | md | 计划与报告文档 | PROJECT_DOCUMENTATION | 登记 |

### poetry-database/reports/（554 文件，33,998,882 字节）——全部登记

- 构成：R2-03 至 R2-15 各轮 `COMPLETE_REPORT.md`、审计 CSV、交付件、LOGS（md/csv/json/jsonl/log/sha256）。
- 性质：项目自产文档与数据审计产物；本轮风险扫描 0 命中（无本机路径泄漏——泄露的路径模式在导出时另有脱敏兜底；无手机号；无凭据）。
- 大文件核查：最大 4.26MB（R2-11 guangyun_entries.json，广韵条目数据，公有领域韵书事实数据），其余大文件均为韵书/集韵/元曲审计 CSV（事实数据）。
- 分类：PROJECT_DOCUMENTATION＋FACTUAL_DATA。**决定：全部登记**（与既有公开范围一致）。

### poetry-database/tools/（159 文件，1,676,019 字节）——登记 156，排除 2

| 文件 | 性质 | 分类 | 决定 |
|---|---|---|---|
| 全部 .py（186 个中的大部分） | 审计/构建/同步脚本 | ENGINEERING | 登记 |
| **ocr_vision** | **macOS Mach-O 二进制（Swift 编译的 OCR 客户端）** | BINARY | **排除**——二进制可能内嵌端点/密钥字符串，公开无价值且不可审计内容；已公开，批准后的同步将从远端删除 |
| **__pycache__/github_sync.cpython-314.pyc** | 编译缓存 | NOISE | **排除** |
| ocr_vision.swift | Swift 源码（53 行，**已扫描**：无 token、无密钥、无硬编码端点，注释明言"零 token 离线"） | ENGINEERING | 登记 |
| github_sync.py | 同步工具（v3） | ENGINEERING | 登记 |
| **public_files.txt**（新增） | 逐文件公开白名单（842 行） | GOVERNANCE | 登记 |
| **public_redactions.json**（新增） | 导出时改写规则（4 条，见 COMPLETE_REPORT 第二轮） | GOVERNANCE | 登记 |
| **make_public_evidence.py**（新增） | 公开证据生成器 | ENGINEERING | 登记 |
| r2_12_facsimile.py / r2_12_jiyun.py | 抓取脚本；风险扫描命中邮箱 `researcher@example.org`——**核实为 UA 占位符**（example.org 保留域），非真实联系方式 | ENGINEERING | 登记 |

### poetry-database/catalog/（6 文件，8,433,536 字节）——全部登记

| 文件 | 性质 | 分类 | 抽查 | 决定 |
|---|---|---|---|---|
| authors.jsonl（4.50MB） | 作者元数据（author_id/朝代/作品数） | FACTUAL_METADATA | 第 1 行核验 | 登记 |
| works_sample.jsonl（3.16MB） | 作品样本文本（首行《诗经·关雎》） | PD_DATA | 第 1 行核验 | 登记 |
| sources.jsonl（0.61MB） | 来源登记（URL/许可证，自述"只收公有领域古籍与明确许可的开放数据集"） | FACTUAL_METADATA | 第 1 行核验 | 登记 |
| books.jsonl（4.8KB） | 书目登记（**首行核验**：王力《诗词格律》，license 字段明记"现代版权，未取得授权，未采集全文"——书目符合硬边界） | FACTUAL_METADATA | 前 2 行核验 | 登记 |
| cards.jsonl / collections.jsonl | 词牌卡片/集合元数据 | FACTUAL_METADATA | — | 登记 |

### poetry-database/research/（7 文件，203,164 字节）——全部登记

acquisition_log.jsonl、ws_fetch_log.jsonl 等采集日志 + tao/wenxuan 抓取记录。分类：PROCESS_LOGS。决定：全部登记。

### poetry-database/audit/（13 文件，918,916 字节）——全部登记

acquisition_log、author_canon_report、coverage、duplicate_report、parsing_log、quality_report、crosscheck_refine 等。分类：AUDIT_METADATA。决定：全部登记。

### poetry-database/sources/（4 文件，1,003,709 字节）——全部登记

manifest.json（875KB，采集范围清单，头部核验："只收公有领域古籍与明确许可的开放数据集；不绕过付费墙/登录与反爬限制"）、t300_index.json、tao_index.json、ws_pages.json。分类：FACTUAL_METADATA。决定：全部登记。

## 2. 全量风险扫描结果（LOGS/tree_risk_scan.log）

| 扫描项 | 结果 |
|---|---|
| 文本文件（20 种扩展名） | 819 个全部成功按 UTF-8 解码，0 解码失败 |
| 二进制/非常规文件（除已排除的 ocr_vision、__pycache__） | **0 个** |
| 手机号模式 | 0 命中 |
| API 凭据模式（Bearer/sk-/ghp_） | 0 命中 |
| 本机用户目录前缀模式（macOS 与 Windows 两种形态） | 3 个文件命中，全部良性：① R2-16 测试报告（引用脱敏测试字符串本身）② github_sync.py（脱敏正则字面量，脚本设计如此，且导出时 NO_SANITIZE 保护） |
| 邮箱模式 | 2 个文件命中，均为 `researcher@example.org` UA 占位符 |

## 3. 排除与登记总账

| 项 | 数量 |
|---|---:|
| 八棵树文件总数 | 818 |
| 排除（ocr_vision、__pycache__/*.pyc） | 2 |
| 八棵树登记 | 816 |
| 顶层登记（AGENTS.md、AGENT_REPORTING_STANDARD.md） | 2 |
| raw/ 区登记（cipai index、manifest、README_CHARCOUNT、2 个 *_public.json、13 个笔记、3 个 r2_07 JSON） | 20 |
| tools 新增登记（public_files.txt、public_redactions.json、make_public_evidence.py） | 3 |
| **public_files.txt 登记总数** | **842**（与文件实际行数核对一致；`comm` 校验八棵树无遗漏） |

## 4. 默认拒绝机制

- `github_sync.py` v3 只导出 `public_files.txt` 登记的文件；
- 每次运行（含 dry-run）输出「默认拒绝审计」：位于原八棵树根下但未登记的文件清单；
- 新增文件必须先通过公开审计并登记，否则**静默不导出**（dry-run 可见），不会进入公开仓库。

## 5. 审计局限性（如实声明）

1. 554 个 reports 文件按"项目自产文档"整类登记，仅对大文件与扩展名异常逐个核查，未逐文件通读正文；其内容均为历轮已公开材料的本地副本（与 GitHub 现状同源）。
2. 186 个 .py 按"工程代码"整类登记，未逐文件人工审读；风险扫描覆盖凭据/路径/手机号模式。
3. 知识库 22 文件中 4 个精读（格律规则、诗话摘录、作品库头部、创作库抽样）、其余按目录性质分类——创作库为项目原创诗稿、韵书为事实数据。
4. 审计不含 poetry-database/raw（R2-16B 第一轮已逐文件审查）与数据库区（硬排除，不属本 Agent 职责）。

## 6. 第二轮补记：公开文件回填登记（干净克隆枚举重生成）

第一轮白名单从本地旧项目目录枚举（842 文件）。切换同步源到干净克隆后，dry-run 的默认拒绝审计发现 **37 个公开文件不在清单内**——它们位于公开仓库 main `37ee224`，但旧项目目录里没有对应文件（历史上由暂存克隆直接生成并同步，如 R2-15 全部轮次交付件、R2-04/R2-14 勘误、r2_15 测试工具）。逐个判定：

| 处理 | 数量 | 明细 |
|---|---:|---|
| **登记保留**（已是过审公开内容，随干净克隆成为同步源） | 36 | R2-15 全部交付件（31 个：COMPLETE_REPORT、COPYRIGHT_SYNC_AUDIT、AUTHOR_FIELD_POLLUTION_UNIVERSE 等 CSV/MD/LOGS）、`R2-04/ERRATA_PUBLIC_SYNC.md`、`R2-14/R2_14_ERRATA.md`、`tools/r2_15_a_tests.py`、`tools/r2_15_tests.py` |
| **确认删除**（审计排除项，随批准后的同步从远端移除） | 1 | `tools/ocr_vision`（macOS 二进制） |

- 白名单改用**干净克隆树枚举**重新生成（今后的同步源），最终 **886 个文件**；树下未登记剩余仅 `ocr_vision` 1 个（预期删除项）。
- 回填含义修正：这 36 个文件的"本地原件"就是干净克隆工作树（内容与公开逐字节同源），不再是旧项目目录。
- 附带发现：本地旧项目目录缺失整个 R2-15 报告目录——进一步证实该目录是过时快照，退役建议见 COMPLETE_REPORT §14.8。

## 7. 最终对账（四数字统一口径，R2-16C-POST-PUSH-CLOSEOUT，权威版本）

> 本节取代 §3 总账与 §6 中的时点数字。842 / 886 / 887 是**同一份白名单在三个时点的快照**，不是并行口径；
> §3 的两处算术笔误已在下表更正（raw 区应为 21 项而非 20，即 816+2+21+3=842 成立；tools 159 = 登记 157 + ocr_vision + __pycache__ pyc 各 1，"登记 156" 系笔误）。
> 机器可复核输出：`LOGS/count_reconciliation.log`（count_reconciliation.py）。

| 口径 | 数值 | 说明 |
|---|---:|---|
| ① 源目录枚举总文件数 | **890** | 同步源（干净克隆）八棵树 + 顶层 2 + raw 显式区；**含 public_files.txt 自身**；不含保护文件（README/LICENSE）、6 个工具生成文件、.git 与 __pycache__ |
| ② 审核通过白名单登记数 | **889** | `tools/public_files.txt` 条目数（含其自身登记） |
| ③ 实际导出/远端发布 blob 数 | **897** | verify-final HEAD 树 = 889 Manifest + 保护 2 + 生成 6（推送时 VERIFY PASS 断言） |
| ④ 默认拒绝/排除文件数 | **1** | `tools/ocr_vision`（唯一枚举内未登记项；批准后同步已从远端删除） |

逐树核对（枚举/登记）：docs 5/5；诗词格律引擎 70/70；reports 599/599；tools 163/162（差=ocr_vision）；catalog 6/6；research 7/7；audit 13/13；sources 4/4；顶层 2/2；raw 显式区 21/21（**审核者怀疑的 raw=21 坐实**：cipai_index 1 + manifest 1 + README_CHARCOUNT 1 + 两个 *_public.json 2 + 笔记 13 + r2_07 3）。

快照沿革（同一清单的时点演进）：842（旧项目目录枚举，第一轮审计）→ 886（干净克隆枚举 + R2-16 报告定稿）→ 887（+redaction_dryrun.log）→ 889（+run_real_push.log / run_e_clean_dryrun.log，push #2 实际导出 889）。

审计深度表述（按审核要求准确化）：本轮完成的是**全量文件枚举、扩展名与二进制审查、凭据/手机号/路径模式扫描、高风险区定向精读、白名单控制**；554 个 reports 文件与 186 个 .py 未逐文件通读正文（见 §5 局限性声明）。不得表述为"818 个文件的全部内容均已人工审查"。
