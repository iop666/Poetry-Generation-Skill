#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E4: 500 条分层抽样质量抽检 -> WORKS_TEXT_500_SAMPLE_AUDIT.csv"""
import sqlite3, csv, re, random, difflib
from collections import Counter, defaultdict

ROOT = "<PROJECT_ROOT>/poetry-database"
DB = f"{ROOT}/database/poetry.db"
OUT = f"{ROOT}/reports/tasks/2026-11-16/R2-12"
PUNCT = r"[\s\u3000，。！？、；：“”‘’（）()《》〈〉「」『』【】〖〗…—\-,.;:!?\"'·～~]"
norm0 = lambda s: re.sub(PUNCT, "", s or "")

STRATA = [
 ("唐诗",   "dynasty='唐' AND genre<>'词'"),
 ("宋诗",   "dynasty='宋' AND genre<>'词'"),
 ("宋词",   "dynasty='宋' AND genre='词'"),
 ("元曲",   "dynasty='元'"),
 ("明清诗词", "dynasty IN ('明','清')"),
 ("六朝诗", "dynasty='魏晋南北朝'"),
 ("先秦两汉韵文", "dynasty IN ('先秦','汉魏')"),
]
PER = 80

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); con.text_factory = str
con.execute("PRAGMA busy_timeout=8000")
cur = con.cursor()

# 全库 20 字前缀索引（用于重复判断）
print("构建前缀索引...")
prefix = defaultdict(list)
for wid, tn in cur.execute("SELECT work_id,substr(text_norm,1,20) FROM works WHERE length(text_norm)>=20"):
    if len(prefix[tn]) < 4:
        prefix[tn].append(wid)
print("前缀数:", len(prefix))

