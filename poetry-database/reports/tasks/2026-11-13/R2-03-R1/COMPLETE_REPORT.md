# COMPLETE_REPORT —— R2-03-R1

| 项 | 内容 |
|---|---|
| 任务编号 | R2-03-R1（用户指令：「重试刚才未完成的任务」） |
| 日期 | 2026-11-13 |
| 工作目录 | `<PROJECT_ROOT>/poetry-database` |
| 任务来源 | 用户已把 PaddleOCR-VL-1.6 固化为 skill，要求重做 R2-03 未完成的 OCR |
| 前置任务 | R2-03（核心文献导入、OCR 解析与系统阅读） |
| 结论 | **PARTIAL**（OCR 重跑完成；OCR 质量未达标；并推翻 R2-03 一项核心数据结论） |
| 阶段 | Phase 1 文献阅读；**Phase 3 未授权、Phase 4 引擎冻结** |

---

## 1. 执行概况

### 1.1 一句话

用 **PaddleOCR-VL-1.6** 把三本扫描书 **1,691 页全部重跑成功并入库**，
同时查出 **R2-03 的 macOS Vision 结果有 1,487 页是复制填充**（实际只有 203 份不同文本），
并正式更正 R2-03 的四项错误结论；但新结果在格律符号上仍有系统性误识，**不能算质量达标**。

### 1.2 必须先讲的三件事

1. **R2-03 说「PaddleOCR 在本环境不可用」是错的**：能力早已作为用户级 skill 接入，缺的只是 token。用户提供后 `ready=true`，三个任务全部成功。
2. **R2-03 的 OCR 逐页数据是损坏的**：每 16 页一批复制填充，「1,691 页 / 140 万字」是虚高口径。这是本轮最严重的发现，已在 `ERRATA.md` 第四节正式更正。
3. **PaddleOCR 也不是「修好了」**：它消除了「○→四/心/西/闪」，但把「字外加圈」识成 ⑨/⑩ 并丢字；格律谱仍须对原图逐条核对。

---

## 2. 执行前状态

- `poetry-database` 已有 375,399 条作品、`book_pages` 2,010 行（Vision OCR + 原生提取）。
- R2-03 报告称 PaddleOCR 不可用，改用 macOS Vision rev2；`EDITION_VERIFIED=0`。
- 用户级 skill `paddleocr-vl` 已存在但**凭据为空**（2026-11-11 那次靠临时环境变量，未持久化）。
- 本机历史会话、shell 历史、skill 目录、2026-11-11 接入工具中**均无有效 AI Studio token**。
- `books/` 六本实体书 + 一个 341 B `.textClipping`（《诗经韵读》《楚辞韵读》仍缺失）。

---

## 3. 本次实际工作

| # | 工作 | 结果 |
|---|---|---|
| 1 | 加载 skill 并按铁律跑 `check` | `isCloudApi=true`、`ready=false`（只缺 token） |
| 2 | 全盘检索历史凭据 | 未找到；会话里的 43 字符 token 属内置 VLM 代理，非本 API |
| 3 | `plan` + `--dry-run` | 列出 3 本待上传 PDF、286 疑似页；未联网未上传 |
| 4 | 向用户索取 token | 用户提供，`setup-token --stdin` 写入 0600；`check` 复检 `ready=true` |
| 5 | 整本提交三本扫描本 | 3 个任务全部 OK，1,691 页，0 失败，26 m 10 s |
| 6 | 逐页对照与入库 | `book_pages_paddle` 1,691 行、`ocr_comparison` 1,691 行 |
| 7 | 发现对照相似度异常 | 汉字相似度仅 0.23–0.34，先怀疑页码漂移 |
| 8 | 下载 API 原始 jsonl 查分片结构 | 3/4 页分片；**后证明页序正确，怀疑方向错误** |
| 9 | 逐页重复性检验 | **查出 Vision 版 1,487 页复制填充**，根因定位 |
| 10 | 渲染 PDF 原图核验页序 | p35 / p100 / p200 与 Paddle 同号页吻合，撤回漂移推断 |
| 11 | 作废标记与质量发现登记 | `baseline_valid=0`、`ocr_quality_findings` 7 条 |
| 12 | 正式勘误 | `ERRATA.md`（四项错误 + 一项本轮误判）；R2-03 两份报告加顶部告示 |
| 13 | 符号质量抽样 | 圈号、带圈数字、入声点标记、丢字四类结论 |

