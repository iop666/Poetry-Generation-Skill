#!/usr/bin/env python3
"""把《陶淵明集》底本自带的 {{另|A|B}} 异文标记写入 variant_candidates。

与另一类异文候选的区别：
    「同作者同题、文本不同」是**程序推测**的候选（可能只是同题异篇）；
    这里的是**底本校记**，即整理者已明确指出「A，一作 B」，属直接证据。
    故单列 category=SOURCE_MARKED_VARIANT，不与其他候选混同。
"""
import glob, json, os, sqlite3, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "database", "poetry.db")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
conn.execute("DELETE FROM variant_candidates WHERE category='SOURCE_MARKED_VARIANT'")

n, miss, groups = 0, 0, []
for path in sorted(glob.glob(os.path.join(BASE, "raw", "poetry", "tao", "*.json"))):
    vol = os.path.basename(path).replace(".json", "")
    for item in json.load(open(path, encoding="utf-8")):
        if not item.get("variants"):
            continue
        row = conn.execute(
            "SELECT work_id, title_norm FROM works WHERE collection='tao' AND title_norm=? LIMIT 1",
            (item["title"],)).fetchone()
        if not row:
            miss += 1
            continue
        detail = "；".join("%s（一作%s）" % (a, b) for a, b in item["variants"])
        gid = "T:" + row["work_id"][:24]
        conn.execute("INSERT INTO variant_candidates VALUES (?,?,?,?,?,?,?,?)",
                     (gid, "SOURCE_MARKED_VARIANT", "陶潜", item["title"], row["work_id"],
                      len(item["variants"]), "底本 {{另|A|B}} 校记：" + detail, "SOURCE_MARKED"))
        n += len(item["variants"])
        groups.append({"卷": vol, "题": item["title"], "异文": len(item["variants"]), "明细": detail})

conn.commit()
print(f"写入 {len(groups)} 篇 / {n} 处异文；未匹配 {miss}")
json.dump(groups, open(os.path.join(BASE, "audit", "tao_variants.json"), "w",
                       encoding="utf-8"), ensure_ascii=False, indent=1)
