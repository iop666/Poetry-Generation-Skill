#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_lexicon.py —— 《平水韵》繁体检字表 → 带溯源的双向索引（v2）

相对 v1 的改动（对应 POETRY-AUDIT-2026-11-11-R1 / A07）：
  1. 保留每个简体字对应的繁体字形（trad），可回溯，不再丢失繁简映射；
  2. 保留声调分组（上平/下平/上/去/入），入声可单独取出，供词林正韵使用；
  3. 清洗源文件中的非汉字污染（入聲十七洽 尾部残留 "PublicdomainPublicdomainfalsefalse"）；
  4. 韵内重复字去重并计数，不再静默吞掉；
  5. 汉字范围扩到 CJK 扩展 A/B 区，不再把扩展区字静默丢弃；
  6. 全部统计口径写入 meta，任何数字都可复算。

输入：诗歌知识库/04_韵书/平水韵_全表_繁体.json
输出：诗歌知识库/04_韵书/平水韵_索引.json
     诗歌知识库/04_韵书/平水韵_数据审计.json
"""

from __future__ import annotations

import collections
import datetime
import hashlib
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YUN = os.path.join(BASE, "诗歌知识库", "04_韵书")
SRC = os.path.join(YUN, "平水韵_全表_繁体.json")
DST = os.path.join(YUN, "平水韵_索引.json")
AUDIT = os.path.join(YUN, "平水韵_数据审计.json")

GROUP_KEY = {"上平聲部": "上平", "下平聲部": "下平", "上聲部": "上", "去聲部": "去", "入聲部": "入"}
GROUP_TO_TONE = {"上平": "平", "下平": "平", "上": "仄", "去": "仄", "入": "仄"}


def is_han(ch: str) -> bool:
    o = ord(ch)
    return (0x3400 <= o <= 0x4DBF) or (0x4E00 <= o <= 0x9FFF) or (0x20000 <= o <= 0x2FFFF)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def strip_tone_prefix(name: str) -> str:
    for p in ("上平聲", "下平聲", "上聲", "去聲", "入聲"):
        if name.startswith(p):
            return name[len(p):]
    return name


# 韵目异名归一：源表用字与通行词韵表不一致者，统一到通行写法
YUN_ALIAS = {
    "二十八琰": "二十八俭",
    "二十八儉": "二十八俭",
    "二十一箇": "二十一个",
    "二十九豔": "二十九艳",
    "二十九艷": "二十九艳",
    "十七筿": "十七筱",
}


def main() -> int:
    try:
        from opencc import OpenCC
        cc = OpenCC("t2s")
        to_simp = cc.convert
        conv_mode = "opencc t2s（opencc-python-reimplemented）"
    except Exception:
        to_simp = lambda s: s  # noqa: E731
        conv_mode = "未安装 opencc，未做繁简转换"

    raw = json.load(open(SRC, encoding="utf-8"))

    # ---------- 逐韵清洗 ----------
    per_rhyme = []          # (group, 韵名, 原始串, 清洗串)
    removed_nonhan = []
    removed_dup = []
    for _tone_key, subs in raw.items():
        for sub, yuns in subs.items():
            g = GROUP_KEY[sub]
            for yun_name, payload in yuns.items():
                blob = "".join(payload)
                s = to_simp(strip_tone_prefix(yun_name))
                name = YUN_ALIAS.get(s, s)
                kept, seen = [], set()
                for ch in blob:
                    if not is_han(ch):
                        removed_nonhan.append({"韵": name, "字": ch})
                        continue
                    if ch in seen:
                        removed_dup.append({"韵": name, "字": ch})
                        continue
                    seen.add(ch)
                    kept.append(ch)
                per_rhyme.append((g, name, blob, "".join(kept)))

    # ---------- 繁 → 简 归并 ----------
    chars: dict = {}
    simp_src: dict = collections.defaultdict(set)
    for g, name, _blob, clean in per_rhyme:
        for trad in clean:
            simp = to_simp(trad)
            simp_src[simp].add(trad)
            item = chars.setdefault(simp, {"trad": set(), "r": []})
            item["trad"].add(trad)
            rec = {"g": g, "y": name}
            if rec not in item["r"]:
                item["r"].append(rec)

    # ---------- 统计口径 ----------
    trad_all = {t for _g, _n, _b, c in per_rhyme for t in c}
    tones_of = lambda recs: {GROUP_TO_TONE[r["g"]] for r in recs}  # noqa: E731
    dup_tone = sorted([c for c, v in chars.items() if len(tones_of(v["r"])) > 1])
    merged = sorted([c for c, v in simp_src.items() if len(v) > 1])
    merged_conflict = sorted([c for c in merged if len(tones_of(chars[c]["r"])) > 1])
    tone_count = collections.Counter(
        "平" if GROUP_TO_TONE[r["g"]] == "平" else "仄" for v in chars.values() for r in v["r"]
    )
    by_group = collections.Counter()
    for _g, _n, _b, _c in per_rhyme:
        by_group[_g] += len(_c)

    stats = {
        "韵目数": len(per_rhyme),
        "源文件字头条目数_含跨韵重复含污染": sum(len(b) for _g, _n, b, _c in per_rhyme),
        "非汉字污染条目": len(removed_nonhan),
        "韵内重复条目": len(removed_dup),
        "清洗后有效字头条目": sum(len(c) for _g, _n, _b, c in per_rhyme),
        "唯一繁体字数": len(trad_all),
        "唯一简体字数": len(chars),
        "跨韵多读繁体字数": sum(1 for t in trad_all if sum(1 for _g, _n, _b, c in per_rhyme if t in c) > 1),
        "平仄兼收字数": len(dup_tone),
        "繁体归并字数": len(merged),
        "繁体归并后平仄冲突字数": len(merged_conflict),
        "各声调字头条目数": dict(tone_count),
        "按声部分组条目数": dict(by_group),
    }

    audit = {
        "生成时间": datetime.datetime.now().isoformat(timespec="seconds"),
        "源文件": os.path.relpath(SRC, BASE),
        "源文件sha256": sha256(SRC),
        "繁简转换": conv_mode,
        "统计口径说明": {
            "唯一简体字数": "把繁体逐字转简后去重得到的字数；同一简体可能来自多个繁体。",
            "跨韵多读繁体字数": "同一繁体字出现在两个及以上韵目中的字数。",
            "平仄兼收字数": "简体字同时具有平声读法与仄声读法的字数，旧引擎对其一律放行。",
            "繁体归并后平仄冲突字数": "因繁简转写把不同繁体并成同一简体、从而出现平仄兼收的字数，属转写副产物，需人工确认。",
        },
        "统计": stats,
        "非汉字污染明细": removed_nonhan,
        "韵内重复明细": removed_dup,
        "繁简归并明细": [{"简体": c, "繁体": sorted(simp_src[c]), "声调": sorted(tones_of(chars[c]["r"])),
                           "平水韵部": [f"{r['g']}{r['y']}" for r in chars[c]["r"]]} for c in merged],
    }

    # ---------- 落盘 ----------
    out_chars = {}
    for c, v in sorted(chars.items()):
        out_chars[c] = {"trad": sorted(v["trad"]),
                        "r": sorted(v["r"], key=lambda x: (x["g"], x["y"]))}
    index = {
        "meta": {
            "生成脚本": "tools/build_lexicon.py",
            "源文件": os.path.relpath(SRC, BASE),
            "源文件sha256": sha256(SRC),
            "原索引字头数_v1": 8116,
            "本索引字头数": len(out_chars),
            "韵目数": len(per_rhyme),
            "声调取值": "g ∈ {上平,下平,上,去,入}；上平/下平为平声，上/去/入为仄声",
            "说明": "「r」为读音记录，每条含声部 g 与平水韵目 y；「trad」为该简体对应的繁体字形，用于回溯。",
        },
        "chars": out_chars,
    }
    with open(DST, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))
    with open(AUDIT, "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)

    print(f"源文件条目 {stats['源文件字头条目数_含跨韵重复含污染']}")
    print(f"清洗后条目 {stats['清洗后有效字头条目']}（删非汉字 {stats['非汉字污染条目']}，删韵内重复 {stats['韵内重复条目']}）")
    print(f"唯一繁体 {stats['唯一繁体字数']} → 唯一简体 {stats['唯一简体字数']}")
    print(f"平仄兼收 {stats['平仄兼收字数']} 字；繁简归并 {stats['繁体归并字数']} 字，其中平仄冲突 {stats['繁体归并后平仄冲突字数']} 字")
    print(f"[写入] {os.path.relpath(DST, BASE)}")
    print(f"[写入] {os.path.relpath(AUDIT, BASE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
