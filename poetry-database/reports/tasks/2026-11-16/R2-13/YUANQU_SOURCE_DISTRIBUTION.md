# 元曲来源分布与原文核对（R2-13 / D2）

- 生成时间：2026-11-16　数据库：`database/poetry.db`（只读）
- 审计全集：**4510** 条（判据见 `LOGS/D_notes.md`）
- 唯一来源：`CP-YUANQU` → `raw/poetry/yuanqu/yuanqu.json`
- 文件 sha256：`c2be37d2349cec99ec7f2d7c4107eb08bbb3ac869221db24531c8ffed2a88b12`　大小 4,188,599 字节　记录 11,057 条

## 一、按 source_id / collection / base_edition 统计

| 维度 | 取值 | 条数 |
|---|---|---|
| source_id | CP-YUANQU | 4510 |
| collection | yuanqu | 4510 |
| base_edition | 整理本（无底本声明） | 4510 |

> 结论：**全库元曲只有一个来源、一个 collection、一个 base_edition**。
> 因此「按来源分层」在本数据集内不可能，真正的分层维度是**来源文件内部的两种结构**（杂剧/套数 vs 散曲），见下节。

## 二、来源内部结构分层（真正的差异所在）

`title_raw` 含「・」者 = 杂剧/套数（剧目名・曲牌），不含者 = 散曲小令。两者是上游同一文件的两种记录形态。

| status | 杂剧/套数(有剧目) | 散曲(无剧目) | 合计 |
|---|---|---|---|
| LYRIC_PRESENT | 2456 | 283 | 2739 |
| IN_OTHER_FIELD | 1729 | 0 | 1729 |
| FRAGMENTARY | 2 | 39 | 41 |
| DIALOGUE_ONLY | 1 | 0 | 1 |
| **合计** | | | **4510** |

## 三、来源判定

| 判定 | 条数 | 含义 |
|---|---|---|
| SOURCE_HAS_QU_TEXT | 4468 | 本地来源里就有该记录的曲文（正文内或标题内），不缺 |
| SOURCE_HAS_DIALOGUE_ONLY | 1 | 本地来源该条本身只有宾白 |
| SOURCE_HAS_MISSING_PAGE | 0 | 来源缺页（本数据集为 JSON，无页概念，恒 0） |
| SOURCE_UNAVAILABLE | 0 | 来源不可得（恒 0，文件在位且 sha256 已核） |
| SOURCE_STRUCTURE_UNKNOWN | 41 | 来源文本在句中截断，无法判断原貌 |

## 四、20 条回原文核对

抽样法：分层（LYRIC_PRESENT / IN_OTHER_FIELD / FRAGMENTARY / DIALOGUE_ONLY），固定种子 20261116，
按作者去重优先；逐条在 `raw/poetry/yuanqu/yuanqu.json` 内定位并比对。

