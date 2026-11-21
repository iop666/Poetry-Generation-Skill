# SYNC_DIFF —— 本轮公开目录相对上一轮（origin/main）的差异

- 生成时间：2026-11-21T16:02:04
- 对比基准：origin/main（导出前 HEAD）
- 状态：A=新增 M=修改 D=删除 R=改名；增/删行数来自 git numstat

| 状态 | 路径 | 增/删行 |
|---|---|---|
| M | `REPORTS_INDEX.md` | +1/-1 |
| D | `SYNC_DIFF.md` | +0/-23 |
| M | `UPLOAD_MANIFEST.csv` | +10/-7 |
| M | `UPLOAD_REPORT.md` | +3/-3 |
| M | `poetry-database/reports/tasks/2026-11-21/R2-16/COMPLETE_REPORT.md` | +38/-0 |
| M | `poetry-database/reports/tasks/2026-11-21/R2-16/FILE_MANIFEST.md` | +13/-8 |
| M | `poetry-database/reports/tasks/2026-11-21/R2-16/FINAL_CHANGE_REPORT.md` | +11/-1 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/count_reconciliation.log` | +30/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/remote_tree_head_26bf0f7.txt` | +897/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/verify_final_greps.log` | +27/-0 |
| M | `poetry-database/reports/tasks/2026-11-21/R2-16/PUBLIC_TREES_AUDIT.md` | +19/-0 |
| M | `poetry-database/reports/tasks/2026-11-21/R2-16/R2-16C_TEST_RESULTS.md` | +86/-57 |
| M | `poetry-database/reports/tasks/2026-11-21/R2-16/SOURCE_AUDIT.md` | +35/-7 |
| M | `poetry-database/tools/public_files.txt` | +3/-0 |

合计：新增 3、修改 10、删除 1、改名 0。
（SYNC_DIFF.md 自身为每轮重新生成，其自身变更不列入本表。）

Manifest 与导出树的双向一致性由 github_sync.py verify_export 在推送前强制校验。
