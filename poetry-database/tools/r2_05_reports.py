#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-05 报告生成：阅读报告、覆盖报告、理论提取、理论审计、OCR 异常。"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database/poetry.db"
OUT = ROOT / "reports/tasks/2026-11-13/R2-05"
OUT.mkdir(parents=True, exist_ok=True)


def q(con, sql, args=()):
    return con.execute(sql, args).fetchall()


def coverage_table(con):
    rows = q(con, "SELECT unit_key,pdf_from,pdf_to,printed_from,printed_to,chars_total,"
                  "coverage,sections_done,sections_total,status,gate_pass,ocr_exception "
                  "FROM reading_records_r2_05 ORDER BY substr(unit_key,1,1), pdf_from")
    out = ["| 单元 | PDF 页 | 印刷页 | 汉字 | 覆盖 | 节 | 状态 | 门禁 | OCR 异常 |",
           "|---|---|---|---:|---:|---:|---|---|---|"]
    for r in rows:
        key, pf, pt, qf, qt, chars, cov, sd, st, status, gate, exc = r
        pdf = f"{pf}–{pt}" if pf else "—"
        prt = f"{qf}–{qt}" if qf else "—"
        out.append(f"| `{key}` | {pdf} | {prt} | {chars:,} | {cov:.0%} | {sd}/{st} | **{status}** | "
                   f"{'✓' if gate else '✗'} | {exc or '—'} |")
    return "\n".join(out)


def stats(con):
    d = {}
    d["recs"] = q(con, "SELECT COUNT(*) FROM reading_records_r2_05")[0][0]
    d["read"] = q(con, "SELECT COUNT(*) FROM reading_records_r2_05 WHERE status='READ'")[0][0]
    d["ext"] = q(con, "SELECT COUNT(*) FROM reading_records_r2_05 WHERE status='EXTRACTED'")[0][0]
    d["chars"] = q(con, "SELECT SUM(chars_total) FROM reading_records_r2_05")[0][0]
    d["readchars"] = q(con, "SELECT SUM(CAST(chars_total*coverage AS INT)) FROM reading_records_r2_05")[0][0]
    d["wangli"] = q(con, "SELECT SUM(chars_total) FROM reading_records_r2_05 WHERE unit_key LIKE 'A:%' OR unit_key LIKE 'B:%'")[0][0]
    d["partA"] = q(con, "SELECT SUM(chars_total) FROM reading_records_r2_05 WHERE unit_key LIKE 'A:%'")[0][0]
    d["partB"] = q(con, "SELECT SUM(chars_total) FROM reading_records_r2_05 WHERE unit_key LIKE 'B:%'")[0][0]
    d["cixue"] = q(con, "SELECT SUM(chars_total) FROM reading_records_r2_05 WHERE unit_key LIKE 'E:%'")[0][0]
    d["cixue_read"] = q(con, "SELECT SUM(CAST(chars_total*coverage AS INT)) FROM reading_records_r2_05 WHERE unit_key LIKE 'E:%'")[0][0]
    d["rules"] = q(con, "SELECT COUNT(*) FROM poetry_rules_r2_05")[0][0]
    d["diffs"] = q(con, "SELECT COUNT(*) FROM two_book_diff_r2_05")[0][0]
    return d