---

## 4. 数据成果

### 4.1 入库存量

| 表 / 文件 | 数量 | 说明 |
|---|---:|---|
| `book_pages_paddle`（新） | **1,691** | 每页带 `engine=PaddleOCR-VL-1.6`、`jobId` |
| `ocr_comparison`（新） | 1,691 | **全部 `baseline_valid=0`，逐页结论作废** |
| `ocr_quality_findings`（新） | 7 | 数据完整性与符号质量发现 |
| `ocr_runs` 新增 | 3 | 本轮 PaddleOCR 运行记录（幂等，无重复） |
| `raw/books_ocr_paddle/*/pages.jsonl` | 1,691 | 逐页文本 |
| `raw/books_ocr_paddle/*/api_result.jsonl` | 3 份 | API 原始返回（含分片结构） |
| `alignment.json` | 1 | **标记 INVALID**，保留过程记录 |
| `book_pages`（旧） | 2,010 | **未改动**，原样保留 |

### 4.2 完整性对照

| 书 | 名义页 | Vision 重复页 / 实际文本 | Paddle 重复页 / 实际文本 | Paddle 空页 |
|---|---:|---:|---:|---:|
| 诗词格律·概要 | 432 | 337 / **94** | 0 / 426 | 7 |
| 汉语音韵学 | 476 | 431 / **45** | 0 / 476 | 1 |
| 同源字典 | 783 | 719 / **64** | 0 / 783 | 1 |
| 合计 | 1,691 | **1,487 / 203** | **0 / 1,685** | **9** |

### 4.3 符号质量（去重后）

| 指标 | Vision | PaddleOCR |
|---|---:|---:|
| 「○→汉字」误识 | 93 次 | 5 次 |
| ⑨/⑩ 带圈数字（《诗词格律》） | 1 | **482 次 / 130 页** |
| 入声字下加点标记 | **0** | **4,368** |
| 七律对照表 `○○` 圈号 | 误作 `◎〇` / `OO` | 正确 |

---

## 5. 文件变更

### 5.1 新增脚本

| 文件 | 用途 |
|---|---|
| `tools/paddle_rerun.py` | `plan / run / compare / ingest / all`；调 skill、逐页对照、入库；缺 token 直接报错不换引擎 |
| `tools/paddle_align.py` | 按内容对齐页号（探索工具，**基于错误前提，产物已标记 INVALID**） |
| `tools/finalize_r2_03_r1.py` | 作废旧基线、登记 7 条质量发现 |

### 5.2 新增报告与数据

`reports/tasks/2026-11-13/R2-03-R1/`：`COMPLETE_REPORT.md`、`ERRATA.md`、
`OCR_QUALITY_REPORT.md`、`SOURCE_AUDIT.md`、`TEST_RESULTS.md`、`FILE_MANIFEST.md`、`LOGS/`。
`raw/books_ocr_paddle/`：`pages.jsonl` ×3、`meta.json` ×3、`api_result.jsonl` ×3、
`comparison.jsonl`、`COMPARISON_SUMMARY.json`（INVALID）、`alignment.json`（INVALID）、`runs.json`。

### 5.3 修改

- `AGENTS.md`：阶段状态更新，记录 PaddleOCR 误判更正。
- `R2-03/COMPLETE_REPORT.md`、`R2-03/OCR_QUALITY_REPORT.md`：顶部加正式勘误告示。
- `database/poetry.db`：新增 3 表、`ocr_comparison` 加 `baseline_valid` 列。

### 5.4 未修改

`books/` 原书一字未改；`诗词格律引擎/`、`gedou.py` 未动；`book_pages`（Vision 版）未删未覆盖；
`theory_claims`、`cipai_specs` 未增删；未进入 Phase 3、未封装 Skill、未做模型微调。

---

## 6. 技术实现

