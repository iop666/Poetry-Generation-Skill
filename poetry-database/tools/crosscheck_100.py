#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crosscheck_100.py —— 100 首作品独立来源逐字核对（ROUND 2-01 六）

为什么这么做：
  上一轮所谓「核实」只是「数据来自某个采集源」。审核 R2 指出：
  `source_id` ≠ 古籍底本出处。故本轮取两个**互不相同的上游**逐字比对：

    上游 A：chinese-poetry 数据集（全唐诗／唐诗三百首分片）
    上游 B：维基文库《唐詩三百首》逐篇页面（独立转录，另一个整理者）

  两者若出自同一底本或同一转录，比对价值为零。此处 A 是 GitHub 整理本，
  B 是维基文库社区转录，**不是同一上游的镜像或分片**，符合独立性要求。

判定：
  MATCH    两版归一化后完全一致 → 标 TEXT_CROSSCHECKED
  DIFF     有实质差异 → 记录差异位置，仍标 TEXT_CROSSCHECKED（差异已记录），
           但 quality_grade 不升 EDITION_VERIFIED（无版本页次）
  NOT_FOUND 维基页面未取到或库内无对应作品 → UNKNOWN，不升级

不做：不因为匹配上就宣称「版本已核」。EDITION_VERIFIED 需版本、卷次、页次。
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sqlite3
import subprocess
import time
import urllib.parse
from difflib import SequenceMatcher

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "database", "poetry.db")
OUT_RAW = os.path.join(BASE, "raw", "books", "t300_ws")
INDEX = os.path.join(BASE, "sources", "t300_index.json")
UA = "PoetryDatabase/1.0 (academic corpus build; wikisource API)"
HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002ffff]")


def fetch(title: str) -> str:
    """用 action=parse 取 wikitext，附带 redirects=1。

    为什么不用 action=raw：raw 不跟随 #REDIRECT，遇到重定向页会拿到空内容
    （首轮 5 首「页面无正文」即由此产生）。API 版会解析到目标页。
    """
    url = ("https://zh.wikisource.org/w/api.php?action=parse&prop=wikitext&format=json&redirects=1&page="
           + urllib.parse.quote(title.replace(" ", "_")))
    r = subprocess.run(["curl", "-sS", "-m", "45", "-A", UA, url], capture_output=True)
    try:
        d = json.loads(r.stdout.decode("utf-8", "replace"))
        return d["parse"]["wikitext"]["*"]
    except Exception:
        return ""


def strip_wiki(s: str) -> str:
    """去模板/链接/标签，保留可见文字。模板保留首参（防吞字，同 convert_books）。"""
    for _ in range(5):
        s2 = re.sub(r"\{\{([^{}]*)\}\}", lambda m: (lambda p: p[1].strip() if len(p) > 1 and "=" not in p[1] else "")(m.group(1).split("|")), s)
        if s2 == s:
            break
        s = s2
    s = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", s)
    s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    return s


