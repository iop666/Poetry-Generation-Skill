# WORKS_TEXT_BODY_RECONSTRUCTION — 作品正文本与校记分离

## 0 前提更正（本轮实测推翻三项旧表述）

| 旧表述 | 实测 | 影响 |
|---|---|---|
| 「`text_norm` 混入校记 339 条」 | 339 是 `text_raw` 中含「一作」的条数；`text_norm` 中仍残留「一作」二字的只有 **15 条**，且这 15 条全是诗句正文（如陸游「一作劍關客」），norm 是对的 | 「污染」不等于「残留一作」 |
| 「王孫歸不歸明年」因「一作」残留 | 真正成因：归一化删掉了「（明年 一作：年年）」中的「一作：年年」却把注头「明年」留在句尾 → **norm 变长** | 116 条属此向 |
| 「校记混入正文」是主要方向 | **反向才是主要方向**：184 条 norm 把正文当校记删了 | 见 §1 |

反向删除的实例（真实数据）：

- 王安石「相看一作秦吳別」→ norm 作「相看別」
- 任希夷「狂風一作浪如屋」→ norm 作「狂風屋」
- 143 条「X（一作「Y」）」把 X 一并删掉，只留 Y

**`char_count` 因此是「一致地错」**：全库 `count(*) WHERE char_count <> length(text_norm)` = **0**，即 char_count 忠实记录了被毁后的 norm。將進酒 char_count=196 / norm 196 / 真实正文 176。

## 1 339 条的构成（逐条判定）

| 分类 | 条数 | 含义 | 处理 |
|---|---|---|---|
| `EDITORIAL_NOTE` | 143 | 编者校记（「一作某」「某本作某」）串入正文 | 可剥离 |
| `MIXED_BODY_AND_NOTE` | 141 | 正文与校记黏连／注头残留 | 需按句切分后剥离 |
| `POEM_BODY` | 42 | 「一作」本在原文（自注、诗题小序、词牌题注） | **不得删除** |
| `VARIANT_NOTE` | 13 | 异文校记独立成段 | 可剥离至独立字段 |

置信度：HIGH 134 / MEDIUM 205 / LOW 0。

## 2 重建建议的结构

```
text_original   原文（= 现 text_raw，不动）
text_body       去校记后的正文（建议新增字段）
text_preface    题注/小序
text_annotation 作者自注
text_variants   异文校记（「一作某」列表）
text_source     来源定位
text_cleaning_status  CLEANED / PARTIAL / KEPT_AS_IS / UNRESOLVED
```

`text_norm` **保留原字段不动**，新增字段并存，便于回滚与比对。

## 2.1 污染方向核账

| 方向 | 条数 |
|---|---|
| norm 偏长（注头残留） | 116 |
| norm 等长但内容不同 | 15 |
| **norm 偏短（正文被删）** | **184** |
| 无损失 | 24 |

184 条偏短是本轮最严重的发现：被删的是诗句里的字，不是标点，导致下游任何以 norm 为输入的断句、韵脚、字数统计全部偏移。

## 3 已生成的修订表

`WORKS_TEXT_REVISIONS_R2_12.csv`：328 条（339 条中 11 条因边界无法确定未出建议），字段含
`work_id, old_text_norm（完整原值）, suggested_text_body, removed_segments, source_text, change_reason, confidence, applied`。

**applied 全部为 NO**——本轮不做任何写入，符合「修改必须追加式修订、不得覆盖历史表」。

置信度分布：HIGH 206 / MEDIUM 53 / LOW 69。LOW 者多为校记边界落在句读之外、无法确定归属。

## 4 典型样例（真实数据）

| work_id | 现象 | 判定 |
|---|---|---|
| 见 CSV 中 `MIXED_BODY_AND_NOTE` 行 | 正文末句与「一作：X」黏连，导致 `char_count` 虚高（如 196 vs 实 176） | 剥离，HIGH |
| 见 `POEM_BODY` 行 | 诗题小序「时年十七」被括号包裹，被误判为校记 | **保留**，KEPT_AS_IS |

## 5 未做

- 未对全库 375,399 条做同型扫描（只做了 `LIKE '%一作%'` 的 339 条 + 560 条分层抽样）。
- 未估算全库污染率（560 条抽样只能给类型分布，不能外推）。

## 6 建议

1. 先清洗 `text_norm`（它是下游匹配与韵律分析的输入），再谈全库质量。
2. 42 条 `POEM_BODY` 需人工确认后从「污染」名单剔除。
3. 校记应独立成表（`work_text_variants`），而不是从正文里删掉——删除会丢失版本信息。
