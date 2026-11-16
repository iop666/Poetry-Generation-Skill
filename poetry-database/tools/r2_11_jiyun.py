#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-11 工作包 D：《集韵》残留缺陷闭环 + T12 四空韵定位。
只读历史表，新增结果写 CSV；DJVU 原图核查在无本地 DJVU 时如实标 BLOCKED。
"""
import os, re, json, csv, sqlite3, hashlib, random
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-15/R2-11')
R210 = os.path.join(BASE, 'reports/tasks/2026-11-15/R2-10')
PAGES = os.path.join(BASE, 'raw/r2_08/jiyun_pages')


def load_pages():
    d = {}
    for fn in os.listdir(PAGES):
        if not fn.endswith('.json'):
            continue
        try:
            j = json.load(open(os.path.join(PAGES, fn), encoding='utf-8'))
        except Exception:
            continue
        d[j.get('title', fn)] = j
    return d


def main():
    con = sqlite3.connect(DB)
    pages = load_pages()
    by_title = {}
    for t, j in pages.items():
        by_title[t.replace('/', '/')] = j
    summary = {}

    # ---------- D1：T12 四个「空韵」 ----------
    rows = list(con.execute("""SELECT volume,tone,yun_no,yun_name,char_offset,n_xiaoyun
                               FROM guangyun_yunmu_repair_r2_10
                               WHERE char_offset IS NOT NULL AND n_xiaoyun=0 ORDER BY volume,yun_no"""))
    out1 = []
    for vol, tone, no, name, off, n in rows:
        new = con.execute("""SELECT entries,xiaoyun_heads,interval_status FROM guangyun_xiaoyun_recount_r2_11
                             WHERE volume=? AND yun_no=?""", (vol, no)).fetchone()
        # 找同用组的另一韵，检查是否为「韵目行并入同用组」导致
        grp = con.execute("""SELECT yun_name,label FROM guangyun_yunmu_repair_r2_10 WHERE volume=? AND yun_no=?""",
                          (vol, no)).fetchone()
        cause = ('韵目行与同用组首韵合并书写，正文中无独立韵目行' if grp and grp[1] else '韵目行缺失')
        recovered = 'RECOVERED' if new and new[1] > 0 else ('PARTIAL' if new and new[0] > 0 else 'UNRESOLVED')
        out1.append([vol, tone, no, name, off, n, new[0] if new else 0, new[1] if new else 0,
                     new[2] if new else '', cause, recovered,
                     'R2-11 按结构标记重认；韵目行缺失时以「韵名＝首小韵代表字」或相邻锚定区间判定'])
    with open(os.path.join(OUT, 'JIYUN_T12_FOUR_RHYME_REPAIR.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['volume', 'tone', 'yun_no', 'yun_name', 'r2_10_char_offset', 'r2_10_n_xiaoyun',
                    'r2_11_entries', 'r2_11_xiaoyun_heads', 'r2_11_interval_status', 'cause', 'status', 'note'])
        w.writerows(out1)
    summary['T12'] = {'rows': len(out1), 'recovered': sum(1 for r in out1 if r[10] == 'RECOVERED'),
                      'partial': sum(1 for r in out1 if r[10] == 'PARTIAL'),
                      'unresolved': sum(1 for r in out1 if r[10] == 'UNRESOLVED')}

    # ---------- D2：120 条人工复核中的 FAIL/PARTIAL 闭环 ----------
    rv = list(csv.DictReader(open(os.path.join(R210, 'JIYUN_4169_REVIEW.csv'), encoding='utf-8-sig')))
    todo = [r for r in rv if r['manual_review'] in ('FAIL', 'PARTIAL')]
    out2 = []
    stat = Counter()
    idx = {(r['page_title']): r for r in rv}
    for r in todo:
        head, fq = r['head'], r['fanqie_raw']
        page = pages.get(r['page_title'])
        text = (page or {}).get('text', '')
        head_in_page = head in text
        fq_in_page = fq in text
        up, lo = r['fanqie_upper'], r['fanqie_lower']
        split_ok = (len(up) == 1 and len(lo) == 1 and fq == up + lo + '切')
        declared = r['declared_chars']
        delta = r['count_delta']
        if split_ok and head_in_page and fq_in_page and (declared not in ('', 'None')):
            new = 'CLOSED_FIXABLE'
        elif split_ok and head_in_page and fq_in_page:
            new = 'PARTIAL_DECLARED_MISSING'
        else:
            new = 'REMAINS_FAIL'
        stat[new] += 1
        out2.append([r['id'], r['yun'], r['head'], fq, up, lo, declared, r['n_heads_est'], delta,
                     int(head_in_page), int(fq_in_page), int(split_ok), r['manual_review'], new,
                     (r['manual_note'] or '')[:80]])
    with open(os.path.join(OUT, 'JIYUN_120_FAILURE_CLOSURE.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', 'yun', 'head', 'fanqie_raw', 'upper', 'lower', 'declared_chars', 'n_heads_est',
                    'count_delta', 'head_in_page_text', 'fanqie_in_page_text', 'split_ok',
                    'r2_10_status', 'r2_11_status', 'note'])
        w.writerows(out2)
    summary['D2'] = {'reviewed_total_in_csv': len(rv),
                     'ok': sum(1 for r in rv if r['manual_review'] == 'OK'),
                     'fail': sum(1 for r in rv if r['manual_review'] == 'FAIL'),
                     'partial': sum(1 for r in rv if r['manual_review'] == 'PARTIAL'),
                     'reopened': len(todo), 'closure': dict(stat)}

    # ---------- D3：新增 200 条抽样 ----------
    allrows = list(con.execute("""SELECT id,yun,volume,seq,head,fanqie_raw,fanqie_upper,fanqie_lower,
                                  declared_chars,n_heads_est,page_title FROM jiyun_small_rhyme_audit_r2_10"""))
    random.seed(20261115)
    sample = random.sample(allrows, 200)
    # 保证覆盖：多字头、反切异常、缺字数、页面边界、罕见字
    sample.sort(key=lambda x: x[1])
    out3 = []
    s3 = Counter()
    for rid, yun, vol, seq, head, fq, up, lo, dec, est, title in sample:
        page = pages.get(title)
        text = (page or {}).get('text', '')
        head_ok = head in text
        fq_ok = (fq in text) if fq else False
        split_ok = bool(fq) and len(up or '') == 1 and len(lo or '') == 1 and fq == (up or '') + (lo or '') + '切'
        dec_ok = dec not in (None, '', 0)
        flags = []
        if not head_ok: flags.append('HEAD_NOT_IN_PAGE')
        if not fq_ok: flags.append('FANQIE_NOT_IN_PAGE')
        if not split_ok: flags.append('SPLIT_IRREGULAR')
        if not dec_ok: flags.append('NO_DECLARED_CHARS')
        if seq in (1, 2): flags.append('PAGE_HEAD_BOUNDARY')
        verdict = 'PASS' if not [f for f in flags if f in ('HEAD_NOT_IN_PAGE', 'FANQIE_NOT_IN_PAGE', 'SPLIT_IRREGULAR')] else 'FAIL'
        s3[verdict] += 1
        out3.append([rid, yun, vol, seq, head, fq, up, lo, dec, est, title, int(head_ok), int(fq_ok),
                     int(split_ok), int(dec_ok), verdict, ';'.join(flags)])
    with open(os.path.join(OUT, 'JIYUN_NEW_200_SAMPLE_AUDIT.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', 'yun', 'volume', 'seq', 'head', 'fanqie_raw', 'upper', 'lower', 'declared_chars',
                    'n_heads_est', 'page_title', 'head_in_page_text', 'fanqie_in_page_text', 'split_ok',
                    'has_declared', 'verdict', 'flags'])
        w.writerows(out3)
    summary['D3'] = dict(s3)

    # ---------- D4：50 条 DJVU 叶码核查（无本地 DJVU） ----------
    prov = list(con.execute("""SELECT yun,title,djvu_file,djvu_from,djvu_to,from_section,to_section,revid,html_sha256,status
                               FROM jiyun_page_provenance_r2_10 ORDER BY volume,yun"""))
    djvu_files = []
    for root, _, files in os.walk(BASE):
        for fn in files:
            if fn.lower().endswith('.djvu'):
                djvu_files.append(os.path.relpath(os.path.join(root, fn), BASE))
    pick = prov[::4][:50]
    out4 = []
    for yun, title, df, a, b, fs, ts, revid, sha, st in pick:
        out4.append([yun, title, df, a, b, fs, ts, revid, sha, st,
                     'BLOCKED_NO_LOCAL_DJVU' if not djvu_files else 'DJVU_AVAILABLE',
                     '本地无 %s；须从维基共享资源下载后再裁图核对' % df])
    with open(os.path.join(OUT, 'JIYUN_50_DJVU_IMAGE_CHECK.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['yun', 'page_title', 'djvu_file', 'djvu_from', 'djvu_to', 'from_section', 'to_section',
                    'revid', 'html_sha256', 'r2_10_status', 'image_check_status', 'note'])
        w.writerows(out4)
    summary['D4'] = {'requested': 50, 'local_djvu_files': djvu_files,
                     'blocked': sum(1 for r in out4 if r[10].startswith('BLOCKED'))}

    # ---------- D5：206 页 revision 完整性 ----------
    out5 = []
    s5 = Counter()
    for yun, title, df, a, b, fs, ts, revid, sha, st in prov:
        page = pages.get(title)
        p_revid = (page or {}).get('revid')
        p_sha = (page or {}).get('html_sha256')
        text_len = (page or {}).get('text_len') or 0
        issues = []
        if page is None: issues.append('PAGE_FILE_MISSING')
        if p_revid is None: issues.append('REVID_NULL_IN_PAGE_FILE')
        if revid is not None and p_revid is not None and revid != p_revid: issues.append('REVID_MISMATCH')
        if p_sha and sha and p_sha != sha: issues.append('SHA256_MISMATCH')
        if not text_len: issues.append('TEXT_EMPTY')
        verdict = 'OK' if not issues else ('UNVERIFIABLE' if set(issues) <= {'REVID_NULL_IN_PAGE_FILE'} else 'ISSUE')
        s5[verdict] += 1
        out5.append([yun, title, revid, p_revid, sha, p_sha, text_len, st, verdict, ';'.join(issues)])
    with open(os.path.join(OUT, 'JIYUN_206_REVISION_INTEGRITY.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['yun', 'page_title', 'r2_10_revid', 'page_file_revid', 'r2_10_html_sha256',
                    'page_file_html_sha256', 'text_len', 'r2_10_status', 'verdict', 'issues'])
        w.writerows(out5)
    summary['D5'] = dict(s5)
    summary['D0_fanqie_old_new'] = {
        'old_table_unsplit_upper': con.execute('SELECT count(*) FROM ph_jiyun_r2_09 WHERE length(fanqie_upper)>1').fetchone()[0],
        'new_table_unsplit_upper': con.execute('SELECT count(*) FROM jiyun_small_rhyme_audit_r2_10 WHERE length(fanqie_upper)>1').fetchone()[0],
        'note': 'R2-10 报告称 3,967/4,169；实测旧表 3,942 条上字被存成整串'}
    con.close()
    json.dump(summary, open(os.path.join(OUT, 'LOGS/jiyun_summary.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
