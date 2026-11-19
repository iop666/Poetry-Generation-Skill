# 元曲完整性审计（R2-15 / C4）：把「来源匹配度」与「作品完整性」拆成两个正交维度

> 只读审计。未修改 `works`、未重新导入、未关闭任何过滤规则、未联网。
> 全部数字可由 `LOGS/build_completeness_4510.py` 对 `poetry.db` + `raw/poetry/yuanqu/yuanqu.json` 复算。

---

## 一、结论先行

**「100 条 EXACT」只说明 DB 与来源逐字一致，不等于 100 首完整作品。**

本轮对 4,510 条元曲审计全集做的逐条比对给出：

| 维度 | 结果 |
|---|---|
| 来源匹配 | **4,510 / 4,510 = 100% SOURCE_EXACT**（0 VARIANT、0 ABSENT） |
| 作品完整 | **仅 2,739 / 4,510 = 60.7% COMPLETE** |
| 因字段边界不完整 | 1,727（38.3%）曲文首段被刮进 `title_raw`，正文只是后半截 |
| 因源截断不完整 | 41（0.9%）整支曲只剩 1–2 句 |
| 无法判定边界 | 2（0.04%） |
| 只有科白 | 1（0.02%） |

因为 **match_level 全部落在 SOURCE_EXACT 一个格子里**，它在元曲这一批数据上**没有任何区分能力**。
真正有区分力的是 completeness：**约 39.3%（1,771/4,510）的库内记录不是可用的完整作品**，
而这个事实在「来源匹配 100%」的口径下被完全掩盖。

一句话：**匹配率证明的是导入管道没有篡改，完整性评价的是上游数据本身残缺。两者不能互相担保。**

---

## 二、两个维度的定义（互不推导）

### 2.1 `match_level` —— 只看「库里存的字」与「来源里的字」是否一致

对每条记录，用 `(author_name, title_raw)` 命中 `raw/poetry/yuanqu/yuanqu.json`，
再把源 `paragraphs` 用换行拼接，与 `works.text_raw` **逐字符**比较：

| 取值 | 判据 | 条数 |
|---|---|---|
| `SOURCE_EXACT` | 拼接结果与 `text_raw` 完全相等 | **4,510** |
| `SOURCE_VARIANT` | 命中同一源记录但字符有差异 | 0 |
| `SOURCE_ABSENT` | 源中无对应记录 | 0 |

> 说明：4,510 条 100% 命中且逐字相同，原因是 `works` 由该 JSON 机械导入。
> 反过来讲，**`SOURCE_EXACT` 不是质量背书**——上游 JSON 的 `title` 字段本身就在 32 字处硬切，
> 库里忠实地继承了这个切法（1,423 条 `title_raw` 恰为 32 字）。
> 忠实导入一个残缺源，结果仍然是残缺的。

### 2.2 `completeness` —— 只看「这条记录作为一件作品是否完整」，与来源是否一致无关

判据按优先级短路，全部可在 CSV 的 `evidence` 列逐条复核：

| 取值 | 判据 | 条数 | 占比 |
|---|---|---|---|
| `COMPLETE` | 曲文完整落在 `text_raw`，以句末标点/唱腔提示收束，长度 ≥29 字 | **2,739** | 60.73% |
| `TITLE_ONLY` | 曲文首段（或全部）在 `title_raw`，`text_raw` 单独不构成完整作品 | **1,727** | 38.29% |
| `TRUNCATED` | 整支曲仅存 1–2 句，句中/句间断裂（`FRAGMENTARY`） | **41** | 0.91% |
| `AMBIGUOUS` | 标题与正文的切点无法判定（`SPLIT_AMBIGUOUS`） | **2** | 0.04% |
| `DIALOGUE_ONLY` | 全条只有科白，无曲文 | **1** | 0.02% |
| `EMPTY_BODY` | `text_raw` 为空 | **0** | 0% |
| 合计 | | **4,510** | 100% |

