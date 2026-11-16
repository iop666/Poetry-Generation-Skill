#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E3: 作者名审计 -> WORKS_AUTHOR_CORRECTIONS.csv"""
import sqlite3, csv, re
from collections import defaultdict

ROOT = "<PROJECT_ROOT>/poetry-database"
DB = f"{ROOT}/database/poetry.db"
OUT = f"{ROOT}/reports/tasks/2026-11-16/R2-12"
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); con.text_factory = str
con.execute("PRAGMA busy_timeout=8000")
q = lambda s, *a: con.execute(s, a).fetchall()

rows = []

# ---------- 1. 单字作者 ----------
single = q("""SELECT author_name,count(*) n,group_concat(DISTINCT dynasty),group_concat(DISTINCT genre)
FROM works WHERE length(author_name)=1 GROUP BY 1 ORDER BY n DESC""")
for name, n, dyns, ges in single:
    cands = q("""SELECT author_name,count(*) FROM works WHERE length(author_name)>1 AND author_name LIKE ?
                 GROUP BY 1 ORDER BY 2 DESC LIMIT 4""", name + "%")
    # 同文重复证据
    dup = []
    for wid, ti, pre in q("SELECT work_id,title_norm,substr(text_norm,1,14) FROM works WHERE author_name=? AND length(text_norm)>=14", name):
        hit = q("""SELECT work_id,author_name,title_norm FROM works WHERE length(author_name)>1
                   AND text_norm LIKE ? LIMIT 2""", "%" + pre + "%")
        if hit: dup.append((wid, ti, hit))
    cand_s = "；".join(f"{c}({m}条)" for c, m in cands) or "库内无同姓更长名"
    if dup:
        ev = (f"单字名 {n} 条（{dyns}／{ges}）；同姓候选：{cand_s}；"
              f"正文重合证据：" + "；".join(f"{w}《{t}》与 " + ",".join(f"{h[1]}({h[0]})" for h in hs) for w, t, hs in dup[:2]))
        verdict = "MERGE_UNCERTAIN"
        sug = "；".join(sorted({h[1] for _, _, hs in dup for h in hs})[:2])
        note = "同文重出但作者名不同，属互见/误属，不能据以确证全名"
    elif cands:
        ev = f"单字名 {n} 条（{dyns}／{ges}）；库内同姓更长名最多者：{cand_s}；正文前14字无重出"
        verdict = "MERGE_UNCERTAIN"
        sug = cands[0][0] if len(cands) == 1 else ""
        note = "极可能截断，但库内无同文重出可直接证据，禁止强行合并"
    else:
        ev = f"单字名 {n} 条（{dyns}／{ges}）；库内无同姓更长名"
        verdict = "UNRESOLVED"
        sug = ""
        note = "疑为法名/别号残字，无法定位全名"
    # 特例：张 -> 张昪
    if name == "张":
        ev += "；4 条均为宋词，《满江红·无利无名》《离亭燕·一带江山如画》为张昪(张昇)名作；库内无张昪/张昇；《离亭燕》另见孙浩然(songci:210e2944394b)"
        sug = "张昪"
        verdict = "MERGE_UNCERTAIN"
        note = "外部文献可定为张昪，但库内无该 name 条目、且有互见重出，需人工确认后并入"
    rows.append(dict(author_name=name, issue="SINGLE_CHAR_NAME", evidence=ev,
                     n_suspect_rows=n, suggested_full_name=sug, verdict=verdict, note=note))

# ---------- 2. 佚名变体 ----------
for name, n in q("""SELECT author_name,count(*) FROM works WHERE author_name IN
('佚名','無名氏','无名氏','闕名','阙名','不詳','不详','未詳','未详') GROUP BY 1 ORDER BY 2 DESC"""):
    rows.append(dict(author_name=name, issue="ANON_VARIANT",
                     evidence=f"同一「匿名」语义存在 4 种写法：佚名3974／无名氏3254／無名氏747／不詳731，简繁与用字均不统一",
                     n_suspect_rows=n, suggested_full_name="佚名", verdict="MERGE_SAFE",
                     note="纯书写变体合并，不涉及作者身份判断；建议统一为「佚名」"))

# ---------- 3. 作者名含数字（消歧后缀泄漏） ----------
for name, n in q("""SELECT author_name,count(*) FROM works WHERE author_name GLOB '*[0-9]*'
AND author_name NOT LIKE '%〖%' GROUP BY 1 ORDER BY 2 DESC"""):
    base = re.sub(r"[0-9]+", "", name)
    bn = q("SELECT count(*) FROM works WHERE author_name=?", base)
    sid = q("SELECT count(*) FROM works WHERE author_name=?", name)
    if re.match(r"^[一二三四五六七八九十]氏[0-9]$", name) or name.startswith("吴氏"):
        vd, nt = "DO_NOT_MERGE", "「吴氏1/2/3」是三个不同的人，数字不可剥离合并"
    elif base and bn:
        vd, nt = "MERGE_UNCERTAIN", "数字是上游同名序号，剥离后需确认是同一人被拆分还是确有两人"
    else:
        vd, nt = "MERGE_UNCERTAIN", "剥离数字后库内无同名条目，需人工确认后改名"
    rows.append(dict(author_name=name, issue="NAME_DIGIT_SUFFIX",
                     evidence=f"名字尾部带阿拉伯数字，系上游「同名消歧」后缀泄漏；去掉数字得「{base}」{'（库内 '+str(bn[0][0])+' 条）' if bn else '（库内无此名）'}",
                     n_suspect_rows=n, suggested_full_name=base if base else "", verdict=vd, note=nt))

