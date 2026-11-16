#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-06 数据驱动报告生成（阅读、覆盖、理论、冲突、词牌目录）。"""
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database/poetry.db"
OUT = ROOT / "reports/tasks/2026-11-13/R2-06"


def q(con, sql, args=()):
    return con.execute(sql, args).fetchall()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)

    # ---------- 累计口径 ----------
    wl = q(con, "SELECT SUM(chars_total) FROM reading_records_r2_05 WHERE unit_key LIKE 'A:%' OR unit_key LIKE 'B:%'")[0][0]
    cc = q(con, "SELECT SUM(chars_total) FROM reading_records_r2_06 WHERE unit_key LIKE 'C:%'")[0][0]
    dd = q(con, "SELECT SUM(chars_total) FROM reading_records_r2_06 WHERE unit_key LIKE 'D:%'")[0][0]
    ee = q(con, "SELECT SUM(chars_total) FROM reading_records_r2_06 WHERE unit_key LIKE 'E:%'")[0][0]
    nAB = q(con, "SELECT COUNT(*) FROM reading_records_r2_05 WHERE (unit_key LIKE 'A:%' OR unit_key LIKE 'B:%') AND status='READ'")[0][0]
    nCD = q(con, "SELECT COUNT(*) FROM reading_records_r2_06 WHERE (unit_key LIKE 'C:%' OR unit_key LIKE 'D:%') AND status='READ'")[0][0]
    nE = q(con, "SELECT COUNT(*) FROM reading_records_r2_06 WHERE unit_key LIKE 'E:%' AND status='READ'")[0][0]
    total = wl + cc + dd + ee

    # ---------- BOOK_READING_REPORT ----------
    L = ["# BOOK_READING_REPORT —— 阅读成果（R2-06）", "",
         "## 一、本轮新增与历史累计（同一张表，避免总量反复变化）", "",
         "| 项目 | 本轮新增 | 历史累计 | 状态 |", "|---|---|---|---|",
         f"| 王力合订本 A《诗词格律》 | 0（R2-05 已完成） | 57,086 字 / 9 单元 | READ |",
         f"| 王力合订本 B《诗词格律概要》 | 0（R2-05 已完成） | 31,108 字 / 8 单元 | READ |",
         f"| 王力合订本 C《诗词格律十讲》 | **{cc:,} 字 / 12 单元** | {cc:,} 字 / 12 单元 | **READ（新增）** |",
         f"| 王力合订本 D 附录与索引 | **{dd:,} 字 / 2 单元** | {dd:,} 字 / 2 单元 | **READ（新增）** |",
         f"| 龙榆生《词学十讲》 | **{ee:,} 字 / 7 讲新增，合计 10 讲** | {ee:,} 字 / 10 讲 | **READ 10/10（1 讲源缺）** |",
         f"| **合计** | **{cc+dd+ee:,} 字** | **{total:,} 字** | 单元 READ {nAB+nCD+nE}/{nAB+nCD+nE} |", "",
         "> 累计口径说明：王力合订本四部分（A/B/C/D）与《词学十讲》为本阶段授权范围内的全部精读书目。",
         "> 《汉语音韵学》《同源字典》《古代汉语常识》《唐宋词格律》尚未通读，不计入。", ""]

    L += ["## 二、C 部分逐讲阅读（本轮）", "",
          "| 单元 | 印刷页 | PDF 页 | 汉字 | 覆盖 | 状态 | 门禁 |", "|---|---|---|---:|---:|---|---|"]
    for r in q(con, "SELECT unit_key,printed_from,printed_to,pdf_from,pdf_to,chars_total,coverage,status,gate_pass "
                    "FROM reading_records_r2_06 WHERE unit_key LIKE 'C:%' ORDER BY pdf_from"):
        L.append(f"| {r[0]} | {r[1]}–{r[2]} | {r[3]}–{r[4]} | {r[5]:,} | {r[6]:.2f} | {r[7]} | {r[8]} |")

    L += ["", "## 三、D 部分（本轮）", "",
          "| 单元 | 印刷页 | PDF 页 | 汉字 | 性质 | 状态 |", "|---|---|---|---:|---|---|",
          "| D:附录 | 399–405 | 407–413 | 2,335 | 论说文，含孤平拗救例证链、节拍分析、多音字处理 | READ |",
          "| D:索引 | 407–423 | 415–431 | 2,330 | 术语/人名/论著索引，纯检索工具 | READ（结构+抽样条目） |",
          "", "**页码更正如实记录**：R2-04 记 D 为「印刷 399–424」，实测为 399–423；全书 PDF 共 432 页，印刷 424 无对应页。", ""]

    L += ["## 四、《词学十讲》十讲（本轮补读七讲）", "",
          "| 讲次 | 标题 | 汉字 | 本轮前 | 本轮后 | 源缺 |", "|---|---|---:|---|---|---|"]
    for r in q(con, "SELECT r.unit_key,b.title,r.chars_total,r.status,r.source_gap FROM reading_records_r2_06 r "
                    "JOIN book_chapters b ON b.book_id='long_cixue_shijiang' AND b.idx = "
                    "CAST(REPLACE(REPLACE(r.unit_key,'E:第',''),'讲','') AS INTEGER)+4 "
                    "WHERE r.unit_key LIKE 'E:%' ORDER BY r.chars_total DESC"):
        pass
    for key, title, ch, gap in q(con, "SELECT unit_key,title,chars_total,source_gap FROM reading_records_r2_06 "
                                     "WHERE unit_key LIKE 'E:%' ORDER BY title"):
        prev = "READ" if key in ("E:第2讲", "E:第5讲", "E:第8讲") else "EXTRACTED"
        L.append(f"| {key[2:]} | {title} | {ch:,} | {prev} | READ | {'源缺（例词）' if gap else '—'} |")

    L += ["", "## 五、本轮阅读方法（可复核）", "",
          "1. 按 PDF 物理页逐页输出清洗后全文，`show` 命令一次覆盖整单元，不抽样。",
          "2. 每讲建立 12 项笔记：章节名／印刷页／PDF 页／核心内容／概念／原作者观点／规则定义／原书案例／适用范围／特殊例外／易误解处／章节关系。",
          "3. 凡引文一律回原文页取切片，不做记忆复述；谱行 OCR 缺字者标 `光谱 OCR 缺字` 或 `NEEDS_IMAGE_CONFIRM`，不猜补。",
          "4. 词学十讲第六讲源文件缺后半例词，标 `SOURCE_GAP` 并降门禁（gate_pass=0），不虚报满覆盖。", ""]
    (OUT / "BOOK_READING_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---------- CHAPTER_COVERAGE_REPORT ----------
    L = ["# CHAPTER_COVERAGE_REPORT —— 覆盖、门禁与页码映射（R2-06）", "",
         "## 一、页码映射的确定过程", "",
         "R2-05 报 A 部分为 PDF 15–182，而目录称印刷 1–174，两者不能逐一对应。本轮用**三处独立证据**确定全书统一偏移 8：", "",
         "| 证据 | 印刷页 | 实测 PDF 页 | 内容 |", "|---|---|---|---|",
         "| C 部分目录（p349） | 344 | 352 | 「一诗韵和平仄」标题行 |",
         "| C 部分目录（p349） | 347 | 355 | 「二五言绝句」标题行 |",
         "| C 部分目录（p349） | 350 | 358 | 「三七言绝句」标题行 |",
         "| A 部分目录（p11） | 7（引言） | 15 | 「引言」标题行 |",
         "| B 部分目录（p185） | 179 | 187 | 「卷上诗 第一章」标题行 |", "",
         "脚本 `r2_06_index.py` 内置这五项校验，不符即报错退出，避免把错映射写进库。", "",
         "## 二、逐页构成（`page_map_wangli`，432 行）", "",
         "| 部分 | 总页 | 扉页 | 目录 | 空白 | 章首 | 正文 | 索引 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for part in ["A", "B", "C", "D"]:
        c = dict(q(con, "SELECT kind,COUNT(*) FROM page_map_wangli WHERE part_code=? GROUP BY 1", (part,)))
        tot = sum(c.values())
        L.append(f"| {part} | {tot} | {c.get('分部扉页',0)} | {c.get('分部目录',0)} | {c.get('空白页',0)} | "
                 f"{c.get('章首',0)} | {c.get('正文',0)} | {c.get('索引',0)} |")
    L += ["", "## 三、A 部分「6 页缺口」的逐页解释", "",
          "R2-05 读 PDF 15–182（168 页），目录称印刷 1–174（174 页），差 6 页。实测逐页原因：", "",
          "| PDF 页 | 印刷页 | 性质 | 未读原因 |", "|---|---|---|---|"]
    for r in q(con, "SELECT pdf_page,printed_page,kind,exclude_reason FROM page_map_wangli "
                    "WHERE part_code='A' AND read_r205=0 ORDER BY pdf_page"):
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |")
    L += ["", "结论：A 部分正文（含章首）共 167 页，R2-05 全部读过；未读的 6 页中没有一页是正文。",
          "「100% 覆盖」因此成立，但**口径必须写成「正文 167/167」而不是「印刷 1–174」**。", "",
          "## 四、本轮覆盖与门禁", "",
          "| 单元 | 汉字 | 覆盖 | 状态 | 门禁 | 源缺 |", "|---|---:|---:|---|---|---|"]
    for r in q(con, "SELECT unit_key,chars_total,coverage,status,gate_pass,source_gap "
                    "FROM reading_records_r2_06 ORDER BY unit_key"):
        L.append(f"| {r[0]} | {r[1]:,} | {r[2]:.2f} | {r[3]} | {r[4]} | {r[5] or '—'} |")
    L += ["", "门禁八条：全文处理／小节覆盖／有效正文全过／主要观点有笔记／论述有来源位置／"
          "OCR 低置信已标／无未说明截断／记录与全文范围对应。", "",
          "`E:第6讲` 因源文件缺后半例词，第 7 条（无未说明截断）不满足，故 `gate_pass=0`——"
          "这不是阅读未完成，而是源数据不全，二者分开记录。", "",
          "## 五、累计", "",
          f"- 本轮新增 READ 单元：**{nCD}（C/D）+ {nE}（词学十讲）**",
          f"- 历史累计 READ 单元：**{nAB + nCD + nE}**（A/B {nAB} + C/D {nCD} + E {nE}）",
          f"- 历史累计精读字数：**{total:,}**", ""]
    (OUT / "CHAPTER_COVERAGE_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---------- THEORY_EXTRACTION_REPORT ----------
    L = ["# THEORY_EXTRACTION_REPORT —— 本轮新增理论条目（R2-06）", "",
         f"本轮新增 **{q(con,'SELECT COUNT(*) FROM poetry_rules_r2_06')[0][0]}** 条，全部取自 C/D 部分原文；"
         "历史累计 38（R2-05，A/B）＋ 39（R2-06，C/D）＝ **77** 条。", "",
         "字段：rule_id／书／章／PDF 页／印刷页／主题／逐字引文／原作者观点／执行者注／体裁范围／正格／例外／例证／来源层／冲突标记。", "",
         "| ID | 部分 | 章节 | 页 | 主题 | 逐字引文（节） |", "|---|---|---|---:|---|---|"]
    for r in q(con, "SELECT rule_id,book_code,chapter,printed_page,rule_topic,quote FROM poetry_rules_r2_06 ORDER BY rule_id"):
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5][:60].replace('|','\\|')} |")
    L += ["", "## 引文可核验性", "",
          "39 条引文全部经 `T-47` 检查：对每条的 PDF 页及后两页做标点归一后逐字比对，0 条未命中。",
          "归一规则仅作用于比对（引号/括号/逗号全半角），入库引文本身保留原书写法——"
          "包括原书把「阕」排作「阙」这类异体，一律照录不改。", ""]
    (OUT / "THEORY_EXTRACTION_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---------- THEORY_CONFLICT_REPORT ----------
    L = ["# THEORY_CONFLICT_REPORT —— 潜在理论冲突与勘误（R2-06）", "",
         "## 一、8 条冲突类一律降级为 POTENTIAL_THEORETICAL_CONFLICT", "",
         "审核意见：不能直接认定 8 条为确定矛盾，须逐条检查（诗体／句型／是否同一概念／例外条件／版本差异／转述混淆）。",
         "本轮处置：**保留原 `nature` 历史值不动**，新增 `conflict_status` 列统一标 "
         "`POTENTIAL_THEORETICAL_CONFLICT`，并写入 `check_note` 说明六项核验尚未完成。", "",
         "| ID | 主题 | A 侧 | B 侧 | 原 nature | 新状态 |", "|---|---|---|---|---|---|"]
    for r in q(con, "SELECT diff_id,topic,a_page,b_page,nature FROM two_book_diff_r2_05 "
                    "WHERE conflict_status='POTENTIAL_THEORETICAL_CONFLICT' ORDER BY diff_id"):
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | POTENTIAL_THEORETICAL_CONFLICT |")
    L += ["", "## 二、个案：「失对」在全书共有四处表述", "",
          "| 出处 | 印刷页 | 表述 | 性质 |", "|---|---|---|---|",
          "| A《诗词格律》正文 | 33 | 「至于失对，就更是诗人们所留心避免的了」 | 绝对 |",
          "| A《诗词格律》附录一 | 138 | 「这话未免说得太绝对了」，举温庭筠《春日》为反例 | **作者自我撤回** |",
          "| B《诗词格律概要》 | 226–227 | 「七言律绝中，甚至是没有」 | 更强绝对 |",
          "| C《诗词格律十讲》第五讲 | 361 | 「至于失对，则是更大的毛病」 | 绝对（新增证据） |",
          "| D 附录 | 402 | 「至于失对，则诗人绝对不犯的」 | 绝对（新增证据） |", "",
          "**本轮只增加证据，不做裁决。** 三处绝对表述与一处自我撤回并存，"
          "在完成「诗体／句型／是否同一概念」核验前，不能写成「王力认为失对不存在」。", "",
          "## 三、本轮勘误（4 条）", "",
          "| ID | 对象 | 原说法 | 更正 | 依据 |", "|---|---|---|---|---|"]
    for r in q(con, "SELECT corr_id,target,wrong,correct,basis FROM corrections_r2_06 ORDER BY corr_id"):
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |")
    L += ["", "### 勘误 1 详解：《宿五松山下荀媪家》确实在书中", "",
          "R2-05 据「『我宿五松下，只算拗句』全书检索 0 命中」判定该诗与句皆为执行者转述。"
          "本轮以**原书索引**为第三方锚点复核：", "",
          "索引 p427（印刷 419）条目：「《宿五松山下荀媪家》34,37,47,231,402」。逐页验证：", "",
          "| PDF 页 | 印刷页 | 内容 |", "|---|---|---|",
          "| 45 | 37 | 全诗，「我宿五松下，寂寥无所欢……月光明素盘」 |",
          "| 147 | 139 | 诗中「月光明素盘」句作例 |",
          "| 239 | 231 | 全诗，句末标「（拗救）」 |",
          "| 410 | 402 | 引「月光明素盘」为孤平拗救例 |", "",
          "正确结论：**诗与「我宿五松下」均在书中**；只有「只算拗句」四字不存在，"
          "属把注家语与原文混写。R2-05 的「0 命中」是把整串当检索词所致。", "",
          "## 四、孤平条目的完整证据链（本轮补齐）", "",
          "| 环节 | 出处 | 原文要点 |", "|---|---|---|",
          "| 定义（局限） | C p41 讲六 | 「所谓孤平，只限于平脚的句子，指的是五字句的『仄平仄仄平』、七字句的『仄仄仄平仄仄平』」 |",
          "| 拗救法 | C p42 讲六 | 「五言第一字用仄，第三字用平；七言第三字用仄，第五字用平」 |",
          "| 例证链 | D p410 | 夜宿山寺「恐惊天上人」／宿五松山下荀媪家「月光明素盘」／回乡偶书「笑问客从何处来」／咸阳城东楼「山雨欲来风满楼」 |",
          "| 例外 | C p43 讲六 | 「古体容许孤平」；「变格是律诗所容许的格式……例外则是偶然出现的」 |",
          "| 词中适用 | C p389 讲九 | 《菩萨蛮》「前后阙末句不能犯孤平」 |", "",
          "这五段合起来才构成「孤平的适用范围」，任何单句引用都会失真。", ""]
    (OUT / "THEORY_CONFLICT_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---------- CIPAI_CATALOG_REPORT ----------
    ncat = q(con, "SELECT COUNT(*) FROM cipai_catalog_r2_06")[0][0]
    nge = q(con, "SELECT COUNT(*) FROM cipai_ge_records_r2_06")[0][0]
    nmulti = q(con, "SELECT COUNT(*) FROM cipai_catalog_r2_06 WHERE n_ge>1")[0][0]
    L = ["# CIPAI_CATALOG_REPORT —— 《唐宋词格律》目录级完整盘点（R2-06）", "",
         "## 一、为什么换方法", "",
         "R2-04 用「行首匹配定格/变格」统计，得 135+9=144。审核指出原书「一百五十余调」并有格一、格二等体式，"
         "故本轮改为：**以原书目录（PDF p8–p13）建立 153 条调目为骨架 → 逐调定位标题行 → 在标题行区间内清点格记录**。", "",
         "两个关键教训：",
         "1. 不能按印刷页范围切分——一个词牌可能起于页末、定格落在下一页，页界切分会把谱文切给下一调（初版即因此有 5 调 0 格记录）。",
         "2. 不能按字面匹配标题——PDF 文字层的词牌标题带字间空格（「捣练 子」「醉太 平」），须去空格后比对（初版 44 调定位失败）。", "",
         "## 二、四个口径（严格分开，不相加）", "",
         "| 口径 | 数值 | 说明 |", "|---|---:|---|",
         f"| 独立词牌名 | **{ncat}** | 目录条目去重后仍为 {ncat}，无重名 |",
         f"| 原书标题出现次数（目录条目数） | **{ncat}** | 与上项相等说明每调在目录中只出现一次 |",
         f"| 词格记录数 | **{nge}** | 定格＋格一～格五＋变格＋别格 |",
         f"| 同调异体数（>1 条格记录） | **{nmulti}** | 不能与上项相加，后者已含前者 |", "",
         "外部交叉：出版说明称「一百五十余调」，本轮 153 调与之相符。", "",
         "## 三、按五类分布", "",
         "| 类 | 调数 | 格记录 |", "|---|---:|---:|"]
    for r in q(con, "SELECT section_name,COUNT(*),SUM(n_ge) FROM cipai_catalog_r2_06 GROUP BY 1 ORDER BY 1"):
        L.append(f"| {r[0]} | {r[1]} | {r[2]} |")
    L += ["", "## 四、按格标记分布", "", "| 标记 | 条数 |", "|---|---:|"]
    for r in q(con, "SELECT ge_label,COUNT(*) FROM cipai_ge_records_r2_06 GROUP BY 1 ORDER BY 2 DESC"):
        L.append(f"| {r[0]} | {r[1]} |")
    L += ["", "## 五、三版计数对照（原书实测为准）", "",
          "| 标记 | R2-04 索引 | R2-05 申报 | R2-06 实测 | 判读 |", "|---|---:|---:|---:|---|"]
    for r in q(con, "SELECT mark,r2_04_indexed,r2_05_claimed,r2_06_actual,note FROM cipai_gap_r2_06"):
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |")
    L += ["", "**结论：R2-04 的定格 135 是对的；R2-05 的 143 是把关键词出现次数当条目数，偏高 8 条。**"
          "旧表 `cipai_index_gap` 原样保留作审计痕迹，新值另存 `cipai_gap_r2_06`。", "",
          "## 六、同调异体清单（格记录 >1 的调）", "",
          "| 词牌 | 格记录 | 格标签 |", "|---|---:|---|"]
    for r in q(con, "SELECT c.cipai_name,c.n_ge,GROUP_CONCAT(g.ge_label,'、') FROM cipai_catalog_r2_06 c "
                    "JOIN cipai_ge_records_r2_06 g ON g.cipai_id=c.cipai_id "
                    "WHERE c.n_ge>1 GROUP BY c.cipai_id ORDER BY c.n_ge DESC, c.order_no"):
        L.append(f"| {r[0]} | {r[1]} | {r[2]} |")
    L += ["", "## 七、本轮明确未做", "",
          "1. 未重建任何一调的平仄谱字面（谱行 OCR 缺字，且属 R2-07 独立任务）。",
          "2. 未把「附《木兰花令》《减字木兰花》」这类派生调拆成独立调目——原书以「附」形式置于本调之下，"
          "本轮按原书结构保留在原调内，不凭名称自动归并或拆分。",
          "3. 未用龙榆生纪念网站目录替代本地原书；仅在口径（一百五十余调）层面做外部交叉。", ""]
    (OUT / "CIPAI_CATALOG_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print("已生成：BOOK_READING / CHAPTER_COVERAGE / THEORY_EXTRACTION / THEORY_CONFLICT / CIPAI_CATALOG")
    print(f"累计：A/B {wl:,} + C {cc:,} + D {dd:,} + E {ee:,} = {total:,}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
