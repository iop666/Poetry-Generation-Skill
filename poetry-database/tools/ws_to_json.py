#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ws_to_json.py —— 把维基文库分卷 wikitext 转成与 chinese-poetry 同形的 JSON

为什么要转成同形：
  `tools/parse.py` 已经有一套稳定入库逻辑（唯一化、去重、异文分组、繁简索引）。
  新语料若另写一套入库，会产生两套口径，正是审计批评的「统计不可复算」。
  因此这里只做「版式 → 中间 JSON」，入库仍走 parse.py。

支持两种版式：

A. skqs_anchor（四庫全書本，古詩紀 / 明詩綜 / 中州集）
   {{SKQS header|...}}<onlyinclude><poem>
   　　欽定四庫全書
   　　{{SK anchor|梁第二十七}}          ← 朝代段（仅古詩紀有）
   　　劉峻{{SK notes|字孝標……}}        ← 作者（notes 含「字/人/進士」）
   　　{{SK anchor|登郁洲山望海}}        ← 篇题
   　　滄潦聮霄岫……                     ← 正文
   </poem>

B. heading_poem（晚晴簃詩匯）
   ==清世祖福臨==                        ← 作者
   ===[[聖母皇太后萬壽詩]]===            ← 篇题
   <poem>香花淑節壽陽宮，…</poem>       ← 正文（已带标点）

输出：raw/poetry/<coll>/<vol>.json
  [{"title":…, "author":…, "paragraphs":[…], "chapter":…, "section":…, "volume":…}]

已知边界（写进报告，不掩饰）：
  - 四庫本无标点，正文只能整段切分，句读依赖 chinese-poetry 之外的人工判断；
  - 作者判定是启发式，会把个别小传误判为作者；
  - 组诗（「三首」「二首」）不拆，仍作一条，与 chinese-poetry 的处理一致。
