#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-04 索引构建：合订本四部分章节表 + 《唐宋词格律》全部定格索引 + 词学十讲讲次。

数据来源（均为本地已入库文本，不新增抓取）：
  - raw/books_ocr_paddle/wangli_shicilv/pages.jsonl   PaddleOCR-VL-1.6，页序已核验
  - raw/books_native/long_yushsheng_cilv/pages.jsonl   PDF 文字层
  - database/poetry.db :: book_chapters               EPUB 章节

印刷页码 = PDF 物理页(0基) - 8，已用 p35/p100/p200 原图核验。
合订本实为四部分（总目录 p8），不是审核假设的两部。
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database/poetry.db"
SHICILV = ROOT / "raw/books_ocr_paddle/wangli_shicilv/pages.jsonl"
CILV = ROOT / "raw/books_native/long_yushsheng_cilv/pages.jsonl"
OFFSET = 8  # 印刷页 = PDF 页 - 8

PARTS = [
    ("A", "诗词格律", 1, 174, 9, 182, [11, 12, 13]),
    ("B", "诗词格律概要", 175, 338, 183, 346, [185, 186]),
    ("C", "诗词格律十讲", 339, 398, 347, 406, []),
    ("D", "附录：诗词的平仄／索引", 399, 424, 407, 431, []),
]

TOC_LINE = re.compile(r"^\s*(第[一二三四五六七八九十百]+[章节])\s*(.+?)\s*[.…]{2,}\s*(\d+)\s*$")
TOC_SUB = re.compile(r"^\s*[（(]([一二三四五六七八九十]+)[）)]\s*(.+?)\s*[.…]{2,}\s*(\d+)\s*$")
TOC_MISC = re.compile(r"^\s*(引言|结语|附录[一二三四五六七八九十]+|卷[上下]\s*\S*)\s*(.*?)\s*[.…]{2,}\s*(\d+)\s*$")


def load(path: Path) -> dict[int, str]:
    return {int(json.loads(l)["page"]): json.loads(l)["text"]
            for l in path.open(encoding="utf-8") if l.strip()}


def parse_toc(rows: dict[int, str], pages: list[int]) -> list[dict]:
    """从目录页原文提取章/节条目；只取级别 1（章）与级别 2（节）。"""
    out, volume = [], ""
    for pg in pages:
        for ln in rows.get(pg, "").splitlines():
            s = ln.strip().lstrip("#").strip()
            if s.startswith("卷上") or s.startswith("卷下"):
                volume = s
                continue
            m = TOC_LINE.match(s) or TOC_SUB.match(s) or TOC_MISC.match(s)
            if not m:
                continue
            num, title, printed = m.group(1), m.group(2).strip(), int(m.group(3))
            if TOC_MISC.match(s) and not (TOC_LINE.match(s) or TOC_SUB.match(s)):
                level = 1
                title = (num + (" " + title if title else "")).strip()
            elif re.match(r"^第[一二三四五六七八九十百]+章", num):
                level = 1
            elif num.startswith("第"):
                level = 2
            else:
                level = 3
            out.append({"part": "", "volume": volume, "level": level,
                        "num": num, "title": title, "printed_page": printed,
                        "pdf_page": printed + OFFSET, "toc_page": pg})
    return out


def build_units(rows: dict[int, str]) -> list[dict]:
    units: list[dict] = []
    part_by_page = []
    for code, name, ps, pe, pdfs, pdfe, tocs in PARTS:
        part_by_page.append((pdfs, pdfe, code, name))

    for code, name, ps, pe, pdfs, pdfe, tocs in PARTS:
        if not tocs:
            units.append({"part_code": code, "part": name, "volume": "", "level": 0,
                          "num": "", "title": f"【{name}】整部", "printed_page": ps,
                          "pdf_page_from": pdfs, "pdf_page_to": pdfe,
                          "status": "PARSED", "note": "本轮未逐章建索引"})
            continue
        items = parse_toc(rows, tocs)
        for it in items:
            it["part_code"], it["part"] = code, name
        # 同页重复条目去重（目录跨页续排时可能出现）
        seen, dedup = set(), []
        for it in items:
            k = (it["num"], it["title"], it["printed_page"])
            if k in seen:
                continue
            seen.add(k)
            dedup.append(it)
        dedup.sort(key=lambda x: (x["printed_page"], x["level"]))
        for i, it in enumerate(dedup):
            # 章到下一章为止，节到下一节为止；小节不截断上级范围
            nxt = next((x["pdf_page"] for x in dedup[i + 1:]
                        if x["level"] <= it["level"] and x["pdf_page"] > it["pdf_page"]), None)
            it["pdf_page_from"] = it["pdf_page"]
            it["pdf_page_to"] = (nxt - 1) if nxt else pdfe
            units.append({
                "part_code": it["part_code"], "part": it["part"], "volume": it["volume"],
                "level": it["level"], "num": it["num"], "title": it["title"],
                "printed_page": it["printed_page"],
                "pdf_page_from": it["pdf_page_from"], "pdf_page_to": it["pdf_page_to"],
                "status": "PARSED", "note": "目录条目，来自 PaddleOCR 目录页原文"})
    return units


