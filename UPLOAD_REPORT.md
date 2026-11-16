# GitHub 上传报告

- 时间：2026-11-16T21:52:51
- 仓库：`git@github.com:iop666/Poetry-Generation-Skill.git`（公开）
- 上传文件：**861** 个，合计 **48,615,698** 字节
- 脱敏处理：CLEAN 769、COPIED 15、SANITIZED 77
- 推送前门禁：本机路径 / 手机号 / 凭据残留 **0 处**；邮箱 1 个（researcher@example.org）

## 排除项及原因

| 路径 | 原因 |
|---|---|
| `poetry-database/database/poetry.db` | 732 MB，超 GitHub 单文件上限；含本机绝对路径 |
| `poetry-database/normalized/*.jsonl` | 395 MB，超 GitHub 单文件上限 |
| `books/*.pdf|epub` | z-library 来源的现代版权书全文，项目规则禁止分发 |
| `poetry-database/raw/books*/**` | 上述版权书的 OCR 全文与书页图像 |
| `poetry-database/raw/*/images|facsimile` | 书页影印，版权风险 |
| `.workbuddy/**` | 本机记忆与临时数据 |

## 复核

逐文件 SHA-256 见 `UPLOAD_MANIFEST.csv`。
可用 `python3 poetry-database/tools/github_sync.py --dry-run` 复算白名单。
