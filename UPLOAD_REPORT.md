# GitHub 上传报告

- 时间：2026-11-21T16:02:03
- 仓库：`https://github.com/iop666/Poetry-Generation-Skill.git`（公开）
- 同步机制：严格逐文件白名单 v3（默认拒绝未登记文件）——导出树先清空（保护名单除外），再复制 `tools/public_files.txt` 登记的文件
- 本轮导出：**892** 个文件，合计 **51,633,481** 字节
- 脱敏处理：CLEAN 854、COPIED 34、REDACTED_PUBLIC 3、VERBATIM 1
- 推送前门禁：本机路径 / 手机号 / 凭据残留 **0 处**；邮箱 1 个（researcher@example.org）
- 生成后校验：Manifest 双向对应、全部文件在白名单内、SHA-256（脱敏+改写后文件）可复算、硬排除 0。
- 差异报告：见 [SYNC_DIFF.md](SYNC_DIFF.md)。

## 排除项及原因

| 路径 | 原因 |
|---|---|
| `poetry-database/raw/r2_04_evidence/ocr_samples.json` | R2-16B 裁决：维持 WITHHELD。公开版 ocr_samples_public.json 只保留页码/字符统计/质量标记，不保留 OCR 正文前缀（make_public_evidence.py 生成） |
| `poetry-database/raw/r2_04_evidence/theory_locate.json` | R2-16B 裁决：维持 WITHHELD。公开版 theory_locate_public.json 保留页码/主题/核验状态，引文以 SHA-256 代替（make_public_evidence.py 生成） |
| `poetry-database/database/poetry.db` | SQLite 数据库，含本机绝对路径（硬排除） |
| `poetry-database/normalized/*.jsonl` | 超 GitHub 单文件上限语料（硬排除） |
| `books/*.pdf|epub` | 现代版权书全文，项目规则禁止分发（硬排除） |
| `poetry-database/raw/r2_04_evidence/full|chapters` | 现代版权著作连续正文（硬排除，历史清理对象） |
| `poetry-database/raw/*/images|facsimile` | 书页影印，版权风险（硬排除） |
| `.workbuddy/**` | 本机记忆与临时数据（硬排除） |
| `poetry-database/tools/ocr_vision` | macOS Mach-O 二进制，公开审计决定不公开（R2-16C 第二轮） |
| `（原八棵树下未登记文件共 1 个）` | 默认拒绝：未通过公开审计登记 |

## 复核

逐文件 SHA-256 见 `UPLOAD_MANIFEST.csv`。
可用 `python poetry-database/tools/github_sync.py --dry-run` 复算白名单与默认拒绝审计。
