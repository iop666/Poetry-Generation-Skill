# R2-14 C 线工作日志：三集合对账 / 1,729 边界 / 372 过滤 / 100 回源

执行者：general-purpose-1（独立调查者）
日期：2026-11-16
约束：**只读**。全部连接使用 `sqlite3.connect("file:...?mode=ro", uri=True)`；未执行任何 `INSERT/UPDATE/DELETE/ALTER/CREATE`；未联网；未改 `tools/` 任何脚本。

---

## 0. 环境与前置核对

```sql
PRAGMA table_info(works);                     -- 38 列，与 R2-13 D_notes 一致
SELECT collection,COUNT(*) FROM works GROUP BY 1;   -- yuanqu 10,685
SELECT COUNT(*) FROM works;                   -- 375,399
SELECT MIN(seq),MAX(seq),COUNT(DISTINCT seq) FROM works WHERE collection='yuanqu';
-- 327703 | 338387 | 10685   → 元曲 seq 是连续段，可直接当导入顺序
SELECT COUNT(*),SUM(record_locator IS NULL),SUM(record_locator='') FROM works WHERE collection='yuanqu';
-- 10685 | 10685 | 0        → record_locator 全 NULL，不能靠它定位
```

`PRAGMA table_info(works)` 关键列：`work_id, title_raw, title_norm, author_name, collection, genre, cipai, chapter, section, text_raw, text_norm, line_count, char_count, source_id, seq, variant_group, dup_status, quality_grade, record_locator, juan, base_edition, ...`（共 38 列）。

---

## 1. C1 三集合：定义与复现

### 1.1 定义（逐字）

| 集合 | 定义 | 实现 |
|---|---|---|
| `R2_12_2447` | `genre='曲' AND text_raw LIKE '%(%唱)%'` | 纯 SQL，可直跑 |
| `R2_13_2740` | `genre='曲'` 且 `re.search(r'[（(][^）)]*唱[）)]', text_raw)` | SQLite 无内置 regexp，故 `SELECT work_id,text_raw FROM works WHERE genre='曲'` 后在 Python 过滤 |
| `R2_13_4510` | A ∪ B ∪ C：<br>A=上条 2,740<br>B=`title_raw` 含句读 `[，。；？！、：]` 且 `length(title_raw)>=17`<br>C=去掉 `[（(][^）)]*[）)]` 后汉字 <12 | 同上，Python 实现 |

`R2_12_2447` 用的字面量必须写成 `LIKE '%(%唱)%'`（半角 `(` 与半角 `)`），这是复现 2,447 的唯一方式。

### 1.2 复现结果（`LOGS/C1_counts.json`）

```
works_yuanqu      10,685
R2_12_2447         2,447   ← 与 R2-12 完全一致
R2_13_2740         2,740
R2_13_4510         4,510
  A(2740 正则)     2,740
  B(title 含句读>=17) 1,729
  C(去括注汉字<12)   206
A∩B 0 ; A∩C 0 ; B∩C 165 ; C 净新增 41
2,740 + 1,729 + 41 = 4,510  ✅
```

### 1.3 两两交并差（`YUANQU_2447_2740_4510_SET_RECONCILIATION.csv`）

| 对 | 交集 | 差集 |
|---|---|---|
| 2740 ∩ 2447 | **2,447** | 2740−2447 = **293**；2447−2740 = **0**（2,447 ⊂ 2,740） |
| 4510 ∩ 2740 | **2,740** | 4510−2740 = 1,770（=1,729 B + 41 C） |
| 4510 ∩ 2447 | 2,447 | 4510−2447 = 2,063 |

work_id 清单已落地：`LOGS/yq_set_2447.txt`、`LOGS/yq_set_2740.txt`、`LOGS/yq_set_4510.txt`（各 2,447 / 2,740 / 4,510 行，一行一个 `work_id`，utf-8-sig）。

### 1.4 293 条差额的精确构成（对 R2-13「292 全角 + 1 混用」的修正）

对 293 条逐条判括号形态（排他分类）：

| 形态 | 条数 |
|---|---|
| 整对全角 `（…唱）` | **290** |
| 跨式 `(…唱）`（半角开、全角闭） | **3** |

3 条跨式明细：`yuanqu:357c462f1426`（`(正末唱）`）、`yuanqu:b4a9e38a69e5`（`(唱）`）、`yuanqu:e26897dfec15`（`(正末唱）`）。

R2-13 的「292 全角 + 1 混用」应修正为 **「290 全角整对 + 3 跨式」**：292 的口径应是「文本中任一处出现全角 `（`」，把另外 2 条跨式记录也算进了全角组。

---

## 2. C2 1,729 条边界：方法与判定

### 2.1 集合来源

