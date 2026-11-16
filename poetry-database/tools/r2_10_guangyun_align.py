#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-10 工作包 C：《廣韻》反切上下字修正與韻目歸屬重判（不修改 R2-08 表）。

演算法
------
1. 對每卷掃描所有「韻目標記候選」：序號（允許數字間有全角空格）＋可選韻名＋其後接
   〈 或兩個以上全角空格，且必須位於行首或緊跟 〉 之後。
2. 把候選按出現順序與卷內韻序 1..N 做**單調對齊**：
   候選序號 == 期望值 → 接受並前進；== 期望值+1 → 判定中間那一韻缺標記（NOT_FOUND），
   接受並前進兩格；其餘（如條目字頭恰為「三」）視為假候選跳過。
3. 韻目成立後，其 body_start 到下一韻 start 之間即該韻正文；
   每條舊條目按 `字頭〈反切` 單調定位得字符偏移 → 由區間判定韻目（HEADER_DIRECT）。
4. 未能定位或落在未錨定韻段內的條目，一律標 UNRESOLVED，不用推定補齊。
"""
import collections
import csv
import json
import os
import re
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
GV = os.path.join(ROOT, "raw", "books", "guangyun")
OUT = os.path.join(ROOT, "raw", "r2_10", "guangyun")
os.makedirs(OUT, exist_ok=True)

CJK = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
FW = "\u3000"
SP = "[" + FW + r"\s]"
VOL_TONE = {1: "上平聲", 2: "下平聲", 3: "上聲", 4: "去聲", 5: "入聲"}
LABEL = re.compile(r"^(獨用|同用|通用|[^，。]{1,6}同用)$")
DIG = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九"}
CNV = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

# 候選：行首或 〉 之後 → 空白 → 序號（數字間可夾空白）→ 空白{1,} → 1~3 字名 → 後面是 〈 或 空白
CAND = re.compile(
    r"(?:^|(?<=〉))" + SP + r"*([一二三四五六七八九十](?:" + SP + r"{0,2}[一二三四五六七八九十]){0,2})"
    + SP + r"{0,3}([" + CJK + r"]{1,3})(?=〈)", re.M
)


def cn2int(s):
    s = re.sub(SP, "", s)
    if not s:
        return None
    if "十" not in s:
        return CNV.get(s[0]) if len(s) == 1 else None
    if s == "十":
        return 10
    if s.startswith("十"):
        return 10 + CNV.get(s[1], 0)
    if s.endswith("十"):
        return CNV.get(s[0], 0) * 10
    a, b = s.split("十", 1)
    return CNV.get(a, 0) * 10 + CNV.get(b, 0)


def build_boundaries(text, vol, yunmus, start_off=0):
    cands = []
    for m in CAND.finditer(text):
        if m.start() < start_off:
            continue
        v = cn2int(m.group(1))
        if v is None or not (1 <= v <= 60):
            continue
        cands.append({"pos": m.start(), "end": m.end(), "num": v,
                      "name": m.group(2), "raw": m.group(0)[:30]})
    # 標籤：候選之後若接 名〈獨用〉，body 需跳過
    out, k, ci = [], 1, 0
    def name_ok(c, no):
        return c["name"] == yunmus[no - 1]["yun_name"]

    while ci < len(cands) and k <= len(yunmus):
        c = cands[ci]
        if c["num"] == k and name_ok(c, k):
            out.append((k, c, 0))
            k += 1
            ci += 1
        elif c["num"] == k + 1 and name_ok(c, k + 1):
            out.append((k, None, 1))   # k 缺標記
            out.append((k + 1, c, 0))
            k += 2
            ci += 1
        else:
            ci += 1
    while k <= len(yunmus):
        out.append((k, None, 1))
        k += 1

    bounds = []
    for no, c, missing in out:
        y = yunmus[no - 1]
        if c is None:
            bounds.append({"vol": vol, "tone": VOL_TONE[vol], "yun_no": no,
                           "yun_name": y["yun_name"], "offset": None, "body_start": None,
                           "method": "NOT_FOUND", "label": y.get("label", ""),
                           "line_no": None, "snippet": "", "raw_cand": ""})
            continue
        tail = text[c["end"]:c["end"] + 40]
        lm = re.match(r"(" + SP + r"*)([" + CJK + r"]{1,3})〈([^〉]{0,14})〉", tail)
        if lm and LABEL.match(lm.group(3)):
            body_start, label = c["end"] + lm.end(), lm.group(3)
        else:
            body_start, label = c["end"], ""
        bounds.append({"vol": vol, "tone": VOL_TONE[vol], "yun_no": no,
                       "yun_name": y["yun_name"], "offset": c["pos"],
                       "body_start": body_start,
                       "method": "ANCHORED" + ("_AFTER_GAP" if missing else ""),
                       "label": label or y.get("label", ""),
                       "line_no": text.count("\n", 0, c["pos"]) + 1,
                       "snippet": text[max(0, c["pos"] - 10):c["pos"] + 44].replace("\n", "⏎"),
                       "raw_cand": c["raw"]})
    return bounds, len(cands)



def repair_missing(text, bounds, by_vol):
    """對 NOT_FOUND 的韻，在相鄰兩錨定韻之間的區間內按「序號+〈同用/獨用〉」定點修補。"""
    fixed = 0
    for vol, yl in by_vol.items():
        for i, b in enumerate(bounds):
            if b["vol"] != vol or b["offset"] is not None:
                continue
            prev = next((x for x in reversed(bounds[:i]) if x["vol"] == vol and x["offset"] is not None), None)
            nxt = next((x for x in bounds[i + 1:] if x["vol"] == vol and x["offset"] is not None), None)
            lo = prev["body_start"] if prev else 0
            hi = nxt["offset"] if nxt else len(text)
            num = to_cn_local(b["yun_no"])
            nump = ("[" + FW + r"\s]{0,3}").join(re.escape(c) for c in num)
            pat = re.compile(
                r"(?:^|(?<=〉))[" + FW + r"\s]*" + nump + r"[" + FW + r"\s]{0,3}"
                r"([" + CJK + r"]{1,3})〈(獨用|同用|通用|[^，。]{1,6}同用)〉", re.M)
            m = pat.search(text, lo, hi)
            if not m:
                continue
            b["offset"] = m.start()
            b["body_start"] = m.end()
            b["method"] = "ANCHORED_BY_LABEL_REPAIR"
            b["label"] = m.group(2)
            b["line_no"] = text.count("\n", 0, m.start()) + 1
            b["snippet"] = text[max(0, m.start() - 10):m.start() + 44].replace("\n", "⏎")
            b["raw_cand"] = m.group(0)[:30]
            fixed += 1
    return fixed


def to_cn_local(k):
    if k <= 9:
        return DIG[k]
    if k == 10:
        return "十"
    if k < 20:
        return "十" + DIG[k - 10]
    t, u = divmod(k, 10)
    return {2: "二", 3: "三", 4: "四", 5: "五", 6: "六"}[t] + "十" + ("" if u == 0 else DIG[u])


def main():
    yunmus = json.load(open(os.path.join(ROOT, "raw", "r2_08", "guangyun_yunmu.json"),
                            encoding="utf-8"))
    by_vol = collections.defaultdict(list)
    for y in yunmus:
        by_vol[y["volume"]].append(y)
    for v in by_vol:
        by_vol[v].sort(key=lambda x: x["yun_no"])

    texts, bounds, cand_stat = {}, [], {}
    for vol in (1, 2, 3, 4, 5):
        text = open(os.path.join(GV, "卷%d.wikitext" % vol), encoding="utf-8").read()
        texts[vol] = text
        _lines = text.split("\n")
        _hdr = [i for i, ln in enumerate(_lines) if re.search(r"原本廣韻[卷巻]", ln)]
        _cut = next((i for i, ln in enumerate(_lines) if "切" in ln), 0)
        _before = [i for i in _hdr if i < _cut]
        _so = sum(len(l) + 1 for l in _lines[:_before[-1]]) if _before else 0
        b, ncand = build_boundaries(text, vol, by_vol[vol], _so)
        bounds.extend(b)
        cand_stat[vol] = {"n_candidates": ncand,
                          "n_anchored": sum(1 for x in b if x["offset"] is not None),
                          "n_rhymes": len(by_vol[vol])}

    _nf = repair_missing("".join([]) or "", [], {})
    # 逐卷修補（需要各卷自身文本）
    fixed_total = 0
    for vol in (1, 2, 3, 4, 5):
        vb = [b for b in bounds if b["vol"] == vol]
        fixed_total += repair_missing(texts[vol], vb, {vol: by_vol[vol]})
    # 回寫
    bounds = [x for vol in (1, 2, 3, 4, 5) for x in [b for b in bounds if b["vol"] == vol]]
    found = [b for b in bounds if b["offset"] is not None]
    print("韻目錨定:", len(found), "/206", "（區間修補 %d）" % fixed_total)
    print("各卷:", cand_stat)
    miss = [(b["vol"], b["yun_no"], b["yun_name"]) for b in bounds if b["offset"] is None]
    print("缺標記韻:", len(miss), miss[:14])

    intervals = {}
    for vol in (1, 2, 3, 4, 5):
        vb = [b for b in found if b["vol"] == vol]
        for k, b in enumerate(vb):
            hi = vb[k + 1]["offset"] if k + 1 < len(vb) else len(texts[vol])
            # 若下一錨定韻的序號與本韻不連號，說明中間有未錨定韻，區間末段歸屬無法確定
            gap = (vb[k + 1]["yun_no"] - b["yun_no"] > 1) if k + 1 < len(vb) else False
            intervals.setdefault(vol, []).append((b["body_start"], hi, b, gap))

    old = [json.loads(l) for l in open(os.path.join(ROOT, "raw", "r2_08", "guangyun_xiaoyun.jsonl"),
                                      encoding="utf-8")]
    cur = {v: 0 for v in (1, 2, 3, 4, 5)}
    rows, stat = [], collections.Counter()
    for r in old:
        vol, text = r["volume"], texts[r["volume"]]
        head = (r.get("head_raw") or r["head"] or "")[:4]
        fq = r.get("fanqie") or ""
        pos = -1
        if head and fq:
            m = re.compile(re.escape(head) + r"〈" + re.escape(fq[:-1]) + r"[" + CJK + r"]切") \
                .search(text, cur[vol])
            if m:
                pos = m.start()
        if pos < 0 and head and fq:
            m = re.compile(re.escape(head) + r"〈").search(text, cur[vol])
            if m and fq[:1] in text[m.end():m.end() + 40]:
                pos = m.start()
        if pos < 0:
            stat["POS_NOT_FOUND"] += 1
        else:
            cur[vol] = pos

        yun = None
        amb = False
        if r["is_xiaoyun_head"] and pos >= 0:
            for lo, hi, b, gap in intervals.get(vol, []):
                if lo <= pos < hi:
                    yun, amb = b, gap
                    break
        fc = fq[:-1] if fq.endswith("切") else fq
        if len(fc) >= 2:
            upper, lower = fc[0], fc[1]
            fkind = "TWO_CHAR" if len(fc) == 2 else "LONGER"
        elif len(fc) == 1:
            upper = lower = ""
            fkind = "INCOMPLETE_ONE_CHAR"
        else:
            upper = lower = ""
            fkind = "NO_FANQIE"
        old_up = r.get("fanqie_upper") or ""
        if fkind == "TWO_CHAR":
            cmp_ = "OLD_STORED_LOWER" if old_up == lower else (
                "OLD_STORED_UPPER" if old_up == upper else "OLD_OTHER")
        elif fkind == "LONGER":
            cmp_ = "OLD_STORED_LOWER" if old_up == lower else "OLD_LONG_FANQIE"
        else:
            cmp_ = "OLD_" + fkind
        stat[cmp_] += 1
        rows.append({
            "entry_id": r["entry_id"], "volume": vol, "tone": r["tone"],
            "old_yun_no": r["yun_no"], "old_yun_name": r["yun_name"],
            "yun_no": (yun["yun_no"] if (yun and not amb) else None),
            "yun_name": (yun["yun_name"] if (yun and not amb) else None),
            "yun_method": ("HEADER_DIRECT" if (yun and not amb) else
                           ("UNRESOLVED_SPAN" if amb else
                            ("UNRESOLVED_POS" if r["is_xiaoyun_head"] else "NA_NON_HEAD"))),
            "char_offset": pos, "head": r["head"], "fanqie": fq,
            "fanqie_upper": upper, "fanqie_lower": lower, "fanqie_kind": fkind,
            "old_fanqie_upper": old_up, "comparison": cmp_,
            "is_xiaoyun_head": r["is_xiaoyun_head"], "old_attribution": r["yun_attribution"],
            "evidence": text[max(0, pos - 10):pos + 26].replace("\n", "") if pos >= 0 else "",
        })

    heads = [x for x in rows if x["is_xiaoyun_head"]]
    yun_chg = sum(1 for x in heads if x["yun_name"] and x["yun_name"] != x["old_yun_name"])
    yun_same = sum(1 for x in heads if x["yun_name"] and x["yun_name"] == x["old_yun_name"])
    unresolved = sum(1 for x in heads if not x["yun_name"])
    unres_span = sum(1 for x in heads if x["yun_method"] == "UNRESOLVED_SPAN")
    print("條目:", len(rows), "小韻首:", len(heads))
    print("反切比對:", dict(stat))
    print("韻目改變:", yun_chg, "未變:", yun_same, "UNRESOLVED:", unresolved,
          "（其中跨未錨定韻段 %d，位置無法定位 %d）" % (unres_span, unresolved - unres_span))

    per_yun = collections.Counter((x["volume"], x["yun_no"]) for x in heads if x["yun_no"])
    zero = [b for b in found if per_yun[(b["vol"], b["yun_no"])] == 0]
    print("錨定韻中小韻為 0 者:", [(b["vol"], b["yun_no"], b["yun_name"]) for b in zero][:10])

    seg, run = [], None
    for x in rows:
        if x["yun_name"] and x["yun_name"] != x["old_yun_name"]:
            if run and run["vol"] == x["volume"] and run["new"] == x["yun_name"]:
                run["n"] += 1
                run["end"] = x["entry_id"]
            else:
                if run:
                    seg.append(run)
                run = {"vol": x["volume"], "old": x["old_yun_name"], "new": x["yun_name"],
                       "start": x["entry_id"], "end": x["entry_id"], "n": 1}
        else:
            if run:
                seg.append(run)
                run = None
    if run:
        seg.append(run)
    big = [s0 for s0 in seg if s0["n"] >= 5]
    print("錯掛連續段:", len(seg), "（≥5 條者 %d）" % len(big))
    for s0 in big[:12]:
        print("   vol%d 舊[%s]→新[%s] %s..%s 共 %d" %
              (s0["vol"], s0["old"], s0["new"], s0["start"], s0["end"], s0["n"]))

    cols = ["entry_id", "volume", "tone", "old_yun_no", "old_yun_name", "yun_no", "yun_name",
            "yun_method", "char_offset", "head", "fanqie", "fanqie_upper", "fanqie_lower",
            "fanqie_kind", "old_fanqie_upper", "comparison", "is_xiaoyun_head",
            "old_attribution", "evidence"]
    with open(os.path.join(OUT, "guangyun_rebuild_all.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for x in rows:
            w.writerow(x)

    with open(os.path.join(OUT, "guangyun_206_boundaries.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["volume", "tone", "yun_no", "yun_name", "label", "offset", "body_start",
                    "method", "line_no", "n_xiaoyun", "snippet", "raw_candidate"])
        for b in bounds:
            w.writerow([b["vol"], b["tone"], b["yun_no"], b["yun_name"], b["label"],
                        b["offset"], b["body_start"], b["method"], b["line_no"],
                        per_yun[(b["vol"], b["yun_no"])], b["snippet"], b["raw_cand"]])

    with open(os.path.join(OUT, "guangyun_misattach_segments.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["volume", "old_yun_name", "new_yun_name", "entry_from", "entry_to", "n_entries"])
        for s0 in seg:
            w.writerow([s0["vol"], s0["old"], s0["new"], s0["start"], s0["end"], s0["n"]])

    con = sqlite3.connect(DB)
    con.execute("DROP TABLE IF EXISTS guangyun_fanqie_r2_10")
    con.execute("""CREATE TABLE guangyun_fanqie_r2_10(
      entry_id TEXT PRIMARY KEY, volume INT, tone TEXT,
      old_yun_no INT, old_yun_name TEXT, yun_no INT, yun_name TEXT, yun_method TEXT,
      char_offset INT, head TEXT, fanqie TEXT, fanqie_upper TEXT, fanqie_lower TEXT,
      fanqie_kind TEXT, old_fanqie_upper TEXT, comparison TEXT, is_xiaoyun_head INT,
      old_attribution TEXT, evidence TEXT, round TEXT)""")
    con.executemany("""INSERT INTO guangyun_fanqie_r2_10 VALUES
      (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, '2026-11-15')""",
        [(x["entry_id"], x["volume"], x["tone"], x["old_yun_no"], x["old_yun_name"],
          x["yun_no"], x["yun_name"], x["yun_method"], x["char_offset"], x["head"],
          x["fanqie"], x["fanqie_upper"], x["fanqie_lower"], x["fanqie_kind"],
          x["old_fanqie_upper"], x["comparison"], x["is_xiaoyun_head"],
          x["old_attribution"], x["evidence"]) for x in rows])
    con.execute("DROP TABLE IF EXISTS guangyun_yunmu_repair_r2_10")
    con.execute("""CREATE TABLE guangyun_yunmu_repair_r2_10(
      volume INT, tone TEXT, yun_no INT, yun_name TEXT, label TEXT,
      char_offset INT, body_start INT, locate_method TEXT, line_no INT,
      n_xiaoyun INT, snippet TEXT, round TEXT)""")
    con.executemany("""INSERT INTO guangyun_yunmu_repair_r2_10 VALUES
      (?,?,?,?,?,?,?,?,?,?,?, '2026-11-15')""",
        [(b["vol"], b["tone"], b["yun_no"], b["yun_name"], b["label"], b["offset"],
          b["body_start"], b["method"], b["line_no"], per_yun[(b["vol"], b["yun_no"])],
          b["snippet"]) for b in bounds])
    con.commit()
    con.close()

    stats = {
        "n_boundaries_found": len(found), "n_boundaries_total": len(bounds),
        "n_rhymes_missing_marker": len(miss), "missing_marker": miss,
        "volume_stats": cand_stat, "n_entries": len(rows), "n_xiaoyun_heads": len(heads),
        "fanqie_comparison": dict(stat),
        "xiaoyun_yun_changed": yun_chg, "xiaoyun_yun_same": yun_same,
        "xiaoyun_unresolved": unresolved, "xiaoyun_unresolved_span": unres_span,
        "anchored_yun_with_zero_xiaoyun": [(b["vol"], b["yun_no"], b["yun_name"]) for b in zero],
        "n_misattach_segments": len(seg),
        "n_misattach_segments_ge5": len(big),
        "big_segments": big,
    }
    json.dump(stats, open(os.path.join(OUT, "rebuild_stats.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({k: stats[k] for k in ["n_boundaries_found", "n_rhymes_missing_marker",
                                            "fanqie_comparison", "xiaoyun_yun_changed",
                                            "xiaoyun_unresolved", "n_misattach_segments_ge5"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
