# EVIDENCE_LEVEL_R2_12 — 证据等级细化

## 1 本轮采用的分级

| 等级 | 定义 | 本轮实例 | 条数 |
|---|---|---|---|
| `PRINTED_EDITION_DIRECT` | 直接查看印本（含影印）页面并逐字比对 | 宋刻本卷一「東/同/中/蟲/終/忡/嵩/戎」反切 | 8 |
| `FACSIMILE_IMAGE_DIRECT` | 查看影印图像但未逐字比对（如仅确认版面、谱行轮廓） | 词谱 600dpi 图、宋刻本叶序确认 | 若干 |
| `DIGITAL_TRANSCRIPTION` | 来自数字转录（维基文库/ctext 转写），未对图 | 广韵 25,619 条、集韵 42,352 字行、新韵 7,597 条 | 绝大多数 |
| `SECONDARY_REFERENCE` | 他人整理/统计（文脉 3,702、商务 3,872） | 仅作对照 | — |
| `OCR_DERIVED` | PaddleOCR 文本（王力二书） | 阅读记录、音标索引 | — |
| `COMPUTED` | 由规则派生（新韵 7,216 条派生、韵部归并） | — | — |
| `INFERRED` | 推断（添/狠定韵、28 条候选首） | — | — |
| `UNKNOWN` | 无来源 | 上古音全部 | 100 查询行 |

## 2 关键规则

1. **不得升级**：`DIGITAL_TRANSCRIPTION` 不得因「与另一转录本一致」升级；只有对图才可升 `FACSIMILE_IMAGE_DIRECT`，逐字比对才可升 `PRINTED_EDITION_DIRECT`。
2. **不得扩散**：某字在影印页出现，不等于同韵其他字自动获得图像证据。
3. **反向也要标**：`jiyun_char_index_r2_12` 全部 42,352 行标 `UNVERIFIED_IMAGE`，明确「未对图」。
4. `SOURCE_PRIMARY` 这个笼统等级**本轮停用**，改用上表具体形态。

## 3 现状统计

- `PRINTED_EDITION_DIRECT`：8 条（广韵卷一 8 个小韵的反切）。
- 集韵：0 条（影印页未定位）。
- 词谱：11 条 `FACSIMILE_IMAGE_DIRECT`（单人判读）＋ 第二人盲读结果另计。
- 音标：0 条（`BLOCKED_MISSING_COORDINATES`）。

## 4 与外部审查意见的对应

外部审查第 R11-09/R11-10/R11-11 条指出「单人判读≠双人核验」「类型级≠逐符号」「RENDERED_NOT_READ≠已核」。本轮据此：

- 词谱 11 条新增第二审查者盲读（`CIPAI_11_DOUBLE_BLIND_REVIEW.csv`），冲突保留为 UNDECIDABLE；
- 20 条控制样本仍标 `NOT_SYMBOL_COLLATED`，不冒充逐符号；
- 音标 50 条改标 `BLOCKED_MISSING_COORDINATES` 并说明技术原因。
