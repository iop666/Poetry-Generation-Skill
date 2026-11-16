# SOURCE_AUDIT —— R2-03-R1 来源审计

| 项 | 内容 |
|---|---|
| 任务 | R2-03-R1：用 PaddleOCR-VL-1.6 重跑 R2-03 未完成的三本扫描书 OCR |
| 日期 | 2026-11-13 |
| 审计范围 | 原始文件、OCR 引擎、上传合规、凭据、结果质量等级、缺口 |

---

## 1. 本地原始文献（只读）

三本纯图像扫描本，文件路径与 SHA-256 见 `../R2-03/BOOK_INVENTORY.md`；本轮**未修改、未改名、未复制原书全文**。

| book_id | 文件 | 字节 | 页 | 文字层 |
|---|---|---:|---:|---|
| `wangli_shicilv` | 王力全集 诗词格律 诗词格律概要 | 6,403,238 | 432 | 无 |
| `wangli_yinyunxue` | 王力全集 汉语音韵学 | 9,430,420 | 476 | 无 |
| `wangli_tongyuan` | 王力全集 同源字典 | 17,954,213 | 783 | 无 |
| 合计 | 3 本 | 33,787,871 B ≈ 32.2 MiB | 1,691 | — |

**未上传**：2 本 EPUB（《词学十讲》《古代汉语常识》）、有文字层的《唐宋词格律》PDF、
341 B 的 `.textClipping`。理由：无需 OCR，避免不必要的第三方上传。

## 2. OCR 引擎来源

| 项 | 值 |
|---|---|
| 引擎 | `PaddleOCR-VL-1.6`（由脚本写入 `pages.jsonl.engine` 与 `meta.json.engine`） |
| 调用方式 | 用户级 skill `paddleocr-vl`，唯一入口 `~/.workbuddy/skills/paddleocr-vl/scripts/paddleocr_vl.py` |
| 形态 | 公网 SaaS 异步任务 API 客户端，**非本地 Python 包** |
| 端点 | `https://paddleocr.aistudio-app.com/api/v2/ocr/jobs` |
| 模型参数 | `model=PaddleOCR-VL-1.6` |
| 鉴权 | `Authorization: bearer <token>`，凭据文件 `~/.workbuddy/.credentials/paddleocr_vl.json` |
| 任务粒度 | **整本一次提交**（3 个任务，非逐页），避免排队开销放大 |
| jobId | 逐本记录于 `raw/books_ocr_paddle/<book_id>/meta.json` 与 `COMPLETE_REPORT.md` §7 |
| 文档依据 | skill 自带 `references/api_reference.md`（2026-11-11 实测契约） |

对照基线：R2-03 的 `macos-vision-rev2`，`raw/books_ocr/<book_id>/pages.jsonl`，
**原样保留，engine 不改标，结果不冒充 PaddleOCR**。

## 3. 上传合规

1. 用户于 2026-11-13 明确点名：「PDF的识别等内容请用PaddleOCR-VL-1.6的api」；
2. 本轮用户再次明确「你可以直接调用了，重试刚才未完成的任务」；
3. 本轮交互中用户选择「我贴 token（推荐）」，该选项文案已写明「选择此项即表示同意上传这三本 PDF」。

以上构成 skill 铁律 2 所要求的上传确认，故 `run` 显式带 `--allow-upload`。
未使用环境变量绕过闸门，未私换其它在线 OCR 服务。

## 4. 凭据处理

- 用户提供 token 后，用 `setup-token --stdin` 写入 `~/.workbuddy/.credentials/paddleocr_vl.json`，权限 `0600`（父目录 `0700`），`check` 复检 `ready=true`。
- token **未写入**任何报告、脚本、数据库、日志或 ZIP；仅出现于本机凭据文件与一次性 stdin 管道。
- 报告只记录 `tokenLength=40`、`configured=true`，不记录明文。

## 5. 结果质量等级（按 `AGENT_REPORTING_STANDARD.md` v2.0 词表）

| 对象 | 等级 | 理由 |
|---|---|---|
| PaddleOCR 逐页文本 | `PARSED` + `SOURCE_TRACEABLE` | 机器解析成功，可回溯到具体 PDF 物理页、jobId、引擎；**但未与影印本逐字对勘** |
| 与 Vision 的对照数据 | `CROSS_SOURCE_COMPARED` | 两个引擎并列，统计差异与符号命中 |
| 理论规则 | **未升级** | 本轮不新增、不改写 `theory_claims`；格律符号须人工复核后方可引用 |
| 版本校勘 | `EDITION_VERIFIED = 0` | 无影印本对勘，本轮不改善此项 |

**明确不做的结论**：本审计不宣称 PaddleOCR 比 Vision「更准」，只提供可复核的差异数据。
自动择优、把 OCR 规则写进正式格律库、修改引擎，均属未授权范围。

### 5.1 基线有效性更正（本轮实测后追加）

按「相邻页文本完全相同」检验，作为对照基线的 Vision 版
`raw/books_ocr/*/pages.jsonl` 存在「每 16 页一批」的复制填充：

| 书 | 名义页 | 重复页 | 实际不同文本 |
|---|---:|---:|---:|
| 诗词格律·概要 | 432 | 337 | 94 |
| 汉语音韵学 | 476 | 431 | 45 |
| 同源字典 | 783 | 719 | 64 |

因此上表中「`CROSS_SOURCE_COMPARED`」一行**降级作废**：
`ocr_comparison` 的逐页配对不可用于结论，已置 `baseline_valid=0`；
`alignment.json` 与 `COMPARISON_SUMMARY.json` 标记 `INVALID`。
**有效的只有全书级去重统计**（重复页数、符号次数）与 PDF 原图核验。
Vision 版原文仍原样保留，不删除、不改 engine（失败记录须留存）。

## 6. 仍缺的来源（不因本轮改变）

| 缺口 | 状态 |
|---|---|
| 《诗经韵读》《楚辞韵读》PDF | **仍缺失**，books/ 里只有 341 B `.textClipping`，无法 OCR |
| 《集韻》正文 216 子页 | 未补 |
| 辽代作品（0 条） | 未补 |
| `author_entities` 表 | 未建 |
| 版本学核验 | 0 |

## 7. 禁止事项核查

| 禁止项 | 本轮 |
|---|---|
| 伪造来源 / 伪造引擎标注 | 无；engine 由脚本写入，逐页可查 |
| 删除失败日志 | 无；日志留存于 `LOGS/` 与 `.tmp` |
| 修改 `gedou.py` / 格律引擎 | 未修改 |
| 进入 Phase 3 知识体系 | 未进入 |
| 封装 Skill / 模型微调 | 未做 |
| 覆盖 Vision 原文 | 未覆盖，另表存放 |
| 数据完整性核查 | 已做：相邻重复页计数、去重文本数、PDF 原图三点核验 |
| 作废数据是否删除 | 否，只加标记（`baseline_valid=0` / `INVALID`） |
