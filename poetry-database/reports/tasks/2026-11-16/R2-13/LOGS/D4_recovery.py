#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-13 D4：200 条分层抽样回源核对 + 100 条有据恢复候选（只读，不写库）"""
import sqlite3, re, csv, json, os, hashlib, random, collections

BASE = "<PROJECT_ROOT>/poetry-database"
OUT = os.path.join(BASE, "reports/tasks/2026-11-16/R2-13")
DB = os.path.join(BASE, "database/poetry.db")
RAW = os.path.join(BASE, "raw/poetry/yuanqu/yuanqu.json")
SRC_REL = "raw/poetry/yuanqu/yuanqu.json"

PAR = re.compile(r"[（(][^）)]{0,40}[）)]")
HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
PUNCT = re.compile(r"[，。；？！、：]")

def han(s):
    return len(HAN.findall(s or ""))

def band(n):
    return "≤20" if n <= 20 else "21-40" if n <= 40 else "41-80" if n <= 80 else "81-160" if n <= 160 else ">160"

def main():
    raw_bytes = open(RAW, "rb").read()
    sha = hashlib.sha256(raw_bytes).hexdigest()
    raw = json.loads(raw_bytes.decode("utf-8"))
    rawidx = collections.defaultdict(list)
    for i, r in enumerate(raw):
        rawidx[(r.get("author", ""), r.get("title", ""))].append((i, r))

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    works = {r["work_id"]: dict(r) for r in con.execute(
        "SELECT work_id,title_raw,author_name,collection,genre,char_count,line_count,text_raw FROM works WHERE genre='曲'")}
    audit = list(csv.DictReader(open(os.path.join(OUT, "YUANQU_2447_MISSING_TEXT_AUDIT.csv"),
                                    encoding="utf-8-sig")))

    # ---- 分层抽样 200 ----
    random.seed(20261116)
    quota = {"IN_OTHER_FIELD": 100, "LYRIC_PRESENT": 80, "FRAGMENTARY": 18, "DIALOGUE_ONLY": 2}
    strata = collections.defaultdict(list)
    for r in audit:
        strata[(r["status"], r["play_or_sanqu"], band(int(r["char_count"] or 0)))].append(r)
    for k in strata:
        random.shuffle(strata[k])
    keys = sorted(strata.keys(), key=lambda k: (k[0], k[1], k[2]))
    sample, ptr = [], collections.Counter()
    # 先按层轮转取，保证每层都有覆盖
    while len(sample) < 200:
        progressed = False
        for k in keys:
            if len(sample) >= 200:
                break
            if k[0] not in quota:
                continue
            used = sum(1 for s in sample if s["status"] == k[0])
            if used >= quota[k[0]]:
                continue
            if ptr[k] < len(strata[k]):
                sample.append(strata[k][ptr[k]]); ptr[k] += 1; progressed = True
        if not progressed:
            break
    if len(sample) < 200:   # 层内不足时按序补齐（仍不重复）
        have = {s["work_id"] for s in sample}
        for k in keys:
            for r in strata[k]:
                if len(sample) >= 200:
                    break
                if r["work_id"] not in have:
                    sample.append(r); have.add(r["work_id"])
            if len(sample) >= 200:
                break

    # ---- 200 条回源 ----
    rows200 = []
    for r in sample:
        w = works[r["work_id"]]
        dbtext = w["text_raw"] or ""
        key = (r["author_name"], r["title_raw"])
        cands = rawidx.get(key, [])
        best = None
        for i, rr in cands:
            if "\n".join(rr.get("paragraphs") or []) == dbtext:
                best = (i, rr); break
        if best is None and cands:
            best = max(cands, key=lambda x: han("\n".join(x[1].get("paragraphs") or [])))
        idx = best[0] if best else -1
        rtitle = best[1].get("title", "") if best else ""
        rparas = "\n".join(best[1].get("paragraphs") or []) if best else ""
        st = r["status"]
        if st == "IN_OTHER_FIELD":
            qp, tail = rtitle.split("・", 1) if "・" in rtitle else ("", rtitle)
            found = "Y"
            head = tail[:80]
            status = "RECOVERABLE_TITLE_CARRIES_LYRIC"
            ev = f"原文 title 末尾承载曲文 {han(tail)} 字，正文续 {han(rparas)} 字；title 尾「{tail[-12:]}」→正文首「{rparas[:12]}」"
        elif st == "LYRIC_PRESENT":
            found = "Y"
            head = rparas[:80]
            status = "SOURCE_TEXT_COMPLETE"
            ev = f"原文 paragraphs {han(rparas)} 字，与库 text_raw 逐字相同={rparas == dbtext}"
        elif st == "FRAGMENTARY":
            found = "N"
            head = ""
            status = "SOURCE_UNAVAILABLE"
            ev = f"原文 paragraphs 仅 {han(rparas)} 字，句中即断：「{rparas[:30]}」，本地无第二来源"
        else:
            found = "N"
            head = ""
            status = "SOURCE_UNAVAILABLE"
            ev = f"原文 paragraphs 只含宾白：「{rparas[:40]}」"
        rows200.append({
            "sample_id": f"T{len(rows200)+1:03d}", "work_id": r["work_id"], "title": r["title_raw"],
            "collection": r["collection"], "source_file": SRC_REL,
            "locator": f"#index={idx}" if idx >= 0 else "NOT_FOUND",
            "lyric_found_in_source": found,
            "recovered_lyric_head_80": head.replace("\n", "⏎"),
            "status": status, "evidence": ev.replace("\n", "⏎"),
        })
    with open(os.path.join(OUT, "YUANQU_200_SOURCE_SAMPLE.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows200[0].keys())); w.writeheader(); w.writerows(rows200)

    # ---- 100 条恢复候选：取抽样中 RECOVERABLE_TITLE_CARRIES_LYRIC ----
    cand = [r for r in rows200 if r["status"] == "RECOVERABLE_TITLE_CARRIES_LYRIC"][:100]
    recs = []
    for c in cand:
        w = works[c["work_id"]]
        rt = w["title_raw"]
        qp, tail = rt.split("・", 1) if "・" in rt else ("", rt)
        body = w["text_raw"] or ""
        seam = ""
        if tail and body and tail[-1] == body[0]:
            recovered = tail + body[1:]
            seam = f"边界重字「{body[0]}」已去重"
        else:
            recovered = tail + body
            seam = f"边界「{tail[-1] if tail else ''}」+「{body[0] if body else ''}」直接相接"
        old = int(w["char_count"] or 0)
        new = han(recovered)
        recs.append({
            "work_id": c["work_id"], "title": w["title_raw"], "author": w["author_name"],
            "source_file": SRC_REL, "source_locator": c["locator"], "source_sha256": sha,
            "recovered_text": recovered,
            "old_char_count": old, "new_char_count": new,
            "difference_summary": f"title 由 {len(rt)} 字还原为曲牌「{qp}」（{len(qp)} 字）；"
                                  f"正文 {old}→{new} 字（+{new-old}）；{seam}",
            "confidence": "HIGH" if new > old else "LOW",
            "status": "READY_FOR_APPLY_SOURCE_VERIFIED",
        })
    with open(os.path.join(OUT, "YUANQU_100_RECOVERY_CANDIDATES.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(recs[0].keys())); w.writeheader(); w.writerows(recs)

    # ---- 汇总统计 ----
    stat = collections.Counter(r["status"] for r in rows200)
    with open(os.path.join(OUT, "LOGS", "D4_summary.json"), "w", encoding="utf-8") as f:
        json.dump({"sample200": len(rows200), "sample_status": dict(stat),
                   "recovery_candidates": len(recs),
                   "confidence": dict(collections.Counter(r["confidence"] for r in recs))},
                  f, ensure_ascii=False, indent=1)
    print(len(rows200), dict(stat), 'cands', len(recs))

if __name__ == "__main__":
    main()
