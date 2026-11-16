#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E1+E2 最终：339 条污染分类 + 可回滚正文重建建议。只读库，输出两份 CSV。"""
import sqlite3, re, difflib, json, csv, os
from collections import Counter

ROOT = "<PROJECT_ROOT>/poetry-database"
DB = f"{ROOT}/database/poetry.db"
OUT = f"{ROOT}/reports/tasks/2026-11-16/R2-12"
PUNCT = r"[\s\u3000，。！？、；：“”‘’（）()《》〈〉「」『』【】〖〗…—\-,.;:!?\"'·～~]"
BR = r"[（）()「」『』]"
def norm0(s): return re.sub(PUNCT, "", s or "")
def strip_br(s): return re.sub(BR, "", s or "")

# 括号内含「一作」的整段；允许跨行
RE_NOTE = re.compile(r"[（(][^（）()]{0,20}?一作[^（）()]{0,60}?[）)]", re.S)
# 其他校记（校/案/一本作/集作/或作/京本作…）
RE_NOTE2 = re.compile(r"[（(][^（）()]{0,14}?(?:校|案|一本作|集作|或作|京本作|項校|通：)[^（）()]{0,60}?[）)]", re.S)
# 尖括号 ref
RE_REF = re.compile(r"<ref>.*?</ref>", re.S)
# 注内拆分：HEAD + 一作 + VAR
RE_SPLIT = re.compile(r"^(?:[（(])\s*(.*?)\s*一作\s*[：:]?\s*(.*?)\s*(?:[）)])$", re.S)
RE_SPLIT_NOHEAD = re.compile(r"^(?:[（(])\s*一作\s*[「『\"]?\s*(.*?)\s*[」』\"]?\s*(?:[）)])$", re.S)

EXPECT = {"五言绝句": 20, "七言绝句": 28, "五言律诗": 40, "七言律诗": 56,
          "五言排律": None, "七言排律": None, "古体诗": None, "词": None, "曲": None,
          "四言诗": None, "楚辞": None, "未定": None}

def parse_spans(raw):
    """返回 note 列表：dict(start,end,text,head,variant)"""
    cand = [(m.start(), m.end(), m.group(0)) for m in RE_NOTE.finditer(raw)]
    for m in RE_NOTE2.finditer(raw):
        if not any(s <= m.start() < e for s, e, _ in cand):
            cand.append((m.start(), m.end(), m.group(0)))
    cand.sort()
    notes = []
    for s, e, txt in cand:
        head, var, parsed = "", "", False
        m = RE_SPLIT_NOHEAD.match(txt)
        if m:
            var = m.group(1); parsed = True
        else:
            m = RE_SPLIT.match(txt)
            if m:
                inner = m.group(1); var = m.group(2)
                if "一作" in inner:
                    k = inner.split("一作")
                    head, var = k[0].strip(), (k[1].lstrip("：: ").strip() + var).strip()
                parsed = True
        notes.append(dict(start=s, end=e, text=txt, head=head.strip(), variant=var.strip(), parsed=parsed))
    return notes

def build_body(raw, notes):
    """把注段替换为注头（若注头为正文词），否则删除。"""
    out, last = [], 0
    for n in notes:
        out.append(raw[last:n["start"]])
        last = n["end"]
    out.append(raw[last:])
    return "".join(out)

