#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-12 工作包 C：《集韵》206 页版本链修复 + 30,862 条字级索引。

C1：从维基文库 API 取每页当前 revision（revid/timestamp/content-sha1），与本地保存的解析文本对比，
    建立「页面—版本—文件」三重绑定；取不到则记 REVISION_UNAVAILABLE，不填造。
C4：按 ○ 切小韵、按 〈〉 切字组，生成字级索引（小韵首 vs 成员字分别标记）。
"""
import os, re, json, csv, sqlite3, hashlib, urllib.request, urllib.parse, time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-12')
PAGES = os.path.join(BASE, 'raw/r2_08/jiyun_pages')
UA = 'PoetryDatabank/1.0 (academic collation; contact researcher@example.org)'
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002ffff]')
ANN = re.compile(r'([^\s〈〉○]{0,14})〈([^〉]{0,400})〉')
FQ = re.compile(r'([^\s，。]{1,2})([^\s，。]{1,2})切')
NUM = '一二三四五六七八九十'


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def api_revisions(titles, batch=40):
    """批量取当前 revision 元数据。"""
    out = {}
    for i in range(0, len(titles), batch):
        chunk = titles[i:i + batch]
        q = urllib.parse.urlencode({'action': 'query', 'prop': 'revisions', 'titles': '|'.join(chunk),
                                    'rvprop': 'ids|timestamp|sha1|size', 'rvslots': 'main',
                                    'format': 'json', 'formatversion': '2', 'redirects': '1'})
        req = urllib.request.Request('https://zh.wikisource.org/w/api.php?' + q, headers={'User-Agent': UA})
        try:
            d = json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:
            print('API ERR', e)
            continue
        norm = {}
        for n in d.get('query', {}).get('normalized', []):
            norm[n['to']] = n['from']
        for p in d.get('query', {}).get('pages', []):
            title = p.get('title')
            src = norm.get(title, title)
            rev = (p.get('revisions') or [{}])[0]
            out[src] = dict(title=title, revid=rev.get('revid'), timestamp=rev.get('timestamp'),
                            content_sha1=rev.get('sha1'), size=rev.get('size'))
        time.sleep(0.4)
    return out


def parse_page(text):
    """把一页文本切成小韵段，再切成字组条目。"""
    # 去掉首尾导航（← 脂第六 / 微第八 →）
    text = re.sub(r'^←[^\n]*\n', '', text)
    text = re.sub(r'\n[^\n]*→\s*$', '', text)
    parts = text.split('○')
    segs = []
    for p in parts:
        p = p.strip('\n ')
        if not p:
            continue
        entries = []
        pos = 0
        for m in ANN.finditer(p):
            grp = m.group(1)
            note = m.group(2)
            gap = p[pos:m.start()]
            pos = m.end()
            grp = ''.join(CJK.findall(grp))
            if not grp:
                # 无字组：注文续行，并入上一条
                if entries:
                    entries[-1]['note'] += note
                continue
            entries.append(dict(group=grp, note=note, gap=gap))
        if not entries:
            continue
        head = entries[0]
        fqm = FQ.search(head['note'][:16])
        fanqie = (fqm.group(0) if fqm else '')
        segs.append(dict(head_group=head['group'], fanqie=fanqie, entries=entries,
                         raw=p[:60].replace('\n', ' ')))
    return segs


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    prov = list(cur.execute('SELECT title,volume,yun,revid,n_xiaoyun_mark,n_qie,status,text_len FROM jiyun_page_provenance_r2_10'))
    files = {f: json.load(open(os.path.join(PAGES, f), encoding='utf-8')) for f in os.listdir(PAGES) if f.endswith('.json')}
    by_title = {}
    for f, d in files.items():
        by_title[d['title']] = (f, d)
    titles = [p[0] for p in prov]
    revs = api_revisions(titles)
    print('api got', len(revs), 'of', len(titles))

    # ---------- C1 版本绑定 ----------
    cur.executescript('''
    DROP TABLE IF EXISTS jiyun_page_integrity_r2_12;
    CREATE TABLE jiyun_page_integrity_r2_12(
      page_title TEXT PRIMARY KEY, volume INT, yun TEXT, local_file TEXT,
      revid INT, rev_timestamp TEXT, rev_content_sha1 TEXT, rev_size INT,
      local_text_sha256 TEXT, local_json_sha256 TEXT, local_text_len INT,
      n_mark_stored INT, n_mark_actual INT, match_mark INT,
      fetch_status TEXT, verification_status TEXT, note TEXT);
    DROP TABLE IF EXISTS jiyun_character_index_r2_12;
    CREATE TABLE jiyun_character_index_r2_12(
      char_id TEXT PRIMARY KEY, character TEXT, entry_id TEXT, volume INT, rhyme_group TEXT,
      xiaoyun_id TEXT, is_xiaoyun_head INT, head_group TEXT, fanqie TEXT,
      note_head TEXT, source_locator TEXT, evidence_level TEXT, verification_status TEXT);
    DROP TABLE IF EXISTS jiyun_30862_entry_r2_12;
    CREATE TABLE jiyun_30862_entry_r2_12(
      entry_id TEXT PRIMARY KEY, volume INT, rhyme_group TEXT, seg_idx INT, entry_idx INT,
      char_group TEXT, n_chars INT, note_len INT, fanqie TEXT, is_head INT,
      page_title TEXT, raw_segment_head TEXT);
    ''')
    integ = []
    char_rows = []
    entry_rows = []
    cid = 0
    eid = 0
    total_chars = 0
    all_chars = set()
    for title, volume, yun, revid_old, n_mark, n_qie, status, tlen in prov:
        f, d = by_title.get(title, (None, None))
        if not d:
            integ.append([title, volume, yun, '', None, None, None, None, '', '', 0, n_mark, 0, 0,
                          'LOCAL_FILE_MISSING', 'UNVERIFIABLE', '本地无对应页文件'])
            continue
        text = d['text']
        r = revs.get(title, {})
        lsha = sha256_bytes(text.encode('utf-8'))
        jsha = sha256_bytes(open(os.path.join(PAGES, f), 'rb').read())
        segs = parse_page(text)
        n_actual = len(segs)
        ver = 'REVISION_BOUND' if r.get('revid') else 'REVISION_UNAVAILABLE'
        note = ''
        if r.get('revid') and r.get('size'):
            note = f"rev size={r['size']}；本地解析文本 {len(text)} 字符（含格式），非逐字等价，仅作绑定"
        integ.append([title, volume, yun, f, r.get('revid'), r.get('timestamp'), r.get('content_sha1'),
                      r.get('size'), lsha, jsha, len(text), n_mark, n_actual,
                      1 if n_actual == n_mark else 0, 'OK' if f else 'MISSING', ver, note])
        for si, s in enumerate(segs, 1):
            for ei, e in enumerate(s['entries']):
                eid += 1
                entry_rows.append([f'JY12E-{eid:06d}', volume, yun, si, ei + 1, e['group'], len(e['group']),
                                   len(e['note']), s['fanqie'] if ei == 0 else '', 1 if ei == 0 else 0,
                                   title, s['raw']])
                for ch in e['group']:
                    cid += 1
                    char_rows.append([f'JY12C-{cid:06d}', ch, f'JY12E-{eid:06d}', volume, yun,
                                      f'JY12S-{volume}-{yun}-{si:03d}', 1 if ei == 0 else 0,
                                      e['group'], s['fanqie'] if ei == 0 else '', e['note'][:40],
                                      f'{title}#seg{si}.{ei+1}', 'DIGITAL_TRANSCRIPTION', 'UNVERIFIED_IMAGE'])
                    total_chars += len(ch)
                    all_chars.add(ch)
    cur.executemany('INSERT INTO jiyun_page_integrity_r2_12 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', integ)
    cur.executemany('INSERT INTO jiyun_30862_entry_r2_12 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', entry_rows)
    cur.executemany('INSERT INTO jiyun_character_index_r2_12 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', char_rows)
    con.commit()

    stat = {
        'pages': len(integ),
        'pages_revision_bound': sum(1 for x in integ if x[15] == 'REVISION_BOUND'),
        'pages_revision_unavailable': sum(1 for x in integ if x[15] == 'REVISION_UNAVAILABLE'),
        'pages_mark_match': sum(1 for x in integ if x[13] == 1),
        'entries': len(entry_rows),
        'character_rows': len(char_rows),
        'distinct_characters': len(all_chars),
        'head_entries': sum(1 for e in entry_rows if e[9] == 1),
        'entries_with_fanqie': sum(1 for e in entry_rows if e[8]),
    }
    json.dump(stat, open(os.path.join(OUT, 'LOGS/jiyun_r2_12.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(stat, ensure_ascii=False, indent=1))

    # CSV
    with open(os.path.join(OUT, 'JIYUN_REVISION_206_REPAIR.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['page_title', 'volume', 'yun', 'local_file', 'revid', 'rev_timestamp', 'rev_content_sha1',
                    'rev_size', 'local_text_sha256', 'local_json_sha256', 'local_text_len', 'n_mark_stored',
                    'n_mark_actual', 'mark_match', 'fetch_status', 'verification_status', 'note'])
        w.writerows(integ)
    with open(os.path.join(OUT, 'JIYUN_30862_ENTRY_CLASSIFICATION.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['entry_id', 'volume', 'rhyme_group', 'seg_idx', 'entry_idx', 'char_group', 'n_chars',
                    'note_len', 'fanqie', 'is_head', 'page_title', 'raw_segment_head'])
        w.writerows(entry_rows)
    con.close()


if __name__ == '__main__':
    main()
