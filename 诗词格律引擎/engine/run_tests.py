#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_tests.py —— ROUND 1 独立测试集执行器

与 run_acceptance.py 的区别（对应 POETRY-AUDIT-2026-11-11-R1 / A05）：
  · run_acceptance.py 的六道题由本项目自出、自答、自评，属自测；
  · 本脚本的样本取自唐宋名篇与《钦定词谱》例词，题目先于结论存在，
    期望值写在 JSON 里，引擎只能去匹配，不能改题。

除逐例期望外，另执行 6 条全量不变量检查（A04 的结构性证据）：
  I1 每个位置状态必须落在 6 种之内
  I2 展示谱长度必须等于句长
  I3 「示谱为中」与「状态为 FLEXIBLE」必须一一对应
  I4 判为 PASS 的位置，该字读音必须唯一且与正格一致
  I5 违律条数必须等于违律计数
  I6 待确认条数必须等于待确认计数

用法：
  python3 engine/run_tests.py            # 全跑
  python3 engine/run_tests.py --only 03  # 只跑某文件
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from gedou import (FLEXIBLE, FAIL, PASS, UNKNOWN, check_ci, check_poem, render,  # noqa: E402
                   STATUS_GLYPH)
from yunshu import LEX  # noqa: E402

STATUSES = {"PASS", "FLEXIBLE", "FLEXIBLE_READING", "FAIL", "UNKNOWN", "NOT_CHECKED"}
LOGDIR = os.path.join(BASE, "reports", "round-1-audit", "logs")


def run_case(case: dict) -> dict:
    try:
        if case.get("词牌"):
            return check_ci(case["文"], case["词牌"], case.get("标题", case["id"]))
        return check_poem(case["文"], case.get("标题", case["id"]))
    except SystemExit as e:
        return {"_拒绝": str(e), "判定": "REJECTED", "错误": [], "待确认": [], "备注": []}


def judge(case: dict, res: dict) -> tuple[bool, list]:
    """返回 (是否通过, 失败原因列表)。"""
    exp = case.get("期望", {})
    bad = []
    verdict = res.get("判定", "REJECTED")
    errs = "\n".join(res.get("错误", []))
    pend = "\n".join(res.get("待确认", []))
    notes = "\n".join(res.get("备注", []))
    n_fail = len(res.get("错误", []))
    n_pend = len(res.get("待确认", []))

    if "判定" in exp and verdict not in exp["判定"]:
        bad.append(f"判定应为 {exp['判定']}，实为 {verdict}")
    if "违律" in exp and n_fail != exp["违律"]:
        bad.append(f"违律数应为 {exp['违律']}，实为 {n_fail}")
    if "违律最少" in exp and n_fail < exp["违律最少"]:
        bad.append(f"违律数应 ≥ {exp['违律最少']}，实为 {n_fail}")
    if "待确认" in exp and n_pend != exp["待确认"]:
        bad.append(f"待确认数应为 {exp['待确认']}，实为 {n_pend}")
    for k in exp.get("错误含", []):
        if k not in errs:
            bad.append(f"错误中应含「{k}」")
    for k in exp.get("错误不含", []):
        if k in errs:
            bad.append(f"错误中不应含「{k}」")
    for k in exp.get("待确认含", []):
        if k not in pend:
            bad.append(f"待确认中应含「{k}」")
    for k in exp.get("备注含", []):
        if k not in notes:
            bad.append(f"备注中应含「{k}」")
    if exp.get("押韵同部") is True:
        items = res.get("押韵", [])
        if not items:
            bad.append("无押韵记录，无法验证同部")
        elif not all(r.get("同部") for r in items if r.get("同部") is not None):
            bad.append("韵脚应全部同部，实有不同部")
    pos = case.get("定点校验")
    if pos:
        try:
            cell = res["平仄表"][pos["句"] - 1]["格"][pos["字位"] - 1] if "平仄表" in res \
                else res["平仄"][pos["句"] - 1]["格"][pos["字位"] - 1]
            if cell["字"] != pos["字"]:
                bad.append(f"定点校验字数不符：应为「{pos['字']}」，实为「{cell['字']}」")
            if cell["状态"] != pos["期望状态"]:
                bad.append(f"第{pos['句']}句第{pos['字位']}字状态应为 {pos['期望状态']}，实为 {cell['状态']}")
        except Exception as e:  # noqa: BLE001
            bad.append(f"定点校验取值失败：{e}")
    return (not bad), bad


