#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yunshu.py —— 音韵判定层（韵书查询 + 平仄状态判定 + 词林正韵查部）

设计原则（对应 POETRY-AUDIT-2026-11-11-R1 / A03、A07）：

  1. 查得到就是查得到，查不到就说查不到。
     一个字如果平仄两收，本层不替它选音，只如实返回「两读」；
     谁来定音，由上层按证据决定，绝不按格律反推。

  2. 唯一允许放宽的，是一份显式白名单 POLICY_LENIENT。
     白名单里的字在《平水韵》中平仄两收、且诗家历来混用，
     本引擎按「又音可通」处理，但状态记为 FLEXIBLE_READING，
     不计为 PASS，并在输出中标注，供人工复核。
     该白名单是工程政策，不是考据结论——报告第七章已列为待审事项。

  3. 半韵（十灰/九佳/十三元 等）在《词林正韵》中按字分属两部，
     本项目没有字级依据，因此返回两个候选部，状态 UNKNOWN，不做猜测。
"""

from __future__ import annotations

import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(BASE, "诗歌知识库", "04_韵书", "平水韵_索引.json")

GROUP_TONE = {"上平": "平", "下平": "平", "上": "仄", "去": "仄", "入": "仄"}

# 状态常量
T_PING, T_ZE, T_BOTH, T_MISSING = "平", "仄", "两读", "未收录"

# ---------------------------------------------------------------- 放宽白名单
#
# 收录条件（三条同时满足）：
#   a. 《平水韵》中平声韵与仄声韵两收；
#   b. 平仄两读在诗律工具书中历来被视为「又音」，非严格义项对立；
#   c. 高频，且若一律判 UNKNOWN 会使绝大多数唐宋名篇无法判定。
#
# 本表是政策而非考据：未逐字给出《广韵》反切与义训对勘，
# 属 ROUND 1 已知缺口，已在报告 04_多音字机制审计.md 与 10_完整报告 第七章列明。
POLICY_LENIENT = frozenset("望看听忘凭漫叹教令醒过")

POLICY_NOTE = (
    "该字平仄两收，按「又音可通」放宽：可依格律取音，但状态记 FLEXIBLE_READING，"
    "不计为 PASS；本引擎未做义项核验，属工程政策。"
)


def is_han(ch: str) -> bool:
    o = ord(ch)
    return (0x3400 <= o <= 0x4DBF) or (0x4E00 <= o <= 0x9FFF) or (0x20000 <= o <= 0x2FFFF)


class Lexicon:
    def __init__(self, path: str = INDEX):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.meta: dict = data["meta"]
        self.chars: dict = data["chars"]

    # ---------- 基础查询 ----------
    def has(self, ch: str) -> bool:
        return ch in self.chars

    def readings(self, ch: str) -> list:
        item = self.chars.get(ch)
        return list(item["r"]) if item else []

    def trad_of(self, ch: str) -> list:
        item = self.chars.get(ch)
        return list(item["trad"]) if item else []

    def tones(self, ch: str) -> frozenset:
        rs = self.readings(ch)
        if not rs:
            return frozenset()
        return frozenset(GROUP_TONE[r["g"]] for r in rs)

    def yuns(self, ch: str, classes=None) -> set:
        """返回韵目名集合；classes 可限定 {"平"} / {"上","去","入"} 等。"""
        out = set()
        for r in self.readings(ch):
            if classes and r["g"] not in classes:
                continue
            out.add(r["y"])
        return out

    def classes_of(self, ch: str) -> set:
        return {r["g"] for r in self.readings(ch)}

    # ---------- 平仄状态 ----------
    def tone_state(self, ch: str) -> str:
        """返回 '平' / '仄' / '两读' / '未收录'。不做任何语境推断。"""
        ts = self.tones(ch)
        if not ts:
            return T_MISSING
        if len(ts) == 2:
            return T_BOTH
        return next(iter(ts))

    def is_lenient(self, ch: str) -> bool:
        return ch in POLICY_LENIENT

    def candidate_tones(self, ch: str) -> list:
        """供报告使用：列出该字全部可读声调及所据韵目。"""
        out = []
        for r in self.readings(ch):
            out.append({"声部": r["g"], "韵目": r["y"], "平仄": GROUP_TONE[r["g"]]})
        return out

    # ---------- 词林正韵 ----------
    def cilin(self, ch: str, tone_class: str) -> dict:
        """
        tone_class: '平' 或 '仄'（仄 = 上/去/入）。
        返回 {"bus": set, "ambiguous": bool, "half": bool, "reasons": list}
        """
        import cilin as _cilin  # 同目录模块

        classes = {"平": ("上平", "下平"), "仄": ("上", "去", "入")}[tone_class]
        bus, half, reasons = set(), False, []
        for r in self.readings(ch):
            if r["g"] not in classes:
                continue
            cand = _cilin.bu_of(r["g"], r["y"])
            if not cand:
                reasons.append(f"{r['g']}{r['y']} 未映射")
                continue
            if len(cand) > 1:
                half = True
                reasons.append(f"{r['g']}{r['y']} 属半韵，候选部 {list(cand)}")
            bus |= set(cand)
        return {"bus": bus, "ambiguous": half or len(bus) > 1, "half": half, "reasons": reasons}


LEX = Lexicon()
