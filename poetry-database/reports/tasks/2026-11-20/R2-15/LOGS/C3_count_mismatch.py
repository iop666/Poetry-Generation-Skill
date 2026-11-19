#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-15 / C3：214 个 COUNT_MISMATCH 来源的成因定位审计。

方法
----
1. works_n  ← `SELECT count(*) FROM works GROUP BY source_id`（库内实际条数）
2. json_n    ← 直接解析 `sources.local_path` 的 JSON 数组长度（dict 取最大 list 字段）
   解析失败时区分「抓取失败占位页（<1KB 文本）」与「真实损坏」
3. diff = works_n - json_n
4. 成因按 diff 方向 + 量级 + 文件结构判定（规则见 probable_cause 说明）
5. 对 |diff| 最大的 10 个来源抽 3 条 works，按 title_raw 在 JSON 中定位，
   判断缺口是「过滤」（能定位、位置单调、有间隔）还是「错位/替换」（定位不到）

只读，零写入。输出：
  SOURCE_COUNT_MISMATCH_214.csv
  LOGS/C3_stats.json
"""
import collections
import csv
import json
import re
import os
import sqlite3

BASE = "<PROJECT_ROOT>/poetry-database"
DB = os.path.join(BASE, "database", "poetry.db")
OUT = os.path.join(BASE, "reports", "tasks", "2026-11-20", "R2-15")
LOG = os.path.join(OUT, "LOGS")
PREV = os.path.join(BASE, "reports", "tasks", "2026-11-16", "R2-14")


HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002ffff]")


def rec_text(r):
    p = r.get("paragraphs") or r.get("content") or ""
    return "".join(p) if isinstance(p, list) else str(p)


def load_json_len(path):
    """返回 (json_n, status, first_titles)"""
    try:
        with open(path, "rb") as f:
            head = f.read(400)
        txt = head.decode("utf-8", "ignore").strip()
        if not txt.startswith("[") and not txt.startswith("{"):
            return None, "NOT_JSON_TEXT", [], []
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:  # noqa: BLE001
        return None, f"PARSE_ERROR:{type(e).__name__}", [], []
    if isinstance(data, list):
        recs = data
    elif isinstance(data, dict):
        lists = [(len(v), k, v) for k, v in data.items() if isinstance(v, list)]
        if not lists:
            return None, "NO_LIST_FIELD", [], []
        recs = max(lists)[2]
    else:
        return None, "UNSUPPORTED_ROOT", [], []
    titles, short = [], []
    for r in recs:
        if isinstance(r, dict):
            t = str(r.get("title") or r.get("rhythmic") or "")
            titles.append(t)
            n_han = len(HAN.findall(rec_text(r)))
            if n_han < 8:
                short.append((t, str(r.get("author") or ""), n_han))
    return len(recs), "OK", titles, short


def main():
    os.makedirs(LOG, exist_ok=True)
    con = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
    src = {r[0]: r for r in con.execute(
        "SELECT source_id, local_path, format, parse_status, bytes, sha256 FROM sources")}
    works_n = dict(con.execute("SELECT source_id, count(*) FROM works GROUP BY source_id"))
    path_use = collections.Counter(r[1] for r in src.values())

    prev = {r["source_id"]: r for r in
            csv.DictReader(open(os.path.join(PREV, "LOGS", "seq2_verify.csv"),
                                encoding="utf-8-sig"))}
    target = [s for s, r in prev.items() if r["verdict"] == "COUNT_MISMATCH"]

    rows = []
    for sid in target:
        s = src.get(sid)
        if not s:
            rows.append({"source_id": sid, "local_path": "", "works_n": 0, "json_n": "",
                         "diff": "", "probable_cause": "SOURCE_ROW_MISSING",
                         "suggested_match_rule": "", "verified_sample": "",
                         "note": "sources 表无此 source_id"})
            continue
        path, fmt, pstat, nbytes, sha = s[1], s[2], s[3], s[4], s[5]
        n = works_n.get(sid, 0)
        full = os.path.join(BASE, path)
        jn, status, titles, short = load_json_len(full)

        # ---- 成因判定 ----
        if jn is None:
            if status == "NOT_JSON_TEXT" and (nbytes or 0) < 2048:
                cause = "FILE_IS_FETCH_ERROR_PAGE"
                rule = "文件不可用：需重新抓取该分片，禁止按当前文件对齐"
            else:
                cause = "FILE_UNPARSEABLE"
                rule = "文件损坏：需重新抓取后再对齐"
        else:
            diff = n - jn
            if path_use[path] > 1:
                cause = "DUP_SOURCE_REGISTRATION"
                rule = f"同一 local_path 被 {path_use[path]} 个 source_id 登记，需按 seq 区间拆分归属"
            elif n == 0 and jn > 0:
                cause = "NOT_IMPORTED"
                rule = "该分片未入库：检查导入日志，按整片重放"
            elif diff > 0 and jn < n * 0.5:
                cause = "FILE_REPLACED_SMALLER"
                rule = "库内条数远超现存文件：文件疑被替换，需用 sha256 追溯旧版"
            elif diff > 0:
                cause = "DUPLICATE_ROWS_IN_DB"
                rule = "库内重复：按 (title_raw, text 前 30 字) 去重后复算"
            elif jn - len(short) == n:
                cause = "FILTER_TEXT_LT8"
                rule = "导入器丢弃正文 CJK<8 的残句；json_n - 短句数 = works_n，可精确复算"
            elif (jn - len(short)) - n > 0:
                cause = "FILTER_TEXT_LT8_PLUS_EXTRA"
                rule = ("短句过滤 + 额外丢弃；json_n - short = works_n + "
                        f"{(jn - len(short)) - n}，多丢的条目需按 title 逐条核")
            elif abs(diff) <= max(2, int(0.002 * jn)):
                cause = "IMPORT_FILTER_EDGE"
                rule = "少量过滤（空正文/非诗记录）：按 title_raw 精确匹配即可对齐"
            elif abs(diff) <= 0.05 * jn:
                cause = "IMPORT_FILTER"
                rule = "导入过滤（重复标题/空段落）：按 title_raw 精确匹配，缺口计为未入库"
            else:
                cause = "SHARD_OVERLAP_OR_SPLIT"
                rule = "跨片重叠或分片切分：按 (title_raw, author) 联合键去重后对齐"

        rows.append({
            "source_id": sid, "local_path": path, "works_n": n,
            "json_n": "" if jn is None else jn,
            "diff": "" if jn is None else n - jn,
            "probable_cause": cause, "suggested_match_rule": rule,
            "verified_sample": "", "note": f"format={fmt}; status={status}; bytes={nbytes}",
            "_titles": titles, "_short": short,
        })

    # ---- 最大差值 10 个来源的抽样核对 ----
    ranked = sorted([r for r in rows if r["diff"] != ""], key=lambda r: -abs(r["diff"]))[:10]
    for r in ranked:
        sid = r["source_id"]
        ws = con.execute("""SELECT work_id, title_raw, seq FROM works WHERE source_id=?
                            ORDER BY seq LIMIT 3""", (sid,)).fetchall()
        titles = r["_titles"]
        pos = {}
        for i, t in enumerate(titles):
            pos.setdefault(t, i)
        hits, detail = 0, []
        for wid, title, seq in ws:
            idx = pos.get(title)
            if idx is None:
                detail.append(f"{wid[-6:]}:{title[:12]}=MISS")
            else:
                hits += 1
                detail.append(f"{wid[-6:]}:{title[:12]}@json#{idx}")
        r["verified_sample"] = f"{hits}/3 hit; " + "; ".join(detail)
        if hits == 3:
            idxs = [pos[t] for _, t, _ in ws]
            mono = all(a < b for a, b in zip(idxs, idxs[1:]))
            r["verified_sample"] += f"; monotonic={'Y' if mono else 'N'}"
            r["note"] += "；抽样可定位 → 缺口属过滤，非错位"
        elif hits == 0:
            r["note"] += "；抽样全部定位不到 → 文件与库内容不匹配（替换/错位）"
        else:
            r["note"] += "；抽样部分命中 → 混合型，需逐条核对"

    cols = ["source_id", "local_path", "works_n", "json_n", "diff", "probable_cause",
            "suggested_match_rule", "verified_sample", "note"]
    with open(os.path.join(OUT, "SOURCE_COUNT_MISMATCH_214.csv"), "w",
              encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    stats = {
        "target_from_seq2_verify": len(target),
        "rows_written": len(rows),
        "cause_distribution": dict(collections.Counter(r["probable_cause"] for r in rows)),
        "diff_sign": dict(collections.Counter(
            "works>json" if isinstance(r["diff"], int) and r["diff"] > 0
            else "works<json" if isinstance(r["diff"], int) and r["diff"] < 0
            else "n/a" for r in rows)),
        "sum_abs_diff": sum(abs(r["diff"]) for r in rows if isinstance(r["diff"], int)),
        "top10": [{"source_id": r["source_id"], "diff": r["diff"],
                   "cause": r["probable_cause"], "sample": r["verified_sample"]}
                  for r in ranked],
        "json_parse_status": dict(collections.Counter(
            r["note"].split("status=")[1].split(";")[0] for r in rows)),
    }
    json.dump(stats, open(os.path.join(LOG, "C3_stats.json"), "w"),
              ensure_ascii=False, indent=2)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
