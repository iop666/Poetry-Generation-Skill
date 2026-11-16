#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gedou.py —— 诗词格律审查引擎（v2，ROUND 1 整改版）

v1 的三个致命问题（POETRY-AUDIT-2026-11-11-R1 / A03、A04）：
  1. fits() 对「平仄两收」的字一律放行 —— 等于按格律反推读音；
  2. realized() 明确按谱还原读音 —— 为了通过检查而选音；
  3. 逐字表把「一三五不论」的位置直接标 ✓，模板与结论对不上。

v2 的处理：
  · 每个位置输出明确状态：PASS / FLEXIBLE / FLEXIBLE_READING / FAIL / UNKNOWN / NOT_CHECKED
  · 两读字不再自动通过：白名单外一律 UNKNOWN（待依义定音），白名单内记 FLEXIBLE_READING
  · 展示的「示谱」把不论位写成「中」，与逐字结果一一对应；正格另给说明
  · 孤平只施于「两平相连」型平收句（旧版对五言丁型句一律误判，杜甫《春望》曾被误杀）
  · 韵脚全仄 → 判为不适用近体格律（古体/仄韵体），逐字表置 NOT_CHECKED，不套近体谱

用法：
  python3 engine/gedou.py --text "山色苍茫暮雨收，……" --title 秋山
  python3 engine/gedou.py --ci "一曲离歌送客舟，……" --cipai 浣溪沙
  python3 engine/gedou.py --text ... --json out.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yunshu import LEX, POLICY_NOTE, T_BOTH, T_MISSING, T_PING, T_ZE, is_han  # noqa: E402

# ---------------------------------------------------------------- 状态常量

PASS = "PASS"
FLEXIBLE = "FLEXIBLE"
FLEXIBLE_READING = "FLEXIBLE_READING"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"
NOT_CHECKED = "NOT_CHECKED"

STATUS_GLYPH = {PASS: "✓", FLEXIBLE: "~", FLEXIBLE_READING: "≈", FAIL: "✗", UNKNOWN: "?", NOT_CHECKED: "－"}
STATUS_LABEL = {
    PASS: "固定位置，平仄相符",
    FLEXIBLE: "可平可仄位置（一三五不论），不作违律判定",
    FLEXIBLE_READING: "两读字按又音放宽，未计为通过",
    FAIL: "固定位置，平仄相反",
    UNKNOWN: "读音或韵部无法确定，需人工判定",
    NOT_CHECKED: "当前规则未执行检查",
}

# ---------------------------------------------------------------- 诗谱
# A/B/C/D 为七言四式，甲/乙/丙/丁 为五言四式；均为「正格」全字平仄，不含「中」。

QY = {
    "A": "仄仄平平仄仄平",
    "B": "平平仄仄仄平平",
    "C": "平平仄仄平平仄",
    "D": "仄仄平平平仄仄",
}
WY = {"甲": "仄仄平平仄", "乙": "平平仄仄平", "丙": "平平平仄仄", "丁": "仄仄仄平平"}
ALL_PATTERNS = {**QY, **WY}

TEMPLATES = {
    (7, 4): {
        "仄起首句入韵": (["A", "B", "C", "A"], True),
        "仄起首句不入韵": (["D", "B", "C", "A"], False),
        "平起首句入韵": (["B", "A", "D", "B"], True),
        "平起首句不入韵": (["C", "A", "D", "B"], False),
    },
    (7, 8): {
        "仄起首句入韵": (["A", "B", "C", "A", "D", "B", "C", "A"], True),
        "仄起首句不入韵": (["D", "B", "C", "A", "D", "B", "C", "A"], False),
        "平起首句入韵": (["B", "A", "D", "B", "C", "A", "D", "B"], True),
        "平起首句不入韵": (["C", "A", "D", "B", "C", "A", "D", "B"], False),
    },
    (5, 4): {
        "仄起首句不入韵": (["甲", "乙", "丙", "丁"], False),
        "仄起首句入韵": (["丁", "乙", "丙", "丁"], True),
        "平起首句不入韵": (["丙", "丁", "甲", "乙"], False),
        "平起首句入韵": (["乙", "丁", "甲", "乙"], True),
    },
    (5, 8): {
        "仄起首句不入韵": (["甲", "乙", "丙", "丁", "甲", "乙", "丙", "丁"], False),
        "仄起首句入韵": (["丁", "乙", "丙", "丁", "甲", "乙", "丙", "丁"], True),
        "平起首句不入韵": (["丙", "丁", "甲", "乙", "丙", "丁", "甲", "乙"], False),
        "平起首句入韵": (["乙", "丁", "甲", "乙", "丙", "丁", "甲", "乙"], True),
    },
}
FORM_NAME = {(7, 4): "七言绝句", (7, 8): "七言律诗", (5, 4): "五言绝句", (5, 8): "五言律诗"}

# 「一三五不论」：七言第 1/3/5 字、五言第 1/3 字为可平可仄位（0 基）
FLEX_POS = {7: (0, 2, 4), 5: (0, 2)}

