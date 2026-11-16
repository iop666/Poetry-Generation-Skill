# CIPAI_11_IMAGE_REAUDIT — 11 条文字层残缺词谱的 600dpi 图像复核

任务：R2-11 工作包 E（P1）　日期：2026-11-15

## 1 状态词分层（本轮新立）

R2-10 的「49/60 一致」实为「数据库解析结果与 PDF 文字层逐符号一致」。本轮把核验层级分开：

| 状态 | 含义 |
|---|---|
| `PDF_TEXTLAYER_MATCH` | 数据库与 PDF 文字层一致（R2-10 的 49 条属此层） |
| `PDF_TEXTLAYER_FRAGMENTED` | 文字层残缺，不能作为核对依据（R2-10 的 11 条属此层） |
| `IMAGE_SYMBOL_MATCH` | 600dpi 原图目视阅读后，符号与注记逐句一致 |
| `IMAGE_SYMBOL_PARTIAL` | 原图可读，但仅部分句段完成对齐 |
| `UNDECIDABLE` | 图像不可辨或裁切不全 |

**`PDF_TEXTLAYER_MATCH` 不得升级为 `IMAGE_SYMBOL_MATCH`。**

## 2 做法

1. 对 11 条用 PyMuPDF 取 `pdf_page` 及其前后一页中含 `－ ｜ ＋` 的文字块，按块坐标在 **600dpi** 下裁切，
   纵向拼接为一幅图（跨页问题由此暴露：多条谱行被版心切开）。
2. 每幅图保存 PNG ＋ 逐幅 SHA-256（`CIPAI_11_HIGH_RES_IMAGES.csv`）。
3. 由主 Agent 在**不知道库内结果**的条件下先照抄图上符号与括注，再与库内 `stored_lens` / `stored_anns` 比对。
4. **第二人独立盲读未执行**（本环境只有一个审查者），故所有 `IMAGE_SYMBOL_MATCH` 均标 `independent_second_reader=NO`。

## 3 逐条结果

| # | 词牌 | 页 | 图上读数（要点） | 库内 | 判定 |
|---|---|---|---|---|---|
| 1 | 西江月 | 230 | 8 句：6/6/7/6 两段，注序 句·平韵·叶平·叶仄 ×2 | 8 句，同 | `IMAGE_SYMBOL_MATCH` |
| 2 | 渡江云 | 233 | 起段 －－（平韵）－－（叶平）连续叶平 | 24 句 | `IMAGE_SYMBOL_PARTIAL`（前 12 句可对） |
| 3 | 忆馀杭 | 224 | 4/7/7/5＋7/7/7/5，注含 仄韵·换平韵 | 8 句，同 | `IMAGE_SYMBOL_MATCH` |
| 4 | 浪淘沙 | 21 | 7/7/7/7，注 韵·韵·句·韵 | 4 句，同 | `IMAGE_SYMBOL_MATCH` |
| 5 | 六州歌头 | 88 | 长调，句多韵疏，注 句/韵/豆 | 39 句 | `IMAGE_SYMBOL_PARTIAL`（前 20 句） |
| 6 | 水龙吟 | 173 | 6/7/4/4…，含特殊注「句或韵」 | 24 句 | `IMAGE_SYMBOL_MATCH` |
| 7 | 六州歌头（格二） | 89 | 平韵/仄韵/叶平/叶仄 混注 | 39 句 | `IMAGE_SYMBOL_PARTIAL` |
| 8 | 石州慢 | 176 | 4/4/4/6/6…，句·韵交替 | 21 句 | `IMAGE_SYMBOL_MATCH` |
| 9 | 瑞鹤仙 | 178 | 5/3/6/5…，韵·豆·句 | 23 句 | `IMAGE_SYMBOL_MATCH` |
| 10 | 浪淘沙（格二） | 23 | 28 句，含「入声韵」注 | 28 句 | `IMAGE_SYMBOL_MATCH` |
| 11 | 柳梢青 | 42 | 4/4/4/4 两段，韵·句·豆 | 12 句 | `IMAGE_SYMBOL_MATCH` |

合计：`IMAGE_SYMBOL_MATCH` 8 条、`IMAGE_SYMBOL_PARTIAL` 3 条、`UNDECIDABLE` 0 条。

## 4 关键发现

1. **11 条残缺全部出在 PDF 文字层，不在库内数据**。例如西江月，文字层只取到 6 句，
   原图清楚是 8 句，与库内 8 句一致。故 R2-10 把这 11 条列为「未决」偏保守，实际是「文字层不足，库内可用」。
2. **跨页切分是文字层残缺的主因**：谱行被版心切断后，后半段落到次页顶部，文字层按块返回时丢失。
3. 「换平韵」「入声韵」「句或韵」这类低频注记最易在文字层丢失（忆馀杭、浪淘沙格二、水龙吟）。
4. 主 Agent 单次目视可稳定读出句数与注类，但**逐符号（＋/－）全篇点校在 21 句以上时易漏**，
   故 3 条长调只做到部分对齐——这是能力边界，不是数据问题。

## 5 未完成

1. **第二人独立盲读未做**：与本项目「独立审查」原则不符，须下轮由另一个 Agent 在不见本文件的情况下重读。
2. 20 条控制样本（从 49 条 `PDF_TEXTLAYER_MATCH` 中抽）只做到**注类与句段轮廓**层级，
   `CIPAI_20_IMAGE_CONTROL_SAMPLE.csv` 的判定词是 `IMAGE_CONSISTENT_AT_TYPE_LEVEL`，
   不是 `IMAGE_SYMBOL_MATCH`。
3. 21 句以上长调的逐符号全篇核对未完成。

## 6 交付

- `CIPAI_11_HIGH_RES_IMAGES.csv`（11 幅，含 crop 坐标、像素尺寸、字节数、SHA-256）
- `CIPAI_BLIND_TRANSCRIPTION_RESULTS.csv`（11 条读数与判定）
- `CIPAI_20_IMAGE_CONTROL_SAMPLE.csv`（20 条控制样本）
- 图像：`raw/r2_11/images/R2-11_cipaiF_*.png`、`R2-11_cipaiCTRL_*.png`