`TITLE_ONLY` 内部再分两型（`boundary_verdict` 列）：
- `SPLIT_CLEAN` **1,682**：曲牌名保留在 `・` 之前，曲文前半截接在 `・` 之后，与正文无重叠无缺口；
- `TITLE_IS_ALL_LYRIC` **45**：`title_raw` 以 `・` 开头，**曲牌名已整体丢失**，标题里全是曲文。

---

## 三、交叉表 `match_level × completeness`

| match_level ↓ \ completeness → | COMPLETE | TITLE_ONLY | TRUNCATED | AMBIGUOUS | DIALOGUE_ONLY | EMPTY_BODY | 合计 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **SOURCE_EXACT** | **2,739** | **1,727** | **41** | **2** | **1** | 0 | **4,510** |
| SOURCE_VARIANT | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| SOURCE_ABSENT | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **合计** | 2,739 | 1,727 | 41 | 2 | 1 | 0 | 4,510 |

**读法（这是本轮最重要的一格）**：`SOURCE_EXACT` 行里同时躺着 2,739 条完整作品和 1,771 条不完整作品。
如果只用「来源匹配」做质量指标，这 1,771 条会被判为「已验证」；
如果只用「完整性」做质量指标，又会误以为导入管道出了问题。
**两个指标必须并列报告，任何单一指标都会给出错误结论。**

### 3.1 三种缺陷必须分开计数（不可合并为「缺曲文」）

| 缺陷类型 | 条数 | 性质 | 能否本地修复 |
|---|---:|---|---|
| **标题错误**（曲文被刮进 `title_raw`） | 1,727 | 字段边界错位，字一个没少 | **能**（拼接标题尾 + 正文） |
| **正文截断**（整支曲只剩残句） | 41 | 上游抓取时就断了 | **不能**（本地无第二来源，补字即编造） |
| **仅对白** | 1 | 源本身就只有科白 | **不能** |
| **边界不可判** | 2 | 切点两可 | **不能**（不做猜测性切分） |

把这三类合并成一个「缺曲文 1,771 条」的数字是错的：
它们的数据来源、可恢复性、对下游（平仄/韵脚）的影响方向完全不同。

---

## 四、可恢复记录：原文 / 修订文本 / 差异

`YUANQU_RECOVERY_TRIAD.csv`（**1,771 行** = 1,727 条可恢复 + 44 条 `NOT_GENERATED`）：

| 列 | 内容 |
|---|---|
| `orig_text_raw` | 库内原文（`works.text_raw`，未改动） |
| `revised_text` | 修订文本 = `title_raw` 中 `・` 之后的曲文尾 + `text_raw`，**直接拼接，无增删字** |
| `delta_chars` | 修订后增加的字数 |
| `diff_note` | 差异说明：标题尾 N 字前移；曲牌还原为「…」，或标明 `QUPAI_MISSING` / `QUPAI_UNCERTAIN` |

统计：补回 **16–42 字**，中位 **28 字**，合计 **49,579 字**；
修订后长度中位 **63 字**（原中位 33 字），即此前这 1,727 条被当成「30 字短曲」在统计。

**未生成修订文本的记录 = 44 条**（41 `TRUNCATED` + 2 `AMBIGUOUS` + 1 `DIALOGUE_ONLY`），
在这张表中以 `revised_text = NOT_GENERATED` 占位，`diff_note` 逐条写明原因
（源端截断 / 切点两可 / 仅科白），统一前提是 **本地无第二来源，任何补字都属于编造**。
它们只在 `YUANQU_COMPLETENESS_4510.csv` 中保留原文，不进入可复原集合。

> 注意：三列表里的 `revised_text` 是**候选修订**，本轮未写库。
> 是否落库、落库后如何同步 `char_count`，属于另一张任务单。

---

## 五、20 条 TRUNCATED 回源复核

`YUANQU_TRUNCATION_RECHECK_20.csv`，从 41 条 `TRUNCATED` 中均匀抽取 20 条回 `yuanqu.json`：

