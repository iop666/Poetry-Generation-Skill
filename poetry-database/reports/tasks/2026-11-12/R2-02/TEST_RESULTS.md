# TEST_RESULTS —— R2-02 实际运行记录

生成时间：2026-11-12 23:33:59
环境：macOS (darwin) / Python 3.13.12 / SQLite 3.50.4 / curl / OpenCC

所有命令均为本轮真实执行，退出码取自实际进程。

## 一、命令与结果

| # | 命令 | 退出码 | 结果 |
|---|---|---|---|
| 1 | `python3 tools/wenxuan_to_json.py` | 0 | 13 卷 → 359 篇 |
| 2 | `python3 tools/fetch_tao.py` | 0 | 60/60 页 → 124 篇，异文 41 处 |
| 3 | `python3 tools/build_manifest.py` | 0 | 941 源（+13） |
| 4 | `python3 tools/parse.py` | 0 | 375,399 条 |
| 5 | `python3 tools/schema_v2.py` | 0 | provenance 满覆盖 |
| 6 | `python3 tools/author_canon.py` | 0 | 20,809 别名 → 20,326 规范名 |
| 7 | `python3 tools/relabel.py` | 0 | 934 归属候选 + 8,773 异文候选 |
| 8 | `python3 tools/tao_variants.py` | 0 | 7 篇 / 41 处 |
| 9 | `python3 tools/crosscheck_100.py --limit 300` | 0 | MATCH 166 / DIFF 120 / NOT_FOUND 14 |
| 10 | `python3 tools/refine_crosscheck.py` | 0 | 27 异体 + 93 实质 |
| 11 | `python3 tools/coverage.py` | 0 | 11 期，缺口 0 |
| 12 | `python3 tools/quality.py` | 0 | 10 项 + 5 项自检 |

## 二、结构性自检（程序判定）

| 检查 | 结果 | 实测 |
|---|---|---|
| dup_status 之和等于总数 | PASS | — |
| DUPLICATE 数等于冗余条数 | PASS | — |
| KEPT 数等于重复组数 | PASS | — |
| 去重后 = 总数 - 冗余 | PASS | — |
| 无 UNIQUE 落在重复组内 | PASS | — |
| provenance 行数 = works | PASS | 375,399 |
| 孤儿溯源 | 0（清理 1,616 行后） | — |
| 未映射作者 NULL | 0 | — |
| 来源缺失 | 0 | — |

## 三、跨源核对 300 首

| 结果 | 数 |
|---|---|
| MATCH | 166 |
| MATCH_VARIANT | 27 |
| DIFF | 93 |
| NOT_FOUND | 14 |

拆分依据：DIFF 120 中，仅异体写法差异 27，实质差异 93。

## 四、数据质量十项

| 项 | 数值 |
|---|---|
| 完全重复组 / 冗余 | 1,710 / 1,754 |
| 同名异文组 / 涉及作品 | 8,773 / 28,238 |
| 跨作者归属冲突候选 | 934 |
| 含非汉字符 / 残留标点 | 0 / 0 |
| 过短(<10字) / 超长(>2000字) | 295 / 6 |
| 作者佚名 / 空标题 / 词无词牌 | 3,974 / 13 / 27 |

## 五、历史时期覆盖（复算自 audit/coverage.json）

| 时期 | 作品数 |
|---|---|
| 先秦 | 659 |
| 汉代 | 588 |
| 魏晋南北朝 | 4,718 |
| 隋代 | 377 |
| 唐代 | 55,628 |
| 五代 | 543 |
| 宋代 | 271,678 |
| 辽金 | 2,066 |
| 元代 | 10,685 |
| 明代 | 7,641 |
| 清代 | 20,122 |

缺口：无

## 六、已知未覆盖项

1. 未与任何**印本影印件**核对 → `EDITION_VERIFIED` = 0。
2. 辽代作品 0（「辽金」2,066 全为金）。
3. 15,866 条四库本作品体裁「未定」（无标点，无法切句）。
4. 6,959 组异文候选仍为 UNKNOWN。
5. 222 条混入校记的作品只做标记，未清洗。
6. 集韻正文未抓取（需 216 次渲染）。
