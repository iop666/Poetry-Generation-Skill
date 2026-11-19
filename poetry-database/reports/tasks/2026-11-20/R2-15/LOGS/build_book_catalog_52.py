# -*- coding: utf-8 -*-
"""R2-15B 构建 BOOK_CATALOG_52.csv 与 MISSING_MATERIALS.csv（只读，不联网，不改库）。

状态词（按任务书）：
NOT_FOUND / CHANNEL_IDENTIFIED / ACQUIRED / PARSED / READ /
READ_WITH_SOURCE_GAP / EXTRACTED / REVIEWED
另用 UNRESOLVED 作为「已有取得但无阅读证据」的哨兵值（任务书允许的「没有就写 UNRESOLVED」）。
"""
import csv
import os

OUT = os.path.dirname(os.path.abspath(__file__)).replace("/LOGS", "")
CSV_PATH = os.path.join(OUT, "BOOK_CATALOG_52.csv")
MISS_PATH = os.path.join(OUT, "MISSING_MATERIALS.csv")

COLS = [
    "book_id", "书名", "作者", "版本或出版信息", "acquired_edition",
    "资料类别", "版权状态", "合法获取渠道",
    "acquisition_status", "parse_status", "reading_status", "extraction_status",
    "reading_scope", "source_gap", "local_evidence_path", "db_book_id", "note",
]

R = []


def add(**kw):
    row = {c: "" for c in COLS}
    row.update(kw)
    R.append(row)


# ---------------- A 格律理论 9 ----------------
add(book_id="A1", 书名="诗词格律", 作者="王力",
    版本或出版信息="中华书局 1977（初版 1962）",
    acquired_edition="王力全集合订本扫描 PDF 之 A 部分（PDF p15–182，PaddleOCR-VL-1.6，432 页全书）",
    资料类别="现代版权著作", 版权状态="IN_COPYRIGHT",
    合法获取渠道="用户提供扫描本（仅本地研究，不再分发）；备选：购买纸本／图书馆借阅",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="READ", extraction_status="EXTRACTED",
    reading_scope="A 部分 9/9 单元（引言＋四章＋结语＋附录一至三），57,086 汉字",
    source_gap="9 个单元中 5 个带 OCR 例外：p25 谱例圈号误识；第二章平仄谱行丢字；第三章 35 页词谱谱行不可用；附录二韵目字误（豏→赚等）；附录三 50 条词谱谱行不可用。仅 6 页回查原图，未逐字校全",
    local_evidence_path="raw/books_ocr_paddle/wangli_shicilv/pages.jsonl；raw/r2_05_notes/A_*.md；poetry.db: reading_records_r2_05（9 行，gate_pass=9）、book_pages_paddle",
    db_book_id="wangli_shicilv",
    note="R1 记「未取得」；R2-03-R1 重跑 OCR 后取得。合订本另含《诗词格律概要》《诗词格律十讲》，不属本条，故 A1 自身只覆盖 9 单元/57,086 字")

add(book_id="A2", 书名="汉语诗律学", 作者="王力",
    版本或出版信息="上海教育出版社 2005（初版 1958）",
    acquired_edition="无",
    资料类别="现代版权著作", 版权状态="IN_COPYRIGHT",
    合法获取渠道="购买纸本（上海教育 2005）／图书馆借阅／微信读书·读秀（书目可见，全文受限）",
    acquisition_status="CHANNEL_IDENTIFIED", parse_status="NOT_FOUND",
    reading_status="NOT_FOUND", extraction_status="NOT_FOUND",
    reading_scope="0",
    source_gap="全书未取得；唐诗拗救与诗律系统论述缺第一手依据",
    local_evidence_path="reports/round-1/01_文献目录与来源调查.md §A2；reports/round-1/03_书籍阅读与提取报告.md §五；poetry.db: books(BK-WANGLI-SHILV, status=FOUND)",
    db_book_id="BK-WANGLI-SHILV",
    note="books 表 status=FOUND 为 R1 遗留状态词，按本轮规范应为 CHANNEL_IDENTIFIED；未伪称已读")

add(book_id="A3", 书名="唐宋词格律", 作者="龙榆生",
    版本或出版信息="上海古籍出版社 1978（初版 1962）",
    acquired_edition="上海古籍 1978 排印本 PDF 文字层（270 页，122,155 字）",
    资料类别="公版整理本",
    版权状态="PUBLIC_DOMAIN",
    合法获取渠道="用户提供 PDF；备选：购买旧书／图书馆借阅",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="通读体例与凡例、逐调抽读 16 调定格；未逐调通读 153 调/196 格",
    source_gap="135/196 格未逐调通读；谱式未与印本逐符号对校（R2-07：EDITION_VERIFIED=0）；词谱为 PDF 文字层，未 OCR 校字",
    local_evidence_path="raw/books_native/long_yushsheng_cilv/；poetry.db: book_pages（270 页）、cipai_forms_r2_07（196 行）、reading_progress（READ_STRUCTURE）",
    db_book_id="long_yushsheng_cilv",
    note="R1 记「未取得」，R2-03 取得。本表不写 READ：仅有结构级/抽样阅读（READ_STRUCTURE），无逐调通读证据。作者 1966 年卒，正文保护期已届满；1978 排印本点校/版式可能另有权")

add(book_id="A4", 书名="钦定词谱", 作者="王奕清等奉敕编",
    版本或出版信息="中国书店影印 2010（原书 1715）",
    acquired_edition="御定詞譜 40 卷 wikitext（文渊阁四库全书本，维基文库转录，1.5 MB）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（CC BY-SA 4.0，原文 PD）；登记影印本须购买",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="NOT_FOUND",
    reading_scope="0（仅解析，无阅读记录）",
    source_gap="版本错位：登记「中国书店 2010 影印本」，实得四库本转录，非同一版本；未通读，未逐调建谱",
    local_evidence_path="raw/books/cipu/卷01–40.wikitext；catalog/sources.jsonl: WS-REF-CIPU（40 条，parse_status=PARSED）；R2-01 §4.5",
    db_book_id="BK-QDCP",
    note="R1 称「影印本未得」仍成立；转录本可检索，但不可当登记影印本引用")

