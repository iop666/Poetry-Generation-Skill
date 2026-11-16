# AUTHOR_IDENTITY_SCHEMA_R2_14 — 作者身份模型（R2-14 定稿）

工作目录：`<PROJECT_ROOT>/poetry-database`
本轮只读：**未修改 `works` / `authors` / `author_alias` 任何一行**，未建表，零合并。
`authors` 仍 20,809 行 = `works` 不同 `author_name` 数（20,809）——它不是人物库，
是按作品字段反推出来的名字清单。

---

## 1 四条硬约束（本轮实测，设计必须先服从）

### 1.1 朝代是总集的影子，不能当证据

```sql
SELECT note, count(*) FROM authors GROUP BY 1;
-- 作者朝代由所属集合先验推导，未与史传核对 | 20809
```

20,809 行 `note` 完全相同，无一条经史传核对。交叉验证 18 个 `collection` 与 `dynasty`
近乎一一对应（songshi→宋 252,884、tang→唐 55,308、wanqing→清 19,864、songci→宋 18,794…）。

**可以确定的两件事**：

1. **不是史传值**：20,809 行 `note` 同一句"由所属集合先验推导，未与史传核对"，零例外。
2. **也不是该行作品的多数票**。反例：

| 作者 | authors.dynasty | 其作品朝代分布 |
|---|---|---|
| 王珪 | **唐** | 宋 430 / 唐 2 |
| 王融 | **唐** | 魏晋南北朝 62 / 唐 1 |
| 佚名 | 先秦 | 魏晋南北朝 1,798 / 未定 561 / 先秦 418 |

**只能部分复现的生成规律**：20,809 行中有 20,270 行（97.4%）等于"`collections` 字符串按字典序取首位的那个总集的朝代"
（如 `songci,yuanqu`→songci→宋，`tang,tang300`→tang→唐）。但**另有 539 行连这条也不符**，
其中包括上表的王珪（`songshi,tang`，字典序首为 songshi 应得宋，实际得唐）与王融（`gushiji,tang`）。

所以准确的表述是：**`authors.dynasty` 与 `collections` 有强相关（97.4% 可用"字典序首集"复现），
但既不是史传值、也不是作品多数，且 5.2% 的行连这条经验规则都不服从——生成逻辑不可完全复原。**
因此它不能用于"某朝代有多少作者"这类统计，必须逐作品取 `works.dynasty`。

**后果**：R2-13 的 370 对 `SAME_PERSON_SUPPORTED` 靠"朝代一致"支撑，而朝代 = 集子，
等于用集子证明集子。本轮把其中 364 对降为 `NAME_VARIANT_ONLY`。

### 1.2 476 对里混着同名异人，t2s 分组产出的是"字形对"不是"人"

73 对（7 `DISTINCT_PERSON` + 66 `UNRESOLVED`）两侧时代互斥（唐/宋 vs 清）。
原因是晚清诗语料全简体、宋诗/全唐诗语料全繁体，"清代的张埴"与"宋代的張埴"被折叠成一对。

```sql
SELECT author_name, dynasty, count(*) FROM works WHERE author_name IN ('张埴','張埴') GROUP BY 1,2;
-- 张埴|清|2  张埴|宋|1  張埴|宋|133
```

### 1.3 `author_name` 本身已混人，问题在 alias 之前

上面的 `张埴` 一个 raw_name 内同时含 宋词 1 条 + 清诗 2 条；`李师中` 同构。
所以"一个名字 = 一个人"这个前提在 raw 层就不成立。

### 1.4 `author_id` 是名字的哈希，不是身份

```python
author_id == 'A:' + sha1(name)[:10]        # 20,809 行全部成立，零例外
SELECT count(DISTINCT author_id) FROM works;  -- 20,809
```

同名同 id，跨总集自动合并。所以 `authors` 不是人物库，是 `works.author_name` 的哈希索引；
`author_id` 里没有任何身份判断，**它只是名字的另一种写法**。任何"按 author_id 聚合作者"
的统计实际都是"按字符串聚合"。新模型因此另立 `AE-` 前缀实体 id，不复用 `A:` 哈希。

---

## 2 三层结构