# 人工判定的「括号外一作」条目：work_id -> (classification, evidence, 是否正文用词)
BARE_BODY = {
 "tang:4eb85ca81970":"首句「一作邊城客」为五言句（一作=曾作），norm 保留正确",
 "tang:58b1b5953427":"首句「一作江南守」为五言句（一作=曾作），norm 保留正确",
 "tang:59ff2e94e4dd":"首句「一作雲峰別」为五言句，norm 保留正确",
 "tang:83d0d782f83b":"諺語「一作一止」属原文（一作一止=一动一静），norm 保留正确",
 "songshi:00d08b2f940d":"首句「一作閩南客」五言，norm 保留正确",
 "songshi:0a6f92f05cdf":"首句「一作城頭飲」五言，norm 保留正确",
 "songshi:2dff131bdf1b":"首句「一作劍關客」五言，norm 保留正确",
 "songshi:b0dedc13c731":"首句「一作淮南守」五言，norm 保留正确",
 "songshi:d934ac96f58a":"首句「一作重山去」五言，norm 保留正确",
 "songshi:e0c693072a11":"首句「一作東吳去」五言，norm 保留正确",
 "songshi:f959e7297aa4":"首句「一作班荆别」五言，norm 保留正确",
 # —— 以下为正文用词但 norm 已删，造成正文丢字
 "tang:256516182ce3":"七绝「一作迷津一拜侯」为正文（一作=竟作），norm 误删「一作迷津」4字致首句残「江南江北兩風流，一拜侯」",
 "tang:28a269570008":"五排「一作芸香吏，三見牡丹開」为正文，norm 误删「一作芸香」",
 "tang:cb582f199cd4":"「仲宣一作從軍詠」用王粲從軍典故，属正文，norm 误删「一作從軍」",
 "tang:de7dcc17d6fa":"五律「一作南行客，無成空白頭」为正文，norm 误删「一作南行」",
 "songshi:04232b0c20e0":"七绝「如何一一作詩謀」为正文，norm 误删「一作詩謀」",
 "songshi:089ff9239410":"七古「狂風一作浪如屋」为正文，norm 误删「一作浪如」致句残「狂風屋」",
 "songshi:0da6b86516a7":"「墨指一作何紛綸」为正文，norm 误删「一作何紛」",
 "songshi:350defe63674":"五排对句「一爲涸轍魚，一作秋空鵠」为正文，norm 误删「一作秋空」",
 "songshi:3db1b0bd5b5a":"七律「一作同胞疾痛觀」为正文，norm 误删「一作同胞」",
 "songshi:642a70e6e494":"七律「相看一作秦吳別」为正文，norm 误删「一作秦吳」",
 "songshi:69d57c321b87":"五律「一作邗溝別」为正文，norm 误删「一作邗溝」",
 "songshi:7d904605b607":"「此古一作無窮時」为正文，norm 误删「一作無窮」",
 "songshi:80e17d05fd7b":"「俗子一作吏」为正文，norm 误删「一作吏書」",
 "songshi:90ef2dd4860a":"「鋪排短韻一作戲」为正文，norm 误删「一作戲爲」",
 "songshi:912f4f03b0bd":"「油然一作施膏澤」为正文，norm 误删「一作施膏」",
 "songshi:966b33472465":"「故交一作霜葉散」为正文，norm 误删「一作霜葉」",
 "songshi:9d56506aa8d3":"「管商一作俑」用始作俑典，属正文，norm 误删「一作俑蠹」",
 "songshi:ab78f7a85438":"「向人一一作西飛」为正文，norm 误删「一作西飛」",
 "songshi:aca6afb8f337":"「一作市朝人」为正文，norm 误删「一作市朝」",
 "songshi:ad8c1f48c6fd":"对句「一隱盧老堂，一作貧舍兒」为正文，norm 误删「一作貧舍」",
 "songshi:b689448408a2":"禅偈「畢竟一作麽生識」为正文，norm 误删「一作麽生」",
 "songshi:bb0cca861123":"「溪流一作神仙遇」为正文，norm 误删「一作神仙」",
 "songshi:be01c815da8f":"同 tang:cb582f199cd4 重出，「仲宣一作從軍詠」为正文",
 "songshi:cb658dabbd5d":"「一一作利益」对「一一興供養」，属正文，norm 误删「一作利益」",
 "songshi:dfb02508e55f":"「桐皮一作饑腸飽」为正文，norm 误删「一作饑腸」",
 "songshi:f4d04e5fe6de":"五律「一作山頭石，畏看天際途」为正文，norm 误删「一作山頭」",
 "wanqing:3fedb524017f":"「鸡声一作，天地清廓」句中一作=一振，属正文，norm 误删「一作天地」",
 "wanqing:d0a5e2a10f10":"「岁暮例一作」为正文，norm 误删「一作我诗」",
 "wanqing:e193c564b8e4":"「万物尽一作并」为正文，norm 误删「一作并遭」",
 "wanqing:f80067444b0d":"「天阴一作老蛟吼」为正文，norm 误删「一作老蛟」",
 "wanqing:fd2ee4262cb2":"「一作入赘婿」为正文，norm 误删「一作入赘」",
 "tao:1c92e02b8348":"正文后 <ref>曾本云，一作樹木殘根株。</ref> 为校勘标签，norm 误删 ref 内「一作樹木」并遗留标签残迹",
}
BARE_EDITORIAL = {
 "tang:1e1701929a42":"按語「《全唐詩》卷八百六十一作李夢符詩」为编者考證，非诗句",
 "tang:35d608c1007a":"「〖一作「園」〗」为校勘夹注，norm 剥离夹注符后残留异常",
 "tang:3c46ca38064c":"「〖從一作〗」为著录夹注（書目信息），非诗句",
 "tang:4839cf43d903":"「另注『一作蜀臣王承旨詩』」为按語引用，非正文",
 "tang:5c0342816adb":"「校文中均以『一作某』代指該卷」为校例說明，非正文",
 "tang:68a5ef0006b7":"「《全唐詩》一二一作楊炎詩」为互見按語",
 "tang:e29505f67f2b":"「異文注出『一作某』」为校例說明；本条整段为王梵志詩校錄前言",
 "tang:efbe91a28fc3":"「按這一首，《全唐詩》卷三一作爲魏徵的詩」为按語",
 "songshi:220f644c6997":"題注「詩題：原無題首句：…一作蜀國佳人號細腰」为存目著录，非诗",
 "gushiji:ab37b3addbc0":"「蕭索字一作蕭瑟」为梁武帝詩考释文字，非本條正文",
 "tao:1c92e02b8348":"见 BARE_BODY（同为 <ref> 校勘标签）",
}

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); con.text_factory = str
rows = con.execute("""SELECT work_id,title_raw,title_norm,author_name,dynasty,genre,text_raw,text_norm,char_count
FROM works WHERE text_raw LIKE '%一作%' ORDER BY dynasty, work_id""").fetchall()