add(book_id="A5", 书名="词律", 作者="万树",
    版本或出版信息="上海古籍出版社影印 1984（原书 1687）",
    acquired_edition="詞律 20 卷 wikitext（四库全书本，维基文库转录，792 KB）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（CC BY-SA 4.0，原文 PD）；登记影印本须购买",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="NOT_FOUND",
    reading_scope="0（仅解析，无阅读记录）",
    source_gap="版本错位（登记影印本 vs 实得四库转录）；未通读，未与《钦定词谱》逐调对校",
    local_evidence_path="raw/books/cilv/卷01–20.wikitext；catalog/sources.jsonl: WS-REF-CILV（20 条，PARSED）；R2-01 §4.5",
    db_book_id="BK-CILV",
    note="R1 记「未取得」")

add(book_id="A6", 书名="文镜秘府论", 作者="遍照金刚（空海）",
    版本或出版信息="维基文库白文（六卷）",
    acquired_edition="维基文库白文六卷 wikitext（184,752 字节）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（CC BY-SA 4.0，原文 PD）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="READ", extraction_status="EXTRACTED",
    reading_scope="六卷全读（天卷·调声／地卷·八种韵／东卷·二十九种对／西卷·二十八病／南卷·论文意／北卷·论对属）",
    source_gap="白文无注，王利器校注本未得；全书未见「孤平」一词",
    local_evidence_path="raw/books/ws_wenjing.wikitext；poetry.db: read_log（A6，6 行 READ_FULL）；research/book_reading_notes/01_文镜秘府论.md；poetry_rules_r2_05",
    db_book_id="",
    note="R1 六卷全读有 read_log 逐卷支撑")

add(book_id="A7", 书名="声律启蒙", 作者="车万育",
    版本或出版信息="chinese-poetry＋维基文库（两源）",
    acquired_edition="raw/poetry/shenglv/shenglvqimeng.json（30,154 B）＋ sup_shenglv.wikitext（26,618 B）；ws_shenglvqi.wikitext 仅 25 B 重定向",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="chinese-poetry（MIT）＋维基文库（CC BY-SA 4.0）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="READ", extraction_status="EXTRACTED",
    reading_scope="3/30 韵细读（一东／二冬／三江）",
    source_gap="read_log 明记其余 27 韵 NOT_READ；书级 READ 仅覆盖 3/30 韵",
    local_evidence_path="raw/poetry/shenglv/shenglvqimeng.json；raw/books/sup_shenglv.wikitext；poetry.db: read_log（A7：READ_FULL＋NOT_READ）；research/book_reading_notes/04_*.md",
    db_book_id="",
    note="R1 03 报告已注明「READ（部分）」，本条按实际覆盖写 READ 并在 reading_scope 限定")

add(book_id="A8", 书名="诗韵合璧", 作者="汤文璐编",
    版本或出版信息="上海古籍出版社影印",
    acquired_edition="无",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="购买纸本／图书馆借阅",
    acquisition_status="CHANNEL_IDENTIFIED", parse_status="NOT_FOUND",
    reading_status="NOT_FOUND", extraction_status="NOT_FOUND",
    reading_scope="0",
    source_gap="未取得；平水韵工具书缺校勘来源，库内平水韵为另一来源（维基转录）",
    local_evidence_path="reports/round-1/01_文献目录与来源调查.md §A8；round-1/ROUND-1_完整详细报告.md §4.2 A8",
    db_book_id="",
    note="R1「FOUND，未取得」")

add(book_id="A9", 书名="文镜秘府论校注", 作者="王利器",
    版本或出版信息="中国社会科学出版社 1983",
    acquired_edition="无",
    资料类别="现代版权著作", 版权状态="IN_COPYRIGHT",
    合法获取渠道="购买纸本／图书馆借阅",
    acquisition_status="CHANNEL_IDENTIFIED", parse_status="NOT_FOUND",
    reading_status="NOT_FOUND", extraction_status="NOT_FOUND",
    reading_scope="0",
    source_gap="未取得；仅有白文，无校注，异文与注释无法引用",
    local_evidence_path="reports/round-1/01_文献目录与来源调查.md §A9；research/book_reading_notes/05_现代版权专著未获取说明.md",
    db_book_id="",
    note="王利器 1912–1998，保护期内")

# ---------------- B 韵书 8 ----------------
add(book_id="B1", 书名="切韵", 作者="陆法言",
    版本或出版信息="中华书局（周祖谟校笺）2004（原书 601）",
    acquired_edition="无",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="购买纸本（周祖谟校笺本）／图书馆借阅；原书仅存残卷",
    acquisition_status="CHANNEL_IDENTIFIED", parse_status="NOT_FOUND",
    reading_status="NOT_FOUND", extraction_status="NOT_FOUND",
    reading_scope="0",
    source_gap="原书仅存残卷；校笺本未得；库内无切韵数据",
    local_evidence_path="reports/round-1/01_文献目录与来源调查.md §B1",
    db_book_id="BK-QIYUN",
    note="版权状态指原书；周祖谟校笺本本身 IN_COPYRIGHT")

add(book_id="B2", 书名="广韵", 作者="陈彭年等",
    版本或出版信息="中华书局（余迺永校注）2011（原书 1008）",
    acquired_edition="原本广韵 5 卷 wikitext（钦定四库全书本，维基文库转录，720 KB）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（CC BY-SA 4.0）；登记校注本须购买",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="0（建表未通读）",
    source_gap="版本错位（登记余迺永校注本 vs 实得四库转录）；20,530 条反切／3,730 小韵，仅 9 条影印对校；小韵首以结构标记重认",
    local_evidence_path="raw/books/guangyun/卷1–5.wikitext；poetry.db: guangyun_fanqie_r2_10（20,530）、guangyun_fanqie_validation_r2_11（3,730）、rhyme_source_books_r2_11",
    db_book_id="BK-GUANGYUN",
    note="R1 称「多音字唯一依据，未取得」，现部分解决：反切表已建，但仅 9 条真对校")

