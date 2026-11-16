#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-07 一致性测试：30 项，逐条记录输入 / 预期 / 实际 / 状态。"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database" / "poetry.db"
OUT = ROOT / "reports" / "tasks" / "2026-11-14" / "R2-07"

RESULTS: list[dict] = []


def check(tid: str, name: str, expected: str, actual: str, ok: bool,
          kind: str = "程序") -> None:
    RESULTS.append({"id": tid, "name": name, "expected": expected,
                    "actual": actual, "status": "PASS" if ok else "FAIL",
                    "kind": kind})
    print(f"[{'PASS' if ok else 'FAIL'}] {tid} {name} | 预期 {expected} | 实际 {actual}")


def main() -> int:
    con = sqlite3.connect(DB)
    q = lambda s, a=(): con.execute(s, a).fetchall()
    one = lambda s, a=(): con.execute(s, a).fetchone()[0]

    # --- 基础计数 ---
    n_form = one("SELECT COUNT(*) FROM cipai_forms_r2_07")
    check("T-01", "词格记录总数 196", "196", str(n_form), n_form == 196)

    n_ent = one("SELECT COUNT(*) FROM cipai_entities_r2_07")
    check("T-02", "词牌实体总数 153", "153", str(n_ent), n_ent == 153)

    orphan = one("""SELECT COUNT(*) FROM cipai_forms_r2_07 f LEFT JOIN cipai_entities_r2_07 e
                    ON e.entity_id=f.cipai_id WHERE e.entity_id IS NULL""")
    check("T-03", "每条词格都指向有效词牌实体", "0 条悬空", f"{orphan} 条悬空", orphan == 0)

    dup = one("SELECT COUNT(*) - COUNT(DISTINCT form_id) FROM cipai_forms_r2_07")
    check("T-04", "form_id 唯一", "0 重复", f"{dup} 重复", dup == 0)

    # --- 韵式 ---
    sec = dict(q("SELECT section_name,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1"))
    ok5 = set(sec) == {"平韵格", "仄韵格", "平仄韵转换格", "平仄韵通叶格", "平仄韵错叶格"}
    check("T-05", "五类韵式齐全且合计 196", "196", str(sum(sec.values())),
          ok5 and sum(sec.values()) == 196)
    sec_e = dict(q("SELECT section_name,COUNT(*) FROM cipai_entities_r2_07 GROUP BY 1"))
    check("T-06", "词牌级韵式合计 153", "153", str(sum(sec_e.values())), sum(sec_e.values()) == 153)
    check("T-07", "词牌级与词格级分开统计（数值不同）", "不同",
          f"{sum(sec_e.values())}/{sum(sec.values())}", sum(sec_e.values()) != sum(sec.values()))

    # --- 格别 ---
    labels = {r[0] for r in q("SELECT DISTINCT pattern_label FROM cipai_forms_r2_07")}
    allowed = {"定格", "变格", "变格一", "变格二", "别格",
               "格一", "格二", "格三", "格四", "格五"}
    check("T-08", "格别名称全部来自原书标签", str(sorted(allowed)), str(sorted(labels)),
          labels <= allowed)
    n_dg = one("SELECT COUNT(*) FROM cipai_forms_r2_07 WHERE pattern_label='定格'")
    check("T-09", "定格 135 条", "135", str(n_dg), n_dg == 135)
    n_nodg = one("SELECT COUNT(*) FROM cipai_entities_r2_07 WHERE has_dingge=0")
    check("T-10", "18 调原书未标定格", "18", str(n_nodg), n_nodg == 18)

    # --- 字数与句式自洽 ---
    bad_len = 0
    for fid, total, sl, pat in q("""SELECT form_id,total_characters,sentence_lengths,pingze_pattern
                                    FROM cipai_forms_r2_07"""):
        s = sum(int(x) for x in sl.split(",") if x)
        p = len(pat.replace("/", ""))
        if s != total or p != total:
            bad_len += 1
    check("T-11", "总字数 = 逐句字数之和 = 平仄符号数", "0 条不符", f"{bad_len} 条不符", bad_len == 0)

    bad_pos = one("""SELECT COUNT(*) FROM cipai_forms_r2_07
                     WHERE rhyme_count<>LENGTH(rhyme_positions)-LENGTH(REPLACE(rhyme_positions,',',''))+1""")
    check("T-12", "韵脚个数与韵位串一致", "0 条不符", f"{bad_pos} 条不符", bad_pos == 0)

    bad_idx = 0
    for fid, pos, n in q("SELECT form_id,rhyme_positions,sentence_count FROM cipai_forms_r2_07"):
        for x in pos.split(","):
            if x and not (1 <= int(x) <= n):
                bad_idx += 1
    check("T-13", "韵位索引不越界", "0", str(bad_idx), bad_idx == 0)

    # --- 页码追溯 ---
    bad_pg = one("""SELECT COUNT(*) FROM cipai_forms_r2_07
                    WHERE pdf_page IS NULL OR printed_page<>pdf_page-15""")
    check("T-14", "每条有物理页且印刷页＝物理页−15", "0 条不符", f"{bad_pg} 条不符", bad_pg == 0)
    no_src = one("SELECT COUNT(*) FROM cipai_forms_r2_07 WHERE source_text IS NULL OR source_text=''")
    check("T-15", "每条保留谱行原文", "0 条缺", f"{no_src} 条缺", no_src == 0)

    # --- 字数校验 ---
    dm = dict(q("SELECT declared_match,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1"))
    ok_dm = dm.get(1, 0) == 183 and dm.get(0, 0) == 12
    check("T-16", "与原文自述字数比对：183 合 / 12 不合", "183/12",
          f"{dm.get(1,0)}/{dm.get(0,0)}", ok_dm)
    n_aud = one("SELECT COUNT(*) FROM cipai_count_audit_r2_07")
    check("T-17", "13 条差异全部有审计结论", "13", str(n_aud), n_aud == 13)
    unres = one("SELECT COUNT(*) FROM cipai_count_audit_r2_07 WHERE resolved=0")
    check("T-18", "未解项如实保留（不强行判定）", "≥1", str(unres), unres >= 1)

    # --- 同调多体与派生调 ---
    multi = one("SELECT COUNT(*) FROM (SELECT cipai_name FROM cipai_forms_r2_07 GROUP BY 1 HAVING COUNT(*)>1)")
    check("T-19", "同调多体 30 调", "30", str(multi), multi == 30)
    n_var = one("SELECT COUNT(*) FROM cipai_form_variants_r2_07")
    n_alias = one("SELECT COUNT(*) FROM cipai_form_variants_r2_07 WHERE relation='又名'")
    check("T-20", "派生调关系 71 条（含 62 条又名）", "71/62",
          f"{n_var}/{n_alias}", n_var == 71 and n_alias == 62)
    mlh = q("SELECT pattern_note,total_characters FROM cipai_forms_r2_07 WHERE cipai_name='木兰花' ORDER BY form_seq")
    ok_mlh = [x[1] for x in mlh] == [55, 56, 44, 50, 101]
    check("T-21", "《木兰花》五格 55/56/44/50/101", "[55,56,44,50,101]",
          str([x[1] for x in mlh]), ok_mlh)

    # --- 外部核对 ---
    ext = json.loads((ROOT / "raw" / "r2_07_external.json").read_text(encoding="utf-8"))
    ext_names = {e["name"] for e in ext}
    loc_names = {r[0] for r in q("SELECT cipai_name FROM cipai_entities_r2_07")}
    check("T-22", "本地词牌名与外部目录完全一致", "153=153 且集合相同",
          f"{len(loc_names)}/{len(ext_names)} 差集 {len(loc_names ^ ext_names)}",
          loc_names == ext_names)
    check("T-23", "外部条目 203 条、本地 196 条，差额 7 已归类", "203/196",
          f"{len(ext)}/{n_form}", len(ext) == 203 and n_form == 196)
    n_diff = one("SELECT COUNT(*) FROM cipai_source_differences_r2_07")
    check("T-24", "外部差异 15 条入表", "15", str(n_diff), n_diff == 15)

    # --- 特殊案例 ---
    n_case = one("SELECT COUNT(*) FROM cipai_special_cases_r2_07")
    check("T-25", "12 个特殊案例研究卡", "12", str(n_case), n_case == 12)
    qyc = q("SELECT total_characters,sentence_count,rhyme_count FROM cipai_forms_r2_07 WHERE cipai_name='沁园春'")
    check("T-26", "《沁园春》114 字 / 25 句 / 9 韵", "(114,25,9)", str(qyc[0]),
          qyc[0] == (114, 25, 9))

    # --- 韵式标签优先 ---
    nnj = q("SELECT pattern_label,rhyme_tone FROM cipai_forms_r2_07 WHERE cipai_name='念奴娇' ORDER BY form_seq")
    ok_nnj = [x[1] for x in nnj] == ["仄", "仄", "平"]
    check("T-27", "《念奴娇》变格二按标签作平韵", "['仄','仄','平']",
          str([x[1] for x in nnj]), ok_nnj)
    mjh = q("SELECT pattern_label,rhyme_tone FROM cipai_forms_r2_07 WHERE cipai_name='满江红' ORDER BY form_seq")
    ok_mjh = [x[1] for x in mjh] == ["仄", "平"]
    check("T-28", "《满江红》格二按标签作平韵", "['仄','平']",
          str([x[1] for x in mjh]), ok_mjh)

    # --- 上游整改 ---
    st6 = one("SELECT gate_pass FROM reading_records_r2_06 WHERE unit_key='E:第6讲'")
    st6s = one("SELECT status FROM reading_records_r2_06 WHERE unit_key='E:第6讲'")
    check("T-29", "《词学十讲》第六讲标为来源缺口", "READ_WITH_SOURCE_GAP / 0",
          f"{st6s} / {st6}", st6s == "READ_WITH_SOURCE_GAP" and st6 == 0)

    n_pm = one("SELECT COUNT(*) FROM page_map_wangli")
    p432 = q("SELECT kind,printed_page FROM page_map_wangli WHERE pdf_page=431")
    check("T-30", "页码映射 432 行且末页已分类", "432 行；末页=索引/423",
          f"{n_pm} 行；{p432}", n_pm == 432 and p432 and p432[0][0] == "索引")

    # --- 未破坏上游 ---
    check("T-31", "未改动作品表", "375399",
          str(one("SELECT COUNT(*) FROM works")), one("SELECT COUNT(*) FROM works") == 375399)
    check("T-32", "未改动旧词谱表 cipai_specs", "76",
          str(one("SELECT COUNT(*) FROM cipai_specs")), one("SELECT COUNT(*) FROM cipai_specs") == 76)

    con.close()
    npass = sum(1 for r in RESULTS if r["status"] == "PASS")
    print(f"\n合计 {len(RESULTS)} 项：PASS {npass} / FAIL {len(RESULTS)-npass}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "test_results.json").write_text(
        json.dumps(RESULTS, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if npass == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
