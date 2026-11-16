# FILE_MANIFEST —— 交付清单与校验值（R2-06）

> 校验算法：SHA-256 前 16 位。

| # | 路径 | 大小 | SHA-256(16) | 说明 |
|---:|---|---:|---|---|
| 1 | `reports/tasks/2026-11-13/R2-06/BOOK_READING_REPORT.md` | 4.0 KB | `209868ac51bca7cc` | 阅读成果（本轮+累计） |
| 2 | `reports/tasks/2026-11-13/R2-06/CHAPTER_COVERAGE_REPORT.md` | 3.7 KB | `2a55100b4d08b605` | 覆盖、门禁、页码映射 |
| 3 | `reports/tasks/2026-11-13/R2-06/CIPAI_CATALOG_REPORT.md` | 4.2 KB | `b2eee1735be11eff` | 词牌目录盘点 |
| 4 | `reports/tasks/2026-11-13/R2-06/COMPLETE_REPORT.md` | 21.9 KB | `de87e0cffb74f6eb` | 十三章完整报告 |
| 5 | `reports/tasks/2026-11-13/R2-06/LOGS/2026-11-13_R2-06执行日志.txt` | 4.1 KB | `922df719e14d1b44` | 执行日志 |
| 6 | `reports/tasks/2026-11-13/R2-06/LOGS/2026-11-13_R2-06测试记录.json` | 8.7 KB | `e0087789948631ff` | 执行日志 |
| 7 | `reports/tasks/2026-11-13/R2-06/OCR_CORRECTION_REPORT.md` | 4.6 KB | `68c91644bfb7ee4b` | OCR 清洗与修订 |
| 8 | `reports/tasks/2026-11-13/R2-06/SOURCE_AUDIT.md` | 4.7 KB | `2631ed22fb9516e1` | 来源与版本审计 |
| 9 | `reports/tasks/2026-11-13/R2-06/TEST_RESULTS.md` | 5.5 KB | `2c28c55005f20960` | 50 项测试逐条记录 |
| 10 | `reports/tasks/2026-11-13/R2-06/THEORY_CONFLICT_REPORT.md` | 5.6 KB | `8fd98d91a09a14f2` | 潜在冲突与勘误 |
| 11 | `reports/tasks/2026-11-13/R2-06/THEORY_EXTRACTION_REPORT.md` | 7.5 KB | `955579c301280301` | 39 条新理论条目 |
| 12 | `raw/r2_06_notes/C_诗词格律十讲.md` | 28.0 KB | `f63894c4db3099c4` | 阅读笔记 |
| 13 | `raw/r2_06_notes/D_附录与索引.md` | 7.1 KB | `495be20358cd015d` | 阅读笔记 |
| 14 | `raw/r2_06_notes/E_词学十讲十讲复核.md` | 9.5 KB | `84199814d2fd012c` | 阅读笔记 |
| 15 | `tools/r2_06_index.py` | 10.2 KB | `484df4da4ad28d45` | C/D 索引+逐页映射 |
| 16 | `tools/r2_06_cipai_catalog.py` | 11.8 KB | `6675491e12e05504` | 词牌目录盘点 |
| 17 | `tools/r2_06_ingest.py` | 25.3 KB | `7e71c78fc12107ba` | 成果入库 |
| 18 | `tools/r2_06_reports.py` | 18.7 KB | `fd7d0d2252ee164c` | 数据驱动报告 |
| 19 | `tools/r2_06_verify.py` | 10.5 KB | `838ebad0bc03c224` | 全量测试 |
| 20 | `tools/r2_05_dump.py` | 6.2 KB | `65386df1e8fe74ee` | 分页清洗阅读 |

合计 **20** 个文件。

## 有意排除

| 项 | 原因 |
|---|---|
| 原书 PDF/EPUB | 仅本地解析，不分发（版权） |
| `raw/books_ocr_paddle/*/pages.jsonl` | R2-03-R1 已交付，本轮未改动 |
| `raw/books_native/*` | 同上，仅读取 |
| 数据库 `.db` 本体 | 体积大；以增量 SQL 交付 |
| OCR 凭据 | 任何交付物不得含 |
| 格式谱裁切图、页码条带图 | 中间产物，留在 `<LOCAL_WORKBUDDY>/2026-11-13/.tmp/` |
