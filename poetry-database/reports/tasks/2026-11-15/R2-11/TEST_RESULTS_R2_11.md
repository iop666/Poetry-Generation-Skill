# TEST_RESULTS_R2_11 — 实际执行记录

日期：2026-11-15　解释器：`/usr/bin/python3`（3.13）　工作目录：`poetry-database/`

## 1 命令与实际输出

### 1.1 新测试集（本轮）

```bash
TMPDIR="$HOME/Desktop/workbuddy/2026-11-15/.tmp" python3 tools/r2_11_tests.py
# 输出（末行）：
# total=68 pass=68 fail=0
```

68 项分布：廣韻 20、新韻 12、韻書身份 14、集韻 6、詞譜 4、例詞 3、上古音 1、獨立審查 2、固定樣本 2、數據保護 4。

**首轮执行时 T61/T62 曾为 FAIL**（独立审查文件尚未落地），文件生成后重跑转为 PASS；
期望值全程未改。审查对象 120 个唯一 ID，一致 96 / 不一致 18 / 无法判定 6（80.0% 一致率）。

### 1.2 旧测试集回归（未改一字）

```bash
python3 tools/r2_10_tests.py   # R2-10 tests: 82 PASS 80 FAIL 2
#  FAIL T12 每個錨定韻都有小韻（無空韻） expect 0 actual 4
#  FAIL T60 六套體系未被合併成單一平仄字典 expect 6 actual 4

python3 tools/r2_09_tests.py   # tests 71 PASS 71 FAIL 0
```

旧 T12/T60 仍为 FAIL——因为旧表 `guangyun_yunmu_repair_r2_10`、`ph_readings_r2_08` **本轮不得修改**。
本轮的处理方式是另立新表与新测试（见 `RHYME_SYSTEM_TEST_REDESIGN.md`、`JIYUN_T12_FOUR_RHYME_REPAIR.csv`）。

### 1.3 工作包脚本

| 脚本 | 作用 | 输出 |
|---|---|---|
| `tools/r2_11_preflight.py` | 冻结数据库状态 | `LOGS/preflight.json`、两份 PREFLIGHT CSV |
| `tools/r2_11_guangyun.py` | 广韵结构解析 | `LOGS/guangyun_recount.json` |
| `tools/r2_11_guangyun_db.py` | 写 4 表 + 4 CSV | 见 FILE_MANIFEST |
| `tools/r2_11_xinyun.py` | 十四韵解析与重审 | 3 CSV + `LOGS/xinyun_*.json` |
| `tools/r2_11_identity.py` | 六书标识与查询 | 4 表 + 2 CSV |
| `tools/r2_11_jiyun.py` | 集韵闭环 | 5 CSV |
| `tools/r2_11_cipai_images.py` / `r2_11_cipai_montage.py` | 词谱图像 | 11+5 PNG + 2 CSV |
| `tools/r2_11_schwa_images.py` | 音标条带 | 2 PNG + 1 CSV |
| `tools/r2_11_tests.py` | 68 项测试 | `TEST_RESULTS_R2_11.csv` |

## 2 关键数值（可复核）

| 指标 | 值 | 出处 SQL / 文件 |
|---|---|---|
| 广韵正文条目 | 25,619 | `SELECT count(*) FROM guangyun_head_classification_r2_11` |
| 广韵小韵（重认） | 3,730 | `SELECT count(*) FROM guangyun_fanqie_validation_r2_11` |
| 反切结构完整 | 3,482（TWO_CHAR） | `GROUP BY structure` |
| 反切串被串栏污染 | 83（IRREGULAR_LONG） | 同上 |
| 无反切 | 165（NONE） | 同上 |
| 韵目直接锚定 | 25,316 条 | `rhyme_validation` status=VERIFIED_POSITION |
| 韵目跨缺失区间推定 | 303 条 | status=SUPPORTED_POSITION |
| 新韵字表 | 7,597 条 | `zhonghua_xinyun_characters_r2_11` |
| 十三支 | 284 字 | 同上 `yun='十三支'` |
| 新韵规则一致（含多读） | 7,359/7,597 = 96.9% | `sum(rule_match)` |
| 集韵 200 抽样 | 194 PASS / 6 FAIL | `JIYUN_NEW_200_SAMPLE_AUDIT.csv` |
| 词谱 11 条原图 | 8 全对 / 3 部分 | `CIPAI_BLIND_TRANSCRIPTION_RESULTS.csv` |

## 3 未覆盖

1. 广韵未与影印本对校（`SOURCE_PRIMARY=0`）。
2. 集韵 DJVU 原图核查 50 条全部 `BLOCKED`（本地无 DJVU 文件）。
3. 音标 50 条只完成渲染与定位，未完成目视判定。
4. 词谱第二人盲读未做。
5. 独立审查的 120 对象由子 Agent 完成，主 Agent 只复核文件结构与抽样内容，未逐条复算。
