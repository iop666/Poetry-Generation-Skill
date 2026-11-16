#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-12 工作包 C（v2）：以 4,169 小韵表为锚，重建《集韵》字级索引。

v1 用「○」直接切分得 4,327 段、34,779 个「字组」，与 R2-11 的 4,169/30,862 不符。
v2 改为「锚点定位」：按卷次与韵序拼接 206 页文本，再按小韵表的 (head, fanqie) 顺序锚定，
把脉文本切成「小韵区间」，区间内按〈〉切字组。定位失败的如实标 LOCATOR_FAILED，不猜。
"""
import os, re, json, csv, sqlite3, hashlib

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-12')
PAGES = os.path.join(BASE, 'raw/r2_08/jiyun_pages')
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002ffff]')
ANN = re.compile(r'([^\s〈〉○]{0,14})〈([^〉]{0,400})〉')
CN = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}


def cn2int(s):
    if not s:
        return 0
    if '十' in s:
        a, b = s.split('十', 1)
        return (CN.get(a, 1) if a else 1) * 10 + (CN.get(b, 0) if b else 0)
    return CN.get(s, 0)


def yun_order(yun):
    m = re.search(r'第([一二三四五六七八九十]+)$', yun)
    return cn2int(m.group(1)) if m else 0


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    files = {}
    for f in os.listdir(PAGES):
        if f.endswith('.json'):
            d = json.load(open(os.path.join(PAGES, f), encoding='utf-8'))
            files[d['title']] = (f, d)
    # 页面按 volume + 韵序排序，拼接为一条文本，页间记录偏移
    order = sorted(files.items(), key=lambda kv: (files[kv[0]][1].get('volume') or 0, yun_order(files[kv[0]][1]['title'].split('/')[-1])))
    prov = {r[0]: r for r in cur.execute('SELECT title,volume,yun,revid FROM jiyun_page_provenance_r2_10')}
    buf, page_spans = [], []
    pos = 0
    for title, (f, d) in order:
        t = d['text']
        page_spans.append((title, f, pos, pos + len(t)))
        buf.append(t)
        pos += len(t) + 1
    full = '\n'.join(buf)

    def page_of(off):
        for title, f, a, b in page_spans:
            if a <= off < b:
                return title
        return page_spans[-1][0]

    # 小韵锚点
    rows = list(cur.execute('''SELECT id,yun,volume,seq,head,fanqie_raw FROM jiyun_small_rhyme_audit_r2_10
                               ORDER BY volume, yun, seq'''))
    rows.sort(key=lambda r: (r[2] or 0, yun_order(r[1]), r[3]))
    anchors = []
    cursor = 0

    def find_head(head, fq, start):
        """小韵首常为异体组（head 后还有 0-6 字才到〈），故不能要求 head 紧跟〈。"""
        i = full.find(head, start)
        while i >= 0:
            tail = full[i + len(head):i + len(head) + 14]
            if '〈' in tail:
                if fq and fq in tail[:len(fq) + 8]:
                    return i, 'HEAD_FANQIE'
                return i, 'HEAD_ONLY'
            i = full.find(head, i + 1)
        return -1, 'NOT_FOUND'

    for rid, yun, vol, seq, head, fq in rows:
        i, how = find_head(head, fq, cursor)
        if i < 0:
            anchors.append(dict(id=rid, yun=yun, volume=vol, seq=seq, head=head, fanqie=fq,
                                start=None, status='LOCATOR_FAILED'))
            continue
        anchors.append(dict(id=rid, yun=yun, volume=vol, seq=seq, head=head, fanqie=fq,
                            start=i, status='ANCHORED', how=how))
        cursor = i + 1

    # 区间切分
    cur.executescript('''
    DROP TABLE IF EXISTS jiyun_char_index_v2_r2_12;
    CREATE TABLE jiyun_char_index_v2_r2_12(
      char_id TEXT PRIMARY KEY, character TEXT, entry_id TEXT, volume INT, rhyme_group TEXT,
      xiaoyun_id TEXT, xiaoyun_seq INT, is_xiaoyun_head INT, char_group TEXT, fanqie TEXT,
      source_page TEXT, source_offset INT, evidence_level TEXT, verification_status TEXT);
    DROP TABLE IF EXISTS jiyun_entry_v2_r2_12;
    CREATE TABLE jiyun_entry_v2_r2_12(
      entry_id TEXT PRIMARY KEY, volume INT, rhyme_group TEXT, xiaoyun_id TEXT, xiaoyun_seq INT,
      entry_idx INT, char_group TEXT, n_chars INT, note_len INT, fanqie TEXT, is_head INT,
      source_page TEXT, source_offset INT);
    DROP TABLE IF EXISTS jiyun_rhyme_202_206_r2_12;
    CREATE TABLE jiyun_rhyme_202_206_r2_12(
      rhyme_group TEXT PRIMARY KEY, volume INT, n_xiaoyun_in_table INT, n_xiaoyun_anchored INT,
      n_entries INT, n_chars INT, n_pages INT, status TEXT);
    ''')
    entries, chars = [], []
    eid = cid = 0
    from collections import Counter, defaultdict
    stat_rhyme = defaultdict(lambda: dict(tab=0, anc=0, ent=0, ch=0, pg=set()))
    anchored = [a for a in anchors if a['start'] is not None]
    for i, a in enumerate(anchored):
        end = anchored[i + 1]['start'] if i + 1 < len(anchored) else len(full)
        seg = full[a['start']:end]
        xid = f"JY12S-{a['volume']}-{a['yun']}-{a['seq']:03d}"
        k = 0
        for m in ANN.finditer(seg):
            grp = ''.join(CJK.findall(m.group(1)))
            note = m.group(2)
            if not grp:
                continue
            k += 1
            eid += 1
            pg = page_of(a['start'] + m.start())
            entries.append([f'JY12E-{eid:06d}', a['volume'], a['yun'], xid, a['seq'], k, grp,
                            len(grp), len(note), a['fanqie'] if k == 1 else '', 1 if k == 1 else 0,
                            pg, a['start'] + m.start()])
            for ch in grp:
                cid += 1
                chars.append([f'JY12C-{cid:06d}', ch, f'JY12E-{eid:06d}', a['volume'], a['yun'], xid, a['seq'],
                              1 if k == 1 else 0, grp, a['fanqie'] if k == 1 else '', pg,
                              a['start'] + m.start(), 'DIGITAL_TRANSCRIPTION', 'UNVERIFIED_IMAGE'])
        s = stat_rhyme[(a['volume'], a['yun'])]
        s['anc'] += 1
        s['ent'] += k
        s['ch'] += sum(len(e[6]) for e in entries[-k:]) if k else 0
        s['pg'].add(page_of(a['start']))
    for rid, yun, vol, seq, head, fq in rows:
        s = stat_rhyme[(vol, yun)]
        s['tab'] += 1
    cur.executemany('INSERT INTO jiyun_entry_v2_r2_12 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', entries)
    cur.executemany('INSERT INTO jiyun_char_index_v2_r2_12 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', chars)
    rh = []
    for (vol, yun), s in sorted(stat_rhyme.items(), key=lambda x: (x[0][0], yun_order(x[0][1]))):
        st = 'COMPLETE' if s['anc'] == s['tab'] else ('PARTIAL' if s['anc'] else 'NO_ANCHOR')
        rh.append([yun, vol, s['tab'], s['anc'], s['ent'], s['ch'], len(s['pg']), st])
    cur.executemany('INSERT INTO jiyun_rhyme_202_206_r2_12 VALUES (?,?,?,?,?,?,?,?)', rh)
    con.commit()
    stat = {
        'small_rhyme_table': len(rows),
        'anchored': len(anchored),
        'locator_failed': len(anchors) - len(anchored),
        'entries': len(entries),
        'char_rows': len(chars),
        'distinct_chars': len({c[1] for c in chars}),
        'rhyme_groups': len(rh),
        'rhyme_complete': sum(1 for r in rh if r[7] == 'COMPLETE'),
        'rhyme_partial': sum(1 for r in rh if r[7] == 'PARTIAL'),
        'rhyme_no_anchor': sum(1 for r in rh if r[7] == 'NO_ANCHOR'),
        'pages_used': len({e[11] for e in entries}),
    }
    json.dump(stat, open(os.path.join(OUT, 'LOGS/jiyun_v2.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(stat, ensure_ascii=False, indent=1))
    with open(os.path.join(OUT, 'JIYUN_CHARACTER_INDEX_AUDIT.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['character', 'n_records', 'n_as_head', 'rhyme_groups', 'sample_head_group', 'sample_fanqie'])
        agg = defaultdict(lambda: [0, 0, set(), '', ''])
        for c in chars:
            a = agg[c[1]]
            a[0] += 1
            a[1] += c[7]
            a[2].add(c[4])
            if c[7] and not a[3]:
                a[3], a[4] = c[8], c[9]
        for ch, a in sorted(agg.items(), key=lambda x: -x[1][0]):
            w.writerow([ch, a[0], a[1], '|'.join(sorted(a[2])), a[3], a[4]])
    with open(os.path.join(OUT, 'JIYUN_202_206_RHYME_MAPPING.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['rhyme_group', 'volume', 'n_xiaoyun_in_table', 'n_xiaoyun_anchored', 'n_entries',
                    'n_chars', 'n_pages', 'status'])
        w.writerows(rh)
    con.close()


if __name__ == '__main__':
    main()
