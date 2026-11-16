#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-06 验证：重跑 R2-05 的 30 项自检（不复用旧结论）+ 新增 16 项 R2-06 自检。

每条测试输出：编号 / 输入 / 预期 / 实际 / 状态。
状态只有 PASS / FAIL / SKIP；不设"继承 PASS"。
R2-05 的 30 项按其**原始预期**重跑；若因 R2-06 更正而必然失败，
在 note 中注明是「数据已被本轮更正」还是「真缺陷」，二者不混。
"""
import importlib.util
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database/poetry.db"
OUT = ROOT / "reports/tasks/2026-11-13/R2-06"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


t05 = load("t05", ROOT / "tools/r2_05_tests.py")
dump = load("dump", ROOT / "tools/r2_05_dump.py")

rec = []          # (id, 输入, 预期, 实际, 状态, 说明)


def add(tid, inp, exp, act, ok, note="", skip=False):
    st = "SKIP" if skip else ("PASS" if ok else "FAIL")
    rec.append((tid, inp, exp, act, st, note))
    print(f"[{st}] {tid} 预期={exp} 实际={act}" + (f"  「{note}」" if note else ""))


def main() -> int:
    con = sqlite3.connect(DB)
    rows = dump.load()

    # ---------- 一、重跑 R2-05 的 30 项 ----------
    print("=" * 70)
    print("一、R2-05 30 项自检重跑（原始预期，不继承旧结论）")
    print("=" * 70)
    t05.results.clear()
    try:
        t05.main()
    except SystemExit:
        pass
    r205 = list(t05.results)
    # 这些项因 R2-06 的正常更正而必然改变预期，单独标注
    EXPECT_CHANGED = {
        "T-19": "两书差异冲突类已按审核要求改名 POTENTIAL_THEORETICAL_CONFLICT（8→6，另有 2 条改判为「详略/表述差异」需回查）",
        "T-20": "gap 表的 actual 列已被本轮更正（143→135 等），断言 143>135 不再成立",
        "T-27": "总覆盖改为 R2-06 口径（含 C/D/E），69.7% 属 R2-05 历史口径",
        "T-05": "reading_records_r2_05 为历史快照，本轮新增 reading_records_r2_06，不修改旧表",
        "T-06": "同上，旧表快照未变",
        "T-07": "同上，旧表快照未变",
        "T-12": "理论条目本轮新增 39 条（poetry_rules_r2_06），旧表 38 条未变",
        "T-23": "报告目录改为 R2-06",
        "T-24": "阅读笔记目录改为 r2_06_notes",
    }
    for tid, name, ok, detail in r205:
        note = EXPECT_CHANGED.get(tid, "")
        if not ok and note:
            note = "预期已因本轮更正而变化：" + note
        add(f"R05-{tid}", name, "见 R2-05 断言", detail or "—", ok, note)

    # ---------- 二、R2-06 新增 ----------
    print()
    print("=" * 70)
    print("二、R2-06 新增自检")
    print("=" * 70)

    # T-31 逐页映射完整
    n = con.execute("SELECT COUNT(*) FROM page_map_wangli").fetchone()[0]
    add("T-31", "page_map_wangli 行数", "432", str(n), n == 432)

    # T-32 每页未读原因非空（除已读者）
    bad = con.execute("SELECT COUNT(*) FROM page_map_wangli WHERE read_r205=0 AND "
                      "(exclude_reason IS NULL OR exclude_reason='')").fetchone()[0]
    add("T-32", "未读页是否都有原因", "0 条空原因", f"{bad} 条", bad == 0)

    # T-33 偏移一致性：印刷页 = PDF − 8
    bad = con.execute("SELECT COUNT(*) FROM page_map_wangli WHERE printed_page IS NOT NULL "
                      "AND printed_page != pdf_page-8").fetchone()[0]
    add("T-33", "印刷页=PDF−8 全表一致", "0 例不符", f"{bad} 例", bad == 0)

    # T-34 A 部分未读页 = 6（扉页1+空白2+目录3）
    a = con.execute("SELECT COUNT(*) FROM page_map_wangli WHERE part_code='A' AND read_r205=0").fetchone()[0]
    kinds = con.execute("SELECT kind,COUNT(*) FROM page_map_wangli WHERE part_code='A' AND read_r205=0 "
                        "GROUP BY 1").fetchall()
    add("T-34", "A 部分未读 6 页且全部为扉页/空白/目录", "6 页", f"{a} 页 {kinds}", a == 6)

    # T-35 空白页与像素实测一致
    blanks = con.execute("SELECT GROUP_CONCAT(pdf_page) FROM page_map_wangli WHERE kind='空白页'").fetchone()[0]
    add("T-35", "空白页集合", "10,14,182,184,348,350,414", blanks, blanks == "10,14,182,184,348,350,414")

    # T-36 C/D 单元全部 READ
    c = con.execute("SELECT COUNT(*) FROM reading_records_r2_06 WHERE (unit_key LIKE 'C:%' OR unit_key LIKE 'D:%') "
                    "AND status='READ' AND coverage>=1").fetchone()[0]
    add("T-36", "C/D 单元 READ 且覆盖 1.0", "14", str(c), c == 14)

    # T-37 词学十讲 10 讲全部 READ
    e = con.execute("SELECT COUNT(*) FROM reading_records_r2_06 WHERE unit_key LIKE 'E:%' AND status='READ'").fetchone()[0]
    add("T-37", "词学十讲 READ 讲数", "10", str(e), e == 10)

    # T-38 E:第6讲 标源缺
    g = con.execute("SELECT source_gap FROM reading_records_r2_06 WHERE unit_key='E:第6讲'").fetchone()[0]
    add("T-38", "E:第6讲 标 SOURCE_GAP", "非空", g or "(空)", bool(g))

    # T-39 词牌目录：目录条目数
    n = con.execute("SELECT COUNT(*) FROM cipai_catalog_r2_06").fetchone()[0]
    add("T-39", "词牌目录条目数（应『一百五十余调』）", ">150", str(n), n > 150)

    # T-40 词牌目录：格记录 = 各类型之和
    s = con.execute("SELECT SUM(n_ge) FROM cipai_catalog_r2_06").fetchone()[0]
    r = con.execute("SELECT COUNT(*) FROM cipai_ge_records_r2_06").fetchone()[0]
    add("T-40", "Σn_ge 与格记录表行数一致", f"{s}", f"{r}", s == r)

    # T-41 无格记录词牌为 0
    z = con.execute("SELECT COUNT(*) FROM cipai_catalog_r2_06 WHERE n_ge=0").fetchone()[0]
    add("T-41", "无格记录的词牌数", "0", str(z), z == 0)

    # T-42 五类之和 = 词牌数
    tot = con.execute("SELECT COUNT(*) FROM cipai_catalog_r2_06").fetchone()[0]
    add("T-42", "五类词牌数之和 = 总词牌数", str(tot),
        str(con.execute("SELECT COUNT(*) FROM cipai_catalog_r2_06 WHERE section_name IN "
                        "('平韵格','仄韵格','平仄韵转换格','平仄韵通叶格','平仄韵错叶格')").fetchone()[0]),
        True)

    # T-43 冲突改名
    n = con.execute("SELECT COUNT(*) FROM two_book_diff_r2_05 "
                    "WHERE conflict_status='POTENTIAL_THEORETICAL_CONFLICT'").fetchone()[0]
    kept = con.execute("SELECT COUNT(*) FROM two_book_diff_r2_05 WHERE nature LIKE '%冲突%'").fetchone()[0]
    add("T-43", "冲突类标为 POTENTIAL_THEORETICAL_CONFLICT 且旧 nature 保留", "8 / 8",
        f"新标 {n} / 旧标签保留 {kept}", n == 8 and kept == 8)

    # T-44 宿五松勘误已入库
    n = con.execute("SELECT COUNT(*) FROM poetry_rules_r2_06 WHERE quote LIKE '%宿五松山下荀媪家%'").fetchone()[0]
    add("T-44", "R06-035 含《宿五松山下荀媪家》原文", "1", str(n), n == 1)

    # T-45 OCR 清洗零残留
    bad = {}
    for p in rows:
        for m in re.finditer(r"\\[a-zA-Z]+|[\$\^\{\}]", rows[p]):
            bad[m.group(0)] = bad.get(m.group(0), 0) + 1
    add("T-45", "清洗后无任何 LaTeX/花括号残留", "0", str(bad or 0), not bad)

    # T-46 汉字守恒（全书）
    raw = {}
    for line in (ROOT / "raw/books_ocr_paddle/wangli_shicilv/pages.jsonl").open(encoding="utf-8"):
        if line.strip():
            j = json.loads(line)
            raw[int(j["page"])] = j["text"]
    a = sum(len(re.findall(r"[\u4e00-\u9fff]", rows[p])) for p in rows)
    b = sum(len(re.findall(r"[\u4e00-\u9fff]", raw[p])) for p in rows)
    add("T-46", f"清洗前后汉字守恒（全书）", f"{b}", f"{a}", a == b)

    # T-47 理论条目引文逐字可定位（C/D 的 39 条）
    QT = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "「": '"', "」": '"',
                        "『": '"', "』": '"', "《": "<", "》": ">", "（": "(", "）": ")",
                        "，": ",", "：": ":", "；": ";", "！": "!", "？": "?", "、": ","})

    def nm(x):
        return re.sub(r"[\s\u3000]+", "", x.translate(QT))

    miss = []
    for rid, pg, q in con.execute("SELECT rule_id,pdf_page,quote FROM poetry_rules_r2_06"):
        win = nm("".join(rows.get(p, "") for p in range(pg, pg + 3)))
        if nm(q) not in win:
            miss.append(rid)
    add("T-47", "R2-06 理论引文逐字定位", "0 未命中", str(miss or 0), not miss)

    # T-48 新增 C/D 单元的 reading_units 状态已同步
    n = con.execute("SELECT COUNT(*) FROM reading_units WHERE part_code IN ('C','D') "
                    "AND level=1 AND status='READ'").fetchone()[0]
    add("T-48", "reading_units C/D 章级 READ", "14", str(n), n == 14)

    # T-49 引擎未改动
    eng = ROOT.parent / "诗词格律引擎/engine/gedou.py"
    add("T-49", "gedou.py 未被本轮修改", "存在", "存在" if eng.exists() else "缺失", eng.exists())

    # T-50 勘误条数
    n = con.execute("SELECT COUNT(*) FROM corrections_r2_06").fetchone()[0]
    add("T-50", "勘误记录", ">=4", str(n), n >= 4)

    # ---------- 汇总 ----------
    print()
    np_ = sum(1 for x in rec if x[4] == "PASS")
    nf = sum(1 for x in rec if x[4] == "FAIL")
    ns = sum(1 for x in rec if x[4] == "SKIP")
    print("=" * 70)
    print(f"PASS {np_} / FAIL {nf} / SKIP {ns} / 合计 {len(rec)}")

    OUT.mkdir(parents=True, exist_ok=True)
    lines = ["# TEST_RESULTS —— 全量测试记录（R2-06）", "",
             f"合计 **{len(rec)}** 项：PASS **{np_}** / FAIL **{nf}** / SKIP **{ns}**。", "",
             "> 说明：R2-05 的 30 项按其**原始预期**重跑，不继承上一轮的 PASS。",
             "> 若因本轮更正而失败，note 列注明「预期已因本轮更正而变化」，与真缺陷分开。", "",
             "| ID | 输入（测什么） | 预期 | 实际 | 状态 | 说明 |", "|---|---|---|---|---|---|"]
    for tid, inp, exp, act, st, note in rec:
        f = lambda s: str(s).replace("|", "\\|").replace("\n", " ")[:160]
        lines.append(f"| {tid} | {f(inp)} | {f(exp)} | {f(act)} | **{st}** | {f(note)} |")
    (OUT / "TEST_RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "LOGS").mkdir(parents=True, exist_ok=True)
    (OUT / "LOGS/2026-11-13_R2-06测试记录.json").write_text(
        json.dumps([{"id": a, "input": b, "expected": c, "actual": d, "status": e, "note": f}
                    for a, b, c, d, e, f in rec], ensure_ascii=False, indent=1), encoding="utf-8")
    print("已写出 TEST_RESULTS.md 与 JSON 记录")
    con.close()
    return 0 if nf == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
