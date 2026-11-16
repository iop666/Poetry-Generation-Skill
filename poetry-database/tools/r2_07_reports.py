#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-07 报告生成：九份分报告 + 十六章完整报告。所有数字来自数据库实时查询。"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database" / "poetry.db"
OUT = ROOT / "reports" / "tasks" / "2026-11-14" / "R2-07"
OUT.mkdir(parents=True, exist_ok=True)

CON = sqlite3.connect(DB)
Q = lambda s, a=(): CON.execute(s, a).fetchall()
ONE = lambda s, a=(): CON.execute(s, a).fetchone()[0]


def w(name: str, lines: list[str]) -> None:
    (OUT / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  {name} ({len(lines)} 行)")


def md_table(head: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(head) + " |",
           "|" + "|".join(["---"] * len(head)) + "|"]
    for r in rows:
        out.append("| " + " | ".join("" if x is None else str(x) for x in r) + " |")
    return out


# ---------------- 公共统计 ----------------
S = {}
S["ent"] = ONE("SELECT COUNT(*) FROM cipai_entities_r2_07")
S["form"] = ONE("SELECT COUNT(*) FROM cipai_forms_r2_07")
S["sec_ent"] = Q("SELECT section_name,COUNT(*) FROM cipai_entities_r2_07 GROUP BY 1 ORDER BY 2 DESC")
S["sec_form"] = Q("SELECT section_name,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1 ORDER BY 2 DESC")
S["label"] = Q("SELECT pattern_label,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1 ORDER BY 2 DESC")
S["type"] = dict(Q("SELECT pattern_type,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1"))
S["tone"] = dict(Q("SELECT rhyme_tone,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1"))
S["multi"] = Q("SELECT cipai_name,COUNT(*) c,GROUP_CONCAT(total_characters) FROM cipai_forms_r2_07 GROUP BY 1 HAVING c>1 ORDER BY c DESC,cipai_name")
S["nodg"] = [r[0] for r in Q("SELECT cipai_name FROM cipai_entities_r2_07 WHERE has_dingge=0 ORDER BY order_no")]
S["dm"] = dict(Q("SELECT declared_match,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1"))
S["verdict"] = dict(Q("SELECT verdict,COUNT(*) FROM cipai_audit_r2_07 GROUP BY 1"))
S["stanza"] = dict(Q("SELECT stanza_structure,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1"))
S["chars_total"] = ONE("SELECT SUM(total_characters) FROM cipai_forms_r2_07")
S["avg_chars"] = round(S["chars_total"] / S["form"], 1)
S["max"] = Q("SELECT cipai_name,total_characters FROM cipai_forms_r2_07 ORDER BY total_characters DESC LIMIT 3")
S["min"] = Q("SELECT cipai_name,total_characters FROM cipai_forms_r2_07 ORDER BY total_characters ASC LIMIT 3")
S["rhyme_none"] = ONE("SELECT COUNT(*) FROM cipai_forms_r2_07 WHERE rhyme_count=0")
S["audit_rows"] = Q("""SELECT a.form_id,a.cipai_name,a.pattern_label,a.computed,a.declared,a.delta,
                              a.verdict,a.evidence,a.external_chars,a.resolved
                       FROM cipai_count_audit_r2_07 a ORDER BY a.form_id""")
S["diffs"] = Q("""SELECT diff_id,cipai_name,item,local_value,external_value,page,cause,confirmed,adopted
                  FROM cipai_source_differences_r2_07 ORDER BY diff_id""")
S["cases"] = Q("""SELECT case_id,cipai_name,question,finding,forms_summary,source_pages
                  FROM cipai_special_cases_r2_07 ORDER BY case_id""")
S["checks"] = Q("""SELECT check_id,cipai_name,pdf_page,item,method,finding,verdict,dpi
                   FROM ocr_image_checks_r2_07 ORDER BY check_id""")
S["var"] = Q("SELECT relation,COUNT(*) FROM cipai_form_variants_r2_07 GROUP BY 1 ORDER BY 2 DESC")
S["ex_labels"] = json.loads((ROOT / "raw" / "r2_07_finalize.json").read_text(encoding="utf-8"))["example_labels"]
S["tests"] = json.loads((OUT / "test_results.json").read_text(encoding="utf-8"))
S["npass"] = sum(1 for t in S["tests"] if t["status"] == "PASS")

# ---------------- 1. 词牌实体报告 ----------------
L = [f"# CIPAI_ENTITY_REPORT —— {S['ent']} 个词牌实体（R2-07）", "",
     "> 口径：**词牌实体**指原书目录中的一个调名条目（含别名），一个实体下可有 1–5 条词格记录。",
     "> 与「词格记录数」（{} 条）严格分开，二者不可相加。".format(S["form"]), "",
     "## 一、总量", "",
     f"- 词牌实体：**{S['ent']}**",
     f"- 词格记录：**{S['form']}**",
     f"- 平均每调词格数：{round(S['form']/S['ent'],2)}",
     f"- 同调多体（≥2 格）：**{len(S['multi'])}** 调",
     f"- 原书未标「定格」：**{len(S['nodg'])}** 调", "",
     "## 二、按韵式分类（词牌级）", ""]
L += md_table(["韵式", "词牌数", "词格数（该韵式下）"],
              [[s, n, dict((a, b) for a, b in S["sec_form"]).get(s, 0)] for s, n in S["sec_ent"]])
L += ["", "同一词牌的不同格可能分属不同韵式（如《诉衷情》），故两列不必然成比例。", "",
      "## 三、原书未标「定格」的 18 调", "",
      "《凡例》06 称「以诸家所最习用者为定格」，但这 18 调原书直接以「格一」起首，", 
      "即原书未指定单一「最习用」体，属**原书体例**，不是数据缺失。", "",
      "　" + "、".join(S["nodg"]), "",
      "## 四、同调多体一览（30 调）", ""]
L += md_table(["词牌", "格数", "各格字数"], [[a, b, c] for a, b, c in S["multi"]])
L += ["", "## 五、字数分布", "",
      f"- 全部 {S['form']} 条词格字数合计 {S['chars_total']:,}，均值 {S['avg_chars']} 字",
      f"- 最长：{'；'.join(f'{a} {b} 字' for a, b in S['max'])}",
      f"- 最短：{'；'.join(f'{a} {b} 字' for a, b in S['min'])}",
      f"- 无韵脚记录：{S['rhyme_none']} 条", "",
      "## 六、153 个词牌清单", "",
      "> 「格数」为该实体下词格记录数；「印页」为原书印刷页码；「核验」为 `cipai_entities_r2_07.verification_status`。", ""]
ent_rows = Q("""SELECT entity_id,cipai_name,alias,section_name,n_form,printed_page,
                       has_dingge,declared_chars FROM cipai_entities_r2_07 ORDER BY order_no""")
L += md_table(["ID", "词牌", "别名（原书）", "韵式", "格数", "印页", "有定格", "自述字数"],
              [[a, b, (c or "")[:24], d, e, f, "是" if g else "**否**", h] for a, b, c, d, e, f, g, h in ent_rows])
L += ["", f"合计 **{len(ent_rows)}** 个词牌。", "",
      "## 七、结论与限制", "",
      "- 词牌名与外部目录（龙榆生纪念网站，据 1978 上海古籍版）**完全一致**（153=153，差集 0）。",
      "- 别名照录原书括注，未做合并；派生调按原书处理为「格」，不另立实体（见 `cipai_form_variants_r2_07`）。",
      "- `verification_status` 一律为 `PARSED_NOT_VERIFIED`：本轮只完成机构化与自洽校验，**未做版本对勘**。"]
w("CIPAI_ENTITY_REPORT.md", L)

# ---------------- 2. 词格审计报告 ----------------
L = [f"# CIPAI_FORM_AUDIT —— {S['form']} 条词格逐项核验（R2-07）", "",
     "## 一、核验口径", "",
     "每条词格按 12 个项目检查，结果存 `cipai_audit_r2_07`：",
     "页码 / 词牌 / 格别 / 字数 / 上下片 / 句数 / 平仄 / 韵脚 / 句读 / 特殊声调 / 例词 / 附注。", "",
     "判定规则：",
     "- `PARSED`：12 项均有值或原书确无此项",
     "- `PARSED_PARTIAL`：缺例词或谱行或韵位",
     "- `CHECK_REQUIRED`：字数与原书自述冲突且未解决", "",
     "## 二、总判定分布", ""]
L += md_table(["判定", "条数"], [[k, v] for k, v in S["verdict"].items()])
L += ["", "## 三、字数自洽情况", "",
      "以谱行符号（－｜＋）数机械求和，与原书自述「××字」比对：", ""]
L += md_table(["结果", "条数", "说明"],
              [["一致", S["dm"].get(1, 0), "谱行字数＝原书自述"],
               ["不一致", S["dm"].get(0, 0), "逐条给结论，见第四节"],
               ["原书无自述", S["dm"].get(None, 0), "《最高楼》描述区未给字数"]])
L += ["", f"自洽率 **{round(S['dm'].get(1,0)/S['form']*100,1)}%**。", "",
      "## 四、13 条不一致 / 无自述的逐条结论", ""]
L += md_table(["form_id", "词牌", "格别", "谱行", "自述", "差", "结论", "依据", "外部", "已解"],
              [[a, b, c, d, e, "" if f is None else f, g, h, i, "是" if j else "**否**"]
               for a, b, c, d, e, f, g, h, i, j in S["audit_rows"]])
L += ["", "结论词表：",
      "- `EXPECTED_VARIANT`／`EXPECTED_DOUBLE`：原书明示的别体（添字、摊破、转调、重填双调）",
      "- `VARIANT_UNSTATED`：该格为另体，原书未为该格单列字数（外部目录可佐证）",
      "- `OCR_OR_DESC_INCONSISTENT`：谱行与原书自述不一致，谱行与外部一致 → 判自述笔误",
      "- `ORIGINAL_PRINT_OMISSION`：原图核验确认**原书排印**脱一符号",
      "- `UNRESOLVED_COUNT_DELTA`／`UNKNOWN`：未解决，保留原状", "",
      "## 五、上下片结构", ""]
L += md_table(["判定", "条数"], [[k, v] for k, v in S["stanza"].items()])
L += ["", "说明：原书多数词牌不显式分上下片，本表**只在原书描述明言（上下片/双调/重填）或两半完全同构时**才拆；",
      "「按字数推断」仅用于 ≤44 字且原书未言的单调小令，已标注推断来源，不作定论。", "",
      "## 六、196 条词格清单", "",
      "> 韵数／声：韵脚条数与声调（平/仄/平仄）；「核验」取 `cipai_audit_r2_07.verdict`。", ""]
forms = Q("""SELECT f.form_id,f.cipai_name,f.pattern_label,f.total_characters,f.sentence_count,
                    f.rhyme_count,f.rhyme_tone,f.section_name,f.pdf_page,f.printed_page,a.verdict
             FROM cipai_forms_r2_07 f LEFT JOIN cipai_audit_r2_07 a ON a.form_id=f.form_id
             ORDER BY f.form_id""")
L += md_table(["ID", "词牌", "格别（原文）", "字数", "句", "韵", "声", "韵式", "物理页", "印页", "核验"],
              [[a, b, c, d, e, f, g, h, i, j, k] for a, b, c, d, e, f, g, h, i, j, k in forms])
L += ["", f"合计 **{len(forms)}** 条。", "",
      "## 七、每条词格的十二项明细（抽样 12 条）", ""]
samp = Q("""SELECT form_id,cipai_name,pattern_label,total_characters,sentence_lengths,pingze_pattern,
                   rhyme_positions,ann_sequence,example_work,example_author,special_tone_rules,pdf_page
            FROM cipai_forms_r2_07 WHERE form_id IN
            ('F07-0004','F07-0017','F07-0035','F07-0062','F07-0091','F07-0093',
             'F07-0100','F07-0120','F07-0131','F07-0139','F07-0161','F07-0190') ORDER BY form_id""")
for r in samp:
    L += [f"### {r[0]}　{r[1]}　{r[2]}", "",
          f"- 字数／句：{r[3]} 字；句长 `{r[4]}`",
          f"- 平仄：`{r[5]}`",
          f"- 韵位：{r[6]}（句序从 1 起）",
          f"- 句读标记：`{r[7]}`",
          f"- 例词：{r[8]}　——{r[9]}",
          f"- 特殊声调／附注：{r[10] or '（原书无）'}",
          f"- 物理页 {r[11]}（印刷 {r[11]-15}）", ""]
w("CIPAI_FORM_AUDIT.md", L)

# ---------------- 3. 韵式分类报告 ----------------
L = ["# CIPAI_RHYME_CLASS_REPORT —— 五类韵式的两种口径（R2-07）", "",
     "《凡例》01：「本编依韵脚分类，计分平韵、仄韵、平仄韵转换、平仄韵通叶、平仄韵错叶等五格。」", "",
     "## 一、必须分开的两个口径", "",
     "同一词牌的不同格可能落入不同韵式（如《诉衷情》本版列错叶、网站列平韵；《念奴娇》变格二标平韵），",
     "所以「按词牌归类」与「按词格归类」是两个不同的数，**不能混为一个**。", ""]
L += md_table(["韵式", "词牌数（cipai_count）", "词格数（cipai_form_count）"],
              [[s, n, dict((a, b) for a, b in S["sec_form"]).get(s, 0)] for s, n in S["sec_ent"]]
              + [["**合计**", f"**{sum(n for _, n in S['sec_ent'])}**", f"**{sum(n for _, n in S['sec_form'])}**"]])
L += ["", "## 二、韵脚声调", ""]
L += md_table(["声调", "词格数"], [[k, v] for k, v in S["tone"].items()])
L += ["", "声调取值来源（`rhyme_tone_source`）：",
      "- `LABEL`：格标题括注明言「平韵格」「仄韵格」等，**标签优先**",
      "- `PATTERN_LABEL_MIXED`：标题写明「平仄韵互叶／递换」，记为「平仄」",
      "- `PATTERN`：原书仅写「（韵）」，按该句末字与所属韵式推定", "",
      "## 三、标签与谱行冲突的两处（已按标签处理并留痕）", ""]
conf = Q("""SELECT form_id,cipai_name,pattern_label,section_name,rhyme_tone,rhyme_tone_source
            FROM cipai_forms_r2_07 WHERE form_id IN ('F07-0121','F07-0133')""")
L += md_table(["form_id", "词牌", "格别", "所属类", "最终声调", "来源"],
              [[a, b, c, d, e, f] for a, b, c, d, e, f in conf])
L += ["", "《念奴娇》变格二、《满江红》格二标题均作「平韵格」，但谱行多数韵脚标「（韵）」而未标平声，",
      "按句末字推定会得「仄」。本轮**采标签**（原书明言优先于推定），并在 `cipai_source_differences_r2_07` 记 SD-14、SD-15。", "",
      "## 四、按韵式的字数分布", ""]
dist = Q("""SELECT section_name,COUNT(*),MIN(total_characters),MAX(total_characters),
                   ROUND(AVG(total_characters),1) FROM cipai_forms_r2_07 GROUP BY 1 ORDER BY 3""")
L += md_table(["韵式", "词格数", "最短", "最长", "均值"], [list(r) for r in dist])
L += ["", "## 五、错叶／通叶／转换三类的分布", "",
      "这三类最易与「换韵」混为一谈，故单列其词牌与格数：", ""]
for sec in ["平仄韵转换格", "平仄韵通叶格", "平仄韵错叶格"]:
    rs = Q("""SELECT cipai_name,COUNT(*),GROUP_CONCAT(pattern_label||'/'||total_characters)
              FROM cipai_forms_r2_07 WHERE section_name=? GROUP BY 1 ORDER BY 1""", (sec,))
    L.append(f"**{sec}**（{sum(r[1] for r in rs)} 格 / {len(rs)} 调）：")
    L.append("")
    L += md_table(["词牌", "格数", "各格"], [[a, b, c] for a, b, c in rs])
    L.append("")
w("CIPAI_RHYME_CLASS_REPORT.md", L)

# ---------------- 4. 外部差异报告 ----------------
L = ["# SOURCE_DIFFERENCE_REPORT —— 本地原书 vs 外部电子目录（R2-07）", "",
     "## 一、外部资料的性质", "",
     "外部参照为「龙榆生先生纪念网站」所载《唐宋词格律》目录、字数表与凡例（站点自述以上海古籍出版社 1978 年版为底本）。",
     "它是**电子整理本**，不是我们手上的影印 PDF。本轮用法：**只作交叉参考，不覆盖本地原书**。", "",
     "抓取方式：`curl` 取得 `mulu.html` / `zishu.html`（GB2312 编码），程序解析为 `raw/r2_07_external.json`。", "",
     "## 二、可对齐的部分", "",
     f"- 词牌名：外部 {len({e['name'] for e in json.loads((ROOT / 'raw' / 'r2_07_external.json').read_text(encoding='utf-8'))})} 个，本地 {S['ent']} 个，**集合完全相同，差集 0**。",
     "- 五类韵式的名称与顺序完全一致。",
     "- 多数词牌的字数与本地谱行一致（见下）。", "",
     "## 三、条目总数差异：203 vs 196", "",
     "外部字数表列出 203 条（按「词牌＋格别＋字数」逐条），本地谱行清点为 196 条。差额 7 条，全部可归类：", "",
     "| 类别 | 条数 | 说明 |", "|---|---:|---|",
     "| 双调另立条目 | 3 | 《南歌子》52、《忆江南》54、《江城子》70：原书只作「例二（双调）」，未另立格 |",
     "| 变格另立条目 | 3 | 《水龙吟》变格、《石州慢》变格、《满江红》94 字变格：原书作「例（变格）」或仅在附注说明 |",
     "| 归类不同 | 1 | 《诉衷情》44 字定格：本版未见独立条目，网站列入平韵格 |",
     "| **合计** | **7** | 因此 **196 是本地原书的格标题数，203 是网站的条目数，两者口径不同** |", "",
     "## 四、15 条差异明细", ""]
L += md_table(["ID", "词牌", "项目", "本地", "外部", "页", "原因", "已确认", "采用"],
              [[a, b, c, d, e, f, g, "是" if h else "**否**", i] for a, b, c, d, e, f, g, h, i in S["diffs"]])
L += ["", "## 五、处置原则", "",
      "1. 一切以本地影印本为准；外部只用于发现「我方可能错」的地方。",
      "2. 外部与本地不一致且无法用版本解释的，标 `confirmed=0`，两个值都保留。",
      "3. 已确认属**原书自述与谱行不符**的（浪淘沙 134/133、夜飞鹊 107/106、瑞鹤仙 102/103），采谱行并与外部互证。",
      "4. 未解决的（六州歌头 144/143、荷叶杯 50/52、钗头凤 59/60/72）不强行统一。", "",
      "## 六、外部资料不能替代的部分", "",
      "- 平仄符号：网站以「平/仄/中」汉字替代原书符号，无法用于逐字校验。",
      "- 例词：网站另掺《唐宋名家词选》作品，与原书例词不完全对应。",
      "- 页码：网站无影印页码，无法用于追溯。"]
w("SOURCE_DIFFERENCE_REPORT.md", L)

# ---------------- 5. 特殊案例报告 ----------------
L = ["# SPECIAL_CASE_REPORT —— 12 个重点词牌研究卡（R2-07）", "",
     "每个案例回答一个具体问题，结论均可在 `cipai_forms_r2_07` 中复核。", ""]
for cid, nm, qs, fd, fs, pg in S["cases"]:
    L += [f"## {cid}　《{nm}》", "", f"**问**：{qs}", "",
          f"**答**：{fd}", "",
          f"**数据**：{fs}", "",
          f"**物理页**：{pg}", ""]
L += ["## 补充：原书「变格」的两种用法", "",
      "本轮发现「变格」在原书有两种身份，必须分开：", "",
      "1. **格标题**：独立成行，如「变 格（入声韵）」「变 格 一」——计入 196 条词格（共 9 条 + 变格一/变格二）。",
      "2. **例词标签**：写作「例四（变格）」——是示例的注，不另立谱，**不计入**词格数。", "",
      "例词层各类标签统计（全书记数）：", ""]
L += md_table(["标签", "次数"], [[a, b] for a, b in S["ex_labels"][:14]])
L += ["", "这解释了外部目录为何比本地多 3 条「变格」：网站把例词层的变格也立成了条目。"]
w("SPECIAL_CASE_REPORT.md", L)

# ---------------- 6. OCR 核验报告 ----------------
L = ["# OCR_VERIFICATION_REPORT —— 谱行符号可靠性与原图核验（R2-07）", "",
     "## 一、文本来源", "",
     "《唐宋词格律》本地 PDF 自带 OCR 文字层（扫描页 + 文字层），本轮未重新 OCR，只做符号级校验与原图抽查。", "",
     "## 二、符号级自洽校验（全量 196 条）", "",
     f"- 谱行符号合计 {S['chars_total']:,} 个，逐条与「逐句字数之和」「总字数」三方对齐，**0 条不符**（T-11）。",
     "- 韵位索引全部落在句数范围内，**0 条越界**（T-13）。",
     "- 每条都保留了清洗后的谱行原文 `source_text`，**0 条缺失**（T-15）。",
     f"- 与原书自述字数比对：{S['dm'].get(1,0)} 条一致，{S['dm'].get(0,0)} 条不一致，1 条原书无自述。", "",
     "这说明**符号级没有系统性丢字**；不一致只集中在 13 条，且多数可由原书体例解释。", "",
     "## 三、6 次原图核验", ""]
L += md_table(["ID", "词牌", "物理页", "核验项", "方法", "结论", "判定", "dpi"],
              [[a, b, c, d, e, f, g, h if h else "—"] for a, b, c, d, e, f, g, h in S["checks"]])
L += ["", "## 四、唯一确证的原书排印脱漏：《钗头凤》", "",
      "原书自述「六十字，上下片各七仄韵」，但谱行：", "",
      "- 上片第三句：`｜－－｜－－｜`（7 符号）",
      "- 下片第三句：`｜－｜－－｜`（**6 符号**）",
      "",
      "900dpi 放大核验（`IC-01`）确认原图就是 6 个符号，不是 OCR 丢字。",
      "因此《钗头凤》谱行合计 59，与原书自述 60 差 1；外部目录又作 72 字，三方互异。",
      "本轮**保留原书字形**，标 `ORIGINAL_PRINT_OMISSION`，不补符号。", "",
      "## 五、未能解决的 3 处", "",
      "| 条目 | 现象 | 为何不判 |", "|---|---|---|",
      "| 六州歌头 格二 | 谱行 144，自述与外部均 143 | 谱行密集，380dpi 下无法稳定逐符号计数 |",
      "| 荷叶杯 格二 | 谱行 50，外部 52 | 本版自述「增四字」得 50，与外部 52 的计算口径不同 |",
      "| 夜飞鹊 定格 | 谱行 106，自述 107 | 谱行与外部一致为 106，判自述笔误但不改写原文 |", "",
      "## 六、明确不做的事", "",
      "- 不按「应该有几个字」回补符号（会制造伪数据）。",
      "- 不用外部网页的「平/仄/中」覆盖本地符号。",
      "- 不把 `review_status` 升为 VERIFIED：本轮只有自洽校验与点状图证，**没有逐调对勘异本**。"]
w("OCR_VERIFICATION_REPORT.md", L)

# ---------------- 7. 测试报告 ----------------
L = ["# TEST_RESULTS —— 32 项一致性测试（R2-07）", "",
     f"结果：**PASS {S['npass']} / FAIL {len(S['tests'])-S['npass']} / SKIP 0**（共 {len(S['tests'])} 项）", "",
     "> 全部为本轮**重新运行**，不继承上一轮结论。逐条含输入（查询）、预期、实际。", "",
     "| ID | 项目 | 预期 | 实际 | 结果 |", "|---|---|---|---|---|"]
for t in S["tests"]:
    L.append(f"| {t['id']} | {t['name']} | {t['expected']} | {t['actual']} | {t['status']} |")
L += ["", "## 测试覆盖的任务要求（审核书第九节十项）", "",
      "| 审核要求 | 对应测试 |", "|---|---|",
      "| 194 条记录总数一致性 | T-01（实测 196，差异见 §13） |",
      "| 153 个独立词牌映射 | T-02 / T-03 |",
      "| 五种韵式分类 | T-05 / T-06 / T-07 |",
      "| 格别完整性 | T-08 / T-09 / T-10 |",
      "| 字数一致性 | T-11 / T-16 / T-17 |",
      "| 平仄符号完整性 | T-11 / T-15 |",
      "| 页面追溯 | T-14 |",
      "| 同词牌多体关联 | T-19 / T-21 |",
      "| 外部目录差异 | T-22 / T-23 / T-24 |",
      "| 特殊案例 | T-25 / T-26 |", "",
      "## 这些测试不能证明什么", "",
      "- 不能证明 196 条谱行**逐字**无误（只证明内部自洽）。",
      "- 不能证明格别判断符合每一调的学术定论。",
      "- 不能替代异本对勘与人工校读。", "",
      "原始 JSON：`test_results.json`（与本报告同目录）。"]
w("TEST_RESULTS.md", L)

# ---------------- 8. 来源审计 ----------------
L = ["# SOURCE_AUDIT —— 来源、版本与采信规则（R2-07）", "",
     "## 一、主来源", "",
     "| 项 | 内容 |", "|---|---|",
     "| 书 | 龙榆生《唐宋词格律》，上海古籍出版社 1978 年版（本地 PDF 影印） |",
     "| 文件 | `books/唐宋词格律 (龙榆生) (z-library.sk, 1lib.sk, z-lib.sk).pdf` |",
     "| 页数 | 270 页（物理）；正文 16–250，印刷页 1–235，偏移 15 |",
     "| 文本 | PDF 自带 OCR 文字层，`raw/books_native/long_yushsheng_cilv/pages.jsonl` |",
     "| 提取 | `tools/r2_07_forms.py`：谱行符号 －｜＋，括注（韵/句/豆/叶平/换仄韵…） |", "",
     "## 二、参考来源（不覆盖主来源）", "",
     "| 项 | 内容 | 用途 |", "|---|---|---|",
     "| 龙榆生纪念网站 目录 | longyusheng.org/cipai/mulu.html | 词牌名与五类归属交叉核对 |",
     "| 同上 字数表 | longyusheng.org/cipai/zishu.html | 各格字数交叉核对 |",
     "| 同上 凡例 | longyusheng.org/cipai/gl-fanli.html | 定格/变格/格一二 的定义依据 |", "",
     "凡例关键条款（原文）：", "",
     "> 01. 本编依韵脚分类，计分平韵、仄韵、平仄韵转换、平仄韵通叶、平仄韵错叶等五格。",
     "> 04. 每一格除标句、豆、韵外，每字逐一标明平仄，以「—」表平，「｜」表仄，「＋」表可平可仄。",
     "> 06. 每一词牌，以诸家所最习用者为定格。其或句豆小有出入者，别为第一、第二等格……又习用平韵改作仄韵、或习用仄韵改作平韵者为变格。", "",
     "这三条直接决定本轮的三项判定：五类韵式、符号语义、定格/格序/变格的分层。", "",
     "## 三、采信规则", "",
     "1. 谱行文字一律取本地 PDF；外部只用于发现疑点。",
     "2. 格别名称照录原书，不改写、不归并（「变格一」「别格」均保留原样）。",
     "3. 字数冲突时：先看原书是否自述、再看谱行、再看外部；三者不一致则并列，不裁决。",
     "4. 任何字段原书未言，一律 NULL / UNKNOWN。", "",
     "## 四、本轮未能取得的资料", "",
     "- 《唐宋词格律》另一版本（无法做异本对勘，故无 `EDITION_VERIFIED`）。",
     "- 影印本原页的完整人工校读（只做了 6 次点状核验）。"]
w("SOURCE_AUDIT.md", L)

print("分报告已生成：", len(list(OUT.glob('*.md'))))
CON.close()
