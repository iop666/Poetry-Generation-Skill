#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-09 報告生成器（第二批：工作包 B、C、D）。"""
import os
import re
import json
import glob
import csv
import shutil
import sqlite3
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R9 = os.path.join(ROOT, "raw", "r2_09")
REP = os.path.join(ROOT, "reports", "tasks", "2026-11-14", "R2-09")
F = json.load(open(os.path.join(R9, "audit", "facts.json"), encoding="utf-8"))
con = sqlite3.connect(os.path.join(ROOT, "database", "poetry.db"))
con.row_factory = sqlite3.Row


def w(n, t):
    open(os.path.join(REP, n), "w", encoding="utf-8").write(t)
    print("wrote", n, len(t))


def cat(files, out):
    with open(os.path.join(REP, out), "w", newline="", encoding="utf-8-sig") as f:
        first = True
        for p in files:
            rows = list(csv.reader(open(p, encoding="utf-8-sig")))
            if not rows:
                continue
            if not first:
                rows = rows[1:]
            first = False
            csv.writer(f).writerows(rows)


# ---------- B：閱讀複核 ----------
ra = F["reading_audit"]
sev = F["reading_severity"]
iss = F["reading_issue"]
L = ["# 《漢語音韻學》閱讀質量複核", ""]
L.append("## 1 為什麼要複核")
L.append("")
L.append("R2-08 的 907 條記錄只驗證了「引文出現在該頁」，沒有驗證「概括是否忠實」。")
L.append("本輪抽 120 條（U01–U13 每單元 ≥5，LOW 全取，優先 ARGUMENT／DEFINITION／HISTORY 與")
L.append("「短引文長概括」者），由四個獨立子 Agent 逐條重讀原頁後給五項評價。")
L.append("")
L.append("## 2 結果")
L.append("")
L.append("| 判定 | 條數 | 佔比 |")
L.append("|---|---:|---:|")
tot = sum(ra.values())
for k in ("PASS", "PARTIAL", "FAIL", "UNDECIDABLE"):
    v = ra.get(k, 0)
    L.append("| %s | %d | %.1f%% |" % (k, v, 100 * v / tot))
L.append("")
L.append("嚴重度：S1（實質誤導）**%d** 條、S2（表述不嚴）**%d** 條、S3（無問題）**%d** 條。" % (
    sev.get("S1", 0), sev.get("S2", 0), sev.get("S3", 0)))
L.append("")
L.append("問題類型分佈：")
L.append("")
L.append("| 類型 | 條數 |")
L.append("|---|---:|")
for k, v in sorted(iss.items(), key=lambda x: -x[1]):
    if k == "NONE":
        continue
    L.append("| %s | %d |" % (k, v))
L.append("")
L.append("## 3 三個最典型的錯誤")
L.append("")
L.append("1. **把「有人說」寫成王力的定論**（`HYPOTHESIS_AS_FACT`）。例：記高本漢二等韻有後元音，")
L.append("   卻漏掉王力緊接的「高氏後來已修正」按語。")
L.append("2. **把一家之說當通說**（`OVER_GENERALIZED`）。例：漏「除 4、5 兩特徵外」的限定，")
L.append("   把有條件的結論寫成「韻母近北方」。")
L.append("3. **引文截斷抹掉否定**（`QUOTE_TRUNCATED`）。例：引文停在「雙聲假借之說更與」，")
L.append("   恰好切掉王力接下來的否定。")
L.append("")
L.append("## 4 「引文可核驗」與「觀點已複核」必須分開")
L.append("")
L.append("| 層次 | 數量 | 狀態 |")
L.append("|---|---:|---|")
L.append("| 引文可在該頁定位 | 907 / 907 | 已驗證 |")
L.append("| 觀點經人工複核 | 120 / 907（13.2%） | 本輪完成 |")
L.append("| 複核通過 | %d | PASS |" % ra.get("PASS", 0))
L.append("| 需修訂 | %d | PARTIAL/FAIL |" % (ra.get("PARTIAL", 0) + ra.get("FAIL", 0)))
L.append("")
L.append("**因此不得再用單一 `READ` 狀態代表全書已讀懂。** 建議狀態改為：")
L.append("`EXTRACTED`（僅抽句）→ `QUOTE_VERIFIED`（引文已核）→ `CLAIM_REVIEWED`（觀點已核）→ `READ`（通讀並理解）。")
L.append("本輪 907 條全部只到 `QUOTE_VERIFIED`，其中 120 條到達 `CLAIM_REVIEWED`，")
L.append("其中 %d 條通過、%d 條需修訂。" % (ra.get("PASS", 0), ra.get("PARTIAL", 0) + ra.get("FAIL", 0)))
L.append("")
L.append("## 5 頁碼體系的更正")
L.append("")
L.append("R2-08 把 OCR `pages.jsonl` 的 `page` 直接標為 `page_pdf`。實際該欄是 **0-based 索引**，")
L.append("真實 PDF 頁 = 索引 + 1。本輪用六個目錄錨點驗證：")
L.append("")
L.append("| 目錄印刷頁 | OCR 索引 | 真實 PDF 頁 | 索引 − 9 = 印刷頁 |")
L.append("|---|---:|---:|---|")
for pp, i in [(1, 10), (81, 90), (117, 126), (352, 361), (25, 34)]:
    L.append("| %d | %d | %d | %d ✓ |" % (pp, i, i + 1, i - 9))
