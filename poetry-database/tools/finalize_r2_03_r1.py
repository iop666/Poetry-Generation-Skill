#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-03-R1 收尾：标记作废的对照基线、登记本轮质量发现。

R2-03 的 macOS Vision 版 pages.jsonl 存在 16 页一批的重复填充，
按 page 内连接出来的 ocr_comparison 因此不可用于逐页结论。
本脚本不删除任何数据（失败记录须留存），只加显式的有效性标记。
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paddle_rerun as pr  # noqa: E402

FINDINGS = [
    ("R2-03-VISION-DUP", "wangli_shicilv", 432, 94, 337,
     "Vision 版 432 页中 337 页与前一页完全相同，仅 94 份不同文本；16 页一批重复填充"),
    ("R2-03-VISION-DUP", "wangli_yinyunxue", 476, 45, 431,
     "Vision 版 476 页中 431 页重复，仅 45 份不同文本"),
    ("R2-03-VISION-DUP", "wangli_tongyuan", 783, 64, 719,
     "Vision 版 783 页中 719 页重复，仅 64 份不同文本"),
    ("PADDLE-NO-DUP", "ALL", 1691, 1682, 0,
     "PaddleOCR-VL-1.6 三本共 1691 页，相邻重复 0，空页 9（7+1+1）"),
    ("PADDLE-PAGE-ORDER", "wangli_shicilv", 3, 3, 0,
     "PDF p35/p100/p200 原页图像与同号 Paddle 文本逐页吻合，页序正确；"
     "此前所谓『页码漂移』系 Vision 重复填充造成的假象，已撤回"),
    ("PADDLE-RUSHENG-MARK", "ALL", 4368, 4368, 0,
     "PaddleOCR 用 $\\underset{\\cdot}{X}$ 保留入声字下加点标记 4368 处，Vision 版 0 处"),
    ("PADDLE-RING-NUM", "wangli_shicilv", 815, 815, 0,
     "PaddleOCR 把『字外加圈』识成带圈数字 ⑨/⑩ 共 815 处，属新失败模式，不得直接引用"),
]


def main() -> int:
    con = sqlite3.connect(pr.DB)
    cols = {r[1] for r in con.execute("PRAGMA table_info(ocr_comparison)")}
    if "baseline_valid" not in cols:
        con.execute("ALTER TABLE ocr_comparison ADD COLUMN baseline_valid INTEGER DEFAULT 0")
    con.execute("UPDATE ocr_comparison SET baseline_valid=0")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS ocr_quality_findings(
      finding_id TEXT, book_id TEXT, nominal INTEGER, distinct_text INTEGER,
      duplicate_pages INTEGER, detail TEXT,
      PRIMARY KEY(finding_id, book_id));
    """)
    con.executemany("INSERT OR REPLACE INTO ocr_quality_findings VALUES (?,?,?,?,?,?)", FINDINGS)
    con.commit()
    print("ocr_comparison.baseline_valid 全部置 0（Vision 基线损坏，逐页对照不可用于结论）")
    print("ocr_quality_findings 写入", con.execute("SELECT COUNT(*) FROM ocr_quality_findings").fetchone()[0], "条")

    # 基于错误前提产出的对齐表，显式标记作废，不删除
    ap = pr.PADDLE_ROOT / "alignment.json"
    if ap.exists():
        data = json.loads(ap.read_text(encoding="utf-8"))
        for info in data.values():
            info["status"] = "INVALID"
            info["reason"] = ("对齐前提是『Paddle 页序漂移』，经 PDF 原图核验为误判；"
                              "真实原因是 Vision 基线重复填充。本表保留作过程记录，不得使用。")
        ap.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("alignment.json 已标记 INVALID（保留过程记录）")

    # 逐页对照产物同样标记
    sp = pr.PADDLE_ROOT / "COMPARISON_SUMMARY.json"
    if sp.exists():
        d = json.loads(sp.read_text(encoding="utf-8"))
        d = {"status": "INVALID_FOR_PAGE_LEVEL_CONCLUSIONS",
             "reason": "Vision 基线重复填充，按 page 内连接无效；全书级去重统计仍有效",
             "books": d}
        sp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        print("COMPARISON_SUMMARY.json 已标记逐页结论无效")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
