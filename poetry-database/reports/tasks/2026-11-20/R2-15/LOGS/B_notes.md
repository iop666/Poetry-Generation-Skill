# B_notes —— R2-15B 书目登记与阅读审计的取证记录

- 任务：R2-15B
- 日期：2026-11-20
- 工作目录：`<PROJECT_ROOT>`
- 输出：`BOOK_CATALOG_52.csv`、`READING_RECORD_AUDIT.md`、`MISSING_MATERIALS.csv`、本文件
- 约束：只读、离线、不改 `poetry.db`。数据库全部用 `sqlite3 "file:poetry.db?mode=ro"` 打开。
- 构建脚本：`LOGS/build_book_catalog_52.py`（可重跑，输出两份 CSV；只读库，不写库）

---

## 一、52 条书目从哪里来

| 文件 | 作用 | 关键内容 |
|---|---|---|
| `poetry-database/reports/round-1/01_文献目录与来源调查.md` | R1 原始总账 | A9＋B8＋C16＋D8＋E5＋F6＝52 行；但开头写「47 项」 |
| `poetry-database/reports/round-1/ROUND-1_完整详细报告.md` §4.2 | 52 条的权威列表 | 明确「52 条（按书名计 54 部）」；§1 勘误说明 47→52 是漏计 C 类 5 条 |
| `poetry-database/reports/round-1/02_实际资料获取报告.md` | 采集侧证据 | 128 源、40.0 MB、`audit/acquisition_log.jsonl` |
| `poetry-database/reports/round-1/03_书籍阅读与提取报告.md` | 阅读侧证据 | 仅 7 行阅读记录，却写「8 种」 |
| `poetry-database/reports/round-1/08_版权与合法性报告.md` | 许可框架 | PD／MIT／CC BY-SA；13 种现代专著只登记不下 |

采用 ROUND-1 完整报告 §4.2 的 52 条，不增不减。C15 保持 1 行（含 3 部书名），不拆成 3 行。

---

## 二、后续轮次改变了哪些状态（关键）

R1 报告截止 2026-11-11；R2-01 起（2026-11-12）大量补采，因此**不能直接照抄 R1 的「未取得」**。

| 轮次 | 报告/日志 | 改变的书 |
|---|---|---|
| R2-01 | `reports/tasks/2026-11-12/R2-01/COMPLETE_REPORT.md` §4.5 | 廣韻 5 卷、詞律 20 卷、御定詞譜 40 卷 → PARSED；集韻首采失败（仅 40 KB） |
| R2-03 / R2-03-R1 | `reports/tasks/2026-11-13/R2-03-R1/COMPLETE_REPORT.md` | 王力合订本 432 页 PaddleOCR 重跑，首次可用 |
| R2-05 | `reports/tasks/2026-11-13/R2-05/COMPLETE_REPORT.md` | 王力 A/B 17 单元 READ；词学十讲补 3 讲 |
| R2-06 | `reports/tasks/2026-11-13/R2-06/COMPLETE_REPORT.md` | 王力 C/D 14 单元 READ；词学十讲补 7 讲 |
| R2-07 | `reports/tasks/2026-11-14/R2-07/COMPLETE_REPORT.md` | 唐宋词格律 153 调/196 格结构化 |
| R2-08 | `reports/tasks/2026-11-14/R2-08/COMPLETE_REPORT.md` | 集韵 206 页重采 |
| R2-09 | `reports/tasks/2026-11-14/R2-09/COMPLETE_REPORT.md` | 词林正韵、中原音韵字表；平水韵 JSON |
| R2-11 | `reports/tasks/2026-11-15/R2-11/COMPLETE_REPORT.md` | 六套韵书来源登记（`rhyme_source_books_r2_11`）；中华新韵 |
| R2-12 | `reports/tasks/2026-11-16/R2-12/COMPLETE_REPORT.md` | 集韵 33,664 字组/42,352 字级索引；广韵 9 条影印对校 |
| R2-13 | `reports/tasks/2026-11-16/R2-13/COMPLETE_REPORT.md` §8 | 元曲「缺文」翻案为字段错位（1,729 条） |
| R2-14 | `reports/tasks/2026-11-16/R2-14/COMPLETE_REPORT.md` §5 | 元曲 24 条源截断 |

---

## 三、用了哪些库表（全部只读）

