# FILE_MANIFEST —— 交付清单与校验值（R2-07）

> 校验算法：SHA-256 前 16 位。

| # | 路径 | 大小 | SHA-256(16) |
|---:|---|---:|---|
| 1 | `reports/tasks/2026-11-14/R2-07/CIPAI_ENTITY_REPORT.md` | 14.8 KB | `c8ccb9b6d8a328d3` |
| 2 | `reports/tasks/2026-11-14/R2-07/CIPAI_FORM_AUDIT.md` | 31.4 KB | `79ba930b03e1ec0f` |
| 3 | `reports/tasks/2026-11-14/R2-07/CIPAI_RHYME_CLASS_REPORT.md` | 3.2 KB | `5bdd8f0f4e5d1185` |
| 4 | `reports/tasks/2026-11-14/R2-07/COMPLETE_REPORT.md` | 46.5 KB | `402adb5901df1b5d` |
| 5 | `reports/tasks/2026-11-14/R2-07/OCR_VERIFICATION_REPORT.md` | 3.2 KB | `3d81f807f48c5d3b` |
| 6 | `reports/tasks/2026-11-14/R2-07/SOURCE_AUDIT.md` | 2.1 KB | `8d72c1658c9ab3de` |
| 7 | `reports/tasks/2026-11-14/R2-07/SOURCE_DIFFERENCE_REPORT.md` | 5.0 KB | `2a85e272fe9f5827` |
| 8 | `reports/tasks/2026-11-14/R2-07/SPECIAL_CASE_REPORT.md` | 4.8 KB | `532f6ab67950ff06` |
| 9 | `reports/tasks/2026-11-14/R2-07/TEST_RESULTS.md` | 3.6 KB | `c96d61716e1d7921` |
| 10 | `reports/tasks/2026-11-14/R2-07/test_results.json` | 5.2 KB | `8c341ca51a6aa833` |
| 11 | `tools/r2_07_forms.py` | 24.9 KB | `f159bd331e2fd31a` |
| 12 | `tools/r2_07_finalize.py` | 19.2 KB | `6c33f92fd4e752c3` |
| 13 | `tools/r2_07_tests.py` | 9.2 KB | `35e1ba0b27ba3fcf` |
| 14 | `tools/r2_07_reports.py` | 24.3 KB | `5496638077935f9c` |
| 15 | `tools/r2_07_complete.py` | 19.4 KB | `78fa56ce98bf591b` |
| 16 | `raw/r2_07_forms.json` | 623.4 KB | `8bc08ee6bc40262c` |
| 17 | `raw/r2_07_finalize.json` | 4.2 KB | `fb424ea8592d70c3` |
| 18 | `raw/r2_07_external.json` | 24.1 KB | `eeb1624a3b441558` |

合计 **18** 个文件。

## 有意排除

| 项 | 原因 |
|---|---|
| 原书 PDF | 版权，仅本地解析 |
| `raw/books_native/*` | R2-03 已交付，未改动 |
| `database/poetry.db` | 以 `database_delta.sql` 交付 |
| OCR 凭据 | 全包扫描命中 0 |
| 原图裁切件 | 中间产物，在 `<LOCAL_WORKBUDDY>/2026-11-14/.tmp/` |

`FILE_MANIFEST.md` 不列入表内（自指问题）。