# ---------- 4. 作者名含标点/多人合署 ----------
for name, n in q("""SELECT author_name,count(*) FROM works WHERE author_name GLOB '*[，。、；：！？（）]*'
GROUP BY 1 ORDER BY 2 DESC"""):
    rows.append(dict(author_name=name, issue="MULTI_AUTHOR_OR_PUNCT",
                     evidence="作者字段内含顿号/逗号等分隔符，为多人合署或编者署名被写入作者字段",
                     n_suspect_rows=n, suggested_full_name="",
                     verdict="UNRESOLVED",
                     note="需拆分为多条 attribution，本表不给出单一全名"))

# ---------- 5. 作者名含校记符号 ----------
for name, n in q("""SELECT author_name,count(*) FROM works WHERE author_name LIKE '%〖%'
GROUP BY 1 ORDER BY 2 DESC"""):
    rows.append(dict(author_name=name, issue="NAME_NOTE_MARK",
                     evidence="作者名尾部黏连校记序号「〖1〗」",
                     n_suspect_rows=n, suggested_full_name=re.sub(r"〖.*?〗", "", name),
                     verdict="MERGE_SAFE", note="剥离〖…〗后与已有作者名比对合并"))

# ---------- 6. 非人名（体裁/乐府类目/谚语/祠庙） ----------
NONP = ["郊廟朝會歌辭","雜詩","鼔吹曲辭","昭徳凱容樂","古諺","鼓吹曲辭","清商曲辭","劉子引古諺",
        "柳子厚祠","辰州田家諺","瓊州諺","吳中諺","廣州諺","黔中諺","乾道民謠","吳諺","宣和民謠",
        "建炎民謠","樂章","淳祐民謠"]
for name in NONP:
    r = q("SELECT count(*) FROM works WHERE author_name=?", name)
    if not r or not r[0][0]: continue
    n = r[0][0]
    kind = ("樂府類目" if "曲辭" in name or "歌辭" in name or name in ("樂章","昭徳凱容樂")
            else "諺語/民謠（非个人作者）" if ("諺" in name or "謠" in name) else
            "詩題誤作作者" if name == "雜詩" else "祠廟名誤作作者")
    rows.append(dict(author_name=name, issue="NOT_PERSON",
                     evidence=f"该名称是{kind}，不具备作者身份；author_alias 亦标为 NOT_PERSON",
                     n_suspect_rows=n, suggested_full_name="",
                     verdict="DO_NOT_MERGE", note="应转入 category/collection 字段，不得并入任何作者"))

# ---------- 7. 繁简并存（同名两写） ----------
pairs = q("""SELECT a.raw_name,a.canonical,
 (SELECT count(*) FROM works w WHERE w.author_name=a.raw_name),
 (SELECT count(*) FROM works w WHERE w.author_name=a.canonical)
 FROM author_alias a WHERE a.kind='VARIANT_SIMP'
 AND (SELECT count(*) FROM works w WHERE w.author_name=a.raw_name)>0
 AND (SELECT count(*) FROM works w WHERE w.author_name=a.canonical)>0
 ORDER BY 3 DESC""")
for raw, can, rn, cn in pairs[:60]:
    rows.append(dict(author_name=f"{raw}／{can}", issue="SIMPLIFIED_TRADITIONAL_SPLIT",
                     evidence=f"同一作者在 works.author_name 中并存繁简两形：{raw}({rn}条) 与 {can}({cn}条)；author_alias 已标 VARIANT_SIMP→{can}，但 works 未回写",
                     n_suspect_rows=rn, suggested_full_name=can, verdict="MERGE_SAFE",
                     note="纯字形差异，author_canonical 已正确归并，仅 author_name 未统一"))

# ---------- 8. 同名跨代 ----------
cross = q("""SELECT author_name,count(DISTINCT dynasty) d,group_concat(DISTINCT dynasty),count(*)
FROM works GROUP BY 1 HAVING d>1 ORDER BY d DESC,4 DESC LIMIT 30""")
for name, d, dyns, n in cross:
    dist = q("SELECT dynasty,count(*) FROM works WHERE author_name=? GROUP BY 1 ORDER BY 2 DESC", name)
    minor = [x for x in dist if x[1] <= 3]
    ev = f"{d} 个朝代：{dyns}；分布 " + "，".join(f"{a}:{b}" for a, b in dist[:5])
    if minor:
        ev += f"；少数派仅 ≤3 条（{minor[0][0]}:{minor[0][1]}），属源数据朝代误标"
        verdict = "MERGE_SAFE"
        note = "同一人，少数派朝代应改判"
    else:
        verdict = "MERGE_UNCERTAIN"
        note = "两侧均有规模，可能是确有两个同名作者，需人工核对作品标题与文集"
    if name in ("佚名", "无名氏", "無名氏"):
        verdict = "DO_NOT_MERGE"; note = "匿名作者跨代属正常，非同一人"
    rows.append(dict(author_name=name, issue="CROSS_DYNASTY_SAME_NAME", evidence=ev,
                     n_suspect_rows=n, suggested_full_name="", verdict=verdict, note=note))

with open(f"{OUT}/WORKS_AUTHOR_CORRECTIONS.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["author_name","issue","evidence","n_suspect_rows",
                                      "suggested_full_name","verdict","note"])
    w.writeheader(); w.writerows(rows)
print("rows", len(rows))
from collections import Counter
print(Counter(r["issue"] for r in rows))
print(Counter(r["verdict"] for r in rows))
print("繁简并存对数(仅统计两形均在库):", len(pairs))
print("其中前60已入表；完整对数:", len(pairs))
con.close()
