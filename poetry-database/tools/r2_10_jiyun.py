#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-10 工作包 D：《集韻》206 韻頁來源追溯、小韻與字數對帳。

要點
----
1. 每頁都有 `transclude` 元數據（文淵閣四庫全書 djvu 冊號 + 葉碼區間），
   這是比「維基文庫頁面」更精確的來源定位，逐頁入表。
2. 補查 MediaWiki revid（前輪未記），以「頁面版本」證明可回溯。
3. 把 4,344 / 4,432 / 4,169 三個小韻數，與 51,803 / 52,983 / 53,952 / 53,525 /
   50,132 / 49,084 六個字數，逐一給出「統計對象 + 算法 + 可否復算」。
"""
import collections
import csv
import glob
import json
import os
import re
import sqlite3
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
SRC = os.path.join(ROOT, "raw", "r2_08", "jiyun_pages")
OUT = os.path.join(ROOT, "raw", "r2_10", "jiyun")
os.makedirs(OUT, exist_ok=True)

CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8,
      "九": 9, "十": 10, "百": 100, "零": 0, "〇": 0}


def cn2int(s):
    tot = cur = 0
    for ch in s:
        v = CN.get(ch)
        if v is None:
            return None
        if v == 10:
            cur = (cur or 1) * 10
        elif v == 100:
            tot += (cur or 1) * 100
            cur = 0
        else:
            cur += v
    return tot + cur


def api(params):
    params["format"] = "json"
    params["formatversion"] = "2"
    u = "https://zh.wikisource.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(u, headers={"User-Agent": "poetry-research/1.0 (audit)"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def fetch_revids(titles):
    got = {}
    for i in range(0, len(titles), 40):
        batch = titles[i:i + 40]
        for attempt in range(3):
            try:
                r = api({"action": "query", "prop": "revisions", "rvprop": "ids|timestamp",
                         "titles": "|".join(batch)})
                for p in r.get("query", {}).get("pages", []):
                    if p.get("revisions"):
                        got[p["title"]] = p["revisions"][0]
                    elif p.get("missing"):
                        got[p["title"]] = None
                break
            except Exception as e:
                print("retry", str(e)[:40])
                time.sleep(5)
        time.sleep(1)
    return got


def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.json")))
    pages = []
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        tr = d.get("transclude") or {}
        t = re.sub(r"<[^>]+>", "", d.get("text", ""))
        t = re.sub(r"\s+", "", t)
        wens = [cn2int(x) for x in re.findall(r"文([一二三四五六七八九十百零〇]+)", t)]
        wens = [x for x in wens if x]
        pages.append({
            "title": d["title"],
            "volume": (re.search(r"卷(\d+)/", d["title"]) or [None, None])[1],
            "yun": d["title"].split("/")[-1],
            "djvu_file": tr.get("djvu_file", ""),
            "djvu_from": tr.get("djvu_from", ""),
            "djvu_to": tr.get("djvu_to", ""),
            "from_section": tr.get("from_section", ""),
            "to_section": tr.get("to_section", ""),
            "fetched": d.get("fetched", ""),
            "html_sha256": d.get("html_sha256", ""),
            "text_len": d.get("text_len", 0),
            "n_xiaoyun_mark": d.get("n_xiaoyun_mark", 0),
            "n_qie": d.get("n_qie", 0),
            "all_wen_sum": sum(wens),
            "n_wen_tokens": len(wens),
            "status": d.get("status", ""),
            "revid": None,
            "rev_timestamp": "",
        })

    print("查 revid...", len(pages))
    revs = fetch_revids([p["title"] for p in pages])
    for p in pages:
        r = revs.get(p["title"])
        if r:
            p["revid"] = r.get("revid")
            p["rev_timestamp"] = r.get("timestamp", "")
    print("取得 revid:", sum(1 for p in pages if p["revid"]))

    with open(os.path.join(OUT, "jiyun_206_page_provenance.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        cols = ["title", "volume", "yun", "djvu_file", "djvu_from", "djvu_to", "from_section",
                "to_section", "fetched", "revid", "rev_timestamp", "html_sha256",
                "text_len", "n_xiaoyun_mark", "n_qie", "all_wen_sum", "n_wen_tokens", "status"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for p in pages:
            w.writerow(p)

    # 入庫
    con = sqlite3.connect(DB)
    con.execute("DROP TABLE IF EXISTS jiyun_page_provenance_r2_10")
    con.execute("""CREATE TABLE jiyun_page_provenance_r2_10(
      title TEXT PRIMARY KEY, volume INT, yun TEXT, djvu_file TEXT, djvu_from TEXT,
      djvu_to TEXT, from_section TEXT, to_section TEXT, fetched TEXT, revid INT,
      rev_timestamp TEXT, html_sha256 TEXT, text_len INT, n_xiaoyun_mark INT, n_qie INT,
      all_wen_sum INT, n_wen_tokens INT, status TEXT, round TEXT)""")
    con.executemany("""INSERT INTO jiyun_page_provenance_r2_10 VALUES
      (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, '2026-11-15')""",
        [(p["title"], int(p["volume"] or 0), p["yun"], p["djvu_file"], p["djvu_from"],
          p["djvu_to"], p["from_section"], p["to_section"], p["fetched"], p["revid"],
          p["rev_timestamp"], p["html_sha256"], p["text_len"], p["n_xiaoyun_mark"],
          p["n_qie"], p["all_wen_sum"], p["n_wen_tokens"], p["status"]) for p in pages])
    con.commit()

    # ---- 字數與小韻對帳 ----
    stored_n = con.execute("SELECT count(*) FROM ph_jiyun_r2_09").fetchone()[0]
    stored_decl = con.execute("SELECT sum(declared_chars) FROM ph_jiyun_r2_09").fetchone()[0]
    stored_est = con.execute("SELECT sum(n_heads_est) FROM ph_jiyun_r2_09").fetchone()[0]
    n_mark = sum(p["n_xiaoyun_mark"] for p in pages)
    all_wen = sum(p["all_wen_sum"] for p in pages)
    print("頁面○總數", n_mark, "入庫小韻", stored_n, "Σ文N(全頁) ", all_wen,
          "入庫declared", stored_decl, "字頭估計", stored_est)

    recon = [
        ("小韻數", 4344, "R2-08 舊解析器，202 頁（4 頁 429 失敗未採）",
         "舊 r2_08_jiyun_parse.py；每段以「○」切分、逐〈〉串接後取 文N",
         "CONFIRMED_DIFFERENT_DEFINITION",
         "頁集不同：本輪以同腳本在 203 頁重跑得 4,377；202 頁快照已被補抓覆蓋，無法逐頁復原"),
        ("小韻數", 4432, "R2-08 同一舊解析器，但頁數已補至 206（報告未更新）",
         "同上", "CONFIRMED_DIFFERENT_DEFINITION",
         "同腳本重跑 206 頁得 4,432，與此數完全一致，可復算"),
        ("小韻數", 4169, "R2-09 新解析器，206 頁，要求 ○ 後 ≥6 字且首字可匹配",
         "r2_09_jiyun_loader.py；SEG=○[^○]{6,}，HEAD 必須匹配",
         "CONFIRMED_DIFFERENT_DEFINITION",
         "可復算；比舊法少 263 條，主要是頁首導航殘段與缺 ○ 的合併段被排除"),
        ("字數", 51803, "R2-08 舊解析器 202 頁的 Σ文N", "同 4,344",
         "CONFIRMED_DIFFERENT_DEFINITION", "頁集不同；202 頁快照不可復原"),
        ("字數", 52983, "R2-08 舊解析器 206 頁的 Σ文N", "同 4,432",
         "CONFIRMED_SAME_DEFINITION", "本輪以舊腳本重跑 206 頁得 52,983，可復算"),
        ("字數", 53952, "本輪新統計：206 頁全部「文N」字樣求和（含注文中《說文》引文誤命中）",
         "正則 文[中文數字] 全頁求和", "CONFIRMED_DIFFERENT_DEFINITION",
         "與 53,525 相差 427（0.8%），說明原書自述總字數接近「所有文N之和」而非「首文N之和」"),
        ("字數", 53525, "原書（四庫提要/序）自述全書字數",
         "文獻記載，非本項目統計", "SOURCE_DIFFERENCE",
         "非程序可算；與 53,952 差 0.8%，可視為同一量級的兩個來源"),
        ("字數", 50132, "R2-09 每小韻取「段內首個文N」",
         "r2_09_jiyun_loader.py WEN.search(body)", "CONFIRMED_SAME_DEFINITION",
         "可復算；比「全部文N求和」少 3,820，因為一小韻內後續〈〉的「文N」多為《說文》篇卷數"),
        ("字數", 49084, "R2-09 字頭估計（〈〉前緊鄰漢字全計）",
         "r2_09_jiyun_loader.py heads 累加", "COMPUTED",
         "可復算；此為估計值，非原書字頭數"),
    ]
    with open(os.path.join(OUT, "jiyun_count_reconciliation.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value", "definition", "algorithm", "status",
                    "reproducible", "note"])
        for m, v, d, a, s, n in recon:
            rep = "YES" if s == "CONFIRMED_SAME_DEFINITION" or "本輪" in d or "重跑" in n else "NO_PAGE_SNAPSHOT_LOST"
            w.writerow([m, v, d, a, s, rep, n])

    # 120 條人工複核匯總
    mp = os.path.join(ROOT, "raw", "r2_09", "c_pages", "jiyun_sample_120.csv")
    cnt = collections.Counter()
    fails = []
    if os.path.exists(mp):
        for r in csv.DictReader(open(mp, encoding="utf-8-sig")):
            cnt[r.get("verdict", "")] += 1
            if r.get("verdict") == "FAIL":
                fails.append(r)
    print("120 條複核:", dict(cnt))

    stats = {"n_pages": len(pages), "n_with_revid": sum(1 for p in pages if p["revid"]),
             "n_with_djvu_locator": sum(1 for p in pages if p["djvu_file"]),
             "n_status_ok": sum(1 for p in pages if p["status"] == "OK"),
             "sum_xiaoyun_marks": n_mark, "stored_xiaoyun": stored_n,
             "sum_all_wen": all_wen, "stored_declared": stored_decl, "stored_est": stored_est,
             "review120": dict(cnt), "n_fail_listed": len(fails),
             "reconciliation": [{"metric": m, "value": v, "status": s} for m, v, d, a, s, n in recon]}
    json.dump(stats, open(os.path.join(OUT, "jiyun_stats.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    con.close()
    print(json.dumps({k: stats[k] for k in ["n_pages", "n_with_revid", "n_with_djvu_locator",
                                            "sum_xiaoyun_marks", "stored_xiaoyun",
                                            "sum_all_wen", "review120"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
