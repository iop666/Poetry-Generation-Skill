# SOURCE_AUDIT —— R2-16B 现代文献摘录逐条审查

- 审查日期：2026-11-21
- 审查对象：`poetry-database/raw/` 下 15 个文件（2 份 JSON + 13 个阅读笔记）
- 审查方式：全文逐文件通读 + 脚本统计引文跨度（`LOGS/quote_stats.log`）
- 分类词表：ORIGINAL_RESEARCH_SUMMARY / FACTUAL_METADATA / SHORT_QUOTATION / EXTENSIVE_QUOTATION / CLOSE_PARAPHRASE / COPYRIGHT_UNCLEAR
- 统计口径：JSON 取实际公开字段（`head`/`quote`）的字符数；笔记取「」『』引文跨度（注：跨行嵌套引文会被该正则低估，长段落另行人工标注）
- 决定词表：`保留公开` / `暂停公开（WITHHELD）` / `REVIEW_REQUIRED`

## 0. 底本与来源

| 书 | book_id | 版本 | 页码口径 | 版权状态（中国大陆，著作权法：作者终生＋卒后 50 年） |
|---|---|---|---|---|
| 王力《诗词格律》《诗词格律概要》《诗词格律十讲》《附录：诗词的平仄》合订本 | wangli_shicilv 等 | 中华书局合订本，PDF 432 页 | 印刷页 = PDF 物理页 − 8（R2-06 三处互证） | **王力卒于 1996，保护期至 2046 年底，仍在版权期内** |
| 王力《汉语音韵学》 | wangli_yinyunxue | 同上合订本卷 | 同上 | 同上 |
| 王力《同源字典》 | wangli_tongyuan | 同上合订本卷 | 同上 | 同上 |
| 龙榆生《词学十讲》 | long_cixue_shijiang | EPUB 解析（book_chapters idx 5–14） | 章节 idx | 龙榆生卒于 1966，**大陆保护期已于 2016 年底届满**；但 EPUB 版本整理者权利不明（徐培均序等），且项目铁律将王力、龙榆生著作统一列为受限材料。**按项目规则从严处理** |

> 王力笔记中大量引用的赵执信《声调谱》、王士禛《律诗定体》、王夫之《姜斋诗话》、万树《词律·发凡》、刘勰《文心雕龙》、张炎《词源》等古籍引文均为公有领域，不构成风险。

## 1. r2_04_evidence/ocr_samples.json —— 32 条

性质：R2-04 的 OCR 质量抽样证据。每条含 book_id / page / chars（页字符数）/ has_pingze_symbols 等 5 个布尔标记 / engine / **head（该页 OCR 文本前缀，逐字公开）**。

| 组 | book_id | 条数 | head 逐字合计 | 最长单条 | 页码 | 分类 | 公开必要性 |
|---|---|---|---|---|---|---|---|
| 1 | wangli_shicilv | 12 | 928 字符 | 90 字符（p8 目录页） | 0,8,17,35,41,50,79,125,183,265,340,431 | p0/p8/p183/p431 = FACTUAL_METADATA（书名页、总目录、分册扉页、索引页码）；其余 8 条 = SHORT_QUOTATION（正文片段） | 低：质量证据主要由 chars + 5 个布尔标记承担，head 文本非必需 |
| 2 | wangli_yinyunxue | 10 | 900 字符 | 90 字符（p0） | 0,5,50,100,160,200,260,320,400,475 | p0/p475 = FACTUAL_METADATA；其余 8 条 = SHORT_QUOTATION | 低：同上 |
| 3 | wangli_tongyuan | 10 | 826 字符 | 90 字符（p5） | 0,5,50,100,200,300,400,500,650,782 | p0/p782 = FACTUAL_METADATA；其余 8 条 = SHORT_QUOTATION | 低：同上 |
| 合计 | 3 本书 | **32** | **2,654 字符** | 90 字符 | 跨三本版权书 32 个页位 | 混合 | **低 → 暂停公开** |

审查结论：**WITHHELD（暂停公开，自下一轮同步起从仓库移除）**。理由：32 个采样点均匀覆盖三本版权书，单条虽短（≤90 字），但合计构成对版权书的系统化页序摘样；证据功能（OCR 质量核验）可由 `chars`/布尔标记无损失承担，`head` 字段公开必要性不足。
恢复公开的可能形态（供审核者选择）：① 保持暂停；② 剥离 `head` 字段只留元数据；③ 恢复完整公开（审核批准后由 Agent 改白名单）。

## 2. r2_04_evidence/theory_locate.json —— 16 条（id 15–30）

性质：R2-04 理论命题页码定位证据。每条含 id / book_id / old_page / topic / **quote（逐字引文）** / verified_pages / verdict。

