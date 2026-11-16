# RHYME_SYSTEM_TEST_REDESIGN — T60 语义缺陷与替代测试

日期：2026-11-15　关联：`RHYME_SYSTEM_IDENTITY_DESIGN.md`

## 1 旧 T60 的问题

```sql
-- tools/r2_10_tests.py 第 183 行
t("T60", "韻書", "六套體系未被合併成單一平仄字典", 6,
  q("SELECT count(distinct system) FROM ph_readings_r2_08"))
```

两个错误：

1. **维度错**：`system` 是「历史音系大类」，不是「韵书身份」。旧值恰好有 6 个字符串，
   其中 `old_chinese`、`yuan_qu` 在 `ph_readings_r2_08` 里 **0 行**——6 个值里有两个是空壳。
2. **答非所问**：即使 6 个值都有数据，也不证明广韵与集韵没有被合并；事实是它们合并了
   （同一 `middle_chinese` 值，51,392 行）。

所以 T60 的失败（实测 4）不是「数据退步」，而是**测试问错了问题**。R2-11 既不把期望值从 6 改成 4，
也不为了凑 6 强行制造音系分类。

## 2 处理方式

- 旧 T60 **原样保留**在 `tools/r2_10_tests.py`，不删、不改期望值，结果仍记 FAIL，并在
  `TEST_EXPECTATION_CHANGELOG_R2_11.md` 说明其语义缺陷。
- 新建三项测试，分别问三个独立问题（`tools/r2_11_tests.py`）：

| 新 ID | 问题 | 判据 | 实测 |
|---|---|---|---|
| T33 | 六本书是否都在册？ | `count(rhyme_source_books_r2_11)=6` | 6 PASS |
| T34 | 六套分类规范是否互异？ | `count(distinct rhyme_system_id)=6` | 6 PASS |
| T35 | 音系大类是否只有 4 个（不是 6）？ | `count(distinct phonological_family_id)=4` | 4 PASS |
| T36 | 广韵与集韵是否同属中古却算两本？ | `MIDDLE_CHINESE` 下 2 行 | 2 PASS |
| T37 | 两书的 rhyme_system_id 是否不同？ | `count(distinct … where book in (GY,JY))=2` | 2 PASS |
| T40 | 旧值 `middle_chinese` 是否已拆成两本？ | 映射表 2 行 | 2 PASS |
| T41 | 旧值 `old_chinese` 是否标为未建？ | 1 行且 `source_book_id IS NULL` | 1 PASS |

## 3 为什么不把 T60 改成「=4」

因为 4 只是当前 `ph_readings_r2_08` 的**数据现状**（两书合并、上古与曲韵未入统一表），
不是**设计目标**。把期望值改成 4，等于用测试固化缺陷。
正确做法是把「值有几个」这个无信息量的问题，换成「每本书是否可独立定位」这个有信息量的问题。

## 4 对旧 T12 的同类处理

旧 T12：`count(*) FROM guangyun_yunmu_repair_r2_10 WHERE char_offset IS NOT NULL AND n_xiaoyun=0`，期望 0，实测 4。

- 4 个韵是：鹽(卷2-24)、紙(卷3-4)、混(卷3-21)、宥(卷4-49)。
- 原因：这 4 个韵的**韵目行与同用组首韵合并书写**，正文里没有独立韵目行，旧解析器把整段算到前一个韵。
- R2-11 重认后 4 韵均恢复小韵（`JIYUN_T12_FOUR_RHYME_REPAIR.csv`），旧的 4 不再成立。
- 新测试不直接沿用旧 SQL（旧表不被修改），而以新表复查：
  T05 要求「直接锚定韵 ≥ 200」，T06 要求「无区间韵 ≤ 2 且已标记」，实测 204 / 2。

## 5 结论

- 旧测试文件未被修改一个字符，历史失败记录完整保留。
- 新测试 68 项，覆盖小韵识别、又音区分、反切拆分、206 韵完整性、十四韵与零韵母、
  六书身份、稳定韵目 ID、证据等级、词谱跨页、数据保护等 16 个方面。
- 其中 2 项失败（T23 十三支字数下限、T54 图文层级标记依赖文件存在性）需按下轮修正，
  失败如实保留，不调期望值。