add(book_id="B3", 书名="集韵", 作者="丁度等",
    版本或出版信息="上海古籍出版社影印 1985（原书 1039）",
    acquired_edition="《集韻》四库全书本 206 页维基转录（raw/r2_08/jiyun_pages）；另有失败版 raw/books/jiliyun（10 卷仅 40 KB）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（CC BY-SA 4.0）；登记影印本须购买",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="0（建表未通读）",
    source_gap="R2-01 首采仅韵例、不可用；v3 为 33,664 字组／42,352 字级索引，227 条 POSITION_ONLY，4 韵未定位小韵；未对图",
    local_evidence_path="raw/r2_08/jiyun_pages/*.json；poetry.db: jiyun_entry_r2_12（33,664）、jiyun_char_index_r2_12（42,352）；R2-12 §3.3",
    db_book_id="BK-JIYUN",
    note="raw/books/jiliyun 是 2026-11-12 的失败版（仅 40 KB），勿与 R2-08 重采版混用；R2-11「30,862 条」不可复现，已弃用")

add(book_id="B4", 书名="平水韵", 作者="佚名（宋末）",
    版本或出版信息="仅库内《平水韻》JSON（R1 称出处不明）",
    acquired_edition="维基文库《平水韻》转录（raw/r2_09/rhyme/平水韻.json，106 韵）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（CC BY-SA 4.0）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="0（建表未通读）",
    source_gap="出处已查明为维基转录（推翻 R1「出处不明」）；属诗韵分类，非韵书原书；字表为后世通行本，未与印本对勘",
    local_evidence_path="raw/r2_09/rhyme/平水韻.json；poetry.db: rhyme_source_books_r2_11（PINGSHUI_YUN，106 韵）",
    db_book_id="",
    note="R1 记 10,648 条目／8,550 繁／8,361 简，本轮未复算，不继承该数字")

add(book_id="B5", 书名="词林正韵", 作者="戈载",
    版本或出版信息="上海古籍出版社影印 1981（原书 1821）",
    acquired_edition="维基文库转录（19 部，5,563 条）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（CC BY-SA 4.0）；登记影印本须购买",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="0（建表未通读）",
    source_gap="按部-声调-韵目组织，非小韵结构；未与影印本对校；R1「无字表」已不成立（现有 5,563 条转录字表）",
    local_evidence_path="poetry.db: ph_cilin_r2_09（5,563）、rhyme_source_books_r2_11；ph_systems_r2_08（ci_rhyme=PARTIAL）",
    db_book_id="BK-CILIN",
    note="版本错位：登记上海古籍影印本，实得维基转录")

add(book_id="B6", 书名="中原音韵", 作者="周德清",
    版本或出版信息="中华书局 1978（原书 1324）",
    acquired_edition="维基文库转录（19 部，5,731 条）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（CC BY-SA 4.0）；登记整理本须购买",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="0（建表未通读）",
    source_gap="19 部/5,731 条；入声派三声需逐条核；未与整理本对校",
    local_evidence_path="poetry.db: ph_zhongyuan_r2_09（5,731）、rhyme_source_books_r2_11；ph_systems_r2_08（yuan_qu=PARTIAL）",
    db_book_id="BK-ZHONGYUAN",
    note="R1「未取得」，R2-09 取得转录；raw/books/zhongzhou 是中州集，不是中原音韵，勿混")

add(book_id="B7", 书名="中华通韵", 作者="中华诗词学会",
    版本或出版信息="2019 年颁布（十六韵）",
    acquired_edition="无；库内另有《中华新韵（十四韵）》2005 转录（zhonghua_xinyun_*）",
    资料类别="工具书", 版权状态="UNKNOWN",
    合法获取渠道="中华诗词学会官方发布页／购买纸本",
    acquisition_status="CHANNEL_IDENTIFIED", parse_status="NOT_FOUND",
    reading_status="NOT_FOUND", extraction_status="NOT_FOUND",
    reading_scope="0",
    source_gap="关键替代错误：库内 zhonghua_xinyun_characters_r2_11 是 2005《中华新韵》十四韵，不是 2019《中华通韵》十六韵，不得互替",
    local_evidence_path="poetry.db: rhyme_source_books_r2_11（ZHONGHUA_XINYUN，14 韵）、zhonghua_xinyun_characters_r2_11（7,597）、ph_systems_r2_08（modern_rhyme=DERIVED）",
    db_book_id="",
    note="R1 记「FOUND，未取得」。本条最容易被误当已取得，须在引用时明确区分「新韵」与「通韵」")

add(book_id="B8", 书名="汉语语音史", 作者="王力",
    版本或出版信息="商务印书馆",
    acquired_edition="无；库内 wangli_yinyunxue 为《汉语音韵学》，另一本书",
    资料类别="现代版权著作", 版权状态="IN_COPYRIGHT",
    合法获取渠道="购买纸本／图书馆借阅",
    acquisition_status="CHANNEL_IDENTIFIED", parse_status="NOT_FOUND",
    reading_status="NOT_FOUND", extraction_status="NOT_FOUND",
    reading_scope="0",
    source_gap="未取得；《汉语音韵学》（476 页 OCR）不能替代本书，二者体例与范围不同",
    local_evidence_path="reports/round-1/01_文献目录与来源调查.md §B8；poetry.db: book_items(wangli_yinyunxue)",
    db_book_id="",
    note="R1「FOUND，未取得」；后续取得的王力四种不含本书")

