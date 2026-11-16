#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-07：《唐宋词格律》194 条词格逐项核验与结构化。

设计原则
--------
1. 一律以本地 PDF 文字层为主来源；外部网页只作交叉参考，不覆盖原书。
2. 任何字段若原书未明言，一律 NULL / UNKNOWN，不做知识补全。
3. 字数、句数、韵位由谱行符号（－｜＋）与括注（韵/句/豆/叶平/换仄韵…）机械推算，
   再与原文自述的「××字，×韵」比对；不符者不修改数据，只打标记。
4. 原文写「变格」「格一」「别格」等标签原样保留，不归并为泛化的 variant。
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database" / "poetry.db"
SRC = ROOT / "raw" / "books_native" / "long_yushsheng_cilv" / "pages.jsonl"
OUT = ROOT / "raw" / "r2_07_forms.json"

# 本地 PDF 的物理页 → 印刷页偏移（正文首调「十六字令」在 PDF p16、印刷 1）
OFFSET = 15
BODY_FIRST, BODY_LAST = 16, 250

GE_MARK = re.compile(r"^(定\s*格|变\s*格.*|格\s*[一二三四五六七八九十].*|别\s*格.*|又一体.*)$")
STOP = re.compile(r"^(例|附|注|说\s*明|考)")
SYM = re.compile(r"[－｜＋]")
ANN = re.compile(r"[（(]([^）)]{1,12})[）)]")
PAGENO = re.compile(r"^\d{1,3}$")

SECTION = OrderedDict([
    ("第一类", "平韵格"),
    ("第二类", "仄韵格"),
    ("第三类", "平仄韵转换格"),
    ("第四类", "平仄韵通叶格"),
    ("第五类", "平仄韵错叶格"),
])

CN_DIGIT = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def cn2int(s: str) -> int | None:
    """中文数字转整数，覆盖「十六」「二十七」「一百一十四」等原书写法。"""
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total, section = 0, 0
    if "百" in s:
        head, s = s.split("百", 1)
        total += (CN_DIGIT.get(head, 1) if head else 1) * 100
        if s.startswith("零"):
            s = s[1:]
    if "十" in s:
        head, _, tail = s.partition("十")
        section = (CN_DIGIT.get(head, 1) if head else 1) * 10
        s = tail
    if s:
        if s[0] not in CN_DIGIT:
            return None
        section += CN_DIGIT[s[0]]
    return total + section


def load_flat() -> list[tuple[int, str]]:
    rows = {int(json.loads(l)["page"]): json.loads(l)["text"]
            for l in SRC.open(encoding="utf-8")}
    flat = []
    for pg in sorted(rows):
        for ln in rows[pg].splitlines():
            t = ln.strip()
            if not t or "pdfFactory" in t:
                continue
            flat.append((pg, t))
    return flat


def ns(x: str) -> str:
    return re.sub(r"[\s\u3000]+", "", x)


def load_toc() -> list[dict]:
    """从 R2-06 的目录表取骨架，避免重写目录解析（该表已与出版说明核对过）。"""
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT cipai_id, cipai_name, alias, section_class, section_name, order_no,"
        " printed_page, n_ge FROM cipai_catalog_r2_06 ORDER BY order_no").fetchall()
    con.close()
    return [dict(zip(["cipai_id", "name", "alias", "sclass", "sname", "order_no",
                      "printed", "n_ge"], r)) for r in rows]


def locate_titles(flat: list[tuple[int, str]], toc: list[dict]) -> list[dict]:
    """在正文里定位每个词牌的标题行；标题在 PDF 中常带字间空格，故去空格比对。"""
    pos = 0
    for e in toc:
        want = ns(e["name"])
        hint = e["printed"] + OFFSET - 2
        found = -1
        for i in range(pos, len(flat)):
            pg, t = flat[i]
            if pg < hint:
                continue
            if pg > e["printed"] + OFFSET + 2:
                break
            if ns(t) == want:
                found = i
                break
        if found < 0:
            for i in range(pos, len(flat)):
                pg, t = flat[i]
                if pg < hint:
                    continue
                if pg > e["printed"] + OFFSET + 2:
                    break
                n = ns(t)
                if n.startswith(want) and len(n) <= len(want) + 2:
                    found = i
                    break
        e["flat_pos"] = found
        if found >= 0:
            pos = found + 1
    ok = [e for e in toc if e["flat_pos"] >= 0]
    for k, e in enumerate(ok):
        e["flat_end"] = ok[k + 1]["flat_pos"] - 1 if k + 1 < len(ok) else len(flat) - 1
    for e in toc:
        if e["flat_pos"] >= 0:
            e["pdf_from"] = flat[e["flat_pos"]][0]
            e["pdf_to"] = flat[e["flat_end"]][0]
    return toc


