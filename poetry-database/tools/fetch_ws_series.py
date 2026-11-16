#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_ws_series.py —— 抓取维基文库分卷页面（原始 wikitext）

设计要点（对应 ROUND 2-01 一、二、三 的采集要求）：
  1. 按 sources/ws_pages.json 的书目逐页抓取，不靠拼接 URL。
  2. **校验内容**：HTTP 200 且非空不够，还要排除 Wikimedia Error 页与限速页
     —— 上一轮就栽在「文件非空即成功」上（20 个错误页被当成成功）。
  3. 记录 上游页面标题、抓取时间、字节数、SHA-256、HTTP 码、是否转写页。
  4. 幂等：已存在且通过校验的文件跳过，但仍记一条 SKIP。
  5. 限速：默认 1.0 s/页；被限速时退避重试，不换 IP、不伪造 UA。
  6. 转写页（{{transclude pages}}，正文在 DjVu 页命名空间）用 --render 走
     action=parse 取渲染后纯文本，并在日志里标 render=1。

用法：
  python3 tools/fetch_ws_series.py --series gushiji,mingshi,wanqing,zhongzhou
  python3 tools/fetch_ws_series.py --series guangyun,cilv,cipu --render
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.parse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(BASE, "sources", "ws_pages.json")
LOG = os.path.join(BASE, "audit", "ws_fetch_log.jsonl")
UA = "PoetryDatabase/1.0 (academic corpus build; wikisource API)"

ERROR_MARKS = ("<!DOCTYPE html", "Wikimedia Error", "You are making too many requests",
               "Our servers are currently under maintenance")


def http_get(url: str, timeout=45) -> tuple:
    r = subprocess.run(["curl", "-sS", "-m", str(timeout), "-A", UA,
                        "-w", "\n@@HTTP=%{http_code}", url], capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    m = re.search(r"\n@@HTTP=(\d+)$", out)
    code = int(m.group(1)) if m else 0
    body = out[: m.start()] if m else out
    return code, body


def looks_like_error(body: str) -> bool:
    head = body[:2000]
    return any(k in head for k in ERROR_MARKS) or len(body.strip()) == 0


def fetch_raw(title: str) -> tuple:
    url = ("https://zh.wikisource.org/w/index.php?title="
           + urllib.parse.quote(title.replace(" ", "_")) + "&action=raw")
    return http_get(url)


def fetch_rendered(title: str) -> tuple:
    """转写页取渲染后正文：action=parse 展开 {{transclude pages}}，再去 HTML 标签。"""
    url = ("https://zh.wikisource.org/w/api.php?action=parse&prop=text&format=json&page="
           + urllib.parse.quote(title.replace(" ", "_")))
    code, body = http_get(url)
    if code != 200:
        return code, body
    try:
        d = json.loads(body)
        html = d["parse"]["text"]["*"]
    except Exception:
        return code, ""
    html = re.sub(r"(?is)<(script|style|sup|table|div class=\"ws-noexport\").*?</\1>", "", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</(p|div|li|h[1-6]|tr)>", "\n", html)
    txt = re.sub(r"(?s)<[^>]+>", "", html)
    txt = (txt.replace("&nbsp;", " ").replace("&amp;", "&")
              .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    return code, txt


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", required=True, help="逗号分隔的 series 名")
    ap.add_argument("--render", action="store_true", help="转写页取渲染正文")
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    want = {s.strip() for s in args.series.split(",") if s.strip()}
    rows = [r for r in json.load(open(PAGES, encoding="utf-8")) if r["series"] in want]
    # 目录页不是正文，剔除（省请求、也避免把目录当内容）
    rows = [r for r in rows if not re.search(r"目録|目錄", r["vol"])]
    # 《集韻》只取 10 个卷页：正文由 {{transclude pages}} 在渲染时展开，
    # 若连 216 个「卷01/東第一」式部次子页一起抓，会重复十倍且与清单口径不符
    # （清单同样只登记 10 卷）。此过滤必须与 build_manifest.py 保持一致。
    rows = [r for r in rows
            if not (r["series"] == "jiliyun" and not re.fullmatch(r"卷\d+", r["vol"]))]
    rows.sort(key=lambda r: (r["series"], r["order"]))
    if args.limit:
        rows = rows[: args.limit]

    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    n_ok = n_skip = n_fail = 0
    with open(LOG, "a", encoding="utf-8") as logf:
        for i, r in enumerate(rows, 1):
            series, title, vol = r["series"], r["title"], r["vol"]
            d = os.path.join(BASE, "raw", "books", series)
            os.makedirs(d, exist_ok=True)
            dst = os.path.join(d, vol.replace("/", "_") + ".wikitext")
            rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
                   "series": series, "title": title, "path": os.path.relpath(dst, BASE)}

            if os.path.exists(dst) and os.path.getsize(dst) > 200:
                body = open(dst, encoding="utf-8", errors="replace").read(3000)
                if not looks_like_error(body):
                    rec.update({"status": "SKIP", "bytes": os.path.getsize(dst),
                                "sha256": sha256(dst)})
                    logf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n_skip += 1
                    continue

            ok = False
            for attempt in range(1, 4):
                code, body = (fetch_rendered(title) if args.render else fetch_raw(title))
                if code == 200 and not looks_like_error(body):
                    with open(dst, "w", encoding="utf-8") as f:
                        f.write(body)
                    rec.update({"status": "OK", "http": code, "bytes": len(body.encode()),
                                "sha256": hashlib.sha256(body.encode()).hexdigest(),
                                "render": 1 if args.render else 0})
                    ok = True
                    break
                time.sleep(2.0 * attempt)

            if ok:
                n_ok += 1
                print(f"[{i:>3}/{len(rows)}] OK   {series}/{vol:<12} {rec['bytes']:>7}B", flush=True)
            else:
                rec.update({"status": "FAILED", "http": code})
                n_fail += 1
                print(f"[{i:>3}/{len(rows)}] FAIL {series}/{vol}  http={code}", flush=True)
            logf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            time.sleep(args.sleep)

    print(f"\n完成：成功 {n_ok} / 跳过 {n_skip} / 失败 {n_fail}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
