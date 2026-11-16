#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 WP-D2：五類韻式各挑 10 首真實作品，計算韻腳、韻部、轉韻，供專題研究。

做法
- 例詞取自 cipai_form_examples_r2_08（原書例詞，已與 works 關聯者優先）。
- 以該格 sentence_lengths 對齊例詞正文，取每個「韻」位的末字為韻腳。
- 以 ph_readings_r2_08(system='regulated_verse') 查韻腳所屬平水韻目與聲調。
- 判定：同一韻目＝同部；韻目變動＝轉韻；平仄交替＝通叶／錯叶線索。
"""
import json, os, re, sqlite3, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
OUT = os.path.join(ROOT, "raw", "r2_08", "rhyme_mode_cases.json")
TODAY = "2026-11-14"
CJK = re.compile(r"[^\u4e00-\u9fff]")


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    from opencc import OpenCC
    cc = OpenCC("s2t")
    rp = collections.defaultdict(set)
    for r in con.execute("SELECT charx, rhyme_group, tone FROM ph_readings_r2_08 "
                         "WHERE system='regulated_verse'"):
        rp[r["charx"]].add((r["rhyme_group"], r["tone"]))
    # 詞韻以《詞林正韻》部為準；平水韻目只用來看分部細節
    crow = collections.defaultdict(set)
    for r in con.execute("SELECT charx, rhyme_group, tone FROM ph_readings_r2_08 "
                         "WHERE system='ci_rhyme'"):
        crow[r["charx"]].add(r["rhyme_group"])

    ex = [dict(r) for r in con.execute("""
        SELECT e.example_id, e.form_id, e.cipai_name, e.author, e.text, e.n_chars,
               f.section_name, f.sentence_lengths, f.ann_sequence, f.source_text,
               f.total_characters
        FROM cipai_form_examples_r2_08 e JOIN cipai_forms_r2_07 f ON e.form_id=f.form_id
        WHERE e.n_chars >= 20""")]

    cases = collections.defaultdict(list)
    for e in ex:
        # 韻位：由 ann_sequence 得韻句序
        anns = str(e["ann_sequence"] or "").split()
        lens = [int(x) for x in str(e["sentence_lengths"] or "").split(",") if x.isdigit()]
        if not anns or len(anns) != len(lens):
            continue
        text = CJK.sub("", e["text"])
        if abs(len(text) - sum(lens)) > 2:
            continue
        pos, idx, feet = 0, 0, []
        ok = True
        for L, a in zip(lens, anns):
            seg = text[pos:pos + L]
            pos += L
            if not seg:
                ok = False
                break
            if ("韵" in a) or ("叶" in a) or ("叠" in a):
                feet.append({"sent": idx, "char": seg[-1], "ann": a})
            idx += 1
        if not ok or len(feet) < 3:
            continue
        groups, unknown = [], 0
        for f in feet:
            g = rp.get(f["char"])
            if not g:
                alt = cc.convert(f["char"])
                if alt != f["char"]:
                    g = rp.get(alt)
                    if g:
                        f["lookup_via"] = "SIMP2TRAD"
            if not g:
                f["rhyme_group"] = None
                unknown += 1
            else:
                f["rhyme_group"] = sorted({x[0] for x in g})[0]
                f["tone_pingshui"] = sorted({x[1] for x in g})[0]
            cg = crow.get(f["char"])
            if not cg:
                for alt in {cc.convert(f["char"])}:
                    if alt != f["char"] and alt in crow:
                        cg = crow[alt]
                        f["lookup_via"] = "SIMP2TRAD"
                        break
            f["ci_bu_cands"] = sorted(cg) if cg else []
            f["ci_bu"] = f["ci_bu_cands"][0] if f["ci_bu_cands"] else None
            groups.append(f["ci_bu"])
        # 多音/多部字：按全篇多数部消歧（記錄消歧次數，不靜默）
        cand_all = collections.Counter()
        for f in feet:
            for c in f.get("ci_bu_cands", []):
                cand_all[c] += 1
        n_dis = 0
        if cand_all:
            mode_bu = cand_all.most_common(1)[0][0]
            for f in feet:
                cs = f.get("ci_bu_cands", [])
                if len(cs) > 1 and mode_bu in cs:
                    f["ci_bu"] = mode_bu
                    f["disambiguated"] = 1
                    n_dis += 1
        groups = [f.get("ci_bu") for f in feet]
        known = [g for g in groups if g and not str(g).startswith("AMBIGUOUS")]
        changes = sum(1 for i in range(1, len(groups)) if groups[i] and groups[i - 1]
                      and groups[i] != groups[i - 1]
                      and not groups[i].startswith("AMBIGUOUS")
                      and not groups[i - 1].startswith("AMBIGUOUS"))
        cases[e["section_name"]].append({
            "example_id": e["example_id"], "form_id": e["form_id"],
            "cipai_name": e["cipai_name"], "author": e["author"],
            "text": e["text"], "n_chars": e["n_chars"],
            "n_feet": len(feet), "feet": feet,
            "rhyme_groups": groups, "n_group_changes": changes,
            "n_unknown": unknown, "n_distinct_groups": len(set(known)),
            "ci_bu_seq": [f.get("ci_bu") for f in feet],
            "n_disambiguated": n_dis,
            "n_multi_read_feet": sum(1 for f in feet if len(f.get("ci_bu_cands") or []) > 1),
        })

    PREF = {
        "平韵格": ["浣溪沙", "水调歌头", "一剪梅", "临江仙", "满庭芳", "扬州慢", "江城子",
                 "望海潮", "八声甘州", "风入松", "鹧鸪天", "木兰花慢", "高阳台", "唐多令"],
        "仄韵格": ["蝶恋花", "念奴娇", "满江红", "雨霖铃", "声声慢", "青玉案", "摸鱼儿",
                 "贺新郎", "醉花阴", "卜算子", "踏莎行", "齐天乐", "暗香", "疏影"],
        "平仄韵转换格": ["虞美人", "菩萨蛮", "清平乐", "更漏子", "调笑令", "昭君怨", "河传",
                     "喜迁莺", "减字木兰花", "怨王孙"],
        "平仄韵通叶格": ["西江月", "醉翁操", "哨遍", "戚氏", "渡江云", "六州歌头"],
        "平仄韵错叶格": ["定风波", "诉衷情", "荷叶杯", "相见欢", "酒泉子", "上行杯",
                     "最高楼", "定西番", "南乡子", "蕃女怨"],
    }
    picked = {}
    for sec, lst in cases.items():
        prefs = PREF.get(sec, [])
        def key(c):
            nm = c["cipai_name"]
            pr = prefs.index(nm) if nm in prefs else 99
            good = 0 if 6 <= c["n_feet"] <= 14 else 1
            return (pr, good, c["n_unknown"])
        lst.sort(key=key)
        seen, sel = set(), []
        for c in lst:
            if c["cipai_name"] in seen:
                continue
            seen.add(c["cipai_name"])
            sel.append(c)
            if len(sel) == 10:
                break
        for c in lst:
            if len(sel) >= 10:
                break
            if c not in sel:
                sel.append(c)
        picked[sec] = sel[:10]
    out = {"generated": TODAY,
           "note": "韻腳由譜行句長對齊例詞正文取得；韻部據平水韻字表回查，未收字記 None。",
           "by_section": {k: len(v) for k, v in picked.items()},
           "cases": picked}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k, v in picked.items():
        print(k, len(v), "| 例:",
              [(c["cipai_name"], c["n_feet"], c["n_distinct_groups"], c["n_group_changes"])
               for c in v[:4]])


if __name__ == "__main__":
    main()