"""

from __future__ import annotations

import argparse
import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# series → (collection, 篇目所用朝代默认值, 版式)
SERIES_MAP = {
    "gushiji":   ("gushiji",  "",     "skqs_anchor"),
    "mingshi":   ("mingshi",  "明",   "skqs_anchor"),
    "zhongzhou": ("zhongzhou", "金",  "skqs_anchor"),
    "wanqing":   ("wanqing",  "清",   "heading_poem"),
}

# 古詩紀 朝代段 → 本库朝代口径
DYNASTY_MAP = [
    (r"^古逸|^前集", "先秦"),
    (r"^漢", "汉魏"), (r"^魏(?!晉)", "汉魏"),
    (r"^晉|^晋", "魏晋南北朝"),
    # 注意：不可把「隋第」并进南北朝规则 —— 否则隋代整代被吞进魏晋南北朝，
    # 覆盖率会永远显示「隋代 0」。规则按顺序首个命中即 break。
    (r"^宋第|^齊第|^梁第|^陳第|^後魏|^北魏|^北齊|^北周", "魏晋南北朝"),
    (r"^隋", "隋"),
]
SECTION_RE = re.compile(r"^(古逸|前集|漢|魏|晉|晋|宋|齊|梁|陳|後魏|北魏|北齊|北周|隋)第[一二三四五六七八九十百]+$")

SK_ANCHOR = re.compile(r"\{\{SK anchor\|([^}|]+)")
SK_NOTES = re.compile(r"\{\{SK notes\|([^}]*)\}\}")
# 小传特征：四庫本的人物小传一般以「字 X」开头，或含「進士」「…人」。
# 早期版本用单字「人/生/官」做关键词，把《彈歌》「斷竹續竹飛土逐宍」误判成作者，
# 故收紧为：必须有「字／號／謚」＋人名式短名，或含「進士」「處士」。
# ① 小传特征；② 仅标篇数的作者（《明詩綜》「太祖高皇帝（三首）」）
BIO_RE = re.compile(r"(字[\u4e00-\u9fff]{1,3}[，。]?|號[\u4e00-\u9fff]{1,3}|謚[\u4e00-\u9fff]|進士|處士|布衣|官至|^[一二三四五六七八九十百]+首$)")
# 裸作者行：《古詩紀》魏卷「陳思王植」这类无锚点、无小传的短名
BARE_NAME = re.compile(r"^[\u4e00-\u9fff]{2,6}$")
NAME_MAX = 5



# 四庫本的行首短串里混着版头、部类名、篇数与体裁词，早期版本把它们当成了作者：
#   「钦定四库全书」485 条、「郊庙歌辞」304 条、「简文帝三」113 条、「庾肩吾乐府」98 条。
# 这些不是作者，必须过滤（否则作者统计直接失真，也让「陶渊明为 0」这类结论跑偏）。
AUTHOR_STOP = ("钦定四库全书", "欽定四庫全書", "郊庙歌辞", "郊廟歌辭", "乐府古辞",
               "樂府古辭", "乐府", "樂府", "乐章", "樂章", "古诗", "古詩", "歌辞", "歌辭")


def norm_author(a: str) -> str:
    a = (a or "").strip()
    if not a or a in AUTHOR_STOP:
        return ""
    if re.search(r"(歌辞|歌辭|乐章|樂章|四库全书|四庫全書|古辞|古辭)$", a):
        return ""
    a = re.sub(r"(乐府|樂府)$", "", a)
    b = re.sub(r"[一二三四五六七八九十]+$", "", a)
    if len(b) >= 2 and len(a) - len(b) <= 2:
        a = b
    return a


def clean(s: str) -> str:
    """去掉行内模板，保留可见文字。"""
    s = re.sub(r"\{\{SK notes\|[^}]*\}\}", "", s)
    s = re.sub(r"\{\{SKchar\|(\d+)\}\}", "", s)
    s = re.sub(r"\{\{YL\|([^}|]*)[^}]*\}\}", r"\1", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", s)
    s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"<[^>]+>", "", s)
    return s.replace("\u3000", "").strip()


def is_body(line: str) -> bool:
    """正文行判定：去标记后仍有 ≥5 个汉字，且不以「欽定四庫全書」等版头开头。"""
    t = clean(line)
    if not t or t.startswith("欽定四庫全書") or t.startswith("古詩紀巻") or t.startswith("明詩綜巻"):
        return False
    hz = len(re.findall(r"[\u4e00-\u9fff]", t))
    return hz >= 5


def parse_skqs(text: str, default_dynasty: str) -> list:
    """四庫本：按 SK anchor 状态机切分。"""
    body = text
    m = re.search(r"<onlyinclude>(.*?)</onlyinclude>", text, re.S)
    if m:
        body = m.group(1)
    body = body.replace("<poem>", "").replace("</poem>", "")

    out, cur = [], None
    dynasty = default_dynasty
    section = ""
    author = ""
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        anchors = SK_ANCHOR.findall(line)
        if anchors:
            for a in anchors:
                a = a.strip()
                if SECTION_RE.match(a):
                    section = a
                    for pat, dy in DYNASTY_MAP:
                        if re.match(pat, a):
                            dynasty = dy
                            break
                    author = ""
                    continue
                if "巻" in a or "卷" in a or "四庫全書" in a:
                    continue
                notes = " ".join(SK_NOTES.findall(line))
                if notes and BIO_RE.search(notes) and len(a) <= NAME_MAX:
                    author = norm_author(a)
                    cur = None
                    continue
                # 篇题
                cur = {"title": a, "author": author, "paragraphs": [],
                       "chapter": section, "section": "", "dynasty": dynasty}
                out.append(cur)
            continue
        # 纯作者行（如「劉峻{{SK notes|字孝標…}}」）
        if SK_NOTES.search(line) and not is_body(line):
            cand = clean(line)
            notes = " ".join(SK_NOTES.findall(line))
            if BIO_RE.search(notes) and 1 <= len(cand) <= NAME_MAX:
                author = norm_author(cand)
                cur = None
            continue
        # 短行分两种，必须区分，否则会把小題当作者：
        #   ① 无待完成篇目 → 作者（《古詩紀》魏卷「陳思王植」）
        #   ② 有篇目但尚无正文 → 小題，替换通用篇题（「詩」→「上責躬詩」）
        cand = clean(line)
        if BARE_NAME.match(cand) and not re.search(r"[，。！？；：、,.!?;:]", cand):
            if cur is None:
                cand = norm_author(cand)
                if cand:
                    author = cand
                continue
            if not cur["paragraphs"]:
                cur["title"] = cand
                continue
        if cur is not None and is_body(line):
            cur["paragraphs"].append(clean(line))
    # 少数卷（如《古詩紀》外集／別集）没有朝代段标记，不能凭卷号猜朝代，
    # 一律标「未定」，由报告单列，不混入任何一朝。
    for p in out:
        if not p["dynasty"]:
            p["dynasty"] = "未定"
    return [p for p in out if p["paragraphs"] and p["title"]]


def parse_heading_poem(text: str, default_dynasty: str) -> list:
    """晚晴簃詩匯：==作者== / ===篇题=== / <poem> 正文。"""
    out = []
    author = ""
    title = None
    buf = []
    in_poem = False

    def flush():
        nonlocal buf, title
        if title and buf:
            out.append({"title": title, "author": author,
                        "paragraphs": [p for p in buf if p.strip()],
                        "chapter": "", "section": "", "dynasty": default_dynasty})
        buf = []

    for raw in text.splitlines():
        line = raw.rstrip()
        mh2 = re.match(r"^==\s*([^=].*?)\s*==\s*$", line)
        mh3 = re.match(r"^===\s*(.*?)\s*===\s*$", line)
        if mh2 and not mh3:
            flush(); title = None
            author = clean(mh2.group(1))
            continue
        if mh3:
            flush()
            title = clean(mh3.group(1)) or None
            continue
        if "<poem>" in line:
            in_poem = True
            line = line.split("<poem>", 1)[1]
        if "</poem>" in line:
            part = line.split("</poem>", 1)[0]
            if part.strip():
                buf.append(part.strip())
            in_poem = False
            continue
        if in_poem and line.strip():
            buf.append(line.strip())
    flush()
    return [p for p in out if p["paragraphs"] and p["title"]]



def parse_plain_anthology(text: str, default_dynasty: str) -> list:
    """纯缩进版式（《晚晴簃詩匯》多数卷次）：

    　　韩崶                                        ← 作者（短名，无标点）
    　　韩崶，字桂舲，元和人。乾隆丁酉拔贡，官至刑部尚书……  ← 小传（跳过）
    　　赣州夜泊次香杜韵                            ← 篇题（短，无标点）
    　　到此双流合，遥看百雉开。……                  ← 正文（含标点）

    判定靠三件事：短名 + 下一行是小传 → 作者；短行无标点 → 篇题；含标点且非小传 → 正文。
    """
    BODY_PUNCT = re.compile(r"[，。！？；：、]")
    BIO = re.compile(r"(，字|，号|，號|官至|有《|，[\u4e00-\u9fff]{2,4}人[。，])")

    lines = []
    for raw in text.splitlines():
        t = raw.strip().strip("\u3000").strip()
        if not t or t.startswith("{{") or t.startswith("|") or t.startswith("__"):
            continue
        if t.startswith("[[Category:") or t.startswith("卷"):
            continue
        lines.append(t)

    out, author, title, buf = [], "", None, []
    i = 0
    while i < len(lines):
        t = lines[i]
        has_punct = bool(BODY_PUNCT.search(t))
        is_short = len(t) <= 20 and not has_punct
        if is_short:
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if len(t) <= 6 and BIO.search(nxt) and not BIO.search(t):
                # 作者 + 紧随小传
                if title and buf:
                    out.append({"title": title, "author": author,
                                "paragraphs": [x for x in buf if x],
                                "chapter": "", "section": "", "dynasty": default_dynasty})
                author, title, buf = t, None, []
                i += 2
                continue
            # 篇题
            if title and buf:
                out.append({"title": title, "author": author,
                            "paragraphs": [x for x in buf if x],
                            "chapter": "", "section": "", "dynasty": default_dynasty})
            title, buf = t, []
            i += 1
            continue
        if BIO.search(t) and len(t) < 120 and not buf:
            i += 1
            continue
        if title:
            buf.append(t)
        i += 1
    if title and buf:
        out.append({"title": title, "author": author,
                    "paragraphs": [x for x in buf if x],
                    "chapter": "", "section": "", "dynasty": default_dynasty})
    return [p for p in out if p["paragraphs"] and p["title"]]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", default="gushiji,mingshi,zhongzhou,wanqing")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    total = 0
    for series in [s.strip() for s in args.series.split(",") if s.strip()]:
        coll, dyd, fmt = SERIES_MAP[series]
        src = os.path.join(BASE, "raw", "books", series)
        dst_dir = os.path.join(BASE, "raw", "poetry", coll)
        os.makedirs(dst_dir, exist_ok=True)
        files = sorted(f for f in os.listdir(src) if f.endswith(".wikitext"))
        if args.limit:
            files = files[: args.limit]
        n_poem = 0
        for fn in files:
            text = open(os.path.join(src, fn), encoding="utf-8", errors="replace").read()
            if fmt == "skqs_anchor":
                items = parse_skqs(text, dyd)
            elif "===" in text:            # 已加标题标签的卷次
                items = parse_heading_poem(text, dyd)
            else:                          # 纯缩进版式
                items = parse_plain_anthology(text, dyd)
            for it in items:
                it["volume"] = fn.replace(".wikitext", "")
            with open(os.path.join(dst_dir, fn.replace(".wikitext", ".json")), "w",
                      encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False)
            n_poem += len(items)
        print(f"[{series:10}] 卷 {len(files):>3} → 篇目 {n_poem:>5}")
        total += n_poem
    print(f"合计篇目 {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
