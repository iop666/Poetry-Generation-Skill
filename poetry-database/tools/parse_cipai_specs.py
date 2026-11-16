#!/usr/bin/env python3
"""parse_cipai_specs.py —— 从《唐宋词格律》（龙榆生）正文提取词牌定格谱

为什么值得单独做：
    库里 19,595 首词此前没有任何词谱可对照（R2-01 报告已列为缺口）。
    《唐宋词格律》正文给出 135 个「定 格」，用龙榆生自己的符号系统：
        －  平      ｜  仄      ＋  可平可仄
        （韵） 韵位  （句） 句读  （豆） 领字豆
    这套符号可直接转成格律引擎的「平/仄/中」谱，且带页码可回溯。

不做：不把这套谱直接写成「权威词谱」。它是龙榆生一家之说，
      与《钦定词谱》有出入（书中亦屡言「《词谱》作…非」）。
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "database", "poetry.db")
SRC = os.path.join(BASE, "raw", "books_native", "long_yushsheng_cilv", "pages.jsonl")

SYM = set("－｜＋—")
CJK = re.compile(r"^[\u4e00-\u9fff·]{2,9}$")
NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def cn_num(s: str) -> int:
    """「八十一」「五十七」「百」→ int。"""
    if s == "百":
        return 100
    total, cur = 0, 0
    for ch in s:
        if ch in NUM:
            cur = NUM[ch]
        elif ch == "十":
            total += (cur or 1) * 10
            cur = 0
    return total + cur


def load() -> list:
    out = []
    for line in open(SRC, encoding="utf-8"):
        d = json.loads(line)
        t = d["text"]
        t = t.replace("定 格", "定格").replace("例 一", "例一").replace("例 二", "例二")
        t = re.sub(r"PDF 文件使用.*?www\.fineprint\.cn", "", t)
        out.append({"page": d["page"], "text": t})
    return out


def printed_page_map(pages: list) -> dict:
    """PDF 物理页 → 印刷页。

    该书文字层每页第一行就是版心页码（如「3」「45」），可直接取用。
    报告里引页码一律用印刷页，读者能按书翻到。
    """
    m = {}
    for pg in pages:
        for ln in pg["text"].split("\n"):
            ln = ln.strip()
            if not ln:
                continue
            if re.fullmatch(r"\d{1,3}", ln):
                m[pg["page"]] = int(ln)
            break
    return m


def parse_toc(pages: list) -> dict:
    """从目录页（前 12 页）取「词牌 → 印刷页码」。

    为什么要它：正文里「定格」之前的短行有时是例词题（如「听瑶瑟怨」），
    只靠版式会把例词题当词牌。用目录做白名单可挡掉这类误收，
    同时把 PDF 物理页换成书上印刷页码，便于人工核。
    """
    toc = {}
    for pg in pages[:14]:
        for ln in pg["text"].split("\n"):
            ln = ln.strip()
            m = re.match(r"^([\u4e00-\u9fff·]{2,9})(?:（[^）]*）)?\s*[…]+\.*\s*(\d{1,3})\s*$", ln)
            if m:
                toc[m.group(1)] = int(m.group(2))
    return toc


def main() -> int:
    pages = load()
    toc = parse_toc(pages)
    # 目录全文白名单：正则只能抓到部分目录行（又名括注、换行会打断），
    # 但「名字是否出现在目录里」这一判断可靠，故再补一层子串判定。
    toc_text = "".join(pg["text"] for pg in pages[:14])
    pmap = printed_page_map(pages)
    print(f"目录词牌 {len(toc)} 个；页码映射 {len(pmap)} 页")
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS cipai_specs("
                 "name TEXT PRIMARY KEY, aliases TEXT, char_count INTEGER, pattern TEXT,"
                 "rhyme_note TEXT, source_book TEXT, page INTEGER, raw TEXT, parse_status TEXT)")
    conn.execute("DELETE FROM cipai_specs WHERE source_book='唐宋词格律'")

    rows, seen = [], set()
    for pg in pages:
        lines = [x.strip() for x in pg["text"].split("\n") if x.strip()]
        for i, ln in enumerate(lines):
            if ln != "定格":
                continue
            # 词牌名：定格之前最近的一个短中文行（排除「例二」「附注」等）
            name = ""
            for j in range(i - 1, max(-1, i - 12), -1):
                cand = lines[j]
                if cand in ("例二", "例一", "附注", "又一体") or cand.startswith("附"):
                    continue
                if CJK.match(cand):
                    name = cand
                    break
            if not name or (toc and name not in toc and name not in toc_text):
                continue
            # 谱：定格之后、例一/附注之前含符号的行
            pat, rhyme, k = [], [], i + 1
            while k < len(lines):
                s = lines[k]
                if s.startswith("例一") or s.startswith("附注") or s == "例二":
                    break
                if "——" in s:                       # 例词署名，非谱
                    s = s.split("——")[0].strip()
                    if not s:
                        break
                if sum(1 for c in s if c in SYM) >= 2:
                    pat.append(s)
                    for m in re.findall(r"（(韵|句|豆|叠)）", s):
                        rhyme.append(m)
                k += 1
            if not pat:
                continue
            # 字数：名词附近「N字」
            ctx = "".join(lines[max(0, i - 10): i + 2])
            m = re.search(r"([一二三四五六七八九十百]+)字", ctx)
            nchar = cn_num(m.group(1)) if m else None
            # 别名
            alias = ""
            for j in range(max(0, i - 8), i):
                if "又名" in lines[j]:
                    alias = lines[j]
                    break
            pat_s = " ".join(pat)
            # 页码一律记 PDF 物理页：可直接按页打开该 PDF 复核。
            # 印刷页在此本中不可靠（版心数字常被拆成「3」「23」两段，目录又与正文错位），
            # 与其给一个猜的印刷页，不如给一个能点开的物理页。
            pprinted = pg["page"]
            rows.append((name, alias, nchar, pat_s, "/".join(rhyme),
                         "唐宋词格律", pprinted, "\n".join(pat),
                         "OK" if name in toc else "NAME_UNVERIFIED"))
            seen.add(name)
    conn.executemany("INSERT OR REPLACE INTO cipai_specs VALUES (?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()

    ok = len(rows)
    withc = sum(1 for r in rows if r[2])
    print(f"提取词牌定格 {ok} 个（唯一名 {len(seen)}），其中标出字数 {withc} 个")
    for r in rows[:6]:
        print(f"  {r[0]}  字数={r[2]}  p{r[6]}  韵位={r[4][:12]}")
        print(f"     谱: {r[3][:70]}")
    # 与库内词作对照：有多少词牌在语料中出现
    names = [r[0] for r in rows]
    hit = 0
    for n in names:
        c = conn.execute("SELECT COUNT(*) FROM works WHERE cipai=?", (n,)).fetchone()[0]
        if c:
            hit += 1
    print(f"其中 {hit}/{len(names)} 个词牌在语料库中能找到实际词作")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
