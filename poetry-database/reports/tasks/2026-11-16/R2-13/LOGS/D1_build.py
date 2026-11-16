#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-13 D1：元曲「只剩科白」疑似集合的独立圈定与逐条判定（只读，不写库）

判据（全部见 LOGS/D_notes.md）：
  A_set_chang = genre='曲' 且 text_raw 含「(…唱)」（中英圆括号均计）
  B_set_title = genre='曲' 且 title_raw 含句读且长度>=17（曲文被刮进标题）
  C_set_short = genre='曲' 且剔除括注后汉字<12（正文残篇）
  审计全集 A = A_set_chang ∪ B_set_title ∪ C_set_short

状态：
  LYRIC_PRESENT  正文即含曲文（含极短曲牌，标 SHORT_SLOT）
  IN_OTHER_FIELD 曲文在 title_raw（可据本地数据复原）
  DIALOGUE_ONLY  正文只有宾白，标题为科白提示（如「…・仁宗云」）
  FRAGMENTARY    正文残缺，短于 12 字且无标题承载曲文
  EMPTY_TEXT     无汉字
  UNKNOWN        无法判定
"""
import sqlite3, re, csv, json, os, collections

BASE = "<PROJECT_ROOT>/poetry-database"
OUT = os.path.join(BASE, "reports/tasks/2026-11-16/R2-13")
DB = os.path.join(BASE, "database/poetry.db")

PAR = re.compile(r"[（(][^）)]{0,40}[）)]")
DM = re.compile(r"[（(][^）)]{0,14}(唱|云|白|科|做|上|下|了|带云|背云)[）)]")
CHANG = re.compile(r"[（(][^）)]*唱[）)]")
CHANG_END = re.compile(r"[（(][^）)]*唱[）)]\s*[。\.]?\s*$")
HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
PUNCT = re.compile(r"[，。；？！、：]")
KB_TAIL = re.compile(r"[\u4e00-\u9fff]{1,4}(云|唱|白|科)$")

def han(s):
    return len(HAN.findall(s or ""))

def split_title(t):
    return t.split("・", 1) if "・" in t else ("", t)

def classify(r):
    t = r["text_raw"] or ""
    title = r["title_raw"] or ""
    out = PAR.sub("", t)
    out_h = han(out)
    qp, tail = split_title(title)
    title_lyric = bool(PUNCT.search(title)) and len(title) >= 17
    ewc = bool(CHANG_END.search(t.rstrip()))
    if han(t) == 0:
        return "EMPTY_TEXT", "text_raw 无汉字"
    if title_lyric:
        kind = "全部曲文" if out_h < 12 else f"曲文头约{len(title)-len(qp)-1}字"
        return "IN_OTHER_FIELD", (f"title_raw 长{len(title)}含句读，{kind}被刮入标题；"
                                  f"title 尾「{tail[-10:]}」→正文「{out[:10]}」；正文余 {out_h} 字")
    if KB_TAIL.search(tail) and out_h < 25:
        return "DIALOGUE_ONLY", f"标题曲牌位为科白提示「{tail}」，正文 {out_h} 字纯宾白，以唱句提示收尾"
    if out_h < 12:
        return "FRAGMENTARY", f"剔除括注后仅 {out_h} 字，正文截断于源"
    if out_h < 25:
        return "LYRIC_PRESENT", f"SHORT_SLOT：仅 {out_h} 字，短曲牌可容，未发现缺文"
    if ewc:
        return "LYRIC_PRESENT", "曲文在正文；句末括注为下一曲的唱句提示（TAIL_CHANG_CUE，非本段缺文）"
    return "LYRIC_PRESENT", "正文含曲文"

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute("SELECT * FROM works WHERE genre='曲' ORDER BY seq")]

    A = [r for r in rows if CHANG.search(r["text_raw"] or "")]
    B = [r for r in rows if PUNCT.search(r["title_raw"] or "") and len(r["title_raw"]) >= 17]
    C = [r for r in rows if han(PAR.sub("", r["text_raw"] or "")) < 12]
    ascii_only = re.compile(r"\([^)]*唱\)")
    n_ascii = sum(1 for r in rows if ascii_only.search(r["text_raw"] or ""))
    ids = {r["work_id"] for r in A} | {r["work_id"] for r in B} | {r["work_id"] for r in C}
    audit = [r for r in rows if r["work_id"] in ids]

    stat = collections.Counter()
    recs = []
    for r in audit:
        st, note = classify(r)
        stat[st] += 1
        t = r["text_raw"] or ""
        qp, tail = split_title(r["title_raw"] or "")
        recs.append({
            "work_id": r["work_id"], "title_raw": r["title_raw"],
            "author_name": r["author_name"], "collection": r["collection"],
            "genre": r["genre"], "source_id": r["source_id"],
            "chapter": r["chapter"] or "", "section": r["section"] or "",
            "char_count": r["char_count"], "line_count": r["line_count"],
            "has_qu_marker": "Y" if ("【" in t or "〔" in t or "幺篇" in t) else "N",
            "has_dialogue_marker": "Y" if DM.search(t) else "N",
            "ends_with_chang_marker": "Y" if CHANG_END.search(t.rstrip()) else "N",
            "text_head_60": t[:60].replace("\n", "⏎"),
            "text_tail_40": t[-40:].replace("\n", "⏎"),
            "status": st,
            "lyric_found_in": ("title_raw" if st == "IN_OTHER_FIELD" else
                               "text_raw" if st == "LYRIC_PRESENT" else "none"),
            "evidence": note,
            "play_or_sanqu": "杂剧/套数(有剧目)" if "・" in (r["title_raw"] or "") else "散曲(无剧目)",
            "title_tail": tail,
        })

    fields = ["work_id", "title_raw", "author_name", "collection", "genre", "source_id",
              "chapter", "section", "char_count", "line_count", "has_qu_marker",
              "has_dialogue_marker", "ends_with_chang_marker", "text_head_60",
              "text_tail_40", "status", "lyric_found_in", "evidence",
              "play_or_sanqu", "title_tail"]
    path = os.path.join(OUT, "YUANQU_2447_MISSING_TEXT_AUDIT.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(recs)

    meta = {
        "yuanqu_total": len(rows),
        "A_chang_any_bracket": len(A),
        "A_chang_ascii_only_r2_12": n_ascii,
        "B_title_lyric": len(B),
        "C_short": len(C),
        "A_union_B_union_C": len(ids),
        "audit_rows": len(recs),
        "status_counts": dict(stat),
    }
    with open(os.path.join(OUT, "LOGS", "D1_counts.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
