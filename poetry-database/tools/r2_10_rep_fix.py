#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""補生成 CROSS_ROUND_METRIC_RECONCILIATION.csv 與 TEST_RESULTS_R2_10.md。"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REP = os.path.join(ROOT, "reports", "tasks", "2026-11-15", "R2-10")
F = json.load(open(os.path.join(ROOT, "raw", "r2_10", "facts.json"), encoding="utf-8"))

ROWS = [
    ("集韻小韻（舊法/202頁）", 4344, "—", "舊解析器，○切段＋逐〈〉串接取文N，202 頁",
     "CONFIRMED_DIFFERENT_DEFINITION", "NO", "頁集快照已失，無法逐位復原"),
    ("集韻小韻（舊法/206頁）", 4432, "—", "同上，頁集補齊", "CONFIRMED_DIFFERENT_DEFINITION",
     "YES", "同腳本重跑得 4,432"),
    ("集韻小韻（新法/206頁）", 4169, "—", "○後≥6字且首字可匹配", "CONFIRMED_DIFFERENT_DEFINITION",
     "YES", "本輪入庫值"),
    ("集韻頁面○標記總數", 4442, "—", "全頁「○」字符計數", "CONFIRMED_SAME_DEFINITION",
     "YES", "本輪新基準：4,442−10=4,432；4,442−273=4,169"),
    ("集韻字數（舊法202頁）", 51803, "—", "舊解析器 Σ文N", "CONFIRMED_DIFFERENT_DEFINITION", "NO", ""),
    ("集韻字數（舊法206頁）", 52983, "—", "舊解析器 Σ文N", "CONFIRMED_SAME_DEFINITION", "YES", ""),
    ("集韻字數（全頁文N求和）", 53952, "—", "全頁正則求和", "CONFIRMED_DIFFERENT_DEFINITION", "YES",
     "與原書 53,525 差 0.8%"),
    ("集韻字數（原書自述）", 53525, "—", "四庫提要記載", "SOURCE_DIFFERENCE", "NO", "非本項目統計"),
    ("集韻字數（首文N之和）", 50132, "—", "每小韻段首個文N", "CONFIRMED_SAME_DEFINITION", "YES", ""),
    ("集韻字頭估計", 49084, "—", "〈〉前緊鄰漢字全計", "COMPUTED", "YES", "估計值，非原書數"),
    ("平水韻字頭（繁）", 8564, "—", "count(distinct charx)", "CONFIRMED_SAME_DEFINITION", "YES", "唯一可稱「字頭」者"),
    ("平水韻字頭（簡）", 8361, "—", "繁簡歸併後", "CONFIRMED_DIFFERENT_DEFINITION", "NO", "未重算"),
    ("平水韻記錄數", 10662, "—", "表內行數", "CONFIRMED_SAME_DEFINITION", "YES", ""),
    ("平水韻韻目累加", 10714, "—", "sum(n_chars)", "DUPLICATE_COUNT", "YES", "含跨韻重複 52"),
    ("平水韻字頭（Phase 0）", 8116, "—", "早期未清洗值", "SUPERSEDED", "NO", "作廢"),
    ("廣韻小韻候選", 4771, "—", "注文含「切」即小韻首", "PROCESSING_ERROR", "YES", "含 1,416 又音條目"),
    ("廣韻嚴格小韻首", 2907, "—", "反切在注文最前端且不以又起頭", "CONFIRMED_DIFFERENT_DEFINITION", "YES", "本輪新口徑"),
    ("廣韻反切上字（舊）", 4658, "—", "存的是下字", "PROCESSING_ERROR", "YES", "已修正"),
    ("閱讀有記錄頁數", 436, "—", "核驗檔 pages_covered", "CONFIRMED_DIFFERENT_DEFINITION", "YES",
     "含 1 頁 QUOTATION；頁賬本 CLAIM_RECORDED 為 435"),
    ("音標總數", 688, "—", "四類之和", "CONFIRMED_SAME_DEFINITION", "YES", "430+29+130+99"),
    ("例詞可信關聯（累計表）", 196, "—", "310−114(NO_MATCH)", "PROCESSING_ERROR", "YES", "標籤誤用：實為「有候選」"),
    ("例詞 VERIFIED", 166, "—", "50 exact＋116 variant", "CONFIRMED_SAME_DEFINITION", "YES", ""),
    ("原圖核驗（R2-09 宣稱）", 60, "—", "樣本數", "DUPLICATE_COUNT", "YES", "實際符號級 0"),
    ("原圖核驗（歷史累計）", 28, "—", "含重複 1 條", "DUPLICATE_COUNT", "YES", "唯一對象 27"),
    ("詞譜符號級核驗（本輪）", 49, "—", "文字層逐句比對", "CONFIRMED_SAME_DEFINITION", "YES", "另 11 條文字層殘缺"),
    ("新增工具數", 15, "—", "口徑不明", "UNVERIFIABLE", "NO", "r2_09_*.py 共 25 檔，分析腳本 19"),
    ("累計新增表", 36, "—", "R2-07 10＋R2-08 12＋R2-09 14", "CONFIRMED_SAME_DEFINITION", "YES", ""),
    ("報告份數/交付包檔數", 45, "—", "兩個不同集合", "CONFIRMED_DIFFERENT_DEFINITION", "YES", "149 為 ZIP 內檔數"),
    ("資料庫大小（R2-08）", 690, "—", "無位元組無雜湊", "UNVERIFIABLE", "NO", "大於當前 672 MiB，至少一個數字非實測"),
]

