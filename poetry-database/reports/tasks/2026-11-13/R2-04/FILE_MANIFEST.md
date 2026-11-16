# FILE_MANIFEST —— R2-04 交付清单

> 交付包**不含 `books/` 六本原书全文**（现代版权著作，只读保留在项目目录），
> 只含解析产物、脚本、报告与数据库增量。不含任何 token／凭据。

## 一、九份报告（`reports/tasks/2026-11-13/R2-04/`）

| 文件 | 大小 | 内容 |
|---|---:|---|
| `COMPLETE_REPORT.md` | 14.8 KB | 十三章权威完整报告 |
| `BOOK_READING_REPORT.md` | 34.1 KB | 逐章 12 项要素笔记、原有/新增进度、未读内容 |
| `POETRY_RULES_EXTRACTION.md` | 5.0 KB | 诗律词律论述提取，四个需限制结论 |
| `CIPAI_EXTRACTION_REPORT.md` | 38.0 KB | 144 条定格/变格全清单、21 调调查 |
| `OCR_QUALITY_REPORT.md` | 5.0 KB | API 服务核查、分层抽查、失败模式 |
| `THEORY_CLAIMS_AUDIT.md` | 11.7 KB | 16 条理论逐条复核 |
| `FILE_MANIFEST.md` | 本文件 | 交付清单 |
| `TEST_RESULTS.md` | 3.9 KB | 26 项验证（含 4 次返工） |
| `SOURCE_AUDIT.md` | 3.3 KB | 来源、版本、质量等级、缺口 |
| `LOGS/2026-11-13_R2-04执行日志.txt` | 86 行 | 四个脚本的完整输出 |

## 二、证据与数据（`raw/r2_04_evidence/`、`raw/`）

| 路径 | 数量 | 说明 |
|---|---:|---|
| `r2_04_evidence/chapters/*.md` | 17 | 章节证据包（与 `manifest.json` 一致；过时中间版本已清理） |
| `r2_04_evidence/full/*.md` | 17 | 完整可解析章节文本，供逐字复核 |
| `r2_04_evidence/manifest.json` | 1 | 章节、印刷页、PDF 页、证据/全文字数覆盖率 |
| `r2_04_evidence/theory_locate.json` | 1 | 16 条引文定位结果 |
| `r2_04_evidence/ocr_samples.json` | 1 | 32 页分层抽查清单 |
| `raw/r2_04_cipai_index.json` | 1 | 144 条定格/变格完整索引 |

## 三、工具脚本（`tools/`）

| 文件 | 大小 | 用途 |
|---|---:|---|
| `r2_04_index.py` | 13.5 KB | 合订本四部分三级章节索引、定格索引、词学十讲讲次 |
| `r2_04_reading.py` | 8.5 KB | 证据包／完整文本／引文定位／抽查样本 |
| `r2_04_ingest.py` | 31.8 KB | 阅读笔记、理论复核、字数调查、阅读状态入库 |
| `r2_04_reports.py` | 17.0 KB | 生成四份数据报告、登记 OCR 发现 |

## 四、数据库增量（`database_delta.sql`）

| 表 | 行数 | 状态 |
|---|---:|---|
| `reading_units` | 93 | `EXTRACTED` 19 / `PARSED` 84；**无 READ** |
| `reading_notes_r2_04` | 21 | 17 章＋4 讲 |
| `cipai_index` | 144 | 135 定格＋9 变格 |
| `theory_claims_audit` | 16 | 15 VERIFIED / 1 MISATTRIBUTED |
| `cipai_wordcount_audit` | 21 | 短篇统计与抽样 |
| `ocr_quality_findings` | 10 | 含本轮 3 条新增 |

**未修改**：`theory_claims`(16)、`cipai_specs`(76)、`book_pages`(2,010)、
`book_pages_paddle`(1,691)、`works`(375,399)、`诗词格律引擎/`、`gedou.py`。

## 五、原图核验材料（`.tmp`，不在交付包）

`<LOCAL_WORKBUDDY>/2026-11-13/.tmp/2026-11-13_临时_R2-04抽查_*.png`（2 张，110 dpi）、
`2026-11-13_临时_页序核验_p*.png`（R2-03-R1 的 3 张）。按文件归置规则留在 `.tmp`，不删除。

## 六、明确未包含

- 六本原书 PDF/EPUB 全文；AI Studio token 或任何凭据文件；
- `books/` 里缺失的《诗经韵读》《楚辞韵读》（约 5.8 MB，用户第七节要求补入，本轮仍未取得）；
- 旧 R2-03 / R2-03-R1 交付包（另见各自 ZIP）。