| id | book_id | topic | quote 字符 | verdict | 分类 |
|---|---|---|---|---|---|
| 15 | wangli_shicilv | 孤平 | 82 | NOT_FOUND（R2-05 已判 RETIRED_MISATTRIBUTED，仅存档） | FACTUAL_METADATA（错误记录本身） |
| 16 | wangli_shicilv | 特拗（特定平仄格式） | 86 | QUOTE_FOUND | SHORT_QUOTATION |
| 17 | wangli_shicilv | 拗救 | **122（最长）** | QUOTE_FOUND | SHORT_QUOTATION |
| 18 | wangli_shicilv | 一三五不论 | 60 | QUOTE_FOUND | SHORT_QUOTATION |
| 19 | wangli_shicilv | 一三五不论（续） | 88 | QUOTE_FOUND | SHORT_QUOTATION |
| 20 | wangli_shicilv | 三平调 | 39 | QUOTE_FOUND | SHORT_QUOTATION |
| 21 | wangli_shicilv | 合掌 | 30 | QUOTE_FOUND | SHORT_QUOTATION |
| 22 | wangli_shicilv | 对仗优劣 | 34 | QUOTE_FOUND | SHORT_QUOTATION |
| 23 | long_yushsheng_cilv | 词韵分类 | 36 | QUOTE_FOUND | SHORT_QUOTATION |
| 24 | long_yushsheng_cilv | 词谱符号 | 51 | QUOTE_FOUND | SHORT_QUOTATION |
| 25 | long_yushsheng_cilv | 与《钦定词谱》分歧 | 20 | QUOTE_FOUND | SHORT_QUOTATION |
| 26 | long_cixue_shijiang | 词的性质 | 90 | QUOTE_FOUND | SHORT_QUOTATION |
| 27 | long_cixue_shijiang | 选调与声情 | 82 | QUOTE_FOUND | SHORT_QUOTATION |
| 28 | long_cixue_shijiang | 韵位与表情 | 76 | QUOTE_FOUND | SHORT_QUOTATION |
| 29 | long_cixue_shijiang | 四声阴阳 | 87 | QUOTE_FOUND | SHORT_QUOTATION |
| 30 | long_cixue_shijiang | 句度与表情 | 28 | QUOTE_FOUND | SHORT_QUOTATION |
| 合计 | 2 位作者 3 本书 | 16 条 | **901 字符** | 15 FOUND + 1 NOT_FOUND | — |

审查结论：**WITHHELD（暂停公开）**。理由：`quote` 是页码核验的证据本体，剥除即失去证据力，公开必要性**中等**；但 16 条引文带页码、带主题、逐条对应原书位置，构成对版权书的"主题式摘录索引"。合计 901 字符、单条 ≤122 字，属短引范围，风险低于 ocr_samples.json。
建议审核者二选一：① 恢复公开（风险可接受，理由：每条引文均为研究评注的必要证据、有明确出处与页码、全部为短引）；② 保持暂停，改存「quote 的 SHA-256 + 页码」使证据可复核而不逐字公开。

## 3. r2_04_evidence/manifest.json —— 保留公开

- 分类：**FACTUAL_METADATA**（单元 ID、印刷/PDF 页码区间、full_chars/evidence_chars 统计、内部文件路径占位符）。
- 引文：0 字符。
- 注意：`file` 字段引用 `chapters/` 路径——该目录已退出公开仓库，路径引用本身无风险（元数据完整性要求保留）。

## 4. r2_04_evidence/README_CHARCOUNT.md —— 保留公开（本轮回填本地）

- 分类：**ORIGINAL_RESEARCH_SUMMARY**（字符统计口径说明 + 公开同步状态声明；明确记录 full/chapters 自 2026-11-20 退出公开）。
- 引文：0 字符。
- 处理：该文件原只存在于公开仓库（R2-15 期间生成未回填）。本轮已从公开 main `37ee224` **逐字节回填**到本地项目（cmp 校验一致），使其成为严格白名单下的正常受管文件。

## 5. r2_05_notes/（10 文件）与 r2_06_notes/（3 文件）—— 保留公开；3 处 REVIEW_REQUIRED 已于第二轮按外部审核裁决处理为 REDACTED_PUBLIC（见 §7）

逐文件审查表（引文跨度为「」『』内文本，脚本统计；跨行长段人工补充）：

