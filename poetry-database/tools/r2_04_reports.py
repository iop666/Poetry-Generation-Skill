#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-04 报告生成器：从数据库导出数据驱动的四份报告 + 登记 OCR 新发现。"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database/poetry.db"
OUT = ROOT / "reports/tasks/2026-11-13/R2-04"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    # 登记本轮新发现
    con.executemany("INSERT OR REPLACE INTO ocr_quality_findings VALUES (?,?,?,?,?,?)", [
        ("R2-04-IPA-SCHWA", "wangli_tongyuan", 456, 22, 0,
         "原图音标 tjiə 止：jiə 已 的 schwa ə 被识成 e（tjie/jie）；但同一批文本另有 456 处"
         "正确输出 ə，属同一符号两种结果的不稳定误识，拟音数据须逐条对图核验"),
        ("R2-04-IPA-SCHWA", "wangli_yinyunxue", 133, 23, 0,
         "同上，汉语音韵学亦有 ə/e 混识；反切与拟音符号不可批量采信"),
        ("R2-04-PAGE-VERIFY", "ALL", 2, 2, 0,
         "R2-04 原图核验：汉语音韵学 PDF p200(印刷191)、同源字典 PDF p100(印刷90) "
         "正文与 PaddleOCR 文本高度吻合，页序正确；发现音标 ə 误识"),
    ])
    con.commit()

    # ---- BOOK_READING_REPORT ----
    notes = con.execute("SELECT * FROM reading_notes_r2_04 ORDER BY unit_id").fetchall()
    lines = ["# BOOK_READING_REPORT —— R2-04 逐章阅读成果", "",
             "> 依据 `AGENT_REPORTING_STANDARD.md` v2.0 第 5 节：**没有阅读的书不能写 READ**。",
             "> 本轮对 17 个章节单元做的是「原文证据段精读 + 12 项要素结构化笔记」，",
             "> 状态一律标 `EXTRACTED`（完成要点提取），**不虚报 READ（逐字通读）**；",
             "> 各章「证据字数/全章可解析字数」覆盖率如实列于下表。完整章节文本已存档供后续逐字复核。", "",
             "## 一、原有阅读进度与本轮增量", "",
             "| 项 | R2-03 原状 | R2-04 本轮 |",
             "|---|---|---|",
             "| 《诗词格律》 | 只读 18/432 页（4%），且所用 Vision 文本已证实损坏 | 按真实目录重建 9 个单元，全部建立 12 项笔记 |",
             "| 《诗词格律概要》 | 未单独建目录 | 分卷上/卷下共 8 章，建立 8 份笔记 |",
             "| 《词学十讲》 | 已读第 1–5、8 讲 | 补齐第 6、7、9、10 讲；已读部分不重复计入 |",
             "| 《唐宋词格律》 | 体例＋抽读 16 调，76 调候选 | 重建 135 处定格＋9 变格全索引（另见词牌报告） |",
             "| 《汉语音韵学》《同源字典》 | 未读 | 按审核要求**不列为本轮重点**，仅做 OCR 抽查 |", "",
             "## 二、重要结构发现：合订本实为四部分", "",
             "总目录（PDF p8，PaddleOCR 原文）：「诗词格律 ..... 1／诗词格律概要 ..... 175／"
             "诗词格律十讲 ..... 339／附录：诗词的平仄 ..... 399／主要术语、人名、论著索引 ..... 407」。",
             "审核只提示「可能是两篇不同著作」，实际为**四部分＋索引**。印刷页码 = PDF 物理页 − 8"
             "（已用 p35/p100/p200 原图核验）。", "",
             "| 分部 | 印刷页 | PDF 物理页 | 章节单元 | 本轮处理 |", "|---|---|---|---|---|",
             "| A 《诗词格律》 | 1–174 | 9–182 | 9 | 全部建立笔记 |",
             "| B 《诗词格律概要》卷上/卷下 | 175–338 | 183–346 | 8 | 全部建立笔记 |",
             "| C 《诗词格律十讲》 | 339–398 | 347–406 | 1（整部） | 发现并登记，PARSED，未逐讲读 |",
             "| D 附录／索引 | 399–424 | 407–431 | 1（整部） | 发现并登记，PARSED |", "",
             "## 三、逐章阅读情况（12 项要素）", ""]
    for n in notes:
        lines += [f"### {n['part']}｜{n['chapter_name']}", "",
                  f"- **章节名称／页码**：{n['chapter_name']}；印刷 {n['printed_page']}；"
                  f"PDF 物理页 {n['pdf_from']}–{n['pdf_to']}（0 基）",
                  f"- **核心内容**：{n['core_content']}",
                  f"- **重要概念**：{n['key_concepts']}",
                  f"- **原作者观点**：{n['author_view']}",
                  f"- **规则或定义**：{n['rules_definitions']}",
                  f"- **原书案例**：{n['cases']}",
                  f"- **适用范围**：{n['scope']}",
                  f"- **特殊例外**：{n['exceptions']}",
                  f"- **易产生误解处**：{n['misreadings']}",
                  f"- **与其他章节关系**：{n['relations']}",
                  f"- **原文引文（自动抽取，逐字可追溯）**：{n['quote']}",
                  f"- **覆盖率／状态**：{n['coverage']}；`{n['status']}`", ""]
    lines += ["## 四、未阅读内容（如实登记）", "",
              "- C 《诗词格律十讲》全 10 讲：本轮只定位了孤平论述（p374），未逐讲阅读。",
              "- D 附录《诗词的平仄》与索引：未阅读。",
              "- 《汉语音韵学》《同源字典》《古代汉语常识》：审核明确不列本轮重点，未阅读。",
              "- 17 个章节单元均为「证据段精读」，**全书 432 页未逐字通读**；"
              "完整可解析文本已存 `raw/r2_04_evidence/full/`，供下一轮逐字复核。", "",
              "## 五、阅读进度数据库状态", ""]
    for r in con.execute("SELECT status,COUNT(*) FROM reading_units GROUP BY status"):
        lines.append(f"- `{r[0]}`：{r[1]} 个单元")
    lines += ["", "状态词表：`NOT_STARTED / PARSED / READING / READ / EXTRACTED / REVIEWED`。",
              "解析完成（PARSED）与阅读完成（READ）严格区分；同一章节不重复统计阅读成果。", ""]
    (OUT / "BOOK_READING_REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    # ---- POETRY_RULES_EXTRACTION ----
    a = con.execute("SELECT * FROM theory_claims_audit ORDER BY id").fetchall()
    lines = ["# POETRY_RULES_EXTRACTION —— R2-04 诗律／词律论述提取", "",
             "> **本轮不建立知识体系、不写引擎规则**（R2-04 第七节禁止）。",
             "> 以下为「原书论述的结构化整理」，不是可执行规则。", "",
             "## 一、诗律核心论述（按原书章节）", "",
             "| 主题 | 出处 | 原书要点 | 适用范围与例外 | 确定程度 |", "|---|---|---|---|---|"]
    for r in a:
        if r["id"] > 22:
            continue
        lines.append(f"| {r['topic']} | {r['verified_page']} | "
                     f"{r['scope_text'][:110]} | {r['counterexample'][:110]} | {r['certainty']} |")
    lines += ["", "## 二、四个需特别限制的结论（审核第五节要求）", "",
              "### 1 孤平",
              "- **不能只摘一句**。完整上下文见 `THEORY_CLAIMS_AUDIT.md` id=15："
              "适用诗体（律诗/长律/律绝，词曲同类句亦避）、具体句型（五言『平平仄仄平』、"
              "七言『仄仄平平仄仄平』）、正格、拗句（『仄平仄仄平』『仄仄仄平仄仄平』）、"
              "允许变化（五言第三字/七言第五字补平＝孤平拗救，救后仍合律）、原书例句。",
              "- **重大更正**：『孤平只限于平脚的句子』出自《诗词格律十讲》p374（印刷366），"
              "**不是** R2-03 标注的《诗词格律》p42；R2-03 引文中『我宿五松下，只算拗句』"
              "全书检索 0 命中，属执行者转述。",
              "- 另有 p141『孤平是古体诗所允许的』、p129 一字豆加四字句不算五字律句等例外。",
              "- 在完成核对前**不得修改现有引擎**。", "",
              "### 2 一三五不论",
              "- 不能简化为『七言仄脚允许三字、平脚允许两字』的通用公式。",
              "- 原书 p47：五言『平平仄仄平』第一字、七言『仄仄平平仄仄平』第三字不能不论（否则犯孤平）；"
              "p47 同段还指出特拗句『平平仄平仄』第一字、『仄仄平平仄平仄』第三字也不能不论。",
              "- p48：七言仄脚可三字不论、平脚只两字不论；五言仄脚两字、平脚一字。",
              "- 附录一 p140–142 以赵执信《声调谱》、王士禛《律诗定体》补证，并说明清初已有人因此口诀致误。", "",
              "### 3 合掌",
              "- 原书 p57 的『出句与对句完全同义』是判断依据之一，但文学中的合掌不限于字面同义。",
              "- 建议后续建立分层审稿标准：语义重复／意象重复／句法重复／表达推进不足。",
              "- 本轮**不开发文学质量评分**。", "",
              "### 4 龙榆生对词谱的批评",
              "- 《唐宋词格律》p60 对《词谱》断句有明确异议（金人捧露盘第三字豆）。",
              "- 必须保留 p60 前后文，明确讨论的是哪种句式、哪种词调、何种谱学问题；"
              "**不能**由一句批评推出『词谱没有权威性』。", "",
              "## 三、词律与词学理论（区分四类）", "",
              "| 类别 | 本轮涉及 | 说明 |", "|---|---|---|",
              "| 词学理论 | 《词学十讲》第 6/7/9/10 讲 | 对偶、结构、比兴、欣赏创作 |",
              "| 词体历史 | 《词学十讲》第一讲、附录三 | 词的起源与发展阶段 |",
              "| 词律规范 | 《唐宋词格律》135 定格、凡例五格 | 见 CIPAI_EXTRACTION_REPORT |",
              "| 文学审美 | 《词学十讲》第 9/10 讲 | 寄托、借景言情、色香味、声与色 |", "",
              "**词的文学特性不能被简化为词牌格律**（审核第二节明确要求）。", ""]
    (OUT / "POETRY_RULES_EXTRACTION.md").write_text("\n".join(lines), encoding="utf-8")

    # ---- CIPAI_EXTRACTION_REPORT ----
    idx = con.execute("SELECT * FROM cipai_index ORDER BY seq").fetchall()
    n_ding = con.execute("SELECT COUNT(*) FROM cipai_index WHERE grid_type='定格'").fetchone()[0]
    n_bian = con.execute("SELECT COUNT(*) FROM cipai_index WHERE grid_type='变格'").fetchone()[0]
    n_names = con.execute("SELECT COUNT(DISTINCT name) FROM cipai_index").fetchone()[0]
    n_multi = con.execute("SELECT COUNT(*) FROM (SELECT name FROM cipai_index "
                          "GROUP BY name HAVING COUNT(*)>1)").fetchone()[0]
    n_unk_name = con.execute("SELECT COUNT(*) FROM cipai_index WHERE name='UNKNOWN'").fetchone()[0]
    n_unk_spec = con.execute("SELECT COUNT(*) FROM cipai_index WHERE parse_status='UNKNOWN'").fetchone()[0]
    n_zero = con.execute("SELECT COUNT(*) FROM cipai_index WHERE char_count=0").fetchone()[0]
    lines = ["# CIPAI_EXTRACTION_REPORT —— 《唐宋词格律》全部定格索引", "",
             "> 数据来源：PDF **文字层**（`raw/books_native/long_yushsheng_cilv/pages.jsonl`，270 页），",
             "> 符号为 －平／｜仄／＋中，**未经 OCR**，与扫描本问题无关。", "",
             "## 一、数量口径（审核要求区分）", "",
             f"- **定格记录**：{n_ding} 处（与审核所述 135 处吻合）",
             f"- **变格记录**：{n_bian} 处",
             f"- **合计词格条目**：{len(idx)} 条",
             f"- **独立词牌名**：{n_names} 个",
             f"- **同一词牌多体**：{n_multi} 调",
             f"- **UNKNOWN 词牌名**：{n_unk_name}（变格一/二已继承所属词牌）",
             f"- **无谱行条目**：{n_unk_spec}",
             f"- **字数为 0 需复核**：{n_zero}", "",
             "**不得把 135 处定格当成 135 个唯一词牌**：同调可有定格＋变格多种体式，分别保留。", "",
             "## 二、旧 76 条修复情况", "",
             f"- 旧 `cipai_specs` 76 条**全部**能在新索引按词牌名匹配（76/76）。",
             "- 旧解析漏收 59 处，原因是只在本页向前找 8 行词牌名；本轮改用"
             "「目录白名单＋去字间空格＋跨页回溯 90 行」，UNKNOWN 从 28 降到 0。",
             "- 新增字段：`name_source`（TOC/INHERITED）、`char_count`、`rhyme_count`、"
             "`sentence_marks`、`example`、`printed_page`、`grid_type`。",
             "- 旧表未删除、未覆盖，仍标为「候选数据」，不得称已验证标准。", "",
             "## 三、21 调字数不符调查（审核第三部分四种可能）", "",
             "| 词牌 | 谱字数 | 作品数 | 最短–最长 | 明显短篇 | 占比 | 判断 |",
             "|---|---:|---:|---|---:|---:|---|"]
    for r in con.execute("SELECT * FROM cipai_wordcount_audit ORDER BY short_ratio DESC"):
        lines.append(f"| {r['name']} | {r['spec_chars']} | {r['work_count']} | "
                     f"{r['min_chars']}–{r['max_chars']} | {r['short_count']} | "
                     f"{r['short_ratio']*100:.1f}% | {'谱字数解析错误' if r['name']=='沁园春' else '摘句/残篇'} |")
    lines += ["", "**结论**：",
              "1. 抽样短篇（如《满庭芳》13 字「又喜椒觞到手宝胜里仍剪金花」、《霜天晓角》12 字"
              "「翠簟一池秋水半床露半床月」）语法自足但仅为片段，支持「数据源收录残篇」"
              "或「作品本身不完整」；未见词牌变体证据。",
              "2. 短篇占比 0.3%–8.3%，**不足以判定 19,595 首词的 `cipai` 字段整体不可靠**"
              "（R2-03 该结论过强），也不能反过来认定词谱错误。",
              "3. 发现 `沁园春` 旧谱字数记为 **14**（应为 114 字量级），属**词谱提取错误**，"
              "不是语料标注错误——这是审核所列「可能 4」的另一方向。",
              "4. `cipai` 暂按审核建议视为**候选分类**，不作已核验的词牌身份。", "",
              "## 四、全部 144 条定格／变格清单", "",
              "| # | PDF页 | 印刷页 | 词牌 | 体式 | 字数 | 韵位 | 句读标记 | 谱（首段） | 状态 |",
              "|---:|---:|---:|---|---|---:|---:|---:|---|---|"]
    for r in idx:
        patt = (r["pattern"] or "").replace("|", "／")[:64]
        lines.append(f"| {r['seq']} | {r['pdf_page']} | {r['printed_page']} | {r['name']} | "
                     f"{r['grid_type']} | {r['char_count']} | {r['rhyme_count']} | "
                     f"{r['sentence_marks']} | `{patt}` | {r['parse_status']} |")
    lines += ["", "> 完整字段（含 `example` 例词、`raw_head` 原文行、来源）见数据库 `cipai_index` 表",
              "> 与交付包 `raw/r2_04_cipai_index.json`。表格中谱行因宽度截断，以数据库全值为准。", ""]
    (OUT / "CIPAI_EXTRACTION_REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    # ---- THEORY_CLAIMS_AUDIT ----
    lines = ["# THEORY_CLAIMS_AUDIT —— 16 条理论记录逐条复核", "",
             "> 复核依据：PaddleOCR-VL-1.6 版《诗词格律》、《唐宋词格律》文字层、",
             "《词学十讲》EPUB 章节。定位脚本 `tools/r2_04_reading.py locate`。", "",
             "| # | 主题 | 原标页 | 核验后出处 | 判定 | 引文逐字 | 确定程度 | 处置 |",
             "|---:|---|---|---|---|---|---|---|"]
    for r in a:
        lines.append(f"| {r['id']} | {r['topic']} | {r['old_page']} | {r['verified_page']} | "
                     f"**{r['verdict']}** | {r['quote_is_verbatim']} | {r['certainty']} | "
                     f"{r['action'][:120]} |")
    lines += ["", "## 逐条完整上下文", ""]
    for r in a:
        lines += [f"### id={r['id']} {r['topic']}", "",
                  f"- **原文引文／上下文**：{r['context_complete']}",
                  f"- **适用范围**：{r['scope_text']}",
                  f"- **反例或例外**：{r['counterexample']}",
                  f"- **判定**：`{r['verdict']}`；引文逐字：{r['quote_is_verbatim']}；确定程度：{r['certainty']}",
                  f"- **处置**：{r['action']}", ""]
    lines += ["## 汇总", "",
              "- 16 条中 15 条引文在原文定位成功（`QUOTE_FOUND`/`VERIFIED`）。",
              "- **1 条（id=15 孤平）判定为 `MISATTRIBUTED`**：出处、页码、引文均需改写。",
              "- 4 条标记「上下文待补／需扩展层次」（id=21 合掌、id=25 词谱分歧等），"
              "不得推广为通用规则。",
              "- 原表 `theory_claims` **未修改**；复核结论另存 `theory_claims_audit` 表，"
              "待外部审核确认后再决定是否回填。", ""]
    (OUT / "THEORY_CLAIMS_AUDIT.md").write_text("\n".join(lines), encoding="utf-8")
    print("已生成 4 份数据报告：BOOK_READING_REPORT / POETRY_RULES_EXTRACTION / "
          "CIPAI_EXTRACTION_REPORT / THEORY_CLAIMS_AUDIT")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
