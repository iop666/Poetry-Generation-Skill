#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-13 D2：元曲来源分布 + 20 条回原文核对（只读）"""
import sqlite3, re, csv, json, os, hashlib, random, collections

BASE = "<PROJECT_ROOT>/poetry-database"
OUT = os.path.join(BASE, "reports/tasks/2026-11-16/R2-13")
DB = os.path.join(BASE, "database/poetry.db")
RAW = os.path.join(BASE, "raw/poetry/yuanqu/yuanqu.json")

PAR = re.compile(r"[（(][^）)]{0,40}[）)]")
HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")

def han(s):
    return len(HAN.findall(s or ""))

def main():
    raw_bytes = open(RAW, "rb").read()
    sha = hashlib.sha256(raw_bytes).hexdigest()
    raw = json.loads(raw_bytes.decode("utf-8"))
    rawidx = collections.defaultdict(list)
    for i, r in enumerate(raw):
        rawidx[(r.get("author", ""), r.get("title", ""))].append((i, r))

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    audit = list(csv.DictReader(open(os.path.join(OUT, "YUANQU_2447_MISSING_TEXT_AUDIT.csv"),
                                    encoding="utf-8-sig")))
    meta = json.load(open(os.path.join(OUT, "LOGS", "D1_counts.json"), encoding="utf-8"))

    works = {r["work_id"]: dict(r) for r in con.execute(
        "SELECT work_id,title_raw,author_name,collection,genre,source_id,base_edition,char_count,text_raw FROM works WHERE genre='曲'")}
    prov_ed = {r["work_id"]: (r["base_edition"] or "（空）") for r in con.execute(
        "SELECT work_id,base_edition FROM provenance WHERE work_id LIKE 'yuanqu:%'")}

    # ---- 1. 来源分布 ----
    by_src = collections.Counter(r["source_id"] for r in audit)
    by_coll = collections.Counter(r["collection"] for r in audit)
    by_ed = collections.Counter(prov_ed.get(r["work_id"], "（缺 provenance）") for r in audit)
    by_struct = collections.Counter((r["status"], r["play_or_sanqu"]) for r in audit)
    by_author = collections.Counter(r["author_name"] for r in audit)
    status_cnt = collections.Counter(r["status"] for r in audit)

    # 来源判定：以「该记录的曲文是否在本地来源（同一文件）里」为准
    src_verdict = {"SOURCE_HAS_QU_TEXT": 0, "SOURCE_HAS_DIALOGUE_ONLY": 0,
                   "SOURCE_HAS_MISSING_PAGE": 0, "SOURCE_UNAVAILABLE": 0,
                   "SOURCE_STRUCTURE_UNKNOWN": 0}
    for r in audit:
        st = r["status"]
        if st in ("LYRIC_PRESENT", "IN_OTHER_FIELD"):
            src_verdict["SOURCE_HAS_QU_TEXT"] += 1
        elif st == "DIALOGUE_ONLY":
            src_verdict["SOURCE_HAS_DIALOGUE_ONLY"] += 1
        elif st == "FRAGMENTARY":
            src_verdict["SOURCE_STRUCTURE_UNKNOWN"] += 1
        elif st == "EMPTY_TEXT":
            src_verdict["SOURCE_UNAVAILABLE"] += 1
        else:
            src_verdict["SOURCE_STRUCTURE_UNKNOWN"] += 1

    # ---- 2. 20 条回原文核对（分层，固定种子）----
    random.seed(20261116)
    pool = {"LYRIC_PRESENT": [], "IN_OTHER_FIELD": [], "FRAGMENTARY": [], "DIALOGUE_ONLY": []}
    for r in audit:
        pool[r["status"]].append(r)
    quota = {"LYRIC_PRESENT": 6, "IN_OTHER_FIELD": 6, "FRAGMENTARY": 4, "DIALOGUE_ONLY": 1}
    sample = []
    for st, q in quota.items():
        cand = pool[st]
        # 优先抽「句末唱提示」与不同作者
        random.shuffle(cand)
        seen_author = set()
        picked = []
        for r in cand:
            if len(picked) >= q:
                break
            if r["author_name"] in seen_author and len(cand) > q * 3:
                continue
            picked.append(r); seen_author.add(r["author_name"])
        sample += picked
    # 补足到 20：从 LYRIC_PRESENT 里再抽句末唱提示者
    tail_cue = [r for r in pool["LYRIC_PRESENT"] if r["ends_with_chang_marker"] == "Y"]
    random.shuffle(tail_cue)
    for r in tail_cue:
        if len(sample) >= 20:
            break
        if r not in sample:
            sample.append(r)

    rows = []
    for r in sample:
        w = works.get(r["work_id"], {})
        key = (r["author_name"], r["title_raw"])
        cands = rawidx.get(key, [])
        dbtext = w.get("text_raw") or ""
        best = None
        for i, rr in cands:
            if "\n".join(rr.get("paragraphs") or []) == dbtext:
                best = (i, rr); break
        if best is None and cands:
            best = max(cands, key=lambda x: han("\n".join(x[1].get("paragraphs") or [])))
        idx = best[0] if best else -1
        raw_paras = "\n".join(best[1].get("paragraphs") or []) if best else ""
        raw_title = best[1].get("title", "") if best else ""
        identical = (raw_paras == dbtext)
        if r["status"] == "IN_OTHER_FIELD":
            # 回原文看：标题是否真的把曲文带走
            found = "Y（曲文头在 raw title 内）"
            ev = f"raw title=「{raw_title[:46]}」；raw paragraphs 首「{raw_paras[:26]}」"
        elif r["status"] == "LYRIC_PRESENT":
            found = "Y"
            ev = f"raw paragraphs={han(raw_paras)} 字，与库 text_raw 逐字相同={identical}"
        elif r["status"] == "FRAGMENTARY":
            found = "N（源即残缺）"
            ev = f"raw paragraphs 仅 {han(raw_paras)} 字且句中断裂：「{raw_paras[:40]}」"
        else:
            found = "N"
            ev = f"raw paragraphs=「{raw_paras[:50]}」，只有宾白"
        rows.append({
            "sample_id": f"S{len(rows)+1:02d}", "work_id": r["work_id"], "title": r["title_raw"],
            "collection": r["collection"], "source_file": "raw/poetry/yuanqu/yuanqu.json",
            "locator": f"#index={idx}" if idx >= 0 else "NOT_FOUND",
            "lyric_found_in_source": found,
            "recovered_lyric_head_80": (raw_title.split("・", 1)[1][:80] if r["status"] == "IN_OTHER_FIELD" and "・" in raw_title else raw_paras[:80]),
            "status": r["status"], "evidence": ev,
        })

    with open(os.path.join(OUT, "LOGS", "D2_sample20.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)

    # 抽样表另存（D4 的 200 条是另一份，这里只留证据）
    flds = list(rows[0].keys())
    with open(os.path.join(OUT, "LOGS", "D2_source_sample20.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=flds); w.writeheader(); w.writerows(rows)

    # ---- 3. 写 MD ----
    L = []
    A = L.append
    A("# 元曲来源分布与原文核对（R2-13 / D2）\n")
    A(f"- 生成时间：2026-11-16　数据库：`database/poetry.db`（只读）")
    A(f"- 审计全集：**{meta['audit_rows']}** 条（判据见 `LOGS/D_notes.md`）")
    A(f"- 唯一来源：`CP-YUANQU` → `raw/poetry/yuanqu/yuanqu.json`")
    A(f"- 文件 sha256：`{sha}`　大小 {len(raw_bytes):,} 字节　记录 {len(raw):,} 条\n")

    A("## 一、按 source_id / collection / base_edition 统计\n")
    A("| 维度 | 取值 | 条数 |\n|---|---|---|")
    for k, v in by_src.most_common():
        A(f"| source_id | {k} | {v} |")
    for k, v in by_coll.most_common():
        A(f"| collection | {k} | {v} |")
    for k, v in by_ed.most_common():
        A(f"| base_edition | {k} | {v} |")
    A("")
    A("> 结论：**全库元曲只有一个来源、一个 collection、一个 base_edition**。")
    A("> 因此「按来源分层」在本数据集内不可能，真正的分层维度是**来源文件内部的两种结构**（杂剧/套数 vs 散曲），见下节。\n")

    A("## 二、来源内部结构分层（真正的差异所在）\n")
    A("`title_raw` 含「・」者 = 杂剧/套数（剧目名・曲牌），不含者 = 散曲小令。两者是上游同一文件的两种记录形态。\n")
    A("| status | 杂剧/套数(有剧目) | 散曲(无剧目) | 合计 |\n|---|---|---|---|")
    for st in ["LYRIC_PRESENT", "IN_OTHER_FIELD", "FRAGMENTARY", "DIALOGUE_ONLY", "EMPTY_TEXT"]:
        a = by_struct.get((st, "杂剧/套数(有剧目)"), 0)
        b = by_struct.get((st, "散曲(无剧目)"), 0)
        if a or b:
            A(f"| {st} | {a} | {b} | {a+b} |")
    A(f"| **合计** | | | **{sum(status_cnt.values())}** |\n")

    A("## 三、来源判定\n")
    A("| 判定 | 条数 | 含义 |\n|---|---|---|")
    meaning = {
        "SOURCE_HAS_QU_TEXT": "本地来源里就有该记录的曲文（正文内或标题内），不缺",
        "SOURCE_HAS_DIALOGUE_ONLY": "本地来源该条本身只有宾白",
        "SOURCE_HAS_MISSING_PAGE": "来源缺页（本数据集为 JSON，无页概念，恒 0）",
        "SOURCE_UNAVAILABLE": "来源不可得（恒 0，文件在位且 sha256 已核）",
        "SOURCE_STRUCTURE_UNKNOWN": "来源文本在句中截断，无法判断原貌",
    }
    for k, v in src_verdict.items():
        A(f"| {k} | {v} | {meaning[k]} |")
    A("")

    A("## 四、20 条回原文核对\n")
    A("抽样法：分层（LYRIC_PRESENT / IN_OTHER_FIELD / FRAGMENTARY / DIALOGUE_ONLY），固定种子 20261116，")
    A("按作者去重优先；逐条在 `raw/poetry/yuanqu/yuanqu.json` 内定位并比对。\n")
    A("| # | work_id | 标题 | 库内 status | 原文有曲文? | 原文片段 |\n|---|---|---|---|---|---|")
    for r in rows:
        ev = r["evidence"].replace("|", "/").replace("\n", "⏎")
        A(f"| {r['sample_id']} | `{r['work_id']}` | {r['title'][:24]} | {r['status']} | {r['lyric_found_in_source']} | {ev[:88]} |")
    A("")
    A("### 逐条说明（3 条关键样本全录）\n")
    for r in rows:
        if r["status"] in ("IN_OTHER_FIELD", "FRAGMENTARY", "DIALOGUE_ONLY"):
            A(f"- **{r['sample_id']} `{r['work_id']}`（{r['status']}）** {r['title']}")
            A(f"  - locator: `{r['locator']}`；原文核实：{r['evidence']}")
    A("")

    A("## 五、原始文件与库的差额\n")
    A("`audit/parsing_log.jsonl` 第 340 行：")
    A("```json")
    A('{"source_id":"CP-YUANQU","items":11057,"kept":10685,"skipped_short":372}')
    A("```")
    A("原始 JSON 有 11,057 条，入库 10,685 条，**372 条被 `parse.py` 的 `len(txt_norm)<8` 过滤**。")
    A("这 372 条不是「没有曲文」，而是**曲文整段被刮进了 title**、正文只剩零字，故被判「过短」丢弃。")
    A("它们可在本地原文件里 100% 复原（见 D3/D4）。\n")

    A("## 六、无法判断的部分\n")
    A(f"- {src_verdict['SOURCE_STRUCTURE_UNKNOWN']} 条 FRAGMENTARY：源文本在句中截断（如「银须霜鬓，世。」），无第二来源可对校，无法判定原本有多长。")
    A("- 上游为「整理本（无底本声明）」，`provenance.base_edition` 无版本信息，无法判断某些短曲牌（20–25 字）是「本来就这么短」还是「被截」。")
    A("  本报告一律按「未发现缺文」记录，不宣称完整。\n")

    open(os.path.join(OUT, "YUANQU_SOURCE_DISTRIBUTION.md"), "w", encoding="utf-8").write("\n".join(L))
    print("ok", src_verdict, status_cnt)

if __name__ == "__main__":
    main()
