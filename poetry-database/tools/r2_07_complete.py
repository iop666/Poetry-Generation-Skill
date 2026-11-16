#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-07 唯一权威报告：COMPLETE_REPORT.md（十六章）。"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database" / "poetry.db"
OUT = ROOT / "reports" / "tasks" / "2026-11-14" / "R2-07"
CON = sqlite3.connect(DB)
Q = lambda s, a=(): CON.execute(s, a).fetchall()
ONE = lambda s, a=(): CON.execute(s, a).fetchone()[0]

ent = ONE("SELECT COUNT(*) FROM cipai_entities_r2_07")
frm = ONE("SELECT COUNT(*) FROM cipai_forms_r2_07")
labels = dict(Q("SELECT pattern_label,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1"))
sec_ent = Q("SELECT section_name,COUNT(*) FROM cipai_entities_r2_07 GROUP BY 1 ORDER BY 2 DESC")
sec_frm = dict(Q("SELECT section_name,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1"))
tone = dict(Q("SELECT rhyme_tone,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1"))
dm = dict(Q("SELECT declared_match,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1"))
verd = dict(Q("SELECT verdict,COUNT(*) FROM cipai_audit_r2_07 GROUP BY 1"))
stanza = dict(Q("SELECT stanza_structure,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1"))
tests = json.loads((OUT / "test_results.json").read_text(encoding="utf-8"))
npass = sum(1 for t in tests if t["status"] == "PASS")
n_src = ONE("SELECT COUNT(*) FROM cipai_form_sources_r2_07")
chars_total = ONE("SELECT SUM(total_characters) FROM cipai_forms_r2_07")
r06 = Path("reports/tasks/2026-11-13/R2-06/COMPLETE_REPORT.md")


