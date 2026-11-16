# TEXT_NORMALIZATION_SPEC_FINAL — 文本字段规范（终稿）

## 1 七字段与证据等级

| 字段 | 内容 | 证据来源 | 可用于韵律分析 |
|---|---|---|---|
| `source_original` | 源文件原文（JSON `paragraphs`/`content`） | 本地 raw/poetry 文件 + SHA-256 | **是（最高）** |
| `text_transcribed` | 忠实转录（仅统一编码/换行） | 由 source_original 派生 | 是 |
| `text_body` | 结构化正文 | **程序拆分**（非人工整理） | 仅在状态≥`STRUCTURE_SUPPORTED` 时 |
| `text_preface` | 小序/题注 | 程序拆分 | 作背景 |
| `text_annotation` | 作者自注/编者按语 | 程序拆分 | 否 |
| `text_variant` | 异文（一作/一本作/一云） | 程序拆分 | 否 |
| `text_search_normalized` | 检索串 | 由 body 派生 | **否（仅检索）** |

## 2 关键约束（本轮新增）

1. **`body` 这个名字不代表它是原诗。** 只有达到 `SOURCE_TEXT_SUPPORTED` 及以上，才可作为平仄/韵脚分析的输入。
2. **格律不得裁决正文。** 句长/平仄只能标记「疑点」，不能删除或替换原文。本轮 53 条待审中 33 条因此标 `UNRESOLVED`。
3. **异体字不是异文。** `濛/蒙`、脱「軿」等属 `CHARACTER_VARIANT`，不改变 `VERIFIED_EXACT` 状态，只附注。
4. **不合并多版本。** 同一作品的不同版本各自保留 `body`，用 `variant_group` 关联。

## 3 证据等级

| 等级 | 判据 | 本轮条数 |
|---|---|---|
| `SOURCE_VERIFIED` | 源文件逐字核对 + 版本信息 | **0** |
| `FACSIMILE_VERIFIED` | 影印页核对 | 0 |
| `DIGITAL_EDITION_VERIFIED` | 与数字版原文逐字一致 | **29**（339 条中） |
| `SOURCE_TEXT_SUPPORTED` | 有源文件定位但未逐字核 | 0 |
| `STRUCTURE_SUPPORTED` | 仅结构解析 | 243（R2-13） |
| `HEURISTIC_ONLY` | 仅启发式（句长规则） | 53（待审） |
| `UNRESOLVED` | 无法判定 | 33 |

## 4 金样本

`TEXT_NORMALIZATION_GOLDEN_80.csv`：80 条（R2-13 的 55 + 本轮 25 条反例：无括号「一作」13、长篇 6、含编者标记 6）。反例的用途是**检验规则会不会误删正文**，不是用来证明规则正确。

## 5 未解决

- 「一作」在句首且删后仍合律时（如「一作芸香吏」），规则失效 → `UNRESOLVED`。
- 词牌说明与正文同行的情形未处理。
- 53 条待审需回原书，本轮无法定案。
