#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-04 阅读辅助：章节证据包 / 理论条目引文定位 / OCR 分层抽查样本。

本脚本只做「检索与定位」，不生成观点、不代替阅读。
阅读笔记由执行 Agent 基于证据包原文撰写后写入 reading_notes_r2_04 表。

命令：
  python3 tools/r2_04_reading.py evidence   # 生成章节证据包
  python3 tools/r2_04_reading.py locate     # 16 条 theory_claims 引文在 Paddle 文本中的实际页
  python3 tools/r2_04_reading.py sample     # 生成每本 ≥10 页的分层抽查清单
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database/poetry.db"
EVID = ROOT / "raw/r2_04_evidence"
SHICILV = ROOT / "raw/books_ocr_paddle/wangli_shicilv/pages.jsonl"
KEY_TERMS = re.compile(
    r"平仄|孤平|拗|粘|对仗|合掌|韵|四声|入声|律诗|绝句|古体|近体|"
    r"一三五|节奏|词牌|词谱|变格|定格|句读|诗体|对偶|声律|平脚|仄脚|"
    r"三平调|特定的一种|不论|工对|宽对|流水对|借对")


def load(path: Path) -> dict[int, str]:
    return {int(json.loads(l)["page"]): json.loads(l)["text"]
            for l in path.open(encoding="utf-8") if l.strip()}


def clean(t: str) -> str:
    r"""把 PaddleOCR 的 LaTeX 入声点标记还原成汉字，去掉 Markdown 噪声。"""
    t = re.sub(r"\$?\\underset\{\\cdot\}\{([^}]*)\}\$?", r"\1", t)
    t = re.sub(r"\$?\\underline\{([^}]*)\}\$?", r"\1", t)
    t = re.sub(r"\$\s*\^\{?[①-⑳\d]+\}?\s*\$?", "", t)
    t = re.sub(r"\$\s*", "", t)
    t = t.replace("#", "").strip()
    return t


def paragraphs(text: str) -> list[str]:
    out = []
    for p in re.split(r"\n\s*\n", text):
        s = clean(" ".join(x.strip() for x in p.splitlines() if x.strip()))
        if len(s) >= 12:
            out.append(s)
    return out


def cmd_evidence() -> int:
    con = sqlite3.connect(DB)
    rows = load(SHICILV)
    units = con.execute(
        "SELECT unit_id,part_code,part,volume,num,title,printed_page,"
        "pdf_page_from,pdf_page_to FROM reading_units "
        "WHERE book_id='wangli_shicilv' AND level=1 ORDER BY part_code,pdf_page_from"
    ).fetchall()
    (EVID / "chapters").mkdir(parents=True, exist_ok=True)
    manifest = []
    for uid, code, part, vol, num, title, printed, pf, pt in units:
        pf, pt = max(0, pf or 0), min(max(rows), pt or 0)
        full = sum(len(clean(rows.get(p, ""))) for p in range(pf, pt + 1))
        paras = []
        for p in range(pf, pt + 1):
            paras += paragraphs(rows.get(p, ""))
        fn = f"{code}_{pf:03d}_{re.sub(r'[^0-9A-Za-z\u4e00-\u9fff]', '', title)[:14]}.md"
        # 完整章节文本单独存档（供审核与后续逐字复核），证据包只取高信息量段落
        (EVID / "full").mkdir(parents=True, exist_ok=True)
        full_text = "\n\n".join(paras)
        (EVID / "full" / fn).write_text(
            f"# {part}｜{vol} {num} {title}（完整可解析文本）\n"
            f"# 印刷 {printed}　PDF {pf}-{pt}　来源 PaddleOCR-VL-1.6 / jobId 114676397850828800\n\n"
            + full_text, encoding="utf-8")
        picked, total = [], 0
        for s in paras:
            if KEY_TERMS.search(s) and total < 5000:
                picked.append(s)
                total += len(s)
        body = (f"# {part}｜{vol} {num} {title}\n\n"
                f"- 印刷页码：{printed}　PDF 物理页：{pf}–{pt}（0 基）\n"
                f"- 本单元可解析字符：约 {full}　证据段字符：{total}\n"
                f"- 来源：PaddleOCR-VL-1.6，jobId 114676397850828800\n\n"
                + "\n\n".join(f"> {s}" for s in picked))
        (EVID / "chapters" / fn).write_text(body, encoding="utf-8")
        manifest.append({"unit_id": uid, "part": part, "volume": vol,
                         "num": num, "title": title, "printed_page": printed,
                         "pdf_from": pf, "pdf_to": pt, "full_chars": full,
                         "evidence_chars": total, "evidence_paras": len(picked),
                         "file": str(EVID / "chapters" / fn)})
    (EVID / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"证据包：{len(manifest)} 个章节单元")
    for m in manifest:
        print(f"  {m['part'][:8]:8s} {m['num']:8s} {m['title'][:22]:24s} "
              f"印{m['printed_page']} PDF {m['pdf_from']}-{m['pdf_to']} "
              f"证据 {m['evidence_chars']}/{m['full_chars']} 字")
    return 0