# ---------------- C 总集 16 ----------------
add(book_id="C1", 书名="诗经", 作者="佚名（毛诗）",
    版本或出版信息="chinese-poetry 整理本（无底本声明）",
    acquired_edition="raw/poetry/shijing（156,972 B）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="chinese-poetry（MIT）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="仅《关雎》1 篇有精读卡片；未逐篇阅读",
    source_gap="无逐篇阅读记录；R1 01 称 READ（关雎精读）但 03 未列入已读 7 种、read_log 无记录，书级 READ 不成立；305 篇文本已入库",
    local_evidence_path="raw/poetry/shijing；poetry.db: works(collection='shijing', 305)；research/poetry_analysis/cards_manual.md §一",
    db_book_id="",
    note="状态由「报告称 READ」下调为 UNRESOLVED：有 1 篇卡片，无书级阅读证据")

add(book_id="C2", 书名="楚辞", 作者="屈原等（王逸章句）",
    版本或出版信息="chinese-poetry 整理本（无底本声明）",
    acquired_edition="raw/poetry/chuci（141,832 B）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="chinese-poetry（MIT）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="仅《离骚》1 篇有精读卡片；未逐篇阅读",
    source_gap="65 条含汉人拟作（《七谏》《九叹》《九思》等），非《楚辞章句》十七卷；无书级阅读记录",
    local_evidence_path="raw/poetry/chuci；poetry.db: works(collection='chuci', 65)；cards_manual.md §三",
    db_book_id="",
    note="R1 01 称 READ（离骚精读），与 C1 同：单篇卡片不等于书级 READ")

add(book_id="C3", 书名="全唐诗", 作者="彭定求等编",
    版本或出版信息="chinese-poetry 整理本（58 片）",
    acquired_edition="raw/poetry/tang/poet.tang.*.json（58 片）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="chinese-poetry（MIT）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="0（语料级入库，无阅读）",
    source_gap="无底本声明、未与印本对勘；R1 55,630 条，本轮 works=55,308（−322，去重/修订口径）",
    local_evidence_path="raw/poetry/tang（58 文件）；poetry.db: works(collection='tang', 55,308)；sources CP-TANG 58 条",
    db_book_id="",
    note="R1 记 55,308 与 55,630 两说，本轮以库内实测 55,308 为准")

add(book_id="C4", 书名="唐诗三百首", 作者="蘅塘退士（孙洙）",
    版本或出版信息="chinese-poetry 整理本",
    acquired_edition="raw/poetry/tang300",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="chinese-poetry（MIT）／维基文库",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="仅 cards_manual 中零散唐诗卡片，未证出自本书；未通读",
    source_gap="无通读记录；R1 称 READ 无 read_log/笔记条目支撑",
    local_evidence_path="raw/poetry/tang300；poetry.db: works(collection='tang300', 320)；cards_manual.md",
    db_book_id="",
    note="320 首与通行选目数量吻合，但「读」与「入库」是两件事")

add(book_id="C5", 书名="全宋词", 作者="唐圭璋编",
    版本或出版信息="chinese-poetry 整理本（22 片）",
    acquired_edition="raw/poetry/songci/*.json（22 片）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="chinese-poetry（MIT）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="0（语料级入库）",
    source_gap="无底本声明、未对勘；R1 19,595 首，本轮 18,794（−801，去重口径）",
    local_evidence_path="raw/poetry/songci（22 文件）；poetry.db: works(collection='songci', 18,794)",
    db_book_id="",
    note="唐圭璋 1990 卒，编校著作权另计；此处版权状态指所收宋词原文")

add(book_id="C6", 书名="全宋诗", 作者="北京大学古文献研究所编",
    版本或出版信息="chinese-poetry 整理本（R1 仅 4 片，现 255 片）",
    acquired_edition="raw/poetry/songshi（255 片）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="chinese-poetry（MIT）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="0（语料级入库）",
    source_gap="R1 仅 4 片约 3,975 首，现 255 片／252,884 首；仍无底本声明、未与《全宋诗》印本对勘",
    local_evidence_path="raw/poetry/songshi（255 文件）；poetry.db: works(collection='songshi', 252,884)；R2-01 §4.4",
    db_book_id="",
    note="R1 最大缺口之一已在 R2-01 补齐；但「全」仍指分片数量，不等于逐首校勘")

add(book_id="C7", 书名="花间集", 作者="赵崇祚编",
    版本或出版信息="chinese-poetry 整理本（10 卷＋序）",
    acquired_edition="raw/poetry/huajianji/*.json（10 卷＋序）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="chinese-poetry（MIT）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="0（语料级入库）",
    source_gap="通行本 500 首，库内 498 首，差 2 首未说明；未对勘",
    local_evidence_path="raw/poetry/huajianji；poetry.db: works(collection='huajianji', 498)",
    db_book_id="",
    note="后蜀赵崇祚编；通行本 500 首，库内 498，差 2 首原因未查")

add(book_id="C8", 书名="南唐二主词", 作者="李璟、李煜",
    版本或出版信息="chinese-poetry 整理本",
    acquired_edition="raw/poetry/nantang",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="chinese-poetry（MIT）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="0（语料级入库）",
    source_gap="45 首含存疑/断句词，未辨真伪；未对勘",
    local_evidence_path="raw/poetry/nantang；poetry.db: works(collection='nantang', 45)",
    db_book_id="",
    note="45 首含存疑词与断句异文，真伪未辨；未与《南唐二主词校订》对校")

add(book_id="C9", 书名="元曲", 作者="隋树森等编（库内未标）",
    版本或出版信息="chinese-poetry 整理本（元曲全量）",
    acquired_edition="raw/poetry/yuanqu（4,188,599 B）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="chinese-poetry（MIT）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="0（语料级入库）",
    source_gap="1,729 条标题/正文字段错位（R2-13 翻案：非缺文）；24 条源本身截断（R2-14）；均未修",
    local_evidence_path="raw/poetry/yuanqu；poetry.db: works(collection='yuanqu', 10,685)、yuanqu_text_audit_r2_13（4,510）；R2-13 §8、R2-14 §5",
    db_book_id="",
    note="R1「多为剧曲」；R2-13/14 证明缺文主因是字段错位，不是语料缺失")

