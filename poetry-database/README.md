# 诗词文献与作品基础数据库（poetry-database）

**这是「先建资料、再建规则」路线下的第一层：原始文献层 + 结构化数据层。**
不含知识规则、不含格律引擎、不含文学评价。

> 建立时间：2026-11-11　｜　轮次：ROUND 1（文献搜集、阅读与基础数据库建设）
> 姊妹目录 `../诗词格律引擎/` 为上一轮成果，**已冻结**，仅作研究工具。

---

## 一分钟了解它能做什么

```bash
cd poetry-database

# 看总量与分布
python3 tools/query.py stats

# 按作者、体裁、词牌、正文检索
python3 tools/query.py author 杜甫 --limit 5
python3 tools/query.py genre 七言律诗 --limit 3
python3 tools/query.py cipai 声声慢 --limit 3
python3 tools/query.py search 枯藤老树

# 查某个来源的许可与可靠性
python3 tools/query.py source CP-SONGCI-01

# 看某朝某体裁的覆盖
python3 tools/query.py coverage
```

## 现有规模（2026-11-20 实测）

| 项 | 数值 |
|---|---|
| 作品记录 | **375,399** |
| 作者记录 | **20,809**（`author_id` = 姓名哈希，**不是人物实体**；同一名字可能跨朝代） |
| 采集来源 | **941**（在用本地文件 819 个，全部存在） |
| 数据库 | `database/poetry.db`，**767,918,080 字节**（约 732 MB），**108 表 / 2 视图 / 86 索引** |
| 体裁 | 11 类：五律/七律/五绝/七绝/五排/七排/古体/四言/楚辞/词/曲 |
| 来源定位 | 551 个来源可定位到 JSON 数组下标，覆盖 164,217 条（43.7%）；卷次/页码/版本定位为 0 |

> **数据库与 `normalized/` 不在公开仓库。** 克隆后需自备本地 `database/poetry.db`；
> 测试会区分「公开归档测试」与「本地数据库测试」，缺库时后者标 `NOT RUN`。
>
> 早期 README 写的「90,279 作品 / 5,286 作者 / 128 来源 / 95 MB / 7 表」是 ROUND 1 口径，
> 已被上表取代。作者数不是人物数，见 R2-14 的 `AUTHOR_IDENTITY_SCHEMA_R2_14.md`。

## 目录

```
poetry-database/
├── database/poetry.db        SQLite 主库（不在 GitHub）
├── raw/                      原始文件（语料与书页图像，多数不在 GitHub）
├── normalized/               去标记文本与按集合的 JSONL（不在 GitHub）
├── catalog/                  作者 / 来源 / 集合 / 研究卡
├── research/                 阅读笔记与作品研究卡
├── audit/                    采集、解析、质量、覆盖的日志与报告
├── sources/manifest.json     采集合约（采什么、什么许可、可靠性如何）
├── tools/                    审计、治理与同步脚本
└── reports/                  逐轮任务报告（tasks/YYYY-MM-DD/R2-XX/）
```

## 从零复现

```bash
python3 tools/build_manifest.py   # 1 生成来源清单
python3 tools/acquire.py          # 2 采集（幂等）
python3 tools/convert_books.py    # 3 文献去标记
python3 tools/parse.py            # 4 解析入库
python3 tools/quality.py          # 5 质量十项
python3 tools/coverage.py         # 6 覆盖率与研究卡
```

依赖：Python 3.11+、`curl`、`opencc-python-reimplemented`。全部脚本幂等。

## 三条硬边界（用前必读）

1. **只能统计，不能引用。**
   语料来自 chinese-poetry（自述「数据来源于互联网、采集无记录」），已确证存在错字
   （《山居秋暝》「明月**鬆**间照」应为「松」）。引用诗句前必须核印本。

2. **多源并列，没有校定本。**
   《静夜思》在库内有两个文本：「床前明月光……举头望明月」（唐诗三百首）与
   「牀前看月光……举头望山月」（全唐诗）。**两者并存，互不覆盖**，哪一版对由文献学决定。

3. **作者归属有争议，程序不裁决。**
   库内自动发现 377 组「同文异作者」，如《登鹳雀楼》在朱斌与王之涣名下并存。
   这些都真实存在，不是数据错误。

## 已知缺口

- 王力《诗词格律》、龙榆生《唐宋词格律》《钦定词谱》影印本、《广韵》《集韵》《词林正韵》字表：**全部未取得**（现代版权或未找到合法电子本）。
- 魏晋南北朝、隋、辽金、明：**0 作品**。
- 词谱：**完全没有**。库内有 19,595 首词，但没有任何词牌的平仄定格。
- 韵书字表：只有上一轮遗留的平水韵表（出处不明）。

详见 `reports/round-1/09_未完成任务与风险.md`。

## 许可

- `raw/poetry/` 与 `catalog/`：源自 chinese-poetry（MIT），原文公有领域。
- `raw/books/`、`normalized/books/`：维基文库转录（CC BY-SA 4.0），原文公有领域。
- 本库自身脚本与报告：可自由使用。
- 对外分发前请先读 `reports/round-1/08_版权与合法性报告.md` 第五节的风险清单。
