# 作者身份模型设计（C4）

本轮（R2-13）只做复核与证据登记，**不动数据库**。本文说明为什么「人物身份」必须与「显示名/别名」分表，给出建议结构与合并门槛，供后续落地轮次执行。

---

## 1. 现状：身份与名字被压在同一列

`works.author_name`（20,809 个不同取值）、`authors.name`（20,809 行，与前者一一对应）、`author_alias.canonical`（20,809 行）三处都把「名字字符串」当成「人物主键」：

```sql
SELECT count(*) FROM works;                 -- 375,399
SELECT count(DISTINCT author_name) FROM works;      -- 20,809
SELECT count(DISTINCT author_canonical) FROM works; -- 20,327
```

20,809 → 20,327 的差值说明有 482 个名字被字符串规则并到了别的名字上，但：

```sql
SELECT kind, count(*) FROM author_alias GROUP BY 1;
-- SAME 11,382 / VARIANT_SIMP 9,389 / NOT_PERSON 18 / TEMPLE_NAME 11 / VARIANT_GLYPH 6 / STYLE_NAME 3
SELECT auto, count(*) FROM author_alias GROUP BY 1;
-- auto=1: 20,809   （全部为机器生成，无一条人工确认）
```

即：**归并关系全部由 `opencc` 一类的字符转换产生，没有任何一条带「凭什么说这是同一个人」的证据**。这条链一旦出错，下游所有按作者聚合的统计都会跟着错，而且错得没有痕迹——因为 canonical 是字符串，不是可追溯的 id。

本轮复核已经暴露了这条链的三种失效：

| 失效类型 | 实例 | 后果 |
|---|---|---|
| 该合没合 | `曹勋`(183) 与 `曹勛`(1326) 是两个 canonical；`晁冲之`(16) 与 `晁沖之`(171) 同 | 同一位作者被拆成两条，作品集被腰斩 |
| 不该合会误合 | `张翰` 晋 16 条 vs 清 1 条、`王铎` 唐 5 条 vs 清 8 条 | 若按字符规则硬并，会把两个不同朝代的人并成一个 |
| 名字根本不是人 | `郊廟朝會歌辭` 1,639 条、`雜詩` 133 条、`鼓吹曲辭` 35 条 | 类目/诗题被当成作者，进 canonical 后永远洗不掉 |

因此问题不在「合并规则不够聪明」，而在**模型里没有地方存「身份」和「名字」的区别，也没有地方存证据**。

---

## 2. 建议结构

三层，职责互不重叠：**身份**是实体，**名字**是属性，**状态**是证据强度。

### 2.1 `author_identity`（人物身份，一行 = 一个人）

```sql
CREATE TABLE author_identity (
  identity_id     TEXT PRIMARY KEY,      -- 稳定 id，建议 'AI-' || 内部序号，永不复用
  display_name    TEXT NOT NULL,         -- 对外显示用的规范名（简体，姓名优先于字号）
  surname         TEXT,
  given_name      TEXT,
  dynasty         TEXT,                  -- 规范化朝代枚举：先秦/汉魏/魏晋南北朝/隋/唐/五代/宋/金/元/明/清
  era_label       TEXT,                  -- 原始年号或细分时代（如「南唐」「东汉末」），保留原貌
  floruit_year    INTEGER,               -- 活动年代中点，用于跨代判断
  birth_year      INTEGER,
  death_year      INTEGER,
  identity_status TEXT NOT NULL,         -- 见 2.3
  evidence_grade  TEXT NOT NULL,         -- A/B/C/D，见第 3 节
  note            TEXT
);
```

要点：

- `display_name` 是**展示字段**，允许后续修订而不影响 `identity_id`。
- 朝代单独成列且用枚举，`era_label` 只存原貌。本轮已发现 `works.dynasty` 与 `works.collection` 近乎一一对应（见 LOGS），说明 dynasty 很可能是从总集推出来的，不是独立证据；将来必须能标出「哪个朝代是推的、哪个是有传可考的」。
- 一个人允许 `floruit_year` 为空；不允许 `identity_status` 为空。

### 2.2 `author_name_variant`（显示名 / 别名，一行 = 一种写法）