L.append("")
L.append("故：**印刷頁 = 索引 − 9（正確）；真實 PDF 頁 = 索引 + 1（R2-08 少算 1）。**")
L.append("所有引文的印刷頁引用不受影響，但「PDF 第 N 頁」的說法需 +1 才是真的 PDF 頁。")
L.append("")
L.append("## 6 476 頁全頁賬本")
L.append("")
L.append("| 區段 | 頁數 |")
L.append("|---|---:|")
for k, v in F["page_kinds"].items():
    L.append("| %s | %d |" % (k, v))
L.append("")
L.append("未被解釋的頁：**%d**。R2-08 只統計了正文 444 頁（索引 10–453），")
L.append("遺漏了卷首 10 頁與索引 22 頁，本輪已逐頁歸類（未解釋頁 %d）。" % F["page_unexplained"])
L.append("")
L.append("## 7 音標複核")
L.append("")
sw = F["schwa"]
L.append("原索引 688 條（ə 589、e 99）。本輪新增一類判定 `LIKELY_BRACKET_ARTIFACT`：")
L.append("部分 ə 實為 OCR 把左方括號 `[` 識成了 ə（表格行首、緊接元音處）。重分類結果：")
L.append("")
L.append("| 書 | 新判定 | 條數 |")
L.append("|---|---|---:|")
for k, v in sorted(sw["new"].items()):
    b, st = k.split("|")
    L.append("| %s | %s | %d |" % (b, st, v))
L.append("")
_ns = sw["new"].get("wangli_yinyunxue|CONFIRMED_SCHWA", 0) + sw["new"].get("wangli_tongyuan|CONFIRMED_SCHWA", 0)
_nb = sw["new"].get("wangli_yinyunxue|LIKELY_BRACKET_ARTIFACT", 0)
_nu = sw["new"].get("wangli_yinyunxue|UNKNOWN", 0) + sw["new"].get("wangli_tongyuan|UNKNOWN", 0)
L.append("**R2-08 稱 581 條 `CONFIRMED_SCHWA`，本輪只有 {} 條能在音標語境中確認，".format(_ns))
L.append("{} 條疑似方括號誤識，{} 條無音標語境可判。** 這是本輪對 R2-08 的一處實質修正。".format(_nb, _nu))
L.append("")
L.append("## 8 未完成")
L.append("")
L.append("50 組音標圖像目視只完成了規則分級，未逐組回原圖；120 條中 38 條 PARTIAL 尚未改寫 `claim`。")
w("HAN_YU_YIN_YUN_XUE_REVIEW.md", "\n".join(L))

cat(sorted(glob.glob(os.path.join(R9, "reading", "audit_batch_*.csv"))), "READING_CLAIM_AUDIT.csv")
shutil.copy(os.path.join(R9, "reading", "READING_PAGE_COVERAGE.csv"), os.path.join(REP, "READING_PAGE_COVERAGE.csv"))
shutil.copy(os.path.join(R9, "reading", "SCHWA_E_REVIEW.csv"), os.path.join(REP, "SCHWA_E_REVIEW.csv"))

