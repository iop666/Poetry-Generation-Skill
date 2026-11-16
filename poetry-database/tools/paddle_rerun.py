#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-03-R1：用 PaddleOCR-VL-1.6 重跑三本扫描书，并与 macOS Vision 结果逐页对照。

设计约束（来自 R2-03 事故复盘与 AGENT_REPORTING_STANDARD v2.0）：
  1. 唯一 OCR 引擎是 PaddleOCR-VL-1.6 云端 API；缺 token 时报错退出，绝不偷偷换引擎。
  2. 上传须显式 --allow-upload（脚本不默认放行）。
  3. Vision 版 pages.jsonl 原样保留，Paddle 版另表存放，不覆盖、不择优、不自动裁决。
  4. 每页结果带 engine，对照结论只报差异与符号命中，不写「谁更准」。

用法：
  python3 tools/paddle_rerun.py plan                      # 离线：待上传清单 + 重点复核页
  python3 tools/paddle_rerun.py run --allow-upload        # 调 skill 整本提交（需 token）
  python3 tools/paddle_rerun.py compare                   # 逐页对照，产出 jsonl / summary
  python3 tools/paddle_rerun.py ingest                    # 结果入库（新表，不动旧表）
  python3 tools/paddle_rerun.py all --allow-upload        # run + compare + ingest
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # poetry-database
PROJECT = ROOT.parent                                   # 诗词
BOOKS_DIR = PROJECT / "books"
SKILL = Path.home() / ".workbuddy/skills/paddleocr-vl/scripts/paddleocr_vl.py"
VISION_ROOT = ROOT / "raw/books_ocr"
PADDLE_ROOT = ROOT / "raw/books_ocr_paddle"
DB = ROOT / "database/poetry.db"
ENGINE = "PaddleOCR-VL-1.6"

# 只处理三本纯图像扫描本；有文字层的《唐宋词格律》与两本 EPUB 不在重跑范围
BOOK_SPECS = [
    ("wangli_shicilv", "王力全集 诗词格律"),
    ("wangli_yinyunxue", "王力全集 汉语音韵学"),
    ("wangli_tongyuan", "王力全集 同源字典"),
]

# 格律书的本体符号。R2-03 的重大漏判：Vision 把「字外加圈」的 ○/◎ 识成汉字
CIRCLES = "○●◎〇◯◉❍"
# 2026-11-13 实测：PaddleOCR 会把「字外加圈」识成带圈数字 ⑨/⑩。
# 统计它才能发现这类「圈号仍在、但字形已错」的新失败模式；脚注 ①② 也在其中，故只作提示指标。
CIRCLED_NUM = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⓪❶❷❸❹❺"
CORRUPT = re.compile(r"[四因西囚心闪曰目囗〇][仄平]|[仄平][四因西囚心闪]")
KEY_CHARS = "平仄粘對对孤拗救韻韵"


def default_out() -> Path:
    d = date.today().strftime("%F")
    return Path.home() / "Desktop/workbuddy" / d / f"{d}_PaddleOCR-VL重跑结果"


def find_pdfs() -> dict[str, Path]:
    found: dict[str, Path] = {}
    for f in BOOKS_DIR.iterdir():
        if f.suffix.lower() != ".pdf":
            continue
        for book_id, key in BOOK_SPECS:
            if key in f.name:
                found[book_id] = f
    missing = [b for b, _ in BOOK_SPECS if b not in found]
    if missing:
        raise RuntimeError(f"缺少待重跑 PDF: {missing}")
    return found


def load_jsonl(path: Path) -> dict[int, dict]:
    out = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                out[int(r["page"])] = r
    return out


def norm(s: str) -> str:
    """去掉 Markdown 结构与空白，保留中文与全角格律符号。两侧同样处理才可比。"""
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"[\s#*`>_\-|=]+", "", s)
    return s


def bag_ratio(a: str, b: str) -> float:
    """多重集合 Jaccard：比纯集合更不小看重复字，且 O(n)，适合 1691 页批量对照。"""
    ca, cb = Counter(a), Counter(b)
    inter = sum((ca & cb).values())
    union = sum((ca | cb).values())
    return round(inter / union, 4) if union else 1.0


def han_only(s: str) -> str:
    """只留汉字与中文标点，排除 Markdown 标题、LaTeX 入声点公式等噪声。

    PaddleOCR 输出含大量 $ \\underset{\\cdot}{国} $ 之类标记，若与 Vision 纯文本直接比，
    相似度会被 ASCII 噪声压到 0.2 左右，不能解读为「内容差异」。故另算一个汉字相似度。
    """
    return "".join(ch for ch in s
                   if "\u4e00" <= ch <= "\u9fff" or ch in "，。；：、（）「」《》？！")


