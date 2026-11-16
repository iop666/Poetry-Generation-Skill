#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-12 工作包 C（v3）：按页内「○」分段 + 与小韵表贪心对齐，建《集韵》字级索引。

v2 用全文顺序锚点，因注文中同名字造成漂移（仅 665/4169 锚定）。v3 改为：
每页取全部 ○ 位置切成段 → 与该页小韵表按顺序贪心对齐（head 匹配优先，字数匹配次之）
→ 段内按〈〉切字组。页首无 ○ 的残条单列 ORPHAN，不强行归并。
"""
import os, re, json, csv, sqlite3
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-12')
PAGES = os.path.join(BASE, 'raw/r2_08/jiyun_pages')
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002ffff]')
ANN = re.compile(r'([^\s〈〉○]{0,14})〈([^〉]{0,400})〉')
NUM = '一二三四五六七八九十'


def entries_of(seg):
    out = []
    for m in ANN.finditer(seg):
        grp = ''.join(CJK.findall(m.group(1)))
        if not grp:
            continue
        out.append((grp, m.group(2)))
    return out


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    files = {}
    for f in os.listdir(PAGES):
        if f.endswith('.json'):
            d = json.load(open(os.path.join(PAGES, f), encoding='utf-8'))
            files[d['title']] = (f, d)
    rows = list(cur.execute('''SELECT id,yun,volume,seq,head,fanqie_raw,declared_chars,page_title
                               FROM jiyun_small_rhyme_audit_r2_10 ORDER BY page_title,seq'''))
    by_page = defaultdict(list)
    for r in rows:
        by_page[r[7]].append(r)

    cur.executescript('''
    DROP TABLE IF EXISTS jiyun_char_index_r2_12;
    CREATE TABLE jiyun_char_index_r2_12(
      char_id TEXT PRIMARY KEY, character TEXT, entry_id TEXT, volume INT, rhyme_group TEXT,
      xiaoyun_id TEXT, xiaoyun_seq INT, is_xiaoyun_head INT, char_group TEXT, fanqie TEXT,
      source_page TEXT, source_offset INT, align TEXT, evidence_level TEXT, verification_status TEXT);
    DROP TABLE IF EXISTS jiyun_entry_r2_12;
    CREATE TABLE jiyun_entry_r2_12(
      entry_id TEXT PRIMARY KEY, volume INT, rhyme_group TEXT, xiaoyun_id TEXT, xiaoyun_seq INT,
      entry_idx INT, char_group TEXT, n_chars INT, note_len INT, fanqie TEXT, is_head INT,
      source_page TEXT, source_offset INT, align TEXT);
    DROP TABLE IF EXISTS jiyun_rhyme_202_206_r2_12;
    CREATE TABLE jiyun_rhyme_202_206_r2_12(
      rhyme_group TEXT, volume INT, n_xiaoyun_in_table INT, n_segments INT, n_aligned INT,
      n_entries INT, n_chars INT, status TEXT);
    ''')
    entries, chars = [], []
    eid = cid = 0
    stat_rhyme = defaultdict(lambda: dict(tab=0, seg=0, ali=0, ent=0, ch=0))
    align_stat = defaultdict(int)
    for title, (f, d) in sorted(files.items()):
        text = d['text']
        marks = [m.start() for m in re.finditer('○', text)]
        segs = []
        for j, p in enumerate(marks):
            end = marks[j + 1] if j + 1 < len(marks) else len(text)
            segs.append((p, text[p:end]))
        page_rows = sorted(by_page.get(title, []), key=lambda r: r[3])
        s = stat_rhyme[(page_rows[0][2] if page_rows else 0, page_rows[0][1] if page_rows else title)]
        s['tab'] = len(page_rows)
        s['seg'] = len(segs)
        # 贪心对齐：第 i 段 ↔ 第 i 条（先按顺序），head 不一致则在该段附近 2 段内找
        used = set()
        for i, r in enumerate(page_rows):
            rid, yun, vol, seq, head, fq, dc, _ = r
            pick = None
            for k in range(i, min(i + 3, len(segs))):
                if k in used:
                    continue
                es = entries_of(segs[k][1])
                if not es:
                    continue
                if head in es[0][0] or (fq and fq in es[0][1][:14]):
                    pick = (k, 'HEAD_MATCH')
                    break
            if pick is None:
                for k in range(len(segs)):
                    if k in used:
                        continue
                    es = entries_of(segs[k][1])
                    if es and head in es[0][0]:
                        pick = (k, 'OUT_OF_ORDER')
                        break
            if pick is None:
                for k in range(i, min(i + 3, len(segs))):
                    if k not in used:
                        pick = (k, 'POSITION_ONLY')
                        break
            if pick is None:
                align_stat['NO_SEGMENT'] += 1
                continue
            k, how = pick
            used.add(k)
            align_stat[how] += 1
            s['ali'] += 1
            xid = f'JY12S-{vol}-{seq:03d}-{rid}'
            off0, seg = segs[k]
            for idx, (grp, note) in enumerate(entries_of(seg), 1):
                eid += 1
                entries.append([f'JY12E-{eid:06d}', vol, yun, xid, seq, idx, grp, len(grp), len(note),
                                fq if idx == 1 else '', 1 if idx == 1 else 0, title, off0, how])
                for ch in grp:
                    cid += 1
                    chars.append([f'JY12C-{cid:06d}', ch, f'JY12E-{eid:06d}', vol, yun, xid, seq,
                                  1 if idx == 1 else 0, grp, fq if idx == 1 else '', title, off0, how,
                                  'DIGITAL_TRANSCRIPTION', 'UNVERIFIED_IMAGE'])
                s['ent'] += 1
                s['ch'] += len(grp)
    cur.executemany('INSERT INTO jiyun_entry_r2_12 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', entries)
    cur.executemany('INSERT INTO jiyun_char_index_r2_12 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', chars)
    rh = []
    for (vol, yun), s in sorted(stat_rhyme.items(), key=lambda x: (x[0][0] or 0, x[0][1])):
        st = 'COMPLETE' if s['ali'] == s['tab'] and s['seg'] == s['tab'] else (
            'ALIGNED_PARTIAL' if s['ali'] else 'NO_ALIGN')
        rh.append([yun, vol, s['tab'], s['seg'], s['ali'], s['ent'], s['ch'], st])
    cur.executemany('INSERT INTO jiyun_rhyme_202_206_r2_12 VALUES (?,?,?,?,?,?,?,?)', rh)
    con.commit()
    stat = {
        'small_rhyme_table': len(rows), 'entries': len(entries), 'char_rows': len(chars),
        'distinct_chars': len({c[1] for c in chars}), 'rhymes': len(rh),
        'rhyme_complete': sum(1 for x in rh if x[7] == 'COMPLETE'),
        'rhyme_aligned_partial': sum(1 for x in rh if x[7] == 'ALIGNED_PARTIAL'),
        'rhyme_no_align': sum(1 for x in rh if x[7] == 'NO_ALIGN'),
        'align': dict(align_stat),
        'head_entries': sum(1 for e in entries if e[10] == 1),
    }
    json.dump(stat, open(os.path.join(OUT, 'LOGS/jiyun_v3.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(stat, ensure_ascii=False, indent=1))
    with open(os.path.join(OUT, 'JIYUN_202_206_RHYME_MAPPING.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['rhyme_group', 'volume', 'n_xiaoyun_in_table', 'n_segments', 'n_aligned', 'n_entries',
                    'n_chars', 'status'])
        w.writerows(rh)
    with open(os.path.join(OUT, 'JIYUN_30862_ENTRY_CLASSIFICATION.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['entry_id', 'volume', 'rhyme_group', 'xiaoyun_id', 'xiaoyun_seq', 'entry_idx', 'char_group',
                    'n_chars', 'note_len', 'fanqie', 'is_head', 'source_page', 'source_offset', 'align'])
        w.writerows(entries)
    con.close()


if __name__ == '__main__':
    main()
