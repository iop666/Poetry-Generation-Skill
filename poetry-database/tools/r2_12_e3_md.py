#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 WORKS_AUTHOR_NAME_AUDIT.md"""
import csv, sqlite3
from collections import Counter

ROOT = "<PROJECT_ROOT>/poetry-database"
OUT = f"{ROOT}/reports/tasks/2026-11-16/R2-12"
rows = list(csv.DictReader(open(f"{OUT}/WORKS_AUTHOR_CORRECTIONS.csv", encoding="utf-8-sig")))
con = sqlite3.connect(f"file:{ROOT}/database/poetry.db?mode=ro", uri=True)
con.text_factory = str
q = lambda s: con.execute(s).fetchall()

sc = [r for r in rows if r["issue"] == "SINGLE_CHAR_NAME"]
simp = [r for r in rows if r["issue"] == "SIMPLIFIED_TRADITIONAL_SPLIT"]
np_ = [r for r in rows if r["issue"] == "NOT_PERSON"]
dig = [r for r in rows if r["issue"] == "NAME_DIGIT_SUFFIX"]
pun = [r for r in rows if r["issue"] == "MULTI_AUTHOR_OR_PUNCT"]
crs = [r for r in rows if r["issue"] == "CROSS_DYNASTY_SAME_NAME"]
ano = [r for r in rows if r["issue"] == "ANON_VARIANT"]
mark = [r for r in rows if r["issue"] == "NAME_NOTE_MARK"]

n_total_works = q("SELECT count(*) FROM works")[0][0]
n_author = q("SELECT count(DISTINCT author_name) FROM works")[0][0]
n_canon = q("SELECT count(DISTINCT author_canonical) FROM works")[0][0]
simp_pairs_all = 442
cross_all = q("SELECT count(*) FROM (SELECT author_name FROM works GROUP BY 1 HAVING count(DISTINCT dynasty)>1)")[0][0]
single_rows = sum(int(r["n_suspect_rows"]) for r in sc)

def tbl(header, body):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    out += ["| " + " | ".join(x) + " |" for x in body]
    return "\n".join(out)

sc_body = []
for r in sc:
    ev = r["evidence"]
    cand = "—"
    if "同姓候选：" in ev:
        cand = ev.split("同姓候选：")[1].split("；")[0]
    elif "更长名最多者：" in ev:
        cand = ev.split("更长名最多者：")[1].split("；")[0]
    if r["author_name"] == "张":
        cand = "张昪（外部文献；库内无此名）"
    sc_body.append([r["author_name"], r["n_suspect_rows"], cand, r["verdict"]])

simp_tbl = tbl(["作者名（繁/简）","繁形条数","判定"], [[r["author_name"], r["n_suspect_rows"], r["verdict"]] for r in simp[:12]])

