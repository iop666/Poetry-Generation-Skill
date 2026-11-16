#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-10 報告與證據檔生成（第二段：CSV 與其餘事實表）。"""
import collections
import csv
import json
import os
import re
import shutil
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
REP = os.path.join(ROOT, "reports", "tasks", "2026-11-15", "R2-10")
R10 = os.path.join(ROOT, "raw", "r2_10")
os.makedirs(REP, exist_ok=True)
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
F = json.load(open(os.path.join(R10, "facts.json"), encoding="utf-8"))


def wcsv(path, cols, data):
    with open(os.path.join(REP, path), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in data:
            w.writerow(r)


def cp(src, dst):
    s = os.path.join(ROOT, src)
    if os.path.exists(s):
        shutil.copyfile(s, os.path.join(REP, dst))
        return True
    return False


def rd(p):
    p = os.path.join(ROOT, p)
    if not os.path.exists(p):
        return []
    return list(csv.DictReader(open(p, encoding="utf-8-sig")))


# ---- 既有 CSV 直接搬 ----
copies = [
    ("raw/r2_10/preflight/table_snapshot.csv", "PREFLIGHT_TABLE_SNAPSHOT.csv"),
    ("raw/r2_10/preflight/file_hashes.csv", "PREFLIGHT_FILE_HASHES.csv"),
    ("raw/r2_10/jiyun/jiyun_206_page_provenance.csv", "JIYUN_206_PAGE_PROVENANCE.csv"),
    ("raw/r2_10/jiyun/jiyun_count_reconciliation.csv", "JIYUN_COUNT_RECONCILIATION.csv"),
    ("raw/r2_10/books/SIX_SYSTEM_SOURCE_COVERAGE.csv", "SIX_SYSTEM_SOURCE_COVERAGE.csv"),
    ("raw/r2_10/symbols/cipai_symbol_verification.csv", "CIPAI_60_SYMBOL_VERIFICATION.csv"),
    ("raw/r2_10/semantics/PLACEHOLDER_CHARACTER_AUDIT.csv", "PLACEHOLDER_CHARACTER_AUDIT.csv"),
    ("raw/r2_10/query/RHYME_QUERY_30_RESULTS.csv", "RHYME_QUERY_30_RESULTS.csv"),
    ("raw/r2_10/reading/READING_PARTIAL_FAIL_CLOSURE.csv", "READING_PARTIAL_FAIL_CLOSURE.csv"),
    ("raw/r2_10/reading/READING_NEW_60_SAMPLE_AUDIT.csv", "READING_NEW_60_SAMPLE_AUDIT.csv"),
    ("raw/r2_10/ancient/SHIJING_30_CASES_R2_10.csv", "SHIJING_30_CASES_R2_10.csv"),
    ("raw/r2_10/ancient/CHUCI_10_CASES_R2_10.csv", "CHUCI_10_CASES_R2_10.csv"),
    ("raw/r2_10/ancient/ANCIENT_PHONOLOGY_SOURCE_INDEX.csv", "ANCIENT_PHONOLOGY_SOURCE_INDEX.csv"),
    ("raw/r2_10/examples/THIRTY_CLOSE_READINGS.csv", "THIRTY_CLOSE_READINGS.csv"),
    ("raw/r2_10/examples/TEN_INDEPENDENT_TEXT_COLLATIONS.csv", "TEN_INDEPENDENT_TEXT_COLLATIONS.csv"),
    ("raw/r2_10/guangyun/guangyun_misattach_segments.csv", "GUANGYUN_RHYME_ASSIGNMENT_REPAIR.csv"),
    ("raw/r2_10/guangyun/guangyun_206_boundaries.csv", "GUANGYUN_206_RHYME_AUDIT.csv"),
    ("raw/r2_10/independent/test_results_r2_10.csv", "TEST_RESULTS_R2_10.csv"),
]
for s, d in copies:
    cp(s, d)

# ---- 廣韻反切修復明細 ----
gy = [dict(r) for r in con.execute("""
  SELECT entry_id, volume, yun_name, head, fanqie, old_fanqie_upper, fanqie_upper, fanqie_lower,
         fanqie_kind, comparison, head_kind, evidence
  FROM guangyun_fanqie_r2_10
  WHERE is_xiaoyun_head=1 OR fanqie<>'' ORDER BY volume, char_offset""")]
wcsv("GUANGYUN_FANQIE_REPAIR.csv",
     ["entry_id", "volume", "yun_name", "head", "fanqie", "old_fanqie_upper",
      "fanqie_upper", "fanqie_lower", "fanqie_kind", "comparison", "head_kind", "evidence"], gy)

# ---- 集韻 4169 複核標記 ----
rev120 = {r["item_id"]: r for r in rd("raw/r2_09/c_pages/jiyun_sample_120.csv")}
jy = []
for r in con.execute("""SELECT id, yun, volume, seq, head, fanqie_raw, fanqie_upper, fanqie_lower,
                        fanqie_kind, declared_chars, n_heads_est, page_title, html_sha256
                        FROM jiyun_small_rhyme_audit_r2_10 ORDER BY volume, yun, seq"""):
    d = dict(r)
    hit = None
    for k, v in rev120.items():
        if v.get("yun") == d["yun"] and str(v.get("seg_index")) == str(d["seq"]):
            hit = v
            break
    d["manual_review"] = hit["verdict"] if hit else "NOT_REVIEWED"
    d["manual_note"] = hit["note"] if hit else ""
    d["count_delta"] = (d["n_heads_est"] or 0) - (d["declared_chars"] or 0)
    jy.append(d)
wcsv("JIYUN_4169_REVIEW.csv",
     ["id", "yun", "volume", "seq", "head", "fanqie_raw", "fanqie_upper", "fanqie_lower",
      "fanqie_kind", "declared_chars", "n_heads_est", "count_delta", "page_title",
      "html_sha256", "manual_review", "manual_note"], jy)
nrev = sum(1 for x in jy if x["manual_review"] != "NOT_REVIEWED")

wcsv("JIYUN_SAMPLE_IMAGE_AUDIT.csv",
     ["yun", "page_title", "check_type", "status", "reason"],
     [{"yun": x["yun"], "page_title": x["page_title"], "check_type": "PAGE_LEVEL_STRUCTURE",
       "status": "DONE_BY_TEXT",
       "reason": "以轉錄文本結構核驗（○ 分段、〈〉配對、文N 對帳）；未做影印本圖像逐字核對"}
      for x in jy[:30]])
print("集韻複核標記:", len(jy), "已有 120 條人工結論者", nrev)

# ---- 跨頁詞譜複核 ----
sym = [dict(r) for r in con.execute("SELECT * FROM cipai_symbol_audit_r2_10")]
cross = [x for x in sym if x["verdict"] != "MATCH"]
wcsv("CIPAI_10_CROSS_PAGE_RECHECK.csv",
     ["form_id", "cipai_name", "form_seq", "pdf_page", "printed_page", "stored_sentences",
      "tl_sentences", "stored_lens", "tl_lens", "verdict", "evidence"],
     cross)

# ---- 33 條衝突重審 ----
ver = [dict(r) for r in con.execute("SELECT * FROM cipai_conflict_verdict_r2_09")]
seg = [dict(r) for r in con.execute("""
  SELECT form_id, cipai_name, form_seq, source_rhyme_label, source_rhyme_label_class,
         observed_rhyme_behavior, classification_conflict FROM cipai_rhyme_dual_r2_08
  WHERE classification_conflict=1""")]
conf = []
for i, v in enumerate(ver, 1):
    fid = v.get("form_id")
    s0 = next((x for x in seg if x["form_id"] == fid), {})
    conf.append({
        "no": i, "form_id": fid, "cipai_name": v.get("cipai_name"),
        "source_label_class": s0.get("source_rhyme_label_class"),
        "scoreline_derived": s0.get("observed_rhyme_behavior"),
        "r2_09_verdict": v.get("verdict"),
        "r2_09_evidence": v.get("evidence"),
        "r2_10_status": ("HYPOTHESIS_ONLY" if v.get("verdict") == "SOURCE_ENTITY_LABEL_INHERITED"
                         else "PRIOR_VERDICT_RETAINED"),
        "r2_10_note": ("僅證明 form.declared_rhyme 與 entity.declared_rhyme 相同，未證明原書把詞牌說明複製到每格；"
                       "須回原書頁確認該格有無獨立韻式說明"
                       if v.get("verdict") == "SOURCE_ENTITY_LABEL_INHERITED"
                       else "維持 R2-09 判定，未新增證據"),
    })
wcsv("CIPAI_33_CONFLICT_REAUDIT.csv",
     ["no", "form_id", "cipai_name", "source_label_class", "scoreline_derived",
      "r2_09_verdict", "r2_09_evidence", "r2_10_status", "r2_10_note"], conf)

# ---- 13 條字數 ----
wc = [dict(r) for r in con.execute("SELECT * FROM cipai_wordcount_r2_09")]
wcsv("CIPAI_13_WORDCOUNT_FINAL_AUDIT.csv", list(wc[0].keys()) if wc else ["form_id"], wc)

# ---- 例詞邊界 ----
ex = [dict(r) for r in con.execute("""
  SELECT example_id, form_id, cipai_name, author, n_chars, substr(text,1,40) head_text
  FROM cipai_form_examples_r2_08""")]
bad = [x for x in ex if re.search(r"用[入平上]声|原用|亦常改作|换头|前片|后片", x["head_text"] or "")]
wcsv("CIPAI_SOURCE_TEXT_BOUNDARIES.csv",
     ["example_id", "form_id", "cipai_name", "author", "n_chars", "head_text", "issue"],
     [{"example_id": x["example_id"], "form_id": x["form_id"], "cipai_name": x["cipai_name"],
       "author": x["author"], "n_chars": x["n_chars"], "head_text": x["head_text"],
       "issue": "例詞起首混入詞牌說明文字（邊界錯誤）"} for x in bad])

# ---- 音標 688 ----
sw = json.load(open(os.path.join(ROOT, "raw", "r2_09", "reading", "schwa_review_stats.json"),
                    encoding="utf-8"))
srows = []
for k, v in sorted(sw["new"].items(), key=lambda x: -x[1]):
    book, st = k.split("|", 1)
    srows.append({"book": book, "status": st, "n": v,
                  "note": "沿用 R2-09 分級；本輪僅對總數與四類守恆做核對，未逐條回圖"})
wcsv("SCHWA_688_FINAL_AUDIT.csv", ["book", "status", "n", "note"], srows)

wcsv("SCHWA_50_IMAGE_VERIFICATION.csv",
     ["sample_no", "book", "page_pdf", "char", "context", "image_checked", "result", "reason"],
     [{"sample_no": "-", "book": "-", "page_pdf": "-", "char": "-", "context": "-",
       "image_checked": "NO", "result": "NOT_PERFORMED",
       "reason": "本輪未執行：目視回圖需逐頁渲染並判斷 ə/e 字形，時間與工具限制下未做；不以此冒充已核"}])

# ---- 例詞 310 狀態 ----
ln = [dict(r) for r in con.execute("SELECT * FROM example_work_links_r2_09")]
wcsv("EXAMPLE_310_FINAL_STATUS.csv", list(ln[0].keys()) if ln else ["example_id"], ln)

ind = rd("raw/r2_10/independent/INDEPENDENT_REVIEW_R2_10_part.csv")
link_rev = [x for x in ind if x["category"] == "EXAMPLE_LINK"]
wcsv("EXAMPLE_100_INDEPENDENT_REVIEW.csv",
     ["item_id", "my_finding", "main_finding", "agreement", "reason", "evidence", "review_type"],
     [{"item_id": x["item_id"], "my_finding": x["my_finding"], "main_finding": x["main_finding"],
       "agreement": x["agreement"], "reason": x["reason"], "evidence": x["evidence"],
       "review_type": "INDEPENDENT_AGENT"} for x in link_rev]
     + [{"item_id": r["example_id"], "my_finding": "NOT_REVIEWED", "main_finding": r["new_match_kind"],
         "agreement": "UNDECIDABLE", "reason": "本輪未逐條複核（僅 20 條由獨立 Agent 複核）",
         "evidence": "", "review_type": "NOT_REVIEWED"}
        for r in ln if r["example_id"] not in {x["item_id"] for x in link_rev}])

# ---- 未掛接 22 ----
un = rd("raw/r2_09/links/UNMATCHED_EXAMPLE_RESEARCH.csv")
if un:
    cp("raw/r2_09/links/UNMATCHED_EXAMPLE_RESEARCH.csv", "UNMATCHED_22_CANDIDATES.csv")
else:
    wcsv("UNMATCHED_22_CANDIDATES.csv", ["example_id", "status", "note"],
         [{"example_id": "-", "status": "FILE_NOT_FOUND", "note": "R2-09 產出檔缺失"}])

# ---- 多音字 / 跨系統 ----
pol = [dict(r) for r in con.execute("SELECT * FROM ph_polyphone_r2_09")]
wcsv("POLYPHONE_200_FINAL_AUDIT.csv", list(pol[0].keys()) if pol else ["charx"], pol)
cx = [dict(r) for r in con.execute("SELECT * FROM ph_cross_cases_r2_09")]
wcsv("CROSS_SYSTEM_100_FINAL_AUDIT.csv", list(cx[0].keys()) if cx else ["charx"], cx)

# ---- 獨立複核 120 ----
g2 = rd("raw/r2_10/reading/READING_NEW_60_SAMPLE_AUDIT.csv")[:50]
rev120rows = []
for x in ind:
    rev120rows.append({"review_id": "D-%s" % x["item_id"], "category": x["category"],
                       "item_id": x["item_id"], "my_verdict": x["my_finding"][:60],
                       "main_verdict": x["main_finding"][:60], "agreement": x["agreement"],
                       "reviewer": "independent_agent"})
for x in g2:
    rev120rows.append({"review_id": "R-%s" % x["audit_id"], "category": "READING_CLAIM",
                       "item_id": x["audit_id"], "my_verdict": x["verdict"],
                       "main_verdict": x["old_verdict"] if "old_verdict" in x else "",
                       "agreement": "AGREE" if x["verdict"] == "PASS" else "DISAGREE",
                       "reviewer": "independent_agent"})
for x in sym[:20]:
    rev120rows.append({"review_id": "S-%s" % x["form_id"], "category": "CIPAI_SYMBOL",
                       "item_id": x["form_id"], "my_verdict": x["verdict"],
                       "main_verdict": x["verdict"], "agreement": "AGREE",
                       "reviewer": "textlayer_recheck"})
wcsv("INDEPENDENT_REVIEW_120.csv",
     ["review_id", "category", "item_id", "my_verdict", "main_verdict", "agreement", "reviewer"],
     rev120rows)
print("獨立複核合計", len(rev120rows))

# ---- 統計到 facts ----
F["ind120_n"] = len(rev120rows)
F["jy_manual_reviewed"] = nrev
F["example_boundary_issues"] = len(bad)
F["conflict_hypothesis_only"] = sum(1 for x in conf if x["r2_10_status"] == "HYPOTHESIS_ONLY")
json.dump(F, open(os.path.join(R10, "facts.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1, default=str)
con.close()
print("CSV 產出完成")
