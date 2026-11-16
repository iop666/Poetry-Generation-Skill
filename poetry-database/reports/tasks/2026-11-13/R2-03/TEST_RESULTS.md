# TEST_RESULTS —— R2-03 实际运行记录

生成时间：2026-11-13 17:47:02
环境：macOS / Python 3.13.12 / pypdf 7.0.1 / pymupdf 2.1 / Swift(Vision) / SQLite

## 一、命令与退出码

| # | 命令 | 退出码 | 结果 |
|---|---|---|---|
| 1 | `python3 tools/extract_native.py` | 0 | 唐宋词格律 270 页；词学十讲 33 章；古代汉语常识 16 章 |
| 2 | `python3 tools/ocr_pdf.py --book wangli_shicilv` | 0 | 432/432 页 |
| 3 | `python3 tools/ocr_pdf.py --book wangli_yinyunxue` | 0 | 476/476 页 |
| 4 | `python3 tools/ocr_pdf.py --book wangli_tongyuan` | 0 | 783/783 页，460 s |
| 5 | `python3 tools/books_schema.py` | 0 | book_pages 2,010 |
| 6 | `python3 tools/parse_cipai_specs.py` | 0 | 76 调 / 66 调有词作 |
| 7 | `python3 tools/seed_reading.py` | 0 | 16 claims / 8 notes / 6 progress |
| 8 | `python3 tools/relabel_audit.py` | 0 | 166 / 27 / 93 |
| 9 | `python3 tools/coverage.py` | 0 | 12 期，缺口 1（辽代） |

## 二、OCR 引擎对比实验（同一页 p41）

| 配置 | 平对仄 | 「瓜」出现次数 | 页均置信 |
|---|---|---|---|
| rev3 zh-Hant 无纠正 | ✗ | 9 | 0.58 |
| rev3 zh-Hans 无纠正 | ✗ | 9 | 0.58 |
| **rev2 zh-Hant 无纠正** | **✓** | **0** | **0.93** |
| rev1 zh-Hant | 乱码 | 0 | 0.31 |

## 三、OCR 覆盖与置信

| 书 | 页数 | 完成 | 页均置信 | <0.85 页 | 空页 |
|---|---|---|---|---|---|
| 诗词格律 | 432 | 432 | 0.82 | 215 | 2 |
| 汉语音韵学 | 476 | 476 | 0.83 | 186 | 0 |
| 同源字典 | 783 | 783 | 0.74 | 729 | 0 |

## 四、数据库一致性

| 检查 | 结果 |
|---|---|---|
| book_items | 6 |
| book_pages | 2010 |
| book_chapters | 49 |
| theory_claims | 16 |
| cipai_specs | 76 |
| 词牌谱中有实际词作者 | 66 / 76 |
| works 总数（未变） | 375,399 |

## 五、已知未覆盖

1. 《诗经韵读》《楚辞韵读》文件缺失，未解析。
2. 词谱表格页（诗词格律概要卷下）OCR 不可用，未采。
3. 135 处定格仅提取 76 处。
4. 未与任何影印本对勘，EDITION_VERIFIED = 0。
