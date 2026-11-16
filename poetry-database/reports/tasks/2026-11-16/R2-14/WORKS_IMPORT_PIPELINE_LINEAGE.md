# WORKS_IMPORT_PIPELINE_LINEAGE — 导入链路追溯

## 1 链路

```
chinese-poetry (GitHub, JackeyGao)
  └─ jsdelivr CDN 分片文件（全唐诗/poet.tang.N.json 等）
       └─ raw/poetry/<collection>/<file>.json   ← 本地留档（819 个在用）
            └─ tools/parse.py（全库唯一 INSERT INTO works 的脚本）
                 └─ works（375,399 行，source_id + seq）
```

## 2 证据

1. `sources.url` 全部指向 `cdn.jsdelivr.net/gh/chinese-poetry/chinese-poetry@master/...`，文件名可读。
2. `sources.local_path` 指向 `raw/poetry/...`，819 个文件全部存在。
3. `sources.acquired_at` 集中在 2026-11-11 ~ 11-12，说明是同一批抓取。
4. `tools/parse.py` 是全库唯一的 `INSERT INTO works` 脚本（R2-13 元曲专项已核）。

## 3 已知损失点

| 环节 | 损失 | 量 |
|---|---|---|
| 抓取 | 3 个文件抓取失败（50MB 限制），内容是错误页 | 3 |
| 导入过滤 | `len(txt_norm) < 8` 丢记录 | 372（元曲） |
| 字段映射 | 元曲曲文被写入 `title_raw` 并在 32 字处硬切 | 1,729 |
| 定位 | 未保存 JSON 数组下标（`seq` 是全局序号，不可反推） | 全库 |
| 卷页 | chinese-poetry 本身无卷页信息，未补配 | 全库 |

## 4 为什么 `seq` 不是下标

`seq` 在同一 `source_id` 内单调但不连续、且最大值远超文件条数。例：`CP-TANG-08` 有 1,003 条，`max(seq)=7,723`。说明 `seq` 是导入时的全局计数器（跨分片累计），不是数组位置。

**补救方法（本轮已验证）**：对 `COUNT_MATCH` 的来源，按 `seq` 排序后与数组顺序一一对应，30 条抽样标题命中 30/30。551 个来源可据此恢复下标。

## 5 建议

1. 在 `sources` 增列 `json_index_verified` 与 `count_match`，把本轮的 551/604 结论固化。
2. 新导入一律保存 `(file_path, array_index)` 二元组。
3. 抓取失败的文件应重抓或标记 `FETCH_FAILED`，不能写 `PARSED`。