| # | work_id | 标题 | 库内 status | 原文有曲文? | 原文片段 |
|---|---|---|---|---|---|
| S01 | `yuanqu:da4949b0f3e4` | 杨氏女杀狗劝夫・滚绣球 | LYRIC_PRESENT | Y | raw paragraphs=117 字，与库 text_raw 逐字相同=True |
| S02 | `yuanqu:81d51a58ef61` | 洞庭湖柳毅传书・得胜令 | LYRIC_PRESENT | Y | raw paragraphs=102 字，与库 text_raw 逐字相同=True |
| S03 | `yuanqu:c6b8a50d2bec` | 庞居士误放来生债・幺篇 | LYRIC_PRESENT | Y | raw paragraphs=81 字，与库 text_raw 逐字相同=True |
| S04 | `yuanqu:5068b2f71572` | 醉思乡王粲登楼・迎仙客 | LYRIC_PRESENT | Y | raw paragraphs=72 字，与库 text_raw 逐字相同=True |
| S05 | `yuanqu:38f42e332228` | 黑旋风双献功・煞尾 | LYRIC_PRESENT | Y | raw paragraphs=58 字，与库 text_raw 逐字相同=True |
| S06 | `yuanqu:b8fbb9fa9ce3` | 关云长千里独行・菩萨梁州 | LYRIC_PRESENT | Y | raw paragraphs=112 字，与库 text_raw 逐字相同=True |
| S07 | `yuanqu:416fc923b4d2` | 揽筝笆・嫌喧花，不挂许由瓢。玉兔金乌，从昏至晓。 | IN_OTHER_FIELD | Y（曲文头在 raw title 内） | raw title=「揽筝笆・嫌喧花，不挂许由瓢。玉兔金乌，从昏至晓。时复饮浊醪，且吃」；raw paragraphs 首「的，沉醉陶陶。⏎把人间万事都忘，到大来散诞逍遥。」 |
| S08 | `yuanqu:1d07492d8f52` | 红绣鞋・黄甘甘胭憔粉悴，病恹恹瘦损香肌，急煎煎和 | IN_OTHER_FIELD | Y（曲文头在 raw title 内） | raw title=「红绣鞋・黄甘甘胭憔粉悴，病恹恹瘦损香肌，急煎煎和泪数归期。急穰穰」；raw paragraphs 首「情没乱，碜磕磕的两分离，空着我闷恹恹盼望你。」 |
| S09 | `yuanqu:e8caad6ffca5` | 大迓鼓南・相逢莺燕友，四眸相顾，两意相投，此情难 | IN_OTHER_FIELD | Y（曲文头在 raw title 内） | raw title=「大迓鼓南・相逢莺燕友，四眸相顾，两意相投，此情难消受。风流自古，」；raw paragraphs 首「偏惜风流，展转留情双凤眸。」 |
| S10 | `yuanqu:ccc39165838c` | 五煞・照妖镇释坛，护心保命全。分开后对成姻眷，乐 | IN_OTHER_FIELD | Y（曲文头在 raw title 内） | raw title=「五煞・照妖镇释坛，护心保命全。分开后对成姻眷，乐昌暗结风流配，鲁」；raw paragraphs 首「肃深谋斩斫权。⏎憔悴佳人倦，愁观衰貌，鼓照芳研。」 |
| S11 | `yuanqu:12434c4857ef` | 幺篇・月下砧声幽，月下砧声幽，风前笛秦。断肠声无 | IN_OTHER_FIELD | Y（曲文头在 raw title 内） | raw title=「幺篇・月下砧声幽，月下砧声幽，风前笛秦。断肠声无了无休，捣碎我心」；raw paragraphs 首「又加上一场症候，顿使我愁不寐，襄王梦雨散云收。」 |
| S12 | `yuanqu:c70afa4e4569` | 油葫芦・虽住在洗耳溪边不饮牛，贫自守，乐闲身翻作 | IN_OTHER_FIELD | Y（曲文头在 raw title 内） | raw title=「油葫芦・虽住在洗耳溪边不饮牛，贫自守，乐闲身翻作抱官囚。布袍宽褪」；raw paragraphs 首「拿云手，玉箫占断谈天口。⏎吹箫仿伍员，弃瓢学许由。⏎ |
| S13 | `yuanqu:bbdd98666516` | 忒忒令 | FRAGMENTARY | N（源即残缺） | raw paragraphs 仅 11 字且句中断裂：「(生、旦)许多时缘何未归？眼巴。」 |
| S14 | `yuanqu:0130b74f9739` | 上堂水陆 | FRAGMENTARY | N（源即残缺） | raw paragraphs 仅 10 字且句中断裂：「衣锦归故乡。⏎(合)我门得意。」 |
| S15 | `yuanqu:a762cad255d5` | 生查子 | FRAGMENTARY | N（源即残缺） | raw paragraphs 仅 16 字且句中断裂：「(末扮李三公上)村庄守已，茅屋悄然而已。」 |
| S16 | `yuanqu:ccd6ad9ada22` | 陶学士醉写风光好・鲍老作 | FRAGMENTARY | N（源即残缺） | raw paragraphs 仅 11 字且句中断裂：「则见他人丛里叠扑着个幽。」 |
| S17 | `yuanqu:dba46748341c` | 金水桥陈琳抱妆盒・仁宗云 | DIALOGUE_ONLY | N | raw paragraphs=「这等，你怎生送的我到楚王府里去那？(正末唱)。」，只有宾白 |
| S18 | `yuanqu:fa9bd37a9b42` | 争报恩三虎下山・迎仙客 | LYRIC_PRESENT | Y | raw paragraphs=213 字，与库 text_raw 逐字相同=True |
| S19 | `yuanqu:18e157bef8b4` | 前腔 | LYRIC_PRESENT | Y | raw paragraphs=26 字，与库 text_raw 逐字相同=True |
| S20 | `yuanqu:72902b3c62e6` | 亻刍梅香骗翰林风月・双调/新水令 | LYRIC_PRESENT | Y | raw paragraphs=478 字，与库 text_raw 逐字相同=True |

### 逐条说明（3 条关键样本全录）

- **S07 `yuanqu:416fc923b4d2`（IN_OTHER_FIELD）** 揽筝笆・嫌喧花，不挂许由瓢。玉兔金乌，从昏至晓。时复饮浊醪，且吃
  - locator: `#index=4654`；原文核实：raw title=「揽筝笆・嫌喧花，不挂许由瓢。玉兔金乌，从昏至晓。时复饮浊醪，且吃」；raw paragraphs 首「的，沉醉陶陶。
