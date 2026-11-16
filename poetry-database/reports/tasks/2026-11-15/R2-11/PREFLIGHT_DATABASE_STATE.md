# PREFLIGHT_DATABASE_STATE — R2-11 执行前冻结

冻结时间：2026-11-15T23:03:58　工作目录：`poetry-database/`

## 1 数据库物理状态

| 项 | 实测值 |
|---|---|
| 文件 | `database/poetry.db` |
| 字节数 | 709,943,296 |
| SHA-256 | `cddcc659104730895daf51902b96c7e73cbf86d0d01f6d45734c195200b2a50a` |
| 修改时间 | 2026-11-15T21:57:18 |
| PRAGMA integrity_check | `ok` |
| PRAGMA foreign_key_check | 0 行 |
| page_count / page_size | 173,326 / 4,096 |
| journal_mode | `delete` |
| freelist_count | 0 |
| WAL / SHM | 均不存在（`-wal` false，`-shm` false） |
| 对象计数 | table 84 / view 2 / index 68 |

**与任务书基准比对**：任务书要求 R2-10 执行后基准为 709,943,296 字节、SHA-256 `cddcc659…2a50a`。
实测字节数与哈希**完全一致**，说明 R2-10 之后数据库未被任何进程改写。

## 2 R2-10 新增对象存在性与行数

| 对象 | 存在 | 行数 |
|---|---|---|
| `guangyun_fanqie_r2_10` | 是 | 20,530 |
| `guangyun_yunmu_repair_r2_10` | 是 | 206 |
| `jiyun_page_provenance_r2_10` | 是 | 206 |
| `jiyun_small_rhyme_audit_r2_10` | 是 | 4,169 |
| `cipai_symbol_audit_r2_10` | 是 | 60 |
| `v_ph_semantics_r2_10`（视图） | 是 | 80,652 |

## 3 磁盘

`df -k` 实测：239,362,496 KB 总容量 / 163,637,264 KB 已用 / 58,966,560 KB 可用（74%），不构成写入风险。

## 4 本轮新增对象清单（全部 `_r2_11` 后缀）

表 13 个、无视图、无索引变更：

`guangyun_head_classification_r2_11`(25,619)、`guangyun_xiaoyun_recount_r2_11`(206)、
`guangyun_fanqie_validation_r2_11`(3,730)、`guangyun_rhyme_validation_r2_11`(25,619)、
`zhonghua_xinyun_characters_r2_11`(7,597)、`zhonghua_xinyun_zero_final_r2_11`(1)、
`rhyme_source_books_r2_11`(6)、`rhyme_system_identity_r2_11`(6)、`rhyme_group_identity_r2_11`(570)、
`rhyme_identity_mapping_r2_11`(7)。

> 应建未建：任务书建议的 `jiyun_sample_review_r2_11`、`jiyun_djvu_validation_r2_11`、
> `cipai_image_reaudit_r2_11`、`schwa_image_audit_r2_11`、`example_link_review_r2_11`、
> `independent_review_r2_11` 六表，因本轮相应工作以 CSV 交付且部分未完成，**未建空表**
> （任务书明确「实际表数量根据真实数据决定，不得为了满足清单建立空表」）。

## 5 历史表保护核验

R2-07/08/09/10 各表行数与冻结快照一致，未执行任何 UPDATE/DELETE/ALTER。
逐表行数见 `PREFLIGHT_TABLE_SNAPSHOT.csv`，原始文件哈希见 `PREFLIGHT_FILE_HASHES.csv`。

## 6 执行后状态（供 R2-12 冻结基准）

| 项 | 值 |
|---|---|
| 字节数 | 715,800,576（+5,857,280，来自 10 张 `_r2_11` 表） |
| SHA-256 | `25c7d92c273f8e82de11d4bd3b0ec6feccf37cfb5eceea373165ad0c507e621e` |
| integrity_check | ok |
| page_count | 174,756 |
| `_r2_11` 表数 | 10 |
| 历史表修改 | 0 |
