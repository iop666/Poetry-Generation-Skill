# PREFLIGHT_DATABASE_STATE — R2-12 执行前数据库状态

冻结时刻：2026-11-16T00:35:45（本地时间）
数据库：`poetry-database/database/poetry.db`

## 1 与 R2-11 基准逐项比对

| 项 | R2-11 基准 | 本轮实测 | 一致 |
|---|---|---|---|
| 字节数 | 715,800,576 | 715,800,576 | **是** |
| SHA-256 | `25c7d92c273f8e82de11d4bd3b0ec6feccf37cfb5eceea373165ad0c507e621e` | 同左 | **是** |
| integrity_check | ok | ok | 是 |
| foreign_key_check | 0 行 | 0 行 | 是 |
| page_count | 174,756 | 174,756 | 是 |
| page_size | 4,096 | 4,096 | 是 |
| journal_mode | delete | delete | 是 |
| WAL / SHM | 无 | 无 | 是 |
| 表 / 视图 / 索引 | 94 / 2 / 74 | 94 / 2 / 74 | 是 |
| freelist_count | 0 | 0 | 是 |

结论：**执行前状态与 R2-11 执行后基准逐字节一致**，无需调查、未重建。

## 2 R2-11 新增对象行数（执行前）

| 表 | 行数 |
|---|---|
| `guangyun_head_classification_r2_11` | 25,619 |
| `guangyun_rhyme_validation_r2_11` | 25,619 |
| `guangyun_xiaoyun_recount_r2_11` | 206 |
| `guangyun_fanqie_validation_r2_11` | 3,730 |
| `zhonghua_xinyun_characters_r2_11` | 7,597 |
| `zhonghua_xinyun_zero_final_r2_11` | 1 |
| `rhyme_source_books_r2_11` | 6 |
| `rhyme_system_identity_r2_11` | 6 |
| `rhyme_group_identity_r2_11` | 570 |
| `rhyme_identity_mapping_r2_11` | 7 |

`_r2_11` 表共 10 张，与 R2-11 报告一致。

## 3 磁盘

`/dev/disk3s5  239,362,496 KB 总 / 58,915,660 KB 可用（74% 已用）`

## 4 全表快照

见 `LOGS/table_snapshot.csv`（逐表行数）与 `LOGS/preflight.json`（完整 JSON）。

## 5 执行后状态（供 R2-13 冻结基准）

| 项 | 值 |
|---|---|
| 字节数 | 765,222,912（+49,422,336，来自 11 张 `_r2_12` 表，其中 4 张为迭代中间表） |
| SHA-256 | `e4053f6ee9bcd73755876d840fe6a35acb9181ba2118766e5ea388daad33ac27` |
| integrity_check | ok |
| page_count | 186,822 |
| `_r2_12` 表数 | 11 |
| 历史表修改 | 0 |
| WAL / SHM | 无 |
