#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-06 词牌目录完整盘点（目录级，不重建平仄谱）。

为什么不能用「搜索『定格』」当口径
--------------------------------
R2-04 只按行首「定格」「变格」两个关键词统计，得出 135+9=144。
但原书凡例与目录显示：同一词牌可以有定格、变格、格一、格二、格三、别格等
不同形式，且按平韵/仄韵/平仄韵转换/通叶/错叶分五类。
因此必须从**原书目录**建立词牌清单，再在每调正文范围内清点格记录。

四个口径严格分开，不相加
----------------------
1. 独立词牌名（name 去重，别名不另计）
2. 原书标题出现次数（目录条目数）
3. 词格记录数（定格+变格+格X+别格 的条目）
4. 同调异体数（同一词牌下 >1 条格记录）
"""
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database/poetry.db"
PAGES = ROOT / "raw/books_native/long_yushsheng_cilv/pages.jsonl"
OFFSET = 15  # PDF 页 = 印刷页 + 15（p16 = 印刷 1，已核）

FOOTER = re.compile(r"PDF 文件使用.*|www\.fineprint\.cn")
TOC_ENTRY = re.compile(r"^\s*([^\s（(]+?)\s*(?:[（(]([^）)]*)[）)])?\s*[…\.]{1,}\s*(\d{1,3})\s*$")
NAME_ONLY = re.compile(r"^([^\s（(\d]+?)\s*(?:[（(]([^）)]*)[）)])?\s*$")
SECTION = re.compile(r"^第([一二三四五])类\s*(平韵格|仄韵格|平仄韵转换格|平仄韵通叶格|平仄韵错叶格)$")
GE_MARK = re.compile(r"^\s*(定\s*格|变\s*格|格\s*[一二三四五六七八九十]|别\s*格[一二三四五六七八九十]?|又一体)\s*(?:[（(]([^）)]*)[）)])?\s*$")
# 词韵十九部与索引不属于词牌正文
STOP_TITLES = {"词 韵 简 编", "词韵简编", "词 牌 索 引", "词牌索引"}


def load_pages() -> dict[int, str]:
    rows = {}
    for line in PAGES.open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        t = FOOTER.sub("", r["text"])
        rows[int(r["page"])] = t
    return rows


def parse_toc(rows: dict[int, str]) -> tuple[list[dict], list[dict]]:
    """目录页 p8-p13：返回 (词牌条目, 分类段落)。"""
    entries, sections = [], []
    cur_section, cur_class = "", ""
    buf = ("", "")
    for pg in range(8, 14):
        for raw in rows.get(pg, "").splitlines():
            s = raw.strip()
            if not s:
                continue
            m = SECTION.match(s.replace(" ", ""))
            if m:
                cur_class, cur_section = m.group(1), m.group(2)
                sections.append({"cls": cur_class, "name": cur_section,
                                 "pdf_page": pg})
                buf = ("", "")
                continue
            # 词韵简编条目（「第二部 …… 237」）不是词牌
            if re.match(r"^第[一二三四五六七八九十]+部\s*[…\.]{3,}\s*\d+$", s):
                continue
            mnum = re.match(r"^(?:[…\.]{2,}\s*)?(\d{1,3})$", s)
            if mnum and (s.isdigit() and len(s) <= 2 or not s.isdigit()):  # 页码行
                if s.isdigit() and len(s) <= 2 and s == str(pg - 7):
                    continue
                if buf[0]:                          # 折行的页码
                    name, alias = buf
                    entries.append({"name": name, "alias": alias,
                                    "printed": int(mnum.group(1)), "cls": cur_class,
                                    "section": cur_section, "toc_page": pg,
                                    "order": len(entries) + 1})
                    buf = ("", "")
                continue
            m = TOC_ENTRY.match(s)
            if m:
                name, alias, printed = m.group(1), (m.group(2) or ""), int(m.group(3))
                if name in ("词牌索引", "词韵简编") or printed < 1 or printed > 234:
                    buf = ("", "")
                    continue
                entries.append({"name": name, "alias": alias, "printed": printed,
                                "cls": cur_class, "section": cur_section,
                                "toc_page": pg, "order": len(entries) + 1})
                buf = ("", "")
                continue
            m = NAME_ONLY.match(s)
            if m and len(m.group(1)) <= 12:
                buf = (m.group(1), (m.group(2) or ""))
            else:
                buf = ("", "")
    return entries, sections


def flatten(rows: dict[int, str]) -> list[tuple]:
    out = []
    for pg in range(16, 251):
        for ln in rows.get(pg, "").splitlines():
            t = ln.strip()
            if t:
                out.append((pg, t))
    return out


def ns(x: str) -> str:
    """去掉全部空白：PDF 文字层里词牌标题常带字间空格（「捣练 子」「醉太 平」）。"""
    return re.sub(r"[\s\u3000]+", "", x)


def locate_titles(entries: list[dict], flat: list[tuple]) -> None:
    """在每个词牌的目录页附近，定位其标题行在扁平序列中的位置。

    不能按「印刷页范围」切分：一个词牌可能起于页末、定格落在下一页，
    页界切分会把谱文切给下一调（江南春、醉花阴等 5 调即因此丢失格记录）。
    """
    pos = 0
    for e in entries:
        want = e["name"]
        start_hint = e["printed"] + OFFSET - 2
        found = -1
        for i in range(pos, len(flat)):
            pg, t = flat[i]
            if pg < start_hint:
                continue
            if ns(t) == ns(want):
                found = i
                break
            if pg > e["printed"] + OFFSET + 2:
                break
        if found < 0:                      # 退化为包含匹配
            for i in range(pos, len(flat)):
                pg, t = flat[i]
                if pg < start_hint:
                    continue
                if ns(t).startswith(ns(want)) and len(ns(t)) <= len(ns(want)) + 1:
                    found = i
                    break
                if pg > e["printed"] + OFFSET + 2:
                    break
        e["flat_pos"] = found
        if found >= 0:
            pos = found + 1
    # 计算区间
    idx = [e for e in entries if e.get("flat_pos", -1) >= 0]
    for k, e in enumerate(idx):
        e["flat_end"] = (idx[k + 1]["flat_pos"] - 1 if k + 1 < len(idx)
                         else len(flat) - 1)


def scan_ges(rows: dict[int, str], flat: list[tuple], e: dict) -> list[dict]:
    """在词牌的标题行区间内找格记录标记。"""
    out = []
    a, b = e.get("flat_pos", -1), e.get("flat_end", -1)
    if a < 0 or b < a:
        return out
    for i in range(a, b + 1):
        pg, t = flat[i]
        m = GE_MARK.match(t)
        if not m:
            continue
        label = re.sub(r"\s+", "", m.group(1))
        note = (m.group(2) or "").strip()
        mtype = ("定格" if label == "定格" else
                 "变格" if label.startswith("变格") else
                 "别格" if label.startswith("别格") else
                 "格序" if label.startswith("格") else "又一体")
        # 谱行：标记后紧接着的 －｜＋ 行
        pat = []
        for j in range(i + 1, min(i + 30, b + 1)):
            s2 = flat[j][1]
            if GE_MARK.match(s2):
                break
            if re.search(r"[－＋｜]", s2):
                pat.append(s2)
            elif pat and re.match(r"^(例|附注)", s2):
                break
        out.append({"cipai": e["name"], "label": label, "mtype": mtype,
                    "note": note, "pdf_page": pg, "printed_page": pg - OFFSET,
                    "pattern": " / ".join(pat[:6]),
                    "parse_status": "EXTRACTED" if pat else "UNKNOWN"})
    return out


def rhyme_type(desc: str) -> str:
    if "平仄韵转换" in desc:
        return "平仄韵转换"
    if "平仄韵通叶" in desc:
        return "平仄韵通叶"
    if "平仄韵错叶" in desc:
        return "平仄韵错叶"
    if re.search(r"[一二三四五六七八九十百]+平韵", desc):
        return "平韵"
    if re.search(r"[一二三四五六七八九十百]+仄韵", desc):
        return "仄韵"
    return ""


def main() -> int:
    rows = load_pages()
    entries, sections = parse_toc(rows)
    flat = flatten(rows)
    locate_titles(entries, flat)

    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS cipai_catalog_r2_06 (
      cipai_id TEXT PRIMARY KEY, cipai_name TEXT, alias TEXT, section_class TEXT,
      section_name TEXT, order_no INTEGER, printed_page INTEGER,
      pdf_from INTEGER, pdf_to INTEGER, n_ge INTEGER,
      ge_types TEXT, rhyme_type TEXT, has_full_spec INTEGER, note TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS cipai_ge_records_r2_06 (
      ge_id TEXT PRIMARY KEY, cipai_id TEXT, cipai_name TEXT, ge_label TEXT,
      marker_type TEXT, ge_note TEXT, pdf_page INTEGER, printed_page INTEGER,
      pattern TEXT, parse_status TEXT)""")
    con.execute("DELETE FROM cipai_catalog_r2_06")
    con.execute("DELETE FROM cipai_ge_records_r2_06")

    all_ges = []
    missing = []
    for e in entries:
        if e.get("flat_pos", -1) < 0:
            missing.append(e["name"])
        ges = scan_ges(rows, flat, e)
        e["pdf_from"] = flat[e["flat_pos"]][0] if e.get("flat_pos", -1) >= 0 else e["printed"] + OFFSET
        e["pdf_to"] = flat[e["flat_end"]][0] if e.get("flat_end", -1) >= 0 else e["pdf_from"]
        # 描述行：标题行之后紧跟的 2-3 行（字数、韵数、体式说明）
        desc = ""
        if e.get("flat_pos", -1) >= 0:
            desc = " ".join(t for _, t in flat[e["flat_pos"] + 1:e["flat_pos"] + 4])
        types = sorted({g["mtype"] for g in ges})
        all_ges += ges
        cid = f"CIPAI-{e['order']:03d}"
        con.execute("INSERT OR REPLACE INTO cipai_catalog_r2_06 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (cid, e["name"], e["alias"], e["cls"], e["section"], e["order"],
                     e["printed"], e["pdf_from"], e["pdf_to"], len(ges),
                     ",".join(types), rhyme_type(desc), 1 if ges else 0, desc[:120]))
        for k, g in enumerate(ges, 1):
            con.execute("INSERT OR REPLACE INTO cipai_ge_records_r2_06 VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (f"{cid}-G{k:02d}", cid, e["name"], g["label"], g["mtype"],
                         g["note"], g["pdf_page"], g["printed_page"],
                         g["pattern"], g["parse_status"]))
    con.commit()

    names = {e["name"] for e in entries}
    dup = {}
    for e in entries:
        dup[e["name"]] = dup.get(e["name"], 0) + 1
    multi = {k: v for k, v in dup.items() if v > 1}
    print(f"目录条目（标题出现次数）: {len(entries)}")
    print(f"独立词牌名（去重）      : {len(names)}")
    print(f"词格记录数              : {len(all_ges)}")
    print(f"同调异体（>1 条格记录）  : {con.execute('SELECT COUNT(*) FROM cipai_catalog_r2_06 WHERE n_ge>1').fetchone()[0]}")
    print(f"无格记录（需人工核）    : {con.execute('SELECT COUNT(*) FROM cipai_catalog_r2_06 WHERE n_ge=0').fetchone()[0]}")
    print("\n=== 按标记类型 ===")
    for r in con.execute("SELECT marker_type,COUNT(*) FROM cipai_ge_records_r2_06 GROUP BY 1 ORDER BY 2 DESC"):
        print(f"  {r[0]:6s} {r[1]:4d}")
    print("\n=== 按分类 ===")
    for r in con.execute("SELECT section_name,COUNT(*),SUM(n_ge) FROM cipai_catalog_r2_06 GROUP BY 1"):
        print(f"  {r[0] or '(未归)':12s} 调 {r[1]:3d}  格记录 {r[2]}")
    print("\n=== 同调异体（格记录最多的 12 调）===")
    for r in con.execute("SELECT cipai_name,n_ge FROM cipai_catalog_r2_06 WHERE n_ge>1 "
                         "ORDER BY n_ge DESC, order_no LIMIT 12"):
        print(f"  {r[0]:10s} {r[1]} 条")
    if multi:
        print("目录内重名:", multi)
    if missing:
        print("未定位到标题行的词牌（需人工核）:", missing)
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
