#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E1 v2: 基于 difflib 对齐判定 339 条。只读库。"""
import sqlite3, re, difflib, json, os
from collections import Counter

DB = "<PROJECT_ROOT>/poetry-database/database/poetry.db"
OUT = "<PROJECT_ROOT>/poetry-database/reports/tasks/2026-11-16/R2-12"

PUNCT = r"[\s\u3000，。！？、；：“”‘’（）()《》〈〉「」『』【】…—\-,.;:!?\"'·～~]"
def strip_br(s):
    return re.sub(r"[（）()「」『』《》〈〉]", "", s or "")
def norm0(s):
    return re.sub(PUNCT, "", s or "")

RE_P1 = re.compile(r"[（(]\s*([^（）()]{0,14}?)\s*一作\s*[：:]\s*([^（）)]{0,24}?)\s*[）)]", re.S)
RE_P2 = re.compile(r"[（(]\s*一作\s*[「『\"]?([^）)」』\"]{0,24})[」』\"]?\s*[）)]", re.S)
RE_P3 = re.compile(r"[（(]\s*([^（）()]{0,8}?(?:校|案|疑|一本作|集作|或作)[^（）()]{0,24}?)\s*[）)]", re.S)

def find_notes(raw):
    out, cov = [], []
    for m in RE_P1.finditer(raw):
        out.append(dict(start=m.start(), end=m.end(), head=m.group(1).strip(), var=m.group(2).strip(),
                        kind="P1_HEAD_VARIANT", matched=m.group(0)))
        cov.append((m.start(), m.end()))
    for m in RE_P2.finditer(raw):
        if any(s <= m.start() < e for s, e in cov): continue
        out.append(dict(start=m.start(), end=m.end(), head="", var=m.group(1).strip(),
                        kind="P2_VARIANT_ONLY", matched=m.group(0))); cov.append((m.start(), m.end()))
    for m in RE_P3.finditer(raw):
        if any(s <= m.start() < e for s, e in cov): continue
        out.append(dict(start=m.start(), end=m.end(), head=m.group(1).strip(), var="",
                        kind="P3_OTHER_NOTE", matched=m.group(0))); cov.append((m.start(), m.end()))
    out.sort(key=lambda x: x["start"])
    return out

def line_of(raw, pos):
    """返回 pos 所在行（按换行切）"""
    s = raw.rfind("\n", 0, pos) + 1
    e = raw.find("\n", pos)
    if e < 0: e = len(raw)
    return raw[s:e]

def seg_len(t):
    return len(norm0(t))

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); con.text_factory = str
rows = con.execute("""SELECT work_id,title_raw,title_norm,author_name,dynasty,genre,text_raw,text_norm,char_count
FROM works WHERE text_raw LIKE '%一作%' ORDER BY dynasty, work_id""").fetchall()
print("rows", len(rows))

recs = []
for wid, t1, t2, au, dy, ge, raw, nm, cc in rows:
    raw, nm = raw or "", nm or ""
    notes = find_notes(raw)
    raw_nobr = strip_br(raw)
    exp = norm0(raw_nobr)
    sm = difflib.SequenceMatcher(None, exp, nm, autojunk=False)
    deleted, inserted = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            if exp[i1:i2]: deleted.append(exp[i1:i2])
        if tag in ("insert", "replace"):
            if nm[j1:j2]: inserted.append(nm[j1:j2])
    deleted = [d for d in deleted if d]
    inserted = [i for i in inserted if i]
    # 一作 是否在括号外
    spans = [(n["start"], n["end"]) for n in notes]
    bare_occ = [m.start() for m in re.finditer("一作", raw) if not any(s <= m.start() < e for s, e in spans)]

    res = dict(work_id=wid, title=t2 or t1, author=au, dynasty=dy, genre=ge,
               raw_len=len(raw), norm_len=len(nm), char_count=cc,
               n_notes=len(notes), bare_occ=len(bare_occ),
               deleted=deleted, inserted=inserted, raw=raw, norm=nm, notes=notes)
    # 定位标记上下文
    if nm.find("一作") >= 0:
        i = nm.find("一作"); res["marker"] = "一作残留于text_norm"
    elif notes:
        n = notes[0]; i = raw.find(n["matched"][:4]); res["marker"] = f"括号校记({n['kind']})"
    elif bare_occ:
        i = bare_occ[0]; res["marker"] = "括号外「一作」(疑正文用词)"
    else:
        i = max(0, raw.find("一作")); res["marker"] = "其他"
    i = max(0, i) if i is not None and i >= 0 else 0
    res["context"] = raw[max(0, i - 32):i + 34].replace("\n", "/")
    recs.append(res)

print(Counter(("note" if r["n_notes"] else "bare") for r in recs))
json.dump(recs, open(f"{OUT}/LOGS/_e1_recs.json", "w"), ensure_ascii=False, indent=1)

# 打印括号外 case 供人工判读
bare = [r for r in recs if r["n_notes"] == 0]
print("bare-only:", len(bare))
for r in bare:
    print("--", r["work_id"], r["author"], r["title"], "| del=", r["deleted"], "| ins=", r["inserted"])
    print("   ctx:", r["context"])
con.close()