def parse_block(lines: list[tuple[int, str]]) -> dict:
    """把谱行块解析成符号串 + 逐句长度 + 括注。

    原书凡例 04：「以—表平，｜表仄，＋表可平可仄」；凡例 10：句下以符号表豆、句、韵。
    因此每个括注之前累积的符号数，就是该句字数。
    """
    text = "".join(ns(t) for _, t in lines)
    sentences, cur, i = [], 0, 0
    while i < len(text):
        ch = text[i]
        if ch in "－｜＋":
            cur += 1
            i += 1
        elif ch in "（(":
            j = text.find(")", i)
            if j < 0:
                j = text.find("）", i)
            if j < 0:
                break
            ann = text[i + 1:j]
            sentences.append({"len": cur, "ann": ann, "repeat": ann.startswith("叠")})
            cur = 0
            i = j + 1
        else:
            i += 1
    if cur:
        sentences.append({"len": cur, "ann": "", "repeat": False})
    syms = "".join(c for c in text if c in "－｜＋")
    return {"symbols": syms, "sentences": sentences}


def tone_of(syms: str) -> str:
    s = {c for c in syms}
    if s == {"－"}:
        return "平"
    if s == {"｜"}:
        return "仄"
    if s and s <= {"－", "＋"}:
        return "平"
    if s and s <= {"｜", "＋"}:
        return "仄"
    return "UNKNOWN"


def rhyme_tone(ann: str, last_sym: str, section_name: str) -> str:
    """韵脚声调：优先取括注明写的「平韵/叶平/换仄韵」，其次看该句末字，最后用韵式类别。"""
    if any(k in ann for k in ("平韵", "叶平", "转平韵", "换平韵", "再换平韵")):
        return "平"
    if any(k in ann for k in ("仄韵", "叶仄", "换仄韵", "再换仄韵", "叶二仄", "叶首仄")):
        return "仄"
    if ann in ("韵", "叶"):
        if section_name == "平韵格":
            return "平"
        if section_name == "仄韵格":
            return "仄"
        return {"－": "平", "｜": "仄"}.get(last_sym, "UNKNOWN")
    return ""


def extract_examples(flat, a: int, b: int) -> tuple[str, str, int]:
    """从格区间里取例词：第一条「例」的正文首行与署名。"""
    first_txt, author = "", ""
    k = None
    for i in range(a, b + 1):
        if re.match(r"^例", flat[i][1]):
            k = i
            break
    if k is None:
        return "", "", 0
    buf = []
    for i in range(k + 1, min(k + 40, b + 1)):
        t = flat[i][1]
        if re.match(r"^例|^附|^注", t) or GE_MARK.match(t):
            break
        if t.startswith("——"):
            author = t.lstrip("—－- ").strip()
            break
        buf.append(t)
    if buf:
        first_txt = "".join(buf)[:60]
    return first_txt, author, (k + 1 if k is not None else 0)


def extract_notes(flat, a: int, b: int) -> list[str]:
    out = []
    for i in range(a, min(b + 1, len(flat))):
        t = flat[i][1]
        if re.match(r"^附\s*注", t) or re.match(r"^注[:：]", t):
            buf = [t]
            for j in range(i + 1, min(i + 6, b + 1)):
                s = flat[j][1]
                if re.match(r"^例|^定\s*格|^格\s*[一二三四五]|^变\s*格|^别\s*格|^——", s):
                    break
                buf.append(s)
            out.append(ns("".join(buf)))
    return out


def section_at(flat, i: int) -> tuple[str, str]:
    """返回第 i 行所属的韵式类别（第N类 / 名称）。"""
    cls, name = "", ""
    for j in range(i, -1, -1):
        t = ns(flat[j][1])
        if t in SECTION:
            cls = t
            name = SECTION[t]
            break
    return cls, name


