#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_manifest.py —— 生成 sources/manifest.json（来源清单）

清单是采集的唯一定义：采什么、从哪采、什么许可、可靠性如何。
不在此清单中的文件不得进入 raw/。

运行：python3 tools/build_manifest.py
"""

from __future__ import annotations

import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "sources", "manifest.json")

CP = "https://cdn.jsdelivr.net/gh/chinese-poetry/chinese-poetry@master/"
CP_RAW = "https://raw.githubusercontent.com/chinese-poetry/chinese-poetry/master/"
WS = "https://zh.wikisource.org/w/index.php"

REPO_LICENSE = "MIT（整理与标注）；所收原文为公有领域古籍"
REPO_RELIABILITY = "二手整理：来源网站已不可追溯，未与任何印本对勘，无校勘记录。仅可作语料，不可作权威底本。"


def poetry(sid, name, era, collection, rel_path, note="", parser="chinese_poetry", category="诗集"):
    return {
        "source_id": sid,
        "name": name,
        "category": category,
        "era": era,
        "collection": collection,
        "url": CP + rel_path,
        "url_fallback": CP_RAW + rel_path,
        "local": "raw/poetry/%s/%s" % (collection, os.path.basename(rel_path)),
        "license": REPO_LICENSE,
        "copyright": "原文公有领域；整理数据 MIT",
        "format": "json",
        "parser": parser,
        "reliability": REPO_RELIABILITY,
        "maintainer": "chinese-poetry（GitHub 开源项目，作者 JackeyGao）",
        "note": note,
    }


def ws(sid, name, page, category, era, note=""):
    return {
        "source_id": sid,
        "name": name,
        "category": category,
        "era": era,
        "collection": "gudian",
        "url": WS + "?title=%s&action=raw" % page,
        "url_fallback": None,
        "local": "raw/books/%s.wikitext" % sid.lower().replace("-", "_"),
        "license": "CC BY-SA 4.0（维基文库志愿者转录）；原文公有领域",
        "copyright": "原文公有领域；转录文本 CC BY-SA 4.0",
        "format": "wikitext",
        "parser": "wikisource",
        "reliability": "公有领域原典的志愿者转录；未与印本对勘；个别字或有转录讹误，需以印本复核",
        "maintainer": "维基文库（Wikimedia Foundation）",
        "note": note,
    }


ENTRIES = []

# ---------------- A. 诗词总集 / 选集（chinese-poetry，MIT）
ENTRIES.append(poetry("CP-SHIJING", "诗经", "先秦", "shijing", "诗经/shijing.json",
                      "305 篇，含风雅颂。四言诗的主要源头。"))
ENTRIES.append(poetry("CP-CHUCI", "楚辞", "先秦", "chuci", "楚辞/chuci.json",
                      "屈原及宋玉等，骚体。"))
ENTRIES.append(poetry("CP-CAOCAO", "曹操诗集", "汉魏", "caocao", "曹操诗集/caocao.json",
                      "建安四言/五言的少数可核样本。"))
ENTRIES.append(poetry("CP-TANG300", "唐诗三百首", "唐", "tang300", "蒙学/tangshisanbaishou.json",
                      "蘅塘退士选本，家弦户诵，可与全唐诗对照。"))

# 全唐诗：全量 58 片（每片 1000 首）
# 初版曾均匀抽 12 片，导致杜甫、李白等名家缺席（作者按卷序集中于特定分片），
# 故改为全量取入，避免抽样偏差。
for i in range(58):
    n = i * 1000
    ENTRIES.append(poetry("CP-TANG-%02d" % (i + 1), "全唐诗（第 %d 片）" % (i + 1), "唐", "tang",
                          "全唐诗/poet.tang.%d.json" % n,
                          "全唐诗共 58 片，本片为第 %d–%d 首。" % (n + 1, n + 1000)))

# 宋诗：255 片全量
# ROUND 2-01 更正：上一轮只取 4 片（3,975 首），审计指出「4/255」是首要缺口。
# 上游实测：poet.song.0.json … poet.song.254000.json，共 255 片，合计 109.1 MB。
# 分片号即该片首诗的全局序号（每片 1000 首）。
for i in range(255):
    n = i * 1000
    ENTRIES.append(poetry("CP-SONGSHI-%03d" % (i + 1), "全宋诗（第 %d 片）" % (i + 1), "宋", "songshi",
                          "全唐诗/poet.song.%d.json" % n,
                          "全宋诗共 255 片，本片为第 %d–%d 首。" % (n + 1, n + 1000)))

# 宋词：全量 21 片（原抽样 8 片，苏轼、辛弃疾等词家缺席，改为全量）
for i in range(22):
    n = i * 1000
    ENTRIES.append(poetry("CP-SONGCI-%02d" % (i + 1), "全宋词（第 %d 片）" % (i + 1), "宋", "songci",
                          "宋词/ci.song.%d.json" % n,
                          "宋词分片，含词牌（rhythmic）字段。", category="词集"))

ENTRIES.append(poetry("CP-YUANQU", "元曲", "元", "yuanqu", "元曲/yuanqu.json",
                      "散曲小令，非诗词正体，作对照语料。", category="曲集"))
for i in range(1, 11):
    tag = "x" if i == 10 else str(i)   # 原目录第十卷名为 huajianji-x-juan.json
    ENTRIES.append(poetry("CP-HUAJIAN-%02d" % i, "花间集 卷%d" % i, "五代", "huajianji",
                          "五代诗词/huajianji/huajianji-%s-juan.json" % tag,
                          "赵崇祚编，文人词第一部总集。", category="词集"))
ENTRIES.append(poetry("CP-HUAJIAN-PRE", "花间集 序", "五代", "huajianji",
                      "五代诗词/huajianji/huajianji-0-preface.json", "欧阳炯序，词学批评重要文献。"))
ENTRIES.append(poetry("CP-NANTANG", "南唐二主词", "五代", "nantang",
                      "五代诗词/nantang/poetrys.json", "李璟、李煜。", category="词集"))
ENTRIES.append(poetry("CP-NALAN", "纳兰性德诗集", "清", "nalan", "纳兰性德/纳兰性德诗集.json",
                      "清代词人别集，清诗/清词的代表性样本。", category="别集"))
ENTRIES.append(poetry("CP-SHENGLV", "声律启蒙", "清", "shenglv", "蒙学/shenglvqimeng.json",
                      "车万育撰，对仗与声律的蒙学范本，可直接提取对偶规则。", category="蒙学"))

# ---------------- B. 公版理论文献（维基文库）
ENTRIES.append(ws("WS-WENJING", "文镜秘府论", "文鏡秘府論", "格律", "唐",
                  "遍照金刚（空海）撰。唐代声律理论的现存最重要汇编，含「调声」「诗章中用声法式」等。"))
ENTRIES.append(ws("WS-SHENGLVQI", "声律启蒙（维基文库本）", "聲律啟蒙", "蒙学", "清",
                  "与 chinese-poetry 本互为版本对照。"))
ENTRIES.append(ws("WS-SHIPIN", "诗品", "詩品", "诗话", "南朝梁", "钟嵘撰，三品论诗。"))
ENTRIES.append(ws("WS-24SHIPIN", "二十四诗品", "二十四詩品", "诗话", "唐", "司空图撰，以品目论风格。"))
ENTRIES.append(ws("WS-CANGLANG", "沧浪诗话", "滄浪詩話", "诗话", "宋", "严羽撰，「兴趣」「妙悟」说。"))
ENTRIES.append(ws("WS-RENJIAN", "人间词话", "人間詞話", "词话", "清", "王国维撰，「境界」说。"))
for ch in ["神思", "體性", "風骨", "通變", "情采", "聲律", "麗辭", "比興", "物色", "知音"]:
    ENTRIES.append(ws("WS-WXD-%s" % ch, "文心雕龙·%s" % ch, "文心雕龍/" + ch, "文论", "南朝梁",
                      "刘勰撰。选读与诗学、声律、对偶直接相关的十篇。"))

# ---------------- B2. 补充页（目录页的子页、重定向目标）
SUP = [
    ("SUP-SHIPIN-1", "诗品·卷上", "詩品/卷上"),
    ("SUP-SHIPIN-2", "诗品·卷中", "詩品/卷中"),
    ("SUP-SHIPIN-3", "诗品·卷下", "詩品/卷下"),
    ("SUP-CANGLANG-1", "沧浪诗话·卷一诗辨", "滄浪詩話/卷1"),
    ("SUP-CANGLANG-2", "沧浪诗话·卷二诗体", "滄浪詩話/卷2"),
    ("SUP-CANGLANG-3", "沧浪诗话·卷三诗法", "滄浪詩話/卷3"),
    ("SUP-CANGLANG-4", "沧浪诗话·卷四诗评", "滄浪詩話/卷4"),
    ("SUP-CANGLANG-5", "沧浪诗话·卷五考证", "滄浪詩話/卷5"),
    ("SUP-SHENGLV", "声律启蒙（重定向目标页）", "聲律啓蒙"),
]
for sid, name, page in SUP:
    ENTRIES.append(ws(sid, name, page, "诗话" if "诗品" in name or "沧浪" in name else "蒙学", "历代",
                      "目录页的子页；母页仅存目录，正文在此。"))

# ---------------- B4. 维基文库四部总集（ROUND 2-01） ----------------
# 为什么是这四部：
#   《古詩紀》156 卷覆盖先秦至隋（补魏晋南北朝、隋两代空白）；
#   《明詩綜》100 卷补明代；《晚晴簃詩匯》200 卷补清代；《中州集》补金代。
#   四部均为公有领域总集，维基文库有全文转录（四庫全書本 / 新式标点本）。
# local 指向由 ws_to_json.py 生成的中间 JSON（parse.py 读它），
# origin_local 指向原始 wikitext —— 溯源要看后者，不能看中间产物。
WS_SERIES = {
    "gushiji":   ("古詩紀",     "先秦至隋", "明·馮惟訥編，四庫全書本；卷内「漢第七／梁第二十七」等段名标朝代"),
    "mingshi":   ("明詩綜",     "明",       "清·朱彝尊編，四庫全書本"),
    "wanqing":   ("晚晴簃詩匯", "清",       "徐世昌編；已加新式标点，正文按篇分 <poem>"),
    "zhongzhou": ("中州集",     "金",       "金·元好問編，四庫全書本"),
}
_pages_file = os.path.join(BASE, "sources", "ws_pages.json")
if os.path.exists(_pages_file):
    _pages = json.load(open(_pages_file, encoding="utf-8"))
    for _p in _pages:
        _s = _p["series"]
        if _s not in WS_SERIES:
            continue
        _book, _era, _note = WS_SERIES[_s]
        _vol = _p["vol"]
        ENTRIES.append({
            "source_id": "WS-%s-%s" % (_s.upper(), _vol.replace("卷", "")),
            "name": "%s·%s" % (_book, _vol),
            "category": "总集",
            "era": _era,
            "collection": _s,
            "url": WS + "?title=%s&action=raw" % _p["title"].replace(" ", "_"),
            "url_fallback": None,
            "local": "raw/poetry/%s/%s.json" % (_s, _vol),
            "origin_local": "raw/books/%s/%s.wikitext" % (_s, _vol),
            "license": "CC BY-SA 4.0（维基文库志愿者转录）；原文公有领域",
            "copyright": "原文公有领域；转录与录入 CC BY-SA 4.0",
            "format": "json",
            "parser": "ws_series",
            "reliability": "转录本：四庫全書本逐卷录入，未与影印本逐字对勘；"
                           "四庫本无标点，正文分行依赖转录者。可作语料，不可作校定本。",
            "maintainer": "维基文库社区（zh.wikisource.org）",
            "note": _note,
        })

# ---------------- B4a. 陶淵明集 詩四卷（ROUND 2-02） ----------------
# 古詩紀缺陶詩（全库检索「採菊東籬」为 0），文選仅选 7 首。
# 维基文库《陶淵明集》按篇分页，卷一至卷四为诗，逐篇取全文可得 125 首。
for _v, _cn in enumerate(["一", "二", "三", "四"], 1):
    ENTRIES.append({
        "source_id": "WS-TAO-%d" % _v,
        "name": "陶淵明集·卷%s（詩）" % _cn,
        "category": "别集",
        "era": "晋",
        "collection": "tao",
        "url": WS + "?title=%s&action=raw" % ("陶淵明集/卷" + _cn).replace(" ", "_"),
        "url_fallback": None,
        "local": "raw/poetry/tao/卷%s.json" % _cn,
        "origin_local": "raw/books/tao/",
        "license": "CC BY-SA 4.0（维基文库志愿者转录）；原文公有领域",
        "copyright": "陶潜诗文，公有领域；转录 CC BY-SA 4.0",
        "format": "json",
        "parser": "tao",
        "reliability": "转录本：据通行八卷本，卷内按篇分页；底本自带 {{另|A|B}} 异文标记，已原样保留。",
        "maintainer": "维基文库社区（zh.wikisource.org）",
        "note": "陶集卷一至卷四为诗；卷五以下为赋、记、传、祭文，不在本库范围。",
    })

# ---------------- B4b. 昭明文選 詩類（ROUND 2-02） ----------------
# 为什么补：古詩紀（四庫全書本）在維基文庫的转录并不完整 —— 晉卷每卷仅 15 KB，
# 陶潛、謝靈運、曹植等大家詩多缺席（全库检索「採菊東籬」「池塘生春草」皆为 0）。
# 《昭明文選》卷19–31 为詩類，收先秦至齊梁詩，可补这批作者，且带李善注。
for _i in range(19, 32):
    ENTRIES.append({
        "source_id": "WS-WENXUAN-%02d" % _i,
        "name": "昭明文選·卷%d（詩類）" % _i,
        "category": "总集",
        "era": "先秦至梁",
        "collection": "wenxuan",
        "url": WS + "?title=%s&action=raw" % ("昭明文選/卷%d" % _i).replace(" ", "_"),
        "url_fallback": None,
        "local": "raw/poetry/wenxuan/卷%02d.json" % _i,
        "origin_local": "raw/books/wenxuan/卷%02d.wikitext" % _i,
        "license": "CC BY-SA 4.0（维基文库志愿者转录）；原文公有领域",
        "copyright": "萧统编、李善注，均公有领域；转录 CC BY-SA 4.0",
        "format": "json",
        "parser": "wenxuan",
        "reliability": "转录本：依胡刻本文选录入，含李善注；注文已在转换时剥离，未与影印本对勘。",
        "maintainer": "维基文库社区（zh.wikisource.org）",
        "note": "诗歌选本，非全集；用于补六朝大家，不作校定本。",
    })

# ---------------- B5. 韵书与词谱（公版原典） ----------------
# 只登记维基文库有全文者；《集韻》正文在 DjVu 页，需 --render 取渲染文本。
REF_SERIES = {
    "guangyun": ("廣韻",   "宋·陳彭年等", "韻書", "5 卷"),
    "jiliyun":  ("集韻",   "宋·丁度等",   "韻書", "10 卷（正文分見各部）"),
    "cilv":     ("詞律",   "清·萬樹",     "詞譜", "20 卷"),
    "cipu":     ("御定詞譜", "清·王奕清等", "詞譜", "40 卷（即《欽定詞譜》）"),
}
if os.path.exists(_pages_file):
    for _p in _pages:
        _s = _p["series"]
        if _s not in REF_SERIES:
            continue
        _book, _author, _cat, _scope = REF_SERIES[_s]
        _vol = _p["vol"]
        # 过滤：目録页不是正文；《集韻》只取 10 个卷页（正文由 transclude 展开），
        # 不取 216 个「卷01/東第一」式部次子页 —— 否则重复计 10 倍。
        if "目録" in _vol or "目錄" in _vol:
            continue
        if _s == "jiliyun" and not re.fullmatch(r"卷\d+", _vol):
            continue
        ENTRIES.append({
            "source_id": "WS-REF-%s-%s" % (_s.upper(), _vol.replace("卷", "")),
            "name": "%s·%s" % (_book, _vol),
            "category": _cat,
            "era": "历代",
            "collection": "reference",
            "url": WS + "?title=%s&action=raw" % _p["title"].replace(" ", "_"),
            "url_fallback": None,
            "local": "raw/books/%s/%s.wikitext" % (_s, _vol),
            "license": "CC BY-SA 4.0（维基文库志愿者转录）；原文公有领域",
            "copyright": "原文公有领域；转录与录入 CC BY-SA 4.0",
            "format": "wikitext",
            "parser": "raw_text",
            "reliability": "转录本：%s，%s。未与影印本对勘；%s" % (_author, _scope, _book),
            "maintainer": "维基文库社区（zh.wikisource.org）",
            "note": "韵书／词谱原典，供后续规则核对；本阶段不据此改写任何格律规则。",
        })

# ---------------- C. 现代版权专著（仅登记，不采集全文）
MODERN = [
    ("BK-WANGLI-GELV", "诗词格律", "王力", "中华书局", "1977（初版 1962）",
     "现代版权。未获取全文；仅登记书目与公开目录。", "格律"),
    ("BK-WANGLI-SHILV", "汉语诗律学", "王力", "上海教育出版社", "2005（初版 1958）",
     "现代版权。未获取全文。诗律学最系统的现代著作，为后续重点采购对象。", "格律"),
    ("BK-LONG-TANGSONG", "唐宋词格律", "龙榆生", "上海古籍出版社", "1978（初版 1962）",
     "现代版权。未获取全文。词谱与词律的核心现代参考。", "格律"),
    ("BK-QDCP", "钦定词谱", "王奕清等奉敕编", "中国书店（影印）", "2010（原书 1715）",
     "原书公有领域；所用影印本未获取。引擎现有浣溪沙/相见欢谱即据此。", "格律"),
    ("BK-CILV", "词律", "万树", "上海古籍出版社（影印）", "1984（原书 1687）",
     "原书公有领域；影印本未获取。", "格律"),
    ("BK-QIYUN", "切韵", "陆法言", "中华书局（周祖谟校笺本）", "2004（原书 601）",
     "原书公有领域；校笺本有版权，未获取。", "韵书"),
    ("BK-GUANGYUN", "广韵", "陈彭年等", "中华书局（余迺永校注本）", "2011（原书 1008）",
     "原书公有领域；校注本有版权，未获取。", "韵书"),
    ("BK-JIYUN", "集韵", "丁度等", "上海古籍出版社（影印）", "1985（原书 1039）",
     "原书公有领域；影印本未获取。", "韵书"),
    ("BK-CILIN", "词林正韵", "戈载", "上海古籍出版社（影印）", "1981（原书 1821）",
     "原书公有领域；影印本未获取。引擎十九部表据通行韵目对应，非原书字表。", "韵书"),
    ("BK-ZHONGYUAN", "中原音韵", "周德清", "中华书局", "1978（原书 1324）",
     "原书公有领域；整理本有版权，未获取。", "韵书"),
    ("BK-WENXIN", "文心雕龙", "刘勰", "人民文学出版社（范文澜注）", "1958（原书 6 世纪）",
     "原书公有领域；注本有版权。已取维基文库白文，未取注本。", "文论"),
    ("BK-YUANSHI", "原诗", "叶燮", "人民文学出版社", "1979（原书 1685）",
     "原书公有领域；整理本有版权，未获取。", "诗话"),
    ("BK-TANGSONG-SHI", "唐宋诗举要", "高步瀛", "上海古籍出版社", "1978（初版 1934）",
     "现代版权（1934 年后）。未获取。", "选集"),
]
BOOKS = []
for bid, title, author, pub, ed, note, cat in MODERN:
    BOOKS.append({
        "book_id": bid, "title": title, "author": author, "publisher": pub, "edition": ed,
        "category": cat, "license": "现代版权，未取得授权，未采集全文",
        "copyright": "受版权保护", "status": "FOUND", "note": note,
    })

manifest = {
    "生成脚本": "tools/build_manifest.py",
    "说明": "本清单定义本轮全部采集范围。清单外文件不得进入 raw/。",
    "采集原则": [
        "只采公有领域古籍与明确许可的开放数据集。",
        "不绕过付费墙、登录与反爬限制；不采受版权保护的现代专著全文。",
        "每个来源逐条记录许可、可靠性、维护者；可靠性不得笼统写「权威」。",
        "chinese-poetry 为二手整理，仅作语料规模，不作权威底本。",
    ],
    "poetry_sources": ENTRIES,
    "modern_books": BOOKS,
    "统计": {
        "诗词采集源数": len(ENTRIES),
        "现代版权专著（仅登记）": len(BOOKS),
    },
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1)
print(f"来源清单已生成：{OUT}")
print(f"  采集源 {len(ENTRIES)} 个；仅登记不采集的现代专著 {len(BOOKS)} 种")
