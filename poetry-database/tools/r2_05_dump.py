#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-05 阅读输出工具：按单元把 PaddleOCR 全文分页清洗后输出，供逐章通读。

用法：
  python3 tools/r2_05_dump.py list                     # 列出 A/B 单元与字数
  python3 tools/r2_05_dump.py show <unit_key> [--from N] [--to M]
                                                       # 输出某单元全文（带页码标记）
unit_key 形如 A:第二章 / B:卷下:第一章 / A:引言 / A:附录一
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database/poetry.db"
PAGES = ROOT / "raw/books_ocr_paddle/wangli_shicilv/pages.jsonl"
BOOK_ID = "wangli_shicilv"
PRINTED_OFFSET = 8

SUB = r"\$?\s*\\underset\{\\cdot\}\{([^{}]*)\}\s*\$?"
TRI = r"\$?\s*\\underset\{\\triangle\}\{([^{}]*)\}\s*\$?"
# 脚注号：只有 ①-⑳ 与纯数字可删
FN = r"\$?\s*\^\{?([①-⑳]{1,3}|\d{1,3})\}?\s*\$?"
# 其余 ^{X}：X 是原书的上标小字（如「又元半」的「半」、「更少个」的「少」），必须保留
SUP = r"\$?\s*\^\{([^{}]*)\}\s*\$?"
TXT = r"\\(?:text|mathrm)\{([^{}]*)\}"
# 下划线＝原书的着重点/韵脚强调，保留字
UL = r"\\underline\{([^{}]*)\}"
# 词谱里的字外加圈：\oplus / \textcircled{+} 都是「⊕」，\textcircled{2} 是「②」
CIRC = r"\\textcircled\{([^{}]*)\}"
PLUS = r"\\oplus"
FRAC = r"\\frac\{([^{}]*)\}\{([^{}]*)\}"
TIMES = r"\\times"
# 韵目/韵字的重复标记：屑_{x} 表示原书该字下加叉号
XMARK = r"_\{([^{}]*)\}"


def clean(t: str) -> str:
    """清掉 PaddleOCR 的 LaTeX 噪声。

    三类标记的处理原则：
    - `$\\underset{\\cdot}{字}$`＝原书「字下加点」（入声或韵脚标记）→ 保留字，去标记；
    - `$^{①}$` / `$^{2}$`＝脚注号 → 删除；
    - `$^{半}$`＝上标小字（词韵「元半」、词谱衬字）→ **保留字**，不可当脚注删除。
    `$` 有时缺失，故一律用可选匹配。
    """
    prev = None
    for _ in range(4):
        if t == prev:
            break
        prev = t
        t = re.sub(SUB, r"\1", t)
        t = re.sub(TRI, r"\1", t)
        t = re.sub(TXT, r"\1", t)          # 先剥内层 \text{X}，再剥外层 \underline{...}
        t = re.sub(UL, r"\1", t)
        t = re.sub(CIRC, lambda m: "\u2461" if m.group(1) == "2" else "\u2295", t)
        t = re.sub(PLUS, "\u2295", t)
        t = re.sub(r"\\frac\{1\}\{2\}", "\u00bd", t)
        t = re.sub(FRAC, r"\1/\2", t)
        t = re.sub(TIMES, "\u00d7", t)
        # 原书该字下加叉号（疑「又见某韵」标记），保留字形并记作 *，不静默丢弃
        t = re.sub(XMARK, "*", t)
        t = re.sub(FN, "", t)
        t = re.sub(SUP, r"\1", t)
    t = t.replace("$", "").replace("#", "").replace("`", "")
    t = re.sub(r"[ \t\u3000]+", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def load() -> dict[int, str]:
    rows = {}
    for line in PAGES.open(encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            rows[int(r["page"])] = clean(r["text"])
    return rows


def units(con) -> list[tuple]:
    return con.execute(
        "SELECT unit_id,part_code,volume,num,title,printed_page,pdf_page_from,pdf_page_to,level,status "
        "FROM reading_units WHERE part_code IN ('A','B') ORDER BY part_code, pdf_page_from, level"
    ).fetchall()


def cmd_list() -> int:
    con = sqlite3.connect(DB)
    rows = load()
    print(f"{'key':22s} {'pdf范围':13s} {'页':>3s} {'汉字':>6s}  状态  标题")
    for _uid, pc, vol, num, title, pp, a, b, lv, st in units(con):
        if lv != 1 and lv != 2:
            continue
        txt = "".join(rows.get(p, "") for p in range(a, b + 1))
        han = len(re.findall(r"[\u4e00-\u9fff]", txt))
        key = f"{pc}:{vol}:" if vol else f"{pc}:"
        key += num if num != title else title
        print(f"{key:22s} {a:3d}-{b:3d}     {b-a+1:3d} {han:6d}  {st:9s} {'  '*(lv-1)}{num} {title}")
    return 0


def resolve(con, key: str):
    """把 A:第二章 这类键解析成一条单元。"""
    parts = key.split(":")
    pc = parts[0]
    vol = parts[1] if len(parts) == 3 else ""
    num = parts[-1]
    q = ("SELECT unit_id,part_code,volume,num,title,printed_page,pdf_page_from,pdf_page_to,level "
         "FROM reading_units WHERE part_code=? AND num=? ")
    args = [pc, num]
    if vol:
        q += "AND volume=? ORDER BY level DESC"
        args.append(vol)
    else:
        q += "AND level=1 ORDER BY pdf_page_from"
    return con.execute(q, args).fetchall()


def cmd_show(key: str, pg_from: int | None, pg_to: int | None, maxchars: int = 9000) -> int:
    con = sqlite3.connect(DB)
    rows = load()
    hit = resolve(con, key)
    if not hit:
        print(f"未找到单元: {key}")
        return 2
    if len(hit) > 1 and not key.split(":")[1:-1]:
        print(f"命中 {len(hit)} 条，请用更精确的键：")
        for h in hit:
            print(f"  {h[0]}  pdf {h[6]}-{h[7]}")
        return 2
    uid, pc, vol, num, title, pp, a, b, lv = hit[0]
    a = pg_from if pg_from is not None else a
    b = pg_to if pg_to is not None else b
    buf, n = [], 0
    print(f"###### {uid}  pdf {a}-{b}  印刷 {a-PRINTED_OFFSET}-{b-PRINTED_OFFSET} ######")
    for p in range(a, b + 1):
        t = rows.get(p, "")
        head = f"\n--- p{p} 印{p-PRINTED_OFFSET} ---\n"
        if n + len(t) > maxchars and buf:
            print("".join(buf))
            buf, n = [], 0
            print(f"\n<<<CHUNK 断点 p{p}>>>\n")
        buf.append(head + t)
        n += len(t) + len(head)
    if buf:
        print("".join(buf))
    total = sum(len(re.findall(r"[\u4e00-\u9fff]", rows.get(p, ""))) for p in range(a, b + 1))
    print(f"\n###### 共 {total} 汉字 / {b-a+1} 页 ######")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] == "list":
        return cmd_list()
    if args[0] == "show" and len(args) >= 2:
        pf = pt = None
        if "--from" in args:
            pf = int(args[args.index("--from") + 1])
        if "--to" in args:
            pt = int(args[args.index("--to") + 1])
        return cmd_show(args[1], pf, pt)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
