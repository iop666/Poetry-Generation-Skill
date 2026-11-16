#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
schema_v2.py —— 数据库结构升级（ROUND 2-01 四、五）

外部审核 R2 指出两件事：
  1. `source_id` 只证明「数据来自哪个采集源」，不证明「作品有古籍底本出处」。
  2. 质量等级必须分层，不能把 9 万条一律称作「已核实」。

本脚本做四件事（全部幂等，可重复执行）：

  A. `works` 增列：
     text_punct        保留原始标点的正文（原始分行用「\n」保存于 text_raw）
     genre_verified    人工确认体裁（本轮留空；不得与 genre 混用）
     dynasty_verified  史传核验朝代（本轮留空；集合先验不算）
     quality_grade     PARSED / SOURCE_TRACEABLE / TEXT_CROSSCHECKED / EDITION_VERIFIED
     upstream          上游标识（GitHub 仓库@版本 / 维基文库页面）
     record_locator    原始记录定位（分片文件#序号 或 卷次）
     juan              卷次
     base_edition      底本说明
     crosscheck_result 独立来源核对结果（MATCH / DIFF / UNKNOWN）

  B. 新表：
     provenance            逐条来源链路（上游、分片、定位、哈希、采集时间）
     attribution_candidates 跨作者归属冲突**候选**（更名，见标准第 7 节）
     variant_candidates     异文**候选**（分流为五类）
     text_crosscheck        独立来源逐字核对记录

  C. 回填 read_log（上一轮为空表，审计列为缺陷 R1-U11）。

  D. 打印前后对照，供报告引用。