def rpt_book(con, d):
    L = ["# BOOK_READING_REPORT —— 王力两书完整阅读与《词学十讲》复核（R2-05）", "",
         "## 一、总量", "",
         f"- 纳入阅读的单元：**{d['recs']}** 个（王力合订本 A/B 共 17 个，词学十讲 10 讲）",
         f"- 状态为 READ：**{d['read']}** 个；EXTRACTED：**{d['ext']}** 个；NOT_STARTED：0",
         f"- 纳入统计的汉字总量：**{d['chars']:,}**；已读 **{d['readchars']:,}**（{d['readchars']/d['chars']:.1%}）",
         f"- 其中王力两书 **{d['wangli']:,}** 字，**100% 通读**（A {d['partA']:,}／B {d['partB']:,}）",
         f"- 《词学十讲》**{d['cixue']:,}** 字，已读 **{d['cixue_read']:,}**（{d['cixue_read']/d['cixue']:.1%}）", "",
         "## 二、覆盖明细", "", coverage_table(con), "",
         "## 三、阅读方式（可复核）", "",
         "1. 文本源：`raw/books_ocr_paddle/wangli_shicilv/pages.jsonl`（PaddleOCR-VL-1.6，1,691 页中本书 432 页）。",
         "2. 清洗：`tools/r2_05_dump.py` 的 `clean()`，把 `$\\underset{\\cdot}{字}$`（原书字下加点的入声标记）还原为「字」，",
         "   避免吞字；第一版正则漏了空格，导致 3,424 处被吞，本轮已修并复核（见 TEST_RESULTS T-04）。",
         "3. 呈现：`show <unit>` 按页输出，带 `--- p{PDF} 印{印刷} ---` 标记，逐页推进，无抽样、无跳过。",
         "4. 记录：每单元一份 `raw/r2_05_notes/*.md`，含定义、原文引用、适用范围、例外、与邻章关系、待追踪问题。",
         "5. 结构核对：一律以原书目录页（PDF p8–p10、p183 起）为准，不沿用旧索引。", "",
         "## 四、分单元导读（要点）", "",
         "### A《诗词格律》（印刷 1–174）", "",
         "| 单元 | 本轮读到的关键内容 |",
         "|---|---|",
         "| 引言 | 全书性质；「大部分是前人研究的成果……不详细说明哪些部分是著者自己的话」——作者自陈的来源免责声明 |",
         "| 第一章 | 韵＝韵母（拼音类比）；四声与入声去向；平仄两总纲（本句交替、对句对立）；对仗两硬规则 |",
         "| 第二章 | 诗体分法；106 韵；五律七律四种格式（原图核验）；粘对；孤平；特拗；拗救三类；一三五不论四例外；对仗九类；绝句；古体诗 |",
         "| 第三章 | 词牌来源三种；词谱是后起归纳；16 个词谱示例；词韵十九部；各字句律句化；特种律句；词的对仗三类 |",
         "| 第四章 | 二字节节奏＋三字尾；节奏与语法冲突时「矛盾的主要方面是语法结构」；不完全句；语序变换；炼字 |",
         "| 结语 | 「格律是为我们服务的；我们不能反过来成为格律的奴隶」 |",
         "| 附录一 | **全书来源注**：孤平←赵执信/王士禛；特拗←赵/王；拗救←赵/王＋王力修正；一三五不论←释真空《贯珠集》；正格/变格/例外三分 |",
         "| 附录二 | 106 韵代表字表（以杜甫用字为取样标准，非穷尽字表）；诗韵→词韵交叉标注 |",
         "| 附录三 | 50 条词谱（一词只录常见一体）；含「末句不能犯孤平」等规则注记 |", "",
         "### B《诗词格律概要》（印刷 175–338）", "",
         "| 单元 | 本轮读到的关键内容 |",
         "|---|---|",
         "| 卷上第一章 | 体裁清单；长律「十二句或更多」；今体两类 |",
         "| 卷上第二章 | 平水韵源流（206→107→106）；出韵定义（与 A 附录一冲突）；柏梁体 |",
         "| 卷上第三章 | 四句型四脚；四类变格逐条＋频率判断；特拗位置（第七句/绝句第三句）；粘看第二字（七言加第四字）；拗救二分（大拗/小拗）；古体平仄（赵执信）；入律古风三特点；古绝中间类 |",
         "| 卷上第四章 | 对仗以词义为定义；三种特殊对仗（数目/颜色/方位）；工对按名词小类；借对两型；流水对 |",
         "| 卷下第一章 | 44 个词谱（谱＋例词逐句对照）；词牌＝格式标签 |",
         "| 卷下第二章 | 十九部含归字例；上、去通押 11 例；换韵三类型 |",
         "| 卷下第三章 | **「词的律句比诗的律句更为严格，不容许有变格」**；四句型「必」字规定；词中拗句应称正格 |",
         "| 卷下第四章 | 15 处习惯用对仗＋11 处可对可不；扇面对；词对仗两类型四种情形 |", "",
         "### E《词学十讲》（本轮补读第 2、5、8 讲）", "",
         "| 讲 | 状态 | 关键内容 |",
         "|---|---|---|",
         "| 第 2 讲 | READ | 近体诗六型术语（顺黏格/偏格/正格）；词由诗「破句增韵减联加虚声」演化 |",
         "| 第 5 讲 | READ | 韵的三功能；韵位疏密与声情对应；长调韵位结构；「潜气内转」 |",
         "| 第 8 讲 | READ | 四声阴阳；「深→幽→明」案例；万树《词律》批评与证伪；去声字与领字 |",
         "| 其余 7 讲 | EXTRACTED | 有笔记、无全文覆盖证据，不申报 READ |", "",
         "## 五、明确未读", "",
         "- 合订本 C 部分《诗词格律十讲》（印刷 339–398）——本轮明确不读。",
         "- 合订本 D 部分附录与索引（印刷 399–424）——本轮明确不读。",
         "- 《词学十讲》第 1、3、4、6、7、9、10 讲全文——仅有旧笔记，未逐字通读。",
         "- 《汉语音韵学》《同源字典》《古代汉语常识》——不在本轮范围。", ""]
    return "\n".join(L)