md = f"""# 作品库作者名审计（R2-12 / E3）

对象：`database/poetry.db` → `works` 表，{n_total_works:,} 条。只读审计，未改动任何数据。
产出配套文件：`WORKS_AUTHOR_CORRECTIONS.csv`（{len(rows)} 行，逐条含 evidence 与 verdict）。

## 0. 结论摘要

| 指标 | 数值 | 说明 |
|---|---|---|
| distinct `author_name` | {n_author:,} | 现存写法数 |
| distinct `author_canonical` | {n_canon:,} | 已做繁→简归并，但**未修截断** |
| 单字作者 | {len(sc)} 个 / {single_rows} 条 | 全部疑为截断或残字 |
| 匿名写法 | 4 种 / {sum(int(r['n_suspect_rows']) for r in ano):,} 条 | 佚名/无名氏/無名氏/不詳 |
| 名字含阿拉伯数字 | {len(dig)} 个 / {sum(int(r['n_suspect_rows']) for r in dig)} 条 | 上游同名消歧后缀泄漏 |
| 非人名（体裁/谚语/祠庙） | {len(np_)} 个 / {sum(int(r['n_suspect_rows']) for r in np_):,} 条 | 最大一项「郊廟朝會歌辭」1,639 条 |
| 繁简两形并存 | {simp_pairs_all} 对 | 已入表前 60 对（按条数排序） |
| 同名跨代 | {cross_all} 个作者名 | 绝大多数为 1–2 条少数派误标 |

## 1. 方法

1. `PRAGMA table_info(works)` 确认字段：`work_id / title_raw / title_norm / author_name / author_id / dynasty / genre / text_raw / text_norm / char_count / source_id / author_canonical …`（与任务描述一致）。
2. 单字作者：`length(author_name)=1` 分组，取 `count(*)`、`dynasty`、`genre`。
3. 候选全名：对每个单字 `X` 执行 `author_name LIKE 'X%' AND length(author_name)>1`，按条数排序取前 4。
4. **同文重出**（唯一可用的客观证据）：取单字作者每条作品的 `substr(text_norm,1,14)`，在**非单字作者**的作品中做 `LIKE '%前缀%'` 检索；命中即说明同篇作品在库内有更完整署名。
5. 空白/异常：`IS NULL`、`trim()=''`、`GLOB '*[0-9]*'`、`GLOB '*[，。、；：！？（）]*'`、`LIKE '%〖%'`。
6. 同名跨代：`GROUP BY author_name HAVING count(DISTINCT dynasty)>1`。
7. 繁简：以 `author_alias(kind='VARIANT_SIMP')` 为映射表，用两侧在 `works` 中均真实存在的 `raw_name/canonical` 对计数。

## 2. 单字作者（{len(sc)} 个，{single_rows} 条）

{chr(10).join(x for x in [tbl(["作者名","条数","库内同姓最长候选","判定"], sc_body)])}

**关键判断**：42 个单字作者中，**没有一个能凭库内证据确证全名**（没有任何一个单字作者的整篇作品在库内以更长姓名重出且姓氏相符）。因此：

- `MERGE_UNCERTAIN` {sum(1 for r in sc if r['verdict']=='MERGE_UNCERTAIN')} 个：几乎必然是截断，但候选有多个（同姓诗人动辄数百条），无法唯一定位；
- `UNRESOLVED` {sum(1 for r in sc if r['verdict']=='UNRESOLVED')} 个：「洽」等字在库内无任何同字起首的更长作者名，疑为法名残字；
- `MERGE_SAFE` **0 个**。

**唯一有文本证据的特例：「张」（4 条，均为宋词）**

- 《满江红·无利无名》《离亭燕·一带江山如画》按其首句可定为**张昪（张昇）**之作（外部文献判断）；
- 库内**不存在** `张昪 / 张昇 / 張昪 / 張昇` 任何一种写法（`LIKE '%昇%'` 仅得温子昇、朱元昇等无关者）；
- 同篇《离亭燕》在库内另有 `songci:210e2944394b 孙浩然` 一条，属**互见/误属**，不能作为合并依据；
- 另一个巧合：《水调歌头·雪月两相映》（`songci:5c72778ae6c4`）在库内另有 `朱熹` 名下同文一条。

→ verdict 定 `MERGE_UNCERTAIN`，`suggested_full_name=张昪`，需人工确认后再合并。**没有拿到库内闭环证据，不做 MERGE_SAFE。**

> 附带发现：这些单字行的 `dynasty` 同样不可靠。例如「查」标为「宋／词」（查慎行为清人）、「徐」标为「明／未定」（徐積为宋人）。截断的不仅是名字，作者归属字段整体是坏的。

## 3. 空白与异常作者

| 类型 | 条数 | 明细 |
|---|---|---|
| `author_name IS NULL` | 0 | — |
| `trim(author_name)=''` | 0 | — |
| 含阿拉伯数字 | {sum(int(r['n_suspect_rows']) for r in dig)} | 见下表 |
| 含标点（顿号/逗号） | {sum(int(r['n_suspect_rows']) for r in pun)} | 多人合署 |
| 含 `〖〗` 校记符号 | {sum(int(r['n_suspect_rows']) for r in mark)} | 曹菘〖1〗 等 |

### 3.1 数字后缀（同名消歧后缀泄漏）

{tbl(["author_name","条数","去数字后","判定"], [[r["author_name"], r["n_suspect_rows"], r["suggested_full_name"] or "—", r["verdict"]] for r in dig[:12]])}

`姚述尧2`、`刘镇2`、`李好古1` 这类写法的数字是上游「同名第二人」的编号，被当成了名字的一部分。库里同时存在 `姚述尧` 与 `姚述尧2`、`刘镇`/`刘镇1`/`刘镇2`，说明上游已经做过同音同名拆分——**但拆分是否正确无法在库内验证**（可能本来是一个人的作品被强行分到两个号上），所以一律 `MERGE_UNCERTAIN`，只把数字从显示名中剥离。

`吴氏1 / 吴氏2 / 吴氏3` 是三个不同的人，`DO_NOT_MERGE`；`曹菘〖1〗` 属于校记符号黏连（见第 3 节首表），不是数字后缀，已从本表剔除。

### 3.2 多人合署 / 编者署名

{tbl(["author_name","条数","判定"], [[r["author_name"], r["n_suspect_rows"], r["verdict"]] for r in pun])}

`王重民輯錄，劉脩業整理。` 是**整理者署名**被写进作者字段，不是作者；`趙光逢、張衮` 是联句/合撰。这类需要拆成多条 attribution，不能简单改名。

### 3.3 非人名

{tbl(["author_name","条数","判定"], [[r["author_name"], r["n_suspect_rows"], r["verdict"]] for r in np_])}

`郊廟朝會歌辭`（1,639 条）、`鼓吹曲辭`/`鼔吹曲辭`（35+44，且「鼓/鼔」异体并存）、`清商曲辭`、`昭徳凱容樂` 是**乐府类目**；`古諺`/`吳中諺`/`辰州田家諺`/`乾道民謠` 是**谚语民谣的出处标签**；`雜詩`（133 条）是**诗题**被当成作者；`柳子厚祠`（15 条）是**祠庙名**。

`author_alias` 表本身已把这批标为 `NOT_PERSON`，但 `works.author_name` 没有跟着改。

### 3.4 匿名写法未统一

| 写法 | 条数 |
|---|---|
| 佚名 | 3,974 |
| 无名氏 | 3,254 |
| 無名氏 | 747 |
| 不詳 | 731 |
| **合计** | **8,706** |

同一语义四种写法（且简繁不一）。建议统一为「佚名」，属纯书写变体，`MERGE_SAFE`。

## 4. 同名跨代

全库 **{cross_all}** 个 `author_name` 出现 >1 个 `dynasty`。前 30 名（按朝代数与条数）见 CSV。

判定逻辑：看少数派朝代是否只有 1–3 条——若是，则为**源数据朝代误标**，同一人，`MERGE_SAFE`（改 dynasty）；若两侧都有规模，则可能是同名两人，`MERGE_UNCERTAIN`。

典型：

| author_name | 朝代分布 | 判定 | 说明 |
|---|---|---|---|
| 劉禹錫 | 唐 890 / 宋 2 | MERGE_SAFE | 2 条宋诗源误收 |
| 王建 | 唐 581 / 宋 1 | MERGE_SAFE | 同上 |
| 趙蕃 | 宋 3,735 / 唐 2 | MERGE_SAFE | 同上 |
| 李中 | 唐 310 / 宋 1 | MERGE_SAFE | 同上 |
| 徐鉉 | 宋 431 / 唐 309 | MERGE_UNCERTAIN | 南唐入宋，两朝皆通，需人工定 |
| 佚名 / 無名氏 / 无名氏 | 10 / 4 / 2 朝 | DO_NOT_MERGE | 匿名者跨代属正常 |

> 需要提醒：`dynasty` 字段本身是「按所属集合先验推导」（`authors.note` 里明写「作者朝代由所属集合先验推导，未与史传核对」）。因此「唐/宋」冲突很大程度是**集合级先验**的产物，不是逐条考证的结果。

## 5. 繁简混用

`author_alias` 中有 **9,389** 条 `VARIANT_SIMP`（繁简归并）映射；其中 **{simp_pairs_all}** 对的**两种写法在 `works` 中同时真实存在**——即 `author_canonical` 已归并，但 `author_name` 从未回写。

{simp_tbl}

最严重的是 `陸游(9,269) / 陆游(144)`、`劉克莊(4,553) / 刘克庄(269)`、`蘇軾(2,811) / 苏轼(356)`、`楊萬里(4,284) / 杨万里(8)`。

后果：任何按 `author_name` 分组的统计（作者产量、风格分析、去重）都会把同一个人算成两个人。**这是全库影响面最大、修复成本最低的一类问题**——直接 `author_name = author_canonical` 即可，`MERGE_SAFE`。

## 6. 我无法确定的地方

1. **单字作者无法闭环**：全库没有任何一篇单字作者的作品在更长姓名下重出。因此 42 个单字作者里，除「张」有外部文献线索外，其余 41 个只能停在 `MERGE_UNCERTAIN`/`UNRESOLVED`。要真正确证，需要外部工具书（如《中国文学家大辞典》）或原始影印页，本环境不联网，做不了。
2. **「张」的全名**是靠《满江红·无利无名》《离亭燕》的名篇记忆判定的，属外部知识，未在库内验证；`张昪` 与 `张昇` 两种写法何者为正，也未定。
3. **同名跨代中「两侧都有规模」的那些**（如 徐鉉、李質、王偁、方澤）：没有生卒年字段，无法判断是同一人还是两个同名者。CSV 里给 `MERGE_UNCERTAIN`，不做合并。
4. **单字作者的 dynasty 也坏**，但我只审计了 name，没有逐条重判 dynasty。若要修，需要按 collection 重新推导。
5. 数字后缀（`姚述尧2`）剥离后是否与已有条目重名，需要逐个人工确认；本表只标 `MERGE_SAFE` 当 `base` 已在库内存在时（因为此时 base 与本条必然指同一人以外的第二人，情况反而更复杂），**实际这一批我标的是"先剥数字再人工判"**，请以 CSV 的 note 为准。

## 7. 附：完整 SQL

```sql
-- 字段确认
PRAGMA table_info(works);

-- 单字作者
SELECT author_name, count(*) n FROM works WHERE length(author_name)=1 GROUP BY 1 ORDER BY n DESC;

-- 候选全名
SELECT author_name,count(*) FROM works
WHERE length(author_name)>1 AND author_name LIKE '张%'
GROUP BY 1 ORDER BY 2 DESC LIMIT 4;

-- 同文重出（逐条）
SELECT work_id,author_name,title_norm FROM works
WHERE length(author_name)>1 AND text_norm LIKE '%<前14字>%' LIMIT 2;

-- 空白/异常
SELECT sum(author_name IS NULL) null_n,
       sum(trim(author_name)='') empty_n,
       sum(author_name GLOB '*[0-9]*') digit_n,
       sum(author_name GLOB '*[，。、；：！？（）]*') punct_n
FROM works;

-- 匿名写法
SELECT author_name,count(*) FROM works
WHERE author_name IN ('佚名','無名氏','无名氏','闕名','阙名','不詳','不详','未詳','未详')
GROUP BY 1 ORDER BY 2 DESC;

-- 同名跨代
SELECT author_name, count(DISTINCT dynasty) d, group_concat(DISTINCT dynasty), count(*)
FROM works GROUP BY 1 HAVING d>1 ORDER BY d DESC, 4 DESC LIMIT 30;

-- 繁简并存
SELECT a.raw_name,a.canonical,
 (SELECT count(*) FROM works w WHERE w.author_name=a.raw_name),
 (SELECT count(*) FROM works w WHERE w.author_name=a.canonical)
FROM author_alias a WHERE a.kind='VARIANT_SIMP'
 AND (SELECT count(*) FROM works w WHERE w.author_name=a.raw_name)>0
 AND (SELECT count(*) FROM works w WHERE w.author_name=a.canonical)>0
ORDER BY 3 DESC;
```
"""
open(f"{OUT}/WORKS_AUTHOR_NAME_AUDIT.md", "w").write(md)
print("written", len(md), "chars")
con.close()