def invariants(case: dict, res: dict) -> list:
    """结构不变量检查。返回违规描述列表。"""
    bad = []
    if res.get("判定") == "REJECTED":
        return bad
    is_ci = "词牌" in res
    rows = res.get("平仄", []) if is_ci else res.get("平仄表", [])
    for row in rows:
        shown = row.get("谱") if is_ci else row.get("示谱")
        text = row["文"]
        if len(shown) != len(text):
            bad.append(f"第{row['句']}句：展示谱长 {len(shown)} ≠ 句长 {len(text)}")
        for cell in row["格"]:
            st = cell["状态"]
            if st not in STATUSES:
                bad.append(f"第{row['句']}句第{cell['第']}字：非法状态 {st}")
            if is_ci:
                if (cell["正格"] == "中") != (st == FLEXIBLE):
                    bad.append(f"第{row['句']}句第{cell['第']}字：词谱中位与 FLEXIBLE 不对应")
            elif st != "NOT_CHECKED":
                ch_at = shown[cell["第"] - 1]
                if (ch_at == "中") != (st == FLEXIBLE):
                    bad.append(f"第{row['句']}句第{cell['第']}字：「示谱为{'中' if ch_at == '中' else '定'}」"
                               f"与状态 {st} 不对应")
            if st == PASS:
                ts = LEX.tone_state(cell["字"])
                if ts != cell["正格"]:
                    bad.append(f"第{row['句']}句第{cell['第']}字「{cell['字']}」判 PASS，"
                               f"但读音状态为 {ts}，正格为 {cell['正格']}")
    n_cell_fail = sum(1 for r in rows for c in r["格"] if c["状态"] == FAIL)
    n_err = len(res.get("错误", []))
    if n_cell_fail and not n_err:
        bad.append(f"有 {n_cell_fail} 个逐字 FAIL 却无违律记录")
    if not n_err and res.get("判定") == "违律":
        bad.append("违律判定与零违律记录矛盾")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="只跑文件名前缀，如 03")
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(BASE, "tests", "*.json")))
    if a.only:
        files = [f for f in files if os.path.basename(f).startswith(a.only)]

    buf = io.StringIO()

    def w(s=""):
        buf.write(s + "\n")

    total = passed = 0
    inv_total = inv_bad = 0
    records = []
    w("ROUND 1 独立测试集执行记录")
    w("=" * 72)
    w("样本来源：唐宋名篇通行本、《钦定词谱》例词；期望值先于执行写入 tests/*.json。")
    w("")
    for path in files:
        spec = json.load(open(path, encoding="utf-8"))
        w(f"## {os.path.basename(path)}　{spec.get('类别', '')}")
        w(f"说明：{spec.get('说明', '')}")
        w("")
        cases = list(spec.get("样本", []))
        if spec.get("基线"):
            cases = [dict(spec["基线"], id=spec["基线"].get("id", "BASE"), _base=True)] + cases
        for case in cases:
            res = run_case(case)
            ok, reasons = judge(case, res)
            invs = invariants(case, res)
            total += 1
            passed += int(ok and not invs)
            inv_total += 1
            inv_bad += int(bool(invs))
            flag = "PASS" if (ok and not invs) else "FAIL"
            w(f"[{flag}] {case['id']}　{case.get('类别', case.get('标题', ''))}")
            w(f"       判定={res.get('判定', 'REJECTED')}　违律={len(res.get('错误', []))}"
              f"　待确认={len(res.get('待确认', []))}")
            if reasons:
                for r in reasons:
                    w(f"       ✗ {r}")
            if invs:
                for r in invs[:6]:
                    w(f"       ✗ 不变量：{r}")
            records.append({
                "文件": os.path.basename(path), "id": case["id"],
                "类别": case.get("类别", ""), "判定": res.get("判定", "REJECTED"),
                "违律": len(res.get("错误", [])), "待确认": len(res.get("待确认", [])),
                "通过": ok and not invs, "失败原因": reasons, "不变量违规": invs,
                "错误": res.get("错误", []), "待确认明细": res.get("待确认", []),
                "输出": render(res),
            })
        w("")

    w("=" * 72)
    w(f"用例总数 {total}　逐例通过 {passed}　不通过 {total - passed}")
    w(f"不变量检查 {inv_total} 例，违规 {inv_bad} 例")
    w(f"用例通过率 {passed / total:.1%}" if total else "无用例")

    os.makedirs(LOGDIR, exist_ok=True)
    with open(os.path.join(LOGDIR, "independent_test_results.json"), "w", encoding="utf-8") as f:
        json.dump({"用例总数": total, "通过": passed, "不变量违规": inv_bad, "明细": records},
                  f, ensure_ascii=False, indent=1)
    with open(os.path.join(LOGDIR, "independent_test_console.txt"), "w", encoding="utf-8") as f:
        f.write(buf.getvalue())

    print(buf.getvalue())
    return 0 if passed == total and inv_bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
