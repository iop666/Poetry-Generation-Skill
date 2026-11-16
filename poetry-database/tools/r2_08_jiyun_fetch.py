#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 WP-B1：《集韻》維基文庫（四庫全書本）逐韻採集。

設計要點
- 先 enumerate 全部子頁（卷/韻/提要），不預設「216」之類數字。
- 每個韻頁渲染後保存原文（HTML→純文本）、原始 HTML 的 SHA-256、頁面修訂號。
- 低併發（默認 1）、本地緩存、指數退避重試。
- 空白頁 / 無「〈…切」的頁面不得計為成功。
- 同時記錄 transclude 的 DJVU 頁與其校對級別（pagequality 0-4）。
"""
import os, sys, json, time, hashlib, re, urllib.request, urllib.parse, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "raw", "r2_08", "jiyun_pages")
CACHE = os.path.join(ROOT, "raw", "r2_08", "cache")
API = "https://zh.wikisource.org/w/api.php"
UA = "poetry-research/1.0 (academic corpus audit; contact: local)"

os.makedirs(OUT, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)


def _get(url, timeout=60, retries=4):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception as e:  # noqa
            last = e
            time.sleep(1.5 * (2 ** i))
    raise last


def api(params, retries=4):
    params = dict(params)
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    cache_key = hashlib.sha256(
        (API + "?" + urllib.parse.urlencode(sorted(params.items()))).encode()
    ).hexdigest()[:24]
    cf = os.path.join(CACHE, "api_" + cache_key + ".json")
    if os.path.exists(cf):
        return json.load(open(cf, encoding="utf-8"))
    url = API + "?" + urllib.parse.urlencode(sorted(params.items()))
    data = json.loads(_get(url, retries=retries).decode("utf-8"))
    open(cf, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False))
    return data


def list_subpages(prefix="集韻 (四庫全書本)/"):
    out, cont = [], None
    while True:
        p = {"action": "query", "list": "allpages", "apprefix": prefix, "aplimit": "500"}
        if cont:
            p["apcontinue"] = cont
        r = api(p)
        out += [x["title"] for x in r["query"]["allpages"]]
        cont = r.get("continue", {}).get("apcontinue")
        if not cont:
            break
    return out


CSS_JUNK = re.compile(r"\.mw-parser-output[^\n]*?\}")


def html_to_text(h):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", h, flags=re.S)
    h = CSS_JUNK.sub("", h)
    h = re.sub(r"<br\s*/?>", "\n", h)
    h = re.sub(r"</(p|div|li|tr|h[1-6])>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = h.replace("&#8203;", "").replace("&nbsp;", " ").replace("&lt;", "〈").replace("&gt;", "〉")
    h = h.replace("&amp;", "&")
    h = re.sub(r"[ \t\u00a0]+", " ", h)
    h = re.sub(r"\n\s*\n\s*\n+", "\n\n", h)
    return h.strip()


TRANS = re.compile(r"\{\{transclude pages(.*?)\}\}", re.S)


def parse_transclude(wikitext):
    m = TRANS.search(wikitext)
    if not m:
        return {}
    body = m.group(1)
    toks = [t.strip() for t in body.split("|")]
    toks = [t for t in toks if t]
    info = {"raw": body.strip().replace("\n", " ")}
    nums = [t for t in toks if t.isdigit()]
    if len(nums) >= 2:
        info["djvu_from"], info["djvu_to"] = nums[0], nums[1]
    for t in toks:
        if t.startswith("fromsection="):
            info["from_section"] = t.split("=", 1)[1]
        if t.startswith("tosection="):
            info["to_section"] = t.split("=", 1)[1]
    if toks:
        info["djvu_file"] = toks[0]
    return info


def pagequality(titles):
    """批量取 Page: 命名空间的校對級別。"""
    res = {}
    for i in range(0, len(titles), 40):
        chunk = titles[i:i + 40]
        r = api({"action": "query", "prop": "info", "titles": "|".join(chunk),
                 "inprop": "quality"})
        for p in r["query"].get("pages", []):
            res[p["title"]] = p.get("pagequality")
        time.sleep(0.2)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sleep", type=float, default=0.9)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--retry", action="store_true", help="重試先前 FETCH_ERROR 的頁")
    args = ap.parse_args()

    titles = list_subpages()
    yun_titles = [t for t in titles if re.search(r"/卷\d\d/.+第", t)]
    other = [t for t in titles if t not in yun_titles]
    print(f"subpages total={len(titles)} yun={len(yun_titles)} other={len(other)}")

    manifest = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "source": "zh.wikisource.org 集韻 (四庫全書本)",
                "license": "原書公有領域；維基文庫轉錄 CC BY-SA",
                "n_subpages": len(titles), "n_yun": len(yun_titles),
                "other_pages": other, "pages": []}

    todo = yun_titles[: args.limit] if args.limit else yun_titles
    for idx, title in enumerate(todo, 1):
        safe = re.sub(r"[/\\]", "_", title)
        fp = os.path.join(OUT, safe + ".json")
        if os.path.exists(fp):
            old = json.load(open(fp, encoding="utf-8"))
            if not (args.retry and old.get("status") != "OK"):
                manifest["pages"].append(old)
                continue
        rec = {"title": title, "fetched": time.strftime("%Y-%m-%dT%H:%M:%S")}
        try:
            wt = api({"action": "parse", "page": title, "prop": "wikitext",
                      "formatversion": "2", "redirects": "1"})
            wikitext = wt["parse"]["wikitext"]
            rec["revid"] = wt["parse"].get("revid")
            rec["wikitext_len"] = len(wikitext)
            rec["transclude"] = parse_transclude(wikitext)
            html = api({"action": "parse", "page": title, "prop": "text",
                        "formatversion": "2", "disableeditionmarkup": "1"})["parse"]["text"]
            rec["html_sha256"] = hashlib.sha256(html.encode()).hexdigest()
            text = html_to_text(html)
            rec["text"] = text
            rec["text_len"] = len(text)
            rec["n_xiaoyun_mark"] = text.count("○")
            rec["n_qie"] = len(re.findall(r"[〈（(][^〈〉（）()]{1,4}切", text))
            rec["status"] = "OK" if rec["n_qie"] >= 3 else "EMPTY_OR_PARTIAL"
        except Exception as e:
            rec["status"] = "FETCH_ERROR"
            rec["error"] = repr(e)[:300]
        open(fp, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=1))
        manifest["pages"].append({k: v for k, v in rec.items() if k != "text"})
        if idx % 10 == 0 or idx == len(todo):
            print(f"[{idx}/{len(todo)}] {title} status={rec.get('status')} len={rec.get('text_len')}")
        time.sleep(args.sleep)

    # 校對級別
    djvu_titles = []
    for p in manifest["pages"]:
        tr = p.get("transclude") or {}
        a, b = tr.get("djvu_from"), tr.get("djvu_to")
        if a and b and tr.get("djvu_file"):
            for n in range(int(a), int(b) + 1):
                djvu_titles.append(f"Page:{tr['djvu_file']}/{n}")
    if djvu_titles:
        q = pagequality(djvu_titles)
        manifest["djvu_quality"] = q
        vals = [v for v in q.values() if isinstance(v, int)]
        manifest["djvu_quality_summary"] = {
            "n": len(vals),
            "proofread_3_4": sum(1 for v in vals if v >= 3),
            "problematic_0_2": sum(1 for v in vals if v < 3),
            "mean": round(sum(vals) / len(vals), 3) if vals else None,
        }
    json.dump(manifest, open(os.path.join(ROOT, "raw", "r2_08", "jiyun_manifest.json"), "w",
                             encoding="utf-8"), ensure_ascii=False, indent=1)
    ok = sum(1 for p in manifest["pages"] if p.get("status") == "OK")
    print("DONE ok=%d total=%d" % (ok, len(manifest["pages"])))


if __name__ == "__main__":
    main()
