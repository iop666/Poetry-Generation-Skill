#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_cilin.py —— 由 engine/cilin.py 的表生成《词林正韵》十九部数据文件与人读对照表。

单一事实来源是 engine/cilin.py（供引擎查表），本脚本把同一张表导出为
  诗歌知识库/04_韵书/词林正韵_十九部.json    机读
  诗歌知识库/04_韵书/词林正韵_十九部.md      人读
避免「代码里一份、文档里另一份」的漂移。
"""

from __future__ import annotations

import collections
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(BASE, "engine"))

import cilin  # noqa: E402

YUN = os.path.join(BASE, "诗歌知识库", "04_韵书")


def main() -> int:
    problems = cilin.validate()
    if problems:
        print("十九部表自检未通过：", problems)
        return 1

    bus = collections.defaultdict(lambda: {"平": [], "上": [], "去": [], "入": []})
    for cls, table in cilin.CILIN.items():
        for yun, cand in table.items():
            for b in cand:
                bus[b][cls].append(yun)
    for b in bus:
        for cls in bus[b]:
            bus[b][cls].sort()

    data = {
        "生成时间": datetime.datetime.now().isoformat(timespec="seconds"),
        "生成脚本": "tools/build_cilin.py（表源：engine/cilin.py）",
        "依据": [
            "戈载《词林正韵》十九部：平、上、去十四部 + 入声五部",
            "韵目对照采用搜韵网《词林正韵·总目》所载「以平水韵目对应」通行表",
            "《四库全书》本《词林正韵》序（总目分部），韵目原依《集韵》，已折算为平水韵 106 韵",
        ],
        "收字规模": "《词林正韵》原书一万二千九百九十九字（据其自序）；本项目未收字表，只收部目对照",
        "覆盖": "平 30 韵、上 29 韵、去 30 韵、入 17 韵，合计 106 韵，与平水韵韵目数一致",
        "半韵": {
            "韵目": sorted(cilin.HALF_RHYMES),
            "处理": "同一韵目被两部共分，字级归属缺依据；引擎对落在半韵中的字返回两个候选部、"
                    "状态记 UNKNOWN，不做猜测。",
        },
        "十九部": {f"第{b}部": {"说明": cilin.BU_SIZE_NOTE[b], **bus[b]} for b in range(1, 20)},
        "未实现": [
            "仄韵词牌谱（如蝶恋花、醉花阴）未收，故目前只能校验平韵词牌；仄韵部数据已备。",
            "上去通押未做专门判定（现按同部即通押处理，未区分上声与去声的细分规则）。",
        ],
    }
    with open(os.path.join(YUN, "词林正韵_十九部.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    md = ["# 词林正韵 · 十九部", "",
          "> 本文件由 `tools/build_cilin.py` 从 `engine/cilin.py` 导出，请勿手改。",
          "> 依据：戈载《词林正韵》；韵目对照采用搜韵网《词林正韵·总目》通行表，已折算为平水韵 106 韵。", "",
          "## 一、为何是十九部", "",
          "词韵比诗韵宽：平水韵 30 个平声韵在词里合并为 14 部；入声独立为 5 部，共 19 部。"
          "填词押韵以「部」为单位，同部可通押，跨部即出韵。", "",
          "## 二、十九部对照表", "",
          "| 部 | 平声 | 上声 | 去声 | 入声 |", "|---|---|---|---|---|"]
    for b in range(1, 20):
        r = bus[b]
        cell = lambda xs: "、".join(xs) if xs else "—"  # noqa: E731
        md.append(f"| 第{b}部 | {cell(r['平'])} | {cell(r['上'])} | {cell(r['去'])} | {cell(r['入'])} |")
    md += ["", "## 三、半韵：本项目无法判定的一类", "",
           f"被两部共分的韵目共 {len(cilin.HALF_RHYMES)} 个：{'、'.join(sorted(cilin.HALF_RHYMES))}。", "",
           "《词林正韵》是按**字**分配半韵归属的（如「回」入第三部、「来」入第五部），"
           "而本项目只有平水韵一级数据，没有字级依据。因此引擎对这些字返回两个候选部、"
           "状态记 `UNKNOWN`，并在输出中说明「属半韵、未作判定」。", "",
           "这不是可以含糊过去的小问题：十灰是高频韵，涉及「回、来、台、杯、梅、开」等常用字。"
           "补全需引入《词林正韵》字表并逐字对勘，列入后续轮次。", "",
           "## 四、当前能力边界", "",
           "1. 平韵词牌可校验（浣溪沙、忆江南、相见欢上片等）。",
           "2. 仄韵部数据已备，但**仄韵词牌的词谱未收录**，故仄韵词牌尚不能校验。",
           "3. 上去通押未细分，同部即视为可通押。", ""]
    with open(os.path.join(YUN, "词林正韵_十九部.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"十九部自检：{'通过' if not problems else problems}")
    print(f"[写入] 诗歌知识库/04_韵书/词林正韵_十九部.json / .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
