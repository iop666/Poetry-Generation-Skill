# WORKS_SOURCE_SCHEMA_AUDIT — 作品来源字段全量审计

## 1 结论先行

**R2-13「作品无来源」的表述不成立。** 准确说法是：作品**有文件级来源**（100%），但**没有书目级卷页定位**（0%）。

| 层级 | 字段 | 覆盖 |
|---|---|---|
| 来源标识 | `works.source_id` | **375,399 / 375,399（100%）** |
| 来源登记 | `sources` 表（941 行，含 url/local_path/bytes/获取时间/可靠性声明） | source_id **100% 命中** |
| 文件定位 | `sources.local_path` → 实际文件 | 819 个在用来源**文件全存在**（0 missing） |
| 文本偏移 | `(source_id, 数组下标)` | **551 个来源 / 164,217 条作品可精确定位（43.7%）** |
| 卷次 | `works.juan` | **0** |
| 页码/叶码 | `works.record_locator` | **0** |
| 版本 | `works.base_edition` | **0** |

## 2 sources 表

941 行，字段：`source_id, name, category, era, collection, url, license, copyright, reliability, maintainer, format, local_path, sha256, bytes, acquired_at, parse_status, verified`。

- `local_path` 100% 非空；`verified` 100% 为 `NO`（从未对校，声明诚实）。
- `reliability` 明写：「二手整理：来源网站已不可追溯，未与任何印本对勘，无校勘记录。仅可作语料，不可作权威底本。」
- `url` 指向 chinese-poetry 项目的 jsdelivr CDN，含具体文件名（如 `全唐诗/poet.tang.14000.json`）。

## 3 文件有效性

| 类型 | 数量 |
|---|---|
| `JSON_LIKE`（以 `[`/`{` 开头，可用） | **855** |
| `NON_JSON_TEXT`（纯文本/其他格式） | 83 |
| `FETCH_ERROR_PAGE`（抓取失败，内容是 "Package size exceeded 50MB"） | **3** |

3 个失败页的 `bytes` 记录为 157，与实际文件大小一致——**当时就抓失败了，但 `parse_status` 仍写作 `PARSED`**，这是元数据错误（已登记）。

## 4 可精确定位的部分（本轮核心成果）

对全部 818 个在用来源逐个验证：

| 判定 | 来源数 |
|---|---|
| `COUNT_MATCH`（works 数 = JSON 元素数） | **604** |
| 其中「按 seq 排序后与数组顺序一致、30 条抽样标题命中 ≥25」 | **551** |
| `COUNT_MISMATCH`（导入时过滤/合并导致数量不等） | 214 |

551 个可精确定位来源覆盖 **164,217 条作品（43.7%）**，定位方式为 `(source_id → local_path → 数组下标)`，即 `TEXT_OFFSET_LOCATOR`。

**30 条逐字对校结果：30/30 `EXACT`**——`works.text_raw` 与原始 JSON 的 `paragraphs` 拼接，去标点后汉字序列完全相同。

## 5 字段语义校正

| 字段 | 实际语义 | 是否可用于定位 |
|---|---|---|
| `source_id` | chinese-poetry 的分片文件标识 | **是**（文件级） |
| `seq` | 导入时的**全局累计序号**，不是数组下标（如 CP-TANG-08 的 maxseq=7723，文件仅 1003 条） | 需配合 source 内排序 |
| `collection` | 总集名（tang/songshi/songci/…） | 仅书目级 |
| `record_locator` / `juan` / `base_edition` | **全空** | 否 |

## 6 未解决

- 214 个 `COUNT_MISMATCH` 来源：需查清是导入过滤（`len<8`）、合并还是重复，才能把剩余 211,182 条也升到下标级。
- 83 个 `NON_JSON_TEXT` 文件：格式需确认（可能是已转换的 txt）。
- 无任何卷页定位：chinese-poetry 本身不提供卷页，要得到 `PAGE_LOCATOR` 必须换用影印本或善本目录。