`genre='曲'` 且 `title_raw` 含 `[，。；？！、：]` 且 `len(title_raw)>=17` → 1,729 条。与 `yq_set_4510.txt` 中标注为 `IN_OTHER_FIELD` 的 1,729 条 work_id 完全一致（逐条比对，0 差异）。

### 2.2 边界定位（**不按 32 字切**）

规则按优先级：

1. `title` 含 `・`（U+30FB，全角中点）。注意元曲用 **`・`**，不是 `·`(U+00B7)：`SUM(title_raw LIKE '%·%')=0`。
2. `parts = title.split("・")`：
   - `len(parts)>=3 and parts[1] in ("南","北")` → `boundary_method=DOT_SECOND_NANBEI`，曲牌=parts[0]，宫调南/北=parts[1]，曲文=`"・".join(parts[2:])`（5 条）
   - `parts[0]==""` → `DOT_ONLY_EMPTY_HEAD`，曲牌缺失，整个 title 都是曲文（45 条）
   - 其余 → `DOT_FIRST`，曲牌=parts[0]，曲文=`"・".join(parts[1:])`（1,679 条）
3. 无 `・` → `NONE`（0 条）

分隔符频次：`title.count('・')==1` → 1,724；`==2` → 5。

### 2.3 曲牌词表（判断「・」前是否真为曲牌）

从同批数据自建，不引外部知识：

```
vocab = { title 的无句读形态中，'/' 之后 或 '・' 之后 或 整串（无分隔符） } ，长度 <=12
→ 1,406 个曲牌名
```

匹配结果：`HIT 1,400`、`MISS 329`（其中 45 条为空头、`五`9、`六`8、`双调`4 等为残曲牌/宫调，其余 284 条为未收录曲牌，如 `余音`、`后庭花煞`、`天仙子`、`卖花声煞`）。

置信度：

| 值 | 条数 | 依据 |
|---|---|---|
| `HIGH(qupai_in_vocab)` | 1,400 | 头串在词表内 |
| `MEDIUM(qupai_not_in_vocab)` | 284 | 头串无句读、≤12 字，结构上是曲牌位，但词表未收（需人工确认，见第七节） |
| `LOW(qupai_missing…)` | 45 | 头串为空 |

### 2.4 接缝检验（正文是否已含部分曲文）

取 `lyric` 的汉字尾串与 `text_raw` 首段的汉字首串，求最长重叠 `k`（上限 8）：

| k | 条数 | 判读 |
|---|---|---|
| 0 | 1,707 | 无重字，直接相接 |
| 1 | 20 | **叠字续接**（真字）：`恨绵`+`绵，情脉脉`、`脚儿尖`+`尖，越着`、`老`+`老成成`、`年`+`年害`、`青隐`+`隐浑疑`、`渐`+`渐的`、`荧`+`荧，他`、`朝`+`朝携妓` 等 → **拼接时绝对不可去重** |
| 2 | 2 | 疑真重字，需人工定：`彩衣、`+`彩衣轻纱织翠`（yuanqu:5b704777b815）、`<鼻勾>`+`<鼻勾>。`（yuanqu:6c9b…） |

**这直接推翻了「按重叠去重」的做法**：20 条叠字会被错误删字。

### 2.5 `truncation_at_32` 的实测（重要修正）

| title 长度 | 条数 |
|---|---|
| 32 | **1,425** |
| 33 | **235** |
| 34–43 | 69 |
| 19–31 | 12 |

- 不是「32 字硬切」这么简单：32 与 33 两个峰。逐条看 `(head_len, lyric_len)` 组合，`head_len + 1 + lyric_len` 恒为 32 或 33。
- 33 字者 **232/235 以句读收尾**，32 字者仅 235/1,425 以句读收尾 → 上游是**标题整体截到 32 字，再向后吞一个句末标点**（故 33）。
- 因此正确表述是「**标题整体 32 字上限（33 字为句末标点延伸）**」，而不是「曲文固定切 30 字」。切点落在词中间（`鸳衾`／`玉骢`），**没有任何语义边界**。

### 2.6 其余判定

- `other_fields_with_lyric`：1,729 条 **全部** 为 `NONE`——`chapter/section/cipai/volume/juan/record_locator` 全空（0/1,729）。`quality_grade`（等级标签）、`author_canonical`（作者名）有值但非曲文；`title_norm`/`text_norm` 是派生副本，不另计。
- `lyric_in_text_chars`：`text_raw` 去掉全部括注后的汉字数（不含科白）。
- 1,729 条 **全部** `text_raw` 以句末标点收尾 → **无一条可证「正文也断了」**，故 `TRUNCATED_LOSS` 判定为 0 条。

### 2.7 判定分布（`YUANQU_1729_FIELD_BOUNDARY_AUDIT.csv`）