1. **凭据闸门**：`check` → `setup-token --stdin` → 复检 → `--allow-upload`，四步齐全；token 不进报告/代码/库/ZIP。
2. **整本提交**：3 个任务而非 1,691 次请求；API 内部按 3 或 4 页分片，返回顺序不影响落盘页号（经原图核验）。
3. **对照指标**：`bag_ratio`（多重集合 Jaccard）、`han_ratio`（只看汉字，排除 Markdown/LaTeX 噪声）、
   圈号 / 带圈数字 / 汉字误识 / 入声点标记 / 丢字抽样。
4. **完整性检验**：相邻页文本完全相同计数 + 连续重复段长度，定位「16 页一批」的槽位复用 bug。
5. **页序核验**：pymupdf 渲染 PDF 物理页 → 人工读图 → 与同号 Paddle 文本比对。
6. **不覆盖原则**：Vision 版与派生数据全部保留；作废数据只加标记，不删除。

---

## 7. 实际验证

| # | 命令 / 操作 | 结果 |
|---|---|---|
| 1 | `paddleocr_vl.py check`（首次） | `ready=false`，仅缺 token |
| 2 | `setup-token --stdin` + `check` | 0600 凭据，`ready=true` |
| 3 | `paddle_rerun.py plan` / `--dry-run` | 列出 3 本、不联网不上传 |
| 4 | `paddle_rerun.py all --allow-upload` | 3 任务 OK，432+476+783=1,691 页，0 失败 |
| 5 | `paddle_rerun.py compare` | 1,691 页对照，`han_ratio` 全非空 |
| 6 | `paddle_rerun.py ingest` | 1,691 + 1,691 行，`ocr_runs` 幂等 3 条 |
| 7 | 重复性检验 | Vision 1,487 重复页 / Paddle 0 |
| 8 | PDF 原图 p35/p100/p200 | 与 Paddle 同号页逐页吻合 |
| 9 | `finalize_r2_03_r1.py` | `baseline_valid` 全 0，7 条发现入库 |
| 10 | `python3 -m py_compile` ×3 | 全部通过 |
| 11 | 数据库校验 | `book_pages` 仍 2,010；`book_pages_paddle` 1,691，engine 单一 |

**没有一项结论来自「假装跑过」**；jobId、页数、行数、原图核验均可复核。

---

## 8. 问题记录

### 8.1 本轮解决

| # | 问题 | 处理 |
|---|---|---|
| 1 | R2-03 误判 PaddleOCR 不可用 | 检索 skill、补 token，三本重跑成功 |
| 2 | token 未持久化 | `setup-token --stdin` 写入 0600 凭据 |
| 3 | 上传合规 | 用户明确点名 + 显式 `--allow-upload` |
| 4 | 对照相似度异常 | 定位为 Vision 重复填充，非 Paddle 页序问题 |
| 5 | 页序疑云 | 原图三点核验，撤回漂移推断 |
| 6 | 逐页数据虚高 | 正式勘误 + 作废标记 + 新表另存 |
| 7 | 旧表会污染后续引用 | `baseline_valid=0`；原表保留不改 |

### 8.2 未解决（OPEN）

| 编号 | 问题 | 严重度 |
|---|---|---|
| U-01 | 「字外加圈」仍被识成 ⑨/⑩ 且平仄谱丢字 | **高** |
| U-02 | 9 个空页未补 | 中 |
| U-03 | 入声点 LaTeX 标记未与影印本逐字核对 | 中 |
| U-04 | R2-03 的 16 条 `theory_claims` 引文页码未逐条回查 | **高** |
| U-05 | `book_items.chars` / R2-03 字数表口径失效，未重算 | 中 |
| U-06 | 《诗经韵读》《楚辞韵读》PDF 仍缺失 | 高 |
| U-07 | 《诗词格律》仅读 4%；音韵学、同源字典未读 | 高 |
| U-08 | `EDITION_VERIFIED=0`；辽代 0；`author_entities` 未建 | 高 |

---

## 9. 上轮审核意见处理（R2-03 审核请求）

