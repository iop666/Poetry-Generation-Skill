#!/usr/bin/env python3
"""作者名规范化：把「原始著录名」映射到「通行姓名」。

为什么不直接改 author_name：
    RAW 层不可改写（AGENT_REPORTING_STANDARD v2 §5）。原始著录名是《古詩紀》
    《昭明文選》等底本的实际写法，本身即证据；改写后就无法回溯。
    因此新增 author_alias 表 + works.author_canonical 列，原始值原样保留。

处理四类问题（每类都有实际证据，非推测）：
    1) NOT_PERSON —— 根本不是人名。四庫本把部类名、乐曲名当成了作者：
       「郊廟朝會歌辭」1,639 条、「鼔吹曲辭」44 条、「昭徳凱容樂」43 条、「古諺」42 条。
    2) TEMPLE —— 谥号／庙号。《古詩紀》南朝诸卷径题「簡文帝」「元帝」「昭明太子」。
    3) STYLE  —— 以字号署名。《昭明文選》题「王仲宣」「謝玄暉」「顏延年」。
    4) VARIANT —— 异体字与繁简并存：「傅𤣥」/「傅玄」、「曹勛」/「曹勋」、「王襃」/「王褒」。
"""
from __future__ import annotations

import collections
import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "database", "poetry.db")
OUT = os.path.join(BASE, "audit", "author_canon_report.json")

try:
    from opencc import OpenCC
    _t2s, _s2t = OpenCC("t2s"), OpenCC("s2t")
except Exception:  # pragma: no cover
    _t2s = _s2t = None


def t2s(x: str) -> str:
    """逐字繁转简，且只接受「可回环」的转换。

    为什么不能直接用 OpenCC 整串转换：OpenCC 的 t2s 词典含异体字归并，
    实测把「张榘」转成「张矩」—— 这是两个不同的人（张榘字方叔／张矩字梅深），
    整串转换会把 109 首作品错误并到一人名下。
    故改为逐字转换，并要求 s2t(t2s(c)) == c（即确为繁简对应而非异体归并）才接受；
    回环不成立的字符原样保留。
    """
    if _t2s is None:
        return x
    out = []
    for ch in x:
        c = _t2s.convert(ch)
        if len(c) == 1 and _s2t.convert(c) == ch:
            out.append(c)
        else:
            out.append(ch)
    return "".join(out)

# ---------- 1. 非人名 ----------
NOT_PERSON_EXACT = {
    "郊廟朝會歌辭", "郊庙朝会歌辞", "鼔吹曲辭", "鼓吹曲辭", "鼓吹曲辞", "昭徳凱容樂",
    "昭徳凯容乐", "清商曲辭", "清商曲辞", "樂府", "乐府", "郊廟歌辭", "郊庙歌辞",
    "樂章", "乐章", "舞曲", "琴曲", "雜曲", "杂曲", "歌辭", "歌辞", "古辭", "古辞",
}
NOT_PERSON_RE = re.compile(
    r"(曲辭|曲辞|樂章|乐章|歌辭|歌辞|古諺|古谚|諺$|谚$|謠$|谣$|^古詩$|^古诗$"
    r"|鼓吹|凱容|凯容|歌詩$|歌诗$|艷歌|艳歌|^樂府|^乐府)")

# ---------- 2. 谥号 / 庙号 ----------
# 仅收「底本确实以谥号署名、且其人可唯一确定」者。存疑者不入表，交由 UNKNOWN。
TEMPLE = {
    "簡文帝": ("蕭綱", "南朝梁簡文帝蕭綱"),
    "简文帝": ("萧纲", "南朝梁简文帝萧纲"),
    "元帝": ("蕭繹", "南朝梁元帝蕭繹"),
    "武帝": ("蕭衍", "南朝梁武帝蕭衍"),
    "昭明太子": ("蕭統", "昭明太子蕭統"),
    "太宗皇帝": ("李世民", "唐太宗李世民"),
    "明皇帝": ("李隆基", "唐玄宗（谥「至道大圣大明孝皇帝」，唐人称明皇帝）"),
    "德宗皇帝": ("李适", "唐德宗李适"),
    "則天皇后": ("武曌", "则天皇后武曌"),
    "则天皇后": ("武曌", "则天皇后武曌"),
    "高宗皇帝": ("李治", "唐高宗李治"),
    "宣宗章皇帝": ("朱瞻基", "明宣宗朱瞻基"),
    "楊皇后": ("楊桂枝", "宋宁宗杨皇后（据《宋史·后妃传》）"),
}

