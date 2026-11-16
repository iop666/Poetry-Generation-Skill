#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 工作包 D1/D2：《詞林正韻》《中原音韻》字級資料重建。

兩個來源都是維基文庫轉錄（有 revid 與 wikitext SHA-256）：
  詞林正韻            19 部，每部下列韻目【一東】…，字表以字串給出，含「半」韻標記
  中原音韻（四庫全書本）卷上＋卷下，每部列 平聲(隂/陽)/上聲/去聲/入聲作X聲，
                       同音組以全角空格分隔

輸出 raw/r2_09/rhyme/*.jsonl（逐字記錄，含 source/revid/section/字位序），
以及 *_stats.json。不改既有表。
"""
import os
import re
import json
import hashlib
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "raw", "r2_09", "rhyme")

CL19 = ["第一部", "第二部", "第三部", "第四部", "第五部", "第六部", "第七部", "第八部",
        "第九部", "第十部", "第十一部", "第十二部", "第十三部", "第十四部", "第十五部",
        "第十六部", "第十七部", "第十八部", "第十九部"]

YY19 = ["東鐘", "江陽", "支思", "齊微", "魚模", "皆來", "真文", "寒山", "桓歡", "先天",
        "蕭豪", "歌戈", "家麻", "車遮", "庚青", "尤侯", "侵尋", "監咸", "廉纖"]

# ---------------- 詞林正韻 ----------------
d = json.load(open(os.path.join(SRC, "詞林正韻.json"), encoding="utf-8"))
w = d["wikitext"]
revid = d["revid"]

# 以 ==第N部== 切大塊
parts = re.split(r"\n==\s*(第[一二三四五六七八九十]+部)\s*==\n", w)
cl_rows = []
cl_meta = []
for i in range(1, len(parts), 2):
    bu = parts[i]
    body = parts[i + 1]
    # 以 ===…=== 切聲調段，如「平聲：一東二冬通用」
    secs = re.split(r"\n===\s*([^=]+?)\s*===\n", body)
    for j in range(1, len(secs), 2):
        head = secs[j].strip()
        txt = secs[j + 1]
        tone = "平" if "平" in head else ("入" if "入" in head else ("上" if "上" in head else "去"))
        # 韻目：一東二冬通用 → 標出各韻目與半韻
        yunmu_raw = head.split("：")[-1] if "：" in head else head
        halves = {m.group(1) for m in re.finditer(r"([^\s　<>＜＞])(?=<半>)", yunmu_raw)}
        # 【一東】字字字
        for m in re.finditer(r"【([^】]{1,8})】([^\n【]*)", txt):
            ym = m.group(1)
            ym_half = 1 if "<半>" in ym else 0
            ym_name = re.sub(r"^[一二三四五六七八九十百]+", "", re.sub(r"<半>", "", ym))
            chars_raw = m.group(2)
            # 去（注）
            chars_raw = re.sub(r"[（(][^）)]*[）)]", "", chars_raw)
            chars_raw = re.sub(r"\[[^\]]*\]", "", chars_raw)
            for k, ch in enumerate(chars_raw):
                if not ("\u4e00" <= ch <= "\u9fff"):
                    continue
                cl_rows.append({
                    "system": "ci_rhyme", "bu": bu, "tone": tone,
                    "yunmu": ym, "yunmu_name": ym_name,
                    "is_half": 1 if (ym_half or ym_name in halves) else 0,
                    "char": ch, "pos_in_group": k,
                    "page_title": "詞林正韻", "revid": revid,
                })
    cl_meta.append({"bu": bu, "n_sections": (len(secs) - 1) // 2})

# ---------------- 中原音韻（以「中原音韻/正文」為主，四庫本卷上為校本） ----------------
yy_rows = []
yy_meta = []
SRC_MAIN = os.path.join(SRC, "中原音韻_正文.json")
dd = json.load(open(SRC_MAIN, encoding="utf-8"))
t = dd["text"]
rv = dd["revid"]
lines = [re.sub(r"\u200b", "", x).strip() for x in t.split("\n")]
cur_bu = cur_tone = cur_yy = None
BU = set(YY19) | {"東鍾"}
for s0 in lines:
    s = s0.strip()
    if not s or s in ("[编辑]",):
        continue
    if s in BU:
        cur_bu, cur_tone, cur_yy = s, None, None
        yy_meta.append({"bu": s})
        continue
    m = re.match(r"^【(平聲|上聲|去聲|入聲作[平上去]聲)】$", s)
    if m:
        cur_tone, cur_yy = m.group(1), None
        continue
    if s in ("陰平", "陽平", "陰", "陽"):
        cur_yy = "陰" if s.startswith("陰") else "陽"
        continue
    if cur_bu is None or cur_tone is None:
        continue
    grp = re.sub(r"[（(][^）)]*[）)]", "", s)
    grp = re.sub(r"\[[^\]]*\]", "", grp)
    if not re.search(r"[\u4e00-\u9fff]", grp):
        continue
    for k, ch in enumerate(grp):
        if "\u4e00" <= ch <= "\u9fff":
            yy_rows.append({"system": "yuan_qu", "bu": cur_bu, "tone_raw": cur_tone,
                            "yinyang": cur_yy, "char": ch, "pos_in_group": k,
                            "page_title": "中原音韻/正文（維基文庫）", "revid": rv})

# 四庫本卷上作校本：只統計部名與字數，用於版本對照
cross = {}
fq = os.path.join(SRC, "中原音韻_(四庫全書本)_卷上.json")
if os.path.exists(fq):
    dq = json.load(open(fq, encoding="utf-8"))
    for k in YY19 + ["東鍾"]:
        cross[k] = dq["text"].count(k)

with open(os.path.join(SRC, "cilin_zhengyun_chars.jsonl"), "w", encoding="utf-8") as f:
    for r in cl_rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
with open(os.path.join(SRC, "zhongyuan_yinyun_chars.jsonl"), "w", encoding="utf-8") as f:
    for r in yy_rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

cl_stats = {
    "n_rows": len(cl_rows),
    "n_distinct_char": len({r["char"] for r in cl_rows}),
    "per_bu": dict(collections.Counter(r["bu"] for r in cl_rows)),
    "per_tone": dict(collections.Counter(r["tone"] for r in cl_rows)),
    "n_half_rows": sum(1 for r in cl_rows if r["is_half"]),
    "half_yunmu": sorted({r["yunmu_name"] for r in cl_rows if r["is_half"]}),
    "n_yunmu": len({r["yunmu"] for r in cl_rows}),
    "revid": revid,
}
yy_stats = {
    "n_rows": len(yy_rows),
    "n_distinct_char": len({r["char"] for r in yy_rows}),
    "per_bu": dict(collections.Counter(r["bu"] for r in yy_rows)),
    "per_tone": dict(collections.Counter(r["tone_raw"] for r in yy_rows)),
    "per_yinyang": dict(collections.Counter(r["yinyang"] for r in yy_rows if r["tone_raw"] == "平聲")),
    "n_bu": len({r["bu"] for r in yy_rows}),
}
json.dump(cl_stats, open(os.path.join(SRC, "cilin_stats.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(yy_stats, open(os.path.join(SRC, "zhongyuan_stats.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("詞林正韻 rows", cl_stats["n_rows"], "distinct", cl_stats["n_distinct_char"],
      "half", cl_stats["n_half_rows"], "yunmu", cl_stats["n_yunmu"])
print("  per_bu", {k: v for k, v in list(cl_stats["per_bu"].items())[:5]})
print("  half_yunmu", cl_stats["half_yunmu"])
print("中原音韻 rows", yy_stats["n_rows"], "distinct", yy_stats["n_distinct_char"],
      "bu", yy_stats["n_bu"])
print("  per_tone", yy_stats["per_tone"])
print("  yinyang", yy_stats["per_yinyang"])
print("  per_bu", {k: v for k, v in list(yy_stats["per_bu"].items())})
