# 元曲导入链审计（R2-13 / D3）

> 只读审计。未修改 `works`，未改任何脚本。
> 目标：查清「元曲只剩科白、曲文丢失」的责任层——是导入脚本改坏了，还是上游数据本来如此。

---

## 一、查了哪些脚本

`tools/` 共 143 个文件。与「元曲/曲/yuqu/yuanqu/散曲」相关的只有 2 个：

| 脚本 | 作用 | 是否写 `works` |
|---|---|---|
| `tools/build_manifest.py` (L107-108) | 在 manifest 里登记来源 `CP-YUANQU` | 否 |
| `tools/parse.py` | 解析 `raw/**/*.json` 并**建库** | **是（全库唯一）** |

验证方法：

```
grep -ln "INSERT INTO works\|INSERT OR REPLACE INTO works" tools/*.py
→ 只有 tools/parse.py
grep -ln "yuanqu" tools/*.py
→ tools/build_manifest.py, tools/parse.py
```

**结论：元曲文本只被 `parse.py` 写过一次，不存在「多脚本先后覆盖」。**
`sqlite_master` 中含 `qu`/`yuefu`/`qupai` 的表：**0 个**（见下「曲文是否在别处」）。

---

## 二、采集链

1. `tools/build_manifest.py` L107：
   ```python
   ENTRIES.append(poetry("CP-YUANQU", "元曲", "元", "yuanqu", "元曲/yuanqu.json",
                         "散曲小令，非诗词正体，作对照语料。", category="曲集"))
   ```
   注意：manifest 声明它是**「散曲小令」**，实际文件里大量是**杂剧/套数**（带科白、带剧目名的分曲牌记录）。这是描述失真，不是数据改动。

2. `tools/acquire.py` L54-69 `fetch_to()`：`curl -sS --compressed -o dst`，**直接写盘、不经 stdout**，注释明说是为了防「大文件经管道偶发截断」。因此落盘字节即上游字节。

3. 落盘结果 `raw/poetry/yuanqu/yuanqu.json`：
   - sha256 = `c2be37d2349cec99ec7f2d7c4107eb08bbb3ac869221db24531c8ffed2a88b12`
   - 4,188,599 字节，11,057 条 JSON 记录
   - `provenance.upstream_version` = `master (未固定 commit)`

---

## 三、`parse.py` 对元曲做了什么（逐行）

| 行号 | 代码 | 影响 |
|---|---|---|
| L200 | `lines = (t.get("paragraphs") or t.get("content") or t.get("verse") …)` | 取 `paragraphs` 数组 |
| L307 | `txt_raw = "\n".join(lines)` | **整段照抄，无截断、无正则清洗** |
| L308 | `txt_norm = norm_text(lines)` | 只删标点空白 |
| **L309** | `if len(txt_norm) < 8: n_skip += 1; continue` | **唯一会「丢记录」的一步** |
| L312 | `title_raw = it["title"]` | **上游 title 原样继承**（污染传导点） |
| L320 | `genre, basis = infer_genre(coll, lines, meta.get("genre_hint"))` | 元曲 hint=`曲`，故 genre 恒为「曲」，`genre_basis='依集合先验'` |
| L321 | `wid = f"{coll}:{sha1(author|tnorm|txt_norm)[:12]}"` | id 由归一文本决定 |

**关键：`text_raw` 里没有任何「只保留科白」「括号过滤」「按行截断」的代码。** 正因为没有过滤，
上游把科白与唱词混在一段里，入库后就原样是混的。

---

## 四、证据：库内文本与原始文件逐字节相同

对审计全集 4,510 条逐条比对 `works.text_raw` 与 `raw/poetry/yuanqu/yuanqu.json` 的
`"\n".join(paragraphs)`：

```
2,740 / 2,740 条（含「唱」提示的全部记录）  完全一致，差异 0 条
```

（脚本：`LOGS/D1_build.py`、`LOGS/D2_source.py`；D2 抽样 20 条的结果在
`YUANQU_SOURCE_DISTRIBUTION.md` 第四节，S01–S20 全部标 `逐字相同=True` 或明确说明在标题内。）

**库没有改坏文本。文本在入库前就已经是现在这样。**

---

## 五、证据：`parsing_log` 的可核对差额

`audit/parsing_log.jsonl` 第 340 行（2026-11-12T23:31:30）：

```json
{"source_id":"CP-YUANQU","path":"raw/poetry/yuanqu/yuanqu.json","collection":"yuanqu",
 "status":"PARSED","items":11057,"kept":10685,"skipped_short":372}
```

- 原始 11,057 条 → 入库 10,685 条
- **372 条被 `len(txt_norm) < 8` 判为「过短」丢弃**
- 这 372 条的实际形态（逐条回 `raw` 实测）：**364 条 `title` 含句读且 ≥17 字**，不是「没有曲文」，是「曲文在 title 里」；
  其中 142 条 `paragraphs` 完全为空、312 条正文不足 8 字 → 导入侧的**过度过滤**，属可复原损失。

