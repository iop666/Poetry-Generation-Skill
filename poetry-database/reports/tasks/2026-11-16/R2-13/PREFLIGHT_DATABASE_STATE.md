# PREFLIGHT_DATABASE_STATE — R2-13 执行前状态

冻结时刻：2026-11-16T12:31:50

## 1 与 R2-12 基准比对

| 项 | R2-12 基准 | 实测 | 一致 |
|---|---|---|---|
| 字节数 | 765,222,912 | 765,222,912 | **是** |
| SHA-256 | `e4053f6e…33ac27` | 同左 | **是** |
| integrity_check | ok | ok | 是 |
| page_count | 186,822 | 186,822 | 是 |
| page_size | 4,096 | 4,096 | 是 |
| journal_mode | delete | delete | 是 |
| WAL / SHM | 无 | 无 | 是 |
| 表 / 视图 / 索引 | 105 / 2 / 83 | 105 / 2 / 83 | 是 |
| freelist | 0 | 0 | 是 |

逐字节一致，未调查、未重建。

## 2 作品库与作者规模

| 项 | 值 |
|---|---|
| `works` 行数 | 375,399 |
| `works` 不同 author_name | 20,809 |
| `works` 不同 author_canonical | 20,327 |
| `authors` 行数 | 20,809 |
| `author_alias` 行数 | 20,809 |
| text_raw 为空的 works | 0 |

`authors` 与 `works.author_name` 是 1:1（20,809 = 20,809），说明作者表不是独立权威源，而是按 works 的 author_name 反推生成——这解释了为何作者身份无法从作者表获得独立证据（见 `AUTHORS_CANONICAL_IDENTITY_DESIGN.md`）。

## 3 R2-12 交付件哈希

见 `LOGS/r2_12_hashes.csv`（含 339 审计、328 修订、560 抽样、作者更正、词谱盲读、R2-12 报告）。

## 4 磁盘

`/dev/disk3s5 228Gi 总 / 53Gi 可用（75% 已用）`

## 5 全表快照

`LOGS/table_snapshot.csv`（105 表逐表行数）、`LOGS/preflight.json`。

## 6 执行后状态（供 R2-14 冻结基准）

| 项 | 值 |
|---|---|
| 字节数 | 767,918,080（+2,695,168） |
| SHA-256 | `a9c5bbfb72c0cc8784d080f3332f393e718c61a15d93d35b4114e3edb9258a76` |
| integrity_check | ok |
| page_count | 187,480 |
| `_r2_13` 表数 | 3 |
| `works` 行数 | 375,399（未变） |
| 历史表修改 | 0 |