def main() -> int:
    flat = load_flat()
    toc = load_toc()
    toc = locate_titles(flat, toc)

    # ---- 逐格抽取 -------------------------------------------------------
    all_positions = [i for i, (pg, t) in enumerate(flat) if GE_MARK.match(t)]
    forms = []
    assigned = set()
    for e in toc:
        if e.get("flat_pos", -1) < 0:
            continue
        a, b = e["flat_pos"], e["flat_end"]
        heads = [i for i in all_positions if a < i <= b]
        e["form_positions"] = heads
        e["orphan_positions"] = [i for i in range(a, b + 1)
                                 if GE_MARK.match(flat[i][1]) and i not in heads]
        assigned.update(heads)
        # 词牌描述区（标题后到首个格标记前）
        desc_end = heads[0] if heads else min(a + 8, b)
        desc_lines = [flat[k][1] for k in range(a + 1, desc_end)]
        desc = ns("".join(desc_lines))
        e["desc"] = desc
        declared = []
        for m in re.finditer(r"([一二三四五六七八九十百零两]{1,6})字", desc):
            v = cn2int(m.group(1))
            if v and 10 <= v <= 400:
                declared.append(v)
        e["declared_chars"] = sorted(set(declared))
        dm = re.search(r"([一二三四五六七八九十]{1,3})(平|仄|平仄)?韵", desc)
        e["declared_rhyme"] = dm.group(0) if dm else ""

        cls, sname = section_at(flat, a)
        e["section_class"], e["section_name"] = cls, sname

        prev_end = a
        for n, hi in enumerate(heads, 1):
            pg, raw = flat[hi]
            label_raw = raw
            label = ns(re.sub(r"[（(].*?[）)]", "", raw))
            mnote = ANN.search(raw)
            note = mnote.group(1) if mnote else ""
            ptype = ("定格" if label == "定格" else
                     "变格" if label.startswith("变格") else
                     "别格" if label.startswith("别格") else
                     "格序" if label.startswith("格") else "又一体")
            # 谱行块
            blk, j = [], hi + 1
            while j <= b and j < hi + 40:
                s = flat[j][1]
                if GE_MARK.match(s) or STOP.match(s):
                    break
                if PAGENO.fullmatch(s):
                    j += 1
                    continue
                if SYM.search(s) or ANN.search(s):
                    blk.append((flat[j][0], s))
                    j += 1
                    continue
                break
            parsed = parse_block(blk)
            sents = parsed["sentences"]
            total = sum(x["len"] for x in sents)
            rhyme_idx = [k + 1 for k, x in enumerate(sents)
                         if any(t in x["ann"] for t in ("韵", "叶")) or x["ann"].startswith("叠")]
            tones = []
            for k in [r - 1 for r in rhyme_idx]:
                x = sents[k]
                tones.append(rhyme_tone(x["ann"], parsed["symbols"][
                    sum(y["len"] for y in sents[:k]) + x["len"] - 1:][:1] or "", sname))
            tones = [t for t in tones if t]
            rtone = ("平" if tones and set(tones) == {"平"} else
                     "仄" if tones and set(tones) == {"仄"} else
                     "平仄" if tones else "UNKNOWN")

            # 上下片：只在原书描述明言「上下片/前后片」或两半完全相同时才拆
            n_s = len(sents)
            up = low = None
            stanza_src = "NULL"
            if n_s and n_s % 2 == 0:
                half = n_s // 2
                if desc and re.search(r"(上下片|前后片|前片|后片|上下阕|前后阕|双调|重填|两片|二片)", desc):
                    up, low, stanza_src = half, n_s - half, "DESCRIPTION"
                else:
                    l1 = [x["len"] for x in sents[:half]]
                    l2 = [x["len"] for x in sents[half:]]
                    s1 = "".join(x["ann"] for x in sents[:half])
                    s2 = "".join(x["ann"] for x in sents[half:])
                    if l1 == l2 and s1 == s2:
                        up, low, stanza_src = half, n_s - half, "IDENTICAL_HALVES"

            ex_txt, ex_author, ex_line = extract_examples(flat, hi, min(
                heads[n] - 1 if n < len(heads) else b, b))
            notes = extract_notes(flat, hi, min(
                heads[n] - 1 if n < len(heads) else b, b))

            declared_here = e["declared_chars"]
            match = (total in declared_here) if declared_here else None
            diff_kind = ""
            if match is False:
                if re.search(r"添字|摊破|减字|偷声|慢|转调|又一体|绝句式|双调|叠韵",
                             label_raw + note):
                    diff_kind = "EXPECTED_VARIANT"
                elif any(total == 2 * d for d in declared_here):
                    diff_kind = "EXPECTED_DOUBLE"      # 单调重填为双调
                elif any(abs(total - d) <= 3 for d in declared_here):
                    diff_kind = "COUNT_NEAR_MISS"      # 与原书自述字数差 1-3 字，须核原图/异本
                else:
                    diff_kind = "CHECK_REQUIRED"

            forms.append({
                "cipai_id": e["cipai_id"], "cipai_name": e["name"],
                "order_no": e["order_no"], "form_seq": n,
                "original_heading": raw, "pattern_label": label,
                "pattern_note": note, "pattern_type": ptype,
                "section_class": cls, "section_name": sname,
                "rhyme_category": sname,
                "total_characters": total,
                "sentence_count": n_s,
                "sentence_lengths": ",".join(str(x["len"]) for x in sents),
                "pingze_pattern": "/".join(
                    parsed["symbols"][sum(y["len"] for y in sents[:k]):
                                      sum(y["len"] for y in sents[:k + 1])]
                    for k in range(n_s)),
                "rhyme_positions": ",".join(map(str, rhyme_idx)),
                "rhyme_count": len(rhyme_idx),
                "rhyme_tone": rtone,
                "ann_sequence": " ".join(x["ann"] or "-" for x in sents),
                "upper_stanza": up, "lower_stanza": low,
                "stanza_split_source": stanza_src,
                "special_tone_rules": " ｜ ".join(notes)[:600],
                "notes": " ｜ ".join(notes)[:600],
                "example_work": ex_txt, "example_author": ex_author,
                "declared_chars": ",".join(map(str, declared_here)),
                "declared_rhyme": e["declared_rhyme"],
                "declared_match": "" if match is None else int(match),
                "diff_kind": diff_kind,
                "pdf_page": pg, "printed_page": pg - OFFSET,
                "source_text": " ".join(ns(t) for _, t in blk)[:800],
                "block_lines": len(blk),
                "block_list": [[pg_, ln_] for pg_, ln_ in blk],
                "ocr_status": ("SYMBOL_GAP" if diff_kind in ("CHECK_REQUIRED", "COUNT_NEAR_MISS")
                               else "PARSED" if total else "EMPTY"),
                "image_verified": 0,
                "review_status": "PARSED",
            })
        e["form_count"] = len(heads)

    orphans = sorted(set(all_positions) - assigned)
    print(f"格标记总数 {len(all_positions)}；归属 {len(assigned)}；孤立 {len(orphans)}")
    for i in orphans:
        print(f"  孤立 p{flat[i][0]}: {flat[i][1]!r}（前一行 {flat[i-1][1][:40]!r}）")

    for k, f in enumerate(forms, 1):
        f["form_id"] = f"F07-{k:04d}"

    # ---- 派生调关系 -----------------------------------------------------
    # 关键结构事实：龙榆生把「减字/偷声/摊破/添字/慢/转调」列为同一词牌的「格」，
    # 不是独立词牌（如《木兰花》格三＝减字木兰花、格四＝偷声木兰花、格五＝木兰花慢）。
    variants = []
    for f in forms:
        note = f["pattern_note"]
        if re.search(r"减字|偷声|摊破|添字|慢曲|慢调|转调|绝句式", note):
            variants.append({
                "base": f["cipai_name"], "derived": note,
                "relation": ("减字" if "减字" in note else "偷声" if "偷声" in note else
                             "摊破" if "摊破" in note else "添字" if "添字" in note else
                             "转调" if "转调" in note else "慢" if "慢" in note else "绝句式"),
                "evidence": f"原书标签「{f['original_heading']}」，列为本调之格而非独立词牌",
                "pdf_page": f["pdf_page"], "form_id": f["form_id"],
                "confidence": "TEXT_EXPLICIT"})
    # 别名中指出的异名调（《又名…》）单独记录，不与实体合并
    for e in toc:
        if e.get("alias") and re.search(r"《[^》]+》", e["alias"]):
            variants.append({"base": e["name"], "derived": "", "relation": "又名",
                             "evidence": f"原书别名：{e['alias'][:80]}",
                             "pdf_page": e.get("pdf_from"), "form_id": "",
                             "confidence": "TEXT_EXPLICIT"})

    # 同调多体（同一词牌下 ≥2 条 form）
    multi = [(e["name"], e["form_count"], e["form_positions"]) for e in toc
             if e.get("form_count", 0) > 1]
    print(f"同调多体 {len(multi)} 调")

    # ---- 落库 -----------------------------------------------------------
    con = sqlite3.connect(DB)
    con.executescript("""
    DROP TABLE IF EXISTS cipai_entities_r2_07;
    DROP TABLE IF EXISTS cipai_forms_r2_07;
    DROP TABLE IF EXISTS cipai_form_sources_r2_07;
    DROP TABLE IF EXISTS cipai_form_variants_r2_07;
    DROP TABLE IF EXISTS cipai_audit_r2_07;
    CREATE TABLE cipai_entities_r2_07(
      entity_id TEXT PRIMARY KEY, cipai_name TEXT, alias TEXT,
      section_class TEXT, section_name TEXT, order_no INTEGER,
      printed_page INTEGER, pdf_from INTEGER, pdf_to INTEGER,
      n_form INTEGER, first_label TEXT, has_dingge INTEGER,
      declared_chars TEXT, declared_rhyme TEXT,
      length_class TEXT, length_class_source TEXT,
      desc_text TEXT, source_book TEXT, verification_status TEXT);
    CREATE TABLE cipai_forms_r2_07(
      form_id TEXT PRIMARY KEY, cipai_id TEXT, cipai_name TEXT,
      form_seq INTEGER, original_heading TEXT, pattern_label TEXT,
      pattern_note TEXT, pattern_type TEXT, section_class TEXT, section_name TEXT,
      rhyme_category TEXT, total_characters INTEGER, sentence_count INTEGER,
      sentence_lengths TEXT, pingze_pattern TEXT, rhyme_positions TEXT,
      rhyme_count INTEGER, rhyme_tone TEXT, ann_sequence TEXT,
      upper_stanza TEXT, lower_stanza TEXT, stanza_split_source TEXT,
      special_tone_rules TEXT, notes TEXT, example_work TEXT, example_author TEXT,
      declared_chars TEXT, declared_rhyme TEXT, declared_match INTEGER, diff_kind TEXT,
      pdf_page INTEGER, printed_page INTEGER, source_text TEXT, block_lines INTEGER,
      ocr_status TEXT, image_verified INTEGER, review_status TEXT);
    CREATE TABLE cipai_form_sources_r2_07(
      form_id TEXT, line_no INTEGER, pdf_page INTEGER, raw_line TEXT, role TEXT);
    CREATE TABLE cipai_form_variants_r2_07(
      base_name TEXT, derived_name TEXT, relation TEXT, evidence TEXT,
      pdf_page INTEGER, form_id TEXT, confidence TEXT);
    CREATE TABLE cipai_audit_r2_07(
      form_id TEXT PRIMARY KEY, page_ok INTEGER, name_ok INTEGER, label_ok INTEGER,
      chars_ok INTEGER, stanza_ok INTEGER, sentence_ok INTEGER, pingze_ok INTEGER,
      rhyme_ok INTEGER, division_ok INTEGER, tone_rule_ok INTEGER,
      example_ok INTEGER, note_ok INTEGER, unknown_fields TEXT, verdict TEXT);
    """)

    LEN_CLASS = lambda n: ("小令" if n <= 58 else "中调" if n <= 90 else "长调")
    for k, e in enumerate(toc, 1):
        if e.get("flat_pos", -1) < 0:
            continue
        labs = [ns(re.sub(r"[（(].*", "", flat[i][1])) for i in e["form_positions"]]
        declared = e["declared_chars"][0] if e["declared_chars"] else None
        con.execute("INSERT INTO cipai_entities_r2_07 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            e["cipai_id"], e["name"], e["alias"] or "", e["section_class"], e["section_name"],
            e["order_no"], e["printed"], e["pdf_from"], e["pdf_to"],
            len(e["form_positions"]), labs[0] if labs else "",
            1 if "定格" in labs else 0,
            ",".join(map(str, e["declared_chars"])), e["declared_rhyme"],
            LEN_CLASS(declared) if declared else "",
            "DERIVED_FROM_DECLARED_CHARS" if declared else "",
            e["desc"][:400], "唐宋词格律（上海古籍 1978 影印，本地 PDF 文字层）",
            "PARSED_NOT_VERIFIED"))

    for f in forms:
        fid = f["form_id"]
        con.execute("INSERT INTO cipai_forms_r2_07 VALUES (" +
                    ",".join("?" * 37) + ")", (
            fid, f["cipai_id"], f["cipai_name"], f["form_seq"], f["original_heading"],
            f["pattern_label"], f["pattern_note"], f["pattern_type"], f["section_class"],
            f["section_name"], f["rhyme_category"], f["total_characters"],
            f["sentence_count"], f["sentence_lengths"], f["pingze_pattern"],
            f["rhyme_positions"], f["rhyme_count"], f["rhyme_tone"], f["ann_sequence"],
            f["upper_stanza"], f["lower_stanza"], f["stanza_split_source"],
            f["special_tone_rules"], f["notes"], f["example_work"], f["example_author"],
            f["declared_chars"], f["declared_rhyme"],
            None if f["declared_match"] == "" else f["declared_match"],
            f["diff_kind"], f["pdf_page"], f["printed_page"], f["source_text"],
            f["block_lines"], f["ocr_status"], f["image_verified"], f["review_status"]))
        con.execute("INSERT INTO cipai_form_sources_r2_07 VALUES (?,?,?,?,?)",
                    (fid, 0, f["pdf_page"], f["original_heading"], "heading"))
        for k, (pg_, ln_) in enumerate(f.get("block_list", []), 1):
            con.execute("INSERT INTO cipai_form_sources_r2_07 VALUES (?,?,?,?,?)",
                        (fid, k, pg_, ln_, "pattern"))

    for v in variants:
        con.execute("INSERT INTO cipai_form_variants_r2_07 VALUES (?,?,?,?,?,?,?)",
                    (v["base"], v["derived"], v["relation"], v["evidence"],
                     v["pdf_page"], v["form_id"], v["confidence"]))
    con.commit()

    # 审计表
    for f in forms:
        unk = []
        if not f["pingze_pattern"]:
            unk.append("pingze_pattern")
        if f["declared_match"] is None:
            unk.append("declared_chars")
        if f["stanza_split_source"] == "NULL":
            unk.append("stanza_split")
        if not f["example_work"]:
            unk.append("example_work")
        if not f["notes"]:
            unk.append("special_tone_rules")
        verdict = ("CHECK_REQUIRED" if f["ocr_status"] == "SYMBOL_GAP"
                   else "PARSED_PARTIAL" if unk else "PARSED")
        con.execute("INSERT INTO cipai_audit_r2_07 VALUES (" + ",".join("?" * 15) + ")", (
            f["form_id"],
            1 if f["pdf_page"] else 0, 1 if f["cipai_name"] else 0,
            1 if f["pattern_label"] else 0,
            -1 if f["declared_match"] is None else int(bool(f["declared_match"])),
            0 if f["stanza_split_source"] == "NULL" else 1,
            1 if f["sentence_count"] else 0,
            1 if f["pingze_pattern"] else 0,
            1 if f["rhyme_positions"] else 0,
            1 if f["ann_sequence"] else 0,
            1 if f["notes"] else 0,
            1 if f["example_work"] else 0,
            1 if f["notes"] else 0,
            ",".join(unk), verdict))
    con.commit()
    con.close()

    OUT.write_text(json.dumps(
        {"entities": [{k: v for k, v in e.items() if k != "form_positions"}
                      for e in toc if e.get("flat_pos", -1) >= 0],
         "forms": forms, "variants": variants, "orphans": [flat[i] for i in orphans]},
        ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- 摘要 -----------------------------------------------------------
    print(f"\n词牌 {len([e for e in toc if e.get('flat_pos',-1)>=0])} 个；词格 {len(forms)} 条")
    print("格别:", Counter(f["pattern_type"] for f in forms).most_common())
    print("格标签原文:", Counter(f["pattern_label"] for f in forms).most_common())
    print("韵式:", Counter(f["section_name"] for f in forms).most_common())
    print("字数校验:",
          Counter("MATCH" if f["declared_match"] == 1 else
                  "MISMATCH" if f["declared_match"] == 0 else "NO_DECL"
                  for f in forms).most_common())
    print("差异类型:", Counter(f["diff_kind"] for f in forms).most_common())
    print("OCR:", Counter(f["ocr_status"] for f in forms).most_common())
    print("上下片来源:", Counter(f["stanza_split_source"] for f in forms).most_common())
    print(f"派生调关系 {len(variants)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