| 文件 | 全文字符 | 引文处数 | 引文合计 | 最长跨度 | 内容构成 | 分类 | 决定 |
|---|---:|---:|---:|---:|---|---|---|
| r2_05_notes/A_00_引言.md | 1,014 | 16 | 397 | 84 | 要点归纳 + 2 条短引 + 时代话语标注 + 原创分析 | ORIGINAL_RESEARCH_SUMMARY（含 SHORT_QUOTATION） | 保留公开 |
| r2_05_notes/A_01_第一章.md | 3,137 | 72 | 914 | 57 | 同上；引《康熙字典》歌诀（公有领域） | 同上 | 保留公开 |
| r2_05_notes/A_02_第二章.md | 10,878 | 211 | 3,144 | （正则）82；**人工：孤平段"原文全录"约 280 字** | 平仄谱（公式化符号，非著作权客体）+ 要点归纳 + 原图核验记录 + 原创辨析 | ORIGINAL_RESEARCH_SUMMARY；**孤平全录段 REVIEW_REQUIRED** | 保留公开 + REVIEW_REQUIRED |
| r2_05_notes/A_03_第三章.md | 5,417 | 108 | 1,639 | 79 | 16 词谱示例表（事实数据）+ 归纳 + OCR 缺陷记录 | 同上 | 保留公开 |
| r2_05_notes/A_04_第四章.md | 3,310 | 113 | 1,269 | 61 | 归纳 + 短引 | 同上 | 保留公开 |
| r2_05_notes/A_05_附录一.md | 6,226 | 170 | 1,908 | 72；人工：正格/变格/例外三分原文约 110 字、失对自我更正约 85 字 | 清代诸家原文（公有领域）为主 + 王力正文短引 + 三分表（原创整理） | 同上；**三分段 REVIEW_REQUIRED（轻微）** | 保留公开 + REVIEW_REQUIRED |
| r2_05_notes/A_06_附录二三.md | 3,219 | 48 | 578 | 68 | 韵字表结构、50 词谱清单（事实数据）、编纂说明短引、规则注记摘录 | 同上 | 保留公开 |
| r2_05_notes/B_01_卷上.md | 7,612 | 164 | 2,537 | 109 | 归纳 + A/B 术语对照表（原创分析）+ 短引 | 同上 | 保留公开 |
| r2_05_notes/B_02_卷下.md | 7,084 | 97 | 1,451 | 106 | 44 词谱清单（事实数据）+ 归纳 + 术语定性辨析 | 同上 | 保留公开 |
| r2_05_notes/E_词学十讲状态复核.md | 6,871 | 151 | 2,115 | 98；人工：万树《词律·发凡》原文约 180 字（**清代文献，公有领域**） | 阅读状态复核（原创）+ 龙榆生短引 | 同上 | 保留公开 |
| r2_06_notes/C_诗词格律十讲.md | 11,486 | 99 | 2,195 | 114 | 十二讲结构化笔记（12 固定字段），每讲引文 ≤114 字 | 同上 | 保留公开 |
| r2_06_notes/D_附录与索引.md | 3,137 | 43 | 699 | 81 | 附录归纳 + 索引条目样例（页码列表，事实数据）+ 时代话语标注 | 同上 | 保留公开 |
| r2_06_notes/E_词学十讲十讲复核.md | 3,941 | 62 | 639 | 47 | 阅读状态复核 + 各讲要点 | 同上 | 保留公开 |
| 合计 | 74,044 | 1,354 | 19,485 | — | 古籍（公有领域）与谱表占相当比例；现代版权引文为短引形态 | — | — |

### REVIEW_REQUIRED 明细（3 处，请外部审核裁决）

| 位置 | 内容 | 规模 | 出处 | 我方评估 |
|---|---|---|---|---|
| A_02_第二章.md「（四）孤平的避忌」 | 王力孤平定义段逐字全录（含脚注交代），文末明确标注"原文全录，因上轮此处出过严重错误"——该保留决定有审计动机 | 约 280 字 | wangli_shicilv p44–45（印刷 36–37） | 属"适当引用"边缘但可辩护：占原书约 0.26%，有出处与页码，服务于错误追溯与边界标注；如审核要求更保守，可将该段节录为首尾两句加省略号 |
| A_05_附录一.md「★★ 正格／变格／例外 三分」 | 三分定义原文引用 + 三分表（表为原创整理，引文部分约 110 字） | 约 110 字 | wangli_shicilv 附录一 p153（印145） | 短引，服务方法论建模，建议保留 |
| C_诗词格律十讲.md 第六讲 | 孤平完整版定义引文 | 114 字（正则最长跨度） | 合订本 C p364 | 短引，建议保留 |

### CLOSE_PARAPHRASE 检查

13 个笔记文件的"要点"部分均为对原书的**归纳改写**（非逐句同义替换），且每文件末尾的"待追踪的学术问题""与其他章节关系"为原创分析。未发现成段的 CLOSE_PARAPHRASE。判定依据：要点均带页码锚点、含大量作者自己的判断词（"★ 关键限定""必须并列""不得混引"）与跨章节对照。

### COPYRIGHT_UNCLEAR 记录

