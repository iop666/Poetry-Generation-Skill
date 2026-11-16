# FILE_MANIFEST —— 交付文件清单与校验值（R2-05）

> 校验算法：SHA-256 前 16 位。

| # | 路径 | 大小 | SHA-256(16) | 说明 |
|---:|---|---:|---|---|
| 1 | `reports/tasks/2026-11-13/R2-05/BOOK_READING_REPORT.md` | 8.0 KB | `494c2f3378c4fdce` | 阅读总报告 |
| 2 | `reports/tasks/2026-11-13/R2-05/CHAPTER_COVERAGE_REPORT.md` | 6.8 KB | `6b8d685a537ef6b5` | 覆盖与门禁 |
| 3 | `reports/tasks/2026-11-13/R2-05/COMPLETE_REPORT.md` | 23.3 KB | `1bb271224c41d265` | 十三章完整报告 |
| 4 | `reports/tasks/2026-11-13/R2-05/LOGS/2026-11-13_R2-05自检日志.txt` | 2.0 KB | `e895015014ee2785` | 执行日志 |
| 5 | `reports/tasks/2026-11-13/R2-05/OCR_EXCEPTION_REPORT.md` | 5.7 KB | `e8ca72859fa2810b` | OCR 异常与核验 |
| 6 | `reports/tasks/2026-11-13/R2-05/SOURCE_AUDIT.md` | 6.3 KB | `96edd32042e375de` | 来源与版本审计 |
| 7 | `reports/tasks/2026-11-13/R2-05/TEST_RESULTS.md` | 9.1 KB | `8607c251b32f98d8` | 30 项自检记录 |
| 8 | `reports/tasks/2026-11-13/R2-05/THEORY_CLAIMS_AUDIT.md` | 4.1 KB | `c520a7696d6617d3` | 旧 16 条处理 |
| 9 | `reports/tasks/2026-11-13/R2-05/THEORY_EXTRACTION_REPORT.md` | 25.5 KB | `0c714554de2c5a97` | 38 条理论条目 |
| 10 | `raw/r2_05_notes/A_00_引言.md` | 2.6 KB | `63796951c47d2a36` | 阅读笔记 |
| 11 | `raw/r2_05_notes/A_01_第一章.md` | 8.0 KB | `a49f2e75ae78cc30` | 阅读笔记 |
| 12 | `raw/r2_05_notes/A_02_第二章.md` | 28.0 KB | `4b14bd11fda3fc68` | 阅读笔记 |
| 13 | `raw/r2_05_notes/A_03_第三章.md` | 13.3 KB | `1018fff738b9333b` | 阅读笔记 |
| 14 | `raw/r2_05_notes/A_04_第四章.md` | 8.8 KB | `b1af0ac08b57db0a` | 阅读笔记 |
| 15 | `raw/r2_05_notes/A_05_附录一.md` | 16.4 KB | `7c8c1b6c7f890e0e` | 阅读笔记 |
| 16 | `raw/r2_05_notes/A_06_附录二三.md` | 7.5 KB | `040696285f755be4` | 阅读笔记 |
| 17 | `raw/r2_05_notes/B_01_卷上.md` | 19.6 KB | `3c9fa822e44afb31` | 阅读笔记 |
| 18 | `raw/r2_05_notes/B_02_卷下.md` | 16.6 KB | `ccedad9f5865cd9f` | 阅读笔记 |
| 19 | `raw/r2_05_notes/E_词学十讲状态复核.md` | 17.0 KB | `13755ba86de13a6d` | 阅读笔记 |
| 20 | `tools/r2_05_dump.py` | 5.2 KB | `d04dc58320d37b43` | 分页清洗阅读工具 |
| 21 | `tools/r2_05_ingest.py` | 43.9 KB | `797f70b6b6168d54` | 成果入库 |
| 22 | `tools/r2_05_reports.py` | 22.9 KB | `cdbcb80d6bfd9f1b` | 报告生成 |
| 23 | `tools/r2_05_tests.py` | 11.1 KB | `18c9aaa9bce4b34b` | 自检脚本 |
| 24 | `tools/r2_05_fix_quotes.py` | 3.1 KB | `88c686e31eb6ccbf` | 引文逐字回填 |

合计 **24** 个文件。

## 有意排除

| 项 | 原因 |
|---|---|
| 原书 PDF/EPUB | 仅本地解析，不分发 |
| `raw/books_ocr_paddle/*/pages.jsonl` | R2-03-R1 已交付，未改动 |
| 数据库本体 | 以增量 SQL 交付 |
| OCR 凭据 | 任何交付物不得含 |
| 格式谱裁切图 | 中间产物，在 `<LOCAL_WORKBUDDY>/2026-11-13/.tmp/` |
