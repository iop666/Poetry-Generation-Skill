#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-14 / C4：372 条被 `len(txt_norm)<8` 过滤记录的逐条审计。

方法：用与 tools/parse.py 完全相同的抽取与归一函数重跑 raw JSON，
      按导入顺序对齐（113 与 114 两处已验证 seq 连续），
      于是「被跳过」的 372 条可精确定位到 JSON 下标，无一条需要猜测。
输出：
  YUANQU_372_IMPORT_FILTER_AUDIT.csv
  LOGS/C4_counts.json
"""
import collections
import csv
import datetime
import json
import os
import re
import sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
DB = os.path.join(BASE, "database", "poetry.db")
SRC = os.path.join(BASE, "raw", "poetry", "yuanqu", "yuanqu.json")
OUT = os.path.join(BASE, "reports", "tasks", "2026-11-16", "R2-14")
LOG = os.path.join(OUT, "LOGS")
TS = datetime.datetime.now().isoformat(timespec="seconds")

HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002ffff]")
PUNCT = re.compile(r"[，。；：、！？,.;:!?（）()《》〈〉“”‘’\"'—…·\s]")
BRACKET_NOTE = re.compile(r"[（(][^）)]{0,20}(?:一作|又作|某作)[^）)]{0,20}[）)]")
INLINE_NOTE = re.compile(r"([\u4e00-\u9fff])一作[\u4e00-\u9fff]{1,2}")
JUDOU = set("，。；？！、：")


def strip_notes(s):
    s = BRACKET_NOTE.sub("", s)
    prev = None
    while prev != s:
        prev = s
        s = INLINE_NOTE.sub(r"\1", s)
    return s


def norm_text(lines):
    out = []
    for ln in lines:
        s = PUNCT.sub("", ln)
        s = "".join(ch for ch in s if HAN.match(ch))
        if s:
            out.append(s)
    return strip_notes("".join(out))


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    conn = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
    kept_work_ids = [r[0] for r in conn.execute(
        "SELECT work_id FROM works WHERE collection='yuanqu' ORDER BY seq")]

    skipped = []
    kept_i = 0
    for i, t in enumerate(data):
        title = t.get("title") or t.get("rhythmic") or t.get("chapter") or ""
        lines = (t.get("paragraphs") or t.get("content") or t.get("verse")
                 or t.get("para") or [])
        if isinstance(lines, str):
            lines = [lines]
        lines = [l for l in lines if l and str(l).strip()]
        raw = "\n".join(lines)
        tn = norm_text(lines)
        if len(tn) < 8:
            skipped.append({"idx": i, "title": title, "author": t.get("author") or "",
                            "raw": raw, "norm_len": len(tn),
                            "prev_wid": kept_work_ids[kept_i - 1] if kept_i else ""})
        else:
            kept_i += 1

    rows = []
    stats = collections.Counter()
    for s in skipped:
        title, raw = s["title"], s["raw"]
        has_jd = bool(JUDOU & set(title))
        body_han = len([c for c in BRACKET_NOTE.sub("", raw)
                        if HAN.match(c)])
        # 题内含曲文的判据：标题带句读，且去曲牌/宫调后仍有 >=8 汉字
        tail = title.split("・")[-1] if "・" in title else title
        tail_han = len([c for c in tail if HAN.match(c)])
        title_lyric = has_jd and tail_han >= 8
        if title_lyric and body_han:
            rec = "Y_TITLE+BODY"
        elif title_lyric:
            rec = "Y_TITLE_ONLY"
        else:
            rec = "N"
        valid = "Y" if (has_jd and tail_han >= 8) or body_han >= 8 else "N"
        if not title_lyric and not raw.strip():
            note = "title/paragraphs 均无曲文，源即空记录"
        elif not title_lyric:
            note = "title 为曲牌名或残句，paragraphs 不足 8 字，源即残篇"
        elif not body_han:
            note = ("曲文仅在 title（约 %d 字），paragraphs 全空；"
                    "标题只到硬切点，其后是否还有曲文无法判定" % len(title))
        else:
            note = "曲文头在 title，余文 %d 字在 paragraphs，可直接拼接" % body_han
        stats[rec] += 1
        stats["valid:" + valid] += 1
        rows.append([f"json#{s['idx']}", "CP-YUANQU", "raw/poetry/yuanqu/yuanqu.json",
                     "Y", title, len(raw), raw[:60].replace("\n", "⏎"),
                     f"len(txt_norm)={s['norm_len']}<8", valid, rec, note])

    p = os.path.join(OUT, "YUANQU_372_IMPORT_FILTER_AUDIT.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["work_id_or_index", "source_id", "source_file", "in_json", "title",
                    "text_len_in_source", "text_in_source_head", "filtered_reason",
                    "is_valid_work", "recoverable", "note"])
        w.writerows(rows)

    with open(os.path.join(LOG, "C4_counts.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_at": TS, "n_json": len(data), "n_skipped": len(skipped),
                   "n_kept": len(kept_work_ids), "stats": dict(stats),
                   "align_ok": len(data) - len(skipped) == len(kept_work_ids)},
                  f, ensure_ascii=False, indent=2)
    print(json.dumps(dict(stats), ensure_ascii=False, indent=2))
    print("json", len(data), "skipped", len(skipped), "kept", len(kept_work_ids))


if __name__ == "__main__":
    main()
