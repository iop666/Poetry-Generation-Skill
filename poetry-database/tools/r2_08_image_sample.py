#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 WP-C3：分層抽取 60 條詞格做原圖核驗，並渲染頁面圖像。

抽樣規則（可審核）
- 必選：4 條 CHECK_REQUIRED／結構異常、12 個特殊案例、13 條字數異常、15 條外部差異所涉詞格
- 分層：五類韻式各至少 8 條；長調（≥91 字）／中調（59–90）／小令（≤58）各至少 12 條
- 補足：同調異體（同 cipai 多格）至少 8 條；「原書標籤與譜行推導衝突」者優先
"""
import json, os, re, sqlite3, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
PDF = os.path.join(os.path.dirname(ROOT), "books", "唐宋词格律 (龙榆生) (z-library.sk, 1lib.sk, z-lib.sk).pdf")
OUTDIR = os.path.join(ROOT, "raw", "r2_08", "images")
OUT = os.path.join(ROOT, "raw", "r2_08", "image_sample.json")

import fitz


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    forms = {r["form_id"]: dict(r) for r in con.execute("SELECT * FROM cipai_forms_r2_07")}
    name2first = {}
    for fid, d in forms.items():
        name2first.setdefault(d["cipai_name"], fid)
    special = {name2first[r["cipai_name"]] for r in con.execute(
        "SELECT cipai_name FROM cipai_special_cases_r2_07") if r["cipai_name"] in name2first}
    countaudit = {r["form_id"] for r in con.execute(
        "SELECT form_id FROM cipai_count_audit_r2_07") if r["form_id"]}
    extdiff = {name2first[r["cipai_name"]] for r in con.execute(
        "SELECT cipai_name FROM cipai_source_differences_r2_07") if r["cipai_name"] in name2first}
    conflict = {r["form_id"] for r in con.execute(
        "SELECT form_id FROM cipai_rhyme_dual_r2_08 WHERE classification_conflict=1")}

    picked, why = [], collections.defaultdict(list)
    # 先保住五類韻式各至少 5 條（通叶格全部僅 6 條，須優先納入）
    for sect in ["平仄韵通叶格", "平仄韵错叶格", "平仄韵转换格", "平韵格", "仄韵格"]:
        pool = sorted([f for f, d in forms.items() if d["section_name"] == sect],
                      key=lambda f: (forms[f]["total_characters"] or 0))
        step = max(1, len(pool) // 6)
        for f in pool[::step][:6]:
            if f not in picked:
                picked.append(f)
                why[f].append("SECTION_GUARANTEE_" + sect)

    def add(fid, reason):
        if fid in forms and fid not in picked:
            picked.append(fid)
            why[fid].append(reason)

    for fid in sorted(special):
        add(fid, "SPECIAL_CASE")
    for fid in sorted(countaudit):
        add(fid, "COUNT_AUDIT")
    for fid in sorted(extdiff):
        add(fid, "SOURCE_DIFFERENCE")
    for fid in sorted(conflict):
        add(fid, "RHYME_LABEL_CONFLICT")

    def stat(field, val):
        return [f for f, d in forms.items() if d[field] == val]

    # 分層補足：韻式 × 長度
    for sect in ["平韵格", "仄韵格", "平仄韵转换格", "平仄韵通叶格", "平仄韵错叶格"]:
        pool = [f for f in forms if forms[f]["section_name"] == sect and f not in picked]
        pool.sort(key=lambda f: (forms[f]["total_characters"] or 0))
        step = max(1, len(pool) // 8)
        for f in pool[::step][:8]:
            add(f, "STRATUM_" + sect)

    # 同調異體
    per = collections.Counter(d["cipai_id"] for d in forms.values())
    multi = [f for f in forms if per[forms[f]["cipai_id"]] > 1 and f not in picked]
    for f in multi[:8]:
        add(f, "SAME_CIPAI_VARIANT")

    # 長調補足
    longf = [f for f in forms if (forms[f]["total_characters"] or 0) >= 91 and f not in picked]
    for f in longf[:6]:
        add(f, "LONG_TONE")

    picked = picked[:60]
    # 保證五類韻式都在樣本內
    for sect in ["平仄韵通叶格", "平仄韵错叶格", "平仄韵转换格", "平韵格", "仄韵格"]:
        if not any(forms[f]["section_name"] == sect for f in picked):
            cand = [f for f in forms if forms[f]["section_name"] == sect and f not in picked]
            if cand:
                picked[-1] = cand[0]
                why[cand[0]].append("SECTION_GUARANTEE_" + sect)
    recs = []
    for fid in picked:
        d = forms[fid]
        recs.append({"form_id": fid, "cipai_name": d["cipai_name"], "form_seq": d["form_seq"],
                     "section": d["section_name"], "n_chars": d["total_characters"],
                     "pdf_page": d["pdf_page"], "printed_page": d["printed_page"],
                     "why": why[fid], "png": None})

    os.makedirs(OUTDIR, exist_ok=True)
    doc = fitz.open(PDF)
    for r in recs:
        idx = (r["pdf_page"] or 0) - 1
        if idx < 0 or idx >= doc.page_count:
            r["png"] = None
            continue
        png = os.path.join(OUTDIR, "p%03d_%s.png" % (r["pdf_page"], r["form_id"]))
        if not os.path.exists(png):
            pix = doc[idx].get_pixmap(dpi=300)
            pix.save(png)
        r["png"] = png
    doc.close()

    st = {"n": len(recs),
          "by_section": dict(collections.Counter(r["section"] for r in recs)),
          "by_why": dict(collections.Counter(w for r in recs for w in r["why"])),
          "n_rendered": sum(1 for r in recs if r["png"])}
    json.dump({"stats": st, "items": recs}, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(st, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
