#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
discover_ws_series.py —— 枚举维基文库分卷页面，生成抓取清单

为什么需要它：
  四库全书本的卷页命名不统一（`卷001` / `卷1` / `卷一`），且各书卷数不同。
  硬编码卷号会漏卷或抓到 404 页。改用 allpages 前缀枚举，以站点实际页面为准。

输出：sources/ws_pages.json
  [{"series":"gushiji","title":"古詩紀 (四庫全書本)/卷001","vol":"001","order":1}, ...]

限速：每次请求间隔 1.5 s，UA 写明用途（Wikimedia API 规范）。
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.parse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "sources", "ws_pages.json")
UA = "PoetryDatabase/1.0 (academic corpus build; wikisource API)"

API = "https://zh.wikisource.org/w/api.php?"

# series → 页面前缀
SERIES = {
    "gushiji":  "古詩紀 (四庫全書本)/卷",      # 明·馮惟訥：先秦至隋
    "mingshi":  "明詩綜 (四庫全書本)/卷",      # 清·朱彝尊：明
    "wanqing":  "晚晴簃詩匯/卷",               # 徐世昌：清
    "zhongzhou": "中州集 (四庫全書本)",        # 金·元好問：金
    "guangyun": "廣韻 (四庫全書本)/卷",        # 宋·陳彭年：韻書
    "jiliyun":  "集韻 (四庫全書本)/卷",        # 宋·丁度：韻書
    "cilv":     "詞律 (四庫全書本)/卷",        # 清·萬樹：詞譜
    "cipu":     "御定詞譜 (四庫全書本)/卷",    # 清·王奕清：詞譜（即《欽定詞譜》）
}


def api(params: dict) -> dict:
    url = API + urllib.parse.urlencode(params)
    r = subprocess.run(["curl", "-sS", "-m", "40", "-A", UA, url], capture_output=True)
    try:
        return json.loads(r.stdout.decode("utf-8"))
    except Exception:
        return {"_error": r.stdout[:200].decode("utf-8", "replace")}


def enumerate_prefix(prefix: str) -> list:
    """前缀枚举，自动翻页。"""
    titles, cont = [], {}
    while True:
        p = {"action": "query", "list": "allpages", "apprefix": prefix,
             "aplimit": "500", "format": "json"}
        p.update(cont)
        d = api(p)
        page = d.get("query", {})
        titles += [x["title"] for x in page.get("allpages", [])]
        if "continue" in d:
            cont = d["continue"]
            time.sleep(1.5)
        else:
            break
    return titles


def main() -> int:
    rows = []
    for series, prefix in SERIES.items():
        titles = enumerate_prefix(prefix)
        for i, t in enumerate(titles, 1):
            vol = t.split("/")[-1] if "/" in t else t
            rows.append({"series": series, "title": t, "vol": vol, "order": i})
        print(f"[{series:10}] {len(titles):>3} 页  {titles[0] if titles else '-'} … {titles[-1] if titles else '-'}")
        time.sleep(1.5)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"合计 {len(rows)} 页 → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