audit, revis = [], []
for wid, t1, t2, au, dy, ge, raw, nm, cc in rows:
    raw, nm = raw or "", nm or ""
    notes = parse_spans(raw)
    body = build_body(raw, notes)
    sug = norm0(strip_br(body))
    sm = difflib.SequenceMatcher(None, sug, nm, autojunk=False)
    extra, missing = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("insert", "replace") and nm[j1:j2]: extra.append(nm[j1:j2])
        if tag in ("delete", "replace") and sug[i1:i2]: missing.append(sug[i1:i2])
    bare = [m.start() for m in re.finditer("一作", raw) if not any(n["start"] <= m.start() < n["end"] for n in notes)]

    # ---------- 分类 ----------
    has_var_note = any(n["variant"] for n in notes)
    if not notes and not bare:
        cls, ev, conf = "UNCLASSIFIED", "text_raw 含一作但未定位到任何出现位置", "LOW"
    elif not notes:
        if wid in BARE_BODY:
            if wid == "tao:1c92e02b8348":
                cls, ev, conf = "EDITORIAL_NOTE", BARE_BODY[wid], "HIGH"
            else:
                cls, ev, conf = "POEM_BODY", BARE_BODY[wid], "HIGH"
                if missing: conf = "HIGH"
        elif wid in BARE_EDITORIAL:
            cls, ev, conf = "EDITORIAL_NOTE", BARE_EDITORIAL[wid], "HIGH"
        else:
            cls, ev, conf = "UNCLASSIFIED", "括号外一作，未能判定", "LOW"
    else:
        # 有括号校记
        glue = bool(extra)
        loss = bool(missing)
        if glue and not loss:
            cls = "MIXED_BODY_AND_NOTE"
            ev = f"校记注头被吸附入正文：norm 多出 {extra}；原文校记 {notes[0]['text']!r}"
            conf = "HIGH"
        elif glue and loss:
            cls = "MIXED_BODY_AND_NOTE"
            ev = f"注头吸附 {extra} 且正文丢字 {missing}；原文校记 {notes[0]['text']!r}"
            conf = "MEDIUM"
        elif loss and not glue:
            cls = "EDITORIAL_NOTE"
            ev = f"校记已剥离但连带删去正文字 {missing[:3]}；原文校记 {notes[0]['text']!r}"
            conf = "MEDIUM"
        else:
            cls = "VARIANT_NOTE" if has_var_note else "EDITORIAL_NOTE"
            ev = f"校记 {notes[0]['text']!r} 已完整剥离，norm 无残留污染"
            conf = "HIGH"

    # 括号外 + 括号注并存：以括号注性质为主，附注说明
    if notes and bare:
        cls = "MIXED_BODY_AND_NOTE" if cls == "MIXED_BODY_AND_NOTE" else cls
        ev += f"；另有括号外「一作」{len(bare)} 处（疑正文用词）"

    n0 = notes[0] if notes else None
    ctx_src = nm if "一作" in nm else raw
    i = ctx_src.find("一作") if "一作" in ctx_src else 0
    ctx = ctx_src[max(0, i - 30):i + 32].replace("\n", "/") if i >= 0 else raw[:62].replace("\n", "/")

    ev += f"（norm {len(nm)} 字 → 重建正文 {len(sug)} 字）"
    audit.append(dict(work_id=wid, title=t2 or t1, author_name=au, dynasty=dy,
                      raw_len=len(raw), norm_len=len(nm), char_count=cc,
                      marker_type="+".join([m for m in ("一作","一本作","某本作","集作","或作","校改","項校","案") if m in raw]
                                          + (["括号外一作"] if bare else [])),
                      marker_context=ctx, classification=cls, evidence=ev, confidence=conf))

    # ---------- 重建建议 ----------
    if cls in ("MIXED_BODY_AND_NOTE", "EDITORIAL_NOTE", "VARIANT_NOTE") or (cls == "POEM_BODY" and missing):
        removed = [n["text"] for n in notes] + (["（正文被误删：%s）" % "".join(missing)] if cls == "POEM_BODY" else [])
        # 正文重建：POEM_BODY 类取 sug（已含一作），其余取 sug
        # 置信度：括号配平 + 注全部解析 + 行长规整度校验
        balanced = (raw.count("（") + raw.count("(")) == (raw.count("）") + raw.count(")"))
        parsed_all = all(n["parsed"] for n in notes) and bool(notes)
        segs = [norm0(x) for x in re.split(r"[，。！？；、\n]", body) if norm0(x)]
        meter_ok, modal, cnt = False, 0, 0
        if segs:
            c = Counter(len(x) for x in segs)
            modal, cnt = c.most_common(1)[0]
            meter_ok = cnt / len(segs) >= 0.75 and modal <= 9
        expect = EXPECT.get(ge)
        head_chars = sum(len(n["head"]) for n in notes)
        exact_head = (len(nm) - len(sug) == head_chars)
        note_charset = set("".join(n["text"] for n in notes))
        extra_from_notes = bool(extra) and all(set(e) <= note_charset for e in extra)
        if expect and len(sug) == expect:
            rc = "HIGH"
        elif not balanced or not parsed_all:
            rc = "LOW"
        elif exact_head or extra_from_notes or (meter_ok and modal >= 4 and modal <= 7):
            rc = "HIGH"
        elif balanced and parsed_all:
            rc = "MEDIUM"
        else:
            rc = "LOW"

        reason = (f"{cls}：删除校记 {len(notes)} 处" +
                  (f"，归位注头 {[n['head'] for n in notes if n['head']]}" if any(n["head"] for n in notes) else "") +
                  (f"；并回补被误删正文字「{''.join(missing)}」" if cls == "POEM_BODY" else "") +
                  f"；重建后 {len(sug)} 字（原 norm {len(nm)} 字）")
        revis.append(dict(work_id=wid, title=t2 or t1, old_text_norm=nm, suggested_text_body=sug,
                          removed_segments=" | ".join(removed) or "（无，纯正文补回）",
                          source_text=(" | ".join(n["text"] for n in notes) or "（无括号，正文缺失段：%s）" % "".join(missing)),
                          change_reason=reason, confidence=rc, applied="NO"))

print("分类分布:", Counter(a["classification"] for a in audit))
print("审计置信度:", Counter(a["confidence"] for a in audit))
print("重建条数:", len(revis), "重建置信:", Counter(r["confidence"] for r in revis))

with open(f"{OUT}/WORKS_TEXT_POLLUTION_339_AUDIT.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["work_id","title","author_name","dynasty","raw_len","norm_len","char_count",
                                      "marker_type","marker_context","classification","evidence","confidence"])
    w.writeheader(); w.writerows(audit)
with open(f"{OUT}/WORKS_TEXT_REVISIONS_R2_12.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["work_id","title","old_text_norm","suggested_text_body","removed_segments",
                                      "source_text","change_reason","confidence","applied"])
    w.writeheader(); w.writerows(revis)
json.dump(dict(audit=audit, revis=revis), open(f"{OUT}/LOGS/_e1_final.json","w"), ensure_ascii=False, indent=1)
con.close()