| 层 | 表 | 一行 = | 回答的问题 |
|---|---|---|---|
| 身份 | `author_entity` | 一个可识别的人 | 是谁 |
| 名字 | `author_name_variant` | 一种写法挂在一个身份上 | 怎么写 |
| 角色 | `collection_role` | 一个"非人"署名 | 不是人时它是什么 |

### 2.1 `author_entity`

```sql
CREATE TABLE author_entity (
  entity_id        TEXT PRIMARY KEY,       -- 'AE-' || 序号，永不复用
  display_name     TEXT NOT NULL,
  surname          TEXT,
  given_name       TEXT,
  dynasty_verified TEXT,                   -- 有史传/小传才填
  dynasty_derived  TEXT,                   -- 由 collection 推出，仅供检索
  era_label        TEXT,                   -- 原貌年号（"南唐""东汉末"）
  floruit_year     INTEGER, birth_year INTEGER, death_year INTEGER,
  identity_status  TEXT NOT NULL CHECK (identity_status IN
                     ('VERIFIED','PROBABLE','CANDIDATE','UNRESOLVED')),
  evidence_grade   TEXT NOT NULL CHECK (evidence_grade IN ('A','B','C','D')),
  note             TEXT
);
```

`dynasty_verified` 与 `dynasty_derived` **必须分列**：任何把后者写进证据的操作按缺陷处理
（R2-13 的 370 对就是这么错的）。

### 2.2 `author_name_variant`

```sql
CREATE TABLE author_name_variant (
  variant_id   TEXT PRIMARY KEY,           -- 'NV-' || 序号
  entity_id    TEXT NOT NULL REFERENCES author_entity(entity_id),
  raw_name     TEXT NOT NULL,              -- 库内原字符串（含 ==…==、□）
  variant_type TEXT NOT NULL CHECK (variant_type IN
                 ('PRIMARY','TRAD_SIMP','GLYPH','STYLE_NAME','TEMPLE_NAME',
                  'COURTESY_WITH_OFFICE','ALIAS_KNOWN','OCR_LOSS','WRAPPED',
                  'TITLE_POLLUTION','MIXED_SCRIPT','KINSHIP_PLACEHOLDER')),
  script       TEXT CHECK (script IN ('simp','trad','mixed','glyph')),
  is_display   INTEGER NOT NULL DEFAULT 0,
  evidence     TEXT,                       -- 凭什么认为它指这个实体
  source_ref   TEXT,                       -- 书名 + 卷次 + 页码/条目号
  auto         INTEGER NOT NULL DEFAULT 0,
  UNIQUE(raw_name, entity_id)              -- 同一写法可挂多个实体（同名异人）
);
```

相对 R2-13 的三个修正：

1. 唯一键由 `UNIQUE(raw_name)` 改为 `UNIQUE(raw_name, entity_id)` —— `张埴` 必须能挂两条。
2. 新增 `MIXED_SCRIPT`：整串只转换了一部分字（`歐陽炯/欧陽炯`、`曹勋/曹勛`、`晁冲之/晁沖之`、
   `張鎡/张鎡`、`劉義/劉义`）。476 对中有 **35 对**属此类，R2-13 无此档，只能塞进 `TRAD_SIMP`。
3. 新增 `KINSHIP_PLACEHOLDER`：`张氏/刘氏/苏氏/杨氏/卢氏` 等（本轮 9 对），
   是"某姓之女"的通称，同名者必多人，不能当一个人。

### 2.3 `collection_role`

```sql
CREATE TABLE collection_role (
  role_id      TEXT PRIMARY KEY,           -- 'CR-' || 序号
  raw_name     TEXT NOT NULL UNIQUE,
  role_type    TEXT NOT NULL CHECK (role_type IN
                 ('ANONYMOUS','COLLECTION','INSTITUTIONAL','UNKNOWN')),
  target_collection TEXT,                  -- 归属总集（COLLECTION 必填）
  section_label     TEXT,                  -- 类目名原文（郊廟朝會歌辭）
  n_works      INTEGER,
  evidence     TEXT, source_ref TEXT
);
```

---

## 3 允许的四类"非个人作者"

