# EXAMPLE_LINK_STATUS_RECONCILIATION — 例词关联状态重估

## 1 本轮复核规模

- 输入：`EXAMPLE_310_FINAL_STATUS.csv`（310 条全量状态）＋ R2-11 已复核 88 条 ＋ R2-10 已复核 20 条。
- 本轮新增 100 条，与上述 108 条**零交集**（脚本内用 example_id 断言）。
- 复核方法：先检索后判定。取例词首句 8–10 字，在 `works.text_raw` 与 `text_norm` 双路 LIKE，命中后做去标点的最长公共子串比例。

## 2 结果

| 新状态 | 条数 |
|---|---|
| `VERIFIED_VARIANT` | 36 |
| `SEARCHED_NO_RESULT` | 39 |
| `POSSIBLE_MATCH` | 16 |
| `VERIFIED_EXACT` | 9 |
| 合计 | 100 |

判定动作：`UPGRADED` 54、`CONFIRMED_NO_MATCH` 39、`CONFIRMED` 7。

## 3 最重要的一条

**原状态为 `NO_MATCH` 的 90 条中，有 51 条在重新检索后找到了作品**（升级为 VERIFIED_* 或 POSSIBLE_MATCH）。

这说明 R2-10/R2-11 的 `NO_MATCH` 里，绝大部分是「没搜过」（`work_len=0`），不是「搜过没有」。这与 `DISPUTE_RESOLUTION_18_R2_12.md` 中 8 条争议 6 条一搜即得互相印证。

## 4 状态口径（今后必须区分）

| 状态 | 含义 | 禁止 |
|---|---|---|
| `NOT_SEARCHED` | 未执行检索 | 不得计为「无匹配」 |
| `SEARCHED_NO_RESULT` | 已双路检索且 `work_len=0` | — |
| `POSSIBLE_MATCH` | 相似但未达门槛（异文清单不全／作者不符／非同词牌） | 不得因相似度高直接升级 |
| `TITLE_ONLY` | 仅标题同，正文不匹配 | — |
| `AUTHOR_CONFLICT` | 正文匹配但作者不符 | 不得强行归给例词标注的作者 |
| `VERIFIED_EXACT` | 去标点后逐字相同 | — |
| `VERIFIED_VARIANT` | 有明确异文清单且作者一致且同词牌 | — |

升级三条件（缺一不可）：① 逐处异文清单 ② 作者规范化后一致 ③ 同词牌。

## 5 累计独立复核

| 轮次 | 条数 | 性质 |
|---|---|---|
| R2-10 | 20 | 独立会话复核（原报告误称 100） |
| R2-11 | 88 | 主 Agent 脚本 + 抽样 |
| R2-12 | 100 | 另一会话执行者，先检索后判定 |
| **累计（去重）** | **208** | — |

## 6 未做

- 剩余约 100 条（310 − 108 − 100 中的未覆盖部分）未复核。
- `AUTHOR_CONFLICT` 未逐条判定「应归谁」，只标冲突。
- 未核例词文本本身的版本（例词可能取自词谱转引，与作家本集有异文）。
