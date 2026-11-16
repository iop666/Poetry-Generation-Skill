# WORKS_TEXT_EVIDENCE_FINAL — 339 条正文候选的最终证据状态

## 1 状态分布

| 状态 | 条数 | 说明 |
|---|---|---|
| `DIGITAL_EDITION_VERIFIED` | **29** | 能定位到源 JSON 数组下标，且 `text_raw` 与 `paragraphs` 逐字一致 |
| `STRUCTURE_SUPPORTED` | 243 | 仅结构重建（括号剥离/异文分离），无源文件逐字核 |
| `HEURISTIC_ONLY` | 53 | 规则失效或括号错乱，待审 |
| `SOURCE_VERIFIED` | **0** | 无一条达到 |
| `FACSIMILE_VERIFIED` | **0** | 无一条达到 |

## 2 为什么只有 29 条

339 条中 310 条的来源属于 `COUNT_MISMATCH`（works 数 ≠ JSON 条数），`seq` 无法与数组下标一一对应；改用「双指针 + 标题匹配」后仍大量未命中，原因推断为**导入时标题被规范化**（去括号/改异体）。本轮未批量改用正文匹配，故只完成 29 条。

## 3 这 29 条证明了什么

- 证明**导入未改字**：29/29 `works.text_raw` 与源 JSON `paragraphs` 去标点后完全相同。
- 不证明**源文正确**：源为 chinese-poetry 二手整理，未对任何印本。

## 4 与 R2-13 的关系

R2-13 的 243 `SUPPORTED_RECONSTRUCTION` 与 43 `TEXT_STRUCTURE_CONFIRMED` **不升级**。本轮新增的 29 条 `DIGITAL_EDITION_VERIFIED` 是独立新增，不改变原状态。

## 5 下游使用建议

- 需要「可信正文」的场景（平仄/韵脚分析）：只用 29 条 `DIGITAL_EDITION_VERIFIED`。
- 一般检索/展示：可用 `text_raw`（未经归一化），不用 `text_norm`。
- 339 条候选仅作修订参考，不得替换正式字段。
