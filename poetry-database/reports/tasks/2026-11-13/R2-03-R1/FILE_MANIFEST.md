# FILE_MANIFEST —— R2-03-R1 交付清单

> 交付包**不含 `books/` 六本原书全文**，只含解析产物、脚本、报告与数据库增量。
> 原始 PDF/EPUB 一律只读保留在项目目录，未复制、未上传至交付包。

## 一、报告（`reports/tasks/2026-11-13/R2-03-R1/`）

| 文件 | 大小 | 内容 |
|---|---:|---|
| `COMPLETE_REPORT.md` | 13.1 KB | 十三章完整报告 + 最终结论 |
| `ERRATA.md` | 7.5 KB | 对 R2-03 四项错误结论及本轮一项误判的更正 |
| `OCR_QUALITY_REPORT.md` | 5.7 KB | 引擎、任务返回、数据完整性、符号质量 |
| `SOURCE_AUDIT.md` | 4.4 KB | 来源、上传合规、凭据、质量等级、缺口 |
| `TEST_RESULTS.md` | 3.9 KB | 30 项实际验证 + 失败/误判记录 |
| `FILE_MANIFEST.md` | 本文件 | 交付清单 |
| `LOGS/2026-11-13_PaddleOCR重跑执行日志.txt` | 8.5 KB | 三个任务的提交、排队、解析、下载、对照、入库原始日志 |

## 二、解析数据（`raw/books_ocr_paddle/`）

| 文件 | 大小 | 说明 |
|---|---:|---|
| `wangli_shicilv/pages.jsonl` | 628 KB | 432 页，逐页 `engine=PaddleOCR-VL-1.6` |
| `wangli_yinyunxue/pages.jsonl` | 1,258 KB | 476 页 |
| `wangli_tongyuan/pages.jsonl` | 2,753 KB | 783 页 |
| `*/meta.json` ×3 | 0.8 KB each | jobId、页数、空页、model、完成时间 |
| `*/api_result.jsonl` ×3 | 3.9 / 5.1 / 9.6 MB | API 原始返回（含分片结构），供复核 |
| `*/result.md` ×3 | 0.5 / 1.1 / 2.5 MB | 合并 Markdown |
| `comparison.jsonl` | 692 KB | 1,691 页对照指标（**逐页结论作废**） |
| `COMPARISON_SUMMARY.json` | 2 KB | 已标记 `INVALID_FOR_PAGE_LEVEL_CONCLUSIONS` |
| `alignment.json` | 4.9 KB | 已标记 `INVALID`，仅作过程记录 |
| `runs.json` | 0.5 KB | 云端产物到项目内的落地映射 |

## 三、工具脚本（`tools/`）

| 文件 | 状态 | 用途 |
|---|---|---|
| `paddle_rerun.py` | 新增 | `plan/run/compare/ingest/all`；缺 token 报错不换引擎 |
| `paddle_align.py` | 新增（探索） | 按内容对齐页号；基于错误前提，产物已作废 |
| `finalize_r2_03_r1.py` | 新增 | 作废旧基线、登记质量发现 |

## 四、数据库增量（`database/poetry.db`）

| 对象 | 变化 |
|---|---|
| `book_pages_paddle` | 新表，1,691 行 |
| `ocr_comparison` | 新表，1,691 行 + `baseline_valid` 列（全 0） |
| `ocr_quality_findings` | 新表，7 条 |
| `ocr_runs` | 新增 3 条 PaddleOCR 运行记录（幂等，无重复） |
| `book_pages` | **未改动**（2,010 行，原样保留） |
| `book_items` / `theory_claims` / `cipai_specs` | **未改动** |

## 五、被修改的既有文件

| 文件 | 改动 |
|---|---|
| `AGENTS.md` | 阶段状态更新；登记 PaddleOCR 误判更正与 Vision 数据缺陷 |
| `reports/tasks/2026-11-13/R2-03/COMPLETE_REPORT.md` | 顶部加正式勘误告示（含虚高口径作废） |
| `reports/tasks/2026-11-13/R2-03/OCR_QUALITY_REPORT.md` | 顶部加正式勘误告示（按页统计整体作废） |

## 六、明确未包含

- `books/` 六本原书（版权与体积原因，只读保留在项目目录）。
- AI Studio token 或任何凭据文件（仅存于本机 `~/.workbuddy/.credentials/`，0600）。
- `诗词格律引擎/` 任何文件（冻结，本轮未动）。