# ---------------------------------------------------------------- 词谱
# 浣溪沙正体谱据《钦定词谱》卷四（韩偓「宿醉离愁慢髻鬟」）：
#   中仄中平中仄平／中平中仄仄平平／中平中仄仄平平
#   中仄中平平仄仄／中平中仄仄平平／中平中仄仄平平
# v1 把第一句第三字写成「平」，与《钦定词谱》「中」不符，本版已改（A01）。

CI_PATTERNS = {
    "浣溪沙": {
        "字数": 42,
        "句式": [7, 7, 7, 7, 7, 7],
        "谱": ["中仄中平中仄平", "中平中仄仄平平", "中平中仄仄平平",
               "中仄中平平仄仄", "中平中仄仄平平", "中平中仄仄平平"],
        "韵位": [1, 2, 3, 5, 6],
        "韵类": "平",
        "体": "正体",
        "依据": "《钦定词谱》卷四 浣溪沙，韩偓体；双调四十二字，前段三句三平韵，后段三句两平韵",
        "说明": "双调四十二字，上片三句三平韵；下片首句仄收不押，后两句平韵。",
    },
    "忆江南": {
        "字数": 27,
        "句式": [3, 5, 7, 7, 5],
        "谱": ["平中仄", "中仄仄平平", "中仄中平平仄仄", "中平中仄仄平平", "中仄仄平平"],
        "韵位": [2, 4, 5],
        "韵类": "平",
        "体": "正体",
        "依据": "《钦定词谱》卷一 忆江南，白居易体；单调二十七字，五句三平韵",
        "说明": "单调二十七字，五句三平韵。",
    },
    "相见欢": {
        "字数": 36,
        "句式": [6, 3, 9, 3, 3, 3, 9],
        "谱": ["中平中仄平平", "中平平", "中仄中平中仄仄平平",
               "中中仄", "中中仄", "仄平平", "中仄中平中仄仄平平"],
        "韵位": [1, 2, 3, 6, 7],
        "仄韵位": [4, 5],
        "韵类": "平",
        "体": "正体（部分校验）",
        "依据": "《钦定词谱》卷二 相见欢（乌夜啼），薛昭蕴体；上下片各三平韵，下片另有两仄韵",
        "说明": "双调三十六字：上片 6/3/9，下片 3/3/3/9。下片第 1、2 句押仄韵，"
                "本引擎尚无仄韵词谱，该二句平仄与用韵标记为未检查。",
    },
}

# 变体登记：只登记元数据，不提供可平可仄谱，故不参与校验（A01 整改要求「检查变体管理」）
CI_VARIANTS = {
    "浣溪沙": [
        {"名": "薛昭蕴体", "字数": 42, "句式": [7, 7, 7, 7, 7, 7], "韵位": [2, 3, 5, 6],
         "特征": "首句不起韵",
         "谱状态": "《钦定词谱》仅例句词平仄，未归纳可平可仄谱；本引擎不收谱、不校验",
         "依据": "《钦定词谱》卷四 浣溪沙「又一体」"},
        {"名": "孙光宪体", "字数": 44, "句式": [7, 7, 7, 7, 7, 3, 3, 3],
         "特征": "后结作三字三句", "谱状态": "未收谱、不校验",
         "依据": "《钦定词谱》卷四 浣溪沙「又一体」"},
        {"名": "李煜体（仄韵）", "字数": 42, "句式": [7, 7, 7, 7, 7, 7], "韵位": [1, 2, 3, 4, 5, 6],
         "特征": "全押仄韵", "谱状态": "未收谱、不校验（引擎尚无仄韵词牌谱）",
         "依据": "《钦定词谱》卷四 浣溪沙「又一体」"},
    ],
}

# ---------------------------------------------------------------- 词性小词典（仅对仗粗检）
# 来源：本项目手编，覆盖有限，未经权威词性标注集校验 —— 报告中已声明。

_POS_RAW = {
    "N": "山水风云烟雨霜雪天江楼舟帆雁鸿草木花叶林峰岭岸汀洲月日星灯窗门庭园亭台城墙郭路桥关塞沙尘波浪泉溪河海湖潭村寺钟砧笛箫酒诗书剑琴棋烛漏更春宵秋夜晓昏东西南北中上下声影色光明暗愁恨情思心梦魂客乡家国君王臣吏兵戈马弓刀旗鼓角烽戍闺阁帘屏罗袖钗环鬓眉眼泪衣裳襟袍笠蓑楫钓纶野世事生理名利害生涯尘土泥沙滩途程雁书音信",
    "V": "送照落飞来归望看听卧起行过入出动摇立倚凭掩锁湿染洗吹拂裁剪沾点缀横斜流去回映弄卷垂滴坠压拥断隔连迷催唤问寄忘却恨愁怜惜惊怯吟醉眠钓浣拍随尽胜酬饮待负逢遇涉渡济宿泊系惹抛掷题咏怀忆梦醒知觉",
    "A": "寒孤深长高低远近轻重空荒苍微茫萧疏残老枯瘦浓淡幽明清暗暖冷浅遥迢寥森凛沧莽皎皓碧翠绿黄白红青紫密平满斜乱碎闲静喧迟疾缓急新故旧陈半",
    "U": "之不与而无有在于是为以自相何谁且又还犹已但只休莫更欲应将共同独",
    "M": "一二三四五六七八九十百千万半双满尽几重数",
}
POS: dict = {}
for _cat, _chars in _POS_RAW.items():
    for _ch in _chars:
        POS.setdefault(_ch, set()).add(_cat)