| role_type | 定义 | 本轮落点（76 个 raw_name） |
|---|---|---|
| `ANONYMOUS` | 明确的佚名占位 | 佚名 3,974 / 无名氏 3,254 / 無名氏 747 / 不詳 731 / **缺名 39** / 無名僧 / 無名鬼 / 南唐失名僧 等 |
| `COLLECTION` | 总集名、类目名、乐府旧题、集名 | 郊廟朝會歌辭 1,639 / 雜詩 133 / 鼔吹曲辭 44 / 昭徳凱容樂 43 / 鼓吹曲辭 35 / 月重輪行 27 / **暮雨谣三叠 6** / **清江道中 2** / **西湖竹枝詞 2** 等 |
| `INSTITUTIONAL` | 乐署/教坊/翰林院等机构 | 本轮 **0 例**（郊庙乐章以类目名出现，归 COLLECTION）。类型保留，防止将来并入人 |
| `UNKNOWN` | 无法归类且非人名 | 《靖康小雅》作者 14、上元夫人 3 |

**边界 1：姓+官+名是人，不是非人。** `蔡太常珪`(44)、`髙内翰士談`(28)、`馮内翰延登`(16)、
`李承㫖晏`(5)、`王先生予可`(5)、`孟内翰宗獻`(4)、`趙内翰可`(3) 共 7 个 / 105 条，
用 `COURTESY_WITH_OFFICE`，不得按"含官职"判成非人。

**边界 2：人名+剧名黏连是人，不是非人。** `高明《蔡伯喈琵琶记》`(377) 等 8 种 / 1,966 条，
用 `TITLE_POLLUTION` 记一条 variant 并切出干净名，**不得**放进 `collection_role`。
R2-13 把它们标成 `PERSON`（非人名表内）是对的，但应显式说明它们不进 `collection_role`。

**边界 3：`郊廟朝會歌辭` 不是被谁改出来的。** 1,639 条在原始 JSON 中逐条核对，
`author` 原值即类目名，标题多重集与 `works` 完全一致（multiset equal = True），零差异。
所以不能"找一位编者顶上"，只能进 `collection_role`。

---

## 4 合并门槛

| 级别 | 定义 | 本库可得性 |
|---|---|---|
| **A** | 史传/总集小传/别集题署明载"某，字某，某朝人" | 全库 **20 条**（`author_alias` 帝号 11 / 字号 3 / 异体 6，含《宋史·后妃传》《李善注》），但**均不覆盖 476 对** |
| **B** | 总集编者注/别集目录/作者索引，可定位卷次条目 | **0 条**（无编者注字段） |
| **C** | 同一作品在两个相互独立的总集分别署两种写法 | 30 对 |
| **D** | 仅字形对应；或仅 collection 推出的朝代 | 366 对 |

注意：A 级证据在库里并非为零，而是**落点错位**——有证据的 20 条都是"异名"（字号/帝号），
需要判断的 476 对都是"同形"（繁简/异体），两个集合不相交。这正是为什么不能拿 alias 表当依据。

```
VERIFIED   = A，或 (B 且 C)
PROBABLE   = B 单独，或 (C 且条数 ≥5 且无第三作者争夺)
CANDIDATE  = 仅 C（条数<5 或有第三作者争夺），或 C+D
UNRESOLVED = 仅 D；或证据冲突（时代互斥、样本过少）
```

**四条硬禁止**
1. `dynasty_derived` 不得进入任何合并证据。
2. `TRAD_SIMP`/`GLYPH`/`MIXED_SCRIPT` 单独存在时不得合并。
3. 不做链式传递（A=B、B=C 不推出 A=C）。
4. raw_name 已确认混人时，先拆 works，再谈合并。

---

## 5 本轮执行结果

476 对全部重审：

| revised_verdict | 对数 | 说明 |
|---|---|---|
| `SAME_PERSON_VERIFIED` | **0** | 无一对满足 A 或 B |
| `SAME_PERSON_SUPPORTED` | **30** | 仅靠跨总集同文（C 级），无文献证据 |
| `NAME_VARIANT_ONLY` | **366** | 无文本重合，朝代又是推导值，只剩字形 |
| `DISTINCT_PERSON` | **5** | 两侧各 ≥3 条且时代互斥（吴栻/吴山/王铎/徐延寿/张元） |
| `UNRESOLVED` | **75** | 含 66 对原判 + 9 对（2 对侧内混人、1 对佚名、6 对样本过少/某氏） |