| 表 | 行数 | 用途 |
|---|---:|---|
| `books` | 13 | R1 遗留书目（发现整体陈旧） |
| `book_items` | 6 | 当前 6 部书的解析元数据（页数/字数/引擎） |
| `book_chapters` | 49 | 词学十讲 33 章、古代汉语常识 16 章 |
| `book_pages` | 2,010 | Vision／PDF 文字层／EPUB 原文 |
| `book_pages_paddle` | 1,691 | 王力 3 部 PaddleOCR 原文（字数复算） |
| `reading_records_r2_05` | 27 | 王力 A/B＋词学十讲（R2-05 状态） |
| `reading_records_r2_06` | 24 | 王力 C/D＋词学十讲（最终状态） |
| `reading_units` | 117 | 节级单元（含 SUPERSEDED） |
| `reading_units_r2_06` | 14 | 王力 C/D 节级单元 |
| `reading_progress` | 6 | 粗粒度进度（READ_STRUCTURE 等） |
| `read_log` | 26 | A6/A7/D1–D5 逐章状态 |
| `reading_notes` | 8 | 王力/龙榆生零散笔记 |
| `works` | 18 collections | 总集入库量 |
| `cipai_forms_r2_07` | 196 | 唐宋词格律结构化格记录 |
| `jiyun_entry_r2_12` | 33,664 | 集韵字组（v3） |
| `jiyun_char_index_r2_12` | 42,352 | 集韵字级索引（v3） |
| `guangyun_fanqie_r2_10` | 20,530 | 广韵反切 |
| `guangyun_fanqie_validation_r2_11` | 3,730 | 广韵小韵验证 |
| `ph_cilin_r2_09` | 5,563 | 词林正韵字表 |
| `ph_zhongyuan_r2_09` | 5,731 | 中原音韵字表 |
| `zhonghua_xinyun_characters_r2_11` | 7,597 | 中华新韵（注意：不是中华通韵） |
| `rhyme_source_books_r2_11` | 6 | 六套韵书来源、底本、局限 |
| `poetry_rules_r2_05/06` | 38 / 39 | 理论规则提取 |

---

## 四、关键 SQL（可复跑）

### 4.1 王力 31 单元

```sql
select part_code,count(*) units,sum(chars_total) ct,sum(chars_read) cr,
       sum(gate_pass) gate,group_concat(distinct status) st
from reading_records_r2_05
where book_id='wangli_shicilv' group by part_code;
-- A|9|57086|57086|9|READ
-- B|8|31108|31108|8|READ

select part_code,count(*) units,sum(chars_total) ct,sum(chars_read) cr,
       sum(gate_pass) gate,group_concat(distinct status) st
from reading_records_r2_06
where book_id='wangli_shicilv' group by part_code;
-- C|12|13601|13601|12|READ
-- D|2|4665|4665|2|READ
```

### 4.2 词学十讲

```sql
select count(*),sum(chars_total),sum(chars_read),group_concat(status)
from reading_records_r2_06 where book_id='long_cixue_shijiang';
-- 10|74652|74652|READ×9,READ_WITH_SOURCE_GAP×1
```

### 4.3 汉字数独立复算（不依赖 reading_records）

```python
import sqlite3, re
con = sqlite3.connect("file:poetry.db?mode=ro", uri=True)
cjk = re.compile(r'[\u4e00-\u9fff]')
def seg(p):
    if 15 <= p <= 182: return 'A'
    if 187 <= p <= 346: return 'B'
    if 351 <= p <= 406: return 'C'
    if 407 <= p <= 431: return 'D'
    return 'other'
tot = {}
for page, text in con.execute(
        "select page,text from book_pages_paddle where book_id='wangli_shicilv'"):
    tot[seg(page)] = tot.get(seg(page), 0) + len(cjk.findall(text or ''))
# {'A': 57086, 'B': 31108, 'C': 13601, 'D': 4665, 'other': 1828}
```

结果 A+B+C+D = **106,460**，A+B+C+D+other = **108,288**（与 R2-06「汉字守恒」一致）。

### 4.4 词学十讲章节字数

```sql
select idx,title,chars from book_chapters
where book_id='long_cixue_shijiang' order by idx;
-- idx 5–14 为十讲，合计 74,652；33 章合计 105,395
```

### 4.5 总集入库量

```sql
select collection,count(*) from works group by collection order by count(*) desc;
-- songshi 252884 / tang 55308 / wanqing 19864 / songci 18794 / yuanqu 10685
-- mingshi 7641 / gushiji 6159 / zhongzhou 2066 / huajianji 498 / wenxuan 357
-- tang300 320 / shijing 305 / nalan 258 / tao 124 / chuci 65 / nantang 45 / caocao 26
```

### 4.6 元数据陈旧

```sql
select book_id,title,status,reading_status from books;
-- 13 行全部 FOUND / NOT_STARTED
```

---

## 五、判定规则（与任务书对齐）

