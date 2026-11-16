#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
capture_probe.py —— 用「权威名篇」探测引擎行为，生成前后对照证据。

只依赖 check_poem / check_ci 两个入口，因此修复前后的引擎都能跑，
用于 ROUND 1 的 before/after 对照（证据而非结论）。

用法：
  python3 tools/capture_probe.py --out reports/round-1-audit/logs/baseline/probe_before.txt
"""

import argparse
import io
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "engine"))

from gedou import check_poem, check_ci, render  # noqa: E402

# 权威底本：诗句按通行本录入；韵部依《平水韵》，句式依近体定格。
POEMS = [
    ("P01", "登鹳雀楼", "王之涣", "五绝", "下平十一尤",
     "白日依山尽，黄河入海流。欲穷千里目，更上一层楼。"),
    ("P02", "山居秋暝", "王维", "五律", "下平十一尤",
     "空山新雨后，天气晚来秋。明月松间照，清泉石上流。"
     "竹喧归浣女，莲动下渔舟。随意春芳歇，王孙自可留。"),
    ("P03", "登高", "杜甫", "七律", "上平十灰",
     "风急天高猿啸哀，渚清沙白鸟飞回。无边落木萧萧下，不尽长江滚滚来。"
     "万里悲秋常作客，百年多病独登台。艰难苦恨繁霜鬓，潦倒新停浊酒杯。"),
    ("P04", "山行", "杜牧", "七绝", "下平六麻",
     "远上寒山石径斜，白云生处有人家。停车坐爱枫林晚，霜叶红于二月花。"),
    ("P05", "春望", "杜甫", "五律", "下平十二侵",
     "国破山河在，城春草木深。感时花溅泪，恨别鸟惊心。"
     "烽火连三月，家书抵万金。白头搔更短，浑欲不胜簪。"),
    ("P06", "早发白帝城", "李白", "七绝", "上平十五删",
     "朝辞白帝彩云间，千里江陵一日还。两岸猿声啼不住，轻舟已过万重山。"),
    ("P07", "春晓", "孟浩然", "古绝", "上声十七筱（仄韵）",
     "春眠不觉晓，处处闻啼鸟。夜来风雨声，花落知多少。"),
    ("P08", "鹿柴", "王维", "古绝", "上声二十二养（仄韵）",
     "空山不见人，但闻人语响。返景入深林，复照青苔上。"),
    ("P09", "静夜思", "李白", "古绝", "下平七阳",
     "床前明月光，疑是地上霜。举头望明月，低头思故乡。"),
]

CIS = [
    ("C01", "浣溪沙", "韩偓",
     "宿醉离愁慢髻鬟，六铢衣薄惹轻寒。慵红闷翠掩青鸾。"
     "罗袜况兼金菡萏，雪肌仍是玉琅玕。骨香腰细更沈檀。"),
    ("C02", "浣溪沙", "晏殊",
     "一曲新词酒一杯，去年天气旧亭台。夕阳西下几时回。"
     "无可奈何花落去，似曾相识燕归来。小园香径独徘徊。"),
    ("C03", "忆江南", "白居易",
     "江南好，风景旧曾谙。日出江花红胜火，春来江水绿如蓝。能不忆江南。"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    buf = io.StringIO()

    def w(s=""):
        buf.write(s + "\n")

    w("权威名篇探测记录")
    w("=" * 64)
    w("说明：本文件由 tools/capture_probe.py 生成。诗句为通行本，韵部/体式依《平水韵》与近体定格。")
    w("本记录只呈现引擎实际输出，不加评价。")
    w()
    for pid, title, author, form, yun, text in POEMS:
        try:
            res = check_poem(text, title)
            out = render(res)
            verdict = res["结论"]
        except SystemExit as e:
            out, verdict = f"[引擎拒绝] {e}", "REJECTED"
        w(f"### {pid} {author}《{title}》（{form}，{yun}）")
        w(f"引擎结论：{verdict}　判定码：{res.get('判定', '-') if isinstance(res, dict) else '-'}")
        w("-" * 64)
        w(out)
        w()
    for cid, cipai, author, text in CIS:
        try:
            res = check_ci(text, cipai, author)
            out = render(res)
            verdict = res["结论"]
        except SystemExit as e:
            out, verdict = f"[引擎拒绝] {e}", "REJECTED"
        w(f"### {cid} {author}《{cipai}》")
        w(f"引擎结论：{verdict}　判定码：{res.get('判定', '-') if isinstance(res, dict) else '-'}")
        w("-" * 64)
        w(out)
        w()

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    print(buf.getvalue()[:2000])
    print(f"\n[写入] {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