def count_circles(s: str) -> int:
    return sum(s.count(c) for c in CIRCLES)


def count_circled(s: str) -> int:
    """圈形记号中的带圈数字（含脚注编号，仅作提示，不等于误识数）。"""
    return sum(s.count(c) for c in CIRCLED_NUM)


def count_corrupt(s: str) -> int:
    return len(CORRUPT.findall(s))


def count_keys(s: str) -> int:
    return sum(s.count(c) for c in KEY_CHARS)


def cmd_plan(_args) -> int:
    pdfs = find_pdfs()
    print("=== 待上传文件（三本纯图像扫描本，整本提交，不逐页提交） ===")
    for book_id in sorted(pdfs):
        p = pdfs[book_id]
        print(f"  {book_id:20s} {p.stat().st_size/1024/1024:6.1f} MB  {p.name}")
    print("\n=== R2-03 Vision 版需重点复核的页（含疑似圈号误识） ===")
    total_focus = 0
    for book_id, _ in BOOK_SPECS:
        vp = VISION_ROOT / book_id / "pages.jsonl"
        if not vp.exists():
            print(f"  {book_id}: Vision 结果缺失")
            continue
        rows = load_jsonl(vp)
        focus = [p for p, r in rows.items() if count_corrupt(r["text"]) or count_circles(r["text"])]
        total_focus += len(focus)
        print(f"  {book_id:20s} 总页 {len(rows):4d}  重点页 {len(focus):4d}  页号(0基)前20 {sorted(focus)[:20]}")
    print(f"\n  合计重点页 {total_focus}。R2-03 报告只写了「词谱表格页不可用」，实际范围更大。")
    print("\n=== 凭据状态 ===")
    r = subprocess.run([sys.executable, str(SKILL), "check"], capture_output=True, text=True)
    info = json.loads(r.stdout)
    print(f"  engine={info['engine']}  isCloudApi={info['isCloudApi']}  "
          f"token.configured={info['token']['configured']}  ready={info['ready']}")
    if not info["ready"]:
        print("  BLOCKED: 缺 AI Studio token。按 skill 铁律不换引擎，须向用户索取并 setup-token。")
    return 0


