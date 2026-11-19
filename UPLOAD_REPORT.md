# GitHub 上传报告

- 时间：2026-11-20T01:16:47
- 仓库：`git@github.com:iop666/Poetry-Generation-Skill.git`（公开）
- 上传文件：**864** 个，合计 **51,444,697** 字节
- 脱敏处理：CLEAN 767、COPIED 16、SANITIZED 80、VERBATIM 1
- 推送前门禁：本机路径 / 手机号 / 凭据残留 **0 处**；邮箱 2 个（git@github.com, researcher@example.org）

## 排除项及原因

| 路径 | 原因 |
|---|---|
| `poetry-database/database/poetry.db` | 732 MB，超 GitHub 单文件上限；含本机绝对路径 |
| `poetry-database/normalized/*.jsonl` | 395 MB，超 GitHub 单文件上限 |
| `books/*.pdf|epub` | z-library 来源的现代版权书全文，项目规则禁止分发 |
| `poetry-database/raw/books*/**` | 上述版权书的 OCR 全文与书页图像 |
| `poetry-database/raw/r2_04_evidence/full|chapters` | 现代版权著作连续章节正文（2026-11-20 起排除） |
| `poetry-database/raw/*/images|facsimile` | 书页影印，版权风险 |
| `.workbuddy/**` | 本机记忆与临时数据 |

## 复核

逐文件 SHA-256 见 `UPLOAD_MANIFEST.csv`。
可用 `python3 poetry-database/tools/github_sync.py --dry-run` 复算白名单。