DINGGE = re.compile(r"^\s*定\s*格\s*$")
BIANGE = re.compile(r"^\s*变\s*格.*$")
PATTERN_LINE = re.compile(r"[－｜+＋]")
NOT_CIPAI = {"第一类", "第二类", "第三类", "第四类", "第五类", "目录", "凡例",
             "出版说明", "平韵格", "仄韵格", "平仄韵转换格", "平仄韵通叶格", "平仄韵错叶格"}


def toc_whitelist(rows: dict[int, str]) -> set[str]:
    """从目录页 p8-p15 提取词牌名白名单，用于挡掉例词题/说明行被误认成词牌。"""
    names: set[str] = set()
    for pg in range(8, 16):
        for ln in rows.get(pg, "").splitlines():
            s = ln.strip()
            m = re.match(r"^([\u4e00-\u9fff]{2,10})\s*[（(]", s)
            if m and re.search(r"[.…]{2,}\s*\d+", s):
                names.add(m.group(1))
                continue
            m2 = re.match(r"^([\u4e00-\u9fff]{2,10})\s*[.…]{2,}\s*(\d+)", s)
            if m2:
                names.add(m2.group(1))
    return names - NOT_CIPAI


def build_cipai_index(rows: dict[int, str]) -> list[dict]:
    """按「定 格 / 变 格」标题行重建索引。

    词牌名用「目录白名单 + 跨页向前回溯」定位（词牌标题常在前一页末尾），
    避免 R2-03 只在本页向前找 8 行导致的 28 条 UNKNOWN 与误取。
    """
    wl = toc_whitelist(rows)
    flat: list[tuple[int, str]] = []
    for pg in sorted(rows):
        if pg < 16:
            continue
        for ln in rows[pg].splitlines():
            if ln.strip():
                flat.append((pg, ln.strip()))
    out = []
    for k, (pg, ln) in enumerate(flat):
        if not (DINGGE.match(ln) or BIANGE.match(ln)):
            continue
        name, name_src = "UNKNOWN", "UNKNOWN"
        # PDF 文字层把标题字距拆开（如「捣练 子 」「醉太 平 」），去空格后再匹配目录白名单
        for j in range(k - 1, max(-1, k - 90), -1):
            s2 = re.sub(r"\s+", "", flat[j][1]).split("（")[0].split("(")[0]
            if s2 in wl:
                name, name_src = s2, "TOC"
                break
        spec, j = [], k + 1
        while j < len(flat) and j < k + 16:
            s = flat[j][1]
            if re.match(r"^(例|附注|说明|考|注|变\s*格|定\s*格)", s):
                break
            if PATTERN_LINE.search(s):
                spec.append(s)
            elif spec and len(s) < 30 and re.search(r"[（(](韵|句|豆|叠)[）)]", s):
                spec.append(s)
            j += 1
        # 印刷页码固定在本页第一行（版心数字），不向前跨页猜
        head = rows[pg].splitlines()
        printed = int(head[0].strip()) if head and re.match(r"^\d{1,3}$", head[0].strip()) else None
        example = ""
        for j in range(k + 1, min(len(flat), k + 25)):
            if re.match(r"^例", flat[j][1]):
                example = " / ".join(x[1] for x in flat[j + 1:j + 5])[:200]
                break
        patt = " / ".join(spec)
        char_count = len(re.findall(r"[－｜+＋]", patt))
        rhyme_count = len(re.findall(r"[（(]韵[）)]", patt))
        sent_count = len(re.findall(r"[（(](?:韵|句|豆|叠)[）)]", patt))
        out.append({
            "seq": len(out) + 1, "pdf_page": pg, "printed_page": printed,
            "name": name, "name_source": name_src,
            "grid_type": "定格" if DINGGE.match(ln) else "变格",
            "pattern": patt, "pattern_lines": len(spec),
            "char_count": char_count, "rhyme_count": rhyme_count,
            "sentence_marks": sent_count, "example": example,
            "parse_status": "EXTRACTED" if spec else "UNKNOWN",
            "raw_head": ln, "source": "《唐宋词格律》PDF 文字层",
        })
    # 「变 格 一／二」之类不另立词牌名，继承其所属词牌
    for r in out:
        if r["name"] == "UNKNOWN" and r["grid_type"] == "变格":
            prev = next((x["name"] for x in reversed(out[:r["seq"] - 1])
                         if x["name"] != "UNKNOWN"), "UNKNOWN")
            r["name"], r["name_source"] = prev, "INHERITED"
    return out


