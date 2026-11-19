#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-15 测试：公开归档测试（A）与本地数据库测试（B）分层。

用法：
    python3 tools/r2_15_tests.py                 # 自动找 database/poetry.db
    python3 tools/r2_15_tests.py --db /path/x.db # 指定数据库
    POETRY_DB=/path/x.db python3 tools/r2_15_tests.py

没有数据库时，B 组整体标 NOT RUN，不计为失败。
"""
import argparse
import csv
import hashlib
import os
import sqlite3
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
DBROOT = TOOLS.parent
PROJECT = DBROOT.parent
OUT = DBROOT / "reports/tasks/2026-11-20/R2-15"

R = []


def t(grp, i, name, cond, actual="", expect=""):
    if cond is None:
        R.append((grp, i, name, "NOT RUN", str(actual)[:70], str(expect)[:40]))
    else:
        R.append((grp, i, name, "PASS" if cond else "FAIL",
                  str(actual)[:70], str(expect)[:40]))


def read(p):
    return Path(p).read_text(encoding="utf-8")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def group_a():
    inc = read(TOOLS / "github_sync.py")
    t("A", "A01", "同步白名单不含 r2_04_evidence 目录",
      '"poetry-database/raw/r2_04_evidence",' not in inc)
    t("A", "A02", "同步黑名单含 full/ 与 chapters/",
      "/r2_04_evidence/full/" in inc and "/r2_04_evidence/chapters/" in inc)
    t("A", "A03", "README 不再含旧作品数 90,279", "90,279" not in read(PROJECT / "README.md"))
    t("A", "A04", "README 含当前作品数 375,399", "375,399" in read(PROJECT / "README.md"))
    t("A", "A05", "README 声明不是已发布 Skill",
      "不是" in read(PROJECT / "README.md") and "Skill" in read(PROJECT / "README.md"))
    need = ["COPYRIGHT_SYNC_AUDIT.md", "COPYRIGHT_HISTORY_IMPACT.md",
            "WORKS_339_EVIDENCE_CLOSURE.md", "TEST_EXPECTATION_CHANGELOG_R2_15.md"]
    miss = [n for n in need if not (OUT / n).exists()]
    t("A", "A06", "R2-15 必需交付文档齐备", not miss, f"缺 {miss}" if miss else "4/4")
    idx = PROJECT / "poetry-database/reports/tasks"
    rounds = [p for p in idx.glob("*/*/COMPLETE_REPORT.md")]
    t("A", "A07", "逐轮 COMPLETE_REPORT 数量 ≥15", len(rounds) >= 15, len(rounds), ">=15")
    t("A", "A08", "R2-15 报告目录已建立", OUT.exists())
    t("A", "A09", "版权历史影响分析存在", (OUT / "COPYRIGHT_HISTORY_IMPACT.md").exists())
    t("A", "A10", "339 证据闭合表 339 行",
      len(list(csv.DictReader(open(OUT / "WORKS_339_EVIDENCE_CLOSURE.csv", encoding="utf-8-sig")))) == 339
      if (OUT / "WORKS_339_EVIDENCE_CLOSURE.csv").exists() else False)
    t("A", "A11", "AGENTS 仍声明 Phase 3 未授权",
      "未授权" in read(PROJECT / "AGENTS.md"))
    # 本地存在不等于公开：确认 books/ 与 full/ 未进白名单展开
    import importlib.util
    spec = importlib.util.spec_from_file_location("gs", TOOLS / "github_sync.py")
    gs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gs)
    rels = [x[0] for x in gs.collect()]
    bad = [r for r in rels if "/r2_04_evidence/full/" in r
           or "/r2_04_evidence/chapters/" in r or r.startswith("books/")]
    t("A", "A12", "白名单展开后无版权正文", not bad, f"{len(bad)} 条", 0)


def group_b(db):
    if db is None or not Path(db).exists():
        for i, name in [
            ("B01", "数据库可只读打开"), ("B02", "integrity_check=ok"),
            ("B03", "works=375,399"), ("B04", "authors=20,809"),
            ("B05", "sources=941"), ("B06", "R2-13 三表行数"),
            ("B07", "无 _r2_15 新表"), ("B08", "DB SHA 与 R2-14 基线一致"),
        ]:
            t("B", i, name, None, "no db", "")
        return
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    q = lambda s: con.execute(s).fetchone()[0]
    t("B", "B01", "数据库可只读打开", True, str(db)[-40:])
    t("B", "B02", "integrity_check=ok", q("PRAGMA integrity_check") == "ok",
      q("PRAGMA integrity_check"))
    t("B", "B03", "works=375,399", q("SELECT count(*) FROM works") == 375399,
      q("SELECT count(*) FROM works"))
    t("B", "B04", "authors=20,809", q("SELECT count(*) FROM authors") == 20809,
      q("SELECT count(*) FROM authors"))
    t("B", "B05", "sources=941", q("SELECT count(*) FROM sources") == 941,
      q("SELECT count(*) FROM sources"))
    r213 = (q("SELECT count(*) FROM work_text_revision_candidates_r2_13"),
            q("SELECT count(*) FROM work_author_variant_r2_13"),
            q("SELECT count(*) FROM yuanqu_text_audit_r2_13"))
    t("B", "B06", "R2-13 三表 = 339/476/4,510", r213 == (339, 476, 4510), r213)
    n15 = q("SELECT count(*) FROM sqlite_master WHERE type='table' AND name LIKE '%_r2_15'")
    t("B", "B07", "无 _r2_15 新表", n15 == 0, n15)
    base = (DBROOT / "reports/tasks/2026-11-16/R2-14/LOGS/preflight.json")
    import json
    b = json.loads(base.read_text(encoding="utf-8"))["sha256"] if base.exists() else ""
    cur = sha256(db)
    t("B", "B08", "DB SHA 与 R2-14 基线一致", cur == b, cur[:16], b[:16])
    con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("POETRY_DB"))
    a = ap.parse_args()
    db = a.db or str(DBROOT / "database/poetry.db")
    group_a()
    group_b(db)

    out = OUT / "LOGS"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "tests_r2_15.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["group", "id", "name", "result", "actual", "expect"])
        w.writerows(R)

    p = sum(1 for x in R if x[3] == "PASS")
    fl = sum(1 for x in R if x[3] == "FAIL")
    nr = sum(1 for x in R if x[3] == "NOT RUN")
    for x in R:
        if x[3] != "PASS":
            print(x[3], x[1], x[2], "|", x[4])
    print(f"total={len(R)} pass={p} fail={fl} not_run={nr}")
    return 0 if fl == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