# ---------- 3. 字号 → 姓名 ----------
# 依据：《昭明文選》李善注与题署、《古詩紀》小传。只收可唯一对应者。
STYLE = {
    "王仲宣": "王粲", "劉公幹": "劉楨", "曹子建": "曹植", "曹子桓": "曹丕",
    "陶淵明": "陶潛", "陶渊明": "陶潜",
    "顔延年": "顏延之", "顏延年": "顏延之", "顏特進": "顏延之",
    "沈休文": "沈約", "江文通": "江淹", "范彥龍": "范雲", "范彦龙": "范云",
    "謝玄暉": "謝朓", "谢玄晖": "谢朓",
    "左太沖": "左思", "左太冲": "左思",
    "陸士衡": "陸機", "陆士衡": "陆机",
    "潘安仁": "潘岳", "張景陽": "張協", "张景阳": "张协",
    "郭景純": "郭璞", "郭景纯": "郭璞",
    "劉越石": "劉琨", "刘越石": "刘琨",
    "鮑明遠": "鮑照", "鲍明远": "鲍照",
    "任彥昇": "任昉", "任彦昇": "任昉",
    "何仲言": "何遜", "何仲言": "何逊",
    "吳叔庠": "吳均", "吴叔庠": "吴均",
    "王元長": "王融", "王元长": "王融",
    "丘希範": "丘遲", "丘希范": "丘迟",
    "嵇叔夜": "嵇康", "阮嗣宗": "阮籍", "張平子": "張衡", "张平子": "张衡",
    "蔡伯喈": "蔡邕", "蘇子卿": "蘇武", "苏子卿": "苏武",
    "李少卿": "李陵", "曹大家": "班昭",
    "謝宣遠": "謝瞻", "谢宣远": "谢瞻", "潘正叔": "潘尼",
    "傅長虞": "傅咸", "傅长虞": "傅咸", "張茂先": "張華", "张茂先": "张华",
    "盧子諒": "盧諶", "卢子谅": "卢谌", "應德璉": "應瑒", "应德琏": "应玚",
    "阮元瑜": "阮瑀", "陳孔璋": "陳琳", "陈孔璋": "陈琳",
    "徐偉長": "徐幹", "徐伟长": "徐干", "應休璉": "應璩", "应休琏": "应璩",
    "棗道彥": "棗據", "枣道彦": "枣据", "王正長": "王讚", "王正长": "王赞",
    "何敬宗": "何劭", "石季倫": "石崇", "石季伦": "石崇",
    "曹顏遠": "曹攄", "曹颜远": "曹摅", "束廣微": "束皙", "束广微": "束皙",
    "張孟陽": "張載", "张孟阳": "张载", "司馬紹統": "司馬彪", "司马绍统": "司马彪",
    "劉伯倫": "劉伶", "刘伯伦": "刘伶", "向子期": "向秀", "謝叔源": "謝混",
    "谢叔源": "谢混", "傅休奕": "傅玄", "袁陽源": "袁淑", "袁阳源": "袁淑",
    "王景玄": "王微", "陳思王植": "曹植", "陈思王植": "曹植",
}

# ---------- 4. 异体字 ----------
# 只处理「同一人、写法不同」的确证个例；不做全局字形替换。
GLYPH = {
    "傅𤣥": "傅玄", "𥞇康": "嵇康", "鮑照": "鮑照",
    "荀㫤": "荀昶", "王襃": "王褒", "呉均": "吳均",
    "髙適": "高適", "髙帝": "高帝",
}

TRAIL = re.compile(r"[一二三四五六七八九十百]+$")
SUFFIX = re.compile(r"(樂府|乐府)$")


def classify(raw: str):
    """返回 (canonical, kind, evidence)。canonical 为空串表示「非人名」。"""
    name = (raw or "").strip()
    if not name:
        return "", "EMPTY", "原始著录为空"
    if name in NOT_PERSON_EXACT or NOT_PERSON_RE.search(name):
        return "", "NOT_PERSON", "部类名／乐曲名，非作者"
    # 映射表内是通行繁体名，仍需统一转简，否则「蕭綱」与「萧纲」会并存两条
    if name in TEMPLE:
        return t2s(TEMPLE[name][0]), "TEMPLE_NAME", TEMPLE[name][1]
    if name in STYLE:
        return t2s(STYLE[name]), "STYLE_NAME", "以字号署名，据李善注／本传归姓名"
    if name in GLYPH:
        return t2s(GLYPH[name]), "VARIANT_GLYPH", "异体字，同一人"
    base = SUFFIX.sub("", name)
    canon = t2s(base)
    # 尾部数字只在「去掉后能命中谥号／字号表」时才剥离 —— 否则会误伤
    # 「王锡九」「刘锡五」「张元一」这类真的以数字结尾的人名（实测 3 组被并错）。
    if TRAIL.search(canon):
        trimmed = TRAIL.sub("", canon)
        if trimmed in TEMPLE or trimmed in STYLE:
            canon = t2s(TEMPLE.get(trimmed, (STYLE.get(trimmed, trimmed),))[0]) \
                if trimmed in TEMPLE else t2s(STYLE[trimmed])
            return canon, "TEMPLE_NAME", "底本以谥号＋篇数题署（如「簡文帝三」）"
    return canon, ("VARIANT_SIMP" if canon != base else "SAME"), \
        ("繁简归并" if canon != base else "原样")