def main() -> int:
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS reading_units(
      unit_id TEXT PRIMARY KEY, book_id TEXT, part_code TEXT, part TEXT,
      volume TEXT, level INTEGER, num TEXT, title TEXT,
      printed_page INTEGER, pdf_page_from INTEGER, pdf_page_to INTEGER,
      status TEXT, note TEXT);
    DROP TABLE IF EXISTS cipai_index;
    CREATE TABLE cipai_index(
      seq INTEGER PRIMARY KEY, pdf_page INTEGER, printed_page INTEGER,
      name TEXT, name_source TEXT, grid_type TEXT, pattern TEXT,
      pattern_lines INTEGER, char_count INTEGER, rhyme_count INTEGER,
      sentence_marks INTEGER, example TEXT, parse_status TEXT,
      raw_head TEXT, source TEXT);
    """)
    shicilv = load(SHICILV)
    units = build_units(shicilv)
    con.execute("DELETE FROM reading_units WHERE book_id='wangli_shicilv'")
    for u in units:
        uid = f"wangli_shicilv:{u['part_code']}:{u['num']}:{u['title']}"
        con.execute("INSERT OR REPLACE INTO reading_units VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (uid, "wangli_shicilv", u["part_code"], u["part"], u["volume"],
                     u["level"], u["num"], u["title"], u["printed_page"],
                     u["pdf_page_from"], u["pdf_page_to"], u["status"], u["note"]))
    # 词学十讲十讲
    con.execute("DELETE FROM reading_units WHERE book_id='long_cixue_shijiang'")
    for idx, title, chars in con.execute(
            "SELECT idx,title,chars FROM book_chapters WHERE book_id='long_cixue_shijiang' "
            "AND idx BETWEEN 5 AND 14 ORDER BY idx").fetchall():
        num = re.match(r"第([一二三四五六七八九十]+)讲", title)
        uid = f"long_cixue_shijiang:{idx}"
        con.execute("INSERT OR REPLACE INTO reading_units VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (uid, "long_cixue_shijiang", "E", "词学十讲", "", 1,
                     num.group(0) if num else str(idx), title, None, None, None,
                     "PARSED", f"EPUB 章节 idx={idx}，{chars} 字"))
    con.commit()

    cilv = load(CILV)
    idx = build_cipai_index(cilv)
    con.executemany("INSERT INTO cipai_index VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [(r["seq"], r["pdf_page"], r["printed_page"], r["name"],
                      r["name_source"], r["grid_type"], r["pattern"], r["pattern_lines"],
                      r["char_count"], r["rhyme_count"], r["sentence_marks"],
                      r["example"], r["parse_status"], r["raw_head"], r["source"]) for r in idx])
    con.commit()

    print("=== 合订本四部分章节索引 ===")
    for code, name, *_ in PARTS:
        rows = con.execute("SELECT COUNT(*),MIN(printed_page),MAX(printed_page) FROM reading_units "
                           "WHERE part_code=?", (code,)).fetchone()
        print(f"  {code} {name:16s} 单元 {rows[0]:3d}  印刷页 {rows[1]}–{rows[2]}")
    print("\n=== 《唐宋词格律》定格索引 ===")
    print("  总条目:", len(idx))
    for t, n in con.execute("SELECT grid_type,COUNT(*) FROM cipai_index GROUP BY grid_type"):
        print(f"   {t}: {n}")
    print("  独立词牌名(排除UNKNOWN):", con.execute(
        "SELECT COUNT(DISTINCT name) FROM cipai_index WHERE name<>'UNKNOWN'").fetchone()[0])
    print("  有谱行:", con.execute("SELECT COUNT(*) FROM cipai_index WHERE pattern_lines>0").fetchone()[0])
    print("  UNKNOWN 谱:", con.execute("SELECT COUNT(*) FROM cipai_index WHERE parse_status='UNKNOWN'").fetchone()[0])
    print("  name=UNKNOWN:", con.execute("SELECT COUNT(*) FROM cipai_index WHERE name='UNKNOWN'").fetchone()[0])
    multi = con.execute("SELECT COUNT(*) FROM (SELECT name FROM cipai_index WHERE name<>'UNKNOWN' "
                        "GROUP BY name HAVING COUNT(*)>1)").fetchone()[0]
    print("  同调多体词牌数:", multi)
    old = con.execute("SELECT COUNT(*) FROM cipai_specs").fetchone()[0]
    print("  R2-03 旧 cipai_specs 行数:", old)
    hit = con.execute("SELECT COUNT(*) FROM cipai_specs s WHERE EXISTS "
                      "(SELECT 1 FROM cipai_index i WHERE i.name=s.name)").fetchone()[0]
    print(f"  旧 76 条中可在新索引按名匹配: {hit}/{old}")
    print("  字数为0(需人工复核):", con.execute(
        "SELECT COUNT(*) FROM cipai_index WHERE char_count=0").fetchone()[0])
    print("\n  前 12 条:")
    for r in idx[:12]:
        print(f"   #{r['seq']:3d} p{r['pdf_page']:3d} 印{r['printed_page']} {r['name']:8s} "
              f"{r['grid_type']} 谱行{r['pattern_lines']} {r['pattern'][:52]}")
    (ROOT / "raw/r2_04_cipai_index.json").write_text(
        json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
