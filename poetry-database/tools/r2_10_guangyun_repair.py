#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-10 工作包 C：《廣韻》反切上下字修正與韻目歸屬重判（不修改 R2-08 表）。

設計
----
保留 R2-08 的 20,530 條條目集（確保「4,771 條全部重審」可對帳），做兩件事：

1. 反切拆分：由既有 `fanqie` 字串（形如 `徳紅切`）按定義重拆
   —— 上字＝第 1 字（取聲母）、下字＝第 2 字（取韻母）。
   只有 1 字者標 INCOMPLETE_ONE_CHAR，不補、不猜。

2. 韻目歸屬：先在正文中按「卷內韻序」定位 206 個韻目標記，得到字符偏移區間；
   再把每條舊條目按 `字頭〈反切` 在正文中順序定位（游標單調前進），
   由其所處區間判定韻目 —— 位置直證（HEADER_DIRECT），不用 CARRIED_FORWARD 推定。

3. 與舊 yun_name 逐條比對，找出錯掛，並統計錯掛連續段。
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
VOL_TONE = {1: "上平聲", 2: "下平聲", 3: "上聲", 4: "去聲", 5: "入聲"}
LABEL = re.compile(r"^(獨用|同用|通用|[^，。]{1,6}同用)$")
DIG = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九"}


def to_cn(k):
    if k <= 9:
        return DIG[k]
    if k == 10:
        return "十"
    if k < 20:
        return "十" + DIG[k - 10]
    t, u = divmod(k, 10)
    return {2: "二", 3: "三", 4: "四", 5: "五", 6: "六"}[t] + "十" + ("" if u == 0 else DIG[u])


def locate_yunmu(text, yun, cursor):
    num = to_cn(yun["yun_no"])
    name = re.escape(yun["yun_name"])
    nump = ("[" + FW + r"\s]{0,3}").join(re.escape(c) for c in num)
    pats = [
        (r"(?:^|(?<=〉))[" + FW + r"\s]*" + nump + "[" + FW + r"]{2,}" + name + r"(?=〈)",
         "MID_LINE"),
        (r"(?m)^[" + FW + r"\s]*" + nump + r"[" + FW + r"\s]*" + name +
         r"(?=[〈" + FW + r"\s]|$)", "LINE_STANDALONE"),
        (r"(?:^|(?<=〉))[" + FW + r"\s]*" + nump + "[" + FW + r"]{2,}", "NUM_GAP_ONLY"),
        (r"(?m)^[" + FW + r"\s]*" + nump + r"(?=[" + FW + r"\s]|$)", "NUM_LINE_ONLY"),
    ]
    for pin, method in pats:
        m = re.search(pin, text[cursor:])
        if not m:
            continue
        start, end = cursor + m.start(), cursor + m.end()
        tail = text[end:end + 40]
        lm = re.match(r"\s*([" + CJK + r"]{1,3})〈([^〉]{0,14})〉", tail)
        if lm and LABEL.match(lm.group(2)):
            body_start, label = end + lm.end(), lm.group(2)
        else:
            body_start, label = end, ""
        return {"start": start, "body_start": body_start, "method": method,
                "label": label, "line_no": text.count("\n", 0, start) + 1,
                "snippet": text[max(0, start - 8):start + 46].replace("\n", "⏎")}
    return None


