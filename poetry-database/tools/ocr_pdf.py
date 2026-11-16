#!/usr/bin/env python3
"""ocr_pdf.py —— 扫描版 PDF 逐页 OCR（本机 Vision rev2，离线、零 token）

引擎说明（必须如实标注）：
    本轮环境内**没有可用的 PaddleOCR-VL-1.6 端点**（内置 VLM 代理对多种请求体均返回
    401/400，无法作为 OCR 服务）。故改用 macOS Vision 框架离线识别，
    并在每页记录里写 engine="macos-vision-rev2"，不得冒充 PaddleOCR 结果。
    rev3 会把「平」识成「瓜」、「仄」识成「厂」，故锁定 rev2。

产出：
    raw/books_ocr/<book_id>/pages.jsonl   每页一条：page / text / conf / n_lines
    支持断点续跑：已存在的 page 会跳过。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

import pymupdf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(TOOLS, "ocr_vision")
OUT = os.path.join(BASE, "raw", "books_ocr")
TMP = os.path.expanduser("<LOCAL_WORKBUDDY>/2026-11-13/.tmp/ocr_pages")

BOOKS = {
    "wangli_shicilv": "books/王力全集 诗词格律 诗词格律概要 (王力) (z-library.sk, 1lib.sk, z-lib.sk).pdf",
    "wangli_yinyunxue": "books/王力全集 汉语音韵学 (王力) (z-library.sk, 1lib.sk, z-lib.sk)(1).pdf",
    "wangli_tongyuan": "books/王力全集 同源字典 (王力) (z-library.sk, 1lib.sk, z-lib.sk)(1).pdf",
}


def load_done(path: str) -> set:
    done = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["page"])
                except Exception:
                    continue
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True, choices=list(BOOKS))
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--chunk", type=int, default=16)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=0, help="0 = 到卷末")
    ap.add_argument("--max-pages", type=int, default=0)
    args = ap.parse_args()

    pdf = os.path.join(os.path.dirname(BASE), BOOKS[args.book])
    if not os.path.exists(pdf):
        print("PDF 不存在:", pdf)
        return 2
    outdir = os.path.join(OUT, args.book)
    os.makedirs(outdir, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    jsonl = os.path.join(outdir, "pages.jsonl")

    doc = pymupdf.open(pdf)
    n = doc.page_count
    end = args.end or n
    done = load_done(jsonl)
    todo = [i for i in range(args.start, min(end, n)) if i not in done]
    if args.max_pages:
        todo = todo[: args.max_pages]
    print(f"{args.book}: 共 {n} 页，已完成 {len(done)}，本次处理 {len(todo)}", flush=True)

    t0 = time.time()
    with open(jsonl, "a", encoding="utf-8") as f:
        for k in range(0, len(todo), args.chunk):
            batch = todo[k: k + args.chunk]
            paths = []
            for p in batch:
                pix = doc[p].get_pixmap(dpi=args.dpi)
                # 固定文件名、覆盖复用：不产生删除动作（沙箱对批量删除有 50 次/轮 的限制，
                # 逐页 os.remove 会在第 50 页被拦下，导致 OCR 中途停摆）。
                path = os.path.join(TMP, f"{args.book}_slot{k % args.chunk:02d}.png")
                pix.save(path)
                paths.append(path)
            r = subprocess.run([BIN] + paths, capture_output=True, text=True)
            # 输出顺序与输入 paths 一致（同一批一次调用），按序取页号；
            # 文件名已改为复用槽位，不再含页码，不能从文件名解析。
            outs = [json.loads(x) for x in r.stdout.splitlines() if x.strip()]
            for page, d in zip(batch, outs):
                rec = {"page": page, "text": "\n".join(d["lines"]), "conf": round(d["conf"], 3),
                       "n_lines": d["n"], "engine": "macos-vision-rev2", "dpi": args.dpi}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            el = time.time() - t0
            print(f"  {min(k+args.chunk, len(todo))}/{len(todo)} 页  {el:.0f}s  "
                  f"均 {el/max(1,min(k+args.chunk,len(todo))):.2f}s/页", flush=True)
    print("完成", args.book, f"{time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
