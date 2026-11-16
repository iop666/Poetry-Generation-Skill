#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 WP-B3/B4：六套音韻體系的分層資料庫（候選研究層）。

絕對不把不同歷史音系合併成單一「平仄字典」。每一條讀音記錄都帶 system 與
evidence_level，可追溯至書、卷、韻目、頁（有則填，無則 NULL）。

體系與來源
  old_chinese        上古音        — 本輪未建（缺《詩經韻讀》《楚辭韻讀》原書）
  middle_chinese     中古音        — 《廣韻》(四庫本, 5 卷)＋《集韻》(四庫本, 206 韻)
  regulated_verse    近體詩用韻    — 《平水韻》106 韻字表
  ci_rhyme           詞韻          — 《詞林正韻》十九部（部目級，原書字表未得）
  yuan_qu            曲韻          — 《中原音韻》十九部（維基文庫本）
  modern_rhyme       現代詩韻      — 《中華新韻》十四韻（韻母層，字級為拼音派生）
"""
import json, os, re, sqlite3, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
KB = os.path.join(os.path.dirname(ROOT), "诗词格律引擎", "诗歌知识库", "04_韵书")
RAW = os.path.join(ROOT, "raw", "r2_08")
TODAY = "2026-11-14"

SYSTEMS = [
    ("old_chinese", "上古音", "《詩經》《楚辭》韻部研究", "NOT_BUILT", "本輪未取得原書"),
    ("middle_chinese", "中古音", "《廣韻》《集韻》", "BUILT", ""),
    ("regulated_verse", "近體詩用韻", "《平水韻》106 韻", "BUILT", ""),
    ("ci_rhyme", "詞韻", "《詞林正韻》十九部", "PARTIAL", "僅部目，無原書字表"),
    ("yuan_qu", "曲韻", "《中原音韻》十九部", "PARTIAL", ""),
    ("modern_rhyme", "現代詩韻", "《中華新韻》十四韻", "DERIVED", "字級由拼音派生，非原書字表"),
]

TONE_OF = {"上平聲部": "平", "下平聲部": "平", "上聲部": "上", "去聲部": "去", "入聲部": "入"}


def load_pingshui():
    p = json.load(open(os.path.join(KB, "平水韵_全表_繁体.json"), encoding="utf-8"))
    groups = []
    for section, tone in TONE_OF.items():
        for yun, chars in p.get(section.split("部")[0] + "部" if False else section, {}).items():
            pass
    for section, tone in TONE_OF.items():
        block = p.get("ping" if tone == "平" else "ze", {})
        for yun, chars in block.get(section, {}).items():
            if isinstance(chars, list):
                chars = "".join(chars)
            groups.append({"system": "regulated_verse", "group_name": yun, "tone": tone,
                           "source": "平水韵_全表_繁体.json", "chars": chars})
    return groups


def cn_num(s):
    CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    m = re.match(r"^(上平聲|下平聲|上聲|去聲|入聲)?([一二三四五六七八九十]+)(.+)$", s)
    if not m:
        return None, s
    pre, num, name = m.group(1) or "", m.group(2), m.group(3)
    total, cur = 0, 0
    for ch in num:
        v = CN.get(ch)
        if v == 10:
            total += (cur or 1) * 10
            cur = 0
        else:
            cur = v
    return total + cur, pre + name


def build_pingshui(con):
    groups = load_pingshui()
    n = 0
    for g in groups:
        no, _ = cn_num(g["group_name"])
        con.execute("INSERT INTO ph_rhyme_groups_r2_08 VALUES(?,?,?,?,?,?,?,?,?)",
                    ("regulated_verse", g["group_name"], no, g["tone"], "", len(g["chars"]),
                     g["source"], "PARSED", TODAY))
        for c in dict.fromkeys(g["chars"]):
            con.execute("INSERT INTO ph_readings_r2_08 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (None, "regulated_verse", c, None, None, None, g["tone"],
                         g["group_name"], None, g["source"], None, None,
                         "PINGSHUI_TABLE"))
            n += 1
    return len(groups), n


CANON = {
 "上平聲": "东 冬 江 支 微 鱼 虞 齐 佳 灰 真 文 元 寒 删".split(),
 "下平聲": "先 萧 肴 豪 歌 麻 阳 庚 青 蒸 尤 侵 覃 盐 咸".split(),
 "上聲": "董 肿 讲 纸 尾 语 麌 荠 蟹 贿 轸 吻 阮 旱 潸 铣 筱 巧 皓 哿 马 养 梗 迥 有 寝 感 琰 豏".split(),
 "去聲": "送 宋 绛 寘 未 御 遇 霁 泰 卦 队 震 问 愿 翰 谏 霰 啸 效 号 个 祃 漾 敬 径 宥 沁 勘 艳 陷".split(),
 "入聲": "屋 沃 觉 质 物 月 曷 黠 屑 药 陌 锡 职 缉 合 叶 洽".split(),
}
NAME2KEY = {}
for blk, names in CANON.items():
    for i, nm in enumerate(names, 1):
        NAME2KEY[nm] = (blk, i)


def norm_yun_label(s):
    """「上平聲一東」→ (block, no)；「一东」→ (block, no) 由 NAME2KEY 決定。"""
    m = re.match(r"^(上平聲|下平聲|上聲|去聲|入聲)([一二三四五六七八九十]+)(.+)$", s)
    if not m:
        return None
    blk = m.group(1)
    CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    total, cur = 0, 0
    for ch in m.group(2):
        v = CN.get(ch)
        if v == 10:
            total += (cur or 1) * 10
            cur = 0
        else:
            cur = v
    return blk, total + cur


def build_cilin(con):
    """詞林正韻：只到部目級；字級由平水韻目折算而來，標 DERIVED，半韻標 UNKNOWN。"""
    d = json.load(open(os.path.join(KB, "词林正韵_十九部.json"), encoding="utf-8"))
    bu = d["十九部"]
    half = set(d.get("半韵", {}).get("韵目", []))
    n_g, n_r, n_half = 0, 0, 0
    ps = collections.defaultdict(list)
    for r in con.execute("SELECT rhyme_group, charx FROM ph_readings_r2_08 WHERE system='regulated_verse'"):
        k = norm_yun_label(r[0])
        if k:
            ps[k].append(r[1])
    for name, v in bu.items():
        con.execute("INSERT INTO ph_rhyme_groups_r2_08 VALUES(?,?,?,?,?,?,?,?,?)",
                    ("ci_rhyme", name, int(re.sub(r"\D", "", name) or 0), "平上去入",
                     v.get("说明", "")[:120], 0, "词林正韵_十九部.json", "DEPENDENT_LABEL", TODAY))
        n_g += 1
        for tone_key, tone in (("平", "平"), ("上", "上"), ("去", "去"), ("入", "入")):
            for yun in v.get(tone_key, []):
                derived = yun in half
                nm = re.sub(r"^[一二三四五六七八九十]+", "", yun)
                key = NAME2KEY.get(nm)
                if key is None:
                    continue
                for c in ps.get(key, []):
                    con.execute("INSERT INTO ph_readings_r2_08 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                (None, "ci_rhyme", c, None, None, None, tone, name, None,
                                 "词林正韵_十九部.json", None, None,
                                 "DERIVED_FROM_PINGSHUI_HALF" if derived
                                 else "DERIVED_FROM_PINGSHUI"))
                    n_r += 1
                    if derived:
                        n_half += 1
    return n_g, n_r, n_half


def build_guangyun(con):
    f = os.path.join(RAW, "guangyun_xiaoyun.jsonl")
    if not os.path.exists(f):
        return 0, 0
    rows = [json.loads(l) for l in open(f, encoding="utf-8")]
    n_g = len({(r["volume"], r["yun_no"]) for r in rows})
    n = 0
    for r in rows:
        con.execute("INSERT INTO ph_readings_r2_08 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (None, "middle_chinese", r["head"], None, None, None, r["tone"],
                     r["yun_name"] or "", r["fanqie"], "廣韻（四庫全書本·維基文庫轉錄）",
                     str(r["volume"]), None, "GUANGYUN_ENTRY"))
        n += 1
    return n_g, n


def build_jiyun(con):
    f = os.path.join(RAW, "jiyun_xiaoyun.jsonl")
    if not os.path.exists(f):
        return 0, 0
    rows = [json.loads(l) for l in open(f, encoding="utf-8")]
    n_g = len({(r["volume"], r["yun_no"]) for r in rows})
    n = 0
    for r in rows:
        for c in (r["chars"] or r["head_char"]):
            con.execute("INSERT INTO ph_readings_r2_08 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (None, "middle_chinese", c, None, None, None, r["tone"],
                         r["yun_name"] or "", r["fanqie"], "集韻（四庫全書本·維基文庫轉錄）",
                         r["volume"], None, "JIYUN_SMALL_RHYME"))
            n += 1
    return n_g, n


ZHONGYUAN_BU = ["東鍾", "江陽", "支思", "齊微", "魚模", "皆來", "真文", "寒山", "桓歡",
                "先天", "蕭豪", "歌戈", "家麻", "車遮", "庚青", "尤侯", "侵尋", "監鹹", "廉纖"]


def build_zhongyuan(con):
    f = os.path.join(RAW, "zhongyuan", "中原音韻_正文.json")
    n_g = 0
    for i, b in enumerate(ZHONGYUAN_BU, 1):
        con.execute("INSERT INTO ph_rhyme_groups_r2_08 VALUES(?,?,?,?,?,?,?,?,?)",
                    ("yuan_qu", "第%d部 %s" % (i, b), i, "平上去", "", 0,
                     "中原音韻_正文.json", "INDEX_ONLY", TODAY))
        n_g += 1
    return n_g, 0


YUN14 = [("一麻", "a ia ua"), ("二波", "o e uo"), ("三皆", "ie üe"), ("四开", "ai uai"),
         ("五微", "ei ui"), ("六豪", "ao iao"), ("七尤", "ou iu"), ("八寒", "an ian uan üan"),
         ("九文", "en in un ün"), ("十唐", "ang iang uang"), ("十一庚", "eng ing ong iong"),
         ("十二齐", "i ü er"), ("十三支", "zhi chi shi ri zi ci si"), ("十四姑", "u")]


def build_modern(con):
    """現代詩韻：韻目層據《中華新韻》十四韻；字級由普通話拼音派生（非原書字表）。"""
    n_g = 0
    for name, finals in YUN14:
        con.execute("INSERT INTO ph_rhyme_groups_r2_08 VALUES(?,?,?,?,?,?,?,?,?)",
                    ("modern_rhyme", name, int(re.sub(r"\D", "", name) or 0), "平",
                     finals, 0, "中华新韵_十四韵.md", "INDEX_ONLY", TODAY))
        n_g += 1
    try:
        from pypinyin import pinyin, Style
    except Exception:
        return n_g, 0
    fmap = {}
    for name, finals in YUN14:
        for f in finals.split():
            fmap[f] = name
    chars = {r[0] for r in con.execute(
        "SELECT DISTINCT charx FROM ph_readings_r2_08 WHERE system='regulated_verse'")}
    n = 0
    for c in chars:
        try:
            fin = pinyin(c, style=Style.FINALS, strict=True, errors="ignore")
        except Exception:
            continue
        if not fin or not fin[0]:
            continue
        f = fin[0][0]
        g = fmap.get(f)
        if not g:
            # 整體認讀音節與 -i 變體
            if f in ("i",) and re.match(r"^(zhi|chi|shi|ri|zi|ci|si)$", ""):
                pass
        if not g:
            continue
        con.execute("INSERT INTO ph_readings_r2_08 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (None, "modern_rhyme", c, None, None, f, "平", g, None,
                     "pypinyin(派生)", None, None, "DERIVED_PINYIN"))
        n += 1
    return n_g, n


def main():
    con = sqlite3.connect(DB)
    con.executescript("""
    DROP TABLE IF EXISTS ph_systems_r2_08;
    DROP TABLE IF EXISTS ph_rhyme_groups_r2_08;
    DROP TABLE IF EXISTS ph_readings_r2_08;
    DROP TABLE IF EXISTS ph_audit_r2_08;
    CREATE TABLE ph_systems_r2_08(system TEXT PRIMARY KEY, name_cn TEXT, sources TEXT,
        build_status TEXT, limitation TEXT, round TEXT);
    CREATE TABLE ph_rhyme_groups_r2_08(system TEXT, group_name TEXT, group_no INT, tone TEXT,
        note TEXT, n_chars INT, source TEXT, quality TEXT, round TEXT);
    CREATE TABLE ph_readings_r2_08(id INTEGER PRIMARY KEY AUTOINCREMENT, system TEXT,
        charx TEXT, reading TEXT, initial TEXT, final TEXT, tone TEXT, rhyme_group TEXT,
        fanqie TEXT, source_book TEXT, volume TEXT, page TEXT, evidence_level TEXT);
    CREATE TABLE ph_audit_r2_08(system TEXT, n_groups INT, n_readings INT, note TEXT, round TEXT);
    """)
    for s in SYSTEMS:
        con.execute("INSERT INTO ph_systems_r2_08 VALUES(?,?,?,?,?,?)", s + (TODAY,))

    res = {}
    ng, nr = build_pingshui(con); res["regulated_verse"] = (ng, nr)
    ng, nr, nh = build_cilin(con); res["ci_rhyme"] = (ng, nr)
    ng, nr = build_guangyun(con); res["middle_chinese/guangyun"] = (ng, nr)
    ng, nr = build_jiyun(con); res["middle_chinese/jiyun"] = (ng, nr)
    ng, nr = build_zhongyuan(con); res["yuan_qu"] = (ng, nr)
    ng, nr = build_modern(con); res["modern_rhyme"] = (ng, nr)

    for system, (ng, nr) in res.items():
        con.execute("INSERT INTO ph_audit_r2_08 VALUES(?,?,?,?,?)",
                    (system, ng, nr, "", TODAY))
    con.execute("INSERT INTO ph_audit_r2_08 VALUES(?,?,?,?,?)",
                ("ci_rhyme_half", 0, nh, "半韻字級歸屬不明，已標 DERIVED_FROM_PINGSHUI_HALF", TODAY))
    con.commit()

    tot = con.execute("SELECT system, COUNT(*), COUNT(DISTINCT charx) FROM ph_readings_r2_08 "
                      "GROUP BY system").fetchall()
    out = {"by_system": {r[0]: {"n_readings": r[1], "n_chars": r[2]} for r in tot},
           "groups": {r[0]: r[1] for r in con.execute(
               "SELECT system, COUNT(*) FROM ph_rhyme_groups_r2_08 GROUP BY system")},
           "half_yun_readings": nh}
    json.dump(out, open(os.path.join(RAW, "ph_audit.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