# ---------------------------------------------------------------- 工具

PUNCT_RE = re.compile(r"[，。；：、！？,.;:!?\s“”‘’\"'《》〈〉—…·（）()]")


def split_lines(text: str) -> list:
    raw = re.split(r"[。！？\n；;，,、]", text)
    out = []
    for seg in raw:
        seg = PUNCT_RE.sub("", seg)
        seg = "".join(ch for ch in seg if is_han(ch))
        if seg:
            out.append(seg)
    return out


def tone_glyph(ch: str) -> str:
    st = LEX.tone_state(ch)
    if st == T_PING:
        return "○"
    if st == T_ZE:
        return "●"
    if st == T_BOTH:
        return "◐"
    return "?"


def depict(ch: str) -> str:
    rs = LEX.readings(ch)
    if not rs:
        return "韵书未收录"
    st = LEX.tone_state(ch)
    parts = [f"{r['g']}{r['y']}" for r in rs]
    if st == T_BOTH:
        return "平仄两收：" + "、".join(parts)
    return "、".join(parts)


def shown_pattern(pattern: str, char_len: int) -> str:
    """把正格中「一三五不论」的位置改写为「中」，使其与逐字结果对应。"""
    flex = FLEX_POS[char_len]
    return "".join("中" if i in flex else c for i, c in enumerate(pattern))


# 特拗（鲤鱼翻波）：五言「平平平仄仄」→「平平仄平仄」；七言「仄仄平平平仄仄」→「仄仄平平仄平仄」。
# 这是近体公认的合法变格，不作出律。v1 未实现，曾把苏轼「欲把西湖比西子」判为出律。
TEAO_POS = {"平平平仄仄": (2, 3), "仄仄平平平仄仄": (4, 5)}


def detect_teao(pattern: str, line: str, char_len: int):
    """
    返回 (状态, 说明)：
      True  —— 确认为特拗句（两个关键位读音已定且为「仄、平」）
      None  —— 疑似特拗，但关键位读音未定，无法确认
      False —— 不是特拗句
    """
    pos = TEAO_POS.get(pattern)
    if not pos or len(line) != char_len:
        return False, ""
    a, b = pos
    ta, tb = LEX.tone_state(line[a]), LEX.tone_state(line[b])
    if ta == T_ZE and tb == T_PING:
        return True, f"特拗（鲤鱼翻波）：第{a + 1}字用仄、第{b + 1}字用平，为近体允许之变格"
    if ta in (T_BOTH, T_MISSING) or tb in (T_BOTH, T_MISSING):
        return None, f"疑似特拗（第{a + 1}字应仄、第{b + 1}字应平），读音未定无法确认"
    return False, ""


def check_position(ch: str, expect: str, idx: int, char_len: int) -> dict:
    """单个位置的判定。expect ∈ {'平','仄','中'}。"""
    cell = {"第": idx + 1, "字": ch, "正格": expect, "实际": tone_glyph(ch),
            "韵书": depict(ch), "状态": None, "说明": ""}
    if expect == "中":
        cell["状态"] = FLEXIBLE
        cell["说明"] = STATUS_LABEL[FLEXIBLE]
        return cell
    if idx in FLEX_POS[char_len]:
        cell["状态"] = FLEXIBLE
        st = LEX.tone_state(ch)
        if st in (T_PING, T_ZE):
            cell["说明"] = f"不论位；与正格{'相同' if st == expect else '不同，允许'}"
        else:
            cell["说明"] = "不论位，不作平仄判定"
        return cell

    st = LEX.tone_state(ch)
    if st == T_MISSING:
        cell["状态"] = UNKNOWN
        cell["说明"] = "韵书未收录，无法判定平仄"
    elif st == T_BOTH:
        if LEX.is_lenient(ch):
            cell["状态"] = FLEXIBLE_READING
            cell["说明"] = POLICY_NOTE
        else:
            cell["状态"] = UNKNOWN
            cell["说明"] = "平仄两收且无据以定音的义项依据，按 UNKNOWN 处理"
    elif st == expect:
        cell["状态"] = PASS
        cell["说明"] = STATUS_LABEL[PASS]
    else:
        cell["状态"] = FAIL
        cell["说明"] = f"正格应{expect}声，实为{st}声"
    return cell


# ---------------------------------------------------------------- 诗：核心审查

