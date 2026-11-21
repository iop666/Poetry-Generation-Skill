# SYNC_DIFF —— 本轮公开目录相对上一轮（origin/main）的差异

- 生成时间：2026-11-21T15:35:37
- 对比基准：origin/main（导出前 HEAD）
- 状态：A=新增 M=修改 D=删除 R=改名；增/删行数来自 git numstat

| 状态 | 路径 | 增/删行 |
|---|---|---|
| M | `.gitignore` | +4/-3 |
| M | `GITHUB_SYNC.md` | +30/-17 |
| M | `REPORTS_INDEX.md` | +3/-2 |
| M | `UPLOAD_MANIFEST.csv` | +111/-88 |
| M | `UPLOAD_REPORT.md` | +19/-13 |
| D | `poetry-database/README.md` | +0/-105 |
| D | `poetry-database/raw/r2_04_evidence/ocr_samples.json` | +0/-354 |
| A | `poetry-database/raw/r2_04_evidence/ocr_samples_public.json` | +322/-0 |
| D | `poetry-database/raw/r2_04_evidence/theory_locate.json` | +0/-178 |
| A | `poetry-database/raw/r2_04_evidence/theory_locate_public.json` | +178/-0 |
| M | `"poetry-database/raw/r2_05_notes/A_02_\347\254\254\344\272\214\347\253\240.md"` | +5/-4 |
| M | `"poetry-database/raw/r2_05_notes/A_05_\351\231\204\345\275\225\344\270\200.md"` | +1/-1 |
| M | `"poetry-database/raw/r2_06_notes/C_\350\257\227\350\257\215\346\240\274\345\276\213\345\215\201\350\256\262.md"` | +2/-2 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/COMPLETE_REPORT.md` | +274/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/FILE_MANIFEST.md` | +78/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/FINAL_CHANGE_REPORT.md` | +61/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/quote_stats.log` | +38/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/redaction_dryrun.log` | +6/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/run_a2_full_sync.log` | +41/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/run_a3_v3_sync.log` | +21/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/run_a_full_sync.log` | +41/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/run_b_hard_abort.log` | +8/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/run_b_v3_hard_abort.log` | +1/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/run_c2_dryrun.log` | +30/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/run_c_dryrun.log` | +8/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/run_c_v3_dryrun.log` | +8/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/run_d_real_dryrun.log` | +7/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/run_d_v3_withheld_guard.log` | +6/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/tree_risk_scan.log` | +13/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/verify_t1_t13_v3.log` | +18/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/verify_t1_t9.log` | +14/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/LOGS/verify_t1_t9_v2.log` | +14/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/PUBLIC_TREES_AUDIT.md` | +133/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/R2-16C_TEST_RESULTS.md` | +70/-0 |
| A | `poetry-database/reports/tasks/2026-11-21/R2-16/SOURCE_AUDIT.md` | +122/-0 |
| M | `poetry-database/tools/github_sync.py` | +717/-456 |
| A | `poetry-database/tools/make_public_evidence.py` | +65/-0 |
| D | `poetry-database/tools/ocr_vision` | +-/-- |
| A | `poetry-database/tools/public_files.txt` | +906/-0 |
| A | `poetry-database/tools/public_redactions.json` | +36/-0 |

合计：新增 27、修改 9、删除 4、改名 0。
（SYNC_DIFF.md 自身为每轮重新生成，其自身变更不列入本表。）

Manifest 与导出树的双向一致性由 github_sync.py verify_export 在推送前强制校验。
