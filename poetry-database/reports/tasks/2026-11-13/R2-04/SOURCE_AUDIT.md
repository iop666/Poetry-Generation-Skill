# SOURCE_AUDIT —— R2-04 来源与核验状态

## 一、本轮使用的来源（全部本地，未新增抓取）

| 来源 | 路径 | 形态 | 核验状态 |
|---|---|---|---|
| 王力合集（四部分合订本） | `raw/books_ocr_paddle/wangli_shicilv/pages.jsonl` | PaddleOCR-VL-1.6 逐页文本，432 页 | `PARSED` + `SOURCE_TRACEABLE`；jobId `114676397850828800`；页序经 p35/p100/p200 原图核验 |
| 同上，API 原始返回 | `raw/books_ocr_paddle/wangli_shicilv/api_result.jsonl` | 144 分片 × 3 页 | 保留供复核 |
| 《唐宋词格律》 | `raw/books_native/long_yushsheng_cilv/pages.jsonl` | PDF **文字层**，270 页 | `PARSED`；符号未经 OCR |
| 《词学十讲》 | `database/poetry.db :: book_chapters` | EPUB 章节，33 章 | `PARSED`；本轮补读第 6/7/9/10 讲 |
| 作品语料 | `database/poetry.db :: works` | 375,399 条 | 仅用于词牌字数统计；按审核要求 `cipai` 视为**候选分类** |
| 原书 PDF | `books/`（只读） | 6 个实体文件 | SHA-256 见 R2-03 `BOOK_INVENTORY.md` |

**未使用网络抓取**；现代版权著作（王力、龙榆生）全文未复制进交付包，只含解析产物与引用片段。

## 二、版本与页码口径

- 合订本总目录（PDF p8）：《诗词格律》1／《诗词格律概要》175／《诗词格律十讲》339／附录 399／索引 407。
- **印刷页码 = PDF 物理页(0基) − 8**，已用 p35（印刷27）、p100（92）、p200（192）三页原图核验。
- 《唐宋词格律》印刷页码取页首版心数字（如 p16 首行「1」），可靠性中等；凡无法读取者标 NULL。
- 版次：合订本版权页「中华书局，2014.3，王力全集」，ISBN 978-7-101-09356-8（R2-03 版权页原文）。
  **本轮未做版本学对勘**，`EDITION_VERIFIED = 0`。

## 三、质量等级（v2.0 词表）

| 对象 | 等级 | 理由 |
|---|---|---|
| 17 个章节笔记 | `EXTRACTED`（阅读进度词表） | 证据段精读＋12 项结构化笔记，**非逐字通读**，不标 READ |
| 135 定格＋9 变格索引 | `PARSED` + `SOURCE_TRACEABLE` | 来自 PDF 文字层，可定位到页；**未逐调版本核对**，仍是候选数据 |
| 16 条理论复核 | 部分 `TEXT_CROSSCHECKED` | 引文与 PaddleOCR/文字层/EPUB 三处原文比对，1 条判为出处错误 |
| 词牌字数调查 | 统计结论 | 基于二手语料，不作为版本或归属证据 |
| 全部 OCR 文本 | `PARSED` | 未与影印本逐字对勘 |

## 四、合规边界

- 未修改 `books/` 原书；未改 `gedou.py`／词牌引擎；未进 Phase 3；未封装 Skill；未做模型微调；未做文学质量评分。
- 未把任何未审核结论升级为 `VERIFIED`；原 `theory_claims`、`cipai_specs`、`book_pages` 三表**均未修改**，
  本轮结论另存 `theory_claims_audit` / `cipai_index` / `reading_notes_r2_04` 等新表。
- 作废数据不删除，只加标记（R2-03-R1 的 `baseline_valid=0`、INVALID 标记）。

## 五、仍缺的来源

| 缺口 | 状态 |
|---|---|
| 《诗经韵读》《楚辞韵读》PDF | 用户第七节要求补入 `books/`；**本轮仍未取得**（目录里只有 341 B `.textClipping`）。不因此暂停 R2-04 |
| 《集韻》正文 216 子页 | 未补 |
| 辽代作品（0 条） | 未补 |
| `author_entities` 表 | 未建（R2-03 审核意见 C 仍 OPEN） |
| 影印本／他本对勘 | 0 |
