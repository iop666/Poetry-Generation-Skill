# DISPUTE_RESOLUTION_18_R2_12 — R2-11 遗留 18 条争议的逐条处置

R2-11 的 120 对象复核结果：AGREE 96 / DISAGREE 18 / UNDECIDABLE 6。本文件处置这 18 条。

## 汇总

| 终态 | 条数 | 说明 |
|---|---|---|
| `RESOLVED_MAIN_WRONG` | 6 | 原判 work_len=0 系检索不足，本轮双路检索找到作品 |
| `RESOLVED_INDEPENDENT_WRONG` | 2 | 独立方按整串反切比对判 NOT_FOUND，新表已按单字重拆 |
| `RECLASSIFIED` | 2 | 找到作品但作者不符，降为 AUTHOR_CONFLICT |
| `OPEN_NEEDS_IMAGE` | 6 | 广韵 6 条须影印本裁定 |
| `OPEN_NEEDS_PAGE_ALIGN` | 2 | 阅读记录页码未对齐 |
| `CONFIRMED_NO_MATCH` | 2 | 确认真缺 |

## 逐条

| ID | 对象 | 原争议 | 本轮证据 | 终态 |
|---|---|---|---|---|
| D01 | GY-11 | SUPPORTED_HEAD_NO_MARKER(□) vs HEAD | 本轮仅对校卷一叶，该条不在其中 | OPEN_NEEDS_IMAGE |
| D02 | GY-13 | 同上 | 同上 | OPEN_NEEDS_IMAGE |
| D03 | GY-16 | ALTERNATIVE_READING(眭) vs HEAD | 同上 | OPEN_NEEDS_IMAGE |
| D04 | GY-20 | POSSIBLE(糖) vs NOT_FOUND | 同上 | OPEN_NEEDS_IMAGE |
| D05 | GY-21 | POSSIBLE(□) vs HEAD | 同上 | OPEN_NEEDS_IMAGE |
| D06 | GY-22 | POSSIBLE(佖) vs NOT_FOUND | 同上 | OPEN_NEEDS_IMAGE |
| D07 | JY-13 | 䵵 判 NOT_FOUND，但 head_in=True, fq_in=True | 新表 `jiyun_small_rhyme_audit_r2_10` 已把 `fanqie_upper` 由整串改单字；独立方比对的是整串「徳紅」故判未命中 | RESOLVED_INDEPENDENT_WRONG |
| D08 | JY-19 | 鄰 同上 | 同上 | RESOLVED_INDEPENDENT_WRONG |
| D09 | RD-03 | 引文「本编依韵脚分类，计分平韵、仄韵…」未命中（页文 652 字） | 该页文本通道存在，但 `reading_notes.page_from` 与 `pages.jsonl` 的页号口径未对齐（差 1 或差 2） | OPEN_NEEDS_PAGE_ALIGN |
| D10 | RD-05 | 引文「二十七字，四平韵…」同上（646 字） | 同上 | OPEN_NEEDS_PAGE_ALIGN |
| D11 | EX-05 | 例词「簟枕邀凉，琴书换日」work_len=0 | 双路检索（text_raw + text_norm）仍 0 命中 | CONFIRMED_NO_MATCH |
| D12 | EX-07 | 例词「河汉，河汉，晓挂秋城漫漫」work_len=0 | 仍 0 命中 | CONFIRMED_NO_MATCH |
| D13 | EX-10 | 例词「子规啼血，可怜又是，春归时节」work_len=0 | **命中**：《柳梢青》/吕渭老，65 字 | RESOLVED_MAIN_WRONG |
| D14 | EX-16 | 例词「长空降瑞，寒风剪」work_len=0 | **命中**：《望远行》/柳永，137 字 | RESOLVED_MAIN_WRONG |
| D15 | EX-17 | 例词「平岸小桥千嶂抱」work_len=0 | **命中**：《渔家傲》/王安石，81 字 | RESOLVED_MAIN_WRONG |
| D16 | EX-19 | 例词「斗酒彘肩，风雨渡江」work_len=0 | 命中《贈別陳東甫呈尚書鍾公》/樂雷發 | RECLASSIFIED（应为刘过《沁园春》，作者冲突） |
| D17 | EX-23 | 例词「麻叶层层檾叶光」work_len=0 | **命中**：《浣溪沙》/苏轼，52 字 | RESOLVED_MAIN_WRONG |
| D18 | EX-26 | 例词「宝钗分，桃叶渡」work_len=0 | 命中《双调·一机锦离思》/无名氏 | RECLASSIFIED（应为辛弃疾《祝英台近》，作者冲突） |

## 结论

1. **`work_len=0` 是"没搜过"，不是"搜过没有"** ——本轮再证：8 条中 6 条一搜即得。R2-11 的 `NO_MATCH` 状态必须整体重估（GD-018 已据此关闭）。
2. 广韵 6 条争议**只能靠影印本裁定**，程序无法解决；本轮因叶码映射未建立而无法推进。
3. 集韵 2 条属**方法差异**，不是数据错误：独立方用整串反切，主方用单字拆分，两者在不同表上工作。
4. 阅读记录 2 条暴露 `reading_notes.page_from` 与 OCR 页号**口径不一致**，需建页号映射表（新缺陷，下轮处理）。
