#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-10 工作包 0：执行前冻结与数据库状态固定。

产出的数字全部由本脚本实时计算，不引用任何历史报告里的值。
"""
import csv
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
OUT = os.path.join(ROOT, "raw", "r2_10", "preflight")
REP = os.path.join(ROOT, "reports", "tasks", "2026-11-15", "R2-10")
os.makedirs(OUT, exist_ok=True)
os.makedirs(REP, exist_ok=True)


def sha256_file(p, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    res = {}
    st = os.stat(DB)
    res["db_path"] = DB
    res["db_bytes"] = st.st_size
    res["db_mib"] = round(st.st_size / 1024 / 1024, 2)
    res["db_mb_decimal"] = round(st.st_size / 1e6, 2)
    res["db_mtime"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))
    res["db_sha256"] = sha256_file(DB)

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    prag = {}
    prag["integrity_check"] = [r[0] for r in con.execute("PRAGMA integrity_check")]
    prag["foreign_key_check"] = [dict(r) for r in con.execute("PRAGMA foreign_key_check")]
    prag["page_count"] = con.execute("PRAGMA page_count").fetchone()[0]
    prag["page_size"] = con.execute("PRAGMA page_size").fetchone()[0]
    prag["journal_mode"] = con.execute("PRAGMA journal_mode").fetchone()[0]
    prag["freelist_count"] = con.execute("PRAGMA freelist_count").fetchone()[0]
    prag["auto_vacuum"] = con.execute("PRAGMA auto_vacuum").fetchone()[0]
    prag["application_id"] = con.execute("PRAGMA application_id").fetchone()[0]
    prag["user_version"] = con.execute("PRAGMA user_version").fetchone()[0]
    # 页数与页大小乘积应与文件大小一致（否则说明有 WAL 或残留）
    prag["page_count_x_page_size"] = prag["page_count"] * prag["page_size"]
    prag["size_matches_pages"] = prag["page_count_x_page_size"] == st.st_size
    res["pragma"] = prag

    # WAL / SHM 残留
    res["wal_files"] = {}
    for suf in ("-wal", "-shm", "-journal"):
        p = DB + suf
        res["wal_files"][suf] = os.path.getsize(p) if os.path.exists(p) else None

    # 对象清单
    objs = []
    for r in con.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master "
        "WHERE type IN ('table','view','index') ORDER BY type,name"
    ):
        nm = r["name"]
        n = None
        if r["type"] in ("table", "view"):
            try:
                n = con.execute('SELECT count(*) FROM "%s"' % nm).fetchone()[0]
            except Exception as e:
                n = "ERR:" + str(e)[:30]
        objs.append({
            "type": r["type"], "name": nm, "tbl_name": r["tbl_name"],
            "n_rows": n,
            "has_sql": 1 if r["sql"] else 0,
        })
    res["n_tables"] = sum(1 for o in objs if o["type"] == "table")
    res["n_views"] = sum(1 for o in objs if o["type"] == "view")
    res["n_indexes"] = sum(1 for o in objs if o["type"] == "index")

    # 按轮次后缀归组
    def era(name):
        for suf in ("_r2_07", "_r2_08", "_r2_09", "_r2_10", "_r2_06", "_r2_05"):
            if suf in name:
                return suf.lstrip("_")
        return "legacy"

    eras = {}
    for o in objs:
        if o["type"] != "table":
            continue
        eras.setdefault(era(o["name"]), []).append(o)
    res["eras"] = {k: {"n_tables": len(v), "n_rows": sum(x["n_rows"] for x in v if isinstance(x["n_rows"], int))}
                   for k, v in eras.items()}

    with open(os.path.join(OUT, "table_snapshot.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["type", "name", "tbl_name", "n_rows", "era"])
        for o in objs:
            w.writerow([o["type"], o["name"], o["tbl_name"], o["n_rows"],
                        era(o["name"]) if o["type"] == "table" else ""])

    # 磁盘
    df = subprocess.run(["df", "-k", ROOT], capture_output=True, text=True).stdout
    res["df_raw"] = df.strip().splitlines()[-1]
    parts = res["df_raw"].split()
    res["disk_avail_gib"] = round(int(parts[3]) / 1024 / 1024, 2)

    # 前序交付包
    pkg = []
    for d in sorted(os.listdir(os.path.expanduser("<LOCAL_WORKBUDDY>/2026-11-14"))):
        if d.endswith(".zip") and "R2-0" in d:
            p = os.path.join(os.path.expanduser("<LOCAL_WORKBUDDY>/2026-11-14"), d)
            pkg.append({"file": d, "bytes": os.path.getsize(p), "sha256": sha256_file(p)})
    res["packages"] = pkg

    # 前序报告的关键交付文件哈希
    keyfiles = []
    for rnd in ("R2-07", "R2-08", "R2-09"):
        d = os.path.join(ROOT, "reports", "tasks", "2026-11-14", rnd)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            p = os.path.join(d, fn)
            if not os.path.isfile(p):
                continue
            if fn.endswith((".png", ".pdf", ".zip")):
                continue
            keyfiles.append({"round": rnd, "file": fn, "bytes": os.path.getsize(p),
                             "sha256": sha256_file(p)})
    res["keyfiles"] = keyfiles

    with open(os.path.join(OUT, "state.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    with open(os.path.join(OUT, "file_hashes.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["category", "name", "bytes", "sha256"])
        w.writerow(["database", os.path.basename(DB), res["db_bytes"], res["db_sha256"]])
        for p in pkg:
            w.writerow(["package", p["file"], p["bytes"], p["sha256"]])
        for k in keyfiles:
            w.writerow(["report_" + k["round"], k["file"], k["bytes"], k["sha256"]])

    print(json.dumps({k: res[k] for k in
                      ["db_bytes", "db_mib", "db_sha256", "n_tables", "n_views", "n_indexes",
                       "wal_files", "eras", "disk_avail_gib"]}, ensure_ascii=False, indent=1))
    print("pragma:", json.dumps(prag, ensure_ascii=False))
    con.close()


if __name__ == "__main__":
    main()
