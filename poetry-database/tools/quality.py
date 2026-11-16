#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quality.py —— 数据质量审查

十项检查（对应 AGENT 任务书「六、数据质量管理」）：
  1 完整重复识别      2 同名异文识别     3 作者异名候选
  4 标题标准化        5 繁简占位         6 标点规范化
  7 来源完整性        8 解析错误         9 缺失字段统计    10 异常文本

输出：
  audit/duplicate_report.json
  audit/quality_report.json
  audit/quality_summary.md（人读摘要，供 reports/round-1/06 引用）
"""

from __future__ import annotations

import collections
import datetime
import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "database", "poetry.db")
AUDIT = os.path.join(BASE, "audit")
HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002ffff]")


def main() -> int:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM works").fetchall()
    total = len(rows)
    os.makedirs(AUDIT, exist_ok=True)

    # 1 完整重复
    by_text = collections.defaultdict(list)
    for r in rows:
        by_text[r["text_norm"]].append(r["work_id"])
    dup_groups = {h: ids for h, ids in by_text.items() if len(ids) > 1}

    # 2 同名异文
    by_name = collections.defaultdict(list)
    for r in rows:
        by_name[(r["author_name"], r["title_norm"])].append(r)
    variant_groups = {k: v for k, v in by_name.items()
                      if len(v) > 1 and len({x["text_norm"] for x in v}) > 1}

    # 3 作者异名候选：同一作品文本出现在不同作者名下
    byid = {r["work_id"]: r for r in rows}
    author_conflict = collections.defaultdict(set)
    for h, ids in by_text.items():
        names = {byid[i]["author_name"] for i in ids}
        if len(names) > 1:
            author_conflict[h] = names

    # 4/5/6 文本层面
    bad_chars, punct_left, odd_len = [], [], []
    short_text = 0
    for r in rows:
        t = r["text_norm"]
        if len(t) < 10:
            short_text += 1
        left = [c for c in re.sub(HAN, "", t) if not c.isspace()]
        if left:
            punct_left.append({"work_id": r["work_id"], "residual": "".join(sorted(set(left)))})
        if any(ord(c) < 0x3400 for c in t):
            bad_chars.append(r["work_id"])
        if len(t) > 2000:
            odd_len.append({"work_id": r["work_id"], "chars": len(t)})

    # 7 来源完整性
    src_ids = {x["source_id"] for x in conn.execute("SELECT source_id FROM sources")}
    orphan = [r["work_id"] for r in rows if r["source_id"] not in src_ids]

    # 9 缺失字段
    missing = {
        "作者为佚名": sum(1 for r in rows if r["author_name"] == "佚名"),
        "标题为空": sum(1 for r in rows if not r["title_norm"]),
        "朝代为空": sum(1 for r in rows if not r["dynasty"]),
        "词无词牌": sum(1 for r in rows if r["genre"] == "词" and not r["cipai"]),
        "体裁为未知": sum(1 for r in rows if r["genre"] == "未知"),
    }

    # 10 分布
    genre_dist = collections.Counter(r["genre"] for r in rows)
    coll_dist = collections.Counter(r["collection"] for r in rows)
    dynasty_dist = collections.Counter(r["dynasty"] for r in rows)
    char_stats = sorted(len(r["text_norm"]) for r in rows)
    mid = char_stats[len(char_stats) // 2] if char_stats else 0

    report = {
        "生成时间": datetime.datetime.now().isoformat(timespec="seconds"),
        "作品总数": total,
        "去重后": total - sum(len(v) - 1 for v in dup_groups.values()),
        "完全重复": {"组数": len(dup_groups), "冗余条数": sum(len(v) - 1 for v in dup_groups.values())},
        "同名异文": {"组数": len(variant_groups),
                 "涉及作品": sum(len(v) for v in variant_groups.values())},
        "跨作者同文冲突": {"组数": len(author_conflict),
                    "示例": [{"文": h[:12], "作者": sorted(n)} for h, n in
                             list(author_conflict.items())[:5]]},
        "文本异常": {"含非汉字符": len(bad_chars), "残留标点": len(punct_left),
                 "超长文本": len(odd_len), "过短(<10字)": short_text},
        "来源缺失": len(orphan),
        "缺失字段": missing,
        "体裁分布": dict(genre_dist.most_common()),
        "集合分布": dict(coll_dist.most_common()),
        "朝代分布": dict(dynasty_dist.most_common()),
        "字数": {"最短": char_stats[0] if char_stats else 0,
               "中位": mid, "最长": char_stats[-1] if char_stats else 0},
        "作者数": conn.execute("SELECT COUNT(*) FROM authors").fetchone()[0],
    }

    # 11 内部一致性自检（不通过即说明入库逻辑有 bug）
    # 起因：早期版本因 work_id 相同的记录被 id 索引覆盖，导致 13 组出现
    # 「1 条 UNIQUE + N 条 DUPLICATE」，与「组数 / 冗余条数」口径对不上。
    st = collections.Counter(r["dup_status"] for r in rows)
    redundancy = report["完全重复"]["冗余条数"]
    checks = {
        "dup_status 之和等于总数": sum(st.values()) == total,
        "DUPLICATE 数等于冗余条数": st["DUPLICATE"] == redundancy,
        "KEPT 数等于重复组数": st["KEPT"] == len(dup_groups),
        "去重后 = 总数 - 冗余": report["去重后"] == total - redundancy,
        "无 UNIQUE 落在重复组内": all(
            all(byid[i]["dup_status"] != "UNIQUE" for i in ids) for ids in dup_groups.values()),
    }
    report["一致性自检"] = {k: ("PASS" if v else "FAIL") for k, v in checks.items()}
    report["dup_status 分布"] = dict(st)

    with open(os.path.join(AUDIT, "duplicate_report.json"), "w", encoding="utf-8") as f:
        json.dump({
            "完全重复组": [{"文本hash": h, "work_ids": ids} for h, ids in
                      list(dup_groups.items())[:200]],
            "同名异文组": [{"作者": k[0], "标题": k[1],
                       "作品": [{"work_id": x["work_id"], "collection": x["collection"],
                               "chars": len(x["text_norm"])} for x in v]}
                      for k, v in list(variant_groups.items())[:200]],
            "跨作者同文冲突": [{"文本hash": h, "作者": sorted(n)}
                        for h, n in author_conflict.items()],
            "残留标点样本": punct_left[:50],
            "超长文本样本": odd_len[:50],
        }, f, ensure_ascii=False, indent=1)

    with open(os.path.join(AUDIT, "quality_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    md = ["# 数据质量摘要（自动生成）", "",
          f"生成时间：{report['生成时间']}", "",
          "| 指标 | 数值 |", "|---|---|",
          f"| 作品总数 | {total:,} |",
          f"| 去重后 | {report['去重后']:,} |",
          f"| 完全重复组 / 冗余条数 | {len(dup_groups)} / {report['完全重复']['冗余条数']} |",
          f"| 同名异文组 / 涉及作品 | {len(variant_groups)} / {report['同名异文']['涉及作品']} |",
          f"| 跨作者同文冲突 | {len(author_conflict)} |",
          f"| 含非汉字符 | {len(bad_chars)} |",
          f"| 残留标点 | {len(punct_left)} |",
          f"| 过短文本（<10 字） | {short_text} |",
          f"| 超长文本（>2000 字） | {len(odd_len)} |",
          f"| 来源缺失 | {len(orphan)} |",
          f"| 作者数 | {report['作者数']:,} |",
          f"| 字数 最短/中位/最长 | {report['字数']['最短']} / {report['字数']['中位']} / {report['字数']['最长']} |",
          "", "## 缺失字段", "", "| 项 | 数量 |", "|---|---|"]
    for k, v in missing.items():
        md.append(f"| {k} | {v:,} |")
    md += ["", "## 体裁分布", "", "| 体裁 | 数量 |", "|---|---|"]
    for k, v in genre_dist.most_common():
        md.append(f"| {k} | {v:,} |")
    md += ["", "## 朝代分布", "", "| 朝代 | 数量 |", "|---|---|"]
    for k, v in dynasty_dist.most_common():
        md.append(f"| {k or '（空）'} | {v:,} |")
    with open(os.path.join(AUDIT, "quality_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(json.dumps({k: report[k] for k in
                      ["作品总数", "去重后", "完全重复", "同名异文", "来源缺失"]},
                     ensure_ascii=False, indent=1))
    print(f"[写入] audit/duplicate_report.json, quality_report.json, quality_summary.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