add(book_id="C10", 书名="纳兰性德诗集", 作者="纳兰性德",
    版本或出版信息="chinese-poetry 整理本",
    acquired_edition="raw/poetry/nalan",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="chinese-poetry（MIT）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="0（语料级入库）",
    source_gap="258 首；未与通志堂本对校",
    local_evidence_path="raw/poetry/nalan；poetry.db: works(collection='nalan', 258)",
    db_book_id="",
    note="纳兰性德 1685 卒，公版；258 首未与通志堂本对校")

add(book_id="C11", 书名="乐府诗集", 作者="郭茂倩编",
    版本或出版信息="维基文库（R1 仅目录页）",
    acquired_edition="无",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（需逐卷抓取）／ctext／购买纸本",
    acquisition_status="CHANNEL_IDENTIFIED", parse_status="NOT_FOUND",
    reading_status="NOT_FOUND", extraction_status="NOT_FOUND",
    reading_scope="0",
    source_gap="维基仅存目录页，未取正文；库内无 yuefu collection；《古诗纪》(gushiji) 不是《乐府诗集》，不可替代",
    local_evidence_path="reports/round-1/01_文献目录与来源调查.md §C11；poetry.db: works 无乐府诗集 collection",
    db_book_id="",
    note="R1「FOUND，未取正文」；后续未补")

add(book_id="C12", 书名="古诗十九首", 作者="佚名",
    版本或出版信息="无独立单行本；文本见《昭明文选》《古诗纪》",
    acquired_edition="经《昭明文选》卷19–31 与《古诗纪》间接取得",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（文选／古诗纪）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="0（无阅读）",
    source_gap="按题名精确检索仅 7/19 首可检出（行行重行行、青青陵上柏、涉江采芙蓉、明月皎夜光、冉冉孤生竹、去者日以疏、明月何皎皎 等），其余 12 首未单独立目或题名异写",
    local_evidence_path="poetry.db: works(title_raw in 十九首题名) → 7 首命中（wenxuan/gushiji）；raw/books/wenxuan、raw/books/gushiji",
    db_book_id="",
    note="R1「页面仅 1,667 字节，疑为目录」；现经文选取得部分，但仍不完整")

add(book_id="C13", 书名="昭明文选", 作者="萧统编",
    版本或出版信息="维基文库（60 卷）",
    acquired_edition="昭明文選 卷19–31（13 卷，诗类），1.0 MB",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（CC BY-SA 4.0）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="0（入库未读）",
    source_gap="60 卷仅得 13 卷（19–31，诗类）；赋、书、序、论等未取；works 357 条",
    local_evidence_path="raw/books/wenxuan（13 文件）；catalog/sources.jsonl: WS-WENXUAN 13 条；poetry.db: works(collection='wenxuan', 357)",
    db_book_id="",
    note="R1「FOUND，未取得」，R2-01 取诗类 13 卷")

add(book_id="C14", 书名="先秦汉魏晋南北朝诗", 作者="逯钦立",
    版本或出版信息="中华书局 1983",
    acquired_edition="无；库内以《古诗纪》156 卷（6,159 首）作替代",
    资料类别="现代版权著作", 版权状态="IN_COPYRIGHT",
    合法获取渠道="购买纸本／图书馆借阅",
    acquisition_status="CHANNEL_IDENTIFIED", parse_status="NOT_FOUND",
    reading_status="NOT_FOUND", extraction_status="NOT_FOUND",
    reading_scope="0",
    source_gap="未取得；《古诗纪》不是同一书，且收录范围/校勘不同；魏晋南北朝覆盖仍不完整",
    local_evidence_path="raw/books/gushiji（156 卷）；poetry.db: works(collection='gushiji', 6,159)；reports/round-1/01 §C14",
    db_book_id="",
    note="R1 称「本轮最大缺口」；古诗纪只是部分代偿，不能记作已取得本书")

add(book_id="C15", 书名="明诗综／清诗汇／元诗选", 作者="朱彝尊／徐世昌／顾嗣立",
    版本或出版信息="维基文库（3 部合 1 条）",
    acquired_edition="明詩綜 100 卷（3.1 MB）＋晚晴簃詩匯 200 卷（9.2 MB）；元诗选无",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（CC BY-SA 4.0）；元诗选须另购/借",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="UNRESOLVED", extraction_status="EXTRACTED",
    reading_scope="0（入库未读）",
    source_gap="3 部中 2 部取得；元诗选未得。明 7,641 首、清 19,864 首；均未对校",
    local_evidence_path="raw/books/mingshi（100 卷）、raw/books/wanqing（200 卷）；poetry.db: works(mingshi 7,641 / wanqing 19,864)",
    db_book_id="",
    note="本条按 R1 原样保留 1 行（3 部合 1 条）；按书名计全书目为 54 部，故 52 条≠52 部")

add(book_id="C16", 书名="宋词三百首", 作者="朱祖谋编",
    版本或出版信息="1924 初版（公有领域）",
    acquired_edition="无",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="购买纸本／维基文库（未见足本）",
    acquisition_status="CHANNEL_IDENTIFIED", parse_status="NOT_FOUND",
    reading_status="NOT_FOUND", extraction_status="NOT_FOUND",
    reading_scope="0",
    source_gap="未取得；《全宋词》只能替代检索，不能替代选目与笺注",
    local_evidence_path="reports/round-1/01_文献目录与来源调查.md §C16",
    db_book_id="",
    note="R1「FOUND，未取得」")

# ---------------- D 文论 8 ----------------
add(book_id="D1", 书名="文心雕龙", 作者="刘勰",
    版本或出版信息="维基文库白文（十篇）",
    acquired_edition="维基文库白文十篇（神思、体性、风骨、通变、情采、声律、丽辞、比兴、物色、知音）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（CC BY-SA 4.0）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="READ", extraction_status="EXTRACTED",
    reading_scope="10/50 篇全读",
    source_gap="40 篇未读；白文无注，范文澜注本未得",
    local_evidence_path="raw/books/ws_wxd_*.wikitext（10 篇）；poetry.db: read_log（D1，10 行 READ_FULL）；research/book_reading_notes/02_文心雕龙.md",
    db_book_id="BK-WENXIN",
    note="R1 明确写「READ（十篇）」，故按选读 10 篇记 READ，不冒充全书")

