#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 WP-C4：抽取《唐宋詞格律》原書例詞，建立 cipai_form_examples_r2_08。

來源：raw/books_native/long_yushsheng_cilv/pages.jsonl（PDF 文字層，270 頁）
體例：
    例 一
    柳色遮楼暗
    ，桐花落砌香
    。画堂开处晚风
    凉
    ，高卷水晶帘额衬斜阳
    。
    ——张泌
每條例詞以「例〔一/二/三〕」起，以「——作者（題）」終。句末標點常置於下一行行首，
故拼接時須把行首標點回貼前句，並去掉行間空白。
"""
import json, os, re, sqlite3, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "raw", "books_native", "long_yushsheng_cilv", "pages.jsonl")
DB = os.path.join(ROOT, "database", "poetry.db")
OUT = os.path.join(ROOT, "raw", "r2_08", "cipai_examples.jsonl")
STAT = os.path.join(ROOT, "raw", "r2_08", "cipai_examples_stats.json")
TODAY = "2026-11-14"

FOOT = re.compile(r"PDF 文件使用.*?fineprint\.cn")
MARK = re.compile(r"例\s*([一二三四五六七八九])?\s*(（[^）]{0,12}）)?\s*\n")
AUTH = re.compile(r"——\s*([^\n（(]{1,12}?)\s*(（([^）]{0,20})）)?\s*\n")
PUNCT = "，。、；：？！“”‘’（）《》…—"


def clean_poem(raw):
    s = FOOT.sub("", raw)
    s = re.sub(r"^\s*\d{1,3}\s*$", "", s, flags=re.M)   # 頁碼行
    s = re.sub(r"[\r\n]+", "", s)
    s = re.sub(r"[ \t\u3000]+", "", s)
    # 頁碼殘留：緊貼標點或行首的 1–4 位阿拉伯數字
    s = re.sub(r"(?<=[，。、；：？！])[0-9]{1,4}(?=[\u4e00-\u9fff])", "", s)
    s = re.sub(r"(?<=[\u4e00-\u9fff])[0-9]{2,4}(?=[\u4e00-\u9fff])", "", s)
    s = re.sub(r"^[0-9]{1,4}(?=[\u4e00-\u9fff])", "", s)
    s = re.sub(r"(?<=[\u4e00-\u9fff])[0-9]{1,4}(?=[，。、；：？！])", "", s)
    return s.strip()


def main():
    pages = [json.loads(l) for l in open(SRC, encoding="utf-8")]
    buf = []
    for p in pages:
        buf.append("\x01%d\x01" % p["page"])
        buf.append(p["text"])
    text = "\n".join(buf)

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    forms = [dict(r) for r in con.execute(
        "SELECT form_id,cipai_name,form_seq,pdf_page,printed_page,example_work,example_author "
        "FROM cipai_forms_r2_07 ORDER BY pdf_page, form_id")]

    # 標題定位：詞牌名獨占一行；格別（定格／格一／變格…）亦獨占一行。
    # 例詞歸屬＝其前最近一個「詞牌標題」，再在其前最近一個「格別標題」對應之 form。
    names = {f["cipai_name"] for f in forms}
    GE_LINE = re.compile(r"^(定\s*格|變\s*格|变\s*格|格[一二三四五六七八九]|別\s*格|别\s*格|又一体|又一體)\s*$")
    events = []
    pos = 0
    for line in text.split("\n"):
        ls = line.strip().replace(" ", "").replace("\u3000", "")
        events.append((pos, "LINE", ls))
        pos += len(line) + 1

    heads = []          # (pos, cipai_name)
    ge_events = []      # (pos, cipai_name, ge_label)
    cur_cipai = None
    for p_, kind, ls in events:
        if kind != "LINE" or not ls:
            continue
        if ls in names:
            cur_cipai = ls
            heads.append((p_, ls))
            continue
        if GE_LINE.match(ls) and cur_cipai:
            ge_events.append((p_, cur_cipai, ls.replace(" ", "")))

    forms_by_cipai = collections.defaultdict(list)
    for f in sorted(forms, key=lambda x: (x["pdf_page"], x["form_seq"])):
        forms_by_cipai[f["cipai_name"]].append(f)

    def form_for(pos_):
        h = [x for x in heads if x[0] < pos_]
        if not h:
            return None
        name = h[-1][1]
        ges = [g for g in ge_events if g[1] == name and g[0] < pos_]
        flist = forms_by_cipai.get(name) or []
        if not flist:
            return None
        if not ges:
            return flist[0]
        idx = len(ges) - 1
        return flist[idx] if idx < len(flist) else flist[-1]

    recs = []
    for m in MARK.finditer(text):
        start = m.end()
        a = AUTH.search(text, start, start + 1200)
        if not a:
            continue
        raw = text[start:a.start()]
        if len(raw) > 1200 or len(raw) < 6:
            continue
        poem = clean_poem(raw)
        if len([c for c in poem if "\u4e00" <= c <= "\u9fff"]) < 8:
            continue
        page = None
        for pm in re.finditer(r"\x01(\d+)\x01", text[:m.start()]):
            page = int(pm.group(1))
        f = form_for(m.start())
        recs.append({
            "cipai_name": f["cipai_name"] if f else None,
            "form_id": f["form_id"] if f else None,
            "form_seq": f["form_seq"] if f else None,
            "example_seq": m.group(1) or "一",
            "example_label": (m.group(2) or "").strip("（）"),
            "author": a.group(1).strip(),
            "author_note": (a.group(3) or "").strip(),
            "text": poem,
            "n_chars": len([c for c in poem if "\u4e00" <= c <= "\u9fff"]),
            "pdf_page": page,
            "printed_page": (page - 15) if page else None,
            "ocr_quality": "TEXT_LAYER",
            "verify_status": "PARSED_NOT_VERIFIED",
            "link_status": "UNLINKED",
            "round": TODAY,
        })

    # 去重（同 form + 同文本）
    seen, uniq = set(), []
    for r in recs:
        k = (r["form_id"], r["text"][:40])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    for i, r in enumerate(uniq, 1):
        r["example_id"] = "EX-%04d" % i

    con.execute("DROP TABLE IF EXISTS cipai_form_examples_r2_08")
    con.execute("""CREATE TABLE cipai_form_examples_r2_08(
        example_id TEXT PRIMARY KEY, form_id TEXT, cipai_name TEXT, form_seq INT,
        example_seq TEXT, example_label TEXT, author TEXT, author_note TEXT, text TEXT,
        n_chars INT, pdf_page INT, printed_page INT, ocr_quality TEXT, link_status TEXT,
        work_id TEXT, match_kind TEXT, match_score REAL, verify_status TEXT, round TEXT)""")
    con.executemany("""INSERT INTO cipai_form_examples_r2_08
        (example_id,form_id,cipai_name,form_seq,example_seq,example_label,author,author_note,
         text,n_chars,pdf_page,printed_page,ocr_quality,link_status,work_id,match_kind,
         match_score,verify_status,round) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    [(r["example_id"], r["form_id"], r["cipai_name"], r["form_seq"],
                      r["example_seq"], r["example_label"], r["author"], r["author_note"],
                      r["text"], r["n_chars"], r["pdf_page"], r["printed_page"],
                      r["ocr_quality"], r["link_status"], None, None, None,
                      r["verify_status"], TODAY) for r in uniq])
    con.commit()
    with open(OUT, "w", encoding="utf-8") as fh:
        for r in uniq:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    per_form = collections.Counter(r["form_id"] for r in uniq)
    st = {
        "n_examples": len(uniq),
        "n_forms_with_example": len([k for k in per_form if k]),
        "n_forms_total": len(forms),
        "n_forms_without_example": [f["form_id"] + " " + f["cipai_name"] for f in forms
                                    if f["form_id"] not in per_form],
        "examples_per_form": dict(collections.Counter(per_form.values())),
        "n_unique_authors": len({r["author"] for r in uniq}),
        "mean_chars": round(sum(r["n_chars"] for r in uniq) / max(1, len(uniq)), 1),
    }
    json.dump(st, open(STAT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in st.items() if k != "n_forms_without_example"},
                     ensure_ascii=False, indent=1))
    print("forms without example:", len(st["n_forms_without_example"]))


if __name__ == "__main__":
    main()
