#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-06 索引构建：C/D 部分章节单元 + 全书逐页映射表。

设计要点
--------
1. 印刷页码 → PDF 物理页固定偏移 8，本脚本不假定，而是用三处独立证据交叉验证：
   C 目录（p349）所载 344/347/350 三讲起点，实测分别落在 PDF 352/355/358；
   A 目录（p11）所载「引言 7」，实测落在 PDF 15；B 目录（p185）所载「第一章 179」，
   实测落在 PDF 187。任一不符则脚本报错退出，避免把错映射写进库。
2. 空白页由像素密度实测（不是靠 OCR 空串判断，OCR 空页可能是识别失败）。
3. 逐页登记：部分、印刷页、页面性质、是否属正文、R2-05 是否读过、未读原因。
"""
import json
import re
import sqlite3
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database/poetry.db"
PDF = Path("<PROJECT_ROOT>/books/"
           "王力全集 诗词格律 诗词格律概要 (王力) (z-library.sk, 1lib.sk, z-lib.sk).pdf")
PAGES = ROOT / "raw/books_ocr_paddle/wangli_shicilv/pages.jsonl"
OFFSET = 8  # PDF 页 = 印刷页 + 8

# C 部分十讲：目录原文（p349）「一诗韵和平仄……344」等
C_UNITS = [
    ("C:卷首语", 343, "卷首语（说明写作目的与取材标准）"),
    ("C:第一讲", 344, "一 诗韵和平仄"),
    ("C:第二讲", 347, "二 五言绝句"),
    ("C:第三讲", 350, "三 七言绝句"),
    ("C:第四讲", 354, "四 五言律诗和长律"),
    ("C:第五讲", 358, "五 七言律诗"),
    ("C:第六讲", 362, "六 平仄的变格"),
    ("C:第七讲", 368, "七 对仗"),
    ("C:第八讲", 372, "八 古风"),
    ("C:第九讲", 376, "九 词牌和词谱"),
    ("C:第十讲", 391, "十 词韵和平仄"),
    ("C:后记", 398, "后记"),
]
D_UNITS = [
    ("D:附录", 399, "附录 诗词的平仄"),
    ("D:索引", 407, "主要术语、人名、论著索引"),
]


def load_pages() -> dict[int, str]:
    rows = {}
    for line in PAGES.open(encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            rows[int(r["page"])] = r["text"]
    return rows


def blank_pages() -> set[int]:
    doc = pymupdf.open(PDF)
    out = set()
    for i in range(doc.page_count):
        pix = doc[i].get_pixmap(dpi=30, colorspace=pymupdf.csGRAY)
        s = pix.samples
        if sum(1 for b in s if b < 200) / len(s) < 0.004:
            out.add(i)
    doc.close()
    return out


def han(t: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", t))


def verify_offset(rows: dict[int, str]) -> None:
    """三处独立证据校验偏移 8；不符则中止。"""
    probes = [(352, "一诗韵和平仄"), (355, "二五言绝句"), (358, "三七言绝句"),
              (15, "引言"), (187, "卷上诗")]
    for pg, kw in probes:
        head = re.sub(r"\s+", "", rows.get(pg, "")[:200])
        if kw not in head:
            raise SystemExit(f"偏移校验失败：PDF p{pg} 首段未见『{kw}』，实际：{head[:60]!r}")


def build_units(rows: dict[int, str]) -> list[dict]:
    doc = pymupdf.open(PDF)
    total = doc.page_count
    doc.close()
    units = []
    # A/B 沿用 R2-05 的章级划分，只为映射表提供边界
    con = sqlite3.connect(DB)
    for uid, pf, title, status in con.execute(
            "SELECT unit_id, pdf_page_from, title, status FROM reading_units "
            "WHERE part_code IN ('A','B') AND level=1 ORDER BY pdf_page_from"):
        units.append({"unit_id": uid, "part": uid[0], "pdf_from": pf, "title": title,
                      "status": status, "printed": pf - OFFSET})
    con.close()

    def next_start(lst, i, printed):
        nxt = lst[i + 1][1] if i + 1 < len(lst) else None
        if nxt is not None:
            return nxt + OFFSET - 1
        return (421 if printed >= 400 else total - 1)

    for i, (uid, printed, title) in enumerate(C_UNITS):
        units.append({"unit_id": uid, "part": "C", "pdf_from": printed + OFFSET,
                      "printed": printed, "title": title, "status": "PARSED",
                      "pdf_to": next_start(C_UNITS, i, printed)})
    for i, (uid, printed, title) in enumerate(D_UNITS):
        units.append({"unit_id": uid, "part": "D", "pdf_from": printed + OFFSET,
                      "printed": printed, "title": title, "status": "PARSED",
                      "pdf_to": next_start(D_UNITS, i, printed)})
    # 结尾校正：C 部分止于 406（后记 398）；D 附录止于 413，索引止于 431
    FIX = {"C:后记": 406, "D:附录": 413, "D:索引": 431}
    for u in units:
        if u["unit_id"] in FIX:
            u["pdf_to"] = FIX[u["unit_id"]]
    return units


def page_kind(pg: int, blanks: set[int], units: list[dict]) -> tuple[str, str]:
    """返回 (页面性质, 说明)。"""
    if pg <= 2:
        return "封面/书名页", "无印刷页码"
    if pg == 3:
        return "版权页", "出版信息，OCR 含印张、字数"
    if 4 <= pg <= 7:
        return "前置页", "无印刷页码"
    if pg == 8:
        return "总目录", "四部分起讫页：1/175/339/399/407"
    if pg in (9, 183, 347):
        return "分部扉页", "仅印著作名，无正文"
    if pg in blanks:
        return "空白页", "像素密度实测为空白，无页码无正文"
    for u in units:
        if u["pdf_from"] == pg:
            if pg == 9:
                return "分部扉页", "《诗词格律》扉页（印刷 1）"
            if pg == 183:
                return "分部扉页", "《诗词格律概要》扉页（印刷 175）"
            if pg == 347:
                return "分部扉页", "《诗词格律十讲》扉页（印刷 339）"
            return "章首", u["title"]
    if 11 <= pg <= 13 or 185 <= pg <= 186 or pg == 349:
        return "分部目录", "目录页，非正文"
    if 15 <= pg <= 182:
        return "正文", "《诗词格律》"
    if 187 <= pg <= 346:
        return "正文", "《诗词格律概要》"
    if 351 <= pg <= 406:
        return "正文", "《诗词格律十讲》"
    if 407 <= pg <= 413:
        return "正文", "附录 诗词的平仄"
    if 415 <= pg <= 431:
        return "索引", "术语/人名/论著索引，纯检索用"
    return "未分类", ""


def main() -> int:
    rows = load_pages()
    verify_offset(rows)
    blanks = blank_pages()
    units = build_units(rows)

    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS reading_units_r2_06 (
      unit_id TEXT PRIMARY KEY, book_id TEXT, part_code TEXT, title TEXT,
      printed_from INTEGER, printed_to INTEGER, pdf_from INTEGER, pdf_to INTEGER,
      chars_total INTEGER, status TEXT, note TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS page_map_wangli (
      pdf_page INTEGER PRIMARY KEY, printed_page INTEGER, part_code TEXT,
      unit_id TEXT, kind TEXT, is_body INTEGER, read_r205 INTEGER,
      exclude_reason TEXT)""")
    con.execute("DELETE FROM reading_units_r2_06")
    con.execute("DELETE FROM page_map_wangli")

    # 逐页映射
    body = 0
    for pg in range(432):
        kind, note = page_kind(pg, blanks, units)
        part = ""
        unit_id = ""
        if 9 <= pg <= 182:
            part = "A"
        elif 183 <= pg <= 346:
            part = "B"
        elif 347 <= pg <= 406:
            part = "C"
        elif 407 <= pg <= 431:
            part = "D"
        for u in units:
            if u["pdf_from"] <= pg <= u.get("pdf_to", u["pdf_from"]):
                unit_id = u["unit_id"]
                break
        is_body = 1 if kind in ("正文", "章首", "索引") else 0
        body += is_body
        read = 1 if (15 <= pg <= 182 or 187 <= pg <= 346) else 0
        reason = "" if read else (
            "空白页" if kind == "空白页" else
            "分部扉页" if kind == "分部扉页" else
            "分部目录（非正文）" if kind == "分部目录" else
            "总目录" if kind == "总目录" else
            "前置页" if kind in ("封面/书名页", "版权页", "前置页") else
            "R2-05 未授权范围" if part in ("C", "D") else "")
        con.execute("INSERT OR REPLACE INTO page_map_wangli VALUES (?,?,?,?,?,?,?,?)",
                    (pg, pg - OFFSET if pg >= 9 else None, part, unit_id, kind,
                     is_body, read, reason))

    # 单元表
    for u in units:
        if u["part"] not in ("C", "D"):
            continue
        chars = sum(han(rows.get(p, "")) for p in range(u["pdf_from"], u["pdf_to"] + 1))
        con.execute("INSERT OR REPLACE INTO reading_units_r2_06 VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (u["unit_id"], "wangli_shicilv", u["part"], u["title"],
                     u["printed"], u["printed"] + (u["pdf_to"] - u["pdf_from"]),
                     u["pdf_from"], u["pdf_to"], chars, "PARSED", ""))
        # 同步 reading_units，便于 r2_05_dump 直接 show
        con.execute("""INSERT INTO reading_units
            (unit_id,book_id,part_code,volume,level,num,title,printed_page,
             pdf_page_from,pdf_page_to,status,note)
            VALUES (?,?,?,?,1,?,?,?,?,?,?,?)
            ON CONFLICT(unit_id) DO UPDATE SET
              pdf_page_from=excluded.pdf_page_from, pdf_page_to=excluded.pdf_page_to,
              printed_page=excluded.printed_page, title=excluded.title,
              num=excluded.num""",
                    (u["unit_id"], "wangli_shicilv", u["part"], "",
                     u["unit_id"].split(":", 1)[1],
                     u["title"], u["printed"], u["pdf_from"], u["pdf_to"], "PARSED", ""))
    con.commit()

    print(f"页数总计 432；正文/索引页 {body}")
    print(f"空白页 {sorted(p for p in blanks)}")
    print("\n=== C/D 单元 ===")
    for r in con.execute("SELECT unit_id,printed_from,printed_to,pdf_from,pdf_to,chars_total "
                         "FROM reading_units_r2_06 ORDER BY pdf_from"):
        print(f"  {r[0]:12s} 印 {r[1]}-{r[2]}  PDF {r[3]}-{r[4]}  {r[5]:5d} 字")
    print("\n=== 各部分页数构成 ===")
    for r in con.execute("SELECT part_code,kind,COUNT(*) FROM page_map_wangli "
                         "WHERE part_code!='' GROUP BY 1,2 ORDER BY 1,2"):
        print(f"  {r[0]} {r[1]:8s} {r[2]:3d}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
