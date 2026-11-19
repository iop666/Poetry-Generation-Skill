# R2-15A 公开版权与同步审计

- 日期：2026-11-20
- 结论：**P0 缺陷成立，已在最新快照修复；Git 历史仍含正文，处置待授权。**

---

## 1 缺陷确认（外部审核所指属实）

### 1.1 根因

`tools/github_sync.py` 的 `INCLUDE_FILES` 里写的是**目录**：

```python
INCLUDE_FILES = [
    ...
    "poetry-database/raw/r2_04_evidence",   # ← 整目录递归
]
```

`collect()` 对目录执行 `rglob("*")`，而 `EXCLUDE_PARTS` 只排除了 `raw/books*` 等，没有排除 `r2_04_evidence/full|chapters`。结果 34 个正文文件随公开包一起上传。

**这不是"声明与实现不一致"的口误，是实现层面的白名单过宽。**

### 1.2 内容性质（逐目录核对）

| 目录 | 文件数 | 字符 | 字节 | 性质判定 |
|---|---|---|---|---|
| `full/` | 17 | 107,351 | 290,894 | 完整章节正文，含标点与页码头，**实质性复制** |
| `chapters/` | 17 | 47,436 | 129,806 | 每章约 15 KB 的连续正文摘录（按关键词筛段），**仍属大段复制，不可公开** |

样本：`full/A_027_诗律.md` 61,442 B（《诗词格律》第二章全章）；`chapters/A_027_诗律.md` 15,530 B（同章去掉低信息段后的连续正文）。二者都不是书目或短引。

判定：**`r2_04_evidence/` 下只允许公开 `manifest.json` 等元数据，正文目录全部排除。**

---

## 2 修复内容

### 2.1 白名单收窄（改「目录」为「单文件」）

```python
# 只上传元数据清单；full/ 与 chapters/ 是现代版权书正文，永不上传
"poetry-database/raw/r2_04_evidence/manifest.json",
```

### 2.2 黑名单双保险

```python
EXCLUDE_PARTS = [
    ...
    "/r2_04_evidence/full/", "/r2_04_evidence/chapters/",
]
```

即使将来有人把父目录加回白名单，正文仍会被拦下。

### 2.3 删除规则改为确定性

原实现依赖「上一轮清单 + 本地文件是否还在」，导致本轮只更新清单、不删文件（第一次修复尝试就失败在这里：远端仍留 37 个文件）。现改为：

- 命中 `is_excluded()` 的已上传文件 → **一律删除**；
- 上一轮在清单、本轮不在白名单 → 删除（正常缩圈）；
- `README.md` / `LICENSE` / `CITATION.cff` / 工具生成文件 → 受 `PROTECTED` 保护；
- 每次输出「从仓库删除 N 个文件」并列出前 10 条。

### 2.4 清理结果（远端实测）

| 项 | 清理前 | 清理后 |
|---|---|---|
| 远端文件总数 | 867 | **833** |
| `full/*.md` | 17 | **0** |
| `chapters/*.md` | 17 | **0** |
| `r2_04_evidence` 剩余 | 37 | **3**（`manifest.json`、`ocr_samples.json`、`theory_locate.json`） |

删除提交：`f7b4b2e`（本次同步）。验证方式：GitHub `git/trees/main?recursive=1` 计数。

---

## 3 manifest 字符数差异：21,522 的成因（已查清）

外部审核指出：`manifest.json` 的 `full_chars` 合计 128,873，实际文件 107,351，差 21,522。

### 3.1 结论

**manifest 没有错、也没有过期；差异是统计口径不同，不是数据丢失。**

- `full_chars` = Σ `len(clean(每页文本))`，统计**页内清洗后全部字符**；
- 文件内容 = `"\n\n".join(paragraphs(每页))`，`paragraphs()` 只保留 **≥12 字**的段落。

被丢掉的 21,522 字符，是页眉、页码、图注、公式残片、孤立短行等 <12 字的非段落文本。

### 3.2 复算证据

`COPYRIGHT_CHARCOUNT_DIFF.csv`（17 单元逐条）：

| 指标 | 数值 |
|---|---|
| manifest `full_chars` 合计 | 128,873 |
| 按原脚本复算页字符 | **128,873（差 0）** |
| 段落化后字符 | 100,880 |
| 实际文件字符（含 2 行标题与空行） | 107,351 |

即：清单可 100% 复算；文件比清单少，是因为段落化过滤；文件比段落字符多，是因为标题与分隔空行。

### 3.3 处置

不修改 manifest（它记录的是"页内可解析字符"，这个口径本身有用）。在 `manifest.json` 同目录加说明，避免后人再误判为数据丢失：

- 新增 `README_CHARCOUNT.md`，写明两种口径的定义与差值来源。

---

## 4 矛盾表述修正

| 文件 | 原表述 | 修正 |
|---|---|---|
| `UPLOAD_REPORT.md` | 「版权书全文永不上传」 | 改为「自 2026-11-20 起不复上传；2026-11-16 至 11-20 的历史提交曾包含，见 `COPYRIGHT_HISTORY_IMPACT.md`」 |
| `GITHUB_SYNC.md` | 仅列 `books/`、`raw/books*` | 补 `raw/r2_04_evidence/full|chapters`（现代版权著作章节正文） |
| R2-04 `SOURCE_AUDIT.md` | 称版权书全文未进入交付材料 | 加勘误：该结论对"本地交付"成立，对"公开仓库"不成立，已补 `ERRATA_PUBLIC_SYNC.md` |

原则：**不删改历史报告正文**，只加勘误文件指向，保留可审计性。

---

## 5 防复发测试

新增 `tools/r2_15_a_tests.py`，断言：

| 编号 | 断言 |
|---|---|
| A1 | `INCLUDE_FILES` 中不含 `r2_04_evidence` 目录本身 |
| A2 | `EXCLUDE_PARTS` 含 `/r2_04_evidence/full/` 与 `/r2_04_evidence/chapters/` |
| A3 | `is_excluded("poetry-database/raw/r2_04_evidence/full/x.md")` 为 True |
| A4 | `is_excluded(".../chapters/x.md")` 为 True |
| A5 | `is_excluded(".../manifest.json")` 为 False |
| A6 | 远端 `git/trees` 中 `full|chapters` 计数为 0（网络可用时；否则 NOT RUN） |
| A7 | 本地 `books/` 下文件不属于白名单 |
| A8 | 白名单实际展开后，无任何文件路径命中 `/books/`、`/r2_04_evidence/full/`、`/r2_04_evidence/chapters/` |

---

## 6 遗留

| 项 | 状态 |
|---|---|
| 最新快照清理 | **完成** |
| Git 历史含正文 | **未处置**，见 `COPYRIGHT_HISTORY_IMPACT.md`，需授权 |
| 历史重写 | **未执行**，未 force push |
| 本地研究材料 | **完整保留**，未删除任何本地文件 |
