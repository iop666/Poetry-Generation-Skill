# Poetry Generation Skill — 项目资料仓库

本仓库保存诗词项目的**报告、审计材料、工具脚本与知识库文档**，供外部审查与复现。

## 内容

| 路径 | 内容 |
|---|---|
| `AGENTS.md` / `AGENT_REPORTING_STANDARD.md` | 项目长期指令与汇报制度 |
| `docs/` | 原始方案与历史文档 |
| `诗词格律引擎/` | 格律引擎代码、独立测试集与执行报告（引擎冻结，仅研究用） |
| `poetry-database/reports/` | **逐轮完整报告**（含每轮 `COMPLETE_REPORT.md` 与全部交付件） |
| `poetry-database/tools/` | 审计与同步工具 |
| `poetry-database/catalog|research|audit|sources/` | 词谱、书目与审计元数据 |
| `UPLOAD_MANIFEST.csv` | 本轮上传文件的逐项字节数与 SHA-256 |
| `UPLOAD_REPORT.md` | 本轮上传说明与排除项 |

## 不上传的内容（硬性）

1. **数据库文件**：`poetry.db`（732 MB）等超过 GitHub 单文件 100 MB 上限的二进制。
2. **版权书全文**：`books/`（z-library 来源的王力、龙榆生著作）及其 OCR 文本/书页图像。
   项目规则：现代版权著作只登记书目与合法渠道，不得抓取或分发全文。
3. **本机个人信息**：所有文本中的本机家目录与绝对路径已替换为 `<PROJECT_ROOT>` / `<HOME>` / `<LOCAL_WORKBUDDY>`。

## 同步方式

每轮任务完成后，在项目根目录执行：

```bash
python3 poetry-database/tools/github_sync.py
```

工具会重建白名单暂存、脱敏、生成新的清单与上传报告，然后推送到 `main`。
需要本机已配置 GitHub SSH key。加 `--dry-run` 只做本地检查不推送。