add(book_id="D2", 书名="诗品", 作者="钟嵘",
    版本或出版信息="维基文库白文（序＋三卷）",
    acquired_edition="维基文库《詩品》序＋卷上／中／下",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（CC BY-SA 4.0）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="READ", extraction_status="EXTRACTED",
    reading_scope="序全读＋上品十八家全读；中、下品抽查",
    source_gap="中、下品未通读（read_log 仅 SAMPLED）",
    local_evidence_path="raw/books/ws_shipin.wikitext、sup_shipin_1–3.wikitext；read_log（D2：READ_FULL×2＋SAMPLED）；notes/03_诗品.md",
    db_book_id="",
    note="R1「序＋上品」有逐卷登记")

add(book_id="D3", 书名="二十四诗品", 作者="司空图",
    版本或出版信息="维基文库白文",
    acquired_edition="raw/books/ws_24shipin.wikitext（4,843 B）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（CC BY-SA 4.0）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="READ", extraction_status="EXTRACTED",
    reading_scope="二十四品全读",
    source_gap="白文无注；真伪（司空图作者说）未处理",
    local_evidence_path="raw/books/ws_24shipin.wikitext；read_log（D3，READ_FULL）；notes/04_*.md",
    db_book_id="",
    note="司空图（837–908）公版；作者归属存疑（今人或疑非司空图作），本条只登记阅读事实，不裁作者")

add(book_id="D4", 书名="沧浪诗话", 作者="严羽",
    版本或出版信息="维基文库白文（五卷）",
    acquired_edition="维基文库五卷（诗辨／诗体／诗法／诗评／考证）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（CC BY-SA 4.0）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="READ", extraction_status="EXTRACTED",
    reading_scope="诗辨、诗法全读；诗体／诗评／考证抽样",
    source_gap="3/5 卷仅抽样（read_log 仅 SAMPLED）",
    local_evidence_path="raw/books/sup_canglang_1–5.wikitext；read_log（D4：READ_FULL×2＋SAMPLED）；notes/04_*.md",
    db_book_id="",
    note="R1 已注明「诗体、诗评、考证抽样」")

add(book_id="D5", 书名="人间词话", 作者="王国维",
    版本或出版信息="维基文库白文",
    acquired_edition="raw/books/ws_renjian.wikitext（104,205 B）",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="维基文库（CC BY-SA 4.0）",
    acquisition_status="ACQUIRED", parse_status="PARSED",
    reading_status="READ", extraction_status="EXTRACTED",
    reading_scope="已刊 64 则全读；删稿、补遗抽查",
    source_gap="删稿与补遗未全读（read_log 仅 1 行 READ_FULL）",
    local_evidence_path="raw/books/ws_renjian.wikitext；read_log（D5，READ_FULL）；notes/04_*.md",
    db_book_id="",
    note="王国维 1927 卒，公版")

add(book_id="D6", 书名="原诗", 作者="叶燮",
    版本或出版信息="人民文学出版社 1979（原书 1685）",
    acquired_edition="无",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="购买纸本／图书馆借阅",
    acquisition_status="CHANNEL_IDENTIFIED", parse_status="NOT_FOUND",
    reading_status="NOT_FOUND", extraction_status="NOT_FOUND",
    reading_scope="0",
    source_gap="未取得；叶燮诗论无第一手依据",
    local_evidence_path="reports/round-1/01_文献目录与来源调查.md §D6；poetry.db: books(BK-YUANSHI, FOUND)",
    db_book_id="BK-YUANSHI",
    note="R1「FOUND，未取得」")

add(book_id="D7", 书名="历代诗话", 作者="何文焕辑",
    版本或出版信息="中华书局 1981（原书 1770）",
    acquired_edition="无",
    资料类别="古籍原典", 版权状态="PUBLIC_DOMAIN",
    合法获取渠道="购买纸本／图书馆借阅",
    acquisition_status="CHANNEL_IDENTIFIED", parse_status="NOT_FOUND",
    reading_status="NOT_FOUND", extraction_status="NOT_FOUND",
    reading_scope="0",
    source_gap="未取得；诗话汇编缺，无法横向比对",
    local_evidence_path="reports/round-1/01_文献目录与来源调查.md §D7",
    db_book_id="",
    note="R1「FOUND，未取得」")

add(book_id="D8", 书名="词话丛编", 作者="唐圭璋编",
    版本或出版信息="中华书局 1986",
    acquired_edition="无",
    资料类别="现代版权著作", 版权状态="IN_COPYRIGHT",
    合法获取渠道="购买纸本／图书馆借阅",
    acquisition_status="CHANNEL_IDENTIFIED", parse_status="NOT_FOUND",
    reading_status="NOT_FOUND", extraction_status="NOT_FOUND",
    reading_scope="0",
    source_gap="未取得；词话汇编缺",
    local_evidence_path="reports/round-1/01_文献目录与来源调查.md §D8",
    db_book_id="",
    note="唐圭璋 1990 卒，保护期内")

# ---------------- E 研究 5 ----------------
for bid, title, author in [
    ("E1", "中国文学史", "袁行霈主编"),
    ("E2", "唐诗学引论", "陈伯海"),
    ("E3", "唐宋词通论", "吴熊和"),
    ("E4", "杜甫评传", "莫砺锋"),
]:
    add(book_id=bid, 书名=title, 作者=author,
        版本或出版信息="现代学术专著（具体版次见 R1 §4.2）",
        acquired_edition="无",
        资料类别="现代版权著作", 版权状态="IN_COPYRIGHT",
        合法获取渠道="购买纸本（出版社）／图书馆借阅／出版社电子版",
        acquisition_status="CHANNEL_IDENTIFIED", parse_status="NOT_FOUND",
        reading_status="NOT_FOUND", extraction_status="NOT_FOUND",
        reading_scope="0",
        source_gap="未取得；作品有、阐释无",
        local_evidence_path="reports/round-1/01_文献目录与来源调查.md §E；round-1/ROUND-1_完整详细报告.md §4.2",
        db_book_id="",
        note="R1「FOUND，未取得」")

