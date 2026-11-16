#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-07 收尾：韵式校正、字数审计、外部差异、原图核验、12 个特殊案例。

所有判断都带证据字段；无法判定的保持 UNRESOLVED / UNKNOWN，不做知识补全。
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database" / "poetry.db"
SRC = ROOT / "raw" / "books_native" / "long_yushsheng_cilv" / "pages.jsonl"
EXT = ROOT / "raw" / "r2_07_external.json"
OUT = ROOT / "raw" / "r2_07_finalize.json"

NS = lambda x: re.sub(r"[\s\u3000]+", "", x or "")


def load_pages() -> dict[int, str]:
    rows = {}
    for line in SRC.open(encoding="utf-8"):
        r = json.loads(line)
        rows[int(r["page"])] = r["text"]
    return rows


def main() -> int:
    con = sqlite3.connect(DB)
    pages = load_pages()
    report = {}

    # ---------- 1. 韵式：标签明言优先 ----------
    con.execute("ALTER TABLE cipai_forms_r2_07 ADD COLUMN rhyme_tone_source TEXT"
                if "rhyme_tone_source" not in
                [r[1] for r in con.execute("PRAGMA table_info(cipai_forms_r2_07)")] else
                "SELECT 1")
    fixed = []
    for fid, note, rt in con.execute(
            "SELECT form_id, pattern_note, rhyme_tone FROM cipai_forms_r2_07").fetchall():
        note = note or ""
        # 注意：「平仄韵互叶」同时含「平韵」「仄韵」子串，必须先判「平仄」
        if "平仄" in note:
            con.execute("UPDATE cipai_forms_r2_07 SET rhyme_tone='平仄', "
                        "rhyme_tone_source='PATTERN_LABEL_MIXED' WHERE form_id=?", (fid,))
            continue
        if "平韵" in note:
            want, src = "平", "LABEL"
        elif "仄韵" in note:
            want, src = "仄", "LABEL"
        else:
            con.execute("UPDATE cipai_forms_r2_07 SET rhyme_tone_source='PATTERN' WHERE form_id=?",
                        (fid,))
            continue
        if rt != want:
            fixed.append((fid, note, rt, want))
        con.execute("UPDATE cipai_forms_r2_07 SET rhyme_tone=?, rhyme_tone_source=? "
                    "WHERE form_id=?", (want, src, fid))
    report["rhyme_fixed"] = fixed

    # ---------- 2. 字数审计：逐条给判定与证据 ----------
    con.executescript("""
    DROP TABLE IF EXISTS cipai_count_audit_r2_07;
    CREATE TABLE cipai_count_audit_r2_07(
      form_id TEXT PRIMARY KEY, cipai_name TEXT, pattern_label TEXT,
      computed INTEGER, declared TEXT, delta INTEGER,
      verdict TEXT, evidence TEXT, external_chars TEXT, resolved INTEGER);
    """)
    ext = json.loads(EXT.read_text(encoding="utf-8")) if EXT.exists() else []
    ext_by_name: dict[str, list[int]] = {}
    for e in ext:
        ext_by_name.setdefault(e["name"], []).append(e["chars"])

    VERDICT = {
        "F07-0007": ("EXPECTED_VARIANT", "原书标签即「格一（七言绝句式）」，28 字为七绝体，与双调 54 字非同一体", 1),
        "F07-0018": ("EXPECTED_VARIANT", "原书描述：「别有《摊破浣溪沙》…上下片各增三字」→ 42+6=48", 1),
        "F07-0021": ("EXPECTED_VARIANT", "原书标签「格二（添字）」，48＝44+4", 1),
        "F07-0071": ("EXPECTED_DOUBLE", "单调 34 字重填一片为双调，34×2=68", 1),
        "F07-0099": ("EXPECTED_VARIANT", "原书标签「格二（转调踏莎行）」，别体 65 字", 1),
        "F07-0037": ("VARIANT_UNSTATED", "原书描述「约有三格，第三格增二字」→ 58+2=60；网站亦标 60 字", 1),
        "F07-0165": ("VARIANT_UNSTATED", "原书描述「五代人词略有增减字数者，兹举两式」，27 与 30 即两式；网站亦标 30 字", 1),
        "F07-0060": ("OCR_OR_DESC_INCONSISTENT", "谱行合计 106，原书自述 107；外部目录亦为 106 字 → 判为原书自述与谱行不一致，谱行 106 可采", 1),
        "F07-0143": ("VARIANT_UNSTATED", "原书「格三」另体，自述 102 字指定格；谱行 103，外部目录亦标 103 字", 1),
        "F07-0100": ("ORIGINAL_PRINT_OMISSION", "原图 900dpi 核验：下片第三句仅 6 个符号（上片同位置 7 个），合计 59；原书自述「六十字」→ 排印脱一符号", 0),
        "F07-0066": ("UNRESOLVED_COUNT_DELTA", "谱行 144，原书与外部均 143；差 1 符号未能定位，图证不足以判定为 OCR 或排印", 0),
        "F07-0188": ("EXPECTED_VARIANT", "原书描述「韦庄体重填一片，增四字」→ 23×2+4=50；外部目录作 52，另说并存", 0),
    }
    rows = con.execute("""
        SELECT form_id,cipai_name,pattern_label,total_characters,declared_chars,diff_kind
        FROM cipai_forms_r2_07 WHERE diff_kind<>'' OR declared_match IS NULL
        ORDER BY form_id""").fetchall()
    for fid, nm, lab, comp, decl, kind in rows:
        v, ev, resolved = VERDICT.get(fid, ("UNKNOWN", "未逐条判定", 0))
        ds = [int(x) for x in (decl or "").split(",") if x.strip().isdigit()]
        delta = (comp - ds[0]) if ds else None
        con.execute("INSERT INTO cipai_count_audit_r2_07 VALUES (?,?,?,?,?,?,?,?,?,?)", (
            fid, nm, lab, comp, decl, delta, v, ev,
            ",".join(map(str, ext_by_name.get(nm, []))), resolved))
    report["count_audit"] = len(rows)

    # ---------- 2b. 上下片结构判定（只用原书描述或两半同构，不靠字数猜） ----------
    if "stanza_structure" not in [r[1] for r in con.execute("PRAGMA table_info(cipai_forms_r2_07)")]:
        con.execute("ALTER TABLE cipai_forms_r2_07 ADD COLUMN stanza_structure TEXT")
    for fid, src_, total, desc in con.execute("""
            SELECT f.form_id, f.stanza_split_source, f.total_characters, e.desc_text
            FROM cipai_forms_r2_07 f JOIN cipai_entities_r2_07 e ON e.entity_id=f.cipai_id"""):
        if src_ == "DESCRIPTION":
            v = "双调（原书明言）"
        elif src_ == "IDENTICAL_HALVES":
            v = "双调（两半同构）"
        elif desc and re.search(r"(上下片|前后片|双调|重填|两片)", desc) and total >= 60:
            v = "双调（原书明言，句数不可均分）"
        elif total and total <= 44:
            v = "单调（按字数推断，原书未明言）"
        else:
            v = "UNKNOWN"
        con.execute("UPDATE cipai_forms_r2_07 SET stanza_structure=? WHERE form_id=?", (v, fid))

    # ---------- 3. 例词层的「变格」标签（与格标题分开） ----------
    ex_labels = Counter()
    for pg in range(16, 251):
        for ln in pages.get(pg, "").splitlines():
            s = NS(ln)
            m = re.match(r"^例[一二三四五六七八九十]*[（(]([^）)]{1,10})[）)]", s)
            if m:
                ex_labels[m.group(1)] += 1
    report["example_labels"] = ex_labels.most_common()

    # ---------- 4. 原图核验记录 ----------
    con.executescript("""
    DROP TABLE IF EXISTS ocr_image_checks_r2_07;
    CREATE TABLE ocr_image_checks_r2_07(
      check_id TEXT PRIMARY KEY, cipai_name TEXT, pdf_page INTEGER,
      item TEXT, method TEXT, finding TEXT, verdict TEXT, dpi INTEGER);
    """)
    CHECKS = [
        ("IC-01", "钗头凤", 123, "定格下片第三句符号数",
         "300/420/900dpi 三级放大 + 文字层 bbox 精确裁切", "上片同位置 7 符号，下片仅 6 符号；原书自述六十字", "PRINT_OMISSION", 900),
        ("IC-02", "瑞鹤仙", 180, "定格三/四行「二字句」是否真实",
         "800dpi 放大 + 文字层 bbox", "图与文字层一致，确为 2 符号；非 OCR 丢字", "MATCH", 800),
        ("IC-03", "夜飞鹊", 80, "定格谱行总符号数",
         "380dpi 全谱带 + 逐行人工计数", "谱行密度高，未能稳定逐符号计数；文字层合计 106，与外部目录一致", "UNRESOLVED", 380),
        ("IC-04", "满江红", 151, "94 字变格是否另有谱",
         "原文与附注通读", "仅附注「又于第七句增一『不』字，是为变格」，原书未另立谱", "TEXT_CONFIRMED", 0),
        ("IC-05", "诉衷情", 243, "44 字定格是否在本版",
         "全书检索 + 目录核对", "本版仅错叶格 33 字一体；网站另立平韵格 44 字，属编排差异", "TEXT_CONFIRMED", 0),
        ("IC-06", "水龙吟", 173, "变格是否另立格",
         "原文通读", "作「例四（变格）」，非格标题；网站另立条目", "TEXT_CONFIRMED", 0),
    ]
    for c in CHECKS:
        con.execute("INSERT INTO ocr_image_checks_r2_07 VALUES (?,?,?,?,?,?,?,?)", c)
    report["image_checks"] = len(CHECKS)

    # ---------- 5. 外部差异 ----------
    con.executescript("""
    DROP TABLE IF EXISTS cipai_source_differences_r2_07;
    CREATE TABLE cipai_source_differences_r2_07(
      diff_id TEXT PRIMARY KEY, cipai_name TEXT, item TEXT,
      local_value TEXT, external_value TEXT, page INTEGER,
      cause TEXT, confirmed INTEGER, adopted TEXT);
    """)
    DIFFS = [
        ("SD-01", "诉衷情", "韵式类别与格数",
         "平仄韵错叶格；1 格 33 字", "平韵格；另见 44 字定格（字数页列 33 别格 + 44 定格）", 228,
         "本版把 33 字一体列入错叶格，44 字一体未收；网站按 44 字定格归类", 1, "本版原书"),
        ("SD-02", "满江红", "格数",
         "2 格（定格 93、格二平韵 93）", "3 条（93 定格、93 变格、94 变格）", 133,
         "原书 94 字变体仅在附注说明，未另立谱；网站据附注另立条目", 1, "本版原书"),
        ("SD-03", "水龙吟", "变格是否独立成格",
         "1 格（定格 102）", "2 条（102 定格、102 变格）", 158,
         "原书作「例四（变格）」，是例词标签而非格标题", 1, "本版原书"),
        ("SD-04", "石州慢", "变格是否独立成格",
         "1 格（定格 102）", "2 条（102 定格、102 变格）", 176,
         "原书作「例三（变格）」并在附注说明句法差异", 1, "本版原书"),
        ("SD-05", "南歌子", "双调是否独立成格",
         "1 格（定格 26）", "2 条（26 定格、52 双调）", 17,
         "原书双调只作「例二（双调）」，网站拆为独立条目", 1, "本版原书"),
        ("SD-06", "忆江南", "双调是否独立成格", "1 格（定格 27）", "2 条（27 定格、54 双调）", 19,
         "原书双调作「例三（双调）」", 1, "本版原书"),
        ("SD-07", "江城子", "双调是否独立成格", "1 格（定格 35）", "2 条（35 定格、70 双调）", 27,
         "原书双调作例词", 1, "本版原书"),
        ("SD-08", "钗头凤", "总字数", "谱行 59，自述 60", "72 字", 123,
         "本版排印脱一符号（图证）；网站 72 字与本版自述均不合，三方互异", 0, "本版谱行，存疑"),
        ("SD-09", "浪淘沙", "格三字数", "谱行 133，自述 134", "133 字", 23,
         "原书自述 134 与谱行、网站均差 1", 1, "谱行 133（与网站一致）"),
        ("SD-10", "夜飞鹊", "定格字数", "谱行 106，自述 107", "106 字", 80,
         "原书自述多 1 字", 1, "谱行 106（与网站一致）"),
        ("SD-11", "瑞鹤仙", "格三字数", "谱行 103，自述 102", "103 字", 180,
         "自述 102 指定格，格三另体为 103", 1, "谱行 103（与网站一致）"),
        ("SD-12", "六州歌头", "格二字数", "谱行 144", "143 字", 89,
         "差 1 符号未定位", 0, "待定"),
        ("SD-13", "荷叶杯", "变格字数", "谱行 50", "52 字", 243,
         "本版自述「韦庄体重填一片，增四字」→50；网站 52，计算口径不同", 0, "本版谱行，存疑"),
        ("SD-14", "念奴娇", "变格二韵式", "标签「平韵格」，谱行韵脚多标仄", "平韵格", 166,
         "标签与谱行括注不一致，标签优先并标记", 1, "标签"),
        ("SD-15", "满江红", "格二韵式", "标签「平韵格」，谱行韵脚多标仄", "平韵格（变格）", 135,
         "同上", 1, "标签"),
    ]
    for d in DIFFS:
        con.execute("INSERT INTO cipai_source_differences_r2_07 VALUES (?,?,?,?,?,?,?,?,?)", d)
    report["source_diffs"] = len(DIFFS)

    # ---------- 6. 十二个特殊案例 ----------
    con.executescript("""
    DROP TABLE IF EXISTS cipai_special_cases_r2_07;
    CREATE TABLE cipai_special_cases_r2_07(
      case_id TEXT PRIMARY KEY, cipai_name TEXT, question TEXT,
      finding TEXT, forms_summary TEXT, source_pages TEXT, status TEXT);
    """)
    def forms_of(name: str) -> tuple[str, str]:
        rs = con.execute("""SELECT pattern_label,total_characters,sentence_count,
                                   rhyme_count,rhyme_tone,pdf_page
                            FROM cipai_forms_r2_07 WHERE cipai_name=? ORDER BY form_seq""",
                         (name,)).fetchall()
        summary = "；".join(f"{r[0]} {r[1]}字/{r[2]}句/{r[3]}韵/{r[4]}" for r in rs)
        pages = ",".join(str(r[5]) for r in rs)
        return summary, pages

    CASES = [
        ("SC-01", "浣溪沙", "摊破浣溪沙是独立词牌还是本调之格？",
         "本版作「格二（摊破浣溪沙）」，48 字＝42＋上下片各增三字；另有别名《山花子》。不另立词牌。"),
        ("SC-02", "南乡子", "三格的字数、韵式如何分？",
         "格一 27 字（平仄韵转换）、格二 30 字（同为转换，五代增减体）、格三 56 字（南唐改平韵、重填一片）。"),
        ("SC-03", "浪淘沙", "七绝体、双调小令、慢曲三者关系？",
         "格一 28 字七言绝句式、格二 54 字双调小令、格三 133 字商调慢曲；自述 134 与谱行差 1。"),
        ("SC-04", "临江仙", "「约有三格」具体指什么？",
         "格一 58、格二 58（句式不同）、格三 60（增二字）、格四 93（仙吕调慢曲）。"),
        ("SC-05", "木兰花", "减字、偷声、慢是否独立词牌？",
         "本版全部作为《木兰花》的格三/格四/格五：44 字减字、50 字偷声、101 字慢；不另立词牌，与网站目录一致。"),
        ("SC-06", "生查子", "三格字数相同，差别在哪？",
         "三格均 40 字、8 句 5 字、4 仄韵；差别在逐字平仄，不在字数。属「同字异谱」。"),
        ("SC-07", "满江红", "94 字变格是否另有谱？",
         "无。仅附注「又于第七句增一『不』字，是为变格」；格二为姜夔平韵体，93 字。"),
        ("SC-08", "念奴娇", "三种体的韵式差别？",
         "定格 100 字仄韵、变格一 100 字仄韵（句读不同）、变格二 100 字标签作平韵格。"),
        ("SC-09", "水龙吟", "变格为何不单列？",
         "本版以「例四（变格）」呈现，属例词标签；网站另立条目，属编排差异。"),
        ("SC-10", "六州歌头", "三格的韵式如何区分？",
         "格一 143 字纯平韵；格二 144 字平仄韵互叶；格三 143 字平仄韵递换。格二多 1 符号未定位。"),
        ("SC-11", "沁园春", "是否 114 字？",
         "是。定格 114 字、25 句、9 平韵，与自述及外部目录三方一致。R2-03 曾误记为 14 字，已勘误。"),
        ("SC-12", "宝鼎现", "定格与变格差异？",
         "两体均 157 字三段的仄韵长调；句读与韵位不同（定格 34 句 14 韵，变格 36 句 14 韵）。"),
    ]
    for cid, nm, q, f in CASES:
        summary, pg = forms_of(nm)
        con.execute("INSERT INTO cipai_special_cases_r2_07 VALUES (?,?,?,?,?,?,?)",
                    (cid, nm, q, f, summary, pg, "TEXT_VERIFIED"))
    report["special_cases"] = len(CASES)

    # ---------- 6b. 回填审计的 chars_ok / verdict ----------
    for c in con.execute("SELECT sql FROM sqlite_master WHERE name='cipai_audit_r2_07'"):
        pass
    for fid, verdict, resolved in con.execute(
            "SELECT form_id, verdict, resolved FROM cipai_count_audit_r2_07").fetchall():
        ok = 1 if (verdict.startswith("EXPECTED") or verdict in
                   ("VARIANT_UNSTATED", "ORIGINAL_PRINT_OMISSION",
                    "OCR_OR_DESC_INCONSISTENT")) else 0
        con.execute("UPDATE cipai_audit_r2_07 SET chars_ok=?, note_ok=note_ok WHERE form_id=?",
                    (ok, fid))
    # 审计总判定：字数未解者降级；缺谱/缺例词者记 PARTIAL；其余 PARSED
    con.execute("UPDATE cipai_audit_r2_07 SET verdict='PARSED'")
    con.execute("""UPDATE cipai_audit_r2_07 SET verdict='PARSED_PARTIAL'
                   WHERE example_ok=0 OR pingze_ok=0 OR rhyme_ok=0""")
    for fid, in con.execute(
            "SELECT form_id FROM cipai_count_audit_r2_07 WHERE resolved=0"):
        con.execute("UPDATE cipai_audit_r2_07 SET verdict='CHECK_REQUIRED' WHERE form_id=?", (fid,))

    con.commit()

    # ---------- 7. 汇总 ----------
    stat = {}
    stat["entities"] = con.execute("SELECT COUNT(*) FROM cipai_entities_r2_07").fetchone()[0]
    stat["forms"] = con.execute("SELECT COUNT(*) FROM cipai_forms_r2_07").fetchone()[0]
    stat["by_label"] = con.execute(
        "SELECT pattern_label,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1 ORDER BY 2 DESC").fetchall()
    stat["by_type"] = con.execute(
        "SELECT pattern_type,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1").fetchall()
    stat["by_section_form"] = con.execute(
        "SELECT section_name,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1 ORDER BY 2 DESC").fetchall()
    stat["by_section_entity"] = con.execute(
        "SELECT section_name,COUNT(*) FROM cipai_entities_r2_07 GROUP BY 1 ORDER BY 2 DESC").fetchall()
    stat["rhyme_tone"] = con.execute(
        "SELECT rhyme_tone,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1").fetchall()
    stat["multi_form"] = con.execute(
        "SELECT COUNT(*) FROM (SELECT cipai_name FROM cipai_forms_r2_07 GROUP BY 1 HAVING COUNT(*)>1)").fetchone()[0]
    stat["no_dingge"] = con.execute(
        "SELECT cipai_name FROM cipai_entities_r2_07 WHERE has_dingge=0").fetchall()
    stat["count_audit"] = con.execute(
        "SELECT verdict,COUNT(*) FROM cipai_count_audit_r2_07 GROUP BY 1 ORDER BY 2 DESC").fetchall()
    stat["declared_match"] = con.execute(
        "SELECT declared_match,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1").fetchall()
    stat["stanza"] = con.execute(
        "SELECT stanza_split_source,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1").fetchall()
    stat["stanza_struct"] = con.execute(
        "SELECT stanza_structure,COUNT(*) FROM cipai_forms_r2_07 GROUP BY 1 ORDER BY 2 DESC").fetchall()
    stat["audit_verdict"] = con.execute(
        "SELECT verdict,COUNT(*) FROM cipai_audit_r2_07 GROUP BY 1 ORDER BY 2 DESC").fetchall()
    stat["variants"] = con.execute("SELECT COUNT(*) FROM cipai_form_variants_r2_07").fetchone()[0]
    stat["variant_kinds"] = con.execute(
        "SELECT relation,COUNT(*) FROM cipai_form_variants_r2_07 GROUP BY 1 ORDER BY 2 DESC").fetchall()
    stat["rhyme_pos_ok"] = con.execute(
        "SELECT COUNT(*) FROM cipai_forms_r2_07 WHERE rhyme_count>0").fetchone()[0]
    stat["empty_form"] = con.execute(
        "SELECT COUNT(*) FROM cipai_forms_r2_07 WHERE total_characters=0").fetchone()[0]
    report["stats"] = stat
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print("韵式校正:", len(fixed), fixed[:3])
    for k, v in stat.items():
        print(f"  {k}: {v}")
    print("\n例词层标签:", report["example_labels"][:12])
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