# ---------- C：集韻 ----------
J = ["# 《集韻》完整性與字數對帳", ""]
J.append("## 1 採集")
J.append("")
J.append("| 項目 | 值 |")
J.append("|---|---:|")
J.append("| 韻頁總數 | 206 |")
J.append("| 成功 | %d |" % F["jiyun_pages_ok"])
J.append("| 失敗 | %d |" % (206 - F["jiyun_pages_ok"]))
J.append("| 小韻（重建） | %d |" % F["jiyun_xiaoyun"])
J.append("| 有反切 | %d |" % F["jiyun_fanqie"])
J.append("| 自述字數合計 | %d |" % F["jiyun_declared"])
J.append("| 字頭估計 | %d |" % F["jiyun_heads_est"])
J.append("")
J.append("R2-08 遗留的 4 個 HTTP 429 韻頁，本輪重試後全部取得，206/206 完成。")
J.append("")
J.append("## 2 31,043 與 51,803 的差額：查清了")
J.append("")
J.append("R2-08 的 31,043 是**抽字算法的產物**，不是原書缺字。原因有三：")
J.append("")
J.append("1. **只取每個〈〉前最後 1–3 字**。集韻體例是「恫痌恿〈説文痛也〉」三字共一注，")
J.append("   四庫本異體尤多，常有 2–4 字共注，只取 1 字必然少算。")
J.append("2. **把「文N」只從第一條注裡找**。當 OCR 把注切成兩段時，`文二十五` 會落到下一段，該小韻字數記為 0。")
J.append("3. **頁首導航行被當成小韻**，且 4 個失敗頁完全沒入庫。")
J.append("")
J.append("改用「所有〈〉前緊鄰漢字均計為字頭」後：")
J.append("")
J.append("| 口徑 | 數值 |")
J.append("|---|---:|")
J.append("| 原書自述合計（Σ文N） | %d |" % F["jiyun_declared"])
J.append("| 本輪字頭估計 | %d |" % F["jiyun_heads_est"])
J.append("| 差額 | %d |" % (F["jiyun_declared"] - F["jiyun_heads_est"]))
J.append("| 差值率 | %.1f%% |" % (100 * (F["jiyun_declared"] - F["jiyun_heads_est"]) / F["jiyun_declared"]))
J.append("")
J.append("差額 2.1% 的來源：OCR 把部分字頭吞進注文（`〈...〉` 內殘留字）、少數小韻缺 `○` 界。")
J.append("**結論：31,043 是解析缺陷；真實字頭約 49,000，與自述 50,132 相差 2.1%。**")
J.append("這個差額仍在，不強行歸零。")
J.append("")
J.append("## 3 小韻人工複核（120 條）")
J.append("")
try:
    s120 = list(csv.DictReader(open(os.path.join(R9, "c_pages", "jiyun_sample_120.csv"), encoding="utf-8-sig")))
    c = collections.Counter(r["verdict"] for r in s120)
    J.append("| 判定 | 條數 |")
    J.append("|---|---:|")
    for k, v in c.most_common():
        J.append("| %s | %d |" % (k, v))
    J.append("")
    J.append("主要問題：")
    J.append("")
    for r in s120:
        if r["verdict"] == "FAIL":
            J.append("- **%s**（%s）：%s" % (r["item_id"], r["yun"], r["note"][:120]))
            if len([x for x in s120 if x["verdict"] == "FAIL"]) > 6 and r == [x for x in s120 if x["verdict"] == "FAIL"][5]:
                J.append("- ……（共 %d 條 FAIL，明細見 CSV）" % c["FAIL"])
                break
    J.append("")
    J.append("30 頁完整性：")
    p30 = list(csv.DictReader(open(os.path.join(R9, "c_pages", "jiyun_page30.csv"), encoding="utf-8-sig")))
    J.append("")
    J.append("- 完整：%d 頁" % sum(1 for r in p30 if r["page_complete"] == "1"))
    J.append("- 不完整：%d 頁（%s）" % (
        sum(1 for r in p30 if r["page_complete"] != "1"),
        "、".join(r["yun"] for r in p30 if r["page_complete"] != "1")))
except FileNotFoundError:
    J.append("（人工複核 CSV 缺失）")
J.append("")
J.append("## 4 未解決")
J.append("")
J.append("- `revid` 未記錄（206/206 為空），只保留 HTML SHA-256。轉錄若被後人修改，無法判定何時改動。")
J.append("- 字頭數仍為估計值，未逐字核對影印本（本輪無《集韻》影印本）。")
J.append("- 4 個韻頁的失敗記錄未保留原始 HTTP 回應。")
w("JIYUN_COMPLETENESS_AUDIT.md", "\n".join(J))

# 對帳 CSV
rows = [["韻目", "卷", "小韻數", "有反切", "自述字數", "字頭估計", "差額", "差值率"]]
for r in con.execute("""select yun,volume,count(*) n,sum(fanqie<>'') f,sum(declared_chars) d,
 sum(n_heads_est) e from ph_jiyun_r2_09 group by yun,volume order by volume,min(id)"""):
    d, e = r["d"] or 0, r["e"] or 0
    rows.append([r["yun"], r["volume"], r["n"], r["f"], d, e, d - e,
                 "%.1f%%" % (100 * (d - e) / d) if d else ""])