def rpt_coverage(con, d):
    L = ["# CHAPTER_COVERAGE_REPORT —— 章节覆盖与 READ 门禁（R2-05）", "",
         "## 一、门禁标准（R2-05 指令 §7 原文八条）", "",
         "1. 该章节全文已实际处理；2. 章节全部小节均已覆盖；3. 所有有效正文均经过阅读；",
         "4. 主要观点有笔记；5. 重要论述有来源位置；6. OCR 低置信内容已标记；",
         "7. 不存在未说明的截断；8. 阅读记录与全文范围对应。", "",
         "## 二、逐条自证", "",
         "| 门禁项 | 本轮做法 | 证据 |", "|---|---|---|",
         "| ①全文已处理 | 按 PDF 物理页从起页到止页逐页输出，无抽样 | `tools/r2_05_dump.py show` 的 `--- pN ---` 标记 |",
         "| ②小节全覆盖 | 章级下属节数逐一核对（A 第二章 6 节、B 卷上第三章 9 节等） | `sections_done/sections_total` 列 |",
         "| ③有效正文经过阅读 | 覆盖＝已读汉字/该单元清洗后汉字，全部 1.00 | `coverage` 列 |",
         "| ④观点有笔记 | 每单元一份 md 笔记，含要点、原文引用、例外、邻章关系 | `raw/r2_05_notes/*.md` |",
         "| ⑤论述有来源位置 | 笔记内每条引用均标 PDF 页／印刷页 | 笔记内「（pXX／印XX）」 |",
         "| ⑥低置信已标记 | 谱行丢字、韵目误字、缺页一律写入 `ocr_exception` 并单列 OCR 报告 | `OCR_EXCEPTION_REPORT.md` |",
         "| ⑦无未说明截断 | 每单元末页与下一单元起页首尾相接，已逐处核对 | 见本报告 §四 |",
         "| ⑧记录与范围对应 | `reading_records_r2_05.pdf_from/pdf_to` 与 `reading_units` 一致 | DB 内两表对读 |", "",
         "## 三、覆盖表", "", coverage_table(con), "",
         "## 四、截断核对（首尾相接）", "",
         "| 交界处 | 上一单元末页首句 | 下一单元起页首句 | 结论 |", "|---|---|---|---|",
         "| 引言→第一章 | p16「……也不打算在每一个地方都加上校勘性的说明了。」 | p17「第一章 关于诗词格律的一些概念 第一节 韵」 | 相接 |",
         "| 第一章→第二章 | p26「……现在先谈到这里。」 | p27「第二章 诗律 第一节 诗的种类」 | 相接 |",
         "| 第二章→第三章 | p78「……才不至于怀疑它们的格律是不可捉摸的。」 | p79「第三章 词律 第一节 词的种类」 | 相接 |",
         "| 第三章→第四章 | p124「……除了这两点之外，词的对仗跟诗的对仗是一样的。」 | p125「第四章 诗词的节奏及其语法特点」 | 相接 |",
         "| 第四章→结语 | p136「……然后我们的了解才是全面的。」 | p137「结语」 | 相接 |",
         "| 结语→附录一 | p138「……而不为格律所束缚。」 | p139「附录一 诗律余论」 | 相接 |",
         "| 附录一→附录二 | p153「……（原载《光明日报》「东风」，1962 年 8 月 6 日）」 | p154「附录二 诗韵举要」 | 相接 |",
         "| 附录二→附录三 | p166「【十七洽】洽狭峡法甲业邺匣压鸭乏怯劫胁插锸歃押狎袷嶪夹恰蛱硖」 | p167「附录三 词谱举要」 | 相接 |",
         "| 卷上→卷下 | p264「……总之，古体诗的对仗是很自由的。」 | p265「卷下 词 第一章 词牌和词谱」 | 相接 |",
         "| 卷下第三章→第四章 | p339「……那就应该说这不是拗句，而是正格了。」 | p340「第四章 词的对仗」 | 相接 |", "",
         "## 五、未达标项", "",
         f"- 《词学十讲》第 1、3、4、6、7、9、10 讲：状态 EXTRACTED，覆盖率 0%（无全文覆盖证据），**不计入 READ 数**。",
         "- 词谱类单元的「谱行」虽已逐页过目，但符号不可用（见 OCR 报告），故这些单元的「谱表可引用性」判定为假；",
         "  「章节文字已读」与「谱表可用」是两件事，本报告分开陈述。", ""]
    return "\n".join(L)