def _build(key: tuple, lines: list, form_key: str) -> dict:
    char_len = key[0]
    seq, first_rhyme = TEMPLATES[key][form_key]
    patterns = [ALL_PATTERNS[s] for s in seq]

    table, errors, pending, warnings, notes = [], [], [], [], []
    tallies = {PASS: 0, FLEXIBLE: 0, FLEXIBLE_READING: 0, FAIL: 0, UNKNOWN: 0, NOT_CHECKED: 0}

    for i, (ln, pat) in enumerate(zip(lines, patterns)):
        cells = [check_position(ch, pat[j], j, char_len) for j, ch in enumerate(ln)]
        # 特拗（鲤鱼翻波）覆盖：合法变格不作出律
        teao, teao_note = detect_teao(pat, ln, char_len)
        shown = list(shown_pattern(pat, char_len))
        if teao is True:
            for j in TEAO_POS[pat]:
                cells[j]["状态"] = FLEXIBLE
                cells[j]["说明"] = teao_note
                shown[j] = "中"
        elif teao is None:
            for j in TEAO_POS[pat]:
                if cells[j]["状态"] == FAIL:
                    cells[j]["状态"] = UNKNOWN
                    cells[j]["说明"] = teao_note
        for c in cells:
            tallies[c["状态"]] += 1
        table.append({"句": i + 1, "文": ln, "正格": pat,
                      "示谱": "".join(shown), "格": cells})
        for c in cells:
            if c["状态"] == FAIL:
                errors.append(f"第{i + 1}句第{c['第']}字「{c['字']}」应为{c['正格']}声，"
                              f"实为{'平' if c['实际'] == '○' else '仄'}声（出律）")
            elif c["状态"] == UNKNOWN:
                pending.append(f"第{i + 1}句第{c['第']}字「{c['字']}」：{c['说明']}（{c['韵书']}）")

    # ---------- 押韵 ----------
    rhyme_idx = [i for i in range(len(lines)) if (i % 2 == 1 or (i == 0 and first_rhyme))]
    rhyme_info, rhyme_pending = [], []
    for i in rhyme_idx:
        ch = lines[i][-1]
        st = LEX.tone_state(ch)
        yuns = LEX.yuns(ch, {"上平", "下平"})
        rec = {"句": i + 1, "韵脚": ch, "平水韵部": sorted(yuns), "平仄状态": st, "韵书": depict(ch)}
        if st == T_MISSING:
            rec["状态"] = UNKNOWN
            rhyme_pending.append(f"第{i + 1}句韵脚「{ch}」未收录，无法判韵部")
        elif st == T_BOTH and not LEX.is_lenient(ch):
            rec["状态"] = UNKNOWN
            rhyme_pending.append(f"第{i + 1}句韵脚「{ch}」平仄两收，无法确定是否押平声韵")
        elif st == T_ZE:
            rec["状态"] = FAIL
            errors.append(f"第{i + 1}句韵脚「{ch}」为仄声，近体押韵句须用平声韵")
        else:
            rec["状态"] = PASS
        rhyme_info.append(rec)

    decided = [r for r in rhyme_info if r["平水韵部"]]
    if len(decided) >= 2:
        common = set.intersection(*[set(r["平水韵部"]) for r in decided])
        if not common:
            allg = sorted({g for r in decided for g in r["平水韵部"]})
            errors.append("韵脚不协：共出现 " + "、".join(allg) + " 等不同韵部，属「出韵（落韵）」")
            for r in rhyme_info:
                r["同部"] = False
        else:
            for r in rhyme_info:
                r["同部"] = bool(set(r["平水韵部"]) & common)
    else:
        for r in rhyme_info:
            r["同部"] = None

    # 白脚
    for i in [k for k in range(len(lines)) if k not in rhyme_idx]:
        ch = lines[i][-1]
        st = LEX.tone_state(ch)
        if st == T_MISSING:
            rhyme_pending.append(f"第{i + 1}句白脚「{ch}」未收录，无法判定是否仄收")
        elif st == T_BOTH and not LEX.is_lenient(ch):
            rhyme_pending.append(f"第{i + 1}句白脚「{ch}」平仄两收，未判定是否仄收")
        elif st == T_PING:
            errors.append(f"第{i + 1}句（白脚）「{ch}」为平声，近体非押韵句应以仄声收尾")

    # ---------- 粘对（据第 2 字实际平仄） ----------
    pair_pending = []

    def second_tone(i: int):
        ch = lines[i][1]
        st = LEX.tone_state(ch)
        return (st, ch) if st in (T_PING, T_ZE) else (None, ch)

    for k in range(0, len(lines) - 1, 2):
        ta, a = second_tone(k)
        tb, b = second_tone(k + 1)
        if ta is None or tb is None:
            pair_pending.append(f"第{k + 1}、{k + 2}句「{a}」「{b}」读音未定，未判失对")
        elif ta == tb:
            errors.append(f"第{k + 1}、{k + 2}句第二字「{a}」「{b}」平仄相同，失对")
    for k in range(1, len(lines) - 1, 2):
        ta, a = second_tone(k)
        tb, b = second_tone(k + 1)
        if ta is None or tb is None:
            pair_pending.append(f"第{k + 1}、{k + 2}句「{a}」「{b}」读音未定，未判失粘")
        elif ta != tb:
            errors.append(f"第{k + 1}、{k + 2}句第二字「{a}」「{b}」平仄相反，失粘")

    # ---------- 孤平 / 三平调 / 三仄尾 ----------
    # 孤平只施于「两平相连」型平收句：五言第 2、3 字为平平，七言第 3、4 字为平平。
    for i, pat in enumerate(patterns):
        if i in rhyme_idx:
            pair = (pat[1], pat[2]) if char_len == 5 else (pat[2], pat[3])
            if pair == ("平", "平"):
                pings, undet = [], []
                for c in lines[i][:-1]:
                    st = LEX.tone_state(c)
                    if st == T_PING:
                        pings.append(c)
                    elif st in (T_BOTH, T_MISSING):
                        undet.append(c)
                if undet and len(pings) <= 1:
                    pending.append(f"第{i + 1}句疑涉孤平，但「{''.join(undet)}」读音未定，未作判定")
                elif len(pings) <= 1:
                    errors.append(f"第{i + 1}句除韵脚外仅「{pings[0] if pings else '（无）'}」"
                                  f"一字为平声，犯「孤平」")

        ln = lines[i]
        tail_chars = ln[-3:]
        tail = [LEX.tone_state(c) for c in tail_chars]
        if i in rhyme_idx:
            if all(t == T_PING for t in tail):
                errors.append(f"第{i + 1}句句末「{tail_chars}」三字全平，犯「三平调」")
            elif not any(t == T_ZE for t in tail):
                # 末三字中没有确定的仄声，却有读音未定的字：无法排除三平调，不得判为通过
                pending.append(f"第{i + 1}句句末「{tail_chars}」是否三平调，因读音未定无法判定")
        elif all(t == T_ZE for t in tail):
            warnings.append(f"第{i + 1}句句末「{tail_chars}」三字全仄，属「三仄尾」（近体不忌，然宜避）")
        elif not any(t == T_PING for t in tail):
            pending.append(f"第{i + 1}句句末「{tail_chars}」是否三仄尾，因读音未定无法判定")

    # ---------- 重字 ----------
    flat = "".join(lines)
    rep: dict = {}
    for ch in flat:
        rep[ch] = rep.get(ch, 0) + 1
    dup = {c: n for c, n in rep.items() if n > 1}
    if dup:
        warnings.append("重字：" + "、".join(f"{c}×{n}" for c, n in dup.items()) + "（有意复沓可忽略）")

    unknown = sorted({ch for ch in flat if not LEX.has(ch)})
    if unknown:
        notes.append("韵书未收录（已按 UNKNOWN 处理，未计为通过）：" + "".join(unknown))

    return {"表": table, "错误": errors,
            "待确认": pending + rhyme_pending + pair_pending,
            "提示": warnings, "备注": notes, "押韵": rhyme_info, "韵位": rhyme_idx,
            "计数": tallies, "正格序列": patterns, "首句入韵": first_rhyme}


