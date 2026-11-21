# 仓库同步说明（工具生成，勿手改）

本文件由 `poetry-database/tools/github_sync.py`（严格逐文件白名单 v3，R2-16C 第二轮）生成。
项目介绍见 `README.md`（人工维护，工具不会覆盖）。

## 同步机制（v3）

- **逐文件白名单，默认拒绝**：唯一导出来源是 `poetry-database/tools/public_files.txt` 登记的文件；
  未登记文件一律不导出。新增文件必须先通过公开审计并登记。
- 每轮导出开始时，仓库工作树除 `README.md`、`LICENSE`（保护名单）外**全部清空**，再复制白名单文件。
- 版权/隐私关键路径为硬排除：白名单或收集阶段命中即中止整次同步。
- **导出时改写**：`tools/public_redactions.json` 声明的逐字段落只作用于公开副本
  （替换为原创摘要），本地原始研究文件永不修改。
- **暂停公开**：`raw/r2_04_evidence/ocr_samples.json`、`theory_locate.json` 原件维持本地（R2-16B 裁决）；
  公开版 `ocr_samples_public.json`、`theory_locate_public.json` 由 `tools/make_public_evidence.py` 生成。
- 每轮生成 `SYNC_DIFF.md`（相对上一轮公开状态的增/改/删清单）与 `UPLOAD_MANIFEST.csv`
  （逐文件 SHA-256，按脱敏+改写后的最终公开文件计算）。
- 推送为普通 fast-forward 推送（非 force）。

## 仓库内容

| 路径 | 内容 |
|---|---|
| `AGENTS.md` / `AGENT_REPORTING_STANDARD.md` | 项目长期指令与汇报制度 |
| `docs/` | 原始方案、历史文档与原 README 备份 |
| `诗词格律引擎/` | 格律引擎代码、独立测试集、原创知识库与执行报告（引擎冻结，仅研究用） |
| `poetry-database/reports/` | **逐轮完整报告**（含每轮 `COMPLETE_REPORT.md` 与全部交付件） |
| `poetry-database/tools/` | 审计与同步工具（逐文件白名单/改写规则/公开证据生成） |
| `poetry-database/catalog|research|audit|sources/` | 词谱、书目与审计元数据（公有领域古籍与事实数据） |
| `poetry-database/raw/` | 经 R2-16B 审查的证据与笔记（公开版/改写版） |
| `SYNC_DIFF.md` | 本轮相对上一轮的公开目录差异 |
| `UPLOAD_MANIFEST.csv` / `UPLOAD_REPORT.md` | 逐文件校验值与上传说明、排除项 |

## 不上传的内容（硬性）

1. **数据库文件**：`poetry.db` 等 SQLite 及超 GitHub 单文件上限的二进制。
2. **版权书全文**：`books/`、`raw/books*`、`raw/r2_04_evidence/full|chapters`（现代版权著作正文）。
3. **暂停公开原件**（R2-16B 裁决）：`ocr_samples.json`、`theory_locate.json`（公开版为 `*_public.json`）。
4. **二进制工具**：`tools/ocr_vision`（macOS Mach-O，公开审计决定不公开）。
5. **本机个人信息**：所有文本中的本机家目录与绝对路径已替换为占位符。

## 同步方式

每轮任务完成后，在项目根目录执行：

```bash
python poetry-database/tools/github_sync.py
```

新产出文件（如新一轮报告）必须先登记进 `tools/public_files.txt` 才会被导出。
远端认证使用 HTTPS + `gh` CLI 凭据；`GITHUB_SYNC_REPO_URL` / `GITHUB_SYNC_STAGING`
可覆盖远端与暂存位置。加 `--dry-run` 只做白名单审计，不建暂存、不推送。