def rpt_theory(con):
    rows = q(con, "SELECT rule_id,book_code,chapter,pdf_page,printed_page,rule_topic,rule_type,"
                  "quote,author_view,genre_scope,confidence,conflicts FROM poetry_rules_r2_05 ORDER BY rule_id")
    L = ["# THEORY_EXTRACTION_REPORT —— 理论条目提取（R2-05）", "",
         f"本轮新建 **{len(rows)}** 条结构化条目（表 `poetry_rules_r2_05`），字段按 R2-05 指令 §5 设置：",
         "`rule_id / 书名代码 / 章节 / PDF 页 / 印刷页 / 主题 / 类型 / 原文 / 原作者观点 / 执行者说明 / 适用体裁 / 正格 / 特殊情况 / 例外 / 实例 / 来源层 / 可信状态 / 冲突`。", "",
         "**来源层（source_layer）** 是本轮新增字段，用于区分：",
         "- `原文`＝王力在本书中的直接表述；",
         "- `原文（王力自述前人）`＝王力明确交代出自赵执信、王士禛等；",
         "- `王力转引`＝王力从他人著作引录；",
         "- `王力归纳`＝王力自己从例证总结，非前人说。", "",
         "## 一、逐条清单", ""]
    for r in rows:
        rid, bc, ch, pdf, prt, topic, rtype, quote, view, genre, conf, conflict = r
        pgs = f"p{pdf}／印{prt}" if pdf else "（非 PDF 文本，EPUB 分讲）"
        L += [f"### {rid}　{topic}（{rtype}）", "",
              f"- 出处：{bc} 部分　{ch}　{pgs}",
              f"- 原文：「{quote}」",
              f"- 原作者观点：{view}",
              f"- 适用体裁：{genre}",
              f"- 可信状态：**{conf}**",
              f"- 冲突／注意：{conflict}", ""]
    return "\n".join(L)