| verdict | 条数 | 说明 |
|---|---|---|
| `SPLIT_CLEAN` | **1,682** | 曲牌位可辨 + 接缝无需裁量 |
| `TITLE_IS_ALL_LYRIC` | **45** | 标题无曲牌前缀，整串都是曲文；且 `text_raw` 首字是下一支曲牌的「幺」 |
| `SPLIT_AMBIGUOUS` | **2** | 接缝 2 字重字待人工定 |
| `TITLE_IS_ALL_META` | 0 | — |
| `TRUNCATED_LOSS` | 0 | 正文均以句末标点收尾，无截断证据 |
| `UNRESOLVED` | 0 | — |
| 合计 | **1,729** | |

分档（互斥，供 C3 引用）：A 完整可拼 1,662 / B 叠字续接 20 / C 接缝待判 2 / D 曲牌缺失 45。

---

## 3. C4 372 条：定位方法与被过滤的原因

### 3.1 为什么能精确还原（不是估算）

1. 用 `tools/parse.py` 的同一套 `extract_items` + `norm_text` 重跑 `raw/poetry/yuanqu/yuanqu.json`：得 `kept=10,685 / skipped=372`，与 `audit/parsing_log.jsonl` 的 `items:11057 / kept:10685 / skipped_short:372` 三项全等。
2. 元曲 `seq` 是 **327,703–338,387 连续 10,685 号**，且 `parse.py` 的 `seq += 1` 只对**入库记录**递增 → `ORDER BY seq` 即导入顺序。
3. 将重跑得到的 kept 序列与 `works ORDER BY seq` 逐条比对 `title_raw` / `author_name` / `text_raw`：
   **10,685/10,685 全等，差异 0**。
4. 故 skipped 的第 k 条 = 该条在 JSON 中的原始下标 `json#i`（0 基），**无一条靠模糊匹配**。

### 3.2 结果（`YUANQU_372_IMPORT_FILTER_AUDIT.csv`）

| recoverable | 条数 | 含义 |
|---|---|---|
| `Y_TITLE+BODY` | 225 | 曲文头在 `title`，余文（1–7 字）在 `paragraphs`，可无损拼接 |
| `Y_TITLE_ONLY` | 140 | 曲文只在 `title`（约 30 字），`paragraphs` 全空；拼出的只是标题内那一段，**其后是否还有曲文不可判**（其中 19 条标题停在半句） |
| `N` | 7 | 非作品：`(残缺)。`×2、空正文+纯曲牌×4、4 字残句×1 |

`is_valid_work`：`Y` 365 / `N` 7。
`filtered_reason` 统一记录 `len(txt_norm)=N<8`，N 分布：0→144、1→2、2→39、3→43、4→29、5→34、6→33、7→48。

**结论：372 条全部精确定位，无缺口。** 与 R2-13 的「364 条 title 含曲文 / 142 条正文全空 / 312 条正文<8 字」略有差异，原因是判据不同（R2-13 用「含句读且 ≥17 字」，本轮用「去曲牌后 ≥8 汉字」）：正文全空本轮为 **144**（R2-13 记 142），曲文在 title 本轮为 **365**（R2-13 记 364，差 1 条为 `(鹧鸪天)宋玉才多…` 无「・」的形态）。

---

## 4. C5 100 条：抽样与核对方法

- 抽样：`random.Random(20261116).sample()`，分层固定 `IN_OTHER_FIELD 50 / LYRIC_PRESENT 25 / FRAGMENTARY 15 / DIALOGUE_ONLY 1`。
- 定位：`json#i`（同上 §3.1 的对齐方式），每条样本都实际打开 `raw/poetry/yuanqu/yuanqu.json` 读取第 i 个元素。
- 比对：`works.text_raw == "\n".join(JSON.paragraphs)` 且 `works.title_raw == JSON.title`。
- 缺口：`SOURCE_UNAVAILABLE` 实测 **0 条**（10,685 条全部可定位），故第 4 层只有 `DIALOGUE_ONLY` 1 条，缺 9 条用 `FRAGMENTARY` 补足并显式标注 `SUBSTITUTE_FRAGMENTARY`。

结果：**100/100 `EXACT`**，`verdict` 分布：
`SOURCE_VERBATIM_TITLE_HELD` 50 / `SOURCE_VERBATIM` 25 / `SOURCE_TRUNCATED` 24 / `SOURCE_DIALOGUE_ONLY` 1。

> 说明：`EXACT` 是「库内文本与本地原文逐字相同」这一点成立，不是「原文本身完整」。因为唯一写库脚本 `tools/parse.py` 不改写正文（R2-13 已用 2,740/2,740 验证），此结果符合预期；它证明的是**文本缺损发生在入库之前**，并给每条样本一个可复查的 JSON 下标。

---

## 5. 全部 SQL 清单