def cmd_run(args) -> int:
    r = subprocess.run([sys.executable, str(SKILL), "check"], capture_output=True, text=True)
    info = json.loads(r.stdout)
    if not info["ready"]:
        print("TOKEN_MISSING: PaddleOCR-VL-1.6 凭据未配置。到 "
              "https://aistudio.baidu.com/paddleocr/task 获取 token，"
              "运行 `paddleocr_vl.py setup-token --stdin`。不改用其他引擎。", file=sys.stderr)
        return 2
    if not args.allow_upload:
        print("UPLOAD_NOT_CONFIRMED: 需显式 --allow-upload（用户已点名要求用此 API 方可加）。",
              file=sys.stderr)
        return 2

    pdfs = find_pdfs()
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    ordered = [str(pdfs[b]) for b, _ in BOOK_SPECS]
    cmd = [sys.executable, str(SKILL), "run", *ordered, "-o", str(out), "--allow-upload",
           "--timeout", str(args.timeout)]
    print("提交：", json.dumps({"files": len(ordered), "out": str(out), "model": ENGINE},
                              ensure_ascii=False), flush=True)
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        print("OCR 任务失败，保留日志，不做任何入库。", file=sys.stderr)
        return proc.returncode

    # 把云端产物落到项目内，保证后续 compare/ingest 不依赖当天日期目录
    PADDLE_ROOT.mkdir(parents=True, exist_ok=True)
    stems = {Path(p).stem: b for b, p in pdfs.items()}
    copied = {}
    for d in out.iterdir():
        if not d.is_dir() or not (d / "pages.jsonl").exists():
            continue
        book_id = stems.get(d.name)
        if not book_id:
            continue
        dst = PADDLE_ROOT / book_id
        dst.mkdir(parents=True, exist_ok=True)
        for name in ("pages.jsonl", "meta.json", "result.md"):
            src = d / name
            if src.exists():
                shutil.copy2(src, dst / name)
        copied[book_id] = str(dst)
    (PADDLE_ROOT / "runs.json").write_text(
        json.dumps({"engine": ENGINE, "out": str(out), "copied": copied,
                    "ts": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print("已落地：", json.dumps(copied, ensure_ascii=False, indent=2))
    return 0


def cmd_compare(_args) -> int:
    rows_out, summary = [], {}
    cmp_path = PADDLE_ROOT / "comparison.jsonl"
    with cmp_path.open("w", encoding="utf-8") as fh:
        for book_id, _ in BOOK_SPECS:
            vp = VISION_ROOT / book_id / "pages.jsonl"
            pp = PADDLE_ROOT / book_id / "pages.jsonl"
            if not pp.exists():
                print(f"  [跳过] {book_id}: 尚无 PaddleOCR 结果")
                continue
            vision, paddle = load_jsonl(vp), load_jsonl(pp)
            common = sorted(set(vision) & set(paddle))
            agg = {"book_id": book_id, "vision_pages": len(vision), "paddle_pages": len(paddle),
                   "common_pages": len(common), "focus_pages": 0, "vision_corrupt": 0,
                   "paddle_corrupt": 0, "vision_circles": 0, "paddle_circles": 0,
                   "vision_circled": 0, "paddle_circled": 0,
                   "vision_chars": 0, "paddle_chars": 0, "ratio_sum": 0.0,
                   "han_ratio_sum": 0.0,
                   "paddle_empty": 0, "engine_paddle": ENGINE, "engine_vision": "macos-vision-rev2",
                   "jobId": None}
            meta_p = PADDLE_ROOT / book_id / "meta.json"
            if meta_p.exists():
                agg["jobId"] = json.loads(meta_p.read_text(encoding="utf-8")).get("jobId")
            for page in common:
                vt, pt = vision[page]["text"], paddle[page]["text"]
                vn, pn = norm(vt), norm(pt)
                vc, pc = count_corrupt(vt), count_corrupt(pt)
                vs, ps = count_circles(vt), count_circles(pt)
                focus = int(bool(vc or vs))
                ratio = bag_ratio(vn, pn)
                han_ratio = bag_ratio(han_only(vt), han_only(pt))
                rec = {
                    "book_id": book_id, "page": page, "focus": focus,
                    "vision_chars": len(vn), "paddle_chars": len(pn),
                    "bag_ratio": ratio, "han_ratio": han_ratio,
                    "vision_key_chars": count_keys(vt), "paddle_key_chars": count_keys(pt),
                    "vision_corrupt_hits": vc, "paddle_corrupt_hits": pc,
                    "vision_circles": vs, "paddle_circles": ps,
                    "vision_circled": count_circled(vt), "paddle_circled": count_circled(pt),
                    "engine_paddle": ENGINE, "engine_vision": "macos-vision-rev2",
                    "diff_level": "HIGH" if ratio < 0.5 else ("MED" if ratio < 0.8 else "LOW"),
                }
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                rows_out.append(rec)
                agg["focus_pages"] += focus
                agg["vision_corrupt"] += vc
                agg["paddle_corrupt"] += pc
                agg["vision_circles"] += vs
                agg["paddle_circles"] += ps
                agg["vision_circled"] += count_circled(vt)
                agg["paddle_circled"] += count_circled(pt)
                agg["vision_chars"] += len(vn)
                agg["paddle_chars"] += len(pn)
                agg["ratio_sum"] += ratio
                agg["han_ratio_sum"] += han_ratio
                agg["paddle_empty"] += int(not pn.strip())
            if common:
                agg["mean_bag_ratio"] = round(agg.pop("ratio_sum") / len(common), 4)
                agg["mean_han_ratio"] = round(agg.pop("han_ratio_sum") / len(common), 4)
            else:
                agg.pop("ratio_sum")
                agg.pop("han_ratio_sum")
            summary[book_id] = agg
    (PADDLE_ROOT / "COMPARISON_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"对照完成：{len(rows_out)} 页 → {cmp_path}")
    for b, a in summary.items():
        print(f"  {b:20s} 共有页 {a['common_pages']:4d}  汉字相似 {a.get('mean_han_ratio')}  "
              f"(全文本 {a.get('mean_bag_ratio')})  "
              f"Vision误识 {a['vision_corrupt']:5d} → Paddle误识 {a['paddle_corrupt']:5d}  "
              f"圈号 Vision {a['vision_circles']:4d} / Paddle {a['paddle_circles']:4d}  "
              f"Paddle空页 {a['paddle_empty']}")
        print(f"      带圈数字(含脚注, 提示指标) Vision {a['vision_circled']} / "
              f"Paddle {a['paddle_circled']}；Paddle 的 ⑨/⑩ 多为「字外加圈」误识")
    return 0


def cmd_ingest(args) -> int:
    con = sqlite3.connect(args.db)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS book_pages_paddle(
      book_id TEXT, page INTEGER, chars INTEGER, text TEXT,
      engine TEXT, job_id TEXT, source TEXT, PRIMARY KEY(book_id, page));
    CREATE TABLE IF NOT EXISTS ocr_comparison(
      book_id TEXT, page INTEGER, focus INTEGER,
      vision_chars INTEGER, paddle_chars INTEGER, bag_ratio REAL,
      vision_key_chars INTEGER, paddle_key_chars INTEGER,
      vision_corrupt_hits INTEGER, paddle_corrupt_hits INTEGER,
      vision_circles INTEGER, paddle_circles INTEGER,
      engine_paddle TEXT, engine_vision TEXT, diff_level TEXT,
      han_ratio REAL, vision_circled INTEGER, paddle_circled INTEGER,
      PRIMARY KEY(book_id, page));
    CREATE TABLE IF NOT EXISTS ocr_runs(
      id INTEGER PRIMARY KEY AUTOINCREMENT, book_id TEXT, engine TEXT,
      dpi INTEGER, pages_done INTEGER, low_conf INTEGER, ts TEXT, note TEXT);
    """)
    # 兼容旧结构：本轮指标是分批加进来的，补列保证重跑幂等
    existing = {r[1] for r in con.execute("PRAGMA table_info(ocr_comparison)")}
    for col, typ in (("han_ratio", "REAL"), ("vision_circled", "INTEGER"),
                     ("paddle_circled", "INTEGER")):
        if col not in existing:
            con.execute(f"ALTER TABLE ocr_comparison ADD COLUMN {col} {typ}")
    n_page = n_cmp = 0
    # 幂等：同一轮重跑不产生重复的运行记录
    con.execute("DELETE FROM ocr_runs WHERE engine=? AND note LIKE 'R2-03-R1%'", (ENGINE,))
    for book_id, _ in BOOK_SPECS:
        pp = PADDLE_ROOT / book_id / "pages.jsonl"
        if not pp.exists():
            continue
        meta_p = PADDLE_ROOT / book_id / "meta.json"
        job_id = json.loads(meta_p.read_text(encoding="utf-8")).get("jobId") if meta_p.exists() else None
        rows = load_jsonl(pp)
        for page, r in rows.items():
            assert r.get("engine") == ENGINE, f"{book_id} p{page} engine 不符: {r.get('engine')}"
            con.execute("INSERT OR REPLACE INTO book_pages_paddle VALUES (?,?,?,?,?,?,?)",
                        (book_id, page, len(r["text"]), r["text"], ENGINE, job_id, r.get("source")))
            n_page += 1
        con.execute("INSERT INTO ocr_runs(book_id,engine,dpi,pages_done,low_conf,ts,note) "
                    "VALUES (?,?,NULL,?,0,?,?)",
                    (book_id, ENGINE, len(rows), time.strftime("%Y-%m-%d %H:%M:%S"),
                     f"R2-03-R1 重跑；jobId={job_id}；Vision 原页保留，不覆盖不择优"))
    cmp_path = PADDLE_ROOT / "comparison.jsonl"
    if cmp_path.exists():
        cols = ("book_id page focus vision_chars paddle_chars bag_ratio vision_key_chars "
                "paddle_key_chars vision_corrupt_hits paddle_corrupt_hits vision_circles "
                "paddle_circles engine_paddle engine_vision diff_level "
                "han_ratio vision_circled paddle_circled").split()
        sql = f"INSERT OR REPLACE INTO ocr_comparison VALUES ({','.join('?'*len(cols))})"
        with cmp_path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    con.execute(sql, tuple(r.get(c) for c in cols))
                    n_cmp += 1
    con.commit()
    print(f"入库完成：book_pages_paddle {n_page} 行；ocr_comparison {n_cmp} 行；"
          f"ocr_runs 新增 {len(BOOK_SPECS)} 条。旧表 book_pages 未改动。")
    con.close()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan").set_defaults(func=cmd_plan)
    r = sub.add_parser("run")
    r.add_argument("--out", default=str(default_out()))
    r.add_argument("--timeout", type=float, default=3600.0)
    r.add_argument("--allow-upload", action="store_true")
    r.set_defaults(func=cmd_run)
    sub.add_parser("compare").set_defaults(func=cmd_compare)
    i = sub.add_parser("ingest")
    i.add_argument("--db", default=str(DB))
    i.set_defaults(func=cmd_ingest)
    a = sub.add_parser("all")
    a.add_argument("--out", default=str(default_out()))
    a.add_argument("--timeout", type=float, default=3600.0)
    a.add_argument("--allow-upload", action="store_true")
    a.add_argument("--db", default=str(DB))
    a.set_defaults(func=None)
    args = p.parse_args(argv)
    if args.cmd == "all":
        for fn in (cmd_run, cmd_compare, cmd_ingest):
            rc = fn(args)
            if rc:
                return rc
        return 0
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