| 检查项 | 结果 |
|---|---|
| `json_last_para_tail_24` == `db_last_line_tail_24` | **20 / 20 逐字相同**（`byte_identical = Y`） |
| 源 `paragraphs` 条数 vs DB 行数 | 20 / 20 一致，**DB 未丢弃任何段** |
| 判定 | **20 / 20 = `SOURCE_TRUNCATED`，0 条 `IMPORT_TRUNCATED`** |

截断位置分布：
- `ARIA_LEVEL_FRAGMENT`（句读完整但整支曲只剩 1–2 句）**14**；
- `SENTENCE_LEVEL_CUT`（前句未收尾即断，出现「？。」「！。」「，。」双标点）**5**；
- `SENTENCE_LEVEL_CUT`（末句仅 2 字）**1**。

**结论：这批截断 100% 发生在源端，不是导入端。**
导入端做的是逐字搬运，它把源里的断句原样搬了进来——所以修导入脚本对这 41 条无效，
只有引入第二来源才可能补齐。

---

## 六、口径自校验：与 R2-14 的 100 条抽样对照

用 R2-14 `YUANQU_100_SOURCE_VERIFICATION.csv` 的 `verdict` 映射到本轮 `completeness`：

| R2-14 verdict | 映射 | 本轮结果 | 一致 |
|---|---|---:|---:|
| `SOURCE_VERBATIM` | → COMPLETE | 25 | 25 |
| `SOURCE_VERBATIM_TITLE_HELD` | → TITLE_ONLY | 50 | 50 |
| `SOURCE_TRUNCATED` | → TRUNCATED | 24 | 24 |
| `SOURCE_DIALOGUE_ONLY` | → DIALOGUE_ONLY | 1 | 1 |
| **合计** | | **100** | **100** |

**100 / 100 一致，0 例冲突。** 说明本轮对 4,510 条的自动判定与 R2-14 的人工抽样口径同源、可互证。

---

## 七、两个附带的边界事实（供下游引用时避坑）

1. **1,143 条正文以唱腔提示收尾**（形如「（正旦唱）。」）。
   抽查其源文件中的下一条：**1,083 条**为同作者、不同曲牌 → 该提示是**曲牌边界标记，不是截断**；
   剩余 **60 条**无法用「下一条即新曲牌」佐证，已在 `note` 标 `ENDS_WITH_CUE_UNCONFIRMED`，
   作为残余风险列出，但本轮**不据此改判 completeness**（无证据表明缺文）。
2. **1,425 条 `title_raw` 长度恰为 32（其中 1,423 条属 `TITLE_ONLY`）**。
   32 是上游的固定列宽硬切点，不是自然句读。任何用 `title_raw` 做曲牌匹配的逻辑，
   必须只取 `・` 之前的部分，否则 1,727 条会全部失配。

---

## 八、复算方式

```bash
cd <PROJECT_ROOT>
python3 poetry-database/reports/tasks/2026-11-20/R2-15/LOGS/build_completeness_4510.py
```

脚本以 `mode=ro` 打开数据库，只读 `works` 与 `yuanqu_text_audit_r2_13`；
输出 `YUANQU_COMPLETENESS_4510.csv`、`YUANQU_RECOVERY_TRIAD.csv`、
`YUANQU_TRUNCATION_RECHECK_20.csv`、`LOGS/stats_completeness.json`。
脚本内不含任何随机数、不含任何外部知识补字，重跑结果逐字节一致。

## 九、产物清单

| 文件 | 内容 | 行数 |
|---|---|---:|
| `YUANQU_COMPLETENESS_4510.csv` | 逐条两维判定 + 证据 + 备注 | 4,510 |
| `YUANQU_COMPLETENESS_SUMMARY.md` | 本文件 | — |
| `YUANQU_RECOVERY_TRIAD.csv` | 原文 / 修订文本 / 差异（1,727 可复原 + 44 NOT_GENERATED） | 1,771 |
| `YUANQU_TRUNCATION_RECHECK_20.csv` | 20 条截断回源复核 | 20 |
| `LOGS/build_completeness_4510.py` | 复算脚本 | — |
| `LOGS/stats_completeness.json` | 机读统计 | — |