def check_poem(text: str, title: str = "", declared: str = "") -> dict:
    lines = split_lines(text)
    if not lines:
        raise SystemExit("未能解析出诗句")
    ns = {len(l) for l in lines}
    key = (ns.pop() if len(ns) == 1 else -1, len(lines))
    if key not in TEMPLATES:
        raise SystemExit(f"暂不支持的体式：{len(lines)} 句、每句字数 {sorted(ns)}")

    first = lines[0]
    notes: list = []

    # 句式判定：首句第二字定起式；首句是否入韵，按「与第 2 句韵脚是否同属一个平声韵部」判定
    # （用韵部而非声调，可避开「收」这类被韵表记为平仄两收、但韵部唯一的字）。
    st2 = LEX.tone_state(first[1])
    rises = {"平": ["平起"], "仄": ["仄起"], T_BOTH: ["平起", "仄起"], T_MISSING: ["平起", "仄起"]}[st2]

    yun1 = LEX.yuns(first[-1], {"上平", "下平"})
    yun2 = LEX.yuns(lines[1][-1], {"上平", "下平"}) if len(lines) > 1 else set()
    if yun1 and yun2:
        rhymed = [bool(yun1 & yun2)]
        rhyme_basis = f"首句末字「{first[-1]}」与第 2 句「{lines[1][-1]}」{'同' if rhymed[0] else '不同'}部"
    else:
        st_end = LEX.tone_state(first[-1])
        rhymed = {"平": [True], "仄": [False], T_BOTH: [True, False], T_MISSING: [True, False]}[st_end]
        rhyme_basis = f"首句末字「{first[-1]}」平仄未定，按声调推定"

    candidates = [f"{r}首句{'入韵' if y else '不入韵'}" for r in rises for y in rhymed]
    candidates = [c for c in candidates if c in TEMPLATES[key]] or list(TEMPLATES[key])
    results = {c: _build(key, lines, c) for c in candidates}

    if len(candidates) == 1:
        form_key = candidates[0]
        res = results[form_key]
        form_label = form_key
    else:
        form_key = min(candidates, key=lambda c: results[c]["计数"][FAIL])
        res = results[form_key]
        form_label = (f"待定（首句第二字「{first[1]}」{LEX.tone_state(first[1])}，"
                      f"并列候选：{'／'.join(candidates)}；取违律较少者「{form_key}」，此项需人工确认）")
        notes.append("句式判定依据不足：首句第二字读音未定，起式无法唯一确定；"
                     "下表按候选式之一计算，不代表唯一正解。")

    res.update({
        "标题": title, "诗体": FORM_NAME[key], "句式判定": form_label,
        "句式依据": rhyme_basis,
        "句式候选违律数": {c: results[c]["计数"][FAIL] for c in candidates},
        "原文": lines, "对仗": [], "备注": notes + res["备注"],
    })
    res["平仄表"] = res.pop("表")
    res["违律计数"] = res["计数"][FAIL]

    # 古体 / 仄韵体识别：近体必押平声韵。
    # 判据取「偶句韵脚」（第 2/4/6/8 句）——不依赖首句是否入韵，避免首句平收而被误判为近体。
    even_rhymes = [lines[i][-1] for i in range(1, len(lines), 2)]
    tones = [LEX.tone_state(ch) for ch in even_rhymes]
    if tones and all(t == T_ZE for t in tones):
        discarded = len(res["错误"]) + len(res["待确认"])
        for row in res["平仄表"]:
            for c in row["格"]:
                c["状态"] = NOT_CHECKED
                c["说明"] = "本诗非近体（仄韵），不套近体诗谱"
        res.update({
            "判定": "不适用",
            "结论": "不适用近体格律（韵脚全为仄声，当属古体或仄韵体）",
            "错误": [], "待确认": [], "对仗": [],
            "备注": res["备注"] + [
                f"近体绝句/律诗必押平声韵；本作韵脚全仄，按仄韵体处理，不作合律判定。"
                f"按近体谱强行计算原本会产出 {discarded} 处判定，已全部作废、不列示。",
            ],
        })
        return res

    if len(lines) == 8:
        res["对仗"] = [judge_duizhang(lines[2], lines[3], "颔联"),
                       judge_duizhang(lines[4], lines[5], "颈联")]

    n_fail, n_pending = len(res["错误"]), len(res["待确认"])
    if n_fail:
        res["判定"] = "违律"
        res["结论"] = f"不合近体格律（{n_fail} 处）"
        res["备注"] = res["备注"] + ["若此作为古体（不守近体平仄），本判定不适用。"]
    elif n_pending:
        res["判定"] = "待确认"
        res["结论"] = f"未见明确违律（{n_pending} 处读音待人工确认）"
    else:
        res["判定"] = "合格"
        res["结论"] = "合格"
    return res