with open(os.path.join(REP, "CROSS_ROUND_METRIC_RECONCILIATION.csv"), "w", newline="",
          encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["metric", "old_value", "new_value", "definition", "status",
                "reproducible", "note"])
    for r in ROWS:
        w.writerow(list(r))

tr = json.load(open(os.path.join(ROOT, "raw", "r2_10", "independent", "test_results_r2_10.json"),
                    encoding="utf-8"))
cats = {}
for x in tr:
    cats.setdefault(x["category"], []).append(x)
lines = ["# R2-10 測試結果", "",
         f"新增 {len(tr)} 項，通過 {F['test_pass']}，失敗 {len(tr) - F['test_pass']}。",
         "舊 R2-09 的 71 項原樣重跑：71 通過 0 失敗（見 `REGRESSION_COMPARISON.md`）。", "",
         "## 1 按類別", "", "| 類別 | 項數 | 通過 | 失敗 |", "|---|---:|---:|---:|"]
for k, v in cats.items():
    lines.append(f"| {k} | {len(v)} | {sum(1 for x in v if x['result'] == 'PASS')} | "
                 f"{sum(1 for x in v if x['result'] != 'PASS')} |")
lines += ["", "## 2 失敗項（未修改期望值）", ""]
for x in tr:
    if x["result"] != "PASS":
        lines += [f"### {x['code']}　{x['description']}", "",
                  f"- 期望：`{x['expected']}`　實測：`{x['actual']}`",
                  f"- 判定：**真實缺陷，保留 FAIL**", ""]
lines += ["## 3 全部測試", "", "| 代號 | 類別 | 說明 | 期望 | 實測 | 結果 |", "|---|---|---|---|---|---|"]
for x in tr:
    lines.append(f"| {x['code']} | {x['category']} | {x['description']} | "
                 f"`{x['expected']}` | `{x['actual']}` | {x['result']} |")
lines += ["", "## 4 須聲明", "",
          "約 30 項屬於「用自己的口徑量自己的資料」（如 206、4,169、20,530 等常數斷言），",
          "通過只表示資料自洽，不構成獨立驗證。真正的獨立驗證只有 K1 的 70 條交叉複核。"]
with open(os.path.join(REP, "TEST_RESULTS_R2_10.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("done")
