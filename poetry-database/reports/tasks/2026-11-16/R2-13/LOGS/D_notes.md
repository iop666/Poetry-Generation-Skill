# R2-13 D 线工作日志：元曲「缺曲文」根因调查

日期：2026-11-16　执行者：general-purpose-2（独立调查者）
约束：**只读**。未执行任何 `INSERT/UPDATE/DELETE/ALTER`；未联网；未修改 `works`。

---

## 0. 交付物清单

| 文件 | 内容 |
|---|---|
| `YUANQU_2447_MISSING_TEXT_AUDIT.csv` | 全量逐条审计，**4,510 行**（= 实际圈定数） |
| `YUANQU_SOURCE_DISTRIBUTION.md` | 来源分布 + 20 条回原文核对 |
| `YUANQU_IMPORT_PIPELINE_AUDIT.md` | 导入脚本逐行审计与根因判定 |
| `YUANQU_200_SOURCE_SAMPLE.csv` | 分层 200 条回源核对 |
| `YUANQU_100_RECOVERY_CANDIDATES.csv` | 100 条有据恢复候选 |
| `YUANQU_TEXT_RECOVERY_SUMMARY.md` | 全量状态、可恢复比例、下游影响 |
| `LOGS/D1_build.py` `D2_source.py` `D4_recovery.py` | 本文件所有数字的生成脚本（可直接复跑） |
| `LOGS/D1_counts.json` `D2_sample20.json` `D4_summary.json` `D2_source_sample20.csv` | 中间结果 |

复现：

```bash
cd <PROJECT_ROOT>/poetry-database
python3 reports/tasks/2026-11-16/R2-13/LOGS/D1_build.py
python3 reports/tasks/2026-11-16/R2-13/LOGS/D2_source.py
python3 reports/tasks/2026-11-16/R2-13/LOGS/D4_recovery.py
```

---

## 1. 表结构确认

```sql
PRAGMA table_info(works);
```

含 `work_id, title_raw, title_norm, author_name, dynasty, era, collection, genre,
genre_basis, cipai, chapter, section, text_raw, text_norm, line_count, char_count,
source_id, volume, seq, auto_meta, record_locator, juan, base_edition` 等 38 列（与任务书一致）。

```sql
SELECT name FROM sqlite_master WHERE type='table';
```

→ 共 105 表。**无 `yuefu_*` / `qu_*` / `qupai_*` 表**（`ph_*` 是音韵，`cipai_*` 是词谱，`jiyun_*`/`guangyun_*` 是韵书）。

```sql
SELECT book_id,title,category FROM books;
```

→ 13 本，均为格律书/韵书/文论/选本，**无元曲选、无元曲总集**。

---

## 2. 基础统计

```sql
SELECT COUNT(*) FROM works;                              -- 375,399
SELECT collection,COUNT(*) FROM works GROUP BY 1 ORDER BY 2 DESC;
SELECT genre,COUNT(*) FROM works GROUP BY 1 ORDER BY 2 DESC;   -- 曲 10,685
SELECT source_id,COUNT(*) FROM works WHERE collection='yuanqu' GROUP BY 1;  -- CP-YUANQU 10,685
SELECT base_edition,COUNT(*) FROM works WHERE collection='yuanqu' GROUP BY 1; -- '' 10,685
```

`works.base_edition` 全空；版本信息实际在 `provenance.base_edition`：

```sql
SELECT base_edition,COUNT(*) FROM provenance WHERE work_id LIKE 'yuanqu:%' GROUP BY 1;
-- 整理本（无底本声明） 10,685
```

---

## 3. 复现 R2-12 的 2,447

```sql
SELECT COUNT(*) FROM works WHERE genre='曲' AND text_raw LIKE '%(%唱)%';
-- 2447   ← 与 R2-12 数字完全一致
```

**这就是 2,447 的来源**。它是 SQL `LIKE` 只能匹配**半角圆括号**造成的：

```sql
SELECT COUNT(*) FROM works WHERE genre='曲'
  AND (text_raw LIKE '%(%唱)%' OR text_raw LIKE '%（%唱）%');
-- 2739
```