1. 状态词只用：`NOT_FOUND / CHANNEL_IDENTIFIED / ACQUIRED / PARSED / READ / READ_WITH_SOURCE_GAP / EXTRACTED / REVIEWED`。
2. `UNRESOLVED` 仅用于「已 ACQUIRED 但无阅读证据」的 `reading_status`，是任务书「没有证据就写 UNRESOLVED」的哨兵值，不替代 8 个主状态词。
3. **不用 FOUND 代替 READ**：`books.status=FOUND` 一律不采信为阅读证据。
4. `READ` 要求：逐单元状态＋gate_pass＋笔记三项齐备。
5. `EXTRACTED` 对总集的含义是「作品条目已入 `works` 表」，对理论书是「规则/概念已入 `poetry_rules_*` 等表」；两类都在 `note` 写明。
6. 报告数字与库内数字冲突时：**库内实测优先**，报告数字作为「报告声称」保留在 `note` 或审计报告。
7. 只登记 R1 的 52 条，不新增书目；52 条之外的《词学十讲》只在审计报告与 `MISSING_MATERIALS.csv` 以 `EXTRA-` 前缀出现，并注明「52 条之外」。

---

## 六、逐条判断依据（摘要）

### 6.1 判 ACQUIRED 的 29 条

| 类别 | 条件 | 例 |
|---|---|---|
| 有原始文件 + 有库表 | `raw/` 文件存在且 `book_pages`/`works`/韵书表有行 | A1 A3 A6 A7 B2 B3 B4 B5 B6 C1–C10 C12 C13 C15 D1–D5 |
| 只到解析、未建表 | `raw/books/*` 有 wikitext，`sources` 标 PARSED，但无提取表 | A4 A5 |
| 间接取得 | 文本见于已取得的总集 | C12（文选/古诗纪） |

### 6.2 判 CHANNEL_IDENTIFIED 的 23 条

A2 A8 A9 B1 B7 B8 C11 C14 C16 D6 D7 D8 E1 E2 E3 E4 E5 F1 F2 F3 F4 F5 F6。
共同点：**本地无全文**，只有 R1 书目 + 购买/借阅渠道。B7 例外：本地有「新韵」但不是「通韵」。

### 6.3 判 READ 的 8 条

A1 A6 A7 D1 D2 D3 D4 D5。每条都有 `read_log` 或 `reading_records` + 笔记。

### 6.4 判 UNRESOLVED 的 21 条

已取得但无阅读记录。最典型的是 C1/C2/C4：R1 写了 READ，但只有单篇卡片，故下调。

---

## 七、发现的差异（按严重度）

| # | 差异 | 证据 | 处置 |
|---|---|---|---|
| 1 | `books` 13 行全部陈旧 | 4.6 查询 | 登记表不用 `books` 作状态源；审计报告 §5.1 列出 |
| 2 | R1 READ 数 7/8/10 三说 | 01 开头、01 表、03 表、ROUND-1 §4.3 | 采用 7 部最低可信集；审计 §4.3 |
| 3 | C1/C2/C4 书级 READ 无证据 | `read_log` 无记录、03 未列 | 降为 UNRESOLVED |
| 4 | 六部韵书/词谱版本错位 | 登记版本 vs `raw/books/*` | 新增 `acquired_edition` 列逐条写明 |
| 5 | 《中华通韵》≠《中华新韵》 | `rhyme_source_books_r2_11` | B7 保持 CHANNEL_IDENTIFIED，标 SUBSTITUTE_RISK |
| 6 | 全宋词 19,595 vs 18,794 | `works` | 以库内为准，记 −801 |
| 7 | 全唐诗 55,630 vs 55,308 | 01 §C3、ROUND-1 §4.2、`works` | 以 55,308 为准 |
| 8 | 集韵 30,862 不可复现 | R2-11 → R2-12 §3.3 | 采用 v3 33,664 字组/42,352 字级 |
| 9 | raw/books/jiliyun 是失败版 | 10 卷仅 40 KB | MISSING 标 PARSE_UNUSABLE，防误用 |
| 10 | 古诗十九首仅 7/19 可检出 | `works` 题名检索 | C12 标 PARTIAL_TEXT |
| 11 | 元曲 1,729 条字段错位 | R2-13 §8 | C9 标 DATA_QUALITY |
| 12 | 陶渊明作品已 124 首 | `works(collection='tao')` | E5 note 更正 R1「作品为 0」 |

---

## 八、没有做的事（边界声明）

- 未联网、未下载任何资料；所有书目状态基于本地文件与库表。
- 未修改 `poetry.db`；未 `INSERT/UPDATE/DELETE`。
- 未扩充书目：52 条之外只有《词学十讲》因任务要求单独审计，CSV 中不出现。
- 未把「报告声称」写成「已核实」：正文中所有「R1 称」与「本次核实」分开表述。
- 未复核 R1 的平水韵 10,648 条目/8,550 繁数字（无对应库表），故 B4 note 写「不继承」。
- 未复核 52 条中 23 条未取得书的馆藏现状（离线约束），渠道信息沿用 R1。
