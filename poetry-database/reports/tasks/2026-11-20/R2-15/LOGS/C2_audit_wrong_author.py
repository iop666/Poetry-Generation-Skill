#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-15 / C2：WRONG_AUTHOR_FIELD 组内作品逐条审计（作者字段实指什么）。

口径（必须与报告一起读）
------------------------
1. R2-14 的 “1,017 条 WRONG_AUTHOR_FIELD” 是 **组数**，不是作品条数。
   证据：`LOGS/D2_notes.md` L437 表格 “WRONG_AUTHOR_FIELD | 1,017（60.6%）| 40”，
   分母 1,678 组；`AUTHOR_1678_CROSS_AUTHOR_TEXT_AUDIT.csv` 仅 162 行（分层抽样），
   其中 WRONG_AUTHOR_FIELD 40 组 / 84 个 work_id。生成全量分类的脚本未随报告保留。
2. 本脚本按 D2_notes D5.2 的文字定义重建分组：
     组键 = substr(text_s,1,30)；长度>=20；HAVING count(DISTINCT author_canonical)>=2
   复现结果：1,678 组 / 3,418 条（与 R2-14 一致，见 LOGS/C2_stats.json → group_universe）
3. 组级判定顺序（本轮定稿，见 C2_rule.md）：
     ① IMPORT_DUPLICATE：组内 author 含“、”（联句合署）或 于鄴/于武陵 并存
     ② WRONG_AUTHOR_FIELD：同一 collection 内，全同文本 或 同题异文（同题即同作）
     ③ SAME_WORK_MULTI_COLLECTION：跨 collection 且（全同 或 相似度>=0.95）
     ④ SAME_TITLE_DIFF_TEXT：跨 collection、同题、相似度<0.75
     ⑤ VARIANT_TEXT：相似度>=0.75
     ⑥ UNKNOWN：其余
4. 每条作品的 verdict_type 只描述「这个 author 字段现在装的是什么」，不裁决
   组内谁对谁错（库内无别集证据，D2_notes 已明示不可判）。