```sql
CREATE TABLE author_name_variant (
  variant_id   TEXT PRIMARY KEY,
  identity_id  TEXT NOT NULL REFERENCES author_identity(identity_id),
  raw_name     TEXT NOT NULL,          -- 库内实际出现的字符串，原样保存
  variant_type TEXT NOT NULL,          -- 见下
  script       TEXT,                   -- simp / trad / mixed / glyph
  is_display   INTEGER NOT NULL DEFAULT 0,  -- 1 = 该 identity 的默认显示名
  evidence     TEXT,                   -- 凭什么认为它指这个人
  source_ref   TEXT,                   -- 证据出处（书名+卷次+页码/条目号）
  auto         INTEGER NOT NULL DEFAULT 0,
  UNIQUE(raw_name)                     -- 一个写法只允许挂一个身份；歧义写法需拆 identity
);
```

`variant_type` 建议取值（本轮实测都在库里出现过）：

| variant_type | 含义 | 本轮实例 |
|---|---|---|
| `PRIMARY` | 姓名本体 | 苏轼 |
| `TRAD_SIMP` | 繁简/异体对应 | 蘇軾→苏轼；曹勛→曹勋；张榘→张矩 |
| `STYLE_NAME` | 字号 | 陶淵明→陶潜、張茂先→张华、陳思王植→曹植 |
| `TEMPLE_NAME` | 帝号/封号/谥号 | 昭明太子→萧统、明皇帝→李隆基 |
| `COURTESY_WITH_OFFICE` | 姓+官衔+名（金元诗常见） | 蔡太常珪、髙内翰士談、馮内翰延登 |
| `ALIAS_KNOWN` | 文献可考的异名 | 于鄴＝于武陵（本轮抽检文本重合证实） |
| `OCR_LOSS` | 缺字/残字 | `□`、`洽`、`含` |
| `WRAPPED` | 标注残留（`==…==`） | 287 个 `==姓名==` |
| `TITLE_POLLUTION` | 作品名/剧名黏在作者名后 | 高明《蔡伯喈琵琶记》 |
| `NOT_A_PERSON` | 类目/谚谣/祠庙 | 郊廟朝會歌辭、古諺、柳子厚祠 |

**关于 `TRAD_SIMP` 的实测警告**：本轮 476 对繁简配对中，455 对的两侧来自**不同总集**，其中 343 对是 `songci ↔ songshi`，且 340 对的简体形固定落在宋词一侧。也就是说这不是「随机字形差异」，而是《全宋词》按简体入库、《全宋诗》按繁体入库造成的**语料规范冲突**。因此 `TRAD_SIMP` 只能作为「候选提示」，绝不能作为合并依据；每一对都必须另有身份证据（第 3 节门槛）。

`UNIQUE(raw_name)` 是关键约束：它把「一个写法只能属于一个人」变成数据库层面的硬规则，歧义写法（如 `张翰`）必须建两条 identity 才能入库，从结构上防止误并。

### 2.3 `identity_status`（证据状态，驱动能不能合并）

```
CONFIRMED        有 ≥2 条独立证据（如文本重合 + 史传），可合并
PROBABLE         有 1 条强证据 + 朝代一致，可合并但需标注
CANDIDATE        只有字符/朝代层面的弱证据，禁止合并，只登记
UNRESOLVED       证据冲突或不足，禁止合并
NOT_A_PERSON     非人名，只能重挂到总集/佚名，不能进 identity
```

对应关系：**只有 `CONFIRMED` / `PROBABLE` 允许写 `works.author_identity_id`；`CANDIDATE` 及以下一律保持原样。**

### 2.4 `works` 侧改动（建议，不在本轮执行）

```sql
ALTER TABLE works ADD COLUMN author_identity_id TEXT;   -- 新列，先全空
ALTER TABLE works ADD COLUMN identity_confidence TEXT;   -- 与 identity_status 同名枚举
```

`works.author_canonical` 保留为「历史字段」，只读，不再写入。不要在原列上反复刷值——本轮已经证明，字符串列的每次批量重写都无法回滚、无法审计。

---

## 3. 合并的证据门槛（至少满足三条）

任何一次「A 名 = B 名」的合并，必须同时满足下列**至少三条**，且证据要写进 `author_name_variant.evidence`，不允许只写「繁简归并」：