def poem_text(raw: str) -> str:
    body = raw
    m = re.search(r"<poem>(.*?)</poem>", raw, re.S)
    if m:
        body = m.group(1)
    else:
        body = re.sub(r"(?s)\{\{header.*?\}\}", "", body)
        body = re.sub(r"(?s)\{\{album header.*?\}\}", "", body)
        body = re.sub(r"\[\[Category:[^\]]*\]\]", "", body)
    return "".join(HAN.findall(strip_wiki(body)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--sleep", type=float, default=2.0)
    args = ap.parse_args()

    os.makedirs(OUT_RAW, exist_ok=True)
    index = json.load(open(INDEX, encoding="utf-8"))

    # 分层抽样：按体裁轮取，保证五古/七古/乐府/五律/七律/五绝/七绝都有
    by_sec = {}
    for sec, author, link, disp in index:
        by_sec.setdefault(sec, []).append((sec, author, link, disp))
    picks, i = [], 0
    while len(picks) < args.limit and any(by_sec.values()):
        for sec in list(by_sec):
            if by_sec[sec]:
                picks.append(by_sec[sec].pop(0))
                if len(picks) >= args.limit:
                    break
        i += 1
        if i > 500:
            break

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    # 前缀索引：取库内每条正文前 12 字做键，避免逐条 LIKE 全表
    # 双索引：
    #   ① 标题索引 —— 主匹配路径。首轮用 12 字前缀做唯一入口，结果「爐/壚」「螘/蟻」
    #      这类单字异写一出现就整首匹配不上（100 首里有 21 首误报 NOT_FOUND）。
    #   ② 8 字前缀索引 —— 仅在标题对不上时兜底（如维基用异名标题）。
    title_idx, pref = {}, {}
    for r in conn.execute("SELECT work_id, author_name, title_norm, text_norm FROM works"):
        title_idx.setdefault(r["title_norm"], []).append(r)
        t = r["text_norm"]
        if len(t) >= 8:
            pref.setdefault(t[:8], []).append(r)

    stat = {"MATCH": 0, "DIFF": 0, "NOT_FOUND": 0}
    rows = []
    for n, (sec, author, link, disp) in enumerate(picks, 1):
        fn = os.path.join(OUT_RAW, re.sub(r"[^\w\u4e00-\u9fff]+", "_", link)[:60] + ".wikitext")
        if os.path.exists(fn) and os.path.getsize(fn) > 100:
            raw = open(fn, encoding="utf-8", errors="replace").read()
        else:
            # 空响应必须重试：维基文库对连发请求会返回 429／空体，
            # 300 首那次跑出 35% NOT_FOUND，逐条查证后确认绝大多数是被限速，
            # 不是页面真的没有正文。退避重试 3 次，仍空才计 NOT_FOUND。
            raw = ""
            for attempt in (1, 2, 3):
                raw = fetch(link)
                if raw.strip() and "<!DOCTYPE html" not in raw[:200] and len(poem_text(raw)) >= 10:
                    break
                raw = ""
                time.sleep(3 * attempt)
            if raw.strip():
                open(fn, "w", encoding="utf-8").write(raw)
            time.sleep(args.sleep)

        txt_b = poem_text(raw)
        if len(txt_b) < 10:
            stat["NOT_FOUND"] += 1
            print(f"[{n:>3}] NOT_FOUND  {disp}（三次重试后仍无正文）", flush=True)
            continue

        # 标题归一：去掉「並序」与括注，再试
        t_norm = re.sub(r"[（(].*?[）)]", "", disp).replace("並序", "").strip()
        # 候选合并：标题命中 + 正文前 8 字命中。
        # 只用标题会踩「同题异篇」——《唐詩三百首》有两首《出塞》、两首《塞下曲》，
        # 标题命中却选了另一首，相似度 0.09–0.12 被打成 NOT_FOUND（300 首里 35 首）。
        # 两路候选合并后取整体最优，可把这类误报纠正为 MATCH/DIFF。
        cands = list(title_idx.get(t_norm) or title_idx.get(disp) or [])
        seen = {c["work_id"] for c in cands}
        for c in pref.get(txt_b[:8], []):
            if c["work_id"] not in seen:
                cands.append(c)
                seen.add(c["work_id"])
        best, best_r = None, 0.0
        for c in cands:
            r = SequenceMatcher(None, txt_b, c["text_norm"]).ratio()
            if r > best_r:
                best, best_r = c, r

        if not best or best_r < 0.80:
            stat["NOT_FOUND"] += 1
            why = "库内无同题作品" if not cands else f"同题作品相似度仅 {best_r:.2f}"
            print(f"[{n:>3}] NOT_FOUND  {disp}（{why}）", flush=True)
            continue

        a, b = txt_b, best["text_norm"]
        if a == b:
            res, detail = "MATCH", ""
            stat["MATCH"] += 1
        else:
            diffs = [(t, i1, i2, j1, j2) for t, i1, i2, j1, j2 in
                     SequenceMatcher(None, a, b).get_opcodes() if t != "equal"]
            detail = "；".join(f"{t}:A[{i1}:{i2}]={a[i1:i2]} B[{j1}:{j2}]={b[j1:j2]}" for t, i1, i2, j1, j2 in diffs[:6])
            res = "DIFF"
            stat["DIFF"] += 1
        rows.append((best["work_id"], best["title_norm"], best["author_name"],
                     "chinese-poetry", "zh.wikisource:唐詩三百首",
                     res, len(a), len(b), detail,
                     datetime.datetime.now().isoformat(timespec="seconds")))
        print(f"[{n:>3}] {res:9} {disp}  相似度 {best_r:.3f}", flush=True)

    conn.executemany("INSERT OR REPLACE INTO text_crosscheck VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    conn.executemany("""UPDATE works SET quality_grade='TEXT_CROSSCHECKED',
                        crosscheck_result=? WHERE work_id=?""",
                     [(r[5], r[0]) for r in rows])
    conn.commit()
    print(f"\n合计 {len(picks)} 首：MATCH {stat['MATCH']} / DIFF {stat['DIFF']} / NOT_FOUND {stat['NOT_FOUND']}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
