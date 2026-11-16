# TEST_RESULTS —— R2-01 实际运行记录

生成时间：2026-11-12 12:36:02
环境：macOS (darwin) / Python 3.13.12 / SQLite 3.50.4 / curl

以下命令均为本轮真实执行，退出码取自实际进程。

## 一、执行命令与结果

| # | 命令 | 退出码 | 结果 |
|---|---|---|---|
| 1 | `python3 tools/discover_ws_series.py` | 0 | 枚举 791 个分卷页（8 类古籍） |
| 2 | `python3 tools/build_manifest.py` | 0 | 924 个采集源 + 13 种现代专著 |
| 3 | `python3 tools/acquire.py --only CP-SONGSHI` | 0 | 全宋诗 255/255 片成功 |
| 4 | `python3 tools/fetch_ws_series.py --series gushiji,mingshi,wanqing,zhongzhou` | 0 | 470/470 卷成功，失败 0 |
| 5 | `python3 tools/fetch_ws_series.py --series guangyun,jiliyun,cilv,cipu --render` | 1（首轮）→ 0（补抓） | 首轮 429 失败 1 卷，重抓后 75/75 落地 |
| 6 | `python3 tools/ws_to_json.py` | 0 | 四部总集 35,741 篇转中间 JSON |
| 7 | `python3 tools/parse.py` | 0 | 374,918 条入库 |
| 8 | `python3 tools/schema_v2.py` | 0 | 9 新列 + 4 新表 + 374,918 条 provenance |
| 9 | `python3 tools/relabel.py` | 0 | 934 归属候选 + 8,742 异文候选分流 |
| 10 | `python3 tools/crosscheck_100.py --limit 100` | 0 | 100 首：MATCH 51 / DIFF 37 / NOT_FOUND 12 |
| 11 | `python3 tools/quality.py` | 0 | 10 项检查 + 5 项一致性自检 |
| 12 | `python3 tools/coverage.py` | 0 | 11 期，缺口 **0**；103 张研究卡 |

## 二、结构性自检（由程序判定，非人工声称）

| 检查 | 结果 | 实测值 |
|---|---|---|
| dup_status 之和等于总数 | PASS | 371,456 + 1,709 + 1,753 = 374,918 |
| DUPLICATE 数等于冗余条数 | PASS | 1,753 |
| KEPT 数等于重复组数 | PASS | 1,709 |
| 去重后 = 总数 - 冗余 | PASS | 373,165 |
| 无 UNIQUE 落在重复组内 | PASS | PASS |
| 来源缺失 | 0 | 每条 work 均可回 source_id |
| 非汉字符 / 残留标点 | 0 / 0 | 全表正则扫描 |

## 三、数据质量十项

| 项 | 数值 |
|---|---|
| 完全重复组 / 冗余 | 1,709 / 1,753 |
| 同名异文组 / 涉及作品 | 8,742 / 28,168 |
| 跨作者归属冲突候选 | 934 |
| 含非汉字符 / 残留标点 | 0 / 0 |
| 过短(<10字) / 超长(>2000字) | 295 / 6 |
| 作者佚名 / 空标题 / 词无词牌 | 3,929 / 13 / 27 |

## 四、历史时期覆盖（复算自 audit/coverage.json）

| 时期 | 作品数 |
|---|---|
| 先秦 | 655 |
| 汉代 | 544 |
| 魏晋南北朝 | 4,354 |
| 隋代 | 377 |
| 唐代 | 55,628 |
| 五代 | 543 |
| 宋代 | 271,678 |
| 辽金 | 2,066 |
| 元代 | 10,685 |
| 明代 | 7,641 |
| 清代 | 20,122 |

缺口：无

## 五、100 首独立核对明细

| 结果 | 数量 | 含义 |
|---|---|---|
| MATCH | 51 | 两上游归一化后完全一致 |
| DIFF | 37 | 有实质差异，差异已逐条写库 |
| NOT_FOUND | 12 | 同题不同篇／库内缺该首 → 标 UNKNOWN，不升级 |

## 六、已知未覆盖项

1. 未与任何**印本影印件**核对 → `EDITION_VERIFIED` = 0。
2. 四庫本无标点 → 古詩紀／明詩綜／中州集 15,866 条体裁标「未定」，未作判定。
3. 集韻仅取到韵例与部分韵目（10 卷共 40 KB），非全文。
4. 作者异名未归并（陶潛／陶渊明、陳思王植／曹植），按现代名查询会漏。
5. 12 首核对未匹配，原因已逐条记录，未强行判为一致。