def judge_duizhang(a: str, b: str, name: str) -> dict:
    """
    词性位置一致率。只统计词性类别是否重合，不判对仗工整与否。
    旧版把「结构相似度 100%」当作「对仗工整」，属表述错误（A06）。
    """
    if len(a) != len(b):
        return {"联": name, "结论": "字数不等，不成对", "词性位置一致率": None,
                "可比对字数": 0, "一致字数": 0, "未定字对": [], "细目": []}
    seg = [(0, 2), (2, 4), (4, len(a))] if len(a) == 7 else [(0, 2), (2, len(a))]
    total = matched = 0
    unknown, detail = [], []
    for s, e in seg:
        pair = []
        for x, y in zip(a[s:e], b[s:e]):
            px, py = POS.get(x, set()), POS.get(y, set())
            if not px or not py:
                unknown.append(x + y)
                pair.append((x, y, "?"))
                continue
            total += 1
            if px & py:
                matched += 1
                pair.append((x, y, "同类"))
            else:
                pair.append((x, y, "异类"))
        detail.append({"片段": a[s:e] + " / " + b[s:e], "逐字": pair})
    rate = round(matched / total * 100) if total else None
    return {
        "联": name, "词性位置一致率": rate, "可比对字数": total, "一致字数": matched,
        "未定字对": unknown, "细目": detail,
        "结论": "需人工复核（本引擎不判对仗工整）",
        "说明": "一致率仅表示对应位置词性类别重合的比例；词性同类不等于对仗成立，更不等于工整。"
                "本项不对仗打分。",
    }


# ---------------------------------------------------------------- 词：审查