- 龙榆生《词学十讲》EPUB 整理本：正文引文按大陆保护期已届满处理，但版本整理者（序、注释）权利不明。本轮公开文件中不含其连续正文，只有短引，按项目规则从严后仍属可保留范围。
- `诗词格律引擎/`（整体白名单树）不在本轮审查范围（R2-16B 指定范围为 4 个目标）；其内容为引擎代码、测试集与报告，无版权书正文（引擎冻结期间未变）。

## 6. 审查总决定（待外部审核确认）

| 文件 | 决定 | 生效方式 |
|---|---|---|
| ocr_samples.json | 暂停公开（WITHHELD） | **已生效**：2026-11-21 真实同步后远端当前树计数 0（提交 eba6774 删除）；原件保留本地 |
| theory_locate.json | 暂停公开（WITHHELD） | **已生效**：同上 |
| manifest.json / README_CHARCOUNT.md | 保留公开 | 白名单显式收录，远端在位 |
| r2_05_notes/（10 文件） | 保留公开；2 处 REVIEW_REQUIRED → 已改写 | 白名单收录；导出时改写生效（REDACTED_PUBLIC），逐字原文仅存本地 |
| r2_06_notes/（3 文件） | 保留公开；1 处 REVIEW_REQUIRED → 已改写（含第五讲一并为 2 条规则） | 同上 |

> 状态更新（第二轮收尾）：上述决定已于 2026-11-21 经用户批准的真实同步落地，远端 main 当前为 `26bf0f763153418b59f9b81688f9229b803924ff`；全新克隆路径级验证见 `LOGS/verify_final_greps.log`。第一轮"未执行真实同步、仍存在于公开仓库"的说明已被本状态取代。

## 7. 第二轮收尾更新（2026-11-21，审核裁决后执行结果）

### 7.1 REVIEW_REQUIRED → REDACTED_PUBLIC（4 条改写规则，public_redactions.json）

| 规则 ID | 位置（更正后） | 原文规模 | 处理 | 原件状态 |
|---|---|---|---|---|
| A02-GUPING-VERBATIM | A_02_第二章.md「（四）孤平的避忌」 | 约 280 字（原文全录段） | 公开版改为要点转述 + 页码（wangli_shicilv PDF p44–45／印36–37） | 本地原件未动 |
| A05-SANGE-VERBATIM | A_05_附录一.md「★★ 正格／变格／例外 三分」 | 约 110 字 | 公开版改为要点转述（三分表为笔记原创整理，保留） | 本地原件未动 |
| C-SHIDUI-VERBATIM | **C_诗词格律十讲.md 第五讲（七言律诗）**——更正：第一轮误标"第六讲"，114 字最长跨度经复核实际位于此（失粘/失对表述） | 114 字 | 公开版改为要点转述 + 页码（合订本 C 印刷 360–361／PDF 368–369） | 本地原件未动 |
| C-GUPING-VERBATIM | C_诗词格律十讲.md 第六讲（孤平完整版定义，嵌套引文约 90 字，第一轮被正则切碎漏计） | 约 90 字 | 公开版改为要点转述 + 页码（印刷 364／PDF 372） | 本地原件未动 |

改写机制：唯一锚点定位（8 锚点验证唯一）、只作用于导出副本、锚点失效 exit 7。真实文件模拟 4/4 PASS（LOGS/redaction_dryrun.log）；真实推送中 3 个文件 treatment=REDACTED_PUBLIC；远端抽查 `A_02_第二章.md` 含改写标记、不含逐字孤平原文。

### 7.2 两份原始 JSON：WITHHELD 已远端生效，公开版在位

| 项 | ocr_samples.json | theory_locate.json |
|---|---|---|
| 原件（本地，未删未改） | SHA-256 `9b8f11cd…`（14,580B） | `4ba74f22…`（6,001B） |
| 远端当前树 | **不存在（计数 0）** | **不存在（计数 0）** |
| 公开版本 | `ocr_samples_public.json`（发布 blob 6,488B，SHA-256 `41ea6237…`；仅页码/字符统计/质量标记，无 head） | `theory_locate_public.json`（发布 blob 3,941B，SHA-256 `f15cddf4…`；quote→quote_sha256） |
| 公开版自检 | 无 head 字段（断言通过） | 16 条 quote_sha256 与本地原件引文重算全部一致（True） |

### 7.3 远端生效状态

- 生效提交：`eba67745d998b3bfd6d559124ca89a1fe58437b8`（删除 3 路径 + 新增公开版与治理文件），当前 main `26bf0f763153418b59f9b81688f9229b803924ff`。
- 路径级验证：全新克隆 `verify-final` 逐项 grep（LOGS/verify_final_greps.log）——三删除路径 0 命中、4 新公开文件在位、全历史 full/chapters 0 命中。
- 如实记录：两份原件与 ocr_vision 在**可达历史**中仍各有 1 个对象（公开至 eba6774）；历史重写与否属审核者决策，本轮未动历史。