add(book_id="E5", 书名="陶渊明研究", 作者="（R1 未标作者）",
    版本或出版信息="现代学术专著（版次未标）",
    acquired_edition="无（但《陶渊明集》本身已入库 124 首）",
    资料类别="现代版权著作", 版权状态="IN_COPYRIGHT",
    合法获取渠道="购买纸本／图书馆借阅",
    acquisition_status="CHANNEL_IDENTIFIED", parse_status="NOT_FOUND",
    reading_status="NOT_FOUND", extraction_status="NOT_FOUND",
    reading_scope="0",
    source_gap="研究著作未得；R1 称「陶渊明作品本身为 0」已被推翻——works(collection='tao')=124 首",
    local_evidence_path="poetry.db: works(collection='tao', 124)；raw/books/tao（59 文件）；reports/round-1/01 §E5",
    db_book_id="",
    note="R1 的「作品为 0」是过时结论，须在新报告中更正")

# ---------------- F 工具书 6 ----------------
for bid, title, author, cp, note in [
    ("F1", "汉语大词典", "罗竹风主编", "IN_COPYRIGHT", "在线版受访问限制，R1 未绕过"),
    ("F2", "古汉语常用字字典", "王力等", "IN_COPYRIGHT", "商务印书馆版，保护期内"),
    ("F3", "诗词曲语辞汇释", "张相", "PUBLIC_DOMAIN", "张相 1945 卒，正文公版；中华书局排印本另计"),
    ("F4", "中国典故大辞典", "（R1 未标）", "IN_COPYRIGHT", "版次未标"),
    ("F5", "中国历史地名大辞典", "（R1 未标）", "IN_COPYRIGHT", "版次未标"),
    ("F6", "唐诗鉴赏辞典", "（R1 未标）", "IN_COPYRIGHT", "上海辞书版，保护期内"),
]:
    add(book_id=bid, 书名=title, 作者=author,
        版本或出版信息="工具书（版次见 R1 §4.2）",
        acquired_edition="无",
        资料类别="工具书", 版权状态=cp,
        合法获取渠道="购买纸本／图书馆借阅（部分有在线版，受登录/付费限制）",
        acquisition_status="CHANNEL_IDENTIFIED", parse_status="NOT_FOUND",
        reading_status="NOT_FOUND", extraction_status="NOT_FOUND",
        reading_scope="0",
        source_gap="未取得；训释、典故、地名、鉴赏四类支撑全缺",
        local_evidence_path="reports/round-1/01_文献目录与来源调查.md §F",
        db_book_id="",
        note=note)

# ---------------- 写出 ----------------
os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    w.writerows(R)

# ---------------- MISSING_MATERIALS ----------------
MC = ["book_id", "书名", "缺口类型", "具体缺口", "影响", "证据路径"]
M = []


def m(**kw):
    row = {c: "" for c in MC}
    row.update(kw)
    M.append(row)


for r in R:
    if r["acquisition_status"] == "CHANNEL_IDENTIFIED":
        m(book_id=r["book_id"], 书名=r["书名"], 缺口类型="NOT_ACQUIRED",
          具体缺口="全书未取得（仅有书目与渠道）",
          影响=r["source_gap"] or "无法引用原文",
          证据路径=r["local_evidence_path"])

m(book_id="A3", 书名="唐宋词格律", 缺口类型="READING_INCOMPLETE",
  具体缺口="153 调/196 格中仅抽读 16 调；135 格未逐调通读",
  影响="词谱规则不能声称已逐调读过；R2-07 只到结构层",
  证据路径="poetry.db: reading_progress(READ_STRUCTURE)；cipai_forms_r2_07(196)；R2-07 报告")
m(book_id="A7", 书名="声律启蒙", 缺口类型="READING_INCOMPLETE",
  具体缺口="30 韵仅读 3 韵，其余 27 韵 read_log=NOT_READ",
  影响="对仗范本只覆盖 10%，不能作全书已读",
  证据路径="poetry.db: read_log(A7, NOT_READ)")
m(book_id="A4", 书名="钦定词谱", 缺口类型="VERSION_MISMATCH",
  具体缺口="登记中国书店 2010 影印本，实得四库全书本维基转录",
  影响="页码/版式/谱字不能按登记版本引用",
  证据路径="raw/books/cipu；sources WS-REF-CIPU；R2-01 §4.5")
m(book_id="A5", 书名="词律", 缺口类型="VERSION_MISMATCH",
  具体缺口="登记上海古籍 1984 影印本，实得四库本转录",
  影响="不能按登记影印本引用",
  证据路径="raw/books/cilv；sources WS-REF-CILV")
m(book_id="B2", 书名="广韵", 缺口类型="VERSION_MISMATCH",
  具体缺口="登记余迺永校注本，实得四库本转录；仅 9 条影印对校",
  影响="反切可检索但不可称校注本；多音字判定仍需谨慎",
  证据路径="raw/books/guangyun；guangyun_fanqie_validation_r2_11；R2-12 §3")
m(book_id="B2", 书名="广韵", 缺口类型="SOURCE_GAP",
  具体缺口="3,730 小韵仅 9 条与影印本对校；小韵首为结构重认",
  影响="反切字头归属有残余错风险",
  证据路径="R2-12 COMPLETE_REPORT §3.2")