def tbl(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
    out += ["| " + " | ".join("" if x is None else str(x) for x in r) + " |" for r in rows]
    return out


L: list[str] = []
A = L.append

A("# COMPLETE_REPORT —— R2-07《唐宋词格律》词格逐项核验与数据库建设")
A("")
A(f"> 任务编号：R2-07　｜　执行日期：2026-11-14　｜　执行依据：`POETRY-AUDIT-2026-11-14-R2-06`")
A("> 唯一权威报告。分报告 8 份同目录存放，数据全部来自 `database/poetry.db` 实时查询。")
A("")
A("**SELF_STATUS: PARTIAL** —— 196 条词格全部结构化并自洽校验，但未做异本对勘，`EDITION_VERIFIED=0`。")
A("")

# 1
A("## 一、项目执行概况")
A("")
A("| 项 | 内容 |")
A("|---|---|")
A("| 本轮目标 | 把《唐宋词格律》目録级的 153 调、196 个格标题，做成可逐条核验、可追溯页码、可复算的结构化数据 |")
A("| 主来源 | 龙榆生《唐宋词格律》，上海古籍出版社 1978 年版（本地影印 PDF，270 页，正文物理 16–250，印刷 1–235，偏移 15） |")
A("| 文本 | PDF 自带 OCR 文字层，未经二次 OCR |")
A("| 外部参照 | 龙榆生纪念网站 目录／字数表／凡例（GB2312 抓取后程序解析，只作交叉核对） |")
A(f"| 产出 | 词牌实体 **{ent}**、词格 **{frm}**、谱行溯源 **{n_src}** 行、派生关系 71 条、审计 196 条、字数审计 13 条、外部差异 15 条、特殊案例 12 个、原图核验 6 次 |")
A(f"| 测试 | {len(tests)} 项，PASS {npass} / FAIL {len(tests)-npass} |")
A("| 未做 | 不改 `gedou.py`、不改 `cipai_specs`、不建知识体系、不封装 Skill |")
A("")

# 2
A("## 二、执行前检查与三项整改")
A("")
A("审核书指出上一轮未给出报告位置，并遗留两个状态问题。三项均已处理：")
A("")
A("### 2.1 R2-06 报告的真实位置")
A("")
if r06.exists():
    b = r06.read_bytes()
    A("| 项 | 值 |")
    A("|---|---|")
    A("| 文件名 | `COMPLETE_REPORT.md` |")
    A("| 项目内相对路径 | `poetry-database/reports/tasks/2026-11-13/R2-06/COMPLETE_REPORT.md` |")
    A(f"| 绝对路径 | `{r06.resolve()}` |")
    A(f"| 大小 | {len(b):,} 字节（{len(b)/1024:.1f} KB） |")
    A(f"| SHA-256 | `{hashlib.sha256(b).hexdigest()}` |")
    A(f"| 行数 | {len(b.decode('utf-8').splitlines())} |")
else:
    A("R2-06 报告文件未找到。")
A("")
A("### 2.2 《词学十讲》第六讲：改为来源缺口状态")
A("")
A("R2-06 报 10/10 READ，但第六讲 `gate_pass=0`（EPUB 丢失后半例词）。审核要求：未补齐则不得记 READ。")
A("")
A("已改为 `READ_WITH_SOURCE_GAP`，`gate_pass` 保持 0；其余九讲维持 `READ` / `gate_pass=1`。")
A("本轮**没有**从其他版本补文，因此不申报 10/10 完成。")
A("")
A("### 2.3 合订本第 432 页的分类")
A("")
A("PDF 共 432 页（0 基 0–431）。审核所指「第 432 页」＝末页 `pdf_page=431`。")
A("原图核验：该页为「主要术语、人名、论著索引」的最后一页，印刷页码 **423**，PaddleOCR 文本 807 字。")
A("分类为 `索引`，已补 `exclude_reason` 与 `page_map_notes_r2_07` 说明。")
A("")
A("同时修正两处：`pdf_page=182`（A 部分末页）空白页缺原因；`415–431` 索引页统一标注「已读，PaddleOCR 文本」。")
A("")
A("### 2.4 词格数：194 → 196 的差异说明")
A("")
A("R2-06 报「194 条」，本轮全量重扫得 **196 条**。差额 2 条为《念奴娇》的「变 格 一」「变 格 二（平韵格）」。")
A("R2-06 的标记扫描漏掉了这两行（标记在页内被前一词格的例词块截断）。")
A("**196 是本地原书的格标题总数**，不是审核误记；下文一律用 196，并保留 194 的来源以备核对。")
A("")

# 3
A("## 三、本轮实际成果")
A("")
A("1. **建立词牌实体层**：153 个实体，带韵式类别、原书页、别名、格数、是否标定格。")
A("2. **建立词格层**：196 条，每条 24 个字段（格别原文、字数、句长、平仄串、韵位、韵声、句读、附注、例词、双页码、谱行原文、核验状态）。")
A("3. **逐行溯源**：1,392 行（196 标题行 + 1,196 谱行），每行带页码与原文。")
A("4. **机械复算**：字数＝逐句字数之和＝平仄符号数，196 条全对；韵位不越界。")
A("5. **与原书自述字数比对**：183 一致、12 不一致、1 无自述；13 条逐条给结论与依据。")
A("6. **外部交叉核对**：词牌名 153=153 完全一致；条目 203 vs 196，差额 7 条全部归类；15 条差异入表。")
A("7. **12 个特殊案例**研究卡（浣溪沙／南乡子／浪淘沙／临江仙／木兰花／生查子／满江红／念奴娇／水龙吟／六州歌头／沁园春／宝鼎现）。")
A("8. **6 次原图核验**，其中《钗头凤》确证为**原书排印脱一符号**（非 OCR）。")
A("")
A("### 历史累计（不是本轮新增）")
A("")
A("| 项 | 累计 |")
A("|---|---|")
A("| 王力合订本 A/B/C/D 通读 | 106,460 汉字，31/31 单元 READ（R2-05、R2-06） |")
A("| 《词学十讲》 | 74,652 字，9 讲 READ + 1 讲 READ_WITH_SOURCE_GAP |")
A("| 结构化理论条目 | 77 条（R2-05 的 38 + R2-06 的 39） |")
A("| 词牌实体／词格（本轮新增） | 153 ／ 196 |")
A("")

# 4
A("## 四、153 个词牌清单")
A("")
A("> 「格」为该实体下词格数；「定格」列标 `是/否` 表示原书是否给出「定格」标题。")
A("> 18 调无定格是原书体例（直接以「格一」起首），不是缺数据。")
A("")
rows = Q("""SELECT cipai_name,section_name,n_form,printed_page,has_dingge,declared_chars
            FROM cipai_entities_r2_07 ORDER BY order_no""")
L += tbl(["词牌", "韵式", "格", "印页", "定格", "自述字数"],
         [[a, b, c, d, "是" if e else "否", f] for a, b, c, d, e, f in rows])
A("")
A(f"合计 **{len(rows)}** 个词牌。")
A("")

# 5
A("## 五、196 条词格清单")
A("")
A("> 韵数／声＝韵脚条数与声调；页为物理页（印刷页＝物理页−15）。")
A("> 完整 12 项明细见 `CIPAI_FORM_AUDIT.md`。")
A("")
fr = Q("""SELECT form_id,cipai_name,pattern_label,total_characters,sentence_count,
                 rhyme_count,rhyme_tone,section_name,printed_page
          FROM cipai_forms_r2_07 ORDER BY form_id""")
L += tbl(["ID", "词牌", "格别", "字数", "句", "韵", "声", "韵式", "印页"],
         [[a, b, c, d, e, f, g, h, i] for a, b, c, d, e, f, g, h, i in fr])
A("")
A(f"合计 **{len(fr)}** 条，字数合计 {chars_total:,}。")
A("")

# 6
A("## 六、每条词格的核验状态")
A("")
A("### 6.1 总判定")
A("")
L += tbl(["判定", "条数"], [[k, v] for k, v in verd.items()])
A("")
A("### 6.2 字数自洽")
A("")
L += tbl(["结果", "条数"], [["与自述一致", dm.get(1, 0)],
                            ["与自述不一致", dm.get(0, 0)],
                            ["原书无自述", dm.get(None, 0)]])
A("")
A(f"自洽率 {dm.get(1,0)/frm*100:.1f}%。")
A("")
A("### 6.3 13 条不一致／无自述的逐条结论")
A("")
aud = Q("""SELECT form_id,cipai_name,pattern_label,computed,declared,delta,verdict,evidence,resolved
           FROM cipai_count_audit_r2_07 ORDER BY form_id""")
L += tbl(["ID", "词牌", "格别", "谱行", "自述", "差", "结论", "依据", "已解"],
         [[a, b, c, d, e, f, g, h, "是" if i else "否"] for a, b, c, d, e, f, g, h, i in aud])
A("")
A("### 6.4 上下片结构")
A("")
L += tbl(["判定", "条数"], [[k, v] for k, v in stanza.items()])
A("")
A("原书多数词牌不显式分片，本轮只在原书明言（上下片／双调／重填）或两半完全同构时拆分；")
A("「按字数推断」仅用于 ≤44 字且原书未言的单调小令，已标推断来源。")
A("")

# 7
A("## 七、五种韵式统计")
A("")
A("### 7.1 两个口径必须分开")
A("")
A("《凡例》01 定五类，但**同一词牌的不同格可分属不同韵式**（如《念奴娇》变格二标平韵）。")
A("因此有两个数，不可相加或互换：")
A("")
L += tbl(["韵式", "词牌数 cipai_count", "词格数 cipai_form_count"],
         [[s, n, sec_frm.get(s, 0)] for s, n in sec_ent]
         + [["合计", sum(n for _, n in sec_ent), sum(sec_frm.values())]])
A("")
A("### 7.2 韵脚声调")
A("")
L += tbl(["声调", "条数"], [[k, v] for k, v in tone.items()])
A("")
A("来源规则：格标题明言「平韵格／仄韵格」者**标签优先**；标题写「平仄韵互叶／递换」记「平仄」；")
A("仅写「（韵）」者按句末字与所属类推定。两处标签与谱行冲突（《念奴娇》变格二、《满江红》格二）已按标签处理并留痕（SD-14／SD-15）。")
A("")

# 8
A("## 八、特殊词牌研究（12 卡）")
A("")
for cid, nm, qs, fd, fs, pg in Q("""SELECT case_id,cipai_name,question,finding,forms_summary,source_pages
                                    FROM cipai_special_cases_r2_07 ORDER BY case_id"""):
    A(f"**{cid}《{nm}》**　问：{qs}")
    A("")
    A(f"　答：{fd}")
    A("")
    A(f"　数据：{fs}（物理页 {pg}）")
    A("")
A("### 8.1 一个结构性发现：「变格」有两种身份")
A("")
A("| 身份 | 写法 | 是否计入词格 | 条数 |")
A("|---|---|---|---|")
A("| 格标题 | 独立成行的「变 格」「变 格 一」 | **计入** | 9 + 变格一 + 变格二 |")
A("| 例词标签 | 「例四（变格）」 | **不计入** | 5 处 |")
A("")
A("这解释了外部目录为何多出 3 条「变格」条目——网站把例词层的变格也立成了条目。")
A("")

# 9
A("## 九、外部交叉核对")
A("")
A("### 9.1 可对齐")
A("")
A(f"- 词牌名：外部 153、本地 {ent}，**集合完全相同**（差集 0）。")
A("- 五类韵式名称与顺序完全一致。")
A("- 多数词牌字数一致。")
A("")
A("### 9.2 条目总数：203 vs 196")
A("")
A("| 类别 | 条数 | 说明 |")
A("|---|---:|---|")
A("| 双调另立条目 | 3 | 《南歌子》52、《忆江南》54、《江城子》70（原书只作「例（双调）」） |")
A("| 变格另立条目 | 3 | 《水龙吟》《石州慢》《满江红》94 字（原书作「例（变格）」或仅附注） |")
A("| 归类不同 | 1 | 《诉衷情》44 字定格本版未见独立条目 |")
A("| 合计 | 7 | 口径差异，不是本地缺数据 |")
A("")
A("### 9.3 15 条差异")
A("")
d = Q("""SELECT diff_id,cipai_name,item,local_value,external_value,page,cause,confirmed,adopted
         FROM cipai_source_differences_r2_07 ORDER BY diff_id""")
L += tbl(["ID", "词牌", "项目", "本地", "外部", "页", "原因", "确认", "采用"],
         [[a, b, c, dd, e, f, g, "是" if h else "否", i] for a, b, c, dd, e, f, g, h, i in d])
A("")

# 10
A("## 十、数据库结构")
A("")
A("| 表 | 行数 | 用途 |")
A("|---|---:|---|")
for t, use in [("cipai_entities_r2_07", "词牌实体（153）"),
               ("cipai_forms_r2_07", "词格（196，24 字段）"),
               ("cipai_form_sources_r2_07", "谱行逐行溯源（1,392）"),
               ("cipai_form_variants_r2_07", "别名与派生调关系（71）"),
               ("cipai_audit_r2_07", "逐格 12 项核验（196）"),
               ("cipai_count_audit_r2_07", "字数冲突逐条结论（13）"),
               ("cipai_source_differences_r2_07", "外部差异（15）"),
               ("cipai_special_cases_r2_07", "特殊案例（12）"),
               ("ocr_image_checks_r2_07", "原图核验记录（6）"),
               ("page_map_notes_r2_07", "页码映射补充说明（3）")]:
    A(f"| `{t}` | {ONE(f'SELECT COUNT(*) FROM {t}')} | {use} |")
A("")
A("旧表一律未改：`cipai_specs` 76 行、`cipai_index` 144 行、`works` 375,399 行、`book_pages` 2,010 行、`book_pages_paddle` 1,691 行。")
A("")

# 11
A("## 十一、全部文件变更")
A("")
A("### 新增脚本")
A("")
L += tbl(["文件", "作用"], [
    ["`tools/r2_07_forms.py`", "词格抽取：定位标题、识别格标记、解析谱行符号与括注、机械复算字数/句数/韵位"],
    ["`tools/r2_07_finalize.py`", "收尾：韵式校正、字数审计、外部差异、原图核验表、12 案例"],
    ["`tools/r2_07_tests.py`", "32 项一致性测试，输出 `test_results.json`"],
    ["`tools/r2_07_reports.py`", "8 份分报告生成"],
    ["`tools/r2_07_complete.py`", "本报告生成"],
])
A("")
A("### 新增数据")
A("")
L += tbl(["文件", "内容"], [
    ["`raw/r2_07_forms.json`", "196 条词格的完整抽取结果（含谱行块）"],
    ["`raw/r2_07_finalize.json`", "审计结论与统计快照"],
    ["`raw/r2_07_external.json`", "外部目录解析结果（203 条）"],
])
A("")
A("### 报告")
A("")
L += tbl(["文件", "内容"], [
    ["`COMPLETE_REPORT.md`", "本文件，十六章"],
    ["`CIPAI_ENTITY_REPORT.md`", "153 实体清单与统计"],
    ["`CIPAI_FORM_AUDIT.md`", "196 格清单、12 项核验、抽样明细"],
    ["`CIPAI_RHYME_CLASS_REPORT.md`", "五类韵式的两种口径"],
    ["`SOURCE_DIFFERENCE_REPORT.md`", "203/196 与 15 条差异"],
    ["`SPECIAL_CASE_REPORT.md`", "12 个案例卡 + 「变格」两义"],
    ["`OCR_VERIFICATION_REPORT.md`", "符号自洽校验与 6 次原图核验"],
    ["`TEST_RESULTS.md`", "32 项测试逐条记录"],
    ["`SOURCE_AUDIT.md`", "来源、版本、采信规则"],
    ["`FILE_MANIFEST.md`", "文件清单与 SHA-256"],
    ["`test_results.json`", "测试原始数据"],
])
A("")

# 12
A("## 十二、测试结果")
A("")
A(f"**PASS {npass} / FAIL {len(tests)-npass} / PASS 率 {npass/len(tests)*100:.0f}%**（{len(tests)} 项，全部重跑）")
A("")
L += tbl(["ID", "项目", "结果"], [[t["id"], t["name"], t["status"]] for t in tests])
A("")
A("测试覆盖审核书第九节十项要求，映射表见 `TEST_RESULTS.md`。")
A("")
A("**测试不能证明什么**：只证明数据内部自洽与结构完整，不证明 196 条谱行逐字无误，不证明格别判断符合学术定论。")
A("")

# 13
A("## 十三、未完成项")
A("")
A("| 项 | 现状 | 原因 |")
A("|---|---|---|")
A("| 异本对勘 | 未做 | 只有 1978 上海古籍一种影印本，`EDITION_VERIFIED=0` |")
A("| 逐调人工校读 | 只做 6 次点状核验 | 196 条全部人工校读需另立轮次 |")
A("| 六州歌头 格二 144/143 | 未解 | 谱行密集，380dpi 无法稳定计数 |")
A("| 荷叶杯 格二 50/52 | 未解 | 与外部计算口径不同 |")
A("| 钗头凤 59/60/72 | 保留原字形 | 图证为原书排印脱漏，不补符号 |")
A("| 《词学十讲》第六讲 | READ_WITH_SOURCE_GAP | 未取得合法补本 |")
A("| 上下片分界 | 41 条 UNKNOWN | 原书未明言且两半不同构，不猜 |")
A("| 平仄符号语义 | 未与韵书对校 | 属 R2-09 韵书研究范围 |")
A("")

# 14
A("## 十四、自我审计")
A("")
A("本轮犯过并已修正的错误，全部留痕：")
A("")
A("1. **韵式标签判定把「平仄韵互叶」误判为「仄」**：`\"仄韵\" in note` 命中了「平仄韵」的子串，导致《六州歌头》格二、《六州歌头》格三一度被写成单一仄韵。已改为先判「平仄」再判平/仄。")
A("2. **派生调初版 0 条**：按「减字／摊破／偷声」名称前缀去找独立词牌，但原书根本没把这些立为词牌，而是作《木兰花》的格三／格四／格五。改为从格标题括注提取，得 9 条派生 + 62 条又名。")
A("3. **钗头凤先疑 OCR，后证为排印**：初判 `OCR_NEAR_MISS`，900dpi 原图核验后改为 `ORIGINAL_PRINT_OMISSION`。这条纠正本身是本轮方法论的收获。")
A("4. **字数比对的初版把「九十」当「十四」**：中文数字解析未处理「百」位，且描述区取窗过窄，误把邻调的「三字」当成本调字数。已改为在整个描述区收集全部「××字」候选并逐个比对。")
A("5. **R2-06 漏采 2 条格标记**：本轮全量重扫才发现《念奴娇》「变 格 一／二」。这说明按区间切分的扫描会漏掉页面边界处的标记。")
A("")
A("**关于「已完成」的自我限制**：")
A("")
A("- 本轮没有把任何一条标为 `VERIFIED`；最高状态是 `PARSED`（192 条）与 `CHECK_REQUIRED`（4 条）。")
A("- 未解决的 3 处字数差异没有强行统一，也没有按「应该有几个字」回补符号。")
A("")

# 15
A("## 十五、下一步建议")
A("")
A("1. **R2-08（审核已定）**：王力《汉语音韵学》系统阅读，建立中古音、反切、声韵调的基本框架。")
A("2. **词格数据的两项收尾**（建议并入后续轮次，不单独开轮）：")
A("   - 对 196 条做分层人工校读：先校 30 条同调多体，再校 18 条无定格，最后余下定格。")
A("   - 六州歌头／荷叶杯两处差异，待取得第二种版本后对勘。")
A("3. **不建议现在做的事**：把 196 条谱行接进格律引擎。谱行虽内部自洽，但尚未逐条校读，直接接入会把未校数据变成「权威规则」。")
A("")

# 16
A("## 十六、外部审核请求")
A("")
A("请重点核以下四点：")
A("")
A(f"1. **196 与 194 的口径**：本轮认定 196 为本地原书格标题数，194 系 R2-06 漏采《念奴娇》两条变格。")
A("2. **203 与 196 的差额 7 条**是否同意按「双调 3 + 变格 3 + 归类 1」处理。")
A("3. **《钗头凤》判为原书排印脱漏**是否成立（图证：下片第三句 6 符号，上片同位置 7 符号，自述 60 字）。")
A("4. **韵式标签优先于谱行推定**是否可作为后续规则（涉及《念奴娇》变格二、《满江红》格二）。")
A("")
A("---")
A("")
A("### 报告文件信息")
A("")
p = OUT / "COMPLETE_REPORT.md"
A("| 项 | 值 |")
A("|---|---|")
A("| 文件名 | `COMPLETE_REPORT.md` |")
A("| 项目内相对路径 | `poetry-database/reports/tasks/2026-11-14/R2-07/COMPLETE_REPORT.md` |")
A(f"| 工作目录绝对路径 | `{p.resolve()}`（生成时自动填入） |")
A("| 大小 / SHA-256 | 见同目录 `FILE_MANIFEST.md`（本文件生成后再计算，避免自指） |")
A("")
A("已按制度停止，等待外部审核。不自行进入知识体系建设，不修改格律引擎。")

(OUT / "COMPLETE_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"COMPLETE_REPORT.md 已生成：{len(L)} 行")
CON.close()