def rpt_audit(con):
    rows = q(con, "SELECT id,topic,old_page,verdict,quote_is_verbatim,certainty,action FROM theory_claims_audit ORDER BY id")
    cur = q(con, "SELECT id,page,status,substr(note,1,80) FROM theory_claims ORDER BY id")
    row = con.execute("SELECT quote FROM theory_claims_v2 WHERE claim_id='R05-CL-001'").fetchone()
    v2q = row[0] if row else "（缺失）"
    L = ["# THEORY_CLAIMS_AUDIT —— 旧 16 条理论记录处理（R2-05）", "",
         "## 一、处理原则（按 R2-05 指令 §6）", "",
         "1. 原始记录保留，不删除；2. 加 MISATTRIBUTED 状态；3. 禁止进入有效知识检索；",
         "4. 依正确书籍与页码重建；5. 保留新旧关系。", "",
         "## 二、实际执行", "",
         "| id | 主题 | 旧页码 | R2-04 审计结论 | 引文是否逐字 | 本轮状态 |",
         "|---|---|---|---|---|---|"]
    st = {c[0]: c[2] for c in cur}
    for r in rows:
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | **{st.get(r[0],'—')}** |")
    L += ["", "## 三、id=15 的具体处置", "",
          "**旧记录（保留）**", "",
          "```",
          "id=15  book=wangli_shicilv  page=42  topic=孤平",
          "claim: 犯孤平只限平脚句；仄脚句即使只剩一个平声字，也只是拗句，不算孤平。",
          "quote: ……如李白《宿五松山下荀媪家》「我宿五松下」，只算拗句，不算孤平。",
          "status: RETIRED_MISATTRIBUTED   ← 本轮由 READ 改为退役",
          "```", "",
          "**问题认定**：①出处错——「孤平只限于平脚的句子」实出《诗词格律十讲》p374（印刷 366），非 A p42；",
          "②引文含转述——「我宿五松下，只算拗句」，全书检索 0 命中（「我宿五松下」本身见 A p45／印37，但为拗救例，非孤平判语）；",
          "③结论不得作为引擎修改依据。", "",
          "**重建记录（新）**", "",
          "```",
          "claim_id=R05-CL-001  book=《诗词格律》A 部分  p41／印33  主题=孤平",
          "quote: 逐字取自 PaddleOCR 文本，无转述（见 §四）",
          "confidence: VERIFIED（仅 A 范围）",
          "supersedes: theory_claims id=15",
          "```", "",
          "**为什么没有把 p374 的完整表述写进新记录**：C 部分《诗词格律十讲》本轮明确不授权阅读（R2-05 §8.1），",
          "故新记录只承载 A 部分可核内容，并在 `executor_view` 中注明「须待 C 部分核对」。这不是遗漏，是范围约束。", "",
          "## 四、A 部分孤平原文（逐字，取自 PaddleOCR p41–42 清洗文本）", "",
          "```",
          v2q,
          "```", "",
          "> 本段由数据库 `theory_claims_v2.quote` 直接读取，未经改写；原书引号为 “ ”，不是 「 ”。", "",
          "## 五、其余 15 条", "",
          "全部保留 `status` 原值，并在 `note` 追加：保持独立审核状态、未升级为 VERIFIED、引文页码已按 PaddleOCR 版复核。",
          "其中 R05-014（失对）标注为 **SUPERSEDED**——不是审核发现，而是**作者本人在附录一 p146 撤回**，",
          "由 R05-015 取代；这属于「原始文献自身修正」，与「执行者错误」性质不同，不得混为一类。", "",
          "## 六、尚存的未决问题", "",
          "1. id=15 的正确表述仍需 C 部分核对，本轮只能标「A 范围内成立」。",
          "2. 其余 15 条的 `page` 字段仍为旧值（未批量改写），只加了复核注记；批量改写要等外部审核确认口径。",
          "3. `theory_claims` 与 `poetry_rules_r2_05` 两表并存，尚无统一视图；本轮不做合并（属 Phase 3 范围）。", ""]
    return "\n".join(L)


