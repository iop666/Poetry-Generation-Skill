#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 收尾：重算 facts、重生報告、修正增量表、重建清單與校驗值。"""
import os
import re
import glob
import json
import hashlib
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REP = os.path.join(ROOT, "reports", "tasks", "2026-11-14", "R2-09")

for s in ["r2_09_facts.py", "r2_09_rep1.py", "r2_09_rep2.py", "r2_09_rep3.py",
          "r2_09_rep4.py", "r2_09_rep5.py"]:
    r = subprocess.run(["python3", os.path.join(ROOT, "tools", s)],
                       capture_output=True, text=True)
    print(s, r.returncode, r.stderr.strip()[:200])

p = os.path.join(REP, "COMPLETE_REPORT.md")
s = open(p, encoding="utf-8").read()

# 修正增量表（用實際值，不用 facts 的舊值）
F = json.load(open(os.path.join(ROOT, "raw", "r2_09", "audit", "facts.json"), encoding="utf-8"))
new = """## 4 新增數據統計

本輪新增與歷史累計嚴格分列。**「本輪新增」只算本輪實際新做的，「歷史累計」含以前各輪。**

| 項目 | 本輪新增 | 歷史累計 | 上一輪（R2-08） | 實際增量 |
|---|---:|---:|---:|---|
| 詞林正韻字級記錄 | %d | %d | 11,382（折算） | **替換**，原折算數據作廢 |
| 中原音韻字級記錄 | %d | %d | 0（僅部目） | +%d |
| 集韻小韻（重建） | %d | %d | 4,432 | **−%d**（算法改嚴，非資料丟失） |
| 集韻韻頁 | 206 | 206 | 202 | +4 |
| 閱讀記錄觀點複核 | 120 | 120 | 0 | +120 |
| 詞譜原圖核驗（唯一對象） | 34 | 60 | 26 | +34 |
| 韻式衝突裁定 | 33 | 33 | 0（僅統計衝突數） | +33 |
| 字數異常對帳 | 13 | 13 | 13 | 重做（改為五方分列） |
| 例詞關聯重判 | 310 | 310 | 310（舊分類） | 重判 |
| 未掛接例詞再調查 | 114 | 114 | 0 | +114 |
| 多音字樣本 | 200 | 200 | 0 | +200 |
| 跨韻書案例 | 100 | 100 | 0 | +100 |
| 上古韻例樣本 | 40 | 40 | 0 | +40（全部未歸部） |
| 新增表 | 14 | 36（R2-07 10＋R2-08 12＋R2-09 14） | 12 | +14 |
| 自動化測試 | 71 | 71 | 61 | +10 |

**須注意兩處「負增長」與「替換」**：集韻小韻由 4,432 降為 %d，是因為本輪把「`○` 後不足 6 字者」排除（多為頁首導航殘段），
不是資料丟失；詞林正韻是由折算數據換成原書字表，兩者不可相加。

""" % (F["cilin_rows"], F["cilin_rows"], F["zy_rows"], F["zy_rows"], F["zy_rows"],
       F["jiyun_xiaoyun"], F["jiyun_xiaoyun"], 4432 - F["jiyun_xiaoyun"], F["jiyun_xiaoyun"])
a = s.index("## 4 新增數據統計")
b = s.index("## 5 歷史累計統計")
s = s[:a] + new + s[b:]

# 修正測試段落的通過數
s = re.sub(r"```\ntests \d+ PASS \d+ FAIL \d+\n```",
           "```\ntests 71 PASS %d FAIL %d\n```" % (F["tests_pass"], 71 - F["tests_pass"]), s)
s = s.replace("自動化測試 **71 項，通過 70**。", "自動化測試 **71 項，通過 %d**。" % F["tests_pass"])
s = s.replace("| I | 獨立審查 135 條、71 項測試、41 份報告 | 完成 |",
              "| I | 獨立審查 135 條、71 項測試、44 份報告 | 完成 |")
s = s.replace("| 報告檔 | 43 |", "| 報告檔 | %d |" % len(glob.glob(os.path.join(REP, "*"))))
s = s.replace("報告 43 份。", "報告 %d 份。" % len(glob.glob(os.path.join(REP, "*"))))
open(p, "w", encoding="utf-8").write(s)

# 重建 FILE_MANIFEST
files = sorted(glob.glob(os.path.join(REP, "*")))
skip = {"FILE_MANIFEST.md", "COMPLETE_REPORT.md", "COMPLETE_REPORT.sha256"}
rows = []
for f in files:
    b2 = os.path.basename(f)
    if b2 in skip:
        continue
    rows.append((b2, os.path.getsize(f), hashlib.sha256(open(f, "rb").read()).hexdigest()))
man = ["# 文件清單與校驗", "",
       "共 %d 個檔。SHA-256 由實際檔案計算。" % len(rows), "",
       "`COMPLETE_REPORT.md` 的校驗值單列於 `COMPLETE_REPORT.sha256`（因其本身不能包含自身雜湊）。", "",
       "| 檔名 | 位元組 | SHA-256 |", "|---|---:|---|"]
for b2, n, h in rows:
    man.append("| `%s` | %d | `%s` |" % (b2, n, h))
man += ["", "## 原始證據（位於 raw/r2_09/，未打包進報告目錄）", "",
        "| 路徑 | 說明 |", "|---|---|",
        "| `raw/r2_09/audit/` | 資料庫審計 JSON 與 CSV |",
        "| `raw/r2_09/reading/` | 120 條樣本、四批審查、476 頁賬本、音標複核 |",
        "| `raw/r2_09/c_pages/` | 集韻 120 條與 30 頁複核、廣韻 150 條抽檢 |",
        "| `raw/r2_09/images/` | 34 條詞譜裁切圖與核驗 CSV |",
        "| `raw/r2_09/conflicts/` | 33 條衝突裁定、13 條字數對帳 |",
        "| `raw/r2_09/links/` | 例詞關聯重判、114 條再調查 |",
        "| `raw/r2_09/rhyme/` | 詞林正韻、中原音韻原文 JSON |",
        "| `raw/r2_09/ancient/` | 上古音書目與詩經楚辭韻例 |",
        "| `raw/r2_09/polyphone/` | 200 多音字、100 跨韻書案例 |",
        "| `raw/r2_09/independent/` | 獨立審查 135 條明細 |"]
open(os.path.join(REP, "FILE_MANIFEST.md"), "w", encoding="utf-8").write("\n".join(man))

h = hashlib.sha256(open(p, "rb").read()).hexdigest()
open(os.path.join(REP, "COMPLETE_REPORT.sha256"), "w").write(h + "  COMPLETE_REPORT.md\n")
print("CR", os.path.getsize(p), h, "files", len(rows))