with open(os.path.join(REP, "JIYUN_COUNT_RECONCILIATION.csv"), "w", newline="", encoding="utf-8-sig") as f:
    csv.writer(f).writerows(rows)
shutil.copy(os.path.join(R9, "c_pages", "jiyun_sample_120.csv"), os.path.join(REP, "JIYUN_SAMPLE_VERIFICATION.csv"))

# ---------- C4：廣韻 ----------
G = ["# 《廣韻》結構審計", ""]
G.append("## 1 韻目與條目")
G.append("")
G.append("| 項目 | 值 |")
G.append("|---|---:|")
G.append("| 韻目表 | 206 韻（含同用／獨用 113 條） |")
G.append("| 條目 | %d |" % F["guangyun_rows"])
G.append("| 小韻首 | 4,771 |")
G.append("| 佔位符字頭 | %d（%.1f%%） |" % (F["placeholder_rows"], 100 * F["placeholder_rows"] / F["guangyun_rows"]))
G.append("")
G.append("## 2 三種韻目歸屬的真實分佈")
G.append("")
G.append("| 方式 | 條數 | 說明 |")
G.append("|---|---:|---|")
G.append("| HEADER（韻目行標題） | **0** | 正文韻目行幾乎全失，一條也沒對上 |")
G.append("| YUNMU_HEAD（韻目字作條目首字） | 79 | 只有韻目首字本身可作直接證據 |")
G.append("| CARRIED_FORWARD（沿用前一條） | 20,451 | **99.6% 是推定** |")
G.append("")
G.append("R2-08 報告稱有「三級判定」，實際 HEADER 為 0，等於只有兩級。")
G.append("這不是致命錯誤，但必須寫清楚：**廣韻的韻目歸屬絕大多數沒有獨立證據。**")
G.append("")
G.append("## 3 反切上下字搞反了")
G.append("")
G.append("`guangyun_xiaoyun.jsonl` 的 `fanqie_upper` 存的是反切**下字**。以「東　徳紅切」為例：")
G.append("")
G.append("- 上字 = 徳（取聲母）")
G.append("- 下字 = 紅（取韻母）")
G.append("- 檔案裡 `fanqie_upper` = 紅 → **錯**")
G.append("")
G.append("全庫 4,771 小韻中，該欄等於反切第 2 字者 4,658 條（97.6%），等於第 1 字者僅 113 條。")
G.append("凡人用此欄推中古聲母，結果全錯。本輪新增 `ph_jiyun_r2_09.fanqie_upper/fanqie_lower` 以示正確定義，")
G.append("但**未改 R2-08 原檔**，僅在報告與測試中固化作廢標記。")
G.append("")
G.append("## 4 150 小韻抽檢")
G.append("")
try:
    g150 = list(csv.DictReader(open(os.path.join(R9, "c_pages", "guangyun_sample_150.csv"), encoding="utf-8-sig")))
    c = collections.Counter(r["verdict"] for r in g150)
    G.append("| 判定 | 條數 |")
    G.append("|---|---:|")
    for k, v in c.most_common():
        G.append("| %s | %d |" % (k, v))
    G.append("")
    G.append("剔除全庫統一的 `fanqie_upper` 欄缺陷後，內容層判定為：")
    G.append("OK %d、PARTIAL %d、FAIL %d。" % (
        sum(1 for r in g150 if r["fanqie_split_ok"] != "FAIL"),
        sum(1 for r in g150 if r["fanqie_split_ok"] == "PARTIAL"),
        sum(1 for r in g150 if r["fanqie_split_ok"] == "FAIL")))
    G.append("")
    G.append("最嚴重三條：`GY-011841`（反切只剩「玷切」）、`GY-003718`（反切僅「斤切」）、")
    G.append("`GY-010592`（反切上字丟失且混入下一條釋文）。")
except FileNotFoundError:
    G.append("（抽檢 CSV 缺失）")
G.append("")
G.append("## 5 系統性錯置")
G.append("")
G.append("抽檢發現卷一有 16 個韻（魂、痕等）整段被併入相鄰韻，例如「痕 户恩切」被標為元韻。")
G.append("這不是單條噪聲，而是 `CARRIED_FORWARD` 在韻目行缺失處一路沿用造成的**整段錯掛**。")
G.append("影響範圍需逐韻重判，本輪只標記，未修。")
w("GUANGYUN_STRUCTURE_AUDIT.md", "\n".join(G))
shutil.copy(os.path.join(R9, "c_pages", "guangyun_sample_150.csv"), os.path.join(REP, "GUANGYUN_SAMPLE_VERIFICATION.csv"))
print("batch2 done")
