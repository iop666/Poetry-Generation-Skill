#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-14 / C1：复现 2,447 / 2,740 / 4,510 三个集合，落地 work_id 清单与两两交并差。

只读 database/poetry.db（mode=ro），不写库。
输出：
  reports/tasks/2026-11-16/R2-14/LOGS/yq_set_2447.txt
  reports/tasks/2026-11-16/R2-14/LOGS/yq_set_2740.txt
  reports/tasks/2026-11-16/R2-14/LOGS/yq_set_4510.txt
  reports/tasks/2026-11-16/R2-14/YUANQU_2447_2740_4510_SET_RECONCILIATION.csv
  reports/tasks/2026-11-16/R2-14/LOGS/C1_counts.json
"""
import csv
import datetime
import json
import os
import re
import sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
DB = os.path.join(BASE, "database", "poetry.db")
OUT = os.path.join(BASE, "reports", "tasks", "2026-11-16", "R2-14")
LOG = os.path.join(OUT, "LOGS")
TS = datetime.datetime.now().isoformat(timespec="seconds")

HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002ffff]")
BR = re.compile(r"[（(][^）)]*[）)]")
CHANG = re.compile(r"[（(][^）)]*唱[）)]")
JUDOU = set("，。；？！、：")

SQL_2447 = ("SELECT work_id FROM works WHERE genre='曲' "
            "AND text_raw LIKE '%(%唱)%'")
SQL_2740 = ("SELECT work_id, text_raw FROM works WHERE genre='曲' "
            "-- 再以正则 re.search(r'[（(][^）)]*唱[）)]', text_raw) 过滤")
SQL_4510 = ("A: 正则 [（(][^）)]*唱[）)] 命中\n"
            "B: title_raw 含句读[，。；？！、：] 且 length(title_raw)>=17\n"
            "C: 去掉[（(][^）)]*[）)]后汉字数<12\n"
            "SET = A ∪ B ∪ C")


def han(s: str) -> int:
    return len([ch for ch in s if HAN.match(ch)])


def main() -> None:
    conn = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT work_id,title_raw,text_raw,char_count FROM works WHERE genre='曲'"
    ).fetchall()

    s2447 = [w for w, t, x, _ in rows if re.search(r"\([^)]*唱\)", x)]
    # SQL LIKE '%(%唱)%' 语义：半角括号、括号内可含任意字符但不得含 ')'。
    s2740 = [w for w, t, x, _ in rows if CHANG.search(x)]
    B = [w for w, t, x, _ in rows if (JUDOU & set(t)) and len(t) >= 17]
    C = [w for w, t, x, _ in rows if han(BR.sub("", x)) < 12]

    A, Bs, Cs = set(s2740), set(B), set(C)
    U = A | Bs | Cs
    S1 = set(s2447)

    def dump(name, ids):
        path = os.path.join(LOG, name)
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write("\n".join(sorted(ids)) + "\n")
        return os.path.relpath(path, OUT)

    f1 = dump("yq_set_2447.txt", S1)
    f2 = dump("yq_set_2740.txt", A)
    f3 = dump("yq_set_4510.txt", U)

    counts = {
        "generated_at": TS,
        "works_yuanqu": len(rows),
        "R2_12_2447": len(S1),
        "R2_13_2740": len(A),
        "R2_13_4510": len(U),
        "A_2740_regex": len(A),
        "B_title_judou_ge17": len(Bs),
        "C_han_lt12_raw": len(Cs),
        "A_and_B": len(A & Bs),
        "A_and_C": len(A & Cs),
        "B_and_C": len(Bs & Cs),
        "C_net_new": len(Cs - Bs),
        "A_minus_2447": len(A - S1),
        "2447_minus_A": len(S1 - A),
        "4510_minus_2740": len(U - A),
        "4510_minus_2447": len(U - S1),
        "sum_parts": len(A) + len(Bs) + len(Cs - Bs),
    }
    with open(os.path.join(LOG, "C1_counts.json"), "w", encoding="utf-8") as f:
        json.dump(counts, f, ensure_ascii=False, indent=2)

    csv_path = os.path.join(OUT, "YUANQU_2447_2740_4510_SET_RECONCILIATION.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["set_name", "definition_sql", "n_records", "work_id_file",
                    "intersection_with_prev", "diff_with_prev", "generated_at"])
        w.writerow(["R2_12_2447", SQL_2447, len(S1), f1, "", "", TS])
        w.writerow(["R2_13_2740", SQL_2740, len(A), f2,
                    len(A & S1), f"{len(A - S1)} (prev⊄cur={len(S1 - A)})", TS])
        w.writerow(["R2_13_4510", SQL_4510, len(U), f3,
                    len(U & A), f"{len(U - A)}", TS])
    print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