1. **作品文本重合**
   同一 `text_norm` 前 30 字（或全文）在两侧名下出现 ≥1 条。本轮 33 对靠这一条拿到 `SAME_PERSON_CONFIRMED`，例如 `顾敻/顧敻` 13 条、`牛峤/牛嶠` 13 条、`韦庄/韋莊` 22 条。
   反向用法：`于鄴` 与 `于武陵` 有 4 首文本完全相同，一次抽检就确认了这对库内尚未登记的别名。

2. **朝代一致（且不是从 collection 反推的）**
   `dynasty` 相同，或属于相邻朝代（唐—五代、五代—宋、宋—金、宋—元、元—明、明—清，视为跨代/遗民，不构成互斥）。本轮 370 对靠「朝代一致」拿到 `SAME_PERSON_SUPPORTED`。
   **注意**：若两侧朝代互斥且都不是边界代（如 唐 vs 清），即使字符完全相同也**不得合并**——本轮 7 对判为 `DISTINCT_PERSON`。

3. **来源书一致，或有史传依据**
   两侧作品出自同一 `collection`/`source_id`，或能在史传、总集小传、作者索引中找到「某，字某，某朝人」的对应。**这是目前唯一能压过字符规则的外部证据，也是本轮所有 `UNRESOLVED` 最缺的东西。**

4. **命名理据可解释**（辅助条件，不能单独成立）
   繁简/异体对应关系必须逐字可解释，且能说明为什么不是同名异人。例如 `张榘/张矩`、`曹勛/曹勋` 属异体；而 `张翰`（晋）与 `张翰`（清）字形全同却不是同一人，说明「字形相同」本身零证据价值。

5. **不做链式传递**
   A=B、B=C 不得自动推出 A=C，除非 A 与 C 之间另有第 1–3 条证据。字符转换天然可传递，一旦允许传递，误差会按连通分量放大。

---

## 4. 本轮为什么不执行任何合并

即便已经有 33 对 `SAME_PERSON_CONFIRMED`，本轮仍然零写入，理由：

1. **没有 id 可写**。现有模型只有字符串 canonical，写进去就是又一次不可审计的覆盖；本轮的产出是「候选表」，不是「结果表」。
2. **证据只覆盖了 33/476 对**。370 对 `SAME_PERSON_SUPPORTED` 只有朝代与字符两条，按第 3 节门槛不达标；66 对 `UNRESOLVED` 连朝代都冲突。按比例硬并等于用 7% 的证据去改 93% 的数据。
3. **66 对 `UNRESOLVED` 的少数侧只有 1–2 条作品**。这类样本无法区分「同名异人」与「朝代误标」，本轮选择记为未决而不是猜（`DISTINCT_PERSON` 只给了两侧都 ≥3 条的 7 对）。
4. **21 对 canonical 尚未统一**（曹勋/曹勛、晁冲之/晁沖之、张景修/張脩之 等）。这说明 alias 表自身的转换也不完整——用一张自身有漏的表去回写 works，只会把错误固化。
5. **非人名与截断尚未处置**。`郊廟朝會歌辭` 1,639 条若先进 identity，再清洗就要动 identity 主键；必须先定 `NOT_A_PERSON`，再谈人物合并。
6. **不可逆性**。works 是 375,399 条的主表，任何 canonical 批量重写都没有事务级审计表配套；本轮不具备回滚条件。

---

## 5. 建议的落地顺序（供后续轮次）

1. 建 `author_identity` / `author_name_variant` 两表，**只迁不并**：20,809 个 raw_name 各自建一条 identity（`identity_status=UNRESOLVED`，`evidence_grade=D`），保证 id 稳定。
2. 把 R2-13 的 `AUTHORS_IDENTITY_MAPPING_R2_13.csv` 逐条导入 `author_name_variant`，`status` 全部按 `CANDIDATE` 落库，不写 `works`。
3. 只对 `CONFIRMED`（33 对）执行 identity 合并，且保留 `merge_log`（from_identity, to_identity, evidence, operator, ts）。
4. 非人名 63 个写法先挂 `NOT_A_PERSON`，走「重挂总集/佚名」流程，与人物合并解耦。
5. 再补外部证据（史传、总集小传、人名权威库），把 `SAME_PERSON_SUPPORTED` 逐批升到 `PROBABLE`。