def main():
    yunmus = json.load(open(os.path.join(ROOT, "raw", "r2_08", "guangyun_yunmu.json"),
                            encoding="utf-8"))
    texts, bounds = {}, []
    for vol in (1, 2, 3, 4, 5):
        text = open(os.path.join(GV, "卷%d.wikitext" % vol), encoding="utf-8").read()
        texts[vol] = text
        lines = text.split("\n")
        hdr = [i for i, ln in enumerate(lines) if re.search(r"原本廣韻[卷巻]", ln)]
        first_cut = next((i for i, ln in enumerate(lines) if "切" in ln), 0)
        before = [i for i in hdr if i < first_cut]
        start_i = before[-1] if before else 0
        cursor = sum(len(l) + 1 for l in lines[:start_i])
        for yun in [y for y in yunmus if y["volume"] == vol]:
            r = locate_yunmu(text, yun, cursor)
            b = {"vol": vol, "tone": VOL_TONE[vol], "yun_no": yun["yun_no"],
                 "yun_name": yun["yun_name"], "offset": None, "body_start": None,
                 "method": "NOT_FOUND", "label": yun.get("label", ""), "line_no": None,
                 "snippet": ""}
            if r:
                b.update({"offset": r["start"], "body_start": r["body_start"],
                          "method": r["method"], "line_no": r["line_no"],
                          "snippet": r["snippet"], "label": r["label"] or b["label"]})
                cursor = r["body_start"]
            bounds.append(b)

    found = [b for b in bounds if b["offset"] is not None]
    print("韻目定位:", len(found), "/206", dict(collections.Counter(b["method"] for b in bounds)))

    intervals = {}
    for vol in (1, 2, 3, 4, 5):
        vb = [b for b in found if b["vol"] == vol]
        for k, b in enumerate(vb):
            hi = vb[k + 1]["offset"] if k + 1 < len(vb) else len(texts[vol])
            intervals.setdefault(vol, []).append((b["body_start"], hi, b))

    old = [json.loads(l) for l in open(os.path.join(ROOT, "raw", "r2_08", "guangyun_xiaoyun.jsonl"),
                                      encoding="utf-8")]
    cur = {v: 0 for v in (1, 2, 3, 4, 5)}
    rows, stat = [], collections.Counter()
    for r in old:
        vol = r["volume"]
        text = texts[vol]
        head = (r.get("head_raw") or r["head"] or "")[:4]
        fq = r.get("fanqie") or ""
        pos = -1
        if head and fq:
            pat = re.escape(head) + r"〈" + re.escape(fq[:-1]) + r"[" + CJK + r"]切"
            m = re.compile(pat).search(text, cur[vol])
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
        if pos >= 0:
            for lo, hi, b in intervals.get(vol, []):
                if lo <= pos < hi:
                    yun = b
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
            "yun_no": yun["yun_no"] if yun else None,
            "yun_name": yun["yun_name"] if yun else None,
            "yun_method": "HEADER_DIRECT" if yun else "UNRESOLVED",
            "char_offset": pos, "head": r["head"], "fanqie": fq,
            "fanqie_upper": upper, "fanqie_lower": lower, "fanqie_kind": fkind,
            "old_fanqie_upper": old_up, "comparison": cmp_,
            "is_xiaoyun_head": r["is_xiaoyun_head"], "old_attribution": r["yun_attribution"],
            "evidence": text[max(0, pos - 10):pos + 26].replace("\n", "") if pos >= 0 else "",
        })

    heads = [x for x in rows if x["is_xiaoyun_head"]]
    yun_chg = sum(1 for x in heads if x["yun_name"] and x["yun_name"] != x["old_yun_name"])
    yun_same = sum(1 for x in heads if x["yun_name"] and x["yun_name"] == x["old_yun_name"])
    print("條目:", len(rows), "小韻首:", len(heads), "位置未定位:", stat["POS_NOT_FOUND"])
    print("反切比對:", dict(stat))
    print("小韻首韻目改變:", yun_chg, "未變:", yun_same,
          "無歸屬:", sum(1 for x in heads if not x["yun_name"]))

    per_yun = collections.Counter((x["volume"], x["yun_no"]) for x in heads if x["yun_no"])
    zero = [b for b in found if per_yun[(b["vol"], b["yun_no"])] == 0]
    print("小韻為 0 的韻:", len(zero), [(b["vol"], b["yun_no"], b["yun_name"]) for b in zero][:10])

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
    print("錯掛連續段:", len(seg))
    for s0 in seg[:14]:
        print("   vol%d 舊[%s]→新[%s] 條目 %s..%s 共 %d" %
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
                    "method", "line_no", "n_xiaoyun", "snippet"])
        for b in bounds:
            w.writerow([b["vol"], b["tone"], b["yun_no"], b["yun_name"], b["label"],
                        b["offset"], b["body_start"], b["method"], b["line_no"],
                        per_yun[(b["vol"], b["yun_no"])], b["snippet"]])

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
        "not_found": [(b["vol"], b["yun_no"], b["yun_name"]) for b in bounds
                      if b["offset"] is None],
        "method_counts": dict(collections.Counter(b["method"] for b in bounds)),
        "n_entries": len(rows), "n_xiaoyun_heads": len(heads),
        "fanqie_comparison": dict(stat),
        "xiaoyun_yun_changed": yun_chg, "xiaoyun_yun_same": yun_same,
        "xiaoyun_pos_unresolved": stat["POS_NOT_FOUND"],
        "yun_with_zero_xiaoyun": [(b["vol"], b["yun_no"], b["yun_name"]) for b in zero],
        "n_misattach_segments": len(seg), "misattach_segments": seg,
    }
    json.dump(stats, open(os.path.join(OUT, "rebuild_stats.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({k: stats[k] for k in ["n_boundaries_found", "fanqie_comparison",
                                            "xiaoyun_yun_changed", "n_misattach_segments",
                                            "yun_with_zero_xiaoyun"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