| 审核请求 | 本轮回应 | 状态 |
|---|---|---|
| 「OCR 质量：rev2/rev3 对比是否足以支撑正文可用、词谱表不可用」 | **不足以支撑**：该结论建立在重复填充数据上，已整体作废；本轮改以 PaddleOCR 版 + 原图核验重新给结论 | **SUPERSEDED** |
| 「16 条理论条目引文与页码是否相符」 | 未逐条回查；已登记 U-04，且指出引文可能取自重复填充页 | **OPEN** |
| 「76 调里 21 调字数不符」 | 词谱取自《唐宋词格律》文字层，与扫描 OCR 无关；本轮不改此结论 | **未处理（本轮范围外）** |

---

## 10. 项目整体进度

| Phase | 状态 |
|---|---|
| Phase 0 文献搜集 | PARTIAL（52 条书目，34 条未取得） |
| Phase 1 文献阅读 | **有进展但基础数据重写**：6 本入库，扫描本 OCR 换引擎并重跑；无一读完 |
| Phase 2 作品库 | 375,399 条；本轮未扩充 |
| Phase 3 知识体系 | **未授权** |
| Phase 4 引擎 | **冻结** |

---

## 11. 下一步建议（未授权不执行）

| 序 | 任务 | 验收 |
|---|---|---|
| 1 | 逐条回查 16 条 `theory_claims` 的引文与页码（用 PaddleOCR 版 + 原图） | 每条标注「原文一致 / 不一致 / 存疑」 |
| 2 | 重算 `book_items.chars` 与 R2-03 字数表，按去重口径 | 与 `pages.jsonl` 可复核 |
| 3 | 补 9 个空页；人工校订格律符号页（⑨/⑩、丢字） | 修订写入 `ocr_corrections`，不覆盖原文 |
| 4 | 用 PaddleOCR 版重读《诗词格律》并补齐理论条目 | 每章笔记，关键规则带页码 |
| 5 | 反馈给 skill：`save_results` 应保留原始 jsonl 与真实页码 | 可追溯到 PDF 物理页 |
| 6 | 补《诗经韵读》《楚辞韵读》PDF | 能解析并列出韵部表 |

---

## 12. 自我审计（六问）

1. **有没有把「重跑成功」说成「质量达标」？** 没有。第 4.3 节明确登记新失败模式，结论为 PARTIAL。
2. **有没有为了好看而夸大？** 没有。反而主动推翻了 R2-03 的 1,691 页 / 140 万字，并撤回本轮自己的页码漂移推断。
3. **有没有删失败记录？** 没有。Vision 原页、`alignment.json`、`COMPARISON_SUMMARY.json` 均保留并标记。
4. **token 安全吗？** 只在 0600 凭据文件与一次性 stdin 管道；报告、代码、库、ZIP 均无。
5. **页序结论可靠吗？** 三点原图核验，抽样有限但足以否定「整体漂移」；全书逐页未核，已在 U-03 注明。
6. **有没有越界？** 未改引擎、未进 Phase 3、未封装 Skill、未把 OCR 规则写入正式库。

---

## 13. 审核请求

请重点核三处：

1. **数据完整性结论**（`ERRATA.md` §4、`OCR_QUALITY_REPORT.md` §3）：1,487 页复制填充的判定与「每 16 页一批」的根因是否成立。
2. **撤回页码漂移推断**（`ERRATA.md` §5）：三点原图核验是否足以否定该推断。
3. **PaddleOCR 的符号质量**（`OCR_QUALITY_REPORT.md` §4）：「修复了汉字误识、但新增带圈数字与丢字」是否应判为 PARSED 而非 TEXT_CROSSCHECKED。

---

## 14. 最终结论

**SELF_STATUS：PARTIAL**

已完成：用 PaddleOCR-VL-1.6 重跑三本扫描书 1,691 页（3 个 jobId，0 失败），逐页落盘入库；
查出并正式更正 R2-03 四项错误结论（含「1,691 页 OCR」这一虚高口径）与本轮一项误判；
经原图核验确认新结果页序正确、无重复页、额外保住 4,368 处入声字标记。

未完成：格律符号仍不可直接引用（⑨/⑩、丢字）；9 个空页；理论条目引文未回查；
字数口径未重算；《诗经韵读》《楚辞韵读》仍缺；`EDITION_VERIFIED=0`。

**本轮把「OCR 是否做完」这个问题解决了，但把「OCR 文本能不能用来建规则」这个问题明确地留成了未解决。**
完成后停止，等待用户转交外部审核。