只读打开，零写入。
"""
import collections
import csv
import difflib
import json
import os
import re
import sqlite3

BASE = "<PROJECT_ROOT>/poetry-database"
DB = os.path.join(BASE, "database", "poetry.db")
OUT = os.path.join(BASE, "reports", "tasks", "2026-11-20", "R2-15")
LOG = os.path.join(OUT, "LOGS")
PREV = os.path.join(BASE, "reports", "tasks", "2026-11-16", "R2-14")

ANON = {"佚名", "无名氏", "無名氏", "不詳", "不详", "缺名", "闕名", "阙名",
        "失名", "無名", "无名", "佚名氏", "無考", "无考"}
COLLECTION_NAMES = {
    "郊廟朝會歌辭", "雜詩", "鼔吹曲辭", "昭徳凱容樂", "鼓吹曲辭", "月重輪行",
    "清商曲辭", "出郊抵東屯", "斋中读书", "歸田雜詠", "紫騮馬歌", "秋日雜詠",
    "自君之出矣", "舟中夜坐", "長安雜詩", "北征雜詠", "田家杂诗", "和陶飲酒",
    "还乡杂诗", "山中雜詠", "春日杂诗", "嶺南雜詠", "榕堂雜詩", "舟中雜詠",
    "秣陵雜詠", "樂章", "暮雨谣三叠", "清江道中", "西湖竹枝詞", "鼓吹曲辞",
}
COMPOUND_SURNAMES = ("司馬", "司徒", "司空", "上官", "歐陽", "欧阳", "諸葛", "诸葛",
                     "皇甫", "令狐", "慕容", "尉遲", "尉迟", "長孫", "长孙", "宇文",
                     "夏侯", "公孫", "公孙", "東方", "东方", "南宮", "南宫", "獨孤",
                     "独孤", "申屠", "呼延", "端木", "百里", "東郭", "东郭", "西門",
                     "西门", "第五", "万俟", "赫連", "赫连")
OFFICE = ("祕書", "秘书", "侍郎", "尚書", "尚书", "員外", "员外", "太守", "刺史",
          "居士", "山人", "先生", "道人", "上人", "禪師", "禅师", "法師", "法师",
          "和尚", "秀才", "處士", "处士", "布衣", "參軍", "参军", "司馬", "司马",
          "別駕", "别驾", "郡守", "明府", "主簿", "縣令", "县令", "丞相", "相公",
          "待制", "學士", "学士", "修撰", "編修", "编修", "給事", "给事", "中書",
          "中书", "舍人", "皇后", "皇帝", "太子", "夫人", "公主", "節度", "节度",
          "觀察", "观察", "轉運", "转运", "提舉", "提举", "知州", "知府", "通判",
          "教授", "大夫", "郎中", "拾遺", "拾遗", "補闕", "补阙", "校書", "校书",
          "正字", "太祝", "協律", "协律", "供奉", "內侍", "内侍", "貴妃", "贵妃",
          "昭儀", "昭仪", "婕妤", "才人", "美人", "郡主", "縣主", "县主", "太君",
          "孺人", "安人", "宜人", "淑人", "恭人", "令人", "碩人", "硕人")
ROLE = ("編", "编", "輯", "辑", "校", "注", "撰", "纂", "評", "评", "點", "点",
        "箋", "笺")
MONK = ("釋", "释", "僧")
OFFICE_RE = re.compile("(" + "|".join(sorted(OFFICE, key=len, reverse=True)) + ")")
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002ffff]")


def load_collection_names():
    names = set(COLLECTION_NAMES)
    p = os.path.join(PREV, "AUTHOR_73_NAME_COUNT_RECONCILIATION.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8-sig")):
            if r["classification"] == "COLLECTION":
                names.add(r["author_name"])
    return names


def build_groups(con):
    q = """SELECT substr(text_s,1,30) t FROM works
           WHERE length(substr(text_s,1,30))>=20
           GROUP BY t HAVING count(DISTINCT author_canonical)>=2"""
    keys = [r[0] for r in con.execute(q)]
    cur = con.execute("""SELECT substr(text_s,1,30) t, work_id, title_raw, author_name,
                                author_canonical, collection, dynasty, text_norm, cipai
                         FROM works WHERE length(substr(text_s,1,30))>=20""")
    by = collections.defaultdict(list)
    for r in cur:
        by[r[0]].append(r)
    return [(k, by[k]) for k in keys]


def classify_group(members):
    names = {m[3] for m in members}
    ident = len({m[7] for m in members}) == 1
    same_coll = len({m[5] for m in members}) == 1
    same_title = len({m[2] for m in members}) == 1
    if any("、" in n for n in names) or {"于鄴", "于邺", "于武陵"} <= names:
        return "IMPORT_DUPLICATE", "CO_SIGNED_OR_KNOWN_ALIAS", ident, same_coll, 1.0
    # 非人名署名（郊廟朝會歌辭等）在 D5.2 里也归 WAField，此处单列以便统计口径
    if names & NONPERSON:
        return "WRONG_AUTHOR_FIELD", "AUTHOR_IS_NONPERSON", ident, same_coll, 1.0
    r = 1.0
    if not ident:
        r = max(difflib.SequenceMatcher(None, a[7], b[7]).ratio()
                for i, a in enumerate(members) for b in members[i + 1:])
    if same_coll and (ident or same_title):
        return "WRONG_AUTHOR_FIELD", ("SAME_COLL_SAME_TEXT" if ident
                                      else "SAME_COLL_SAME_TITLE"), ident, same_coll, r
    if (not same_coll) and (ident or r >= 0.95):
        return "SAME_WORK_MULTI_COLLECTION", ("CROSS_COLL_SAME_TEXT" if ident
                                              else "CROSS_COLL_NEAR_IDENTICAL"), ident, same_coll, r
    if (not same_coll) and same_title and r < 0.75:
        return "SAME_TITLE_DIFF_TEXT", "CROSS_COLL_SAME_TITLE_LOW_SIM", ident, same_coll, r
    if r >= 0.75:
        return "VARIANT_TEXT", "SIM>=0.75", ident, same_coll, r
    return "UNKNOWN", "UNCLASSIFIED", ident, same_coll, r


def judge(name, row_cipai, alias_map, coll_names, cipai_set):
    """(verdict_type, evidence, candidate_fix, confidence, note)"""
    if name in ANON:
        return ("UNKNOWN", "匿名占位符（ANONYMOUS）：本身不是作者，但不属字段污染", "",
                "UNKNOWN", "placeholder=ANONYMOUS")
    canon, kind = alias_map.get(name, ("", ""))
    if kind == "NOT_PERSON" or name in coll_names:
        src = "author_alias.kind=NOT_PERSON" if kind == "NOT_PERSON" else "类目词表命中"
        return ("COLLECTION_NAME", f"{src}：{name} 为总集/乐府类目名", "佚名", "HIGH",
                "应迁 collection_role；这是本组同文异署的结构性根因")
    if "《" in name:
        person = name.split("《")[0].strip()
        return ("TITLE_POLLUTION", f"author 含书名号，人名与剧名黏连：{name}", person,
                "HIGH", f"拆为 author={person} / 作品名={name[len(person):]}")
    if kind == "STYLE_NAME" and canon and canon != name:
        return ("ALIAS", f"author 为字号/谥称，canonical={canon}", canon, "HIGH",
                "字号非本名，别名表已给出本名")
    if kind in ("TEMPLE_NAME",) and canon and canon != name:
        return ("HONORIFIC", f"author 为庙号/尊号，canonical={canon}", canon, "HIGH",
                "庙号应换本名")
    if kind == "VARIANT_GLYPH" and canon and canon != name:
        return ("ALIAS", f"author 为异体字写法，canonical={canon}", canon, "HIGH",
                "仅字形差异")
    if name in cipai_set and name == row_cipai:
        return ("WRONG_FIELD", f"author 与本条 cipai 完全相同：{name}", "", "HIGH",
                "author 取自词牌/曲牌字段")
    if name in cipai_set and len(name) >= 3:
        return ("WRONG_FIELD", f"author 命中词牌/曲牌词表：{name}", "", "MEDIUM",
                "疑似字段串位到词牌")
    if name[0] in MONK and len(name) >= 3:
        core = name[1:]
        return ("ALIAS", f"author 带僧侣身份前缀“{name[0]}”：{name} → {core}", core,
                "MEDIUM", "释/僧前缀非本名一部分，属同一人的异写")
    if len(name) >= 3 and name[-1] in "曲歌行吟詞词" and name in titles:
        return ("WRONG_FIELD", f"author 为乐府/词牌题名（库内亦作标题）：{name}", "",
                "MEDIUM", "author 取自作品题名而非作者")
    if (len(name) >= 4 and name[-1] in ROLE
            and not any(s in name for s in COMPOUND_SURNAMES)):
        core = name[:-1]
        if 1 <= len(core) <= 5:
            return ("WRONG_FIELD", f"author 混入编纂/校注角色词：{name}", core, "MEDIUM",
                    "角色词不属于署名本身")
    if OFFICE_RE.search(name) and not any(name.startswith(s) for s in COMPOUND_SURNAMES):
        core = OFFICE_RE.sub("", name)
        if "夫人" in name and 2 <= len(name.rsplit("夫人", 1)[1]) <= 3:
            tail = name.rsplit("夫人", 1)[1]
            return ("HONORIFIC", f"author 为封号+本名：{name} → 本名 {tail}", tail,
                    "MEDIUM", "封号“夫人”非本名")
        if 2 <= len(core) <= 5 and core != name:
            return ("HONORIFIC", f"author 含官称/尊称：{name} → 去官称得 {core}", core,
                    "MEDIUM", "官称非本名，需别集确认；不得据此改库")
        if "夫人" in name and 1 <= len(name.rsplit("夫人", 1)[1]) <= 3:
            return ("HONORIFIC", f"author 为封号+本名：{name} → 本名 {name.rsplit('夫人',1)[1]}",
                    name.rsplit("夫人", 1)[1], "MEDIUM", "封号“夫人”非本名")
        if len(core) > 5:
            tail = OFFICE_RE.split(name)[-1]
            if 1 <= len(tail) <= 4:
                return ("HONORIFIC", f"author 为尊称+本名：{name} → 本名 {tail}", tail,
                        "MEDIUM", "尊称剥离后取尾段本名")
        return ("HONORIFIC", f"author 含官称/尊称：{name}", "", "LOW", "无法唯一还原本名")
    if len(name) > 6:
        return ("WRONG_FIELD", f"author 长度 {len(name)} 字，非规范人名：{name}", "",
                "MEDIUM", "疑似取自题注/序")
    if re.search(r"(年|月|日|卷|第)$", name) and len(name) >= 3:
        return ("WRONG_FIELD", f"author 形如年份/卷次/题注：{name}", "", "LOW", "疑似串位")
    if 2 <= len(name) <= 5 and CJK.match(name[0]):
        return ("PERSON", f"author 是规范人名（{len(name)} 字；非类目/官称/书名/词牌）",
                name, "MEDIUM", "字段本身是人名；组级谁对谁错库内不可判")
    return ("UNKNOWN", f"author 值异常（{name}）", "", "UNKNOWN", "需调图/别集")


def main():
    os.makedirs(LOG, exist_ok=True)
    con = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
    coll_names = load_collection_names()
    alias_map = {r[0]: (r[1], r[2]) for r in
                 con.execute("SELECT raw_name, canonical, kind FROM author_alias")}
    cipai_set = {r[0] for r in con.execute("SELECT DISTINCT cipai FROM works WHERE cipai<>''")}
    global titles, NONPERSON
    titles = {r[0] for r in con.execute("SELECT DISTINCT title_raw FROM works")}
    NONPERSON = {r[0] for r in con.execute("SELECT raw_name FROM author_alias WHERE kind='NOT_PERSON'")}

    groups = build_groups(con)
    gstats = collections.Counter()
    stats = collections.Counter()
    group_rows, work_rows = [], []

    for gi, (key, members) in enumerate(groups, 1):
        verdict, why, ident, same_coll, ratio = classify_group(members)
        gid = f"WA-{gi:04d}"
        gstats[verdict] += 1
        group_rows.append({
            "group_id": gid, "group_key30": key, "n_members": len(members),
            "work_ids": ";".join(m[1] for m in members),
            "authors": ";".join(m[3] for m in members),
            "collections": ";".join(m[5] for m in members),
            "same_collection": "Y" if same_coll else "N",
            "text_identical": "Y" if ident else "N",
            "max_pair_ratio": f"{ratio:.3f}",
            "group_verdict": verdict, "group_rule": why,
        })
        if verdict != "WRONG_AUTHOR_FIELD":
            continue
        for m in members:
            vt, ev, fix, conf, note = judge(m[3], m[8], alias_map, coll_names, cipai_set)
            stats[(vt, conf)] += 1
            work_rows.append({
                "work_id": m[1], "author_name": m[3], "title_raw": m[2],
                "collection": m[5], "dynasty": m[6],
                "verdict_type": vt, "evidence": ev, "candidate_fix": fix,
                "confidence": conf,
                "note": f"{note}｜{gid}｜{why}",
                "group_id": gid,
            })

    prev_csv = os.path.join(PREV, "AUTHOR_1678_CROSS_AUTHOR_TEXT_AUDIT.csv")
    prev_rows = list(csv.DictReader(open(prev_csv, encoding="utf-8-sig")))
    prev_wrong = [r for r in prev_rows if r["verdict"] == "WRONG_AUTHOR_FIELD"]
    prev_ids = {w for r in prev_wrong for w in r["work_ids"].split(";")}
    mine_ids = {r["work_id"] for r in work_rows}
    recon = {
        "group_universe_reproduced": len(groups),
        "works_in_universe": sum(len(m) for _, m in groups),
        "r2_14_group_universe": 1678,
        "r2_14_group_distribution": {"WRONG_AUTHOR_FIELD": 1017, "VARIANT_TEXT": 436,
                                     "SAME_WORK_MULTI_COLLECTION": 183,
                                     "IMPORT_DUPLICATE": 26, "UNKNOWN": 11,
                                     "SAME_TITLE_DIFF_TEXT": 5},
        "mine_group_distribution": dict(gstats),
        "wrong_author_field_groups": gstats["WRONG_AUTHOR_FIELD"],
        "wrong_author_field_groups_vs_1017": gstats["WRONG_AUTHOR_FIELD"] - 1017,
        "wrong_author_field_works": len(work_rows),
        "prev_sample_rows": len(prev_rows),
        "prev_wrong_groups": len(prev_wrong),
        "prev_wrong_works": len(prev_ids),
        "overlap_works_with_prev_sample": len(prev_ids & mine_ids),
        "prev_works_missing_from_mine": sorted(prev_ids - mine_ids),
    }

    # ---- 全库口径补充：1,678 组 / 3,418 条里作者字段的污染面（不限组判定） ----
    universe_rows = []
    for key, members in groups:
        for m in members:
            vt, ev, fix, conf, note = judge(m[3], m[8], alias_map, coll_names, cipai_set)
            if vt in ("COLLECTION_NAME", "TITLE_POLLUTION", "WRONG_FIELD", "HONORIFIC", "ALIAS"):
                universe_rows.append({
                    "work_id": m[1], "author_name": m[3], "title_raw": m[2],
                    "collection": m[5], "dynasty": m[6], "verdict_type": vt,
                    "evidence": ev, "candidate_fix": fix, "confidence": conf,
                    "note": note})
    with open(os.path.join(OUT, "AUTHOR_FIELD_POLLUTION_UNIVERSE.csv"), "w",
              encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["work_id", "author_name", "title_raw",
                                          "collection", "dynasty", "verdict_type",
                                          "evidence", "candidate_fix", "confidence", "note"])
        w.writeheader()
        w.writerows(universe_rows)

    cols = ["work_id", "author_name", "title_raw", "collection", "dynasty",
            "verdict_type", "evidence", "candidate_fix", "confidence", "note", "group_id"]
    with open(os.path.join(OUT, "AUTHOR_WRONG_FIELD_1017.csv"), "w",
              encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(work_rows)

    with open(os.path.join(OUT, "AUTHOR_WRONG_FIELD_GROUPS.csv"), "w",
              encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(group_rows[0].keys()))
        w.writeheader()
        w.writerows(group_rows)

    json.dump({"recon": recon,
               "verdict_type_works": dict(collections.Counter(r["verdict_type"] for r in work_rows)),
               "confidence_works": dict(collections.Counter(r["confidence"] for r in work_rows)),
               "verdict_x_conf": {f"{k[0]}|{k[1]}": v for k, v in stats.items()},
               "by_collection": dict(collections.Counter(r["collection"] for r in work_rows)),
               "distinct_authors": len({r["author_name"] for r in work_rows}),
               "universe_pollution_rows": len(universe_rows),
               "universe_pollution_by_type": dict(collections.Counter(
                   r["verdict_type"] for r in universe_rows)),
               "universe_pollution_top_authors": collections.Counter(
                   r["author_name"] for r in universe_rows).most_common(15)},
              open(os.path.join(LOG, "C2_stats.json"), "w"), ensure_ascii=False, indent=2)
    print(json.dumps({"recon": recon,
                      "verdict": dict(collections.Counter(r["verdict_type"] for r in work_rows)),
                      "conf": dict(collections.Counter(r["confidence"] for r in work_rows))},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
