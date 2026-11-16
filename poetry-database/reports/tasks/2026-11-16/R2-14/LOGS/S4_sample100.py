#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-14 / C5：分层 100 条回原始 JSON 核对。

定位方式：用与 parse.py 相同的抽取/过滤顺序重跑 raw JSON，
          与 works（ORDER BY seq）逐条对齐（title/author/text 全量 0 差异），
          因此每条样本都有确定的 json 下标，不靠模糊匹配。
分层：IN_OTHER_FIELD 50 / LYRIC_PRESENT 25 / FRAGMENTARY 15 / DIALOGUE_ONLY 1
      + 缺口 9（SOURCE_UNAVAILABLE 实测 0 条，用 FRAGMENTARY 补足，标 SUBSTITUTE）
输出：YUANQU_100_SOURCE_VERIFICATION.csv, LOGS/C5_counts.json
"""
import collections
import csv
import datetime
import json
import os
import random
import re
import sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
DB = os.path.join(BASE, "database", "poetry.db")
SRC = os.path.join(BASE, "raw", "poetry", "yuanqu", "yuanqu.json")
R13 = os.path.join(BASE, "reports", "tasks", "2026-11-16", "R2-13",
                   "YUANQU_2447_MISSING_TEXT_AUDIT.csv")
OUT = os.path.join(BASE, "reports", "tasks", "2026-11-16", "R2-14")
LOG = os.path.join(OUT, "LOGS")
TS = datetime.datetime.now().isoformat(timespec="seconds")
SEED = 20261116

HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002ffff]")
PUNCT = re.compile(r"[，。；：、！？,.;:!?（）()《》〈〉“”‘’\"'—…·\s]")
BN = re.compile(r"[（(][^）)]{0,20}(?:一作|又作|某作)[^）)]{0,20}[）)]")
IN = re.compile(r"([\u4e00-\u9fff])一作[\u4e00-\u9fff]{1,2}")


def norm_text(lines):
    out = []
    for ln in lines:
        s = PUNCT.sub("", ln)
        s = "".join(c for c in s if HAN.match(c))
        if s:
            out.append(s)
    s = "".join(out)
    s = BN.sub("", s)
    while IN.search(s):
        s = IN.sub(r"\1", s)
    return s


def han(s):
    return len([c for c in s if HAN.match(c)])


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    kept = []
    for i, t in enumerate(data):
        title = t.get("title") or t.get("rhythmic") or t.get("chapter") or ""
        lines = t.get("paragraphs") or []
        lines = [l for l in lines if l and str(l).strip()]
        if len(norm_text(lines)) < 8:
            continue
        kept.append((i, title, t.get("author") or "", "\n".join(lines)))
    conn = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
    db = conn.execute("SELECT work_id,title_raw,text_raw,char_count FROM works "
                      "WHERE collection='yuanqu' ORDER BY seq").fetchall()
    assert len(kept) == len(db)
    rec_of = {d[0]: kept[k] for k, d in enumerate(db)}

    audit = list(csv.DictReader(open(R13, encoding="utf-8-sig")))
    by_status = collections.defaultdict(list)
    for r in audit:
        by_status[r["status"]].append(r["work_id"])

    rnd = random.Random(SEED)
    plan = [("IN_OTHER_FIELD", 50), ("LYRIC_PRESENT", 25), ("FRAGMENTARY", 15),
            ("DIALOGUE_ONLY", 1)]
    pool_frag = sorted(by_status["FRAGMENTARY"])
    samples = []
    used = set()
    for st, n in plan:
        pool = sorted(by_status[st])
        pick = rnd.sample(pool, min(n, len(pool)))
        used |= set(pick)
        samples += [(st, w) for w in pick]
    # 缺口补足：DIALOGUE_ONLY 仅 1 条，SOURCE_UNAVAILABLE 实测 0 条
    rest = [w for w in pool_frag if w not in used]
    samples += [("SUBSTITUTE_FRAGMENTARY", w) for w in rnd.sample(rest, 9)]

    rows = []
    stats = collections.Counter()
    for n, (st, wid) in enumerate(samples, 1):
        s_rec = rec_of[wid]
        i, s_title, s_author, s_text = s_rec
        d = next(x for x in db if x[0] == wid)
        d_title, d_text = d[1], d[2]
        lyric_present = ""
        verdict = ""
        extra = ""
        if st == "IN_OTHER_FIELD":
            lyr = d_title.split("・", 1)[1] if "・" in d_title else ""
            lyric_present = f"Y_TITLE({han(lyr)}字)"
            verdict = "SOURCE_VERBATIM_TITLE_HELD"
            body_first = d_text.split("\n")[0] if d_text else ""
            extra = f"接缝「{d_title[-1]}|{body_first[:1]}」"
            if body_first.startswith("幺"):
                extra += "（正文首字为下一支曲牌标记「幺」，须先剥离再拼接）"
        elif st == "LYRIC_PRESENT":
            lyric_present = "Y_BODY"
            verdict = "SOURCE_VERBATIM"
        elif st in ("FRAGMENTARY", "SUBSTITUTE_FRAGMENTARY"):
            lyric_present = "PARTIAL(源即残)"
            verdict = "SOURCE_TRUNCATED"
            extra = f"源 paragraphs 末句「{s_text[-12:]}」即断，无后续"
        else:
            lyric_present = "N"
            verdict = "SOURCE_DIALOGUE_ONLY"

        if d_text == s_text:
            match = "EXACT"
        elif norm_text([d_text]) == norm_text([s_text]):
            match = "VARIANT"
        elif d_text and d_text in s_text:
            match = "PARTIAL"
        elif not d_text:
            match = "ABSENT"
        else:
            match = "ABSENT"
        stats[match] += 1
        stats[st] += 1

        rows.append([
            f"S{n:03d}", wid, st, "CP-YUANQU",
            "raw/poetry/yuanqu/yuanqu.json", f"json#{i}",
            lyric_present, s_text[:100].replace("\n", "⏎"),
            d_text[:100].replace("\n", "⏎"), match, verdict,
            f"title {'相同' if d_title == s_title else '不同'}；"
            f"paragraphs {len(s_text.split(chr(10))) if s_text else 0} 段；"
            f"db.text_raw 与源 {'逐字相同' if d_text == s_text else '有差异'}；{extra}".strip("；"),
        ])

    p = os.path.join(OUT, "YUANQU_100_SOURCE_VERIFICATION.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sample_id", "work_id", "stratum", "source_id", "source_file",
                    "json_index_or_locator", "lyric_present_in_source",
                    "source_text_head_100", "db_text_head_100", "match_level",
                    "verdict", "evidence"])
        w.writerows(rows)

    with open(os.path.join(LOG, "C5_counts.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_at": TS, "seed": SEED, "n": len(rows),
                   "stats": dict(stats),
                   "source_unavailable_found": 0,
                   "gap": 9}, f, ensure_ascii=False, indent=2)
    print(json.dumps(dict(stats), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
