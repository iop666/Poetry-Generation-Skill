#!/usr/bin/env python3
"""《昭明文選》詩類（卷19–31）→ 中间 JSON。

为什么补这一部：
    古詩紀（四庫全書本）在維基文庫的转录并不完整 —— 晉卷每卷仅 15 KB，
    陶潛、謝靈運、曹植等大家的詩大多缺席（全库检索「採菊東籬」「池塘生春草」均为 0）。
    《昭明文選》卷19–31 为詩類，收先秦至齊梁詩，正好补上这批作者，
    且带李善注，可用于后续「用典／训诂」核验。

版式：
    ===篇題===
    {{*|五言}}                       ← 体裁小注，丢弃
    [[作者:王粲|王仲宣]]              ← 作者（显示名为字号，如「王仲宣」）
    {{Main|詠史詩 (王粲)}}            ← 互见，丢弃
    <poem>
    自古無殉死，達人共所知。{{*|禮記曰：…}}   ← 行内夹注，必须剥除
    ...
    </poem>
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "raw", "books", "wenxuan")
DST = os.path.join(BASE, "raw", "poetry", "wenxuan")

# 《文選》詩類作者生卒所屬朝代。
# 依据：《文選》以體裁分類、每體之下按時代先後編次，故作者時代可由編次推定；
# 另与《中國文學史》通行分期对照。**未与史传逐人核对**，属「推定」，非「核验」。
ERA = {
    # 先秦
    "屈原": "先秦", "宋玉": "先秦", "荊軻": "先秦",
    # 漢
    "無名氏": "汉魏", "蘇武": "汉魏", "李陵": "汉魏", "班婕妤": "汉魏",
    "張衡": "汉魏", "蔡邕": "汉魏", "蔡琰": "汉魏", "辛延年": "汉魏",
    "宋子侯": "汉魏", "古詩": "汉魏", "古辭": "汉魏",
    # 魏
    "曹操": "汉魏", "曹丕": "汉魏", "曹植": "汉魏", "王粲": "汉魏",
    "劉楨": "汉魏", "陳琳": "汉魏", "阮瑀": "汉魏", "應瑒": "汉魏",
    "徐幹": "汉魏", "應璩": "汉魏", "嵇康": "魏晋南北朝", "阮籍": "魏晋南北朝",
    # 晉
    "陶潛": "魏晋南北朝", "陶渊明": "魏晋南北朝", "陸機": "魏晋南北朝",
    "陸雲": "魏晋南北朝", "潘岳": "魏晋南北朝", "潘尼": "魏晋南北朝",
    "左思": "魏晋南北朝", "張協": "魏晋南北朝", "張載": "魏晋南北朝",
    "郭璞": "魏晋南北朝", "劉琨": "魏晋南北朝", "盧諶": "魏晋南北朝",
    "束皙": "魏晋南北朝", "石崇": "魏晋南北朝", "曹攄": "魏晋南北朝",
    "何劭": "魏晋南北朝", "傅玄": "魏晋南北朝", "張華": "魏晋南北朝",
    "司馬彪": "魏晋南北朝", "王讚": "魏晋南北朝", "棗據": "魏晋南北朝",
    # 宋（南朝）
    "謝靈運": "魏晋南北朝", "顏延之": "魏晋南北朝", "鮑照": "魏晋南北朝",
    "謝惠連": "魏晋南北朝", "謝瞻": "魏晋南北朝", "謝混": "魏晋南北朝",
    "王微": "魏晋南北朝", "袁淑": "魏晋南北朝", "劉鑠": "魏晋南北朝",
    "顔延年": "魏晋南北朝", "顏延年": "魏晋南北朝",
    # 齊
    "謝朓": "魏晋南北朝", "王融": "魏晋南北朝", "沈約": "魏晋南北朝",
    "范雲": "魏晋南北朝", "江淹": "魏晋南北朝", "丘遲": "魏晋南北朝",
    "王僧達": "魏晋南北朝", "虞羲": "魏晋南北朝", "王儉": "魏晋南北朝",
    # 梁
    "何遜": "魏晋南北朝", "吳均": "魏晋南北朝", "任昉": "魏晋南北朝",
    "徐悱": "魏晋南北朝", "劉孝綽": "魏晋南北朝", "王屮": "魏晋南北朝",
    "陸厥": "魏晋南北朝", "柳惲": "魏晋南北朝", "蕭衍": "魏晋南北朝",
}

# 文選以字号署名的，归到通行姓名（与《古詩紀》一致前先做一次归一）
STYLE = {"王仲宣": "王粲", "劉公幹": "劉楨", "曹子建": "曹植", "曹子桓": "曹丕",
         "陶淵明": "陶潛", "謝靈運": "謝靈運", "顔延年": "顏延之", "顏延年": "顏延之",
         "沈休文": "沈約", "江文通": "江淹", "范彥龍": "范雲", "謝玄暉": "謝朓",
         "左太沖": "左思", "陸士衡": "陸機", "潘安仁": "潘岳", "張景陽": "張協",
         "郭景純": "郭璞", "劉越石": "劉琨", "鮑明遠": "鮑照", "任彥昇": "任昉",
         "何仲言": "何遜", "吳叔庠": "吳均", "王元長": "王融", "丘希範": "丘遲",
         "嵇叔夜": "嵇康", "阮嗣宗": "阮籍", "張平子": "張衡", "蔡伯喈": "蔡邕",
         "蘇子卿": "蘇武", "李少卿": "李陵", "班婕妤": "班婕妤", "曹大家": "班昭",
         "謝宣遠": "謝瞻", "潘正叔": "潘尼", "顏特進": "顏延之", "傅長虞": "傅咸",
         "張茂先": "張華", "盧子諒": "盧諶", "劉公幹": "劉楨", "應德璉": "應瑒",
         "阮元瑜": "阮瑀", "陳孔璋": "陳琳", "徐偉長": "徐幹", "應休璉": "應璩",
         "嵇喜": "嵇喜", "棗道彥": "棗據", "王正長": "王讚", "何敬宗": "何劭",
         "石季倫": "石崇", "曹顏遠": "曹攄", "束廣微": "束皙", "張孟陽": "張載",
         "司馬紹統": "司馬彪", "劉伯倫": "劉伶", "向子期": "向秀", "謝叔源": "謝混",
         "傅休奕": "傅玄", "王康琚": "王康琚", "王僧達": "王僧達", "袁陽源": "袁淑",
         "王景玄": "王微", "謝惠連": "謝惠連", "顏延年": "顏延之"}

TPL = re.compile(r"\{\{[^{}]*\}\}")
LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]")
# 层级 3–5 都可能是篇题：《五君詠》下用 ====阮步兵==== 这类四级标题分咏五人。
H3 = re.compile(r"^(={3,5})\s*(.+?)\s*={3,5}\s*$")
TAG = re.compile(r"</?(?:poem|center|div)[^>]*>")


def strip_tpl(s: str) -> str:
    """剥掉注释模板。注文是李善注，属研究资料，不进正文。"""
    for _ in range(4):
        new = TPL.sub("", s)
        if new == s:
            break
        s = new
    s = LINK.sub(r"\1", s)
    s = TAG.sub("", s)
    s = s.replace("'''", "").replace("''", "")
    return s


def parse_volume(text: str, vol: str) -> list:
    out = []
    # 去掉 header2 模板块
    text = re.sub(r"\{\{header2.*?\}\}", "", text, flags=re.S)
    parts = re.split(r"(?m)^(={3,5})\s*(.+?)\s*={3,5}\s*$", text)
    # parts = [前言, 等号1, 篇題1, 正文1, 等号2, 篇題2, 正文2, ...]
    last_author = ""
    for i in range(1, len(parts) - 2, 3):
        level = len(parts[i])
        title = strip_tpl(parts[i + 1]).strip()
        body = parts[i + 2]
        # 卷末「文選考異」「校記」是校勘记，不是诗，必须剔除
        if re.search(r"考異|考异|校記|校记|音義|音义", title):
            continue
        author = ""
        m = re.search(r"\[\[作者:([^\]|]+)(?:\|([^\]]+))?\]\]", body)
        if m:
            shown = (m.group(2) or m.group(1)).strip()
            author = STYLE.get(shown, shown)
        clean = strip_tpl(body)
        raw_lines = []
        for ln in clean.splitlines():
            t = ln.strip().strip("\u3000")
            if not t or t.startswith("|") or t.startswith("="):
                continue
            if t.startswith("{{Main") or t.startswith("[[作者:") or t.startswith("[[分類"):
                continue
            raw_lines.append(t)

        # 无 [[作者:]] 链接时：正文首行若为「2–5 个汉字、无标点」的短串，
        # 即为作者（文選以字号署名，如「顏延年」「謝玄暉」）。
        # 早期版本没做这一步，导致 241 篇作者为空，且作者名混进正文首行。
        BARE = re.compile(r"^[\u4e00-\u9fff]{2,5}$")
        if not author and raw_lines and BARE.match(raw_lines[0]):
            author = STYLE.get(raw_lines[0], raw_lines[0])
            raw_lines = raw_lines[1:]
        elif raw_lines and BARE.match(raw_lines[0]) and raw_lines[0] == author:
            raw_lines = raw_lines[1:]
        lines = raw_lines
        # 四级标题（组诗分咏）自身无作者行，承上篇作者
        if not author and level >= 4:
            author = last_author
        if not title or not lines:
            continue
        if author:
            last_author = author
        out.append({"title": title, "author": author, "paragraphs": lines,
                    "chapter": "詩類", "section": vol,
                    "dynasty": ERA.get(author, "未定"), "volume": vol})
    return out


def main() -> int:
    os.makedirs(DST, exist_ok=True)
    total = 0
    for path in sorted(glob.glob(os.path.join(SRC, "卷*.wikitext"))):
        vol = os.path.basename(path).replace(".wikitext", "")
        text = open(path, encoding="utf-8", errors="replace").read()
        items = parse_volume(text, vol)
        json.dump(items, open(os.path.join(DST, vol + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        total += len(items)
        print(f"  {vol}: {len(items)} 篇")
    print("合计", total, "篇")
    return 0


if __name__ == "__main__":
    sys.exit(main())
