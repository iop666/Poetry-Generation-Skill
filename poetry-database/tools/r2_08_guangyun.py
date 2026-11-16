#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 WP-B2：《廣韻》結構化審計（四庫全書本維基文庫轉錄，5 卷）。

來源限制（已核實）
- 卷端有完整「韻目總表」（每行兩韻，附同用／獨用），可直接解析 206 韻。
- 正文中只有部分韻保留韻目行：卷1 16/28、卷2 16/29、卷3 30/55、卷4 30/60、卷5 19/34，
  合 111 韻有韻目行。其餘韻目行在轉錄中被省略（來源缺陷）。
- 因此韻歸屬採三級判定，並在欄位中標明依據：
    HEADER          正文韻目行直接給出（由 ptr 前移）
    YUNMU_HEAD      該韻首小韻的韻目字作為字頭出現（广韵通例，屬工程推定）
    CARRIED_FORWARD 沿用上一個已判定之韻（無更強線索時使用，標為不可靠）
"""
import json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "raw", "books", "guangyun")
OUT_Y = os.path.join(ROOT, "raw", "r2_08", "guangyun_yunmu.json")
OUT_X = os.path.join(ROOT, "raw", "r2_08", "guangyun_xiaoyun.jsonl")
OUT_A = os.path.join(ROOT, "raw", "r2_08", "guangyun_audit.json")

CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "百": 100}
VOL_TONE = {1: "上平聲", 2: "下平聲", 3: "上聲", 4: "去聲", 5: "入聲"}
HEAD_LINE = re.compile(r"^[\s\u3000]*([一二三四五六七八九十百]+)([^\s\u3000〈〉]{1,3})〈([^〉]{1,8})〉[\s\u3000]*$")
YUNMU_ITEM = re.compile(r"([一二三四五六七八九十百]+)([^\s\u3000〈〉]{1,2})(?:〈([^〉]{1,8})〉)?")
ENTRY_RE = re.compile(r"([\u4e00-\u9fff□�]{1,3})〈([^〈〉]{0,800}?)〉")


def cn_number(s):
    total, num = 0, 0
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


def parse_yunmu(header_lines):
    out = []
    for line in header_lines:
        for m in YUNMU_ITEM.finditer(line):
            no = cn_number(m.group(1))
            name = m.group(2)
            if no is None or not (1 <= no <= 60) or len(name) != 1:
                continue
            out.append({"yun_no": no, "yun_name": name, "label": (m.group(3) or "").strip()})
    seen, uniq = set(), []
    for y in out:
        if y["yun_no"] in seen:
            continue
        seen.add(y["yun_no"])
        uniq.append(y)
    return uniq


def main():
    yunmu, xiaoyun, audit = [], [], {"volumes": {}, "issues": []}
    for vol in range(1, 6):
        text = open(os.path.join(SRC, "卷%d.wikitext" % vol), encoding="utf-8").read()
        lines = text.split("\n")
        i0 = next((i for i, l in enumerate(lines) if "切" in l), 0)
        yl = parse_yunmu(lines[:i0])
        for y in yl:
            y.update({"volume": vol, "tone": VOL_TONE[vol],
                      "tongyong": ("獨用" not in y["label"])})
            yunmu.append(y)
        ptr = -1
        set_by = None
        ent = []
        for line in lines[max(0, i0 - 5):]:
            hm = HEAD_LINE.match(line)
            if hm:
                no = cn_number(hm.group(1))
                idx = next((k for k, y in enumerate(yl) if y["yun_no"] == no), None)
                if idx is not None:
                    ptr = idx
                    set_by = "HEADER"
                    continue
            for e in ENTRY_RE.finditer(line):
                chars, note = e.group(1), e.group(2)
                if not note:
                    continue
                mq = re.search(r"([\u4e00-\u9fff]{1,2})切", note)
                mt = re.search(r"([一二三四五六七八九十百]+)$", note.strip())
                meth = "CARRIED_FORWARD"
                hd = chars[0]
                if ptr + 1 < len(yl) and hd == yl[ptr + 1]["yun_name"] and (mq or mt):
                    ptr += 1
                    meth = "YUNMU_HEAD"
                    set_by = "YUNMU_HEAD"
                cur = yl[ptr] if ptr >= 0 else None
                ent.append({
                    "volume": vol, "tone": VOL_TONE[vol],
                    "yun_no": cur["yun_no"] if cur else None,
                    "yun_name": cur["yun_name"] if cur else None,
                    "head": hd, "head_raw": chars,
                    "fanqie": mq.group(0) if mq else None,
                    "fanqie_upper": mq.group(1)[-1] if mq else None,
                    "declared_chars": cn_number(mt.group(1)) if mt else None,
                    "meaning": note[:300],
                    "has_placeholder": bool(re.search(r"[□�]", chars)),
                    "yun_attribution": meth,
                    "yun_confidence": "HIGH" if ptr >= 0 and set_by in ("HEADER", "YUNMU_HEAD") else "MEDIUM",
                    "is_xiaoyun_head": bool(mq) and mq.start() <= 8,
                })
        xiaoyun.extend(ent)
        audit["volumes"][str(vol)] = {
            "n_yun": len(yl), "n_entries": len(ent),
            "n_fanqie": sum(1 for x in ent if x["fanqie"]),
            "sum_declared": sum(x["declared_chars"] or 0 for x in ent),
            "n_yunmu_head_advance": sum(1 for x in ent if x["yun_attribution"] == "YUNMU_HEAD"),
        }

    for i, x in enumerate(xiaoyun, 1):
        x["entry_id"] = "GY-%06d" % i

    xy = [x for x in xiaoyun if x["is_xiaoyun_head"]]
    meth = collections.Counter(x["yun_attribution"] for x in xiaoyun)
    dup = collections.Counter((x["yun_no"], x["yun_name"], x["head"]) for x in xy)
    audit.update({
        "n_yun": len(yunmu),
        "n_yun_with_label": sum(1 for y in yunmu if y["label"]),
        "n_entries": len(xiaoyun),
        "n_xiaoyun_with_fanqie": len(xy),
        "n_placeholder_head": sum(1 for x in xiaoyun if x["has_placeholder"]),
        "sum_declared_chars": sum(x["declared_chars"] or 0 for x in xy),
        "n_declared": sum(1 for x in xy if x["declared_chars"]),
        "yun_attribution": dict(meth),
        "n_fanqie_upper_distinct": len({x["fanqie_upper"] for x in xy if x["fanqie_upper"]}),
        "top_fanqie_upper": collections.Counter(
            x["fanqie_upper"] for x in xy if x["fanqie_upper"]).most_common(20),
        "n_yun_attributed": len({x["yun_no"] for x in xy if x["yun_no"]}),
        "n_duplicate_xiaoyun": sum(1 for v in dup.values() if v > 1),
        "duplicate_examples": [{"key": "|".join(map(str, k)), "n": v}
                               for k, v in dup.items() if v > 1][:20],
    })
    json.dump(yunmu, open(OUT_Y, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(OUT_X, "w", encoding="utf-8") as fh:
        for x in xiaoyun:
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    json.dump(audit, open(OUT_A, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in audit.items()
                      if k not in ("duplicate_examples", "top_fanqie_upper")},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
