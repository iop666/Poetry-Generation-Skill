#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 WP-C1/C2：196 條詞格結構審計 + 韻式「原書標籤 / 譜行推導」雙軌。

回應 R2-07 審核第 ④ 點：
  不得規定「標籤永遠優先」。本輪分開保存
    source_rhyme_label      原書分類（第一類平韻格…第五類錯葉格）
    observed_rhyme_behavior 由譜行標注（平韻／仄韻／換／轉／叶）推導
    classification_conflict 兩者是否衝突
  並新增 rhyme_evidence_level 說明推導的證據等級。

推導規則（龍榆生《唐宋詞格律》凡例：依韻腳分類五格）
  R1 無「換／轉」標注且韻腳全平           → 平韻
  R2 無「換／轉」標注且韻腳全仄           → 仄韻
  R3 無「換／轉」標注而平仄韻腳並見       → 平仄通叶（同部互叶）
  R4 有 1 次「換／轉」                    → 平仄轉換
  R5 有 ≥2 次「換／轉」                   → 平仄錯叶（多次轉韻）
  R6 韻腳聲調無法判定                     → UNKNOWN
"""
import json, os, re, sqlite3, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
OUT = os.path.join(ROOT, "raw", "r2_08", "cipai_audit.json")
TODAY = "2026-11-14"

LABEL2CLASS = {
    "平韵格": "平韻", "仄韵格": "仄韻",
    "平仄韵转换格": "平仄轉換", "平仄韵通叶格": "平仄通叶", "平仄韵错叶格": "平仄錯叶",
}


def parse_anns(source_text):
    """把譜行原文拆成 (句子序, 標注) 序列。"""
    if not source_text:
        return []
    parts = re.split(r"([（(][^）)]*[）)])", source_text)
    out, idx = [], 0
    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = re.fullmatch(r"[（(]([^）)]*)[）)]", p)
        if m:
            out.append((idx, m.group(1).strip()))
        else:
            # 一段譜行可能含多句，以空白或逗號斷句
            segs = [s for s in re.split(r"[\s　]+", p) if s]
            idx += max(1, len(segs))
    return out


def rhyme_profile(source_text, ann_sequence):
    """由譜行推出每一韻位及其聲調。

    譜行體例：「｜｜－－（平韵）＋－＋｜｜－－（叶平）…」
    每句平仄符號在前，括注在後；韻位即該句末字，其聲調由末符號決定
    （－平、｜仄、＋可平可仄→不判定）。括注中的「平韻／仄韻／換仄韻」
    僅作校驗與換韻計數，不用來覆蓋符號。
    """
    prof = {"marks": [], "tones": [], "symbol_tones": [], "n_changes": 0,
            "tone_source": []}
    if not source_text:
        return {"marks": [], "tones": [], "n_marks": 0, "n_changes": 0,
                "n_unknown_tone": 0, "symbol_tones": [], "tone_source": []}
    parts = re.split(r"([（(][^）)]*[）)])", source_text)
    pend = ""
    for p in parts:
        if not p:
            continue
        m = re.fullmatch(r"[（(]([^）)]*)[）)]", p.strip())
        if not m:
            pend += p
            continue
        ann = m.group(1).strip()
        if "换" in ann or "轉" in ann or "转" in ann:
            prof["n_changes"] += 1
        if not (("韵" in ann) or ("韻" in ann) or ("叶" in ann) or ("葉" in ann)
                or ("叠" in ann) or ("疊" in ann)):
            pend = ""
            continue
        sym = None
        for ch in reversed(re.sub(r"[\s　]", "", pend)):
            if ch in "－｜＋":
                sym = ch
                break
        symtone = {"－": "平", "｜": "仄", "＋": None}.get(sym)
        anntone = "平" if "平" in ann else ("仄" if "仄" in ann else None)
        tone = symtone if symtone else anntone
        prof["marks"].append(ann)
        prof["tones"].append(tone)
        prof["symbol_tones"].append(sym)
        prof["tone_source"].append("SYMBOL" if symtone else ("ANNOTATION" if anntone else "UNKNOWN"))
        pend = ""
    return {"marks": prof["marks"], "tones": prof["tones"], "n_marks": len(prof["marks"]),
            "n_changes": prof["n_changes"],
            "n_unknown_tone": sum(1 for t in prof["tones"] if t is None),
            "symbol_tones": prof["symbol_tones"], "tone_source": prof["tone_source"]}


def observe(prof):
    t = [x for x in prof["tones"] if x]
    if not t:
        return "UNKNOWN", "R6_NO_TONE"
    ch = prof["n_changes"]
    if ch == 0:
        if set(t) == {"平"}:
            return "平韻", "R1_ALL_PING"
        if set(t) == {"仄"}:
            return "仄韻", "R2_ALL_ZE"
        return "平仄通叶", "R3_MIXED_NO_CHANGE"
    if ch == 1:
        return "平仄轉換", "R4_ONE_CHANGE"
    return "平仄錯叶", "R5_MULTI_CHANGE"


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    forms = [dict(r) for r in con.execute("SELECT * FROM cipai_forms_r2_07 ORDER BY form_id")]

    dual, audit = [], []
    for f in forms:
        prof = rhyme_profile(f["source_text"], f["ann_sequence"])
        obs, rule = observe(prof)
        label = LABEL2CLASS.get(f["section_name"], "UNKNOWN")
        conflict = 0 if obs == "UNKNOWN" else int(obs != label)
        # 結構檢查
        st = (f["source_text"] or "")
        n_sent_src = len(re.findall(r"[（(][^）)]*[）)]", st)) or None
        checks = {
            "page_ok": int(bool(f["pdf_page"] and f["printed_page"] == f["pdf_page"] - 15)),
            "name_ok": int(bool(f["cipai_name"])),
            "label_ok": int(bool(f["pattern_label"])),
            "chars_ok": int(bool(f["total_characters"])),
            "stanza_ok": int(bool(f["stanza_structure"]) and "UNKNOWN" not in (f["stanza_structure"] or "")),
            "sentence_ok": int(bool(f["sentence_count"]) and bool(f["sentence_lengths"])),
            "pingze_ok": int(bool(f["pingze_pattern"])),
            "rhyme_ok": int(prof["n_marks"] > 0),
            "ann_ok": int(prof["n_marks"] > 0 and prof["n_chars"] if False else prof["n_marks"] > 0),
            "annotation_count_ok": int(n_sent_src is not None and n_sent_src == f["sentence_count"]),
            "example_ok": int(bool(f["example_work"])),
            "note_ok": int(bool(f["pattern_note"])),
            "source_text_ok": int(len(st) >= 10),
        }
        unknown_fields = [k for k, v in checks.items() if v == 0]
        if checks["source_text_ok"] and checks["rhyme_ok"] and checks["pingze_ok"] and checks["sentence_ok"]:
            verdict = "STRUCT_OK" if checks["annotation_count_ok"] else "STRUCT_PARTIAL"
        else:
            verdict = "CHECK_REQUIRED"
        audit.append({"form_id": f["form_id"], "cipai_name": f["cipai_name"],
                      **checks, "unknown_fields": ",".join(unknown_fields),
                      "verdict": verdict, "n_sent_src": n_sent_src,
                      "sentence_count": f["sentence_count"]})
        dual.append({
            "form_id": f["form_id"], "cipai_name": f["cipai_name"],
            "form_seq": f["form_seq"],
            "source_rhyme_label": f["section_name"],
            "source_rhyme_label_class": label,
            "source_declared_rhyme": f["declared_rhyme"],
            "observed_rhyme_behavior": obs,
            "derive_rule": rule,
            "n_rhyme_marks": prof["n_marks"],
            "n_change_events": prof["n_changes"],
            "n_tone_unknown": prof["n_unknown_tone"],
            "rhyme_tone_sequence": "".join(x or "?" for x in prof["tones"]),
            "classification_conflict": conflict,
            "rhyme_evidence_level": "PATTERN_ANNOTATION_DERIVED",
            "same_rhyme_group_verified": 0,
            "note": "",
        })

    # 同調多體口徑
    per = collections.Counter(x["cipai_id"] for x in forms)
    dist = collections.Counter(per.values())
    stats = {
        "n_forms": len(forms),
        "n_entities": len(per),
        "n_multi_form_entities": sum(1 for v in per.values() if v >= 2),
        "form_count_distribution": dict(sorted(dist.items())),
        "section_distribution": dict(collections.Counter(f["section_name"] for f in forms)),
        "audit_verdict": dict(collections.Counter(a["verdict"] for a in audit)),
        "conflicts": sum(d["classification_conflict"] for d in dual),
        "conflict_pairs": dict(collections.Counter(
            f'{d["source_rhyme_label_class"]}->{d["observed_rhyme_behavior"]}'
            for d in dual if d["classification_conflict"])),
        "observed_distribution": dict(collections.Counter(d["observed_rhyme_behavior"] for d in dual)),
        "no_rhyme_mark_forms": [d["form_id"] for d in dual if d["n_rhyme_marks"] == 0],
        "annotation_count_mismatch": [a["form_id"] for a in audit if not a["annotation_count_ok"]],
    }

    con.execute("DROP TABLE IF EXISTS cipai_audit2_r2_08")
    con.execute("""CREATE TABLE cipai_audit2_r2_08(
        form_id TEXT PRIMARY KEY, cipai_name TEXT, page_ok INT, name_ok INT, label_ok INT,
        chars_ok INT, stanza_ok INT, sentence_ok INT, pingze_ok INT, rhyme_ok INT, ann_ok INT,
        annotation_count_ok INT, example_ok INT, note_ok INT, source_text_ok INT,
        unknown_fields TEXT, verdict TEXT, n_sent_src INT, sentence_count INT, round TEXT)""")
    con.executemany("""INSERT INTO cipai_audit2_r2_08 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    [(a["form_id"], a["cipai_name"], a["page_ok"], a["name_ok"], a["label_ok"],
                      a["chars_ok"], a["stanza_ok"], a["sentence_ok"], a["pingze_ok"], a["rhyme_ok"],
                      a["ann_ok"], a["annotation_count_ok"], a["example_ok"], a["note_ok"],
                      a["source_text_ok"], a["unknown_fields"], a["verdict"], a["n_sent_src"],
                      a["sentence_count"], TODAY) for a in audit])
    con.execute("DROP TABLE IF EXISTS cipai_rhyme_dual_r2_08")
    con.execute("""CREATE TABLE cipai_rhyme_dual_r2_08(
        form_id TEXT PRIMARY KEY, cipai_name TEXT, form_seq INT, source_rhyme_label TEXT,
        source_rhyme_label_class TEXT, source_declared_rhyme TEXT, observed_rhyme_behavior TEXT,
        derive_rule TEXT, n_rhyme_marks INT, n_change_events INT, n_tone_unknown INT,
        rhyme_tone_sequence TEXT, classification_conflict INT, rhyme_evidence_level TEXT,
        same_rhyme_group_verified INT, note TEXT, round TEXT)""")
    con.executemany("""INSERT INTO cipai_rhyme_dual_r2_08 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    [(d["form_id"], d["cipai_name"], d["form_seq"], d["source_rhyme_label"],
                      d["source_rhyme_label_class"], d["source_declared_rhyme"],
                      d["observed_rhyme_behavior"], d["derive_rule"], d["n_rhyme_marks"],
                      d["n_change_events"], d["n_tone_unknown"], d["rhyme_tone_sequence"],
                      d["classification_conflict"], d["rhyme_evidence_level"],
                      d["same_rhyme_group_verified"], d["note"], TODAY) for d in dual])
    con.commit()
    json.dump({"stats": stats, "dual": dual, "audit": audit},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
