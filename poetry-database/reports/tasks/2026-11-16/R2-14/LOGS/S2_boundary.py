#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-14 / C2：1,729 条 IN_OTHER_FIELD 的字段边界全量审计。

判定原则（与任务书一致）：
  · 不按 32 字硬切。边界取「・」分隔符：`曲牌[・南/北]・曲文`
  · 曲牌词表从同一份数据的「无句读标题」自建（1,406 个），用于判断 ・ 前是否真为曲牌
  · 接缝检验：title 尾部与 text_raw 首部的最长重叠（重字＝拼接需去重）
  · 正文是否已含部分曲文：overlap>0 即说明正文里重复了标题尾部的字
只读库，不写库。
输出：
  YUANQU_1729_FIELD_BOUNDARY_AUDIT.csv
  LOGS/C2_stats.json
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
OUT = os.path.join(BASE, "reports", "tasks", "2026-11-16", "R2-14")
LOG = os.path.join(OUT, "LOGS")
TS = datetime.datetime.now().isoformat(timespec="seconds")

JUDOU = set("，。；？！、：")
END = set("，。；？！、：”’）》」』")
HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002ffff]")
BR = re.compile(r"[（(][^）)]*[）)]")
CUE = re.compile(r"[（(][^）)]{0,14}(?:唱|云|白|科|做|上|下|了)[）)]")
OTHER_FIELDS = ["chapter", "section", "cipai", "volume", "juan", "record_locator",
                "quality_grade", "crosscheck_result", "author_canonical",
                "crosscheck_status", "variant_group", "title_norm"]


def han(s):
    return len([ch for ch in s if HAN.match(ch)])


def clean(s):
    return "".join(ch for ch in s if HAN.match(ch))


def build_vocab(rows):
    """从「无句读标题」自建曲牌词表。"""
    vocab = collections.Counter()
    for t in rows:
        if JUDOU & set(t):
            continue
        s = t
        if "/" in s:
            s = s.split("/")[-1]
        elif "・" in s:
            s = s.split("・")[-1]
        s = s.strip()
        if s and len(s) <= 12:
            vocab[s] += 1
    return vocab