random.seed(20261116)
picked = []
gap = {}
for name, cond in STRATA:
    total = cur.execute(f"SELECT count(*) FROM works WHERE {cond}").fetchone()[0]
    pool = cur.execute(f"""SELECT work_id,title_norm,author_name,text_raw,text_norm,char_count
        FROM works WHERE {cond} ORDER BY random() LIMIT 600""").fetchall()
    cells = defaultdict(list)
    for r in pool:
        traw = r[3] or ""
        punct = 1 if re.search(r"[，。！？；：、]", traw) else 0
        longe = 1 if (r[5] or 0) >= 80 else 0
        tnote = 1 if re.search(r"[（(]|有序|幷序|并序|題注", (r[1] or "") + traw[:20]) else 0
        cells[(punct, longe, tnote)].append(r)
    got, cell_stat = [], Counter()
    keys = sorted(cells, key=lambda k: -len(cells[k]))
    quota = max(8, PER // max(1, len(keys)))
    for k in keys:
        take = cells[k][:max(quota, 10)]
        got += take; cell_stat[k] = len(take)
    # 去重后截断到 80，不足则从剩余补
    seen, final = set(), []
    for r in got:
        if r[0] in seen: continue
        seen.add(r[0]); final.append(r)
        if len(final) >= PER: break
    if len(final) < PER:
        for r in pool:
            if r[0] in seen: continue
            seen.add(r[0]); final.append(r)
            if len(final) >= PER: break
    gap[name] = (total, len(final), dict(cell_stat))
    print(f"{name}: 总体{total} 抽{len(final)} 单元{len(cell_stat)}")
    picked += [(name, r) for r in final]

rows_out = []
sid = 0
for stratum, (wid, title, au, traw, tnorm, cc) in picked:
    sid += 1
    traw, tnorm, title, au = traw or "", tnorm or "", title or "", au or ""
    has_p = 1 if re.search(r"[，。！？；：、]", traw) else 0
    clean_raw = re.sub(r"cq=\d+", "", traw)
    has_num = 1 if re.search(r"[0-9０-９]{3,}|第[一二三四五六七八九十百]+[頁页]", clean_raw + tnorm) else 0
    a0 = norm0(au)
    author_in = 1 if a0 and a0 in norm0(tnorm[:16]) else 0
    tb = norm0(title)
    title_in = 1 if len(tb) >= 4 and norm0(tnorm[:14]).startswith(tb[:6]) else 0
    note_mixed = 1 if re.search(r"一作|一本作|集作|或作|校|詩題|首句|見《|〖|○", tnorm) else 0
    dup_ids = [x for x in prefix.get(tnorm[:20], []) if x != wid][:3]
    dup = 1 if dup_ids else 0
    dup_src = ""
    if dup_ids:
        ph = ",".join("?" * len(dup_ids))
        mine = cur.execute("SELECT source_id FROM works WHERE work_id=?", (wid,)).fetchone()
        others = cur.execute(f"SELECT DISTINCT source_id FROM works WHERE work_id IN ({ph})", dup_ids).fetchall()
        os_ = {o[0] for o in others if o[0]}
        dup_src = "跨集重出" if mine and mine[0] not in os_ else "同源重出"
    cc_delta = (cc or 0) - len(tnorm)
    # 截断判定
    lines = [x for x in traw.split("\n") if norm0(x)]
    tail = traw.rstrip()[-6:]
    trunc = 0
    if lines and len(traw) > 10:
        last = lines[-1]
        if not re.fullmatch(r"[（(].*[）)]\s*", last):
            trunc = 1 if (last.rstrip()[-1:] in "，、；：" or len(norm0(last)) <= 3) else 0
    # 正文丢字：norm 短于 raw 去标点，且差值超过校记长度
    cq_mark = 1 if re.search(r"cq=\d+", traw) else 0
    # 期望正文：去 HTML 标签 / cq 标记 / 括号校记 后归一化
    base = re.sub(r"<[^>]*>", "", traw)
    base = re.sub(r"cq=\d+", "", base)
    base = re.sub(r"[（(][^（）()]*[）)]", "", base)
    exp = norm0(base)
    sm = difflib.SequenceMatcher(None, exp, tnorm, autojunk=False)
    lost = [exp[i1:i2] for tag, i1, i2, j1, j2 in sm.get_opcodes()
            if tag in ("delete", "replace") and exp[i1:i2] and
            re.search(r"[\u4e00-\u9fff]", exp[i1:i2]) and len(exp[i1:i2]) >= 2]
    loss = 1 if lost else 0
    flags = []
    if trunc: flags.append("TRUNCATED")
    if note_mixed: flags.append("NOTE_MIXED")
    if loss: flags.append("BODY_LOSS_SUSPECT")
    if dup: flags.append("DUP")
    if title_in: flags.append("TITLE_REPEAT")
    if author_in: flags.append("AUTHOR_IN_BODY")
    verdict = "OK" if not flags else "|".join(flags)
    ev = []
    if note_mixed: ev.append("norm 含校记/书名/序号残留")
    if cq_mark: ev.append("正文内嵌 cq= 语料库标记，已从 norm 剥离")
    if loss: ev.append("norm 相对 raw 缺失正文段：" + "".join(lost)[:24])
    if dup: ev.append(f"前20字重出({dup_src}):" + ",".join(dup_ids))
    if trunc: ev.append(f"raw 末尾「{tail}」")
    if title_in: ev.append("标题前4字重现于正文首")
    rows_out.append(dict(sample_id=f"R2-12-{sid:04d}", stratum=stratum, work_id=wid, title=title,
                         author_name=au, text_len=len(tnorm), has_punctuation=has_p,
                         has_page_number=has_num, author_in_body=author_in, title_in_body=title_in,
                         note_mixed=note_mixed, dup_flag=dup, dup_work_ids=";".join(dup_ids),
                         char_count_delta=cc_delta, truncated_suspect=trunc, verdict=verdict,
                         evidence="；".join(ev) or "未见异常"))

with open(f"{OUT}/WORKS_TEXT_500_SAMPLE_AUDIT.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["sample_id","stratum","work_id","title","author_name","text_len",
        "has_punctuation","has_page_number","author_in_body","title_in_body","note_mixed","dup_flag",
        "dup_work_ids","char_count_delta","truncated_suspect","verdict","evidence"])
    w.writeheader(); w.writerows(rows_out)

print("\n总抽样", len(rows_out))
print("分层:", Counter(r["stratum"] for r in rows_out))
print("verdict:", Counter(r["verdict"] for r in rows_out))
print("有标点:", sum(r["has_punctuation"] for r in rows_out), "页码:", sum(r["has_page_number"] for r in rows_out))
print("dup:", sum(r["dup_flag"] for r in rows_out), "note_mixed:", sum(r["note_mixed"] for r in rows_out),
      "trunc:", sum(r["truncated_suspect"] for r in rows_out), "loss:", sum(1 for r in rows_out if "BODY_LOSS_SUSPECT" in r["verdict"]))
import json
json.dump({k: [v[0], v[1], {str(kk): vv for kk, vv in v[2].items()}] for k, v in gap.items()}, open(f"{OUT}/LOGS/_e4_strata.json","w"), ensure_ascii=False, indent=1)
con.close()