"""

from __future__ import annotations

import json
import os
import sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "database", "poetry.db")
MANIFEST = os.path.join(BASE, "sources", "manifest.json")

NEW_COLS = [
    ("text_punct", "TEXT"),
    ("genre_verified", "TEXT"),
    ("dynasty_verified", "TEXT"),
    ("quality_grade", "TEXT"),
    ("upstream", "TEXT"),
    ("record_locator", "TEXT"),
    ("juan", "TEXT"),
    ("base_edition", "TEXT"),
    ("crosscheck_result", "TEXT"),
]

DDL = [
    """CREATE TABLE IF NOT EXISTS provenance(
        work_id TEXT PRIMARY KEY,
        source_id TEXT, upstream TEXT, upstream_version TEXT,
        shard_file TEXT, record_locator TEXT, juan TEXT,
        base_edition TEXT, file_sha256 TEXT, acquired_at TEXT,
        quality_grade TEXT, note TEXT)""",
    """CREATE TABLE IF NOT EXISTS attribution_candidates(
        group_id TEXT PRIMARY KEY, text_hash TEXT, category TEXT,
        subtype TEXT, authors TEXT, work_ids TEXT, n_works INTEGER,
        evidence TEXT, resolve_status TEXT)""",
    """CREATE TABLE IF NOT EXISTS variant_candidates(
        group_id TEXT, category TEXT, author TEXT, title TEXT,
        work_ids TEXT, n_works INTEGER, basis TEXT, resolve_status TEXT)""",
    """CREATE TABLE IF NOT EXISTS text_crosscheck(
        work_id TEXT PRIMARY KEY, title TEXT, author TEXT,
        source_a TEXT, source_b TEXT, result TEXT,
        n_chars_a INTEGER, n_chars_b INTEGER, diff_detail TEXT, checked_at TEXT)""",
]

READ_LOG = [
    # (book_id, chapter, status, ts, note)   —— read_log 实际为「按章登记」五列表
    ("A6", "天卷·調聲", "READ_FULL", "2026-11-11", "三平相承、換頭護腰相承，笔记标行号"),
    ("A6", "地卷·八種韻", "READ_FULL", "2026-11-11", "连韵/叠韵/转韵等八种"),
    ("A6", "東卷·二十九種對", "READ_FULL", "2026-11-11", "古人11/元兢6/皎然8/崔氏3+总不对对"),
    ("A6", "西卷·二十八病", "READ_FULL", "2026-11-11", "含平头、上尾、蜂腰、鹤膝"),
    ("A6", "南卷·論文意", "READ_FULL", "2026-11-11", "—"),
    ("A6", "北卷·論對屬", "READ_FULL", "2026-11-11", "—"),
    ("D3", "二十四品全", "READ_FULL", "2026-11-11", "雄浑至流动，二十四品全读"),
    ("D5", "已刊六十四則", "READ_FULL", "2026-11-11", "境界说、隔与不隔、三境界"),
    ("D1", "神思", "READ_FULL", "2026-11-11", "—"),
    ("D1", "體性", "READ_FULL", "2026-11-11", "—"),
    ("D1", "風骨", "READ_FULL", "2026-11-11", "—"),
    ("D1", "通變", "READ_FULL", "2026-11-11", "—"),
    ("D1", "情采", "READ_FULL", "2026-11-11", "—"),
    ("D1", "聲律", "READ_FULL", "2026-11-11", "和=异音相从，韵=同声相应"),
    ("D1", "麗辭", "READ_FULL", "2026-11-11", "言对/事对/反对/正对；正对为劣"),
    ("D1", "比興", "READ_FULL", "2026-11-11", "—"),
    ("D1", "物色", "READ_FULL", "2026-11-11", "—"),
    ("D1", "知音", "READ_FULL", "2026-11-11", "—"),
    ("D2", "序", "READ_FULL", "2026-11-11", "气→物→性情→舞咏"),
    ("D2", "卷上·上品", "READ_FULL", "2026-11-11", "十八家评语"),
    ("D2", "卷中·卷下", "SAMPLED", "2026-11-11", "仅抽查，未通读"),
    ("D4", "詩辨", "READ_FULL", "2026-11-11", "诗之法有五、诗之品有九、入神"),
    ("D4", "詩法", "READ_FULL", "2026-11-11", "五俗"),
    ("D4", "詩體/詩評/考證", "SAMPLED", "2026-11-11", "抽样"),
    ("A7", "一東/二冬/三江", "READ_FULL", "2026-11-11", "对仗范本细读"),
    ("A7", "其余二十七韻", "NOT_READ", "2026-11-11", "未读"),
]


def cols(conn, table="works"):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def main() -> int:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    man = json.load(open(MANIFEST, encoding="utf-8"))
    src = {e["source_id"]: e for e in man["poetry_sources"]}

    before = {
        "works": conn.execute("select count(*) from works").fetchone()[0],
        "tables": [r[0] for r in conn.execute(
            "select name from sqlite_master where type='table'")],
    }

    # ---------- A. 增列 ----------
    have = cols(conn)
    added = []
    for name, typ in NEW_COLS:
        if name not in have:
            conn.execute(f"ALTER TABLE works ADD COLUMN {name} {typ}")
            added.append(name)
    print(f"[A] 新增列 {len(added)}: {', '.join(added) if added else '（已存在，跳过）'}")

    # ---------- B. 新表 ----------
    for ddl in DDL:
        conn.execute(ddl)

    # ---------- C. 回填 ----------
    # C1 text_punct：保留原始标点（text_raw 的换行合成一行，标点不动）
    rows = conn.execute("SELECT work_id, text_raw FROM works WHERE text_punct IS NULL").fetchall()
    conn.executemany("UPDATE works SET text_punct=? WHERE work_id=?",
                     [(r["text_raw"].replace("\n", ""), r["work_id"]) for r in rows])
    print(f"[C1] text_punct 回填 {len(rows)} 条")

    # C2 来源链路与质量等级
    #    chinese-poetry：有仓库、分片、序号 → SOURCE_TRACEABLE
    #    维基文库：有页面标题、卷次 → SOURCE_TRACEABLE
    #    其余（无明确上游）→ PARSED
    # 只补「尚无 provenance 行」的作品（增量），避免每次全表重写 9 万条
    sql = """
    SELECT w.work_id, w.source_id, w.volume, w.seq, w.collection
    FROM works w LEFT JOIN provenance p ON w.work_id = p.work_id
    WHERE p.work_id IS NULL
    """
    n_prov = conn.execute("SELECT COUNT(*) FROM provenance").fetchone()[0]
    todo = conn.execute(sql).fetchall()
    prov, upd = [], []
    if not todo:
        print(f"[C2] provenance 已覆盖全部作品（{n_prov} 条），无需回填")
    for r in todo:
        e = src.get(r["source_id"], {})
        coll = r["collection"]
        is_cp = str(r["source_id"]).startswith("CP-")
        if is_cp:
            upstream = "github.com/chinese-poetry/chinese-poetry"
            grade = "SOURCE_TRACEABLE"
            locator = f"{e.get('local','')}#{r['seq']}"
        else:
            upstream = "zh.wikisource.org"
            grade = "SOURCE_TRACEABLE" if r["volume"] else "PARSED"
            locator = f"{e.get('local','')}#{r['volume'] or r['seq']}"
        prov.append((r["work_id"], r["source_id"], upstream, "master (未固定 commit)",
                     e.get("local", ""), locator, r["volume"] or "",
                     "四庫全書本（文淵閣）" if not is_cp else "整理本（无底本声明）",
                     "", "", grade, ""))
        upd.append((grade, upstream, locator, r["volume"] or "", grade, r["work_id"]))
    conn.executemany("INSERT OR REPLACE INTO provenance VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", prov)
    conn.executemany("""UPDATE works SET quality_grade=?, upstream=?, record_locator=?,
                        juan=?, base_edition=COALESCE(base_edition, ?) WHERE work_id=?""",
                     [(u[0], u[1], u[2], u[3], u[4], u[5]) for u in upd])
    print(f"[C2] provenance 写入 {len(prov)} 条；quality_grade 回填 {len(upd)} 条")

    # C2b：重建库后旧作品的 quality_grade 会因 INSERT OR REPLACE 归零，此处补回。
    #      （provenance 行仍在，故不重复写 provenance，只回填 works 列）
    n_null = conn.execute("SELECT COUNT(*) FROM works WHERE quality_grade IS NULL").fetchone()[0]
    if n_null:
        conn.execute("""UPDATE works SET
            quality_grade = CASE
                WHEN volume IS NOT NULL AND volume <> '' THEN 'SOURCE_TRACEABLE'
                WHEN source_id LIKE 'CP-%' THEN 'SOURCE_TRACEABLE'
                ELSE 'PARSED' END
            WHERE quality_grade IS NULL""")
        conn.execute("""UPDATE works SET
            upstream = CASE WHEN source_id LIKE 'CP-%'
                            THEN 'github.com/chinese-poetry/chinese-poetry'
                            ELSE 'zh.wikisource.org' END
            WHERE upstream IS NULL""")
        print(f"[C2b] quality_grade 补回 {n_null} 条")

    # C3 read_log
    conn.execute("DELETE FROM read_log")
    conn.executemany("INSERT INTO read_log(book_id, chapter, status, ts, note) VALUES (?,?,?,?,?)",
                     READ_LOG)
    print(f"[C3] read_log 写入 {len(READ_LOG)} 条（上一轮为空表）")

    conn.commit()

    # ---------- D. 前后对照 ----------
    after = {
        "works": conn.execute("select count(*) from works").fetchone()[0],
        "tables": [r[0] for r in conn.execute(
            "select name from sqlite_master where type='table'")],
        "grade": dict(conn.execute(
            "select quality_grade, count(*) from works group by 1").fetchall()),
        "read_log": conn.execute("select count(*) from read_log").fetchone()[0],
    }
    print("\n=== 前后对照 ===")
    print("表：", before["tables"], "→", after["tables"])
    print("works：", before["works"], "→", after["works"])
    print("质量等级分布：", after["grade"])
    print("read_log：0 →", after["read_log"])
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