def main():
    conn = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
    cols = "work_id,title_raw,text_raw,char_count,line_count," + ",".join(OTHER_FIELDS)
    rows = conn.execute(f"SELECT {cols} FROM works WHERE genre='曲'").fetchall()
    vocab = build_vocab([r[1] for r in rows])

    recs = [r for r in rows if (JUDOU & set(r[1])) and len(r[1]) >= 17]
    stats = collections.Counter()
    out_rows = []
    for r in recs:
        (wid, title, text, cc, lc) = r[:5]
        others = dict(zip(OTHER_FIELDS, r[5:]))
        tlen = len(title)

        # ---- 边界定位 ----
        method = "NONE"
        head = None
        lyric = title
        if "・" in title:
            parts = title.split("・")
            if len(parts) >= 3 and parts[1] in ("南", "北"):
                method = "DOT_SECOND_NANBEI"
                head = parts[0] + "・" + parts[1]
                lyric = "・".join(parts[2:])
                head_core = parts[0]
            else:
                method = "DOT_FIRST"
                head = parts[0]
                head_core = parts[0]
                lyric = "・".join(parts[1:])
            if head_core == "":
                method = "DOT_ONLY_EMPTY_HEAD"
                head_core = ""
        else:
            head_core = None

        # ---- 接缝重叠 ----
        lyr_h = clean(lyric)
        body_h = clean(BR.sub("", text))
        body_first = clean(text.split("\n")[0])
        ov = 0
        for k in range(min(len(lyr_h), 8), 0, -1):
            if lyr_h[-k:] == body_first[:k]:
                ov = k
                break

        # ---- 置信度 ----
        if method == "NONE":
            conf = "LOW(no_separator)"
        elif method == "DOT_ONLY_EMPTY_HEAD":
            conf = "LOW(qupai_missing)"
            if text.lstrip().startswith("幺"):
                conf = "LOW(qupai_missing;body_leading_幺=下一支曲牌标记)"
        elif head_core in vocab:
            conf = "HIGH(qupai_in_vocab)"
        elif head_core and not (JUDOU & set(head_core)) and len(head_core) <= 12:
            conf = "MEDIUM(qupai_not_in_vocab)"
        else:
            conf = "LOW(head_not_meta)"
        conf += f";ov={ov}" if ov < 2 else f";ov={ov}(疑重字)"

        # ---- 32 字硬切 ----
        if tlen == 32:
            trunc = "Y_32"
        elif tlen == 33:
            trunc = "Y_33"
        else:
            trunc = f"N_len{tlen}"

        # ---- 其他字段是否含曲文 ----
        # 只看可能承载正文的字段；quality_grade/author_canonical 是等级标签与作者名，
        # title_norm/text_norm 是 title_raw/text_raw 的派生副本，单列说明。
        LYRIC_CAND = ["chapter", "section", "cipai", "volume", "juan", "record_locator"]
        filled = [k for k in LYRIC_CAND if others.get(k) not in (None, "")]
        with_judou = [k for k in LYRIC_CAND
                      if others.get(k) and (JUDOU & set(str(others[k])))]
        if filled:
            oth = "|".join(f"{k}:{'有句读' if k in with_judou else '无句读'}" for k in filled)
        else:
            oth = "NONE(章节/曲牌/卷次/定位字段全空)"

        # ---- 判定 ----
        body_ok = han(BR.sub("", text)) >= 1
        if method == "NONE":
            verdict = "TITLE_IS_ALL_LYRIC"
        elif method == "DOT_ONLY_EMPTY_HEAD":
            verdict = "TITLE_IS_ALL_LYRIC"
        elif ov >= 2:
            verdict = "SPLIT_AMBIGUOUS"
        elif conf.startswith("HIGH") or conf.startswith("MEDIUM"):
            verdict = "SPLIT_CLEAN"
        else:
            verdict = "SPLIT_AMBIGUOUS"
        if not body_ok and han(lyr_h) < 12:
            verdict = "FRAGMENTARY" if verdict == "SPLIT_CLEAN" else verdict

        # 正文结尾是否完整（无接续证据才算截断损失）
        tail = re.sub(r"[（(][^）)]*[）)]\s*$", "", text).rstrip()
        ends_ok = bool(tail) and tail[-1] in END
        if not ends_ok and han(BR.sub("", text)) < 12 and tlen in (32, 33):
            verdict = "TRUNCATED_LOSS"

        stats[verdict] += 1
        stats["conf:" + conf] += 1
        stats["method:" + method] += 1
        stats["trunc:" + trunc] += 1
        stats[f"ov{min(ov,2)}"] += 1

        out_rows.append([
            wid, title, tlen, text, len(text), cc, lc,
            han(lyr_h), han(BR.sub("", text)),
            method, conf, trunc, oth, verdict,
        ])

    csv_path = os.path.join(OUT, "YUANQU_1729_FIELD_BOUNDARY_AUDIT.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["work_id", "title_raw", "title_len", "text_raw", "text_len",
                    "char_count", "line_count", "lyric_in_title_chars",
                    "lyric_in_text_chars", "boundary_method", "boundary_confidence",
                    "truncation_at_32", "other_fields_with_lyric", "verdict"])
        w.writerows(out_rows)

    # 额外：曲牌头缺失/未入词表的明细
    miss = collections.Counter()
    for r in recs:
        t = r[1]
        if "・" not in t:
            continue
        core = t.split("・")[0]
        if core and core not in vocab:
            miss[core] += 1
    with open(os.path.join(LOG, "C2_stats.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_at": TS, "n": len(recs), "stats": dict(stats),
                   "vocab_size": len(vocab),
                   "non_vocab_heads": [[k, v] for k, v in miss.most_common()]},
                  f, ensure_ascii=False, indent=2)
    print(len(recs))
    for k, v in sorted(stats.items()):
        print(k, v)


if __name__ == "__main__":
    main()