```sql
-- 表结构
PRAGMA table_info(works);

-- 集合规模
SELECT collection,COUNT(*) FROM works GROUP BY 1 ORDER BY 2 DESC;
SELECT COUNT(*) FROM works WHERE genre='曲';                                  -- 10685
SELECT COUNT(*) FROM works WHERE collection='yuanqu';                         -- 10685

-- C1 三集合
SELECT COUNT(*) FROM works WHERE genre='曲' AND text_raw LIKE '%(%唱)%';      -- 2447
SELECT work_id,text_raw FROM works WHERE genre='曲';                          -- 2,740 由 Python 正则判定
SELECT work_id,title_raw,text_raw FROM works WHERE genre='曲';                -- B/C 判定
SELECT SUM(title_raw LIKE '%・%'),SUM(title_raw LIKE '%·%') FROM works WHERE genre='曲';
-- 8503 | 0    （全角・有、半角·无）

-- 字段可用性
SELECT COUNT(*),SUM(record_locator IS NULL) FROM works WHERE collection='yuanqu';   -- 10685 | 10685
SELECT MIN(seq),MAX(seq),COUNT(DISTINCT seq) FROM works WHERE collection='yuanqu';  -- 327703 | 338387 | 10685
SELECT COUNT(*) FROM works WHERE genre='曲' AND cipai<>'';                    -- 0
SELECT COUNT(*) FROM works WHERE genre='曲' AND (chapter<>'' OR section<>''); -- 0
SELECT COUNT(*) FROM works WHERE genre='曲' AND char_count<>length(text_norm);-- 0
SELECT SUM(text_raw LIKE '%（%'),SUM(text_raw LIKE '%(%') FROM works WHERE genre='曲';
-- 371 | 3963

-- C5 分层母体
SELECT work_id FROM works WHERE collection='yuanqu' ORDER BY seq;             -- 10,685，与 JSON kept 序列等长
```

正则（Python，等价实现）：
```python
CHANG   = re.compile(r"[（(][^）)]*唱[）)]")     # 2,740
JUDOU   = set("，。；？！、：")
HAN     = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002ffff]")
BRACKET = re.compile(r"[（(][^）)]*[）)]")         # 去科白后计字
```

---

## 6. 无法判定的项（如实计数）

| 项 | 条数 | 原因 |
|---|---|---|
| 曲牌位为空、无法恢复曲牌名 | **45** | 上游标题就是「・曲文…」，本地无第二来源；曲文可拼，曲牌不可 |
| 曲牌头不在自建词表（待人工确认是否为曲牌） | **284** | 词表来自同一份数据，未收的曲牌名（`余音`/`天仙子`/`后庭花煞` 等）无法自动确认；结构上位于「・」之前，判为曲牌位 |
| 接缝 2 字重字，需人工决定是否删字 | **2** | `彩衣、`+`彩衣…`、`<鼻勾>`+`<鼻勾>。`；删/不删都会改变原文 |
| 372 条中「曲文只在 title、正文全空」是否还有后续 | **140**（其中 19 条标题停在半句） | 标题被上游截断，本地无第二来源 |
| 41 条短段中「本来就短」与「被截断」的区分 | **33** | 仅 8 条可凭末段 ≤2 字确认句中截断（`世。`/`眼巴。`/`，。`），其余 33 条末段 3–11 字，无第二来源 |
| 32/33 字硬切是否偶发跨字错误（如拆字「扌颠」） | 未逐条验 | 本轮只做接缝重叠与词界抽读，未逐字校对 1,729 条；`扌颠`、`衤离`、`リ` 等拆字在数据中确实存在（`绣鞋重扌颠`、`鹭衤离`、`惟蹴リ最风流`），属上游字符集问题，非截断 |
| 标题/正文垂直错位（标题属下一支曲牌） | 全库未扫描，已确认 1 例 | 仅在「同一套数被两位作者重复收录」的 4 个块内可对齐核出：json#108 关汉卿「尾」paragraphs 为空、其正文挂到 #109「双调・新水令」下（副本 #10769 配对正确）。该行 title 无句读，既不在 1,729 也不在 41 条内。详见 C7_yuanqu_cross_author_check.csv 与字段映射文档 §4.4 |

---

## 7. 复现

```bash
cd <PROJECT_ROOT>/poetry-database
python3 reports/tasks/2026-11-16/R2-14/LOGS/S1_sets.py
python3 reports/tasks/2026-11-16/R2-14/LOGS/S2_boundary.py
python3 reports/tasks/2026-11-16/R2-14/LOGS/S3_filter372.py
python3 reports/tasks/2026-11-16/R2-14/LOGS/S4_sample100.py
```
中间结果：`LOGS/C1_counts.json`、`LOGS/C2_stats.json`、`LOGS/C4_counts.json`、`LOGS/C5_counts.json`。
