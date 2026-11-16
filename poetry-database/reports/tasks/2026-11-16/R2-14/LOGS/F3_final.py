#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F3：30 首终审表（不强制 CLEAN；朝代冲突记 CONFLICT_DB_INFERRED）"""
import csv, re, sqlite3, collections, difflib

D = 'reports/tasks/2026-11-16/R2-14'
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
cj = lambda s: ''.join(CJK.findall(s or ''))
con = sqlite3.connect('file:database/poetry.db?mode=ro', uri=True)

cards = {r['card_id']: r for r in csv.DictReader(
    open('reports/tasks/2026-11-15/R2-10/THIRTY_CLOSE_READINGS.csv', encoding='utf-8-sig'))}
clo = list(csv.DictReader(open(f'{D}/CLOSE_READINGS_30_ISSUE_CLOSURE.csv', encoding='utf-8-sig')))
by = collections.defaultdict(list)
for r in clo:
    by[r['card_id']].append(r)

MAJOR_CARDS = {'C28'}
NOTREV = {'C01', 'C07', 'C12', 'C16', 'C23'}

NOTE = {
 'C01': 'R2-13 已落定 work_id=tang300:c63fe4716683；2 项均为「词已出场／景未出场」与「字位指认」的可证伪错误，卡片未改，故 NOT_REVISED。',
 'C07': 'work_id=songshi:afc90d0ab2ec；库文作「遠近高低總不同」，对勘表 no.6 录四库本「逺近髙低無一同」（異文 2 字），卡片 note 未记；另元丰七年系年与外证皆无院内书可核。',
 'C12': 'work_id=tang300:bc187a889708；对勘表 no.4 三处異文（曲徑/竹逕、俱/都、唯聞/但餘，4 字）卡片一字未记；同源复本 tang:8cceeac1c254 与源2 合，可作旁证。',
 'C16': 'work_id=tang300:b06307c0c39a；注意：库 verify_status=VARIANT_PENDING，TEXT_CONFLICT 在 crosscheck_status 列（值 CROSS_SOURCE_COMPARED:TEXT_CONFLICT）。R2-13 终审表把该值写成 verify_status，属证据字段指认错误，结论不受影响。',
 'C23': 'work_id=songci:76d37f87f2f4；5 项中「晚／曉」为 SIGNIFICANT（改全词时间设定）、「忺／堪」为孤读，另 3 项为意象／韵部／艺术特点的可证伪错误。',
 'C21': '朝代：卡片「唐」 vs 库「五代」——CONFLICT_DB_INFERRED。硬证据：①authors 表 20,809 行 note 完全相同「作者朝代由所属集合先验推导，未与史传核对」（COUNT(*)=20809，COUNT(DISTINCT note)=1）；②authors.dynasty 连多数票都不是——王珪 authors.dynasty=唐而 works 中宋 430／唐 2，王融=唐而魏晋南北朝 62／唐 1；③works.dynasty 同 author_id 跨朝代的 353 个。故库值既非史传亦非多数，不得反推作者断代；温庭筠卒年早于五代。',
 'C29': '朝代：卡片「五代」 vs 库「唐」——CONFLICT_DB_INFERRED（理由同 C21：authors.dynasty 取自集合先验，实例王珪 430 宋诗标唐；works 的 tang 集合归并，欧阳炯仕后蜀入宋，卡片为是）。',
 'C14': '字数三口径互不合（text_raw 62／正文 56／char_count 58），属库字段缺陷而非卡片笔误；校记嵌在颈联与尾联之间。',
 'C20': '字数三口径互不合（294／285／290），校记 9 字嵌在句中；韵表「越／月」误标「屑」并漏一整韵段。',
 'C28': 'MAJOR：title_notes 遗留未定稿的半角「?」与自问自答，且把无名氏《撷芳词》句「可怜孤似钗头凤」当作本词首句（本词首句「红酥手」），属张冠李戴；同卡意象（红跨昔今）、用典（皆语典与苏蕙事典自相抵牾）、句式（三字句实为三、三、七）亦有硬错。',
 'C11': '首句「青山橫北郭」以入声「郭」收，卡片 rhyme 栏「首句入韵（城）」与其 prosody 栏自标平仄自相抵牾。',
 'C13': '「千」「三」字频为 0，属误举；「万」「百」各 1。',
 'C25': '上片起二句「我欲乘风归去／又恐琼楼玉宇」各 6 字，卡片作「两个五字句」。',
 'C26': '韵脚漏「户」「絮」，库谱 10 韵，卡片 8 韵。',
 'C29_r': '',
}

rows = []
for cid in [f'C{i:02d}' for i in range(1, 31)]:
    c = cards[cid]
    wid = c['work_id']
    db = con.execute("SELECT dynasty,collection,char_count FROM works WHERE work_id=?", (wid,)).fetchone()
    tr = con.execute("SELECT text_raw FROM works WHERE work_id=?", (wid,)).fetchone()[0]
    a, b = cj(c['text_full']), cj(tr)
    same = 'MATCH(0字異)' if a == b else f'DIFF({sum(1 for x,y in zip(a,b) if x!=y)}字)'
    items = by[cid]
    n_open = len(items)
    n_unv = sum(1 for x in items if x['final_status'] == 'UNVERIFIABLE_NO_SOURCE')
    if cid in MAJOR_CARDS:
        overall = 'MAJOR_ISSUE'
    elif cid in NOTREV:
        overall = 'NOT_REVISED'
    elif n_open == 0:
        overall = 'CLEAN'
    elif n_unv == n_open:
        overall = 'UNVERIFIABLE'
    else:
        overall = 'MINOR_ISSUE'
    top = items[0]['issue_desc']
    top = top if len(top) <= 90 else top[:88] + '…'
    if n_open > 1:
        top += f'（另有 {n_open - 1} 项）'
    note = NOTE.get(cid, '')
    if overall == 'UNVERIFIABLE':
        note = (note + '；' if note else '') + '仅存库外不可核项（本书无集部／史部／年谱），无文本或论断硬错；按「不可核」记，不并入 CLEAN。'
    if same != 'MATCH(0字異)':
        note = (note + '；' if note else '') + f'正文比对 {same}'
    rows.append(dict(card_id=cid, work_id=wid, title=c['title'], author=c['author'],
                     dynasty_db=db[0], dynasty_card=c['dynasty'], text_matches_raw=same,
                     n_open_issue=n_open, n_fixed=0, top_issue=top,
                     overall_status=overall, note=note))

with open(f'{D}/CLOSE_READINGS_30_FINAL_AUDIT.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['card_id', 'work_id', 'title', 'author', 'dynasty_db',
                                      'dynasty_card', 'text_matches_raw', 'n_open_issue', 'n_fixed',
                                      'top_issue', 'overall_status', 'note'])
    w.writeheader()
    w.writerows(rows)
print(len(rows), collections.Counter(r['overall_status'] for r in rows))
print('open issues', sum(int(r['n_open_issue']) for r in rows))
print('dynasty conflicts', [(r['card_id'], r['dynasty_db'], r['dynasty_card']) for r in rows if r['dynasty_db'] != r['dynasty_card']])
