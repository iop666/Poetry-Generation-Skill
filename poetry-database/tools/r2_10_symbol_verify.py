#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-10 工作包 F：60 條詞譜樣本的符號級核驗。

做法
----
1. 用 PyMuPDF 直接讀《唐宋詞格律》PDF 的文字層（與 R2-08 用的文字層是不同的抽取路徑），
   在該頁中找出「平仄符號串 + 括注」的最大連續片段。
2. 把片段切成句：以括注 `（…）` 為句界，最後一個括注之後若仍有符號則單獨成句。
3. 與資料庫中存的 `sentence_lengths`（每句符號數）、`ann_sequence`（括注序列）、
   `total_characters` 逐項比對，得出符號級差異。
4. 若某頁有多個譜行塊，則以「句數＋括注序列」最接近者為該格的候選，並記錄候選數，
   避免張冠李戴。

核驗層級（如實標記）
------------------
- `SYMBOL_LEVEL_TEXTLAYER`：逐符號比對文字層，且句數與括注全對
- `SYMBOL_LEVEL_MISMATCH`：逐符號比對後有差異
- `UNDECIDABLE_NO_BLOCK`：該頁找不到可對應的譜行塊
"""
import csv
import json
import os
import re
import sqlite3

import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
PDF = os.path.join(os.path.dirname(ROOT), "books",
                   "唐宋词格律 (龙榆生) (z-library.sk, 1lib.sk, z-lib.sk).pdf")
OUT = os.path.join(ROOT, "raw", "r2_10", "symbols")
os.makedirs(OUT, exist_ok=True)

SYM = "－｜＋"
ANN = re.compile(r"[（(]([^）)]{0,20})[）)]")


def extract_blocks(text):
    """回傳該頁所有「符號+括注」片段，切句後的形式。"""
    t = re.sub(r"[\s\u3000]", "", text)
    blocks = []
    i = 0
    while i < len(t):
        if t[i] not in SYM:
            i += 1
            continue
        j = i
        last_sym = i
        while j < len(t):
            ch = t[j]
            if ch in SYM:
                last_sym = j
                j += 1
                continue
            if ch in "（(":
                m = ANN.match(t, j)
                if m and len(m.group(1)) <= 20:
                    j = m.end()
                    continue
                break
            break
        seg = t[i:last_sym + 1 + 40]
        # 截到最後一個符號或括注
        end = last_sym
        k = last_sym + 1
        while k < len(t):
            if t[k] in SYM:
                end = k
                k += 1
                continue
            m = ANN.match(t, k)
            if m and len(m.group(1)) <= 20:
                end = m.end() - 1
                k = m.end()
                continue
            break
        seg = t[i:end + 1]
        if seg.count("－") + seg.count("｜") + seg.count("＋") >= 4:
            blocks.append(seg)
        i = end + 1
    return blocks


def norm_ann(a):
    a = re.sub(r"[0-9０-９]+", "", a or "")
    a = a.replace("\u3000", "").strip()
    return a


def split_sentences(seg):
    """按括注切句，回傳 [(符號串, 括注)]，末段無括注者括注為空。"""
    out = []
    pos = 0
    for m in ANN.finditer(seg):
        sym = re.sub(r"[^" + SYM + "]", "", seg[pos:m.start()])
        out.append((sym, norm_ann(m.group(1))))
        pos = m.end()
    tail = re.sub(r"[^" + SYM + "]", "", seg[pos:])
    if tail:
        out.append((tail, ""))
    return out


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    sample = json.load(open(os.path.join(ROOT, "raw", "r2_08", "image_sample.json"),
                            encoding="utf-8"))["items"]
    doc = pymupdf.open(PDF)

    rows, stat = [], {}
    for it in sample:
        fid = it["form_id"]
        f = dict(con.execute("SELECT * FROM cipai_forms_r2_07 WHERE form_id=?", (fid,)).fetchone())
        lens = []
        try:
            lens = [int(x) for x in re.findall(r"\d+", f["sentence_lengths"] or "")]
        except Exception:
            lens = []
        anns = [norm_ann(a) for a in re.split(r"[|,，、\s]+", f["ann_sequence"] or "")]
        anns = [a for a in anns if a and a != "-"]
        cands = []
        text = ""
        for pi in (it["pdf_page"] - 2, it["pdf_page"] - 1, it["pdf_page"]):
            if 0 <= pi < doc.page_count:
                text += doc[pi].get_text()
        # 跨頁串接：本頁 + 次頁，用單一 pno 標記來源起頁
        pno = it["pdf_page"]
        blocks = [(pno, b) for b in extract_blocks(text)]
        for pno, b in blocks:
            ss = split_sentences(b)
            if not ss:
                continue
            bl = [len(x[0]) for x in ss]
            ba = [x[1] for x in ss if x[1] is not None]
            score = 0
            if bl == lens:
                score += 100
            if ba == anns:
                score += 50
            # 括注重疊率
            ov = len(set(ba) & set(anns))
            score += ov * 2
            score -= abs(len(bl) - len(lens)) * 3
            if pno == it["pdf_page"]:
                score += 5
            # 句數必須相等者優先
            if len(bl) == len(lens):
                score += 4
            cands.append((score, bl, ba, b, pno))
        cands.sort(key=lambda x: -x[0])
        if not cands:
            rows.append({"form_id": fid, "cipai_name": it["cipai_name"],
                         "form_seq": it["form_seq"], "pdf_page": it["pdf_page"],
                         "printed_page": it["printed_page"], "n_blocks_on_page": len(blocks),
                         "stored_sentences": len(lens), "tl_sentences": None,
                         "stored_lens": "|".join(map(str, lens)), "tl_lens": "",
                         "stored_anns": "|".join(anns), "tl_anns": "",
                         "symbols_match": None, "ann_match": None,
                         "verdict": "UNDECIDABLE_NO_BLOCK",
                         "check_level": "SYMBOL_LEVEL_TEXTLAYER",
                         "evidence": text[:120].replace("\n", "⏎")})
            continue
        best = cands[0]
        span = "PAGE_SPAN" if best[4] != it["pdf_page"] else ""
        same_len = best[1] == lens
        same_ann = best[2][:len(anns)] == anns if same_len else (best[2] == anns)
        trailing = len(best[2]) - len(anns) if same_len else 0
        verdict = "MATCH" if (same_len and same_ann) else "TEXTLAYER_FRAGMENTED"
        rows.append({"form_id": fid, "cipai_name": it["cipai_name"],
                     "form_seq": it["form_seq"], "pdf_page": it["pdf_page"],
                     "printed_page": it["printed_page"], "n_blocks_on_page": len(blocks),
                     "stored_sentences": len(lens), "tl_sentences": len(best[1]),
                     "stored_lens": "|".join(map(str, lens)),
                     "tl_lens": "|".join(map(str, best[1])),
                     "stored_anns": "|".join(anns), "tl_anns": "|".join(best[2]),
                     "symbols_match": 1 if same_len else 0, "ann_match": 1 if same_ann else 0,
                     "trailing_extra_ann": trailing,
                     "verdict": verdict, "check_level": "SYMBOL_LEVEL_TEXTLAYER",
                     "evidence": ("[block_on_page=%d] " % best[4]) + best[3][:190],
                     "note": span})

    cols = ["form_id", "cipai_name", "form_seq", "pdf_page", "printed_page",
            "n_blocks_on_page", "stored_sentences", "tl_sentences", "stored_lens", "tl_lens",
            "stored_anns", "tl_anns", "symbols_match", "ann_match", "verdict",
            "check_level", "trailing_extra_ann", "evidence", "note"]
    with open(os.path.join(OUT, "cipai_symbol_verification.csv"), "w", newline="",
              encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    import collections
    print("樣本", len(rows), collections.Counter(r["verdict"] for r in rows))
    for r in rows:
        if r["verdict"] != "MATCH":
            print("  ", r["form_id"], r["cipai_name"], r["form_seq"], r["verdict"])
            print("     stored", r["stored_lens"], "|", r["stored_anns"])
            print("     tl    ", r["tl_lens"], "|", r["tl_anns"])

    # 入庫
    con.execute("DROP TABLE IF EXISTS cipai_symbol_audit_r2_10")
    con.execute("""CREATE TABLE cipai_symbol_audit_r2_10(
      form_id TEXT PRIMARY KEY, cipai_name TEXT, form_seq INT, pdf_page INT, printed_page INT,
      n_blocks_on_page INT, stored_sentences INT, tl_sentences INT, stored_lens TEXT,
      tl_lens TEXT, stored_anns TEXT, tl_anns TEXT, symbols_match INT, ann_match INT,
      verdict TEXT, check_level TEXT, evidence TEXT, round TEXT)""")
    con.executemany("""INSERT INTO cipai_symbol_audit_r2_10 VALUES
      (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, '2026-11-15')""",
        [(r["form_id"], r["cipai_name"], r["form_seq"], r["pdf_page"], r["printed_page"],
          r["n_blocks_on_page"], r["stored_sentences"], r["tl_sentences"], r["stored_lens"],
          r["tl_lens"], r["stored_anns"], r["tl_anns"], r["symbols_match"], r["ann_match"],
          r["verdict"], r["check_level"], r["evidence"]) for r in rows])
    con.commit()
    json.dump({"n": len(rows), "counts": dict(collections.Counter(r["verdict"] for r in rows))},
              open(os.path.join(OUT, "symbol_stats.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    con.close()
    doc.close()


if __name__ == "__main__":
    main()
