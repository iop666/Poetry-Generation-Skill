#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 E3/E4：33 條韻式衝突逐條裁定 + 韻式字段重構。

關鍵假設的檢驗：R2-07 的 source_rhyme_label 是否其實來自「詞牌層級」而非「該格」？
做法：比對 form.declared_rhyme 與 entity.declared_rhyme，並另以例詞實際韻腳
（用 R2-09 新建的《詞林正韻》字表查部與聲調）作為第三方證據。

輸出：
  cipai_rhyme_fields_r2_09   七個分欄（原書標籤／譜行符號／句末聲調／括注特徵／
                              標注推導／例詞觀察／衝突）
  cipai_conflict_verdict_r2_09 33 條逐條判定
"""
import os
import re
import json
import csv
import sqlite3
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
OUT = os.path.join(ROOT, "raw", "r2_09", "conflicts")
os.makedirs(OUT, exist_ok=True)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

# 詞林正韻 字→(部集合, 調集合)
cr = collections.defaultdict(lambda: {"bu": set(), "tone": set()})
for r in con.execute("select bu,charx,tone from ph_cilin_r2_09"):
    cr[r["charx"]]["bu"].add(re.sub(r"^第", "", r["bu"]).replace("部", ""))
    cr[r["charx"]]["tone"].add(r["tone"])

TONE_OF = {"平": "平", "上": "仄", "去": "仄", "入": "仄"}


def sym_tone(s):
    return {"－": "平", "｜": "仄", "＋": None}.get(s)


def split_sent(text):
    parts = re.split(r"([（(][^）)]*[）)])", text or "")
    out, pend = [], ""
    for p in parts:
        m = re.fullmatch(r"[（(]([^）)]*)[）)]", p.strip())
        if not m:
            pend += p
            continue
        out.append((re.sub(r"[\s　]", "", pend), m.group(1)))
        pend = ""
    if pend.strip():
        out.append((re.sub(r"[\s　]", "", pend), ""))
    return out


def ex_rhyme(fid):
    """用例詞實際文字取韻腳：按譜行句長對齊，取每句末字。"""
    e = con.execute("select text,author from cipai_form_examples_r2_08 where form_id=? "
                    "and text is not null order by example_id limit 1", (fid,)).fetchone()
    f = con.execute("select sentence_lengths,source_text,total_characters from cipai_forms_r2_07 "
                    "where form_id=?", (fid,)).fetchone()
    if not e or not f:
        return None
    lens = [int(x) for x in re.findall(r"\d+", f["sentence_lengths"] or "")]
    body = re.sub(r"[^\u4e00-\u9fff]", "", e["text"] or "")
    if not lens or len(body) < sum(lens) - 8:
        return None
    feet, i = [], 0
    for L in lens:
        if i + L > len(body):
            break
        feet.append(body[i + L - 1])
        i += L
    rows = []
    for ch in feet:
        c = cr.get(ch)
        rows.append({"char": ch,
                     "bu": sorted(c["bu"]) if c else [],
                     "tone": sorted(c["tone"]) if c else []})
    return {"author": e["author"], "feet": rows,
            "n_known": sum(1 for r in rows if r["bu"]),
            "n_feet": len(rows)}


# ---------- 重構七欄 ----------
con.execute("DROP TABLE IF EXISTS cipai_rhyme_fields_r2_09")
con.execute("""CREATE TABLE cipai_rhyme_fields_r2_09(
 form_id TEXT PRIMARY KEY, cipai_name TEXT, form_seq INT,
 source_rhyme_label TEXT,          -- 原書明言的韻式分類（詞牌層級，未必屬該格）
 source_rhyme_label_scope TEXT,    -- BRAND_LEVEL / FORM_LEVEL
 scoreline_symbol_sequence TEXT,   -- 譜行符號（原書）
 scoreline_end_tone_sequence TEXT, -- 按句末符號取的聲調序列
 source_annotation_features TEXT,  -- 括注特徵（韵/句/豆/换）
 notation_inferred_rhyme_behavior TEXT,  -- 結合括注與符號的推導
 example_observed_rhyme_behavior TEXT,   -- 由例詞實際韻腳觀察（無例詞則 NULL）
 classification_conflict INT%d, round TEXT)""" % 0)
rows = []
for f in con.execute("""select f.*, e.declared_rhyme ent_rhyme, e.section_name ent_section,
 e.section_class ent_class from cipai_forms_r2_07 f
 left join cipai_entities_r2_07 e on e.entity_id=f.cipai_id"""):
    d = dict(f)
    sents = split_sent(d["source_text"])
    symseq = "/".join(s[0] for s in sents)
    tones = [sym_tone(s[0][-1]) for s in sents if s[0]]
    tone_seq = "".join(t if t else "?" for t in tones)
    anns = [s[1] for s in sents if s[1]]
    feats = collections.Counter()
    for a in anns:
        for k in ("换", "轉", "转", "叶", "疊", "叠", "句", "豆", "韵", "韻"):
            if k in a:
                feats[k] += 1
    obs = con.execute("select observed_rhyme_behavior,classification_conflict,"
                      "source_rhyme_label,source_rhyme_label_class "
                      "from cipai_rhyme_dual_r2_08 where form_id=?", (d["form_id"],)).fetchone()
    ex = ex_rhyme(d["form_id"])
    ex_behavior = None
    if ex and ex["n_known"] >= max(3, ex["n_feet"] // 2):
        ts = set()
        for r in ex["feet"]:
            for t in r["tone"]:
                ts.add(TONE_OF.get(t, "?"))
        if ts == {"平"}:
            ex_behavior = "平韻"
        elif ts == {"仄"}:
            ex_behavior = "仄韻"
        elif ts == {"平", "仄"}:
            bus = collections.Counter()
            for r in ex["feet"]:
                for b in r["bu"]:
                    bus[b] += 1
            multi = len([b for b, n in bus.items() if n >= 2])
            ex_behavior = "平仄通叶" if multi <= 2 else "平仄转换或错叶"
    scope = "FORM_LEVEL" if (d["declared_rhyme"] or "") != (d["ent_rhyme"] or "") else "BRAND_LEVEL"
    rows.append({
        "form_id": d["form_id"], "cipai_name": d["cipai_name"], "form_seq": d["form_seq"],
        "source_rhyme_label": (obs["source_rhyme_label"] if obs else "") or "",
        "source_rhyme_label_scope": scope,
        "scoreline_symbol_sequence": symseq,
        "scoreline_end_tone_sequence": tone_seq,
        "source_annotation_features": "|".join("%s×%d" % (k, v) for k, v in feats.items()),
        "notation_inferred_rhyme_behavior": obs["observed_rhyme_behavior"] if obs else "",
        "example_observed_rhyme_behavior": ex_behavior,
        "classification_conflict": obs["classification_conflict"] if obs else 0,
    })
con.executemany("""INSERT INTO cipai_rhyme_fields_r2_09 VALUES
 (?,?,?,?,?,?,?,?,?,?,?, '2026-11-14')""",
    [(r["form_id"], r["cipai_name"], r["form_seq"], r["source_rhyme_label"],
      r["source_rhyme_label_scope"], r["scoreline_symbol_sequence"],
      r["scoreline_end_tone_sequence"], r["source_annotation_features"],
      r["notation_inferred_rhyme_behavior"], r["example_observed_rhyme_behavior"],
      r["classification_conflict"]) for r in rows])

# ---------- 33 條裁定 ----------
conf = [r for r in rows if r["classification_conflict"]]
con.execute("DROP TABLE IF EXISTS cipai_conflict_verdict_r2_09")
con.execute("""CREATE TABLE cipai_conflict_verdict_r2_09(
 form_id TEXT PRIMARY KEY, cipai_name TEXT, form_seq INT, label_class TEXT,
 observed TEXT, example_observed TEXT, label_scope TEXT, verdict TEXT,
 evidence TEXT, note TEXT, round TEXT)""")
lab = {r["form_id"]: r for r in con.execute(
    "select form_id,source_rhyme_label_class,observed_rhyme_behavior,rhyme_tone_sequence,"
    "source_rhyme_label from cipai_rhyme_dual_r2_08")}
out = []
for r in conf:
    L = lab[r["form_id"]]
    exb = r["example_observed_rhyme_behavior"]
    scope = r["source_rhyme_label_scope"]
    lc = L["source_rhyme_label_class"]
    ob = L["observed_rhyme_behavior"]
    MIX = ("平仄通叶", "平仄转换或错叶")
    if exb and exb == ob:
        verdict = "SOURCE_SCORELINE_SUPPORTED"
        ev = "例詞實際韻腳為%s，與譜行推導一致" % exb
    elif exb in MIX and ob in MIX:
        verdict = "TERM_CATEGORY_MISMATCH"
        ev = "標籤%s、譜行推導%s、例詞%s 屬不同名目（通叶／轉換／錯叶），不宜以「相符/矛盾」二分" % (lc, ob, exb)
    elif exb and ((lc.startswith("平") and exb.startswith("平")) or
                  (lc.startswith("仄") and exb.startswith("仄"))):
        verdict = "EXAMPLE_CONTRADICTION"
        ev = "例詞實際為%s，與原書標籤%s同類，但與譜行推導%s不符" % (exb, lc, ob)
    elif scope == "BRAND_LEVEL" and r["form_seq"] > 1:
        verdict = "SOURCE_ENTITY_LABEL_INHERITED"
        ev = "該格未另立韻式說明，沿用詞牌層級「%s」；譜行與例詞顯示為%s" % (lc, ob)
    elif not exb:
        verdict = "INSUFFICIENT_EVIDENCE"
        ev = "無可用例詞或例詞字不在《詞林正韻》字表內"
    else:
        verdict = "MULTIPLE_INTERPRETATIONS"
        ev = "標籤%s、譜行%s、例詞%s 三者不完全一致" % (lc, ob, exb)
    out.append((r["form_id"], r["cipai_name"], r["form_seq"], lc, ob, exb, scope,
                verdict, ev, r["source_annotation_features"]))
con.executemany("INSERT INTO cipai_conflict_verdict_r2_09 VALUES(?,?,?,?,?,?,?,?,?,?, '2026-11-14')", out)
con.commit()

with open(os.path.join(OUT, "CIPAI_33_RHYME_CONFLICTS.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["form_id", "詞牌", "格", "原書標籤", "譜行推導", "例詞觀察", "標籤層級",
                "判定", "證據", "括注特徵"])
    w.writerows(out)

cnt = collections.Counter(o[7] for o in out)
print("conflicts", len(out), dict(cnt))
print("scope:", collections.Counter(r["source_rhyme_label_scope"] for r in rows))
print("example observed available:", sum(1 for r in rows if r["example_observed_rhyme_behavior"]))
for o in out[:6]:
    print(" ", o[1], o[2], o[3], "->", o[4], "| ex:", o[5], "|", o[7])
