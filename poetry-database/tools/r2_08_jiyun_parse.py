#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 WP-B1：《集韻》韻頁解析——韻目、小韻、反切、字數、字頭。

四庫全書本《集韻》維基文庫轉錄體例：
    二十四○痕〈胡恩切說文胝瘢也文九〉拫艮掀〈博雅拫攎引也或作艮掀〉……
即：〔韻序〕○〔小韻首字〕〈〔反切〕〔釋義〕文〔字數〕〉〔同音字〕〈釋義〉……
- 一個 ○ 開始一個小韻；小韻內每個字（或一組異體字）後接〈…〉釋義。
- 反切與釋義可能被 OCR 拆成多個〈…〉組，故須先把同一小韻的所有括注串接再抽「X切」。
- 「文N」為該小韻收字數（含異體），可用來對帳實際抽到的字頭數。
"""
import json, os, glob, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "raw", "r2_08", "jiyun_pages")
OUT = os.path.join(ROOT, "raw", "r2_08", "jiyun_xiaoyun.jsonl")
STAT = os.path.join(ROOT, "raw", "r2_08", "jiyun_stats.json")

CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
      "百": 100, "零": 0, "〇": 0}


def cn2int(s):
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total, section, num = 0, 0, 0
    for ch in s:
        if ch not in CN:
            return None
        v = CN[ch]
        if v == 100:
            section = (section or 1) * 100
            total += section
            section = 0
        elif v == 10:
            section = (section or 1) * 10
        else:
            num = num * 10 + v if num and v < 10 and False else v
            section += v if v < 10 else 0
    return total + section + num


def cn_number(s):
    """解析中文数字：一百一十四 / 二十四 / 九。"""
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total = 0
    unit = 1
    num = 0
    for ch in s:
        v = CN.get(ch)
        if v is None:
            return None
        if v == 100:
            total += (num or 1) * 100
            num = 0
        elif v == 10:
            total += (num or 1) * 10
            num = 0
        else:
            num = v
    return total + num


TONE_BY_VOL = {"01": "平聲", "02": "平聲", "03": "平聲", "04": "平聲",
               "05": "上聲", "06": "上聲", "07": "去聲", "08": "去聲",
               "09": "入聲", "10": "入聲"}

BR = re.compile(r"[〈(（]([^〈〉()（）]*)[〉)）]")


def clean(text):
    t = text
    t = re.sub(r"^←.*$", "", t, flags=re.M)
    t = re.sub(r"^.*→\s*$", "", t, flags=re.M)
    t = re.sub(r"^集韻\u3000卷.*$", "", t, flags=re.M)
    t = re.sub(r"此作品在全世界都属于公有领域.*$", "", t, flags=re.S)
    t = re.sub(r"Public domain.*$", "", t, flags=re.S)
    return t.strip()


def parse_page(rec):
    title = rec["title"]
    m = re.search(r"/卷(\d\d)/(.+?)第([一二三四五六七八九十百]+)$", title)
    vol = m.group(1) if m else None
    yun_name = m.group(2) if m else None
    yun_no = cn_number(m.group(3)) if m else None
    tone = TONE_BY_VOL.get(vol)
    text = clean(rec.get("text", ""))
    # 去掉首个「韻序○」前的數字前綴
    text = re.sub(r"^[一二三四五六七八九十百]+\s*○", "○", text)
    segs = [s for s in re.split(r"[○〇]", text) if s.strip()]
    out = []
    for k, seg in enumerate(segs):
        seg = seg.strip()
        first = seg.find("〈")
        alt = seg.find("（")
        cand = [x for x in (first, alt) if x >= 0]
        if not cand:
            continue
        head_end = min(cand)
        head = seg[:head_end].strip()
        head = re.sub(r"^[\s\u3000]+", "", head)
        if not head:
            continue
        # 首字：去掉可能的注文；取最後 1–3 個漢字
        head_clean = re.sub(r"[^\u4e00-\u9fff]", "", head)
        head_char = head_clean[0] if head_clean else ""
        notes = [g for g in BR.findall(seg)]
        joined = "".join(notes)
        qie = None
        mq = re.search(r"([\u4e00-\u9fff]{1,2})切", joined)
        if mq:
            qie = mq.group(0)
            qie_up = mq.group(1)[-1] if len(mq.group(1)) == 1 else mq.group(1)[-1]
        else:
            qie_up = None
        mw = re.search(r"文([一二三四五六七八九十百]+)", joined)
        declared = cn_number(mw.group(1)) if mw else None
        # 字頭：每個〈〉前的字（一組可含多字）
        chars = []
        pos = 0
        for mm in BR.finditer(seg):
            between = seg[pos:mm.start()]
            between = re.sub(r"^[\s\u3000，。、]+", "", between)
            cs = re.findall(r"[\u4e00-\u9fff]", between)
            if cs:
                chars.extend(cs[-3:])
            pos = mm.end()
        out.append({
            "title": title, "volume": vol, "tone": tone,
            "yun_no": yun_no, "yun_name": yun_name,
            "seg_index": k, "head_char": head_char, "head_raw": head[:12],
            "fanqie": qie, "fanqie_upper": qie_up,
            "meaning": joined[:400], "declared_chars": declared,
            "n_chars_found": len(chars), "chars": "".join(dict.fromkeys(chars)),
            "qie_in_first_note": bool(re.search(r"切", notes[0] if notes else "")),
        })
    return out


def main():
    rows, bad = [], []
    files = sorted(glob.glob(os.path.join(SRC, "*.json")))
    for f in files:
        rec = json.load(open(f, encoding="utf-8"))
        if rec.get("status") != "OK":
            bad.append({"title": rec["title"], "status": rec.get("status")})
            continue
        rows.extend(parse_page(rec))

    for i, r in enumerate(rows, 1):
        r["xiaoyun_id"] = "JY-%05d" % i
    with open(OUT, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    by_yun = collections.Counter((r["yun_no"], r["yun_name"]) for r in rows)
    n_decl = sum(r["declared_chars"] or 0 for r in rows)
    n_found = sum(r["n_chars_found"] for r in rows)
    stats = {
        "pages_ok": len([1 for f in files if json.load(open(f, encoding='utf-8')).get('status') == 'OK']),
        "pages_total": len(files),
        "pages_failed": bad,
        "n_yun": len(by_yun),
        "n_xiaoyun": len(rows),
        "n_xiaoyun_with_fanqie": sum(1 for r in rows if r["fanqie"]),
        "n_xiaoyun_declared": sum(1 for r in rows if r["declared_chars"]),
        "sum_declared_chars": n_decl,
        "sum_chars_found": n_found,
        "n_unique_head": len({r["head_char"] for r in rows if r["head_char"]}),
        "per_tone": dict(collections.Counter(r["tone"] for r in rows)),
    }
    json.dump(stats, open(STAT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in stats.items() if k != "pages_failed"},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
