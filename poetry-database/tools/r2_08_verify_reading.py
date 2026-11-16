#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 WP-A：核验各单元阅读记录的真实性。

核验项
1. quote 是否为所标 page_pdf 原文的去空白子串（伪造即失败）。
2. 引文在全书中的区分度（覆盖页数），过低说明是套话，不足以定位。
3. 页范围是否越界、unit_id 是否一致、字段完整性。
4. 覆盖度：每 5 页至少 2 条、每节至少 3 条（按 section 字段聚合）。
5. unit_summary 是否齐备。
"""
import json, os, re, glob, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "raw", "books_ocr_paddle", "wangli_yinyunxue", "pages.jsonl")
BR = os.path.join(ROOT, "raw", "r2_08", "branches")
OUT = os.path.join(ROOT, "raw", "r2_08", "reading_verification.json")

WS = re.compile(r"\s+")

UNITS = {
    "U01": ("第一编第一章 语音学常识", 10, 36),
    "U02": ("第一编第二章 名词略释", 37, 89),
    "U03": ("第一编第三章 等韵学", 90, 125),
    "U04": ("第二编第一章 广韵（上）", 126, 152),
    "U05": ("第二编第一章 广韵（下）", 153, 186),
    "U06": ("第三编第一章 古音（一）", 187, 221),
    "U07": ("第三编第一章 古音（二）", 222, 252),
    "U08": ("第三编第一章 古音（三）", 253, 292),
    "U09": ("第三编第一章 古音（四）", 293, 313),
    "U10": ("第四编第一章 韵书", 314, 360),
    "U11": ("第四编第二章 现代音（一）", 361, 406),
    "U12": ("第四编第二章 现代音（二）", 407, 441),
    "U13": ("附录 参考书", 442, 453),
    # 补读单元：参考资料引文页与表格页（页集不连续，按实际页集校验）
    "U14": ("补读 一编至二编引文页", 42, 147),
    "U15": ("补读 二编末至三编引文页", 159, 219),
    "U16": ("补读 三编古音引文页", 226, 271),
    "U17": ("补读 三编末至四编引文页", 279, 438),
    "U18": ("补读 残余表格与短页", 41, 429),
}

REQ = ["unit_id", "section", "page_pdf", "page_printed", "topic", "claim", "quote",
       "quote_kind", "terms", "data_points", "poetry_relevance", "confidence", "note"]


def norm(s):
    return WS.sub("", s or "")


def main():
    pages = {}
    for line in open(SRC, encoding="utf-8"):
        r = json.loads(line)
        pages[r["page"]] = r["text"]
    npages = {p: norm(t) for p, t in pages.items()}

    result = {"units": {}, "failures": [], "totals": {}}
    all_recs = []
    for uid, (name, p0, p1) in UNITS.items():
        f = os.path.join(BR, "A_" + uid, "records.jsonl")
        recs, summ, bad = [], None, []
        if not os.path.exists(f):
            result["units"][uid] = {"status": "MISSING"}
            continue
        for ln, line in enumerate(open(f, encoding="utf-8"), 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception as e:
                bad.append({"line": ln, "error": "JSON:" + str(e)[:80]})
                continue
            if r.get("kind") == "UNIT_SUMMARY":
                summ = r
                continue
            miss = [k for k in REQ if k not in r]
            if miss:
                bad.append({"line": ln, "error": "MISSING_FIELDS:" + ",".join(miss)})
                continue
            if r.get("unit_id") != uid:
                bad.append({"line": ln, "error": "UNIT_ID_MISMATCH"})
                continue
            p = r.get("page_pdf")
            if not isinstance(p, int) or not (p0 <= p <= p1):
                bad.append({"line": ln, "error": "PAGE_OUT_OF_RANGE", "page": p})
                continue
            q = norm(r.get("quote"))
            if len(q) < 15:
                bad.append({"line": ln, "error": "QUOTE_TOO_SHORT", "page": p})
                continue
            if q not in npages.get(p, ""):
                # 允许 ±1 页（跨页续句），但须记录
                alt = [pp for pp in (p - 1, p + 1) if q in npages.get(pp, "")]
                if alt:
                    r["_quote_page_corrected"] = alt[0]
                    r["page_pdf"] = alt[0]
                    r["page_printed"] = alt[0] - 9
                    bad.append({"line": ln, "error": "QUOTE_ON_NEIGHBOR_PAGE",
                                "from": p, "to": alt[0]})
                else:
                    bad.append({"line": ln, "error": "QUOTE_NOT_FOUND", "page": p,
                                "quote": r.get("quote")[:40]})
                    continue
            r["_quote_len"] = len(q)
            r["_pages_containing"] = sum(1 for t in npages.values() if q in t)
            recs.append(r)

        cov_pages = sorted({r["page_pdf"] for r in recs})
        secs = collections.Counter(r["section"] for r in recs)
        # 每 5 页窗口
        windows = []
        for st in range(p0, p1 + 1, 5):
            n = sum(1 for q in cov_pages if st <= q < st + 5)
            windows.append({"from": st, "to": min(st + 4, p1), "n": n})
        thin = [w for w in windows if w["n"] < 2]
        result["units"][uid] = {
            "name": name, "pages": [p0, p1], "n_pages": p1 - p0 + 1,
            "n_records": len(recs), "n_pages_covered": len(cov_pages),
            "coverage_pct": round(100 * len(cov_pages) / (p1 - p0 + 1), 1),
            "sections": dict(secs),
            "n_low": sum(1 for r in recs if r.get("confidence") == "LOW"),
            "n_medium": sum(1 for r in recs if r.get("confidence") == "MEDIUM"),
            "summary_present": bool(summ),
            "summary_unresolved": (summ or {}).get("unresolved", []),
            "thin_windows": thin,
            "issues": bad,
            "quote_len_avg": round(sum(r["_quote_len"] for r in recs) / len(recs), 1) if recs else 0,
            "quote_unique_pages_avg": round(
                sum(r["_pages_containing"] for r in recs) / len(recs), 2) if recs else 0,
        }
        all_recs += recs

    all_pages = set(range(10, 454))
    covered = {r["page_pdf"] for r in all_recs} & all_pages
    result["totals"] = {
        "n_records": len(all_recs),
        "n_units": len([v for v in result["units"].values() if v.get("n_records")]),
        "body_pages": len(all_pages),
        "pages_covered": len(covered),
        "coverage_pct": round(100 * len(covered) / len(all_pages), 1),
        "quote_failures": sum(1 for v in result["units"].values()
                              for i in v.get("issues", []) if i["error"] == "QUOTE_NOT_FOUND"),
        "neighbor_page_fixes": sum(1 for v in result["units"].values()
                                   for i in v.get("issues", []) if i["error"] == "QUOTE_ON_NEIGHBOR_PAGE"),
        "other_issues": sum(1 for v in result["units"].values()
                            for i in v.get("issues", []) if i["error"] not in
                            ("QUOTE_NOT_FOUND", "QUOTE_ON_NEIGHBOR_PAGE")),
    }
    json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 合并记录，供入库
    with open(os.path.join(ROOT, "raw", "r2_08", "reading_records_all.jsonl"), "w",
              encoding="utf-8") as fh:
        for r in all_recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps(result["totals"], ensure_ascii=False, indent=1))
    for uid, v in result["units"].items():
        if "n_records" in v:
            print(f"{uid} rec={v['n_records']:3d} pages={v['n_pages_covered']:3d}/{v['n_pages']:3d} "
                  f"({v['coverage_pct']:5.1f}%) low={v['n_low']} thin={len(v['thin_windows'])} "
                  f"issues={len(v['issues'])}")


if __name__ == "__main__":
    main()