def check_ci(text: str, cipai: str, title: str = "") -> dict:
    if cipai not in CI_PATTERNS:
        raise SystemExit(f"未收录词牌：{cipai}（当前支持 {'、'.join(CI_PATTERNS)}）")
    spec = CI_PATTERNS[cipai]
    lines = split_lines(text)
    errors, pending, notes = [], [], []
    if [len(l) for l in lines] != spec["句式"]:
        msg = f"句式不合：应为 {spec['句式']}，实为 {[len(l) for l in lines]}"
        return {"词牌": cipai, "标题": title, "原文": lines, "平仄": [], "押韵": [],
                "错误": [msg], "待确认": [], "提示": [], "备注": [],
                "判定": "违律", "结论": "不合词谱（句式不符，未逐字校验）",
                "未检查": "句式不符，全部位置未执行检查（NOT_CHECKED）",
                "说明": spec["说明"], "依据": spec["依据"], "词牌体": spec["体"]}

    table = []
    tallies = {PASS: 0, FLEXIBLE: 0, FLEXIBLE_READING: 0, FAIL: 0, UNKNOWN: 0, NOT_CHECKED: 0}
    for i, (ln, pat) in enumerate(zip(lines, spec["谱"])):
        cells = []
        for j, ch in enumerate(ln):
            exp = pat[j]
            if exp == "中":
                cells.append({"第": j + 1, "字": ch, "正格": "中", "实际": tone_glyph(ch),
                              "韵书": depict(ch), "状态": FLEXIBLE, "说明": STATUS_LABEL[FLEXIBLE]})
                continue
            st = LEX.tone_state(ch)
            cell = {"第": j + 1, "字": ch, "正格": exp, "实际": tone_glyph(ch),
                    "韵书": depict(ch), "状态": None, "说明": ""}
            if st == T_MISSING:
                cell["状态"], cell["说明"] = UNKNOWN, "韵书未收录，无法判定平仄"
            elif st == T_BOTH:
                if LEX.is_lenient(ch):
                    cell["状态"], cell["说明"] = FLEXIBLE_READING, POLICY_NOTE
                else:
                    cell["状态"], cell["说明"] = UNKNOWN, "平仄两收且无定音依据，按 UNKNOWN 处理"
            elif st == exp:
                cell["状态"], cell["说明"] = PASS, STATUS_LABEL[PASS]
            else:
                cell["状态"], cell["说明"] = FAIL, f"词谱应{exp}声，实为{st}声"
            cells.append(cell)
        for c in cells:
            tallies[c["状态"]] += 1
        table.append({"句": i + 1, "文": ln, "谱": pat, "格": cells})
        for c in cells:
            if c["状态"] == FAIL:
                errors.append(f"第{i + 1}句第{c['第']}字「{c['字']}」应为{c['正格']}声，"
                              f"实为{'平' if c['实际'] == '○' else '仄'}声")
            elif c["状态"] == UNKNOWN:
                pending.append(f"第{i + 1}句第{c['第']}字「{c['字']}」：{c['说明']}（{c['韵书']}）")

    info = []
    for i in spec["韵位"]:
        ch = lines[i - 1][-1]
        st = LEX.tone_state(ch)
        cy = LEX.cilin(ch, "平")
        rec = {"句": i, "韵脚": ch, "平仄状态": st, "词林正韵候选部": sorted(cy["bus"]),
               "半韵": cy["half"], "平水韵部": sorted(LEX.yuns(ch, {"上平", "下平"})), "韵书": depict(ch)}
        if st == T_MISSING:
            rec["状态"] = UNKNOWN
            pending.append(f"第{i}句韵脚「{ch}」未收录，无法判词韵")
        elif not cy["bus"]:
            rec["状态"] = UNKNOWN
            pending.append(f"第{i}句韵脚「{ch}」无平声读法，无法判词韵")
        elif cy["ambiguous"]:
            rec["状态"] = UNKNOWN
            pending.append(f"第{i}句韵脚「{ch}」属半韵（候选部 {sorted(cy['bus'])}），"
                           f"《词林正韵》按字分属两部，本项目缺字级依据，未作判定")
        elif st == T_ZE:
            rec["状态"] = FAIL
            errors.append(f"第{i}句韵脚「{ch}」为仄声，本调须押平声韵")
        else:
            rec["状态"] = PASS
        info.append(rec)

    decided = [r for r in info if r["状态"] == PASS and r["词林正韵候选部"]]
    if len(decided) >= 2:
        common = set.intersection(*[set(r["词林正韵候选部"]) for r in decided])
        if not common:
            errors.append("词韵不协：韵脚不在《词林正韵》同一部，属「出韵」")
            for r in info:
                r["同部"] = False
        else:
            for r in info:
                r["同部"] = bool(set(r["词林正韵候选部"]) & common) if r["词林正韵候选部"] else None

    if cipai == "浣溪沙" and LEX.tone_state(lines[0][-1]) == T_ZE:
        notes.append("首句末字为仄声，与正体「首句起韵」不合；可能属薛昭蕴体（首句不起韵）。"
                     "本引擎未收录其可平可仄谱，不做判定。")

    n_fail, n_pending = len(errors), len(pending)
    if n_fail:
        j, concl = "违律", f"不合词谱（{n_fail} 处）"
    elif n_pending:
        j, concl = "待确认", f"未见明确违律（{n_pending} 处读音待人工确认）"
    else:
        j, concl = "合格", "合格"

    return {
        "词牌": cipai, "标题": title, "原文": lines, "平仄": table,
        "押韵": info, "错误": errors, "待确认": pending, "提示": [], "备注": notes,
        "判定": j, "结论": concl, "说明": spec["说明"], "依据": spec["依据"],
        "词牌体": spec["体"], "计数": tallies,
    }


