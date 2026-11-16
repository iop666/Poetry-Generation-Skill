#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse.py —— 把 raw/ 里的原始文件解析为结构化数据，并建库

流程：
  raw/*.json  →  逐条抽取（title/author/正文/词牌/卷次）
              →  规范化（标题、正文、体裁自动推导）
              →  去重与异文标记
              →  normalized/poetry/<collection>.jsonl
              →  catalog/works.jsonl、authors.jsonl、collections.jsonl、books.jsonl、sources.jsonl
              →  database/poetry.db（SQLite）

原则：
  · 原文永不改写。text_raw 保留原始分行原貌；text_norm 只做标点与空白归一，且可回溯。
  · 自动推导的字段一律标 auto_meta=1，verify_status='AUTO'，不得当作已核验。
  · 同一作品的不同文本不覆盖，互相记入 variants 表。

运行：python3 tools/parse.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(BASE, "sources", "manifest.json")
RAW = os.path.join(BASE, "raw")
NORM = os.path.join(BASE, "normalized")
CAT = os.path.join(BASE, "catalog")
DB = os.path.join(BASE, "database", "poetry.db")
PARSE_LOG = os.path.join(BASE, "audit", "parsing_log.jsonl")

# 采集集合 → 朝代/体裁先验
COLS = ["work_id", "title_raw", "title_norm", "author_name", "author_id", "dynasty", "era",
        "collection", "genre", "genre_basis", "cipai", "chapter", "section", "text_raw",
        "text_norm", "line_count", "char_count", "source_id", "volume", "seq", "variant_group",
        "dup_status", "verify_status", "auto_meta", "author_s", "title_s", "text_s"]

COLLECTION_META = {
    "shijing": {"dynasty": "先秦", "era": "先秦", "genre_hint": "诗经"},
    "chuci": {"dynasty": "先秦", "era": "战国·楚", "genre_hint": "楚辞"},
    "caocao": {"dynasty": "汉魏", "era": "东汉末", "genre_hint": "诗", "default_author": "曹操"},
    "tang": {"dynasty": "唐", "era": "唐", "genre_hint": "诗"},
    "tang300": {"dynasty": "唐", "era": "唐", "genre_hint": "诗"},
    "songshi": {"dynasty": "宋", "era": "宋", "genre_hint": "诗"},
    "songci": {"dynasty": "宋", "era": "宋", "genre_hint": "词"},
    "huajianji": {"dynasty": "五代", "era": "五代", "genre_hint": "词"},
    "nantang": {"dynasty": "五代", "era": "南唐", "genre_hint": "词"},
    "yuanqu": {"dynasty": "元", "era": "元", "genre_hint": "曲"},
    "nalan": {"dynasty": "清", "era": "清", "genre_hint": "词"},
    "shenglv": {"dynasty": "清", "era": "清", "genre_hint": "蒙学"},
    # ROUND 2-01 新增：维基文库四部总集（补空白时期）
    # gushiji 的朝代不按集合赋值，而按卷内「漢第七／梁第二十七」等段名逐条判定，
    # 故此处只给 era 缺省，实际取 it["dynasty"]。
    "gushiji": {"dynasty": "", "era": "先秦至隋", "genre_hint": "诗", "no_punct": True},
    "mingshi": {"dynasty": "明", "era": "明", "genre_hint": "诗", "no_punct": True},
    "wanqing": {"dynasty": "清", "era": "清", "genre_hint": "诗"},
    "zhongzhou": {"dynasty": "金", "era": "金", "genre_hint": "诗", "no_punct": True},
    # ROUND 2-02：昭明文選詩類（已标点，朝代随作者推定，见 wenxuan_to_json.py 的 ERA 表）
    "wenxuan": {"dynasty": "", "era": "先秦至梁", "genre_hint": "诗"},
    "tao": {"dynasty": "魏晋南北朝", "era": "晋", "genre_hint": "诗"},
}

# 部分数据集（元曲）把朝代写成拼音，直接入库会得到 dynasty='yuan'，
# 与中文朝代混排，覆盖率统计就会漏掉整代。此处归一。
DYNASTY_FIX = {"tang": "唐", "song": "宋", "yuan": "元", "ming": "明", "qing": "清",
               "jin": "金", "sui": "隋", "han": "汉魏", "wei": "魏晋南北朝", "xianqin": "先秦"}

HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002ffff]")
# 校记：「（…一作…）」「(…又作…)」整段删除；行内「X一作YZ」保留 X、删校语
BRACKET_NOTE = re.compile(r"[（(][^）)]{0,20}(?:一作|又作|某作)[^）)]{0,20}[）)]")
INLINE_NOTE = re.compile(r"([\u4e00-\u9fff])一作[\u4e00-\u9fff]{1,2}")

try:
    from opencc import OpenCC
    _cc = OpenCC("t2s")
    def to_simp(x):
        return _cc.convert(x)
except Exception:  # pragma: no cover
    def to_simp(x):
        return x


def strip_notes(s: str) -> str:
    """删除校记，不改动正文用字。"""
    s = BRACKET_NOTE.sub("", s)
    prev = None
    while prev != s:            # 反复处理连续校语
        prev = s
        s = INLINE_NOTE.sub(r"\1", s)
    return s
PUNCT = re.compile(r"[，。；：、！？,.;:!?（）()《》〈〉“”‘’\"'—…·\s]")


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def norm_title(t: str) -> str:
    if not t:
        return ""
    t = re.sub(r"\s+", "", t)
    t = re.sub(r"[（(][^）)]*[）)]$", "", t)  # 去掉末尾括注，如「其一（一作某）」
    return t.strip("　 ·")


def norm_text(lines: list) -> str:
    """标点与空白归一 + 剔除校记；不改动正文用字。"""
    out = []
    for ln in lines:
        s = PUNCT.sub("", ln)
        s = "".join(ch for ch in s if HAN.match(ch))
        if s:
            out.append(s)
    return strip_notes("".join(out))


def split_sentences(lines: list) -> list:
    """按句号/问叹/分号切分，得到「句」列表，用于体裁判断。"""
    buf, out = [], []
    for ln in lines:
        for ch in ln:
            buf.append(ch)
            if ch in "，。；：、！？,.;:!?":
                s = norm_text(["".join(buf)])
                if s:
                    out.append(s)
                buf = []
    tail = norm_text(["".join(buf)])
    if tail:
        out.append(tail)
    return out


def infer_genre(collection: str, lines: list, hint: str) -> tuple:
    """返回 (体裁, 依据)。体裁自动推导，必须标 AUTO。"""
    if hint in ("词", "曲", "蒙学", "楚辞"):
        return hint, "依集合先验"
    sents = split_sentences(lines)
    if not sents:
        return "未知", "无法切句"
    lens = [len(s) for s in sents]
    n = len(sents)
    # 五言/七言判定要求句式整齐
    if len(set(lens)) == 1 and lens[0] in (5, 7):
        L = lens[0]
        if n == 4:
            return ("五言绝句" if L == 5 else "七言绝句"), f"{n}句×{L}字，句式整齐"
        if n == 8:
            return ("五言律诗" if L == 5 else "七言律诗"), f"{n}句×{L}字，句式整齐"
        if n > 8 and n % 2 == 0:
            return ("五言排律" if L == 5 else "七言排律"), f"{n}句×{L}字，超过八句"
    if collection == "shijing" and all(l == 4 for l in lens):
        return "四言诗", "《诗经》句式以四言为主"
    if len(set(lens)) <= 2 and all(4 <= l <= 7 for l in lens):
        return "古体诗", f"{n}句，句长 {sorted(set(lens))} 不齐或非五七言定格"
    return "古体诗", f"{n}句，句长 {sorted(set(lens))}"


def extract_items(obj, collection):
    """把不同 JSON 形状统一成 [{title, author, lines, cipai, chapter, section, volume}]"""
    items = []

    def add(title, author, lines, **kw):
        if not title and not lines:
            return
        items.append({"title": title or "", "author": author or "",
                      "lines": [l for l in lines if l and str(l).strip()],
                      "cipai": kw.get("cipai", ""), "chapter": kw.get("chapter", ""),
                      "section": kw.get("section", ""), "volume": kw.get("volume", ""),
                      "dynasty": kw.get("dynasty", "")})

    if collection == "tang300":
        # {'title':.., 'content':[{type:体裁, content:[{chapter, author, paragraphs}]}]}
        for grp in obj.get("content", []):
            gtype = grp.get("type", "")
            for w in grp.get("content", []) or []:
                add(w.get("chapter"), w.get("author"), w.get("paragraphs") or [],
                    chapter=gtype)
        return items

    if isinstance(obj, dict):
        obj = obj.get("content") or obj.get("data") or []

    if isinstance(obj, list):
        for t in obj:
            if not isinstance(t, dict):
                continue
            title = t.get("title") or t.get("rhythmic") or t.get("chapter") or ""
            author = t.get("author") or ""
            cipai = t.get("rhythmic") or ""
            lines = (t.get("paragraphs") or t.get("content") or t.get("verse")
                     or t.get("para") or [])
            if isinstance(lines, str):
                lines = [lines]
            # 纳兰性德集标题形如「长相思·山一程」，词牌在「·」之前
            if not cipai and "·" in title:
                cipai = title.split("·")[0]
            add(title, author, lines, cipai=cipai,
                chapter=t.get("chapter", ""), section=t.get("section", ""),
                volume=t.get("volume", ""), dynasty=t.get("dynasty", ""))
    return items


def main() -> int:
    man = json.load(open(MANIFEST, encoding="utf-8"))
    os.makedirs(os.path.join(NORM, "poetry"), exist_ok=True)
    os.makedirs(CAT, exist_ok=True)
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    os.makedirs(os.path.dirname(PARSE_LOG), exist_ok=True)

    conn = sqlite3.connect(DB)
    conn.executescript("""
    DROP TABLE IF EXISTS sources; DROP TABLE IF EXISTS books; DROP TABLE IF EXISTS authors;
    DROP TABLE IF EXISTS works; DROP TABLE IF EXISTS variants; DROP TABLE IF EXISTS read_log;
    DROP TABLE IF EXISTS collections;

    CREATE TABLE sources(source_id TEXT PRIMARY KEY, name TEXT, category TEXT, era TEXT,
        collection TEXT, url TEXT, license TEXT, copyright TEXT, reliability TEXT,
        maintainer TEXT, format TEXT, local_path TEXT, sha256 TEXT, bytes INTEGER,
        acquired_at TEXT, parse_status TEXT, verified TEXT);

    CREATE TABLE books(book_id TEXT PRIMARY KEY, title TEXT, author TEXT, editor TEXT,
        publisher TEXT, edition TEXT, category TEXT, license TEXT, copyright TEXT,
        status TEXT, reading_status TEXT, note TEXT);

    CREATE TABLE collections(collection TEXT PRIMARY KEY, dynasty TEXT, era TEXT,
        works INTEGER, sources INTEGER, note TEXT);

    CREATE TABLE authors(author_id TEXT PRIMARY KEY, name TEXT, dynasty TEXT, era TEXT,
        work_count INTEGER, collections TEXT, auto_meta INTEGER, note TEXT);

    CREATE TABLE works(work_id TEXT PRIMARY KEY, title_raw TEXT, title_norm TEXT,
        author_name TEXT, author_id TEXT, dynasty TEXT, era TEXT, collection TEXT,
        genre TEXT, genre_basis TEXT, cipai TEXT, chapter TEXT, section TEXT,
        text_raw TEXT, text_norm TEXT, line_count INTEGER, char_count INTEGER,
        source_id TEXT, volume TEXT, seq INTEGER, variant_group TEXT,
        dup_status TEXT, verify_status TEXT, auto_meta INTEGER,
        author_s TEXT, title_s TEXT, text_s TEXT);

    CREATE TABLE variants(group_id TEXT, work_id TEXT, note TEXT);

    CREATE TABLE read_log(book_id TEXT, chapter TEXT, status TEXT, ts TEXT, note TEXT);

    CREATE INDEX idx_works_author ON works(author_name);
    CREATE INDEX idx_works_genre ON works(genre);
    CREATE INDEX idx_works_dynasty ON works(dynasty);
    CREATE INDEX idx_works_collection ON works(collection);
    CREATE INDEX idx_works_author_s ON works(author_s);
    """)

    # 先把清单内全部来源写入 sources 表（含文献类），保证「每条数据都能追溯到来源」
    for e in man["poetry_sources"]:
        path = os.path.join(BASE, e["local"])
        size = os.path.getsize(path) if os.path.exists(path) else 0
        fmt = e.get("format", "")
        st = "PARSED" if fmt == "json" else "CONVERTED"
        conn.execute("INSERT OR REPLACE INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            e["source_id"], e["name"], e["category"], e["era"], e["collection"], e["url"],
            e["license"], e["copyright"], e["reliability"], e["maintainer"], fmt, e["local"],
            None, size, datetime.datetime.now().isoformat(timespec="seconds"), st, "NO"))
    conn.commit()

    log_f = open(PARSE_LOG, "w", encoding="utf-8")
    works_all, authors_map, coll_stats = [], {}, defaultdict(lambda: {"works": 0, "sources": 0})
    seq = 0                                 # 分组索引在「唯一化」之后统一构建

    for e in man["poetry_sources"]:
        path = os.path.join(BASE, e["local"])
        sid = e["source_id"]
        coll = e["collection"]
        rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
               "source_id": sid, "path": e["local"], "collection": coll}
        if not os.path.exists(path):
            rec.update({"status": "MISSING_FILE"})
            log_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            continue
        size = os.path.getsize(path)
        if coll == "shenglv":
            rec.update({"status": "SKIP_BOOK", "note": "蒙学对韵材料，属文献而非诗词，转由 convert_books.py 处理"})
            log_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            continue
        if e.get("format") != "json":
            rec.update({"status": "SKIP_NON_JSON", "note": "文献类来源，由 tools/convert_books.py 处理"})
            log_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            continue
        meta = COLLECTION_META.get(coll, {})
        try:
            obj = json.load(open(path, encoding="utf-8"))
        except Exception as ex:  # noqa: BLE001
            rec.update({"status": "PARSE_ERROR", "error": f"{type(ex).__name__}: {ex}"})
            log_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            continue

        items = extract_items(obj, coll)
        n_ok = n_skip = 0
        for it in items:
            lines = it["lines"]
            txt_raw = "\n".join(lines)
            txt_norm = norm_text(lines)
            if len(txt_norm) < 8:               # 正文过短，疑似残缺/序跋，跳过但计数
                n_skip += 1
                continue
            title_raw = it["title"]
            tnorm = norm_title(title_raw)
            author = it["author"].strip() or meta.get("default_author") or "佚名"
            if meta.get("no_punct"):
                # 四庫本无标点，正文是连续长串，按句长判体会把全部作品压成「古体诗」。
                # 这属于「无法判定」而非「判定为古体」，故单列「未定」，不冒充结论。
                genre, basis = "未定", "底本无标点，无法切句判体（四庫全書本）"
            else:
                genre, basis = infer_genre(coll, lines, meta.get("genre_hint", "诗"))
            wid = f"{coll}:{sha1(author + '|' + tnorm + '|' + txt_norm)[:12]}"
            seq += 1
            works_all.append({
                "work_id": wid, "title_raw": title_raw, "title_norm": tnorm,
                "author_name": author,
                "author_id": "A:" + sha1(author)[:10],
                "dynasty": DYNASTY_FIX.get(str(it.get("dynasty") or "").lower(),
                                            it.get("dynasty") or meta.get("dynasty", "")),
                "era": meta.get("era", ""),
                "collection": coll, "genre": genre, "genre_basis": basis,
                "cipai": it["cipai"], "chapter": it["chapter"], "section": it["section"],
                "text_raw": txt_raw, "text_norm": txt_norm,
                # 保留原始标点的版本（原始分行见 text_raw；此处合成一行，标点不动）
                "text_punct": "".join(lines),
                "line_count": len(lines), "char_count": len(txt_norm),
                "source_id": sid, "volume": it["volume"], "seq": seq,
                "variant_group": "", "dup_status": "UNIQUE",
                "verify_status": "AUTO", "auto_meta": 1,
                "author_s": to_simp(author), "title_s": to_simp(tnorm),
                "text_s": to_simp(txt_norm),
            })
            n_ok += 1
        coll_stats[coll]["works"] += n_ok
        coll_stats[coll]["sources"] += 1
        rec.update({"status": "PARSED", "items": len(items), "kept": n_ok, "skipped_short": n_skip})
        log_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[PARSE] {sid:<16} {coll:<10} 条目 {len(items):>5}  入库 {n_ok:>5}  过短跳过 {n_skip:>3}")

        # 落 sources 表
        conn.execute("INSERT OR REPLACE INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            sid, e["name"], e["category"], e["era"], coll, e["url"], e["license"],
            e["copyright"], e["reliability"], e["maintainer"], e["format"], e["local"],
            None, size, datetime.datetime.now().isoformat(timespec="seconds"),
            "PARSED", "NO"))

    # ---------- 唯一化 work_id（必须先于重复分组） ----------
    # 同集合内若两条记录的 author/title/text 完全相同，生成的 work_id 也相同。
    # 早期版本先按 {work_id: 对象} 建索引再分组，后一条会把前一条覆盖，
    # 于是同组内「KEPT」被紧随其后的「DUPLICATE」覆盖 —— 表现为 13 组出现
    # 「1 条 UNIQUE + N 条 DUPLICATE」，与「976 组 / 1,010 条冗余」的口径对不上。
    # 现改为：先唯一化 id，再用对象引用分组（不再依赖 id 索引）。
    seen = set()
    for w in works_all:
        if w["work_id"] in seen:
            w["work_id"] = w["work_id"] + "-" + str(w["seq"])
        seen.add(w["work_id"])
        a = authors_map.setdefault(w["author_name"], {
            "author_id": w["author_id"], "name": w["author_name"], "dynasty": w["dynasty"],
            "era": w["era"], "work_count": 0, "collections": set(), "auto_meta": 1,
            "note": "作者朝代由所属集合先验推导，未与史传核对"})
        a["work_count"] += 1
        a["collections"].add(w["collection"])

    # ---------- 去重与异文 ----------
    text_groups = defaultdict(list)      # sha1(text_norm) → [对象]
    name_groups = defaultdict(list)      # (author, title_norm) → [对象]
    for w in works_all:
        text_groups[sha1(w["text_norm"])].append(w)
        name_groups[(w["author_name"], w["title_norm"])].append(w)

    dup_groups = 0
    for h, objs in text_groups.items():
        if len(objs) > 1:
            gid = "G:" + h[:12]
            dup_groups += 1
            objs[0]["dup_status"] = "KEPT"
            objs[0]["variant_group"] = gid
            for o in objs[1:]:
                o["dup_status"] = "DUPLICATE"
                o["variant_group"] = gid
                conn.execute("INSERT INTO variants VALUES (?,?,?)",
                             (gid, o["work_id"], "正文完全相同，判为重复收录"))

    var_groups = 0
    for (author, tn), objs in name_groups.items():
        if len(objs) > 1:
            if len({o["text_norm"] for o in objs}) > 1:   # 同作者同题但文本不同
                gid = "V:" + sha1(author + tn)[:12]
                var_groups += 1
                for o in objs:
                    if not o["variant_group"]:
                        o["variant_group"] = gid
                    o["verify_status"] = "VARIANT_PENDING"
                    conn.execute("INSERT INTO variants VALUES (?,?,?)",
                                 (gid, o["work_id"], "同作者同题、文本不同，列为异文候选，需人工比对"))

    # ---------- 写入 ----------

    conn.executemany(
        # 显式列名：schema_v2 之后 works 多了 9 列（text_punct / quality_grade / ...），
        # 若仍用 "VALUES (?,…)" 按位置插入会因列数不符直接报错。
        "INSERT OR REPLACE INTO works (" + ",".join(COLS) + ") VALUES ("
        + ",".join(["?"] * len(COLS)) + ")",
        [tuple(w[k] for k in COLS) for w in works_all])

    for a in authors_map.values():
        conn.execute("INSERT OR REPLACE INTO authors VALUES (?,?,?,?,?,?,?,?)", (
            a["author_id"], a["name"], a["dynasty"], a["era"], a["work_count"],
            ",".join(sorted(a["collections"])), a["auto_meta"], a["note"]))

    for coll, st in coll_stats.items():
        m = COLLECTION_META.get(coll, {})
        conn.execute("INSERT OR REPLACE INTO collections VALUES (?,?,?,?,?,?)", (
            coll, m.get("dynasty", ""), m.get("era", ""), st["works"], st["sources"], ""))

    for b in man["modern_books"]:
        conn.execute("INSERT OR REPLACE INTO books VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            b["book_id"], b["title"], b["author"], "", b["publisher"], b["edition"],
            b["category"], b["license"], b["copyright"], b["status"], "NOT_STARTED", b["note"]))

    conn.commit()

    # ---------- JSONL 目录 ----------
    def dump(name, rows):
        with open(os.path.join(CAT, name), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    dump("works_sample.jsonl", works_all[:2000])   # 全量见 normalized/poetry/*.jsonl 与 poetry.db
    dump("authors.jsonl", [{**a, "collections": sorted(a["collections"])}
                           for a in sorted(authors_map.values(), key=lambda x: -x["work_count"])])
    dump("sources.jsonl", [dict(zip(
        ["source_id", "name", "category", "era", "collection", "url", "license", "reliability",
         "maintainer", "format", "local", "acquired", "parse_status"],
        [e["source_id"], e["name"], e["category"], e["era"], e["collection"], e["url"],
         e["license"], e["reliability"], e["maintainer"], e["format"], e["local"],
         "", "PARSED"])) for e in man["poetry_sources"]])
    dump("collections.jsonl", [{"collection": k, **v} for k, v in coll_stats.items()])
    dump("books.jsonl", man["modern_books"])

    # 分集合导出 normalized
    by_coll = defaultdict(list)
    for w in works_all:
        by_coll[w["collection"]].append(w)
    for coll, rows in by_coll.items():
        with open(os.path.join(NORM, "poetry", f"{coll}.jsonl"), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    log_f.close()
    conn.close()

    total = len(works_all)
    uniq = sum(1 for w in works_all if w["dup_status"] != "DUPLICATE")
    print(f"\n=== 入库完成 ===")
    print(f"作品记录 {total:,}　去重后 {uniq:,}　作者 {len(authors_map):,}")
    print(f"完全重复组 {dup_groups}　异文候选组 {var_groups}")
    print(f"数据库：{os.path.relpath(DB, BASE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