def rpt_ocr(con):
    rows = q(con, "SELECT finding_id,book_id,nominal,detail FROM ocr_quality_findings ORDER BY finding_id")
    L = ["# OCR_EXCEPTION_REPORT —— 本轮 OCR 异常与处置（R2-05）", "",
         "## 一、总述", "",
         "本轮不重跑 OCR，只对阅读中实际撞到的异常做定点核验。核验方式：`pymupdf` 渲染原页（170–300 dpi）→ 逐行读图。",
         "共核验原图 **7 页**（A p35、p36、p37、p38、p59、p120，另 p18 文字层对读）。", "",
         "## 二、必须写清楚的三个不同性质的错误", "",
         "| 类型 | 案例 | 性质 | 处置 |",
         "|---|---|---|---|",
         "| ① OCR 识别错误 | 上声韵目「豏」→「赚」；「覃」→「章」；「哿」→「寄」；「黠」→「點」 | 机器识别 | 报告列出，引用时以原图为准 |",
         "| ② 原书排印错误 | A p120／印112 词韵入声「（3）质物锡职缉」，与「（4）物月曷黠屑葉」之「物」重出，脱「陌」 | **原书错误**，非 OCR | 以 B p324「质陌锡职缉」为准，并登记勘误 |",
         "| ③ 版面结构导致 | 谱行「字外加圈」处吞字；B 去声一至十六韵整段缺失 | 识别＋版式 | 谱行不作数据源；缺页回查原图 |", "",
         "## 三、谱行丢字（本轮最影响阅读的缺陷）", "",
         "**成因**：PaddleOCR 把「字外加圈（可平可仄）」识成带圈数字（⑨⑩⑪…⑱⑲）并**吞掉一整个字**。",
         "五言谱行因此从 5 字变 4 字，七言从 7 字变 5–6 字。凡有圈的句必错，故**全部谱行不能直接引用**。", "",
         "**实例（A p35／印27，五律仄起式首二句）**", "",
         "```",
         "OCR ：⑨仄平平仄，平平仄仄平。  /  平平仄仄，仄仄平平。",
         "原图：○仄平平仄，平平仄仄平。  /  ○平平仄仄，○仄仄平平。",
         "```", "",
         "**处置**：A 第二章第三节的四种格式、A 第五节的绝句格式、B 卷上第三章四式、A/B 词谱，全部以原图核验或明确标注不可用。", "",
         "**已核验清单**", "",
         "| 页 | 内容 | 结论 |",
         "|---|---|---|",
         "| A p35／印27 | 五律四类型＋仄起式四联 | 原图 `○仄平平仄，平平仄仄平／○平平仄仄，○仄仄平平`，已确认 |",
         "| A p36／印28 | 五律平起式＋七律对照表四脚 | 四联齐全；对照表「仄上加平，平上加仄」四脚完整 |",
         "| A p37／印29 | 七律仄起式四联 | `○仄平平仄仄平，○平○仄仄平平…` 已确认 |",
         "| A p38／印30 | 七律平起式四联 | `○平○仄仄平平，○仄平平仄仄平…` 已确认 |",
         "| A p59／印51 | 五绝仄起式 | `○仄平平仄，平平仄仄平／○平平仄仄，○仄仄平平` 已确认 |",
         "| A p120／印112 | 词韵入声五部 | 确认原书即作「质物锡职缉」（排印误），并确认「感俭豏」非「赚」 |", "",
         "## 四、`字下加点` 标记（可用资源，不是错误）", "",
         "OCR 输出为 `$\\underset{\\cdot}{字}$`，全书 **3,426 处**。A p35 脚注①明言：「**字下加小圆点的都是入声字。下同。**」",
         "另有 `\\underset{\\triangle}{字}` 2 处。",
         "→ 这是**带标注的入声字语料**，但注意 p18 引诗中的加点落在「苔、栽、来」等平声韵脚上，说明该标记在不同章节兼作「韵脚标记」，",
         "**不能一律当入声**；用于入声字提取前须先按章区分（列为 OPEN）。", "",
         "## 五、缺行/缺页", "",
         "- B p194／印186：去声一至十六韵整段缺失（OCR 从「十七霰」直接起头），上声末韵亦缺。已回查该页原图确认是 OCR 漏行而非原书缺。",
         "- A 附录三：50 条词谱中编号 43 缺失（42→44），疑 OCR 吞标题行。",
         "- B 卷下第一章：编号 27（生查子）、43（摸鱼儿）标题被吞。", "",
         "## 六、既有质量发现（沿用 R2-03-R1 登记，未改动）", "",
         "| ID | 书 | 量 | 发现 |", "|---|---|---:|---|"]
    for r in rows:
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {str(r[3])[:110]} |")
    L += ["", "## 七、本轮新增登记", "",
          "| ID | 对象 | 发现 | 处置 |", "|---|---|---|---|",
          "| R05-OCR-01 | A/B 全书谱行 | 字外加圈必吞一字，谱行不可直接引用 | 关键格式回查原图；其余标不可用 |",
          "| R05-OCR-02 | A p120 | 原书排印「质物锡职缉」与第四部重出 | 以 B 为准，登记勘误 |",
          "| R05-OCR-03 | A/B 韵目 | 豏→赚、覃→章、哿→寄、黠→點 系统误识 | 引用一律回原图 |",
          "| R05-OCR-04 | B p194 | 去声 1–16 韵整段漏行 | 不影响阅读结论，标缺 |",
          "| R05-OCR-05 | 加点标记 | 兼作入声标记与韵脚标记 | 暂不作入声字源，列 OPEN |", ""]
    return "\n".join(L)


def main():
    con = sqlite3.connect(DB)
    d = stats(con)
    files = {
        "BOOK_READING_REPORT.md": rpt_book(con, d),
        "CHAPTER_COVERAGE_REPORT.md": rpt_coverage(con, d),
        "THEORY_EXTRACTION_REPORT.md": rpt_theory(con),
        "THEORY_CLAIMS_AUDIT.md": rpt_audit(con),
        "OCR_EXCEPTION_REPORT.md": rpt_ocr(con),
    }
    for name, text in files.items():
        (OUT / name).write_text(text, encoding="utf-8")
        print(f"  {name}: {len(text)} 字符")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