R2-13 的 33 条 `SAME_PERSON_CONFIRMED` **全部降级**：
- 30 条 → `SAME_PERSON_SUPPORTED`（文本重合成立，但只是同一首诗被两个总集各收一次，不构成身份证据）
- 2 条 → `NAME_VARIANT_ONLY`（`王谌/王諶` 的重合文本同时被薛嵎署名；`劉皂/劉皁` 同时被齊澣署名）
- 1 条 → `UNRESOLVED`（`无名氏/無名氏` 两侧都是佚名占位，根本不是人）

---

## 6 为什么不合并（零合并的理由）

1. **没有 id 可写**：现有模型只有字符串 canonical，写进去就是又一次不可审计的覆盖。
2. **0 对达 A/B 级**：33 对"CONFIRMED"的证据全是跨总集同文，按门槛只到 C。
3. **朝代是推导值**：任何以"朝代一致"为据的合并都在复制 `collection` 的分类。
4. **476 里混着同名异人**：t2s 分组不区分字形与人，贸然合并会把清代某人与宋代某人并成一个。
5. **不可逆**：`works` 375,399 条主表没有事务级审计表，无回滚条件。

---

## 7 落地顺序（五步，均可回滚）

1. 建三表；20,809 个 raw_name 各建一条 entity（`UNRESOLVED`，`evidence_grade='D'`），只迁不并。
2. **先**把 76 个非人名迁入 `collection_role` —— 否则 `郊廟朝會歌辭` 会先以"人"的身份进 entity，再清洗就要动主键。
3. 导入 C 级及以上 variant（本轮 30 对 / 60 个 raw_name），`auto=0`，附 `evidence`。
4. 只对 `VERIFIED` 执行合并（本轮 **0** 条），写 `merge_log`。
5. 抽 200 个 entity 反向核对：任取一条 works，`author_entity_id` 必须能回溯到 `raw_name`，且与原 `author_name` 逐字相同。

---

## 8 验收查询（只读，可直接跑）

```sql
-- V1 不允许"仅 C/D 级却标 VERIFIED"
SELECT count(*) FROM author_entity WHERE identity_status='VERIFIED' AND evidence_grade IN ('C','D');
-- V2 朝代推导值不得进入证据
SELECT count(*) FROM author_name_variant WHERE evidence LIKE '%集合%' OR evidence LIKE '%推导%';
-- V3 非人署名不得挂 entity
SELECT count(*) FROM works w JOIN collection_role r ON w.author_role_id=r.role_id
 WHERE w.author_entity_id IS NOT NULL;
-- V4 同名异人必须可消歧
SELECT raw_name,count(DISTINCT entity_id) FROM author_name_variant GROUP BY 1 HAVING count(DISTINCT entity_id)>1;
-- V5 郊廟朝會歌辭 必须 100% 落在 role
SELECT count(*) FROM works WHERE author_name='郊廟朝會歌辭' AND author_entity_id IS NOT NULL;  -- 期望 0
-- V6 非人名总数应为 76，不是 72
SELECT count(*) FROM collection_role;
```

---

## 9 与 R2-13 设计的差异

| 项 | R2-13 | R2-14 | 依据 |
|---|---|---|---|
| 表 | `author_identity` / `author_name_variant` | `author_entity` / `author_name_variant` / `collection_role` | 非人名必须有落点 |
| 名字唯一键 | `UNIQUE(raw_name)` | `UNIQUE(raw_name, entity_id)` | `张埴` 一名含宋/清两人 |
| 朝代 | 单列 `dynasty`（注"可能推的"） | 拆 `dynasty_verified` / `dynasty_derived` | 20,809 条 note 全同 |
| 门槛 | "至少三条"，含"朝代一致" | A/B/C/D 分级，**朝代一律不算** | 朝代=集子影子 |
| CONFIRMED | 33 | **0** | 33 对证据全是跨总集同文 |
| 非人名数 | 72（文件 73 行含汇总行） | **76**（补 缺名/暮雨谣三叠/清江道中/西湖竹枝詞） | D2 复算 |
| 非人名类型 | ANONYMOUS / COLLECTION / PERSON / UNKNOWN | ANONYMOUS / COLLECTION / INSTITUTIONAL / UNKNOWN | PERSON 不属于非人名 |
| 新增 variant_type | — | `MIXED_SCRIPT`、`KINSHIP_PLACEHOLDER` | 35 对混形 + 9 对某氏 |
