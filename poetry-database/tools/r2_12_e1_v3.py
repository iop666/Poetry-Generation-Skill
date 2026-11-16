#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E1 v3: 精确基线对比。exp2 = 彻底删除括号校记后的归一化文本。"""
import sqlite3, re, difflib, json
from collections import Counter

DB = "<PROJECT_ROOT>/poetry-database/database/poetry.db"
OUT = "<PROJECT_ROOT>/poetry-database/reports/tasks/2026-11-16/R2-12"
PUNCT = r"[\s\u3000，。！？、；：“”‘’（）()《》〈〉「」『』【】…—\-,.;:!?\"'·～~]"
def norm0(s): return re.sub(PUNCT, "", s or "")
def strip_br(s): return re.sub(r"[（）()「」『』]", "", s or "")

# 括号内含 一作 的整段（允许无冒号），以及 校/案 类
RE_NOTE = re.compile(r"[（(][^（）()]{0,20}?一作[^（）()]{0,40}?[）)]", re.S)
RE_NOTE2 = re.compile(r"[（(][^（）()]{0,10}?(?:校|案|一本作|集作|或作)[^（）()]{0,40}?[）)]", re.S)

def spans(raw):
    sp = [(m.start(), m.end()) for m in RE_NOTE.finditer(raw)]
    for m in RE_NOTE2.finditer(raw):
        if not any(s <= m.start() < e for s, e in sp):
            sp.append((m.start(), m.end()))
    return sorted(sp)

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); con.text_factory = str
rows = con.execute("""SELECT work_id,title_raw,title_norm,author_name,dynasty,genre,text_raw,text_norm,char_count
FROM works WHERE text_raw LIKE '%一作%' ORDER BY dynasty, work_id""").fetchall()

recs = []
for wid, t1, t2, au, dy, ge, raw, nm, cc in rows:
    raw, nm = raw or "", nm or ""
    sp = spans(raw)
    cut = ""
    last = 0
    for s, e in sp:
        cut += raw[last:s]; last = e
    cut += raw[last:]
    exp2 = norm0(strip_br(cut))
    sm = difflib.SequenceMatcher(None, exp2, nm, autojunk=False)
    extra, missing = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("insert", "replace") and nm[j1:j2]: extra.append(nm[j1:j2])
        if tag in ("delete", "replace") and exp2[i1:i2]: missing.append(exp2[i1:i2])
    bare = [m.start() for m in re.finditer("一作", raw) if not any(s <= m.start() < e for s, e in sp)]
    recs.append(dict(work_id=wid, title=t2 or t1, author=au, dynasty=dy, genre=ge,
                     raw=raw, norm=nm, char_count=cc,
                     note_spans=[[s, e, raw[s:e]] for s, e in sp],
                     bare_pos=bare, extra=[x for x in extra if x], missing=[x for x in missing if x],
                     exp2=exp2,
                     bare_ctx=[raw[max(0, p - 20):p + 22].replace("\n", "/") for p in bare]))

def bucket(r):
    nb = len(r["note_spans"]); bare = len(r["bare_pos"])
    ex, mi = r["extra"], r["missing"]
    if nb and not bare:
        if not ex and not mi: return "N_CLEAN"
        if ex and not mi: return "N_GLUE"
        if mi and not ex: return "N_LOSS"
        return "N_GLUE_LOSS"
    if bare and not nb:
        if not ex and not mi: return "B_KEEP"      # norm 未动，需人工判 一作 是否正文
        if mi and not ex: return "B_LOSS"          # norm 删了 一作 段
        return "B_OTHER"
    if nb and bare:
        return "NB"
    return "X"

for r in recs: r["bucket"] = bucket(r)
print(Counter(r["bucket"] for r in recs))
json.dump(recs, open(f"{OUT}/LOGS/_e1_recs.json", "w"), ensure_ascii=False, indent=1)
for b in ["N_GLUE", "N_GLUE_LOSS", "N_LOSS", "B_OTHER", "NB", "X"]:
    sel = [r for r in recs if r["bucket"] == b]
    print(f"\n### {b} n={len(sel)}")
    for r in sel[:6]:
        print(" -", r["work_id"], r["author"], r["title"])
        print("   notes:", r["note_spans"][:3])
        print("   extra:", r["extra"][:3], "missing:", r["missing"][:3])
con.close()
