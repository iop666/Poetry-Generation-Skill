#!/usr/bin/env python3
"""relabel_audit.py —— 按 R2-02 审核意见修正两处口径

审核意见 A：辽、金必须分开统计，不能用「辽金」合并掩盖辽代为零。
审核意见 B：286 条不能统称「已核对一致」，须分为
    CROSS_SOURCE_COMPARED（完成比对）/ TEXT_MATCHED（一致）/
    ORTHOGRAPHIC_VARIANT（仅异体写法）/ TEXT_CONFLICT（实质差异）/ NOT_FOUND。
"""
import sqlite3

DB = "database/poetry.db"
c = sqlite3.connect(DB)

# --- B：跨源核对状态细分 ---
cols = [r[1] for r in c.execute("PRAGMA table_info(text_crosscheck)")]
if "status" not in cols:
    c.execute("ALTER TABLE text_crosscheck ADD COLUMN status TEXT")
MAP = {"MATCH": "TEXT_MATCHED", "MATCH_VARIANT": "ORTHOGRAPHIC_VARIANT",
       "DIFF": "TEXT_CONFLICT"}
for k, v in MAP.items():
    c.execute("UPDATE text_crosscheck SET status=? WHERE result=? AND (status IS NULL OR status<>?)", (v, k, v))
c.execute("UPDATE text_crosscheck SET status='NOT_FOUND' WHERE status IS NULL")

cols = [r[1] for r in c.execute("PRAGMA table_info(works)")]
if "crosscheck_status" not in cols:
    c.execute("ALTER TABLE works ADD COLUMN crosscheck_status TEXT")
c.execute("""UPDATE works SET crosscheck_status=(
                SELECT t.status FROM text_crosscheck t WHERE t.work_id=works.work_id)
             WHERE work_id IN (SELECT work_id FROM text_crosscheck)""")
# 「已完成比对」是另一维：不是文本一致，而是"做过比对"
c.execute("UPDATE works SET crosscheck_status='CROSS_SOURCE_COMPARED:'||crosscheck_status "
          "WHERE crosscheck_status IS NOT NULL")
c.commit()

print("text_crosscheck.status:", dict(c.execute(
    "SELECT status, COUNT(*) FROM text_crosscheck GROUP BY 1").fetchall()))
print("works.crosscheck_status:", dict(c.execute(
    "SELECT crosscheck_status, COUNT(*) FROM works WHERE crosscheck_status IS NOT NULL GROUP BY 1").fetchall()))
c.close()