def main() -> int:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cols = [r[1] for r in conn.execute("PRAGMA table_info(works)")]
    if "author_canonical" not in cols:
        conn.execute("ALTER TABLE works ADD COLUMN author_canonical TEXT")
        print("[1] works.author_canonical 已新增")
    conn.execute("""CREATE TABLE IF NOT EXISTS author_alias(
        raw_name TEXT PRIMARY KEY, canonical TEXT, kind TEXT, evidence TEXT, auto INTEGER)""")

    raws = [r[0] for r in conn.execute(
        "SELECT author_name FROM works GROUP BY 1")]
    rows, kinds = [], collections.Counter()
    for raw in raws:
        canon, kind, ev = classify(raw)
        rows.append((raw, canon, kind, ev, 1))
        kinds[kind] += 1
    conn.execute("DELETE FROM author_alias")
    conn.executemany("INSERT INTO author_alias VALUES (?,?,?,?,?)", rows)
    print(f"[2] author_alias 写入 {len(rows)} 条：{dict(kinds)}")

    conn.execute("""UPDATE works SET author_canonical = (
        SELECT canonical FROM author_alias a WHERE a.raw_name = works.author_name)""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_works_author_canon ON works(author_canonical)")
    conn.commit()

    # ---------------- 统计 ----------------
    total = conn.execute("SELECT COUNT(*) FROM works").fetchone()[0]
    empty = conn.execute("SELECT COUNT(*) FROM works WHERE author_canonical=''").fetchone()[0]
    nullc = conn.execute("SELECT COUNT(*) FROM works WHERE author_canonical IS NULL").fetchone()[0]
    before = conn.execute("SELECT COUNT(DISTINCT author_name) FROM works").fetchone()[0]
    after = conn.execute(
        "SELECT COUNT(DISTINCT author_canonical) FROM works WHERE author_canonical<>''").fetchone()[0]

    collapse = conn.execute("""
        SELECT raw_name, canonical, COUNT(*) n FROM works w
        JOIN author_alias a ON a.raw_name = w.author_name
        WHERE a.kind IN ('VARIANT_SIMP','VARIANT_GLYPH','STYLE_NAME','TEMPLE_NAME')
           OR a.canonical <> a.raw_name
        GROUP BY raw_name ORDER BY n DESC LIMIT 25""").fetchall()

    # 一名对多原始名（真正的归并效果）
    merged = conn.execute("""
        SELECT canonical, COUNT(DISTINCT raw_name) k, SUM(n) n FROM (
            SELECT w.author_name raw_name, w.author_canonical canonical, COUNT(*) n
            FROM works w WHERE w.author_canonical<>'' GROUP BY 1,2)
        GROUP BY canonical HAVING k > 1 ORDER BY k DESC, n DESC LIMIT 25""").fetchall()

    suspects = conn.execute("""
        SELECT author_name, COUNT(*) n FROM works
        WHERE author_canonical<>'' AND (
              LENGTH(author_name) >= 5
           OR author_name LIKE '%第%' OR author_name LIKE '%公%'
           OR author_name LIKE '%先生%' OR author_name LIKE '%居士%'
           OR author_name LIKE '%山人%')
        GROUP BY 1 ORDER BY n DESC LIMIT 30""").fetchall()

    rep = {
        "统计": {
            "作品总数": total,
            "原始著录名数": before,
            "规范化后姓名数": after,
            "非人名作品条数": empty,
            "未映射(NULL)": nullc,
            "归并净减": before - after,
        },
        "类型分布": dict(kinds),
        "逐条归并示例": [{"原始名": r[0], "归为": r[1], "条数": r[2]} for r in collapse],
        "一名多写": [{"姓名": r[0], "写法数": r[1], "条数": r[2]} for r in merged],
        "待人工复核": [{"名": r[0], "条数": r[1]} for r in suspects],
    }
    json.dump(rep, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"[3] 作品 {total:,}；原始名 {before:,} → 规范名 {after:,}（净减 {before-after}）")
    print(f"[4] 非人名 {empty:,} 条；未映射 {nullc}")
    print("[5] 归并示例:", [(r[0], r[1], r[2]) for r in collapse[:8]])
    print("[6] 一名多写:", [(r[0], r[1]) for r in merged[:8]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
