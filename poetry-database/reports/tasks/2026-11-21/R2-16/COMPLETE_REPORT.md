# COMPLETE_REPORT —— R2-16 PUBLICATION BOUNDARY & SOURCE-LINEAGE CLOSEOUT（16A 收尾核查 + 16B + 16C + 16D）

> 本轮按外部审核 2026-11-21 指令执行「R2-16B+C：PUBLIC CONTENT REVIEW & STRICT EXPORT ALLOWLIST」，
> 并补做 R2-16A 的两项收尾核查（PR/Fork、postBuffer 遗留）。
> 按任务基线：**未做 force push、未修改任何远端历史、未执行真实同步推送**。
> 报告路径：`poetry-database/reports/tasks/2026-11-21/R2-16/`（以下简称 `<R16>`）。

---

## 1 任务基本信息

| 项 | 值 |
|---|---|
| 任务编号 | R2-16（16A 收尾核查 ＋ 16B ＋ 16C ＋ 16D；16D/16E/16F/16G 未授权，未开工） |
| 日期 | 2026-11-21 |
| 本地项目 | `D:\Codex\Poetry-Generation-Skill`（**旧 clone**，HEAD `73e7a110600d`，origin 指向 GitHub；本轮对该仓库零 git 写操作，仅新增/修改工作文件，未提交未推送） |
| 干净工作副本 | `D:\ZCode\zcode\r2_16_workspace\clean-main`（本轮新克隆，HEAD `37ee224d5a09` ＝ 远端 main） |
| 远端 main | `37ee224d5a09f9e73bf9b785db986bc94e76bf6a`（执行前后未变，`ls-remote` 复核） |
| 沙盒 | `D:\ZCode\zcode\r2_16_workspace\synctest\`（origin.git bare + 合成项目 + 独立断言脚本） |
| 任务目标 | ① R2-16A 收尾：PR/Fork 与缓存限制核查、postBuffer 修正项；② 16B：逐条审查 4 组公开材料；③ 16C：重构 github_sync.py 严格白名单导出；④ 16D：七项测试；⑤ 交付本报告后停止 |

## 2 执行前状态

- R2-16A 历史清理已完成并经审核通过（远端 main `5fac693…` → `37ee224…`，公开历史 full/chapters 0 命中）。
- 已知风险（审核指出）：GitHub 隐藏 PR 引用与缓存未核查；两份公开摘录（ocr_samples.json、theory_locate.json）未审查；同步脚本依赖旧 Manifest 删除文件。
- 本轮新发现（勘察阶段）：
  1. **本地项目是旧 clone**：其 git 历史含 34 个 full/chapters 旧对象（与清理前一致），HEAD `73e7a11` 落后远端 5 个提交。任何从该项目根直接 push 的操作都会重新引入旧历史。
  2. **同步脚本使用 SSH 地址**，而本机 SSH 无密钥（`Permission denied (publickey)`）——脚本在本机 clone/push 阶段必然失败；`gh` CLI 已登录 iop666（HTTPS 协议）。
  3. **公开仓库的 `LICENSE`（MIT）不在旧白名单内**，靠旧删除逻辑的漏洞侥幸存活；严格清空设计下若不处理会被误删。
  4. **`raw/r2_04_evidence/README_CHARCOUNT.md` 只有公开仓库有、本地没有**（R2-15 期间生成未回填），严格白名单下它将从公开仓库消失。
  5. 旧白名单把 `raw/r2_04_evidence` **整目录**收编——若本地 full/、chapters/ 原件仍在（确实在），旧脚本下轮同步会把它们**重新推上 GitHub**。这是本轮重构要堵的最大漏洞。

## 3 本次实际工作

### 3.1 A 组：R2-16A 收尾核查

| 检查 | 命令 | 结果 |
|---|---|---|
| PR 引用 | `gh pr list --repo iop666/Poetry-Generation-Skill --state all --limit 100 --json number,state,title,headRefName,baseRefName` | **`[]`（0 条 PR，含关闭状态）** |
| Fork | `gh api repos/iop666/Poetry-Generation-Skill/forks --paginate` | **`[]`（0 个 Fork）** |
| postBuffer 修正项 | `git config --global/--system --show-origin --get-all http.postBuffer` | **全局与系统均无设置**；500MB 只存在于一次性清理副本 `rewrite.git` 的仓库级配置中（当日已顺手清除）。该副本属于受控本地目录、不再用于推送 |
| 备份隔离 | — | `backup.git`（含旧 OCR 的完整备份）保留在 `D:\GitBackups\Poetry-Generation-Skill-history-cleanup-20261121\`，未同步、未分享、未上传；本报告与日志不含任何旧 OCR 内容 |

缓存与旧提交可访问性限制的记录见第 8 章第 4 条。

### 3.2 B 组：逐条审查（详见 `<R16>/SOURCE_AUDIT.md`）

- 通读 13 个笔记文件 + 2 份 JSON + manifest.json + README_CHARCOUNT.md（共 15 文件）。
- 脚本统计引文规模：两份 JSON 公开文本 = **2,654 + 901 字符**（与审核者口径完全一致）；13 个笔记「」『』引文合计 19,485 字符（含公有领域古籍引文；正则低估跨行嵌套段，长段已人工标注）。
- 关键法律事实：王力（1900–1996）作品保护期至 **2046 年底**；龙榆生（1902–1966）作品大陆保护期已于 2016 年底届满（版本整理者权利不明，仍按项目铁律从严处理）。
- 决定：`ocr_samples.json`、`theory_locate.json` → **暂停公开（WITHHELD）**；13 个笔记 + 2 个元数据文件 → **保留公开**，其中 3 处逐字段落标 `REVIEW_REQUIRED`（A_02 孤平段约 280 字、A_05 三分段约 110 字、C 第六讲 114 字）。

### 3.3 C 组：github_sync.py 严格白名单 v2 重构

核心设计（v1 → v2 的实质变化）：

| 机制 | v1（R2-15 版） | v2（本轮） |
|---|---|---|
| 导出起点 | 复用上次克隆，依赖旧 Manifest 删除不再白名单的文件 | **每轮清空导出树（除保护名单 README.md/LICENSE）再复制白名单**；完全不读旧 Manifest |
| r2_04_evidence | 整目录收编（会把本地 full/chapters 原件重新推上 GitHub！） | 逐文件白名单（manifest.json、README_CHARCOUNT.md）；**HARD_EXCLUDE 命中 full/chapters/books/database/normalized 等即整次同步中止（exit 4）** |
| 暂停公开 | 无此概念 | **WITHHELD 清单**：ocr_samples.json、theory_locate.json 保留本地、绝不导出，恢复须审核批准 |
| 生成后校验 | 无 | `verify_export()` 推送前门禁：仓库文件 ↔ Manifest 双向对应、SHA-256 按脱敏后文件复算、硬排除命中必须为 0，失败 exit 6 不提交不推送 |
| 远端地址 | SSH（本机不可用） | HTTPS 默认（gh 凭据），`GITHUB_SYNC_REPO_URL` 可覆盖 |
| 暂存目录 | 固定 | `GITHUB_SYNC_STAGING` 可覆盖（测试用） |
| 换行一致性 | 受本机 autocrlf 影响，Manifest 哈希可能与仓库 blob 不符 | 克隆固定 `core.autocrlf=false`（测试中发现的缺陷，见第 7/8 章） |
| 推送 | `git push origin main` | 不变（普通推送，无 force） |

辅助工作：① 从公开 main `37ee224` **逐字节回填** README_CHARCOUNT.md 到本地（cmp 校验一致）；② LICENSE 加入保护名单；③ 生成文件（.gitignore/UPLOAD_MANIFEST.csv/UPLOAD_REPORT.md/GITHUB_SYNC.md/REPORTS_INDEX.md）纳入校验白名单口径。

## 4 数据成果

| 项 | 数量 | 说明 |
|---|---|---|
| 新增数据 | 0 条 | 未进入任何语料/数据库建设 |
| 修改数据 | 0 条 | 生产 SQLite 数据库未触碰 |
| 删除数据 | 0 条 | 本地原始研究材料零删除（full/、chapters/、两份 JSON 原件均在） |
| 审查文件 | 15 个（48 条逐字片段逐条过目） | 32 条 OCR 页首片段 + 16 条理论引文 + 13 个笔记文件 |
| 暂停公开 | 2 个文件（3,555 字符逐字文本） | 待审核批准后通过一次真实同步在远端生效 |
| 新增文件 | 5（本报告四件套 + LOGS 归档 9 件）+ 1 回填 | 见第 5 章 |

## 5 文件变更

| 变更 | 路径 | SHA-256 / 说明 |
|---|---|---|
| 修改 | `poetry-database/tools/github_sync.py`（591 行，对 v1 diff 412 行） | `0ed57d46dce863a37040ac179fc33cf50bad8ae973539774942779973f27c967` |
| 回填 | `poetry-database/raw/r2_04_evidence/README_CHARCOUNT.md`（1,372 字节，来源公开 main 37ee224，逐字节一致） | `ddb4637928f0d2a078afc223687fb85dd628084eca69c15b7dbd5bff54d0f967` |
| 新增 | `<R16>/COMPLETE_REPORT.md`（本文件） | 写入后计算，见 FILE_MANIFEST.md |
| 新增 | `<R16>/SOURCE_AUDIT.md` | `41c58fc69e4f3d094193220aa7dcebd2ff0180291249f33350d618fbf4a7fcd2` |
| 新增 | `<R16>/R2-16C_TEST_RESULTS.md`（第一轮名 TEST_RESULTS.md，第二轮按审核要求更名以免与数据库任务 R2-16D 混淆） | `65bbc3e865b36924e5b70da21abd71f807e5d13744f71265e0aa9f6b4609b88f`（更名前内容） |
| 新增 | `<R16>/FILE_MANIFEST.md` | 自身不列哈希（自引用问题），其余文件哈希见其中 |
| 新增 | `<R16>/LOGS/`（9 件：Run A/A2/B/C/C2/D、T1–T9 两轮、引文统计） | 含**保留的失败日志** verify_t1_t9.log（首轮 3 FAIL） |
| 工作区（非项目） | `D:\ZCode\zcode\r2_16_workspace\`：clean-main 克隆、synctest 沙盒、verify_tests.py、quote_stats.py、`backup/github_sync_v1_r2-15.py.bak`（v1 脚本备份，保留于项目外） | — |

未变更的关键文件：`raw/r2_04_evidence/ocr_samples.json`（`9b8f11cd…`）、`theory_locate.json`（`4ba74f22…`）——**本地原件未删未改**，仅退出公开白名单。

## 6 技术实现

- 实现位置：`poetry-database/tools/github_sync.py` 单文件；函数级边界：`collect()`（白名单收集 + 硬排除中止 + 软排除记录）→ `ensure_clone()`（fetch/reset + HEAD==origin/main 断言 + autocrlf 固定）→ `wipe_stale()`（清空导出树 + 空目录级联）→ 复制/脱敏（`sanitize_copy`，文本统一 LF）→ `sensitive_scan()`（路径/手机号/凭据硬门禁，继承 v1）→ `verify_export()`（四重校验）→ commit/push。
- 数据结构：`WITHHELD[(path, reason)]`、`HARD_EXCLUDE_PARTS/SUFFIX`、`SOFT_EXCLUDE_*`、`PROTECTED={"README.md","LICENSE"}`、`GENERATED={5 个工具生成文件}`。
- 实现边界：`诗词格律引擎`、`docs`、`reports` 等八棵树沿用项目既有公开范围（本轮未重审其内容，见第 12 章第 5 条）；硬排除对 INCLUDE_TREES 内合法出现的 .db/.pdf 也会中止（fail-safe 方向，需人工处置）。
- 兼容性影响：下一次真实同步将在远端删除 ocr_samples.json、theory_locate.json（白名单外），其余公开内容与现状一致（README_CHARCOUNT.md 经回填保持）。

## 7 实际验证

七项要求测试 **7 PASS / 0 FAIL / 0 BLOCKED / 0 NOT RUN**，附加 4 PASS，命令与真实输出见 `<R16>/R2-16C_TEST_RESULTS.md` 与 `<R16>/LOGS/`。要点：

1. 沙盒完整同步：VERIFY PASS（树 15 = Manifest 8 + 保护 2 + 生成 5）→ PUSH OK（Run A2）。
2. 硬排除中止：白名单树内出现 poison.pdf → exit 4，origin/main 不变（Run B）。
3. 旧 Manifest 已删文件：正确删除、无崩溃（T4）。
4. SHA-256：8 行逐一按 origin blob 复算一致；脱敏生效且 Manifest 按**脱敏后**文件计算（T6）。
5. 本地零误删：6 个毒饵原件全部健在（T7）。
6. 首轮 3 项 FAIL 已全部修复并复测通过（autocrlf 缺陷 1 项真实、2 项断言脚本自身），失败日志保留。
7. 真实项目最终版 `--dry-run` exit 0：826 个白名单候选、~48.6 MB，两份 JSON 正确列入暂停公开。

UNKNOWN 数量：0（本轮所有检查均有确定性输出）。

## 8 问题记录

**已修复**
1. 旧白名单整目录收编 r2_04_evidence → 若运行旧脚本会把本地 full/chapters 原件重新发布到 GitHub（比历史泄漏更直接的再泄漏通道）。v2 已堵死并加硬排除中止。
2. LICENSE 不在任何保护/白名单内 → 严格化后会被误删。已入保护名单。
3. `core.autocrlf` 导致 Manifest 哈希与仓库 blob 不一致 → 克隆内固定 autocrlf=false。
4. README_CHARCOUNT.md 无本地源 → 已逐字节回填。
5. 脚本 SSH 地址在本机不可用 → HTTPS + gh 凭据（可环境变量覆盖）。
6. HTTP 408 归因修正（采纳审核意见）：调大 postBuffer 后推送成功是事实，但"chunked 传输导致 408"未经证实，git 官方文档亦不支持将该参数作为普遍解法；全局/系统配置核查确认无遗留，一次性副本中的设置已清除。

**新发现 / 尚未解决**
7. **两份 JSON 目前仍在 GitHub 公开**：暂停公开决定要等审核批准后的下一次真实同步才在远端生效。在此之前公开风险维持现状。
8. **A_02 孤平段约 280 字逐字全录**等 3 处 REVIEW_REQUIRED 待裁决（我方评估为可辩护的适当引用，详见 SOURCE_AUDIT §5）。
9. **GitHub 缓存与旧提交可访问性无法本地程序化验证**：PR=0、Fork=0 只覆盖可见引用；cached commit view、`refs/pull/*` 内部引用、搜索引擎缓存不在本机核查能力内。现代著作全文（非凭据）也未必适用 GitHub 敏感数据清理流程——如需彻底清除应通过 GitHub Support 或版权渠道评估，本轮仅如实记录该限制。
10. 13 个笔记的引文统计为正则口径（跨行嵌套被低估，长段已人工补注）；"现代版权引文合计"无逐字符精确值。
11. 真实 GitHub 远端的端到端推送未验证（本轮禁止推送）；沙盒与真实远端在网络与凭据上存在差异。

**风险与影响**：当前最大的残余风险是第 7 条（两份 JSON 仍公开）与第 9 条（缓存不可验证）；二者都只能通过"批准后的真实同步 + 平台侧措施"关闭。

## 9 上轮审核意见处理

| 审核要求 | 处理 | 状态 |
|---|---|---|
| A1 检查所有 PR | `gh pr list --state all` → 0 条 | ✅ 完成 |
| A2 检查 Fork | `gh api …/forks --paginate` → 0 个 | ✅ 完成 |
| A3 记录缓存与旧提交可访问性检查限制 | 第 8 章第 9 条如实记录 | ✅ 完成 |
| A4 旧备份只留本地受控目录 | backup.git 未动、未外传；rewrite.git 的 postBuffer 残留已清 | ✅ 完成 |
| postBuffer 技术归因修正 | 全局/系统核查（无遗留）；报告归因改为"调大后成功是事实，确切原因未证实" | ✅ 采纳并执行 |
| B 逐条审查 4 组材料 | 15 文件全文通读 + 脚本统计 + 48 条片段逐条分类（SOURCE_AUDIT） | ✅ 完成（裁决待审核） |
| 不得仅凭文件名判断可公开 | 每文件记录内容构成、引文规模、公开必要性 | ✅ 执行 |
| 不得自动删除本地原始材料 | 本地零删除，两份 JSON 原件 SHA 未变 | ✅ 执行 |
| 无法判断标 REVIEW_REQUIRED | 3 处标注 | ✅ 执行 |
| C 严格白名单重构（空导出目录方案优先） | v2：清空导出树 + 显式白名单 + 硬排除 + 生成后校验；完全不依赖旧 Manifest | ✅ 完成 |
| ocr_samples/theory_locate 待批准再定 | WITHHELD 机制 + 本轮不推送 | ✅ 执行 |
| D 七项测试逐项记录 | 7 PASS + 附加 4 PASS，全部有日志 | ✅ 完成 |
| E 交付 R2-16 报告并停止；不 force push；不改旧历史 | 本报告；远端 main 全程未变（`37ee224…`） | ✅ 完成 |

## 10 项目整体进度

| 子项 | 状态 |
|---|---|
| R2-16A Git 历史清理 | **完成**（前轮已过审；本轮补 PR/Fork/postBuffer 收尾，PASS） |
| R2-16B 现代书籍摘录与阅读笔记审查 | **执行完毕，待外部裁决**（3 处 REVIEW_REQUIRED + 两 JSON 恢复与否） |
| R2-16C 严格公开同步白名单 | **执行完毕，待外部确认**（代码 + 测试就绪；未推送） |
| R2-16D 2,304 条来源差额 | 未授权，未开工 |
| R2-16E 作者字段语义修正 | 未授权，未开工 |
| R2-16F 元曲修复候选抽查 | 未授权，未开工 |
| R2-16G 文档与 Manifest 统一 | 未授权，未开工 |
| 技术债 | 本地项目根仍为旧 clone（只读使用，未 push）；Phase 3–7 仍冻结 |

## 11 下一步建议（只建议，不执行）

1. **裁决点一**：ocr_samples.json / theory_locate.json 三选一（保持暂停｜剥离 head 后公开｜恢复公开）。批准后由 Agent 修改 WITHHELD/白名单并执行一次真实同步（预计远端净变更：删 2 文件 + 新增 R2-16 报告目录）。
2. **裁决点二**：3 处 REVIEW_REQUIRED 段落（A_02 约 280 字孤平全录段为最大项）保留或节略。
3. 裁决后执行真实同步前，建议先在沙盒以真实项目白名单复跑一次（本轮沙盒为合成项目，真实 826 文件集合未端到端推送过）。
4. 同步生效后，将 R2-16B/C 结论回写 `GITHUB_SYNC.md`/`UPLOAD_REPORT.md` 的公开边界说明（16G 的一部分）。
5. 之后再按审核排期进入 16D（2,304 条来源差额）。

## 12 自我审计（尚不能证明正确的事项）

1. **"公开风险已解决"不能宣布**：两份 JSON 在远端仍公开（本轮未推送）；缓存/PR 内部引用不可本地验证；13 个笔记保留公开的决定是我方评估，未经外部确认。
2. **引文统计不精确**：正则口径低估跨行嵌套引文；"现代版权引文合计"只有区间估计（约 1.1–1.3 万字符，其中相当比例为公有领域古籍与谱式符号）。
3. **13 个笔记文件本身未经独立复核**：审查者为执行 Agent 本体，"要点归纳不含 CLOSE_PARAPHRASE 成段"的判断未经第二双眼睛。
4. **INCLUDE_TREES 八棵树未在本轮重审**（docs/诗词格律引擎/reports/catalog/research/audit/sources）：本轮审查范围仅限任务指定的 4 组材料；这八棵树按既有公开范围沿用，其内部是否含未登记风险未知。
5. **硬排除清单是枚举式的**：`/books/`、`/database/` 等模式按当前目录结构设计，未来新增目录若命名不同（如 `corpus_v2/`）不会被拦截；白名单整体收编（INCLUDE_TREES）仍是泄漏面。
6. **沙盒与生产差异**：真实 826 文件、~48.6 MB 白名单只跑过 dry-run；真实推送涉及 gh 凭据刷新、大包上传（上轮 408 教训）等未验证因素。
7. **`verify_export` 的"生成文件"集合是脚本自身声明的**：若未来有人往 GENERATED 之外新增生成文件，需要同步维护清单，否则校验失败（fail-safe 方向，但增加维护成本）。

## 13 最终结论

- **SELF_STATUS：PASS（本轮授权范围内）**——16A 收尾核查完成；16B 逐条审查完成（决定待裁决）；16C 重构完成并通过全部测试；16D 七项测试 7 PASS；未 force push、未改历史、未删除本地材料、未触碰生产数据库、未进入 Phase 3–7。
- **远端 main 执行前后均为 `37ee224d5a09f9e73bf9b785db986bc94e76bf6a`**（本轮零远端写操作）。
- 需要外部审核的事项：① 两份 JSON 的恢复/剥离/维持决定；② 3 处 REVIEW_REQUIRED 段落裁决；③ 是否批准执行真实同步（以使暂停公开在远端生效）；④ 缓存清除是否需要走 GitHub Support/版权渠道。
- 按任务要求，本轮到此**停止**，等待独立审核。

---

# 14 第二轮执行记录（2026-11-21，外部审核裁决后的 R2-16C 收尾）

> 审核裁决（2026-11-21）：R2-16A PASS；R2-16B PARTIAL（两 JSON 维持 WITHHELD，三处 REVIEW_REQUIRED 按审核口径改写）；R2-16C PARTIAL（真实推送未执行）。
> 角色边界确立：本 Agent 只负责 GitHub 公开仓库、文件同步与文档级审查；R2-16D/E/F（数据库来源差额、作者归属、元曲数据）**不属于本 Agent**，TEST_RESULTS.md 已按要求更名为 R2-16C_TEST_RESULTS.md。
> 第二轮未执行真实推送；远端 main 全程仍为 `37ee224d5a09f9e73bf9b785db986bc94e76bf6a`。

## 14.1 审核七项要求的落实

| # | 要求 | 落实 |
|---|---|---|
| 1 | 八棵目录树完整文件级审计 | `PUBLIC_TREES_AUDIT.md`：818 文件全量枚举 + 全量风险扫描（LOGS/tree_risk_scan.log：零手机号/零凭据/零解码失败/二进制仅 ocr_vision）+ 高风险区精读（格律规则/诗话摘录/作品库/书目/数据 JSONL 抽样） |
| 2 | 逐文件白名单取代整树包含 | `poetry-database/tools/public_files.txt` 登记 842 文件；`INCLUDE_TREES` 机制废除；每次运行输出"默认拒绝审计" |
| 3 | 新增文件默认不公开 | v3 默认拒绝未登记文件；沙盒 T10 验证（unregistered_draft.md 未导出） |
| 4 | 每次同步生成最终公开目录与 Manifest 差异报告 | 新增 `SYNC_DIFF.md` 生成（沙盒 T12 验证：A/M/D 条目+numstat+合计）；Manifest↔磁盘双向对应由 verify_export 强制 |
| 5 | 两份 JSON 的 WITHHELD 公开版 | `make_public_evidence.py` 生成 `ocr_samples_public.json`（去 head，6,488 字节）与 `theory_locate_public.json`（quote→SHA-256，3,941 字节），自检断言无泄漏；原件维持本地 |
| 6 | 三处 REVIEW_REQUIRED 处理 | `public_redactions.json` 4 条规则（见 14.3），导出时改写为原创摘要+页码，本地原件不动 |
| 7 | 从 37ee224 干净克隆迁移变更 | 已迁移至 `D:\ZCode\zcode\r2_16_workspace\clean-main`（详见 14.4）；真实 dry-run 在干净克隆内执行 |

## 14.2 文件级审计的重要发现

1. **`tools/ocr_vision` 是 macOS Mach-O 二进制**（Swift 编译的 OCR 客户端）——当前已在公开仓库中。二进制可能内嵌端点/密钥字符串且内容不可审计，已从白名单排除；批准后的同步将从远端删除。其源码 `ocr_vision.swift` 已扫描（53 行，无 token/密钥/硬编码端点），保留公开。
2. **三个文件"本地旧克隆 ≠ 公开 main"，且公开版更新**：`AGENTS.md`（公开 184 行含 R2-15 时代边界条款；本地 170 行为 R2-07 时代快照）、`r2_14_tests.py`/`tests_r2_14.csv`（公开版为带数据库 SHA-256 基线的真实实现；本地版 T75 为 `True` 占位的退化稿）。**迁移策略：三者以公开版为准，不用本地覆盖**——逐文件白名单+哈希比对避免了一次对公开内容的回退。请项目所有者知悉：`D:\Codex` 本地目录的这三个文件已落后于公开版，未来应从干净克隆回补。
3. 风险扫描 3 处路径命中与 2 处邮箱命中全部核实为良性（测试报告自身引用测试字符串、github_sync.py 脱敏正则字面量、`researcher@example.org` UA 占位符）。

## 14.3 REVIEW_REQUIRED 改写（一处更正）

- A_02 孤平段（约 280 字）→ 公开版改为要点转述+页码（wangli_shicilv p44–45／印36–37）。
- A_05 三分句（约 110 字）→ 公开版改为要点转述（三分表本身为笔记原创整理，保留）。
- C 文件长引文 → **更正**：第一轮报告把 114 字最长跨度标为"第六讲"，复核确认实际位于**第五讲**（失对表述）；第六讲孤平定义为嵌套引文（约 90 字）被正则切碎导致误判。按裁决本意，两处均做公开版改写。此更正已同步写入 SOURCE_AUDIT 口径说明。
- 机制：规则以唯一锚点定位（8 个锚点已验证唯一命中），只作用于导出副本；锚点失效时同步以 exit 7 中止，防止静默漂移。沙盒 T11 验证：公开版无逐字原文、含改写标记与页码、本地原件逐字保留、treatment=REDACTED_PUBLIC。

## 14.4 迁移与干净克隆工作流

1. 干净克隆 `clean-main`（HEAD 37ee224）已设 `core.autocrlf=false` 并强制重检出（消除 CRLF 抖动）。
2. 迁移内容：github_sync.py（v3）、public_files.txt、public_redactions.json、make_public_evidence.py、两个 *_public.json、README_CHARCOUNT.md（LF 一致）。
3. 哈希比对 842 个白名单文件：4 个差异（3 个按公开版为准 + 1 个换行噪音），12 个待新增（R2-16 报告目录）。
4. **老项目目录 `D:\Codex\Poetry-Generation-Skill` 自本轮起不再作为同步源**；其唯一遗留价值是本地原始研究材料（full/chapters/两份 JSON 原件），这些文件按约束保留原地。

## 14.5 第二轮测试（沙盒重跑 + 新增）

| 测试 | 结果 |
|---|---|
| T1 白名单导出（含治理文件） | PASS |
| T2 full/chapters 不导出 | PASS |
| T3 非白名单零残留 | PASS |
| T4 旧 Manifest 已删文件处理 | PASS |
| T5 Manifest↔磁盘双向对应（树 19 = Manifest 11 + 保护 2 + 生成 6） | PASS |
| T6 SHA-256 按最终公开文件复算 + 脱敏生效 | PASS |
| T7 本地毒饵零误删 | PASS |
| T8 README/LICENSE 保护 | PASS |
| T9 普通 fast-forward 推送 | PASS |
| **T10 默认拒绝未登记文件** | PASS |
| **T11 导出时改写生效（公开版无逐字原文/本地原件不动/REDACTED_PUBLIC）** | PASS |
| **T12 SYNC_DIFF.md 差异报告正确** | PASS |
| **T13 白名单文件本身公开可审计** | PASS |
| Run B 白名单混入硬排除路径 → exit 4，origin 不变 | PASS |
| Run C 干净 dry-run → exit 0，不建暂存 | PASS |
| Run D 白名单混入暂停公开文件 → exit 4（守卫生效） | PASS |

全部日志：LOGS/（run_a3_v3_sync、verify_t1_t13_v3、run_b_v3_hard_abort、run_c_v3_dryrun、run_d_v3_withheld_guard、tree_risk_scan 等）。

## 14.6 待批准的变更集（批准后执行普通 fast-forward 同步才会落到远端）

预计远端变更（最终以推送时生成的 SYNC_DIFF.md 为准）：
- **新增**：R2-16 报告目录（COMPLETE_REPORT、SOURCE_AUDIT、R2-16C_TEST_RESULTS、PUBLIC_TREES_AUDIT、FINAL_CHANGE_REPORT、FILE_MANIFEST、LOGS）、ocr_samples_public.json、theory_locate_public.json、public_files.txt、public_redactions.json、make_public_evidence.py。
- **修改**：github_sync.py（v1→v3）。
- **删除**：raw/r2_04_evidence/ocr_samples.json、theory_locate.json（维持 WITHHELD 裁决）、tools/ocr_vision（二进制，审计排除）。
- 其余 886 白名单文件内容与公开现状一致（含 R2-15 交付件等 36 个公开文件回填登记，见 PUBLIC_TREES_AUDIT §6；除上述外零内容变更）。

## 14.7 第二轮自我审计补充

1. 八棵树审计对 554 个 reports 文件与 186 个 .py 按"项目自产文档/工程代码"整类登记，仅大文件与异常扩展名逐个核查——未逐文件通读正文（方法与局限已在 PUBLIC_TREES_AUDIT §5 声明）。
2. `SYNC_DIFF.md` 在沙盒验证过，但真实 842 文件集的 SYNC_DIFF 要等真实同步才生成。
3. 干净克隆工作流的提交身份、gh 凭据刷新、大包上传等真实远端因素未验证（本轮禁止推送）。
4. public_files.txt 为机械生成（树枚举+显式登记），生成脚本是内联 bash 而非登记的工具文件——未来轮次建议固化为 make_public_files.py 并登记。
5. 本轮发现本地三个文件落后于公开版，只做了"以公开版为准"的迁移决策，未回写本地旧项目目录（避免在旧 clone 制造新的未同步状态）。

## 14.8 第二轮结论

- **SELF_STATUS：PASS（授权范围内）**——审核七项要求全部落实；沙盒 13 项断言 + 3 个中止场景全 PASS；远端零写操作。
  > **状态更新**：本节的"待批准"状态已被 §15（推送执行）与 §16（推送后收尾）取代；远端 main 已推进至 `26bf0f7…`。
- 待审核批准事项：① 批准后执行一次普通 fast-forward 同步（变更集见 14.6）；② 确认 AGENTS.md/r2_14 两文件"以公开版为准"的处理；③ 确认 local 旧项目目录的退役安排。

---

# 15 推送执行记录（2026-11-21，用户批准后）

- 执行方式：在干净克隆 `clean-main`（@ `37ee224`）运行 `python poetry-database/tools/github_sync.py`，普通 fast-forward 推送。
- **新远端 main：`eba67745d998b3bfd6d559124ca89a1fe58437b8`**（提交信息 `Sync project reports and tools 2026-11-21`，父提交 `37ee224`，单提交推进，无 force）。
- 导出 887 文件（51,543,685 字节）；清空导出树删除残留 869；改写生效 3 文件（A_02/A_05/C → REDACTED_PUBLIC）；敏感扫描仅 `researcher@example.org` 占位符；VERIFY PASS（895 = 887 + 2 保护 + 6 生成）；SYNC_DIFF 新增 27 / 修改 9 / 删除 4；PUSH OK（exit 0）。
- 推送后独立核验（`gh api git/trees`）：
  - 删除路径计数 = 0：`raw/r2_04_evidence/ocr_samples.json`、`theory_locate.json`、`tools/ocr_vision`；
  - 新文件远端存在 = 1：public_files.txt、public_redactions.json、make_public_evidence.py、两份 *_public.json；
  - 改写后的公开笔记（A_02 等）已入远端。
- 本机路径形态的暂存位置信息不出现在公开内容（导出时脱敏）。
- 本节为执行后补记；第二次小同步（本节与执行日志入仓）为远端第二提交。


---

# 16 推送后收尾（R2-16C-POST-PUSH-CLOSEOUT，2026-11-21，依据第二轮独立审核意见）

## 16.1 全新克隆路径级验证（审核指定动作，LOGS/verify_final_greps.log）

- `git clone` 全新克隆 verify-final：HEAD = `26bf0f763153418b59f9b81688f9229b803924ff`；HEAD 树 897 blob。
- 三删除路径（ocr_samples.json / theory_locate.json / tools/ocr_vision）grep → **无输出（均不存在）**。
- 四新公开文件（两个 *_public.json、public_files.txt、public_redactions.json）grep → **全部存在**。
- 全部可达历史 full/chapters → **0 命中**。
- 如实记录：两份 WITHHELD 原件与 ocr_vision 在可达历史中仍各有 1 个对象（公开至 eba6774、于该提交删除）；是否重写历史属审核者决策，本轮未动历史。

## 16.2 审核指出问题的核实与处置

| 审核指出项 | 远端 26bf0f7 实测 | 处置 |
|---|---|---|
| COMPLETE_REPORT 结束在 §14.8、声明远端零写操作 | **实测已含 §15**（审核者核对的是推送 #1/eba6774 版本）；但 §14.8 等历史小节的"待批准"表述仍在 | 保留历史原文，加状态更新注记；新增本节 §16 |
| FINAL_CHANGE_REPORT 仅 §1–4、写明未推送 | **实测已含 §5**（同上） | 增加头部状态注记与 §6 推送后路径级验证 |
| R2-16C_TEST_RESULTS 仍是 v2 七项旧版 | **属实**（更名未重写） | 已完整重写：T1–T13 + 3 中止场景 + 两次真实推送 + 全新克隆验证 |
| SOURCE_AUDIT 仍是第一轮状态、114 字位置错误未更正 | **属实** | §5/§6 状态更新 + 新增 §7（4 条改写规则、五/六讲更正、公开版哈希、quote_sha256 自校验 True、远端生效） |
| FILE_MANIFEST 同步源仍写 37ee224 | **属实**（待批准表述过期） | 头部改为已执行状态 + 最终远端 SHA；哈希经 `git cat-file` 复核与发布 blob 逐字节一致 |
| PUBLIC_TREES_AUDIT 842/886/887 未统一、算术笔误（raw 20→21、tools 156→157） | **属实**（审核者两处算术怀疑均坐实） | §3/§6 标注为历史快照并更正笔误；新增 §7 四数字统一口径（① 枚举 890 / ② 白名单 889 / ③ 发布 blob 897 / ④ 默认拒绝 1，LOGS/count_reconciliation.log 机器可复核） |

技术说明：审核方与我在"COMPLETE_REPORT/FINAL_CHANGE_REPORT 是否含执行记录"上的差异，源于其核对的是推送 #1（eba6774）版本——该推送之后我又追加了执行记录并经推送 #2（26bf0f7）入仓。`git cat-file` 复核确认远端 blob 与本地文件逐字节一致（均为 LF）。

## 16.3 其他收尾项

- **GitHub About 描述已修正**：原"生成、润色与赏析中文诗词的 Agent Skill。"与 README"非已发布 Skill"矛盾；改为"中文诗词文献与格律研究仓库（Phase 0–2 研究阶段，Agent Skill 未发布）：格律引擎研究原型、词谱/韵书元数据、逐轮审计报告与同步治理工具。"
- **审计深度表述准确化**：PUBLIC_TREES_AUDIT §7 明确本轮 = 枚举/扩展名与二进制审查/凭据路径扫描/高风险定向精读/白名单控制，未逐文件通读全部正文。
- 四数字统一口径落地，今后每轮以 `count_reconciliation.py` 输出为准。

## 16.4 第二轮收尾结论

- **SELF_STATUS：PASS（收尾范围内）**——审核 10 项要求全部落实；远端 main `26bf0f7…`；本节经第三次小同步入仓后，远端报告与实际状态一致。
- 待审核复核：本节 + 五份更新后的报告 + About 新描述；R2-16D/E/F 留待数据库 Agent（本 Agent 未触碰）。
