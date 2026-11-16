#!/usr/bin/env python3
"""《陶淵明集》詩四卷 → 中间 JSON。

为什么单独补这一部：
    古詩紀（四庫全書本）在維基文庫的转录并不完整 —— 晉卷每卷仅 13–16 KB，
    全库检索「採菊東籬」「少無適俗韻」命中 0，即陶詩整体缺席。
    《昭明文選》只选 7 首陶诗，远不足以支撑「核心诗人」研究。
    维基文库《陶淵明集》按篇分页（卷一至卷四为诗），可逐篇取全文。

版式：
    {{header|title=停雲|author=陶淵明|times=晉|properties=四言}}
    <onlyinclude><poem>
    正文……{{另|韻|願}}……          ← {{另|A|B}} 表示「A，一作 B」，须取 A 并记录异文
    </poem></onlyinclude>

注意：{{另}} 是底本自带的校记，不是我的推断。取首字为正文、备字入 variants 字段，
不改动任何字，也不合并异文。
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS = os.path.join(BASE, "raw", "books", "tao")
DST = os.path.join(BASE, "raw", "poetry", "tao")
INDEX = os.path.join(BASE, "sources", "tao_index.json")
UA = "PoetryDatabase/1.0 (academic corpus build; zh.wikisource 陶淵明集)"

ELSE = re.compile(r"\{\{另\s*\|([^{}]*)\}\}")          # {{另|正|异|异2}}
TPL = re.compile(r"\{\{[^{}]*\}\}")
TAG = re.compile(r"</?(?:poem|center|div|onlyinclude|templatestyles|CENTER)[^>]*>")
HDR = re.compile(r"\{\{header(.*?)\}\}", re.S)


def fetch(title: str, timeout=45) -> str:
    url = ("https://zh.wikisource.org/w/index.php?title="
           + urllib.parse.quote(title.replace(" ", "_")) + "&action=raw")
    r = subprocess.run(["curl", "-sS", "-m", str(timeout), "-A", UA, url],
                       capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def field(header: str, key: str) -> str:
    m = re.search(r"\|\s*%s\s*=\s*([^|\n]*)" % key, header)
    return m.group(1).strip() if m else ""


def parse_page(text: str, page: str, vol: str = "") -> list:
    m = HDR.search(text)
    header = m.group(1) if m else ""
    title = field(header, "title") or page.split(" (")[0]
    section = field(header, "section")
    body = text[m.end():] if m else text

    def take_else(mm, bucket):
        parts = [x.strip() for x in mm.group(1).split("|")]
        if len(parts) >= 2 and parts[0] and parts[1]:
            bucket.append((parts[0], parts[1]))
        return parts[0] if parts else ""

    # 逐行处理：先取「另」模板的正字并记入「当前节」的异文桶，再清其他模板。
    # 不能在整页层面预先替换 —— 那样各节异文会混成一堆（《歸園田居》六首
    # 每首都曾挂上全页 36 处异文，对应关系全错）。
    # 也不能在整页清模板，否则「另」模板先被当作普通模板删掉，异文信息即丢失。
    #
    # 组诗在底本里用 ===其一=== 分节（《擬古》十二首、《雜詩》十二首皆然），
    # 故必须按节拆，否则整页会并成一条、标题取末节名，等于吞掉十一首。
    blocks, cur_sub, cur, cur_var = [], "", [], []
    for ln in body.splitlines():
        t = ln.strip().strip("\u3000")
        if not t:
            continue
        h = re.match(r"^==+\s*(.+?)\s*==+$", t)
        if h:
            if cur:
                blocks.append((cur_sub, cur, cur_var))
            cur_sub, cur, cur_var = h.group(1).strip(), [], []
            continue
        if t.startswith("|") or t.startswith("[[Category"):
            continue
        t = ELSE.sub(lambda m: take_else(m, cur_var), t)
        for _ in range(4):
            new_t = TPL.sub("", t)
            if new_t == t:
                break
            t = new_t
        t = TAG.sub("", t).replace("'''", "").replace("''", "").strip()
        if not t or t.startswith("{{"):
            continue
        cur.append(t)
    if cur:
        blocks.append((cur_sub, cur, cur_var))

    # 组诗页在首个 ===其一=== 之前有一段总序（《擬古》「余閒居寡歡…」即此类）。
    # 它是序，不是诗；若与分节并列保留，会凭空多出一首「擬古」并把序当正文。
    if len(blocks) > 1 and blocks[0][0] == "":
        blocks = blocks[1:]

    out = []
    for sub, lines, vs in blocks:
        if not lines:
            continue
        full_title = title + ("·" + sub if sub else "")
        if not sub and section and re.fullmatch(r"[一二三四五六七八九十百]+首", section):
            full_title += "（%s）" % section
        out.append({"title": full_title, "author": "陶淵明", "paragraphs": lines,
                    "chapter": "陶淵明集", "section": sub, "dynasty": "魏晋南北朝",
                    "page": page, "variants": vs, "volume": "卷" + vol})
    return out


def main() -> int:
    os.makedirs(BOOKS, exist_ok=True)
    os.makedirs(DST, exist_ok=True)
    idx = json.load(open(INDEX, encoding="utf-8"))
    log = []
    by_vol = {}
    for vol, page in idx:
        dst = os.path.join(BOOKS, page.replace("/", "_") + ".wikitext")
        if not (os.path.exists(dst) and os.path.getsize(dst) > 0):
            txt = fetch(page)
            if not txt.strip():
                log.append({"page": page, "status": "EMPTY", "bytes": 0})
                continue
            open(dst, "w", encoding="utf-8").write(txt)
            time.sleep(1.4)
        txt = open(dst, encoding="utf-8", errors="replace").read()
        recs = parse_page(txt, page, vol)
        log.append({"page": page, "status": "OK" if recs else "NO_BODY",
                    "bytes": len(txt), "items": len(recs),
                    "variants": sum(len(r["variants"]) for r in recs)})
        if recs:
            by_vol.setdefault(vol, []).extend(recs)
    for vol, items in by_vol.items():
        json.dump(items, open(os.path.join(DST, "卷%s.json" % vol), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("  卷%s: %d 篇" % (vol, len(items)))
    ok = sum(1 for r in log if r["status"] == "OK")
    var = sum(r.get("variants", 0) for r in log)
    print(f"页数 {len(idx)}，成功 {ok}，异文标记 {var} 处")
    json.dump(log, open(os.path.join(BASE, "audit", "tao_fetch.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