def cmd_locate() -> int:
    """把 16 条 theory_claims 的引文在三本书各自正文里定位，核验页码与上下文。"""
    con = sqlite3.connect(DB)
    sources = {
        "wangli_shicilv": {p: clean(t) for p, t in load(SHICILV).items()},
        "long_yushsheng_cilv": {p: clean(t) for p, t in
                                load(ROOT / "raw/books_native/long_yushsheng_cilv/pages.jsonl").items()},
        "long_cixue_shijiang": {r[0]: r[2] for r in con.execute(
            "SELECT idx,title,text FROM book_chapters WHERE book_id='long_cixue_shijiang'")},
    }
    claims = con.execute(
        "SELECT id,book_id,page,topic,claim,quote,scope,status FROM theory_claims ORDER BY id"
    ).fetchall()
    out = []
    for cid, bid, oldpage, topic, claim, quote, scope, status in claims:
        joined = sources.get(bid, {})
        rec = {"id": cid, "book_id": bid, "old_page": oldpage, "topic": topic,
               "quote": quote, "verified_pages": [], "verdict": "UNKNOWN"}
        # 取引文中最具辨识度的 8-14 字片段做定位（去掉标点与 LaTeX 残留）
        frag = re.sub(r"[^\u4e00-\u9fff]", "", quote or "")[:14]
        for p, t in joined.items():
            flat = re.sub(r"[^\u4e00-\u9fff]", "", t)
            if frag and frag[:8] in flat:
                rec["verified_pages"].append(p)
        if rec["verified_pages"]:
            rec["verdict"] = "QUOTE_FOUND"
        else:
            # 退一步用主题关键词定位
            key = re.sub(r"[^\u4e00-\u9fff]", "", claim or "")[:8]
            for p, t in joined.items():
                if key and key[:6] in re.sub(r"[^\u4e00-\u9fff]", "", t):
                    rec["verified_pages"].append(p)
            rec["verdict"] = "TOPIC_ONLY" if rec["verified_pages"] else "NOT_FOUND"
        out.append(rec)
    (EVID / "theory_locate.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for r in out:
        print(f"  id={r['id']:2d} 原页 {str(r['old_page']):4s} [{r['topic'][:12]:12s}] "
              f"{r['verdict']:22s} 命中页 {r['verified_pages'][:8]}")
    return 0


SAMPLE_PLAN = {
    "wangli_shicilv": [0, 8, 17, 35, 41, 50, 79, 125, 183, 265, 340, 431],
    "wangli_yinyunxue": [0, 5, 50, 100, 160, 200, 260, 320, 400, 475],
    "wangli_tongyuan": [0, 5, 50, 100, 200, 300, 400, 500, 650, 782],
}


def cmd_sample() -> int:
    out = []
    for bid, pages in SAMPLE_PLAN.items():
        src = ROOT / "raw/books_ocr_paddle" / bid / "pages.jsonl"
        rows = load(src)
        for p in pages:
            t = rows.get(p, "")
            out.append({"book_id": bid, "page": p, "chars": len(t),
                        "empty": not t.strip(),
                        "has_pingze_symbols": bool(re.search(r"[－｜+＋○●◎⑨⑩]", t)),
                        "has_rusheng_mark": r"\underset" in t,
                        "has_footnote": bool(re.search(r"[①-⑳]|脚注|注[：:]", t)),
                        "engine": "PaddleOCR-VL-1.6",
                        "head": clean(t)[:90]})
    (EVID / "ocr_samples.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"抽查样本 {len(out)} 页（每本 ≥10 页，覆盖开头/中间/结尾/符号页/空页）")
    for bid in SAMPLE_PLAN:
        s = [x for x in out if x["book_id"] == bid]
        print(f"  {bid:20s} {len(s):2d} 页　空页 {sum(x['empty'] for x in s)}　"
              f"含平仄符号 {sum(x['has_pingze_symbols'] for x in s)}　"
              f"含入声点 {sum(x['has_rusheng_mark'] for x in s)}　"
              f"含脚注 {sum(x['has_footnote'] for x in s)}")
    return 0


def main() -> int:
    EVID.mkdir(parents=True, exist_ok=True)
    cmds = {"evidence": cmd_evidence, "locate": cmd_locate, "sample": cmd_sample}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        print(__doc__)
        return 2
    return cmds[sys.argv[1]]()


if __name__ == "__main__":
    raise SystemExit(main())
