#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-15A 防复发测试：公开同步不得携带现代版权书正文。

只检查规则与白名单，不联网；A6 需要网络时单独标 NOT RUN。
"""
import sys
import importlib.util
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
DBROOT = TOOLS.parent
PROJECT = DBROOT.parent

spec = importlib.util.spec_from_file_location("gs", TOOLS / "github_sync.py")
gs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gs)

R = []


def t(i, name, cond, actual="", expect=""):
    R.append((i, name, bool(cond), str(actual)[:80], str(expect)[:40]))


def main():
    inc = "\n".join(gs.INCLUDE_FILES)
    exc = gs.EXCLUDE_PARTS

    t("A1", "白名单不含 r2_04_evidence 目录本身",
      "poetry-database/raw/r2_04_evidence\n" not in inc
      and not any(x.rstrip("/") == "poetry-database/raw/r2_04_evidence"
                  for x in gs.INCLUDE_FILES))
    t("A2", "黑名单含 full/ 与 chapters/",
      "/r2_04_evidence/full/" in exc and "/r2_04_evidence/chapters/" in exc, exc[:3])
    t("A3", "full 正文被排除",
      gs.is_excluded("poetry-database/raw/r2_04_evidence/full/A_027_诗律.md"))
    t("A4", "chapters 正文被排除",
      gs.is_excluded("poetry-database/raw/r2_04_evidence/chapters/A_027_诗律.md"))
    t("A5", "manifest.json 不被排除",
      not gs.is_excluded("poetry-database/raw/r2_04_evidence/manifest.json"))
    t("A7", "books/ 下文件被排除",
      gs.is_excluded("books/王力全集 汉语音韵学.pdf"))

    picked = gs.collect()
    rels = [x[0] for x in picked]
    bad = [r for r in rels if "/r2_04_evidence/full/" in r
           or "/r2_04_evidence/chapters/" in r]
    t("A8", "白名单展开后无版权正文", not bad, f"{len(bad)} 条", "0")
    t("A9", "白名单展开后无 books/", not [r for r in rels if r.startswith("books/")])
    t("A10", "白名单规模合理（>700 且 <1500）", 700 < len(rels) < 1500, len(rels))

    # A6 远端核查：可选，网络不可用则 NOT RUN
    remote = "NOT RUN"
    try:
        import json
        import urllib.request
        url = ("https://api.github.com/repos/iop666/Poetry-Generation-Skill/"
               "git/trees/main?recursive=1")
        with urllib.request.urlopen(url, timeout=20) as f:
            d = json.load(f)
        paths = [x["path"] for x in d.get("tree", []) if x["type"] == "blob"]
        n_full = sum(1 for p in paths if "/r2_04_evidence/full/" in p)
        n_chap = sum(1 for p in paths if "/r2_04_evidence/chapters/" in p)
        remote = f"full={n_full} chapters={n_chap}"
        t("A6", "远端 full/chapters 计数为 0", n_full == 0 and n_chap == 0, remote, "0/0")
    except Exception as e:
        R.append(("A6", "远端 full/chapters 计数为 0", None, f"NOT RUN: {e}"[:80], "0/0"))

    ok = sum(1 for x in R if x[2] is True)
    fail = [x for x in R if x[2] is False]
    for x in R:
        if x[2] is not True:
            print(("FAIL" if x[2] is False else "SKIP"), x[0], x[1], "|", x[3])
    print(f"total={len(R)} pass={ok} fail={len(fail)}")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
