#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 C3：由 206 個韻頁重建《集韻》小韻表（不改 R2-08 表）。

與 R2-08 的差別：
  1. 用全部 206 頁（R2-08 只入庫 202 韻）
  2. 反切上下字按正確定義拆分：上字＝取聲母者（反切第 1 字），下字＝取韻母者（第 2 字）
  3. 逐小韻記「文N」自述字數與實際字頭數，便於對帳
  4. 每條保留韻頁 title、HTML SHA-256、採集時間
"""
import os
import re
import json
import glob
import sqlite3
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
SRC = os.path.join(ROOT, "raw", "r2_08", "jiyun_pages")

CJK = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0003ffff"
CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8,
      "九": 9, "十": 10, "百": 100, "零": 0, "〇": 0}


def cn2int(s):
    tot = cur = 0
    for ch in s:
        v = CN.get(ch)
        if v is None:
            return None
        if v == 10:
            cur = (cur or 1) * 10
        elif v == 100:
            tot += (cur or 1) * 100
            cur = 0
        else:
            cur += v
    return tot + cur


SEG = re.compile(r"[○〇]([^○〇]{6,})")
HEAD = re.compile(r"^([%s]{1,4})" % CJK)
GLOSS = re.compile(r"[〈<]([^〉>]{0,400})[〉>]")
FQ = re.compile(r"([%s]{1,3})切" % CJK)
WEN = re.compile(r"文([一二三四五六七八九十百零〇]{1,4})(?![一二三四五六七八九十百零〇])")

rows = []
for f in sorted(glob.glob(os.path.join(SRC, "*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    title = d["title"]
    m = re.search(r"卷(\d+)/(.+)", title)
    vol, yun = (int(m.group(1)), m.group(2)) if m else (None, title)
    t = re.sub(r"<[^>]+>", "", d.get("text", ""))
    t = re.sub(r"\[\[[^\]]*\]\]", "", t)
    t = re.sub(r"\s+", "", t)
    t = re.sub(r"^.*?(?=[○〇])", "", t)
    for i, seg in enumerate(SEG.finditer(t), 1):
        body = seg.group(1)
        hm = HEAD.match(body)
        if not hm:
            continue
        head = hm.group(1)
        g = GLOSS.search(body)
        gloss = g.group(1) if g else ""
        fq = FQ.search(body)
        wm = WEN.search(body)
        # 字頭：除首字外，統計所有〈〉前的緊鄰漢字
        heads = list(head)
        for mm in re.finditer(r"[%s]{1,4}(?=[〈<])" % CJK, body):
            heads.extend(list(mm.group(0)))
        rows.append({
            "page_title": title, "volume": vol, "yun": yun, "seq": i,
            "head": head[0], "head_all": "".join(head),
            "fanqie": fq.group(0) if fq else "",
            "fanqie_upper": fq.group(1) if fq else "",
            "fanqie_lower": (fq.group(1)[1:] if fq and len(fq.group(1)) > 1 else ""),
            "declared": cn2int(wm.group(1)) if wm else None,
            "n_heads_est": len(heads),
            "html_sha256": d.get("html_sha256"), "fetched": d.get("fetched"),
        })

con = sqlite3.connect(DB)
con.execute("DROP TABLE IF EXISTS ph_jiyun_r2_09")
con.execute("""CREATE TABLE ph_jiyun_r2_09(
 id INTEGER PRIMARY KEY AUTOINCREMENT, yun TEXT, volume INT, seq INT, head TEXT,
 fanqie TEXT, fanqie_upper TEXT, fanqie_lower TEXT, declared_chars INT, n_heads_est INT,
 page_title TEXT, html_sha256 TEXT, fetched TEXT, evidence_level TEXT, round TEXT)""")
con.executemany("""INSERT INTO ph_jiyun_r2_09
 (yun,volume,seq,head,fanqie,fanqie_upper,fanqie_lower,declared_chars,n_heads_est,
  page_title,html_sha256,fetched,evidence_level,round)
 VALUES(?,?,?,?,?,?,?,?,?,?,?,?, 'SOURCE_TRANSCRIPTION','2026-11-14')""",
    [(r["yun"], r["volume"], r["seq"], r["head"], r["fanqie"], r["fanqie_upper"],
      r["fanqie_lower"], r["declared"], r["n_heads_est"], r["page_title"],
      r["html_sha256"], r["fetched"]) for r in rows])
con.commit()

n_yun = con.execute("select count(distinct yun) from ph_jiyun_r2_09").fetchone()[0]
n_fq = con.execute("select count(*) from ph_jiyun_r2_09 where fanqie<>''").fetchone()[0]
decl = con.execute("select sum(declared_chars) from ph_jiyun_r2_09").fetchone()[0]
est = con.execute("select sum(n_heads_est) from ph_jiyun_r2_09").fetchone()[0]
print("小韻", len(rows), "韻", n_yun, "有反切", n_fq, "自述合計", decl, "字頭估計", est)
print("revid 已記錄頁數:", sum(1 for f in glob.glob(os.path.join(SRC, "*.json"))
                        if json.load(open(f)).get("revid")), "/206")
