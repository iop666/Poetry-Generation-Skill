#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
acquire.py —— 按 sources/manifest.json 实际获取资料

行为：
  1. 逐个来源下载，落盘到 raw/，保留原始字节（不改一字）。
  2. 计算 SHA-256、字节数、HTTP 状态、耗时。
  3. 每条写入 audit/acquisition_log.jsonl（追加，不覆盖）。
  4. 已存在的文件不重复下载（幂等），但仍记录一次 SKIP 条目。

许可与限速：
  · 仅访问 manifest 中列明的公有领域／MIT／CC BY-SA 资源。
  · 请求间隔 0.5 秒；UA 标明用途与联系方式。
  · 不重试到死：单源最多 2 次，失败即记录 FAILED，继续下一个。

运行：
  python3 tools/acquire.py            # 全部
  python3 tools/acquire.py --only CP  # 只采 source_id 前缀
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(BASE, "sources", "manifest.json")
LOG = os.path.join(BASE, "audit", "acquisition_log.jsonl")
UA = ("PoetryDatabase/1.0 (academic corpus build; contact: local user) "
      "python-urllib/3")
DELAY = 0.5


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def fetch_to(url: str, dst: str, timeout=40):
    """
    直接由 curl 写盘（不经 stdout 管道），返回 HTTP 状态码。
    原因：本机 urllib 对 cdn.jsdelivr.net 会卡在 read 阶段；且经 stdout 转存在大文件上偶发截断。
    直接 -o 写盘最稳，也便于校验字节数。
    """
    safe = urllib.parse.quote(url, safe=":/?&=#%@,")
    out = subprocess.run(
        ["curl", "-sS", "--compressed", "--max-time", str(timeout), "-A", UA,
         "-o", dst, "-w", "%{http_code}", safe],
        capture_output=True,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.decode("utf-8", "replace").strip() or f"curl exit {out.returncode}")
    code = out.stdout.decode("ascii", "replace").strip()
    return int(code) if code.isdigit() else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--timeout", type=int, default=60)
    a = ap.parse_args()

    man = json.load(open(MANIFEST, encoding="utf-8"))
    entries = [e for e in man["poetry_sources"] if not a.only or e["source_id"].startswith(a.only)]
    os.makedirs(os.path.dirname(LOG), exist_ok=True)

    stats = {"ACQUIRED": 0, "SKIPPED": 0, "FAILED": 0}
    print(f"待采 {len(entries)} 项\n")

    for i, e in enumerate(entries, 1):
        dst = os.path.join(BASE, e["local"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        rec = {
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "source_id": e["source_id"], "name": e["name"], "url": e["url"],
            "license": e["license"], "reliability": e["reliability"],
        }
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            rec.update({"status": "SKIPPED", "path": e["local"],
                        "bytes": os.path.getsize(dst), "sha256": sha256(dst)})
            stats["SKIPPED"] += 1
            print(f"[{i:>2}/{len(entries)}] SKIP  {e['source_id']}  {e['name']}")
        else:
            ok = False
            last_err = None
            for url in [e["url"], e.get("url_fallback")]:
                if not url:
                    continue
                for attempt in (1, 2, 3, 4):
                    t0 = time.time()
                    try:
                        code = fetch_to(url, dst, a.timeout)
                        nbytes = os.path.getsize(dst) if os.path.exists(dst) else 0
                        if code != 200 or nbytes == 0:
                            raise RuntimeError(f"HTTP {code} / {nbytes} bytes")
                        rec.update({"status": "ACQUIRED", "path": e["local"], "http": code,
                                    "bytes": nbytes, "sha256": sha256(dst),
                                    "elapsed_s": round(time.time() - t0, 2), "url_used": url})
                        stats["ACQUIRED"] += 1
                        print(f"[{i:>2}/{len(entries)}] OK    {e['source_id']}  {e['name']}  "
                              f"{nbytes:,}B  {rec['elapsed_s']}s")
                        ok = True
                        break
                    except Exception as ex:  # noqa: BLE001
                        last_err = f"{type(ex).__name__}: {ex}"
                        time.sleep(2 * attempt)
                if ok:
                    break
            if not ok:
                rec.update({"status": "FAILED", "error": last_err})
                stats["FAILED"] += 1
                print(f"[{i:>2}/{len(entries)}] FAIL  {e['source_id']}  {last_err}")
            time.sleep(DELAY)

        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\n采集完成：成功 {stats['ACQUIRED']}，跳过 {stats['SKIPPED']}，失败 {stats['FAILED']}")
    print(f"日志：{os.path.relpath(LOG, BASE)}")
    return 0 if stats["FAILED"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