# ---------------------------------------------------------------- 输出

LEGEND = ("图例：○平 ●仄 ◐两读 ?未收录　｜　✓通过 ~可平可仄 ≈又音放宽 ✗违律 ?待确认 －未检查")


def render(result: dict) -> str:
    if "词牌" in result:
        out = [f"【{result['词牌']}】{result.get('标题', '')}　（{result.get('词牌体', '')}）", ""]
        out.append(f"  依据：{result.get('依据', '—')}")
        out.append("")
        out.append("  句  词谱            填词            逐字      判定")
        for row in result.get("平仄", []):
            marks = "".join(c["实际"] for c in row["格"])
            flags = "".join(STATUS_GLYPH[c["状态"]] for c in row["格"])
            out.append(f"  {row['句']:>2}  {row['谱']}  {row['文']}  {marks}  {flags}")
        out.append("")
        out.append("  押韵：")
        for r in result.get("押韵", []):
            mark = {PASS: "✓", FAIL: "✗", UNKNOWN: "?"}.get(r["状态"], "-")
            bu = "、".join(f"第{b}部" for b in r["词林正韵候选部"]) or "—"
            out.append(f"    {mark} 第{r['句']}句「{r['韵脚']}」→ {bu}")
        if result.get("错误"):
            out.append("")
            out.append("  ✗ 词谱问题：")
            for e in result["错误"]:
                out.append(f"    - {e}")
        if result.get("待确认"):
            out.append("")
            out.append("  ? 待人工确认：")
            for p in result["待确认"]:
                out.append(f"    - {p}")
        for n in result.get("备注", []):
            out.append(f"  · {n}")
        out.append("")
        out.append(f"  结论：{result['结论']}")
        out.append(f"  {LEGEND}")
        return "\n".join(out)

    out = [f"【{result['诗体']}】{result.get('标题', '')}　句式：{result['句式判定']}", ""]
    if result.get("句式依据"):
        out.append(f"  句式依据：{result['句式依据']}")
    out.append(f"  {LEGEND}")
    out.append("")
    out.append("  句  示谱          诗句            逐字      判定")
    for row in result["平仄表"]:
        marks = "".join(c["实际"] for c in row["格"])
        flags = "".join(STATUS_GLYPH[c["状态"]] for c in row["格"])
        out.append(f"  {row['句']:>2}  {row['示谱']}  {row['文']}  {marks}  {flags}")
    out.append("")
    out.append("  押韵：")
    for r in result["押韵"]:
        mark = {PASS: "✓", FAIL: "✗", UNKNOWN: "?"}.get(r.get("状态"), "-")
        out.append(f"    {mark} 第{r['句']}句「{r['韵脚']}」→ {'、'.join(r['平水韵部']) or '—'}")
    if result["对仗"]:
        out.append("")
        out.append("  对仗（词性位置一致率，非工拙评判）：")
        for d in result["对仗"]:
            rate = d["词性位置一致率"]
            out.append(f"    {d['联']}：{rate if rate is not None else '—'}%"
                       f"（{d['一致字数']}/{d['可比对字数']} 字可比对）｜{d['结论']}")
            if d["未定字对"]:
                out.append(f"      词性未定字对：{'、'.join(d['未定字对'])}")
    out.append("")
    if result["错误"]:
        out.append("  ✗ 格律错误：")
        for e in result["错误"]:
            out.append(f"    - {e}")
    else:
        out.append("  ✓ 未发现明确违律")
    if result["待确认"]:
        out.append("")
        out.append("  ? 待人工确认（未计为通过，也未计为违律）：")
        for p in result["待确认"]:
            out.append(f"    - {p}")
    for w in result["提示"]:
        out.append(f"  ! {w}")
    for n in result["备注"]:
        out.append(f"  · {n}")
    out.append("")
    out.append(f"  结论：{result['结论']}")
    return "\n".join(out)


def is_ok(result: dict) -> bool:
    """无明确违律即为可接受（待确认会在输出中标明，不等于通过）。"""
    return result.get("判定") in ("合格", "待确认", "不适用")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="诗词格律审查引擎 v2")
    ap.add_argument("--text", help="诗句全文")
    ap.add_argument("--file", help="从文件读取")
    ap.add_argument("--title", default="", help="标题")
    ap.add_argument("--ci", help="词全文")
    ap.add_argument("--cipai", default="浣溪沙", help="词牌")
    ap.add_argument("--json", help="另存 JSON 结果")
    a = ap.parse_args(argv)

    if a.ci:
        res = check_ci(a.ci, a.cipai, a.title)
    else:
        text = a.text or (open(a.file, encoding="utf-8").read() if a.file else "")
        if not text:
            ap.print_help()
            return 1
        res = check_poem(text, a.title)

    print(render(res))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
    return 0 if is_ok(res) else 2


if __name__ == "__main__":
    sys.exit(main())
