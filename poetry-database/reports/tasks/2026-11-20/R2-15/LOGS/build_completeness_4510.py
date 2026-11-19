#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R2-15 / C4  元曲完整性审计（只读）
==================================
目标：把「来源匹配度 match_level」与「作品完整性 completeness」彻底分离。

数据源
-----
1. poetry-database/database/poetry.db  (只读 mode=ro)
   - works                          : 正文 text_raw / 标题 title_raw
   - yuanqu_text_audit_r2_13        : 4,510 条审计全集（status 四分类）
2. raw/poetry/yuanqu/yuanqu.json    : 上游原始 JSON（11,057 条）
3. reports/tasks/2026-11-16/R2-14/YUANQU_100_SOURCE_VERIFICATION.csv     (100 条抽样)
4. reports/tasks/2026-11-16/R2-14/YUANQU_1729_FIELD_BOUNDARY_AUDIT.csv   (1,729 条边界)

输出
----
YUANQU_COMPLETENESS_4510.csv        逐条 4,510 行
YUANQU_COMPLETENESS_SUMMARY.md      交叉表 + 结论（由本脚本生成底稿数据）
YUANQU_TRUNCATION_RECHECK_20.csv    20 条 TRUNCATED 回源复核

不写数据库、不联网、不改任何原始文件。
"""
import csv
import json
import os
import re
import sqlite3
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]          # .../诗词
PDB = ROOT / "poetry-database"
DB = PDB / "database/poetry.db"
RAW = PDB / "raw/poetry/yuanqu/yuanqu.json"
R214 = PDB / "reports/tasks/2026-11-16/R2-14"
OUT = PDB / "reports/tasks/2026-11-20/R2-15"

FULL_STOP = "。！？…”』」）)】"
CUE_RE = re.compile(r"[（(][^（）()]{0,14}唱[）)]。?$")


def norm_ws(s):
    return re.sub(r"\s+", "", s or "")


def split_title(title):
    """title_raw 形如『曲牌・曲文前 N 字』。返回 (曲牌, 标题里的曲文尾巴)。"""
    if "・" in title:
        q, tail = title.split("・", 1)
        return q, tail
    return title, ""


def body_of(title, text):
    """标题里残留的曲文 + 正文，按上游硬切点直接拼接（R2-13 已验证无重叠无缺口）。"""
    _, tail = split_title(title)
    return tail + (text or "")


def main():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    # ---------- 1. 源 JSON 索引 ----------
    src = json.loads(RAW.read_text(encoding="utf-8"))
    idx = collections.defaultdict(list)
    for i, rec in enumerate(src):
        idx[(rec.get("author", ""), rec.get("title", ""))].append(i)

    # ---------- 2. 边界审计（1,729）----------
    boundary = {}
    with open(R214 / "YUANQU_1729_FIELD_BOUNDARY_AUDIT.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            boundary[r["work_id"]] = r["verdict"]

    # ---------- 3. R2-14 100 条抽样（用于口径校验）----------
    sample100 = {}
    with open(R214 / "YUANQU_100_SOURCE_VERIFICATION.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            sample100[r["work_id"]] = r["verdict"]

    # ---------- 4. 主查询 ----------
    rows = con.execute("""
        SELECT a.work_id, a.title_raw, a.author_name, a.char_count, a.status,
               a.has_dialogue_marker, w.text_raw, w.char_count AS w_cc
        FROM yuanqu_text_audit_r2_13 a
        JOIN works w ON w.work_id = a.work_id
        ORDER BY a.work_id
    """).fetchall()

    out, cross, notes = [], collections.Counter(), collections.Counter()

    for r in rows:
        wid, title, author, cc, status = r["work_id"], r["title_raw"] or "", r["author_name"], r["char_count"], r["status"]
        text = r["text_raw"] or ""
        text_len = len(text.strip()) if text.strip() else 0

        # ---- match_level：与源 JSON 逐字比对 ----
        cands = idx.get((author, title), [])
        exact = None
        for i in cands:
            if "\n".join(src[i].get("paragraphs", [])) == text:
                exact = i
                break
        if exact is not None:
            match_level = "SOURCE_EXACT"
        elif cands:
            match_level = "SOURCE_VARIANT"
        else:
            match_level = "SOURCE_ABSENT"

        # ---- boundary_verdict ----
        bv = boundary.get(wid)
        if bv is None:
            bv = "NOT_IN_BOUNDARY_SCOPE"

        # ---- completeness：只看「作品是否完整」，不看来源匹配 ----
        body = body_of(title, text)
        ends_cue = bool(CUE_RE.search(body.strip())) and status != "DIALOGUE_ONLY"
        ev = []
        if text_len == 0:
            completeness = "EMPTY_BODY"
            ev.append("text_raw 为空")
        elif status == "DIALOGUE_ONLY":
            completeness = "DIALOGUE_ONLY"
            ev.append("全条仅科白，无曲文")
        elif status == "FRAGMENTARY":
            completeness = "TRUNCATED"
            ev.append("正文仅 %d 字，句中断裂" % text_len)
        elif bv == "SPLIT_AMBIGUOUS":
            completeness = "AMBIGUOUS"
            ev.append("标题/正文切点无法判定")
        elif status == "IN_OTHER_FIELD":
            completeness = "TITLE_ONLY"
            ev.append("曲文首段落在 title_raw；text_raw 仅 %d 字" % text_len)
        else:
            completeness = "COMPLETE"
            ev.append("曲文全在 text_raw（%d 字）" % text_len)

        # ---- 证据补充 ----
        if match_level == "SOURCE_EXACT":
            ev.append("源 json#%d 逐字相同" % exact)
        ev.append("title_len=%d" % len(title))
        if bv != "NOT_IN_BOUNDARY_SCOPE":
            ev.append("boundary=%s" % bv)
        if ends_cue:
            ev.append("正文以唱腔提示收尾")

        # 唱腔提示是否为曲牌边界：源中下一记录应为同作者、不同曲牌
        cue_confirmed = None
        if ends_cue and exact is not None and exact + 1 < len(src):
            nxt = src[exact + 1]
            cue_confirmed = (nxt.get("author") == author and nxt.get("title") != title)

        # 备注
        note = []
        if completeness == "TITLE_ONLY" and match_level == "SOURCE_EXACT":
            note.append("RECOVERABLE_FROM_TITLE")
        if len(title) == 32:
            note.append("TITLE_CAP_32")
        if ends_cue:
            note.append("ENDS_WITH_CUE_ARIA_BOUNDARY" if cue_confirmed else "ENDS_WITH_CUE_UNCONFIRMED")
        if completeness == "TRUNCATED":
            note.append("NO_LOCAL_SECOND_SOURCE")
        if not note:
            note.append("-")

        out.append({
            "work_id": wid,
            "title_head_40": title[:40],
            "text_len": text_len,
            "match_level": match_level,
            "completeness": completeness,
            "boundary_verdict": bv,
            "evidence": "；".join(ev),
            "note": "; ".join(note),
        })
        cross[(match_level, completeness)] += 1
        notes[(status, completeness)] += 1

    # ---------- 5. 写 4,510 ----------
    cols = ["work_id", "title_head_40", "text_len", "match_level", "completeness", "boundary_verdict", "evidence", "note"]
    with open(OUT / "YUANQU_COMPLETENESS_4510.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)

    # ---------- 6. 20 条 TRUNCATED 回源复核 ----------
    trunc = [o for o in out if o["completeness"] == "TRUNCATED"]
    pick, seen = [], set()
    # 均匀抽样，覆盖不同首字与不同曲牌
    for step in range(0, len(trunc), max(1, len(trunc) // 20)):
        o = trunc[step]
        if o["work_id"] in seen:
            continue
        seen.add(o["work_id"])
        pick.append(o)
        if len(pick) == 20:
            break
    for o in trunc:
        if len(pick) >= 20:
            break
        if o["work_id"] not in seen:
            pick.append(o)
            seen.add(o["work_id"])

    rec_rows = []
    for o in pick:
        wid = o["work_id"]
        w = con.execute("SELECT title_raw, text_raw FROM works WHERE work_id=?", (wid,)).fetchone()
        title, text = w["title_raw"], w["text_raw"] or ""
        cands = idx.get((w["title_raw"] and con.execute("SELECT author_name FROM yuanqu_text_audit_r2_13 WHERE work_id=?", (wid,)).fetchone()[0], title), [])
        hit = None
        for i in cands:
            if "\n".join(src[i].get("paragraphs", [])) == text:
                hit = i
                break
        if hit is None:
            rec_rows.append([wid, title[:40], "SOURCE_NOT_FOUND", "", "", "", "N", "无法回源", "UNVERIFIED"])
            continue
        paras = src[hit].get("paragraphs", [])
        jtail = paras[-1][-24:] if paras else ""
        dtail = text.strip().split("\n")[-1][-24:]
        identical = "\n".join(paras) == text
        last = paras[-1].strip() if paras else ""

        # 截断位置判定（三档，均可肉眼复核）
        if CUE_RE.search(last):
            locus = "AT_CUE(停在唱腔提示)"
        elif re.search(r"[？！，]。[」』”]?$", last) or (len(last) >= 2 and last[-2] in "？！，、" and last[-1] == "。"):
            locus = "SENTENCE_LEVEL_CUT(前句未收尾即断，双标点)"
        else:
            clause = re.split(r"[，。？！；：、]", last)[-2] if re.search(r"[，。？！；：、]", last) else last
            locus = ("SENTENCE_LEVEL_CUT(末句仅 %d 字)" % len(clause)) if len(clause) <= 3 else "ARIA_LEVEL_FRAGMENT(句读完整但整支曲仅存残句)"
        verdict = "SOURCE_TRUNCATED" if identical else "IMPORT_TRUNCATED"
        rec_rows.append([
            wid, title[:40], "json#%d" % hit, "%d" % len(paras),
            jtail, dtail, "Y" if identical else "N", locus, verdict,
        ])

    with open(OUT / "YUANQU_TRUNCATION_RECHECK_20.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["work_id", "title_head_40", "json_index", "json_para_count",
                    "json_last_para_tail_24", "db_last_line_tail_24", "byte_identical",
                    "truncation_locus", "verdict"])
        w.writerows(rec_rows)

    # ---------- 6b. 可恢复记录：原文 / 修订文本 / 差异 ----------
    REASON = {
        "TRUNCATED": "NOT_GENERATED: 源端句中截断，本地无第二来源，补字即编造",
        "AMBIGUOUS": "NOT_GENERATED: 标题/正文切点两可，不做猜测性切分",
        "DIALOGUE_ONLY": "NOT_GENERATED: 全条仅科白，无曲文可复原",
        "EMPTY_BODY": "NOT_GENERATED: text_raw 为空",
    }
    triad = []
    for o in out:
        if o["completeness"] == "COMPLETE":
            continue
        wid = o["work_id"]
        w = con.execute("SELECT title_raw, text_raw FROM works WHERE work_id=?", (wid,)).fetchone()
        title, text = w["title_raw"], w["text_raw"] or ""
        qupai, tail = split_title(title)
        if o["completeness"] != "TITLE_ONLY":
            triad.append({
                "work_id": wid,
                "qupai_restored": qupai or "NOT_IN_TITLE",
                "orig_text_raw": text,
                "revised_text": "NOT_GENERATED",
                "delta_chars": 0,
                "diff_note": REASON[o["completeness"]],
                "basis": "无本地第二来源，不生成修订文本",
            })
            continue
        revised = tail + text
        name = qupai if qupai else "NOT_IN_TITLE"
        if not qupai:
            qnote = "；title_raw 原本以『・』开头，曲牌已丢失，判为 QUPAI_MISSING"
        elif len(qupai) <= 1:
            qnote = "；曲牌名本身被截断，判为 QUPAI_UNCERTAIN"
        else:
            qnote = ""
        triad.append({
            "work_id": wid,
            "qupai_restored": name,
            "orig_text_raw": text,
            "revised_text": revised,
            "delta_chars": len(revised) - len(text),
            "diff_note": "标题尾 %d 字前移并入正文%s" % (len(tail), qnote),
            "basis": "title_raw 硬切点 + text_raw 直接拼接，无增删字",
        })
    with open(OUT / "YUANQU_RECOVERY_TRIAD.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["work_id", "qupai_restored", "orig_text_raw",
                                          "revised_text", "delta_chars", "diff_note", "basis"])
        w.writeheader()
        w.writerows(triad)

    # ---------- 7. 机读统计 ----------
    stats = {
        "total": len(out),
        "match": dict(collections.Counter(o["match_level"] for o in out)),
        "completeness": dict(collections.Counter(o["completeness"] for o in out)),
        "cross": {f"{k[0]}|{k[1]}": v for k, v in sorted(cross.items())},
        "status_x_completeness": {f"{k[0]}|{k[1]}": v for k, v in sorted(notes.items())},
        "boundary": dict(collections.Counter(o["boundary_verdict"] for o in out)),
        "ends_with_cue": sum(1 for o in out if "ENDS_WITH_CUE" in o["note"]),
        "ends_with_cue_confirmed": sum(1 for o in out if "ENDS_WITH_CUE_ARIA_BOUNDARY" in o["note"]),
        "ends_with_cue_unconfirmed": sum(1 for o in out if "ENDS_WITH_CUE_UNCONFIRMED" in o["note"]),
        "title_cap_32": sum(1 for o in out if "TITLE_CAP_32" in o["note"]),
        "text_len_stats": {},
        "recheck": dict(collections.Counter(r[-1] for r in rec_rows)),
        "sample100_agreement": None,
    }
    for c in ("COMPLETE", "TITLE_ONLY", "TRUNCATED", "DIALOGUE_ONLY"):
        v = sorted(o["text_len"] for o in out if o["completeness"] == c)
        if v:
            stats["text_len_stats"][c] = {"n": len(v), "min": v[0], "median": v[len(v) // 2], "max": v[-1]}

    # 与 R2-14 100 条口径对照
    map100 = {"SOURCE_VERBATIM": "COMPLETE", "SOURCE_VERBATIM_TITLE_HELD": "TITLE_ONLY",
              "SOURCE_TRUNCATED": "TRUNCATED", "SOURCE_DIALOGUE_ONLY": "DIALOGUE_ONLY"}
    agree = total = 0
    conf = collections.Counter()
    for o in out:
        if o["work_id"] in sample100:
            total += 1
            exp = map100[sample100[o["work_id"]]]
            conf[(exp, o["completeness"])] += 1
            if exp == o["completeness"]:
                agree += 1
    stats["sample100_agreement"] = {"n": total, "agree": agree,
                                    "detail": {f"{k[0]}->{k[1]}": v for k, v in sorted(conf.items())}}

    (OUT / "LOGS" / "stats_completeness.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