把人间万事都忘，到大来散诞逍遥。」
- **S08 `yuanqu:1d07492d8f52`（IN_OTHER_FIELD）** 红绣鞋・黄甘甘胭憔粉悴，病恹恹瘦损香肌，急煎煎和泪数归期。急穰穰
  - locator: `#index=8379`；原文核实：raw title=「红绣鞋・黄甘甘胭憔粉悴，病恹恹瘦损香肌，急煎煎和泪数归期。急穰穰」；raw paragraphs 首「情没乱，碜磕磕的两分离，空着我闷恹恹盼望你。」
- **S09 `yuanqu:e8caad6ffca5`（IN_OTHER_FIELD）** 大迓鼓南・相逢莺燕友，四眸相顾，两意相投，此情难消受。风流自古，
  - locator: `#index=7055`；原文核实：raw title=「大迓鼓南・相逢莺燕友，四眸相顾，两意相投，此情难消受。风流自古，」；raw paragraphs 首「偏惜风流，展转留情双凤眸。」
- **S10 `yuanqu:ccc39165838c`（IN_OTHER_FIELD）** 五煞・照妖镇释坛，护心保命全。分开后对成姻眷，乐昌暗结风流配，鲁
  - locator: `#index=9088`；原文核实：raw title=「五煞・照妖镇释坛，护心保命全。分开后对成姻眷，乐昌暗结风流配，鲁」；raw paragraphs 首「肃深谋斩斫权。
憔悴佳人倦，愁观衰貌，鼓照芳研。」
- **S11 `yuanqu:12434c4857ef`（IN_OTHER_FIELD）** 幺篇・月下砧声幽，月下砧声幽，风前笛秦。断肠声无了无休，捣碎我心
  - locator: `#index=154`；原文核实：raw title=「幺篇・月下砧声幽，月下砧声幽，风前笛秦。断肠声无了无休，捣碎我心」；raw paragraphs 首「又加上一场症候，顿使我愁不寐，襄王梦雨散云收。」
- **S12 `yuanqu:c70afa4e4569`（IN_OTHER_FIELD）** 油葫芦・虽住在洗耳溪边不饮牛，贫自守，乐闲身翻作抱官囚。布袍宽褪
  - locator: `#index=4752`；原文核实：raw title=「油葫芦・虽住在洗耳溪边不饮牛，贫自守，乐闲身翻作抱官囚。布袍宽褪」；raw paragraphs 首「拿云手，玉箫占断谈天口。
吹箫仿伍员，弃瓢学许由。
」
- **S13 `yuanqu:bbdd98666516`（FRAGMENTARY）** 忒忒令
  - locator: `#index=1929`；原文核实：raw paragraphs 仅 11 字且句中断裂：「(生、旦)许多时缘何未归？眼巴。」
- **S14 `yuanqu:0130b74f9739`（FRAGMENTARY）** 上堂水陆
  - locator: `#index=2673`；原文核实：raw paragraphs 仅 10 字且句中断裂：「衣锦归故乡。
(合)我门得意。」
- **S15 `yuanqu:a762cad255d5`（FRAGMENTARY）** 生查子
  - locator: `#index=8835`；原文核实：raw paragraphs 仅 16 字且句中断裂：「(末扮李三公上)村庄守已，茅屋悄然而已。」
- **S16 `yuanqu:ccd6ad9ada22`（FRAGMENTARY）** 陶学士醉写风光好・鲍老作
  - locator: `#index=6404`；原文核实：raw paragraphs 仅 11 字且句中断裂：「则见他人丛里叠扑着个幽。」
- **S17 `yuanqu:dba46748341c`（DIALOGUE_ONLY）** 金水桥陈琳抱妆盒・仁宗云
  - locator: `#index=6883`；原文核实：raw paragraphs=「这等，你怎生送的我到楚王府里去那？(正末唱)。」，只有宾白

## 五、原始文件与库的差额

`audit/parsing_log.jsonl` 第 340 行：
```json
{"source_id":"CP-YUANQU","items":11057,"kept":10685,"skipped_short":372}
```
原始 JSON 有 11,057 条，入库 10,685 条，**372 条被 `parse.py` 的 `len(txt_norm)<8` 过滤**。
这 372 条不是「没有曲文」，而是**曲文被刮进了 title**：364 条 title 含句读且 ≥17 字，其中 142 条正文全空、312 条正文不足 8 字，故被判「过短」丢弃。
它们可在本地原文件里 100% 复原（见 D3/D4）。

## 六、无法判断的部分

- 41 条 FRAGMENTARY：源文本在句中截断（如「银须霜鬓，世。」），无第二来源可对校，无法判定原本有多长。
- 上游为「整理本（无底本声明）」，`provenance.base_edition` 无版本信息，无法判断某些短曲牌（20–25 字）是「本来就这么短」还是「被截」。
  本报告一律按「未发现缺文」记录，不宣称完整。