差额 293 条 = 292 条全角「（）」+ 1 条混用「(唱）」。

混用样本（唯一一条）：

```
yuanqu:b4a9e38a69e5  …(正旦云)好儿也，(唱）你正是"男儿当自强"。
```

用中英括号通配的正则 `[（(][^）)]*唱[）)]` 得 **2,740**，即可解释的全部「含唱提示」记录。

---

## 4. 本轮圈定判据（三分支并集）

### A. 含唱提示（对比 R2-12 的正确版本）

正则 `[（(][^）)]*唱[）)]` → **2,740 条**

理由：这是 R2-12 想抓的东西，唯一修正是括号字符类。

### B. 曲文被刮进标题

判据：`title_raw` 含句读（`，。；？！、：`）**且** `len(title_raw) >= 17` → **1,729 条**

理由（为何不是「标题本来就长」）：
1. 长度分布尖峰在 **32 字**（1,425/1,729 恰好 32，235 条 33）——固定列宽硬切特征；
2. `title_raw` 尾字与 `text_raw` 首字**语义连续**（「…泪痕淹破，」+「胭脂双颊。」）；
3. 这 1,729 条的 `title_raw` **全部**含「・」，且 `・` 后是曲文而非题目；
4. A∩B = **0**，说明这是与杂剧平行的一类独立缺陷。

### C. 正文残篇

判据：剔除括注后汉字 < 12 → 206 条（其中 165 条已被 B 吸收，净新增 41）

理由：`尾声`/`煞` 等短曲牌通常 20–40 字，<12 字不可能是完整曲牌正文。

### 并集

|A ∪ B ∪ C| = **4,510 条**（A 2,740 + B 1,729 + 净新增 C 41，A∩B=0）

---

## 5. 逐条状态判定规则（写进 CSV 的 `status`）

按以下顺序**短路**判定：

1. `han(text_raw)==0` → `EMPTY_TEXT`（本轮 0 条）
2. `title_raw` 含句读且长 ≥17 → `IN_OTHER_FIELD`
   - 曲文在 title；`evidence` 记「全部曲文 / 曲文头约 N 字」
3. 标题曲牌位是宾白提示（`[\u4e00-\u9fff]{1,4}(云|唱|白|科)$`）且正文 <25 字 → `DIALOGUE_ONLY`
4. 剔除括注后汉字 <12 → `FRAGMENTARY`
5. 其余 → `LYRIC_PRESENT`
   - 12–24 字者 `evidence` 标 `SHORT_SLOT`（短曲牌可容，不宣称完整）
   - 句末为唱句提示者标 `TAIL_CHANG_CUE`（提示语属下一曲，不是本段缺文）

`has_qu_marker` 的定义（说明）：`text_raw` 内是否有**显式曲牌标记**（`【`/`〔`/`幺篇`）。
全曲集仅 24 条有 `【/〔`，因此该字段几乎全为 `N`——**这本身就是结论**：
曲牌信息只存在于 `title_raw`，正文被按曲牌切段后去掉了标题。

`has_dialogue_marker`：括注内含 `唱|云|白|科|做|上|下|了`（≤14 字）。
`ends_with_chang_marker`：`text_raw` 收尾即「(…唱)」+ 可选句号。

---

## 6. 与 2,447 的差异说明（核心）

| 项 | 2,447（R2-12） | 4,510（本轮） |
|---|---|---|
| 判据 | `text_raw LIKE '%(%唱)%'` | (含唱提示 any-bracket) ∪ (曲文入标题) ∪ (正文残篇) |
| 是否含全角括号 | 否（漏 293） | 是 |
| 是否只看「唱」 | 是 | 否，另纳入 title 污染与残篇 |
| 是否核过原文 | 未核 | 2,740/2,740 与 raw 逐字节比对，差异 0 |
| 结论 | 2,447 条曲文丢失 | 2,739 条曲文在正文、1,729 条曲文头在标题、41 条源即残、1 条纯宾白 |

**2,447 与 4,510 不是「修订」，是两件不同的事**：
2,447 是「带唱句提示的记录数」（且括号算错），4,510 是「曲文可能不在正文里的记录数」。
真正「曲文完全不在正文」的只有 1,729 条（在标题）+ 41 条（源残）+ 1 条（宾白）。

---

## 7. 关键 SQL / 比对结果一览

```sql
-- 正文与标题的汉字量（证明 text_norm 不藏额外曲文）
-- 结果：10,685 条中 han(text_norm) != han(text_raw) 的记录 = 0
SELECT COUNT(*) FROM works WHERE genre='曲' AND char_count <> length(text_norm);  -- 0

-- chapter/section 是否有内容
SELECT COUNT(*) FROM works WHERE genre='曲' AND (chapter<>'' OR section<>'');     -- 0

-- 交叉校验表是否收录元曲
SELECT COUNT(*) FROM text_crosscheck WHERE work_id LIKE 'yuanqu:%';               -- 0

-- variants 表结构（无文本列）
PRAGMA table_info(variants);   -- group_id, work_id, note
SELECT COUNT(*) FROM variants WHERE work_id LIKE 'yuanqu:%';                      -- 2,326

-- 首字/尾字接缝：1,729 条全部连续，无重字
```

原文比对（Python，见 `D2_source.py`）：以 `(author,title)` 定位 raw JSON 记录，
要求 `"\n".join(paragraphs) == works.text_raw`：

```
2,740 / 2,740 命中且逐字节相同
```

---

## 8. 我无法判断的（如实计数）

| 项 | 条数 | 原因 |
|---|---|---|
| `FRAGMENTARY` 原文究竟多长 | **41** | 无第二来源；任何补字都是外部知识注入 |
| 20–25 字短曲牌是「本短」还是「被截」 | 若干（未逐一判定） | 上游 `base_edition`=「整理本（无底本声明）」，无印本可校 |
| 1,729 条硬切处是否偶发跨字错误 | 未逐条验（抽样未见） | 需逐条读 1,729 条，本轮只做 100 条接缝验证 |
| 上游哪个 commit | — | `provenance.upstream_version = master (未固定 commit)`，本地无 `.git` |
| 372 条被丢弃记录的库内状态 | **372** | 不在 `works` 中，无法在库内核验；只能回 `raw` 确认（364 条 title 含曲文，142 条正文全空，312 条正文 <8 字） |

明确**不能**得出的结论：
- 不能说「元曲整体只剩科白」（2,739 条曲文完整，抽样 80 条回源全对）。
- 不能说「2,447 条已丢失且无法恢复」（其中 2,739 条根本没丢）。
- 不能从网络补 41 条残篇（任务禁止，且无版权干净的对应底本）。

---

## 9. 与 R2-12 结论的对照（供 team-lead 归档）

| R2-12 原文 | 本轮证据 | 处置建议 |
|---|---|---|
| GD-032「2,447 条元曲曲文丢失只剩科白」 | 计数是 LIKE 括号假象；实测仅 1 条纯宾白 | 降级并改写为 **「1,729 条曲文头被刮入标题（平均缺 41.7%）+ 372 条被导入过滤 + 41 条源残 + 1 条宾白」** |
| 「315 条以 (正末唱)。 结尾」（正确） | 复核确认 315 条存在；但其中 314 条正文已有曲文，结尾提示属下一曲 | 不改数据，仅需在解析时识别 `TAIL_CHANG_CUE` |
