#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 WP-D1：把原書例詞與作品庫（works, 375,399 條）關聯。

不作「見 cipai 字段即認」的自動判定。規則：
  1. 以例詞前 12 字（去標點）在 works.text_norm 中做前綴檢索；
  2. 檢索結果再比對作者（去括注、異名）與全篇相似度；
  3. 分級：
       EXACT_MATCH      全篇去標點後完全相同
       PREFIX_MATCH     前綴一致且相似度 ≥0.95
       VARIANT_CANDIDATE 相似度 0.80–0.95（異文候選，不得直接採信）
       TITLE_ONLY       僅題名作者相符、正文差異大
       MULTI_HIT        命中多條且無法以作者排他
       NO_MATCH         未命中
"""
import json, os, re, sqlite3, difflib, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
SRC = os.path.join(ROOT, "raw", "r2_08", "cipai_examples.jsonl")
OUT = os.path.join(ROOT, "raw", "r2_08", "example_links.json")
TODAY = "2026-11-14"
CJK = re.compile(r"[^\u4e00-\u9fff]")


def norm(s):
    return CJK.sub("", s or "")


def clean_author(a):
    a = re.sub(r"[（(].*?[）)]", "", a or "")
    return re.sub(r"\s", "", a)


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    ex = [json.loads(l) for l in open(SRC, encoding="utf-8")]

    links = []
    for e in ex:
        t = norm(e["text"])
        lead = t[:12]
        au = clean_author(e["author"])
        hits = []
        if len(lead) >= 8:
            rows = con.execute(
                "SELECT work_id, author_name, author_canonical, title_norm, text_norm, dynasty,"
                " collection, source_id FROM works WHERE text_norm LIKE ? LIMIT 40",
                (lead + "%",)).fetchall()
            for r in rows:
                sim = difflib.SequenceMatcher(None, t, r["text_norm"]).ratio()
                hits.append({"work_id": r["work_id"], "author": r["author_name"],
                             "title": r["title_norm"], "dynasty": r["dynasty"],
                             "collection": r["collection"], "source_id": r["source_id"],
                             "sim": round(sim, 4),
                             "same_author": clean_author(r["author_name"]) == au
                             or clean_author(r["author_canonical"] or "") == au})
            if len(rows) == 0 and len(t) >= 10:
                rows = con.execute(
                    "SELECT work_id, author_name, author_canonical, title_norm, text_norm, dynasty,"
                    " collection, source_id FROM works WHERE text_norm LIKE ? LIMIT 20",
                    ("%" + t[2:10] + "%",)).fetchall()
                for r in rows:
                    sim = difflib.SequenceMatcher(None, t, r["text_norm"]).ratio()
                    hits.append({"work_id": r["work_id"], "author": r["author_name"],
                                 "title": r["title_norm"], "dynasty": r["dynasty"],
                                 "collection": r["collection"], "source_id": r["source_id"],
                                 "sim": round(sim, 4),
                                 "same_author": clean_author(r["author_name"]) == au
                                 or clean_author(r["author_canonical"] or "") == au})
        hits.sort(key=lambda h: (h["same_author"], h["sim"]), reverse=True)
        best = hits[0] if hits else None
        if not best:
            kind, wid = "NO_MATCH", None
        elif best["sim"] >= 0.999:
            kind, wid = "EXACT_MATCH", best["work_id"]
        elif best["sim"] >= 0.95:
            kind, wid = "PREFIX_MATCH", best["work_id"]
        elif best["sim"] >= 0.80:
            kind, wid = "VARIANT_CANDIDATE", best["work_id"]
        elif len(hits) > 1 and sum(1 for h in hits if h["sim"] >= 0.8) > 1:
            kind, wid = "MULTI_HIT", None
        else:
            kind, wid = "TITLE_ONLY", best["work_id"]
        links.append({
            "example_id": e["example_id"], "form_id": e["form_id"],
            "cipai_name": e["cipai_name"], "author": e["author"],
            "work_id": wid, "match_kind": kind,
            "match_score": best["sim"] if best else None,
            "n_hits": len(hits),
            "hit_authors": sorted({h["author"] for h in hits})[:5],
            "best_hit_title": best["title"] if best else None,
            "best_hit_collection": best["collection"] if best else None,
            "same_author": bool(best and best["same_author"]),
        })

    con.execute("DROP TABLE IF EXISTS example_work_links_r2_08")
    con.execute("""CREATE TABLE example_work_links_r2_08(
        example_id TEXT PRIMARY KEY, form_id TEXT, cipai_name TEXT, author TEXT,
        work_id TEXT, match_kind TEXT, match_score REAL, n_hits INT, hit_authors TEXT,
        best_hit_title TEXT, best_hit_collection TEXT, same_author INT, round TEXT)""")
    con.executemany("""INSERT INTO example_work_links_r2_08 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    [(l["example_id"], l["form_id"], l["cipai_name"], l["author"], l["work_id"],
                      l["match_kind"], l["match_score"], l["n_hits"],
                      "、".join(l["hit_authors"]), l["best_hit_title"],
                      l["best_hit_collection"], int(l["same_author"]), TODAY) for l in links])
    # 回寫 examples 表
    for l in links:
        con.execute("""UPDATE cipai_form_examples_r2_08 SET work_id=?, match_kind=?, match_score=?,
                       link_status=? WHERE example_id=?""",
                    (l["work_id"], l["match_kind"], l["match_score"],
                     "LINKED" if l["work_id"] else "UNLINKED", l["example_id"]))
    con.commit()
    st = {"n_examples": len(links),
          "by_kind": dict(collections.Counter(l["match_kind"] for l in links)),
          "n_same_author": sum(1 for l in links if l["same_author"]),
          "n_linked": sum(1 for l in links if l["work_id"]),
          "linked_pct": round(100 * sum(1 for l in links if l["work_id"]) / len(links), 1)}
    json.dump({"stats": st, "links": links}, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(st, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
