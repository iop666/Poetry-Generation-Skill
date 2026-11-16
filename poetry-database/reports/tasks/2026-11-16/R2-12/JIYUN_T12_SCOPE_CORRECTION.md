# JIYUN_T12_SCOPE_CORRECTION — T12「四个空韵」的范围纠正

## 1 事实

R2-10 的 T12 测试断言「已锚定韵下均有小韵」，失败时报告 4 个空韵。R2-11 查明这 4 个空韵实际是**《广韵》**的 **鹽、紙、混、宥**，不是《集韵》的问题。

原因：广韵与集韵在 `ph_readings_r2_08` 等旧表中同用 `system='middle_chinese'`，旧测试按 `system` 取数时把两书混在一起，空韵统计落到了错误的书上。

## 2 本轮复核

| 项 | 结果 |
|---|---|
| 4 韵是否存在于广韵原始结构 | 是（鹽=下平二十四、紙=上三、混=上二十一、宥=上四十四，均见 `raw/books/guangyun/卷*.wikitext`） |
| 为何被 T12 检出为空 | 旧测试用 `system='middle_chinese'` 取数，把集韵的韵名与广韵的韵目表混配 |
| 修复后旧表返回什么 | `guangyun_xiaoyun_recount_r2_11` 中 4 韵均有非零 `xiaoyun_heads` |
| 新视图返回什么 | `guangyun_count_crosswalk_r2_12` 按 `source_book_id='GUANGYUN'` 隔离，4 韵记录齐全 |

## 3 T12 的处置

- T12 **保留为历史测试**，在 `tools/r2_10_tests.py` 中不动、期望值不改。
- 其语义缺陷记入 `TEST_EXPECTATION_CHANGELOG.md`：它测的是「旧 system 字段下的空韵」，不是「集韵空韵」。
- 新测试以 `T16~T25`（集韵）与 `T01~T15`（广韵）分别覆盖，**按 source_book_id 隔离**。

## 4 结论

「集韵修复了 4 个空韵」这一表述**不成立**，应改为「旧测试跨书串数导致的 4 个误报空韵，已在广韵侧核清，集韵侧无对应问题」。本轮据此更正 R2-11 报告中的归类错误。
