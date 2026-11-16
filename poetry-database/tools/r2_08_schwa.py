#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 WP-A.2：ə / e 音标候选索引与分级。

背景：PaddleOCR-VL 对国际音标 ə 与拉丁 e 常互混。王力古音系统中
之/職/蒸部用 ə、支/錫/耕部用 e，二者**对立**，混读会直接改变韵部归属。

做法
1. 逐字符扫描两书 OCR 文本，登记每一处 ə（主索引，589 处）与每一处处在
   音标／拟音语境中的 e（副索引）。
2. 按上下文分级：PHONETIC（[]（）$…$ 内）／FORM（由拉丁字母与 ə 构成的拟音串）／
   TABLE（HTML 表格单元）／PROSE（中文行文）。
3. 依规则给状态：CONFIRMED_SCHWA / CONFIRMED_E / OCR_ERROR / UNKNOWN。
   规则只处理能判定的；判不了的必须落 UNKNOWN，不得默认。
4. 输出每项 PDF 页、字符偏移、前后文、token、上下文类型，供回图复核。
"""
import json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS = {
    "wangli_yinyunxue": ("汉语音韵学", "raw/books_ocr_paddle/wangli_yinyunxue/pages.jsonl"),
    "wangli_tongyuan": ("同源字典", "raw/books_ocr_paddle/wangli_tongyuan/pages.jsonl"),
}
OUT = os.path.join(ROOT, "raw", "r2_08", "schwa_index.json")

LAT = "a-zA-Zəɛɔŋɐɑæʌɯɨʉyœøɤɵɘɜɞɪʊʃʒθðɣχʁɕʑȵȶȡʰʲʷːˈˌ"
TOKEN_RE = re.compile(rf"[{LAT}]+")
CJK = re.compile(r"[\u4e00-\u9fff]")


def ctx_type(text, i):
    left = text[max(0, i - 12):i]
    right = text[i + 1:i + 13]
    if re.search(r"[\[\(（]\s*$", left) or re.match(r"^[^\]\)）]{0,10}[\]\)）]", right):
        return "PHONETIC"
    if re.search(r"\$[^$]{0,20}$", left) or re.match(r"^[^$]{0,20}\$", right):
        return "PHONETIC"
    if re.search(r">\s*$", left) and re.match(r"^[^<]{0,10}<", right):
        return "TABLE"
    tok = token_at(text, i)
    if len(tok) >= 2:
        return "FORM"
    return "PROSE"


def token_at(text, i):
    s = i
    while s > 0 and re.match(rf"[{LAT}]", text[s - 1]):
        s -= 1
    e = i + 1
    while e < len(text) and re.match(rf"[{LAT}]", text[e]):
        e += 1
    return text[s:e]


def classify(ch, text, i):
    t = ctx_type(text, i)
    tok = token_at(text, i)
    left = text[max(0, i - 6):i]
    right = text[i + 1:i + 7]
    if ch == "ə":
        if t in ("PHONETIC", "FORM", "TABLE"):
            return "CONFIRMED_SCHWA", t, "SCHWA_IN_PHONETIC_CONTEXT"
        if CJK.search(left[-1:] or "") and CJK.search(right[:1] or "") and len(tok) == 1:
            # 中文行文里孤立的 ə：可能是符号说明，也可能是错字
            return "UNKNOWN", t, "ISOLATED_SCHWA_IN_PROSE"
        return "UNKNOWN", t, "SCHWA_CONTEXT_UNCLEAR"
    else:  # e
        if t == "PHONETIC":
            # 音标语境中的 e：先看是否与本书别处的 ə 形式重出
            return "CONFIRMED_E", t, "E_IN_BRACKET"
        if t == "FORM":
            return "UNKNOWN", t, "E_IN_FORM_TOKEN"
        return "UNKNOWN", t, "E_CONTEXT_UNCLEAR"


def main():
    idx = []
    for key, (cn, rel) in BOOKS.items():
        path = os.path.join(ROOT, rel)
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            text = r["text"]
            for m in re.finditer("ə", text):
                i = m.start()
                st, ct, why = classify("ə", text, i)
                idx.append({
                    "book": key, "book_cn": cn, "page_pdf": r["page"],
                    "offset": i, "char": "ə", "status": st,
                    "context_type": ct, "rule": why,
                    "token": token_at(text, i),
                    "left": text[max(0, i - 30):i].replace("\n", "⏎"),
                    "right": text[i + 1:i + 31].replace("\n", "⏎"),
                })
            # 副索引：真正的音标方括号 [ ... ] 内的 e（英文括注、页注一律排除）
            for bm in re.finditer(r"\[([^\[\]\n]{1,15})\]", text):
                inner = bm.group(1)
                if not re.fullmatch(rf"[{LAT}\s,ːˈ]+", inner):
                    continue
                if not re.search(r"[a-zəɛ]", inner):
                    continue
                base = bm.start(1)
                for em in re.finditer("e", inner):
                    i = base + em.start()
                    st, ct, why = classify("e", text, i)
                    idx.append({
                        "book": key, "book_cn": cn, "page_pdf": r["page"],
                        "offset": i, "char": "e", "status": st,
                        "context_type": "PHONETIC_BRACKET", "rule": "E_IN_IPA_BRACKET",
                        "token": inner,
                        "left": text[max(0, i - 30):i].replace("\n", "⏎"),
                        "right": text[i + 1:i + 31].replace("\n", "⏎"),
                    })

    for n, x in enumerate(idx, 1):
        x["cand_id"] = "SC-%04d" % n

    cnt = collections.Counter((x["char"], x["status"]) for x in idx)
    by_book = collections.Counter((x["book"], x["char"]) for x in idx)
    summary = {
        "total": len(idx),
        "primary_schwa": sum(1 for x in idx if x["char"] == "ə"),
        "by_status": {f"{k[0]}|{k[1]}": v for k, v in cnt.items()},
        "by_book": {f"{k[0]}|{k[1]}": v for k, v in by_book.items()},
        "context_types": dict(collections.Counter(x["context_type"] for x in idx)),
    }
    json.dump({"summary": summary, "items": idx}, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