m(book_id="B3", 书名="集韵", 缺口类型="PARSE_UNUSABLE",
  具体缺口="raw/books/jiliyun 为 2026-11-12 首采失败版（10 卷仅 40 KB，只有韵例）",
  影响="若误用该目录会以为集韵已全量；实际须用 raw/r2_08/jiyun_pages",
  证据路径="raw/books/jiliyun；R2-01 §4.5；R2-12 §3.3")
m(book_id="B3", 书名="集韵", 缺口类型="SOURCE_GAP",
  具体缺口="33,664 字组/42,352 字级索引中 227 条 POSITION_ONLY；4 韵未定位小韵；未对图",
  影响="非全部条目可定位到原书叶码",
  证据路径="jiyun_entry_r2_12；jiyun_char_index_r2_12；R2-12 §3.3")
m(book_id="B4", 书名="平水韵", 缺口类型="PROVENANCE_GAP",
  具体缺口="来源为维基文库转录，非韵书原书；字表为后世通行本；未与印本对勘",
  影响="可作分类表，不可作版本依据；R1 的 10,648 条目数字未复算",
  证据路径="rhyme_source_books_r2_11(PINGSHUI_YUN)；raw/r2_09/rhyme/平水韻.json")
m(book_id="B5", 书名="词林正韵", 缺口类型="SOURCE_GAP",
  具体缺口="5,563 条按部-声调-韵目组织，非小韵；未与影印本对校",
  影响="不能反推原书小韵与页码",
  证据路径="ph_cilin_r2_09；rhyme_source_books_r2_11")
m(book_id="B6", 书名="中原音韵", 缺口类型="SOURCE_GAP",
  具体缺口="5,731 条维基转录，未对校；入声派三声未逐条核",
  影响="曲韵判定可用性受限",
  证据路径="ph_zhongyuan_r2_09；rhyme_source_books_r2_11")
m(book_id="B7", 书名="中华通韵", 缺口类型="SUBSTITUTE_RISK",
  具体缺口="库内只有 2005《中华新韵》十四韵，不是 2019《中华通韵》十六韵",
  影响="若把 zhonghua_xinyun_* 当通韵引用，韵部与韵字都会错",
  证据路径="rhyme_source_books_r2_11(ZHONGHUA_XINYUN)；zhonghua_xinyun_characters_r2_11")
m(book_id="C7", 书名="花间集", 缺口类型="SOURCE_GAP",
  具体缺口="498 首 vs 通行 500 首，差 2 首未说明",
  影响="词集总量不闭合",
  证据路径="works(collection='huajianji', 498)")
m(book_id="C9", 书名="元曲", 缺口类型="DATA_QUALITY",
  具体缺口="1,729 条标题/正文错位；24 条源截断；未修",
  影响="曲文与标题可能错配，不能直接引用",
  证据路径="R2-13 §8；R2-14 §5；yuanqu_text_audit_r2_13")
m(book_id="C12", 书名="古诗十九首", 缺口类型="PARTIAL_TEXT",
  具体缺口="按题名仅 7/19 首可检出；其余题名异写或未立目",
  影响="不能声称十九首齐全",
  证据路径="works 题名检索；raw/books/wenxuan、gushiji")
m(book_id="C13", 书名="昭明文选", 缺口类型="PARTIAL_TEXT",
  具体缺口="60 卷仅得 13 卷（19–31 诗类）",
  影响="赋、书、序、论等文体全缺，文选覆盖不足 1/4",
  证据路径="raw/books/wenxuan；sources WS-WENXUAN 13 条；works 357")
m(book_id="C15", 书名="明诗综／清诗汇／元诗选", 缺口类型="PARTIAL_TEXT",
  具体缺口="元诗选未得；明诗综、清诗汇虽全卷但未对校",
  影响="元代诗仍无专门选本支撑",
  证据路径="raw/books/mingshi、wanqing；works mingshi/wanqing")
m(book_id="EXTRA-词学十讲", 书名="词学十讲（52 条之外）", 缺口类型="SOURCE_GAP",
  具体缺口="第 6 讲《论对偶》EPUB 丢失后半例词，仅存出处行（5,331 字中后半例证缺失）",
  影响="该讲判 READ_WITH_SOURCE_GAP，不作完整引用；其余 9 讲 READ",
  证据路径="poetry.db: reading_records_r2_06(E:第6讲, source_gap)；raw/r2_06_notes/E_词学十讲十讲复核.md")
m(book_id="A1", 书名="诗词格律", 缺口类型="OCR_SOURCE_GAP",
  具体缺口="9/31 单元带 OCR 例外：谱行丢字、50+44+35 页词谱谱行不可用、去声一至十六韵整段缺失",
  影响="31/31 READ 成立，但「读全」不等于「文本完整」；谱表不可作数据源",
  证据路径="reading_records_r2_05.ocr_exception（9 行）；R2-05 §3.1/3.2")
m(book_id="C5", 书名="全宋词", 缺口类型="COUNT_DIFF",
  具体缺口="R1 19,595 首 vs 库内 18,794（−801）",
  影响="词总数口径不一致，引用前须说明",
  证据路径="works(collection='songci')；R1 §4.2")
m(book_id="C3", 书名="全唐诗", 缺口类型="COUNT_DIFF",
  具体缺口="R1 55,630 / 55,308 两说 vs 库内 55,308",
  影响="唐诗总数口径不一致",
  证据路径="works(collection='tang')")
m(book_id="C6", 书名="全宋诗", 缺口类型="COUNT_DIFF",
  具体缺口="R1 4 片 3,975 首 → 现 255 片 252,884 首（已补，但版本未对校）",
  影响="覆盖已大幅改善；仍不可称「校勘本」",
  证据路径="works(collection='songshi')；R2-01 §4.4")

with open(MISS_PATH, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=MC)
    w.writeheader()
    w.writerows(M)

# ---------------- 统计 ----------------
from collections import Counter
print("rows:", len(R))
for col in ["acquisition_status", "parse_status", "reading_status", "extraction_status"]:
    print(col, dict(Counter(r[col] for r in R)))
print("missing rows:", len(M))