---

## 六、逐项排查（任务点名的四类嫌疑）

| 嫌疑 | 结论 | 证据 |
|---|---|---|
| 只取科白 | **否** | `parse.py` 不区分曲/白，整段 `"\n".join(paragraphs)`；2,739 条记录正文明确含曲文 |
| 字段映射错位 | **导入侧否，上游是** | 映射是 `title→title_raw`、`paragraphs→text_raw`，无错位。但**上游 JSON 自己把曲文前半截塞进了 `title`**（1,729 条，title 长度恰为 32 字者 1,425 条），导入原样继承 → 属上游 `FIELD_MISPLACED` 的**传导**，不是导入错位 |
| 按行截断 | **否** | 无 join 长度上限、无 `[:N]` 切片；`line_count` 与 `len(paragraphs)` 全等（可查） |
| 覆盖 text | **否** | `variants` 表只有 `group_id/work_id/note`，**不含文本字段**；`works` 一次写入，无 UPDATE |

补充：去重环节存在，但只写 `dup_status`/`variants` 标记，不合并文本（`parse.py` L383-400）。
所以「同曲牌不同折被误判为重复」只影响标记，不影响文本。

---

## 七、根因判定

**主判定：`SOURCE_INCOMPLETE`（上游数据本身就缺），并与上游 `FIELD_MISPLACED` 同时成立。**

理由链：

1. 文本零改写（第四节）→ 排除导入改写。
2. 唯一写库脚本只有一个（第一节）→ 排除多脚本互相覆盖。
3. 上游 JSON 的内部结构显示出两种**系统性**污染，且都发生在 `title` 字段：
   - 曲文前半截被并入 `title`，`title` 长度在 32 字处被硬切（1,425/1,729 恰为 32 字）；
   - 部分条目曲文整段在 `title`，`paragraphs` 为空或不足 8 字 → 被 `len<8` 丢弃（372 条）。
   这种「32 字硬切」只可能发生在抓取/整理环节，不可能由 `parse.py` 产生。
4. 41 条正文在句中直接断掉（如「银须霜鬓，世。」「则见他人丛里叠扑着个幽。」），
   `paragraphs` 到此为止，说明上游抓取时就截断了。

**导入侧唯一可归责项（次要）：`IMPORT_ERROR`**
- L309 `len(txt_norm) < 8` 过滤过激，把 372 条「曲文在 title」的记录整条丢弃。
  这批记录本可从同一本地文件复原（曲文在 `title`、余文在 `paragraphs`），不需联网。

**为什么不是 `IMPORT_ERROR` 为主因**：若导入有截断/映射错误，`text_raw` 应与原文不同；
实测 2,740/2,740 逐字节相同，差异为 0。

---

## 八、曲文是否在别的表 / 别的字段

| 位置 | 是否存有这些记录的曲文 | 证据 |
|---|---|---|
| `works.text_raw` | 部分有（2,739 条曲文在正文）；1,729 条只有后半截 | D1 分类 |
| `works.text_norm` | 同 `text_raw` 去标点版，**无额外曲文**（`text_norm` 与 `text_raw` 汉字数全等） | SQL 比对 |
| `works.title_raw` | **有：1,729 条曲文前半截在这里**（平均 25.1 字，占恢复后全文 42%） | D1/D4 |
| `works.chapter` / `section` | 全为空 | `SELECT COUNT(*) … WHERE chapter<>''` = 0 |
| `variants` | 只有 `group_id/work_id/note`，**无文本列** | `PRAGMA table_info(variants)` |
| `text_crosscheck` | 0 行引用 yuanqu | 全表 286 行，均非 yuanqu |
| `books` / `book_items` / `book_pages` | 全库 13 本书，**没有元曲选/元曲总集** | `SELECT book_id,title FROM books` |
| `sqlite_master` 中 `yuefu`/`qu`/`qupai` 表 | **0 个** | `SELECT name FROM sqlite_master` |

→ **没有「另一张表藏着完整曲文」这回事。** 唯一的「别处」就是同一行的 `title_raw`。

---

## 九、我无法判断的

1. **上游是哪个 commit**：`master (未固定 commit)`，且本地无 `.git`。无法核对上游历史，也无法确认这个 32 字硬切是 scraper 的 bug 还是原站 HTML 结构所迫。
2. **`tools/` 里没有任何元曲抓取/清洗脚本**，无法看到上游处理代码。只能从数据形态反推。
3. 372 条被丢弃的记录，其 `works` 行不存在，**无法在库内核对**，只能回 `raw` 确认：364 条 `title` 含句读（曲文在 title），142 条正文全空，312 条正文 <8 字。
