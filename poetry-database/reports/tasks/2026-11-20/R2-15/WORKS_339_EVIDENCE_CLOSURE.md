# 339 条正文证据统计闭合（R2-15C1）

- 日期：2026-11-20
- 结论：**旧表 325 条不闭合，已定位为「重 9 + 漏 23」；逐行映射重建后 339 条全部有归属。**

---

## 1 旧表为什么不闭合

`WORKS_TEXT_EVIDENCE_FINAL.md` 给出 `29 + 243 + 53 = 325`，比 339 少 14 条。原因有两个，方向相反：

| 原因 | 数量 | 说明 |
|---|---|---|
| **重复计入** | +9 | 29 条 `DIGITAL_EDITION_VERIFIED` 中有 9 条原本属于 `SUPPORTED_RECONSTRUCTION`；旧表在统计 `STRUCTURE_SUPPORTED` 时仍按 243 全量计，没有扣掉这 9 条 |
| **整档漏计** | −23 | 43 条 `TEXT_STRUCTURE_CONFIRMED` 中，20 条有源文本（已进 DIGITAL），另外 23 条来源下标未定，旧表没有为它们设档 |

算式：

```
339 − 23（漏计）+ 9（重复）= 325     ← 与旧表完全吻合
```

这解释不是推测：逐行重算后，六个交叉格子的数量和恰好对上（见 §2）。

---

## 2 重算后的完整交叉表

| rebuild_status | source_state | evidence_status | 条数 |
|---|---|---|---|
| `SUPPORTED_RECONSTRUCTION` | `SOURCE_TEXT_AVAILABLE` | `DIGITAL_EDITION_VERIFIED` | 9 |
| `SUPPORTED_RECONSTRUCTION` | `SOURCE_FILE_KNOWN_INDEX_UNRESOLVED` | `STRUCTURE_SUPPORTED` | 181 |
| `SUPPORTED_RECONSTRUCTION` | `SOURCE_INDEX_UNAVAILABLE` | `STRUCTURE_SUPPORTED` | 53 |
| `TEXT_STRUCTURE_CONFIRMED` | `SOURCE_TEXT_AVAILABLE` | `DIGITAL_EDITION_VERIFIED` | 20 |
| `TEXT_STRUCTURE_CONFIRMED` | `SOURCE_FILE_KNOWN_INDEX_UNRESOLVED` | `STRUCTURE_CONFIRMED_NO_SOURCE` | 23 |
| `NEEDS_REVIEW` | `SOURCE_FILE_KNOWN_INDEX_UNRESOLVED` | `HEURISTIC_ONLY` | 53 |
| **合计** | | | **339** |

按证据档汇总：

| evidence_status | 条数 | 含义 |
|---|---|---|
| `DIGITAL_EDITION_VERIFIED` | **29** | 9 + 20，来源下标已定且逐字对校 `EXACT` |
| `STRUCTURE_SUPPORTED` | **234** | 243 − 9，仅结构重建，无源逐字核 |
| `STRUCTURE_CONFIRMED_NO_SOURCE` | **23** | 结构已确认，但来源下标未定，**不得算作来源验证** |
| `HEURISTIC_ONLY` | **53** | 规则/括号失效，待审 |
| **合计** | **339** | |

---

## 3 43 条 `TEXT_STRUCTURE_CONFIRMED` 的证据边界

这 43 条容易被误读成"已确认"，实际要分开：

| 子类 | 条数 | 证据到哪一步 |
|---|---|---|
| 来源下标已定 + 逐字一致 | 20 | 可称 `DIGITAL_EDITION_VERIFIED`（但仍只证明"导入未改字"，不证明源文正确） |
| 结构自洽但来源未定 | 23 | 只能到 `STRUCTURE_CONFIRMED_NO_SOURCE`，**不能**写成来源验证 |

因此：「43 条结构确认」≠「43 条来源验证」；真正达到来源级的是 20 条，加上 `SUPPORTED` 里的 9 条，共 29 条。

---

## 4 与 R2-14 的关系（口径不变）

- R2-14 的 29/243/53 是**旧口径**，本表不修改历史文件，只在 R2-15 新增闭合表并在报告里给出换算。
- `DIGITAL_EDITION_VERIFIED` 仍为 29，`SOURCE_VERIFIED` / `FACSIMILE_VERIFIED` 仍为 **0**。
- `WORKS_120_SOURCE_COLLATION.csv` 实际 **29 条**（不是 120），本轮继续按 29 陈述，不补数。

---

## 5 交付

| 文件 | 内容 |
|---|---|
| `WORKS_339_EVIDENCE_CLOSURE.csv` | 339 行逐条映射（work_id / 三个状态 / 证据依据 / 定位类型） |
| 本文档 | 算式、交叉表、边界说明 |
| `LOGS/C1_closure.py` | 可复算脚本 |

## 6 下游使用建议

- 需要「可信正文」：只用 29 条 `DIGITAL_EDITION_VERIFIED`。
- 需要「结构自洽的候选」：234 条 `STRUCTURE_SUPPORTED` + 23 条 `STRUCTURE_CONFIRMED_NO_SOURCE`，但必须标注"未经来源逐字核"。
- 53 条 `HEURISTIC_ONLY` 不得进入任何自动修订流程。
