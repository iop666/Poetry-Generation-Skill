#!/usr/bin/env python3
"""把「只有异体字/繁简差异」的 DIFF 与「实质文字差异」分开。

为什么必须分：
    crosscheck 用纯字符串比较，把「羣/群」「爲/爲」「幸/倖」这类异体写法
    也算成 DIFF。若直接报「120 首有差异」，就把版刻异体夸大成文本分歧。
    这不是校勘结论，只是比对口径问题，必须在报告里拆开说。
"""
import json, re, sqlite3

from opencc import OpenCC
T2S, S2T = OpenCC("t2s"), OpenCC("s2t")

def fold(ch: str) -> str:
    """折到「简化 + 去异体」的同一形，仅用于判定两字是否同一字的异写。"""
    s = T2S.convert(ch)
    if len(s) != 1:
        return ch
    return S2T.convert(s)

DB = "database/poetry.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT work_id,title,result,diff_detail FROM text_crosscheck WHERE result='DIFF'").fetchall()

folded, substantive, samples = 0, 0, []
for r in rows:
    ops = [x for x in r["diff_detail"].split("；") if x.strip()]
    only_variant = True
    for op in ops:
        m = re.match(r"(replace|insert|delete):A\[(\d+):(\d+)\]=(.*?) B\[(\d+):(\d+)\]=(.*)$", op)
        if not m:
            only_variant = False
            break
        a, b = m.group(4), m.group(7)
        if len(a) != len(b) or any(fold(x) != fold(y) for x, y in zip(a, b)):
            only_variant = False
            break
    if only_variant and ops:
        folded += 1
        conn.execute("UPDATE text_crosscheck SET result='MATCH_VARIANT' WHERE work_id=?", (r["work_id"],))
    else:
        substantive += 1
        if len(samples) < 6:
            samples.append((r["title"], r["diff_detail"][:110]))
conn.commit()
print(f"DIFF 共 {len(rows)}：仅异体写法差异 {folded}，实质差异 {substantive}")
for s in samples:
    print("  实质:", s[0], "|", s[1])
json.dump({"总计": len(rows), "仅异体差异": folded, "实质差异": substantive,
           "实质差异示例": [{"题": a, "差异": b} for a, b in samples]},
          open("audit/crosscheck_refine.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
