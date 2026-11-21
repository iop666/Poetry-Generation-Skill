#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从本地原始证据生成公开版本（R2-16B 审核裁决，2026-11-21）。

裁决内容（外部审核 2026-11-21）：
- ocr_samples.json    维持 WITHHELD（原始含 head 逐字文本的文件不公开）；
  公开版只保留 页码、字符统计、质量标记（book_id / page / chars / 5 个布尔标记 / engine），
  不保留 OCR 正文前缀 head。
- theory_locate.json  维持 WITHHELD（原始含逐字引文 quote 的文件不公开）；
  公开版保留 页码、主题、核验状态，引文以 SHA-256 哈希代替（quote_sha256）。

本地原始文件永不删除、永不修改；本脚本只读取原件、写入 *_public.json。
重跑幂等：输出字节由原件决定。
"""
import hashlib
import json
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "raw" / "r2_04_evidence"


def run():
    # ---- ocr_samples_public.json：去掉 head ----
    src = json.loads((RAW / "ocr_samples.json").read_text(encoding="utf-8"))
    pub = [
        {k: it[k] for k in (
            "book_id", "page", "chars", "empty",
            "has_pingze_symbols", "has_rusheng_mark", "has_footnote", "engine",
        )}
        for it in src
    ]
    out1 = RAW / "ocr_samples_public.json"
    out1.write_text(
        json.dumps(pub, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n",
    )

    # ---- theory_locate_public.json：quote → SHA-256 ----
    src = json.loads((RAW / "theory_locate.json").read_text(encoding="utf-8"))
    pub = []
    for it in src:
        item = {k: it[k] for k in (
            "id", "book_id", "old_page", "topic", "verified_pages", "verdict",
        )}
        item["quote_sha256"] = hashlib.sha256(
            it["quote"].encode("utf-8")
        ).hexdigest()
        pub.append(item)
    out2 = RAW / "theory_locate_public.json"
    out2.write_text(
        json.dumps(pub, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n",
    )

    print("written:", out1.name, out1.stat().st_size, "bytes;",
          out2.name, out2.stat().st_size, "bytes")
    # 自检：公开版不得含 head / quote 逐字字段
    assert "head" not in out1.read_text(encoding="utf-8"), "ocr_samples_public 泄漏 head"
    t2 = out2.read_text(encoding="utf-8")
    assert "quote_sha256" in t2 and '"quote"' not in t2, "theory_locate_public 泄漏 quote"
    print("SELF-CHECK PASS: 公开版不含 head / quote 逐字文本")


if __name__ == "__main__":
    run()
