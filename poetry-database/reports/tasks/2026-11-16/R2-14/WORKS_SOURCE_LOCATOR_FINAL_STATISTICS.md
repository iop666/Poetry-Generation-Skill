# WORKS_SOURCE_LOCATOR_FINAL_STATISTICS — 来源定位最终统计

## 1 分层覆盖

| 定位类型 | 含义 | 条数 | 占比 |
|---|---|---|---|
| `TEXT_OFFSET_LOCATOR` | 文件 + 数组下标 | **164,217** | **43.7%** |
| `FILE_LOCATOR` | 有 source_id 与本地文件，但无法确定数组位置（COUNT_MISMATCH） | 211,182 | 56.3% |
| `BIBLIOGRAPHIC_LOCATOR` | 只有总集名 | 0（已含在上行） | — |
| `PAGE_LOCATOR` | 页码/叶码 | **0** | 0% |
| `NO_LOCATOR` | 无任何来源 | **0** | 0% |

## 2 怎么算的

- `sources` 941 条，`local_path` 100% 有值；在用 819 个，文件 0 缺失。
- 855 个文件可用（JSON），83 个非 JSON，3 个抓取失败。
- 818 个在用来源逐个验证：604 个 `COUNT_MATCH`（works 数 = JSON 条数），其中 **551 个**「按 seq 排序后 30 条抽样标题命中 ≥25」。
- 551 个来源覆盖 **164,217 条**。
- 30 条逐字对校：`works.text_raw` vs 源 JSON `paragraphs`，去标点后汉字序列 **30/30 EXACT**。

## 3 与 R2-13 的差异

R2-13 报「`record_locator` 0/1,000 → 无来源」。本轮更正为：

- 「无页码定位」成立（`PAGE_LOCATOR` = 0）；
- 「无来源」**不成立**（`FILE_LOCATOR` = 100%，`TEXT_OFFSET_LOCATOR` = 43.7%）。

## 4 剩余 56.3% 为什么不能下标定位

`COUNT_MISMATCH` 的 214 个来源：导入时过滤（如元曲 `len<8`）、合并或重复导致 works 数少于 JSON 条数，`seq` 排序后无法与数组一一对应。可用「双指针 + 正文前 20 字」逐文件恢复，本轮只对 339 条中的 29 条成功（其余标题在导入时被规范化，匹配失败），未批量做。

## 5 诚实边界

- 43.7% 是「**可定位**」，不是「**已校勘**」。
- 30 条 EXACT 只证明「导入未改字」，不证明「源文无误」。
- chinese-poetry 本身为二手整理，`reliability` 自述「未与任何印本对勘」。
