# RHYME_SYSTEM_IDENTITY_DESIGN — 六套韵书标识体系重新设计

任务：R2-11 工作包 C（P0）　日期：2026-11-15

## 1 问题

- `ph_readings_r2_08.system` 只有 4 个实际取值（old_chinese / middle_chinese / regulated_verse / ci_rhyme / yuan_qu / modern_rhyme 中，前两者为空）。
- `middle_chinese` 一个值下同时装着《广韵》与《集韵》共 51,392 行，无法区分来源书。
- 旧测试 T60 用 `count(distinct system)=6` 冒充「六套体系未被合并」，实际上是**用错了维度**：
  system 表示的是「历史音系大类」，不是「韵书身份」。

## 2 三个维度的定义

| 维度 | 回答的问题 | 取值示例 | 允许共享 |
|---|---|---|---|
| `source_book_id` | 这条记录出自**哪一本书** | GUANGYUN / JIYUN / PINGSHUI_YUN / CILIN_ZHENGYUN / ZHONGYUAN_YINYUN / ZHONGHUA_XINYUN | 否，一书一值 |
| `rhyme_system_id` | 这本书用的是**哪一套分类规范**（韵目数、四声格局） | GY_206 / JY_206 / PS_106 / CL_19 / ZY_19 / XY_14 | 否，一规范一值 |
| `phonological_family_id` | 它属于**哪个历史音系大类** | MIDDLE_CHINESE / TRADITIONAL_POETIC_RHYME / YUAN_DYNASTY_NORTHERN_CHINESE / MODERN_MANDARIN / ANCIENT_CHINESE | **是**，可多书共享 |

关键点：**「六套韵书」是六本书，不是六个音系时期。**
广韵与集韵同属中古音，但必须分开查询；平水韵与词林正韵同属传统诗韵大类，但韵目数 106 与 19 部不同层。

## 3 六本书的档案（`rhyme_source_books_r2_11`）

| source_book_id | 书 | 时代 | 底本/依据 | 韵数 | 条目/字数 | 证据等级 | 主要限制 |
|---|---|---|---|---|---|---|---|
| GUANGYUN | 广韵 | 北宋 1008 | 四库本《原本广韵》维基转录 | 206 | 3,730 小韵 / 25,619 条 | SOURCE_TRANSCRIPTION | 未对影印本 |
| JIYUN | 集韵 | 北宋 1039 | 文渊阁四库本维基转录（附 DJVU 叶码） | 206 | 4,169 小韵 | SOURCE_TRANSCRIPTION | 小韵数为算法口径；4 页曾失败覆盖 |
| PINGSHUI_YUN | 平水韵 | 金 1229 | 维基文库《平水韻》 | 106 | 首行 8,985 字 | SOURCE_TRANSCRIPTION | 诗韵分类，非韵书原书 |
| CILIN_ZHENGYUN | 词林正韵 | 清 | 维基文库转录 | 19 部 | 5,563 行 | SOURCE_TRANSCRIPTION | 以部/声调组织，无小韵结构 |
| ZHONGYUAN_YINYUN | 中原音韵 | 元 1324 | 维基文库转录 | 19 部 | 5,731 行 | SOURCE_TRANSCRIPTION | 入派三声，与其他书不同层 |
| ZHONGHUA_XINYUN | 中华新韵 | 2005 | 子夜星转录简表 | 14 | 7,597 字 | SOURCE_TRANSCRIPTION | 现代普通话，非历史音系 |

## 4 稳定韵目 ID（`rhyme_group_identity_r2_11`，570 条）

| 前缀 | 数量 | 形式 | 例 |
|---|---|---|---|
| GUANGYUN_V{卷}_{韵号} | 206 | 含卷号，因广韵韵号按卷重编 | `GUANGYUN_V1_001`（東） |
| JIYUN_{序号} | 206 | 按韵目原序 | `JIYUN_001`（東第一） |
| PINGSHUI_{序号} | 106 | 平水 106 韵 | `PINGSHUI_001` |
| CILIN_{部号} | 19 | 十九部 | `CILIN_011` |
| ZHONGYUAN_{部号} | 19 | 十九部 | `ZHONGYUAN_001` |
| XINYUN_{序号} | 14 | 十四韵 | `XINYUN_013`（十三支） |

**禁止**再用「第 11 部」「第十一部」这类字符串做关联键——它们在不同书里指的不是同一批字。
每条 ID 同时保存 `display_name`、`source_name`、`normalized_aliases`，别名用于检索，不用于关联。

## 5 旧值映射（`rhyme_identity_mapping_r2_11`）

| 旧值 | 新归属 | 行数 | 处置 |
|---|---|---|---|
| middle_chinese | GUANGYUN(GY_206) / JIYUN(JY_206) | 51,392（两书合计） | 必须按 `source_book` 字段拆分；本轮只建映射，未改历史表 |
| regulated_verse | PINGSHUI_YUN(PS_106) | 10,662 | 直接对应 |
| ci_rhyme | CILIN_ZHENGYUN(CL_19) | 11,382 | 直接对应 |
| modern_rhyme | ZHONGHUA_XINYUN(XY_14) | 7,216 | 派生记录，缺十三支 173 条 |
| yuan_qu | ZHONGYUAN_YINYUN(ZY_19) | 0（在 ph_readings 中） | 实际数据在 `ph_zhongyuan_r2_09`（5,731 行），未并入统一 readings |
| old_chinese | —— | 0 | 未建（ANCIENT_CHINESE），来源未取得 |

## 6 六系统查询复核（摘要，详见 `SIX_SYSTEM_QUERY_REAUDIT.md`）

取 12 个字（東風月雪人山水花白石竹去），各查六书，另加「上古音」一列如实返回 `NO_DATA`，共 90 行。
要点：

- 广韵、集韵命中字形都是**小韵首**；非小韵首字（如「白」「石」在广韵中不是小韵首）
  返回 `NOT_AS_XIAOYUN_HEAD`／`NON_HEAD_ENTRY`，不是「无此字」。
- 平水韵、词林正韵、中原音韵、中华新韵可返回韵/部与声调。
- 中华新韵 3 字不在简表（常用字表覆盖有限），标 `NOT_IN_JIANBIAO`，不伪造。
- 每行都带 `evidence_level` 与 `derived` 标记，**派生数据不与原书记录混排**。

## 7 未完成

1. `ph_readings_r2_08` 未拆分，只在映射表记录应拆；改历史表需外部授权。
2. 广韵/集韵的字级覆盖只到「条目字头」，未做「任意汉字在广韵中属何韵」的全量字表
   （原书非字头字无独立韵目信息，需另建字表级索引）。
3. 上古音仍为 `NO_DATA`。
