#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F4 生成：208/310 状态统一表、检索历史、ID join 审计。"""
import csv, json, re, difflib, collections, sqlite3
from opencc import OpenCC

D = 'reports/tasks/2026-11-16/R2-14'
cc = OpenCC('t2s')
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
cjk = lambda s: ''.join(CJK.findall(s or ''))
FOLD = str.maketrans({'沈': '沉', '攲': '欹', '敧': '欹', '裏': '里', '裡': '里', '濛': '蒙',
                      '著': '着', '甯': '宁', '牀': '床', '悽': '凄', '喫': '吃'})
key = lambda s: cc.convert(cjk(s)).translate(FOLD)

# 异体字／通假对（同一字的不同写法，不得判为文本异文）
CV_PAIRS = [
    ('欹', '敧', '攲'), ('里', '裏', '裡'), ('蒙', '濛', '矇'), ('着', '著'),
    ('高', '髙'), ('远', '逺'), ('峰', '峯'), ('看', '㸔'), ('处', '䖏'), ('悦', '恱'),
    ('幡', '旛'), ('颦', '嚬'), ('淡', '澹'), ('早', '蚤'), ('他', '它'), ('粘', '黏'),
    ('拼', '拚'), ('漫', '慢', '谩'), ('消', '销'), ('彩', '采'), ('旁', '傍'), ('沧', '苍'),
    ('楼', '樓'), (' wan', ''),
]
CV = {}
for grp in CV_PAIRS:
    for ch in grp:
        CV[ch] = grp[0]

def nau(s):
    s = re.sub(r'《[^》]*》', '', s or '').replace('所载', '').replace(' ', '').replace('　', '')
    return cc.convert(s)

def cls_diff(t, a, b):
    if t in ('insert', 'delete'):
        if a in ('去声', '读上声', '上声', '平声') or b in ('去声', '读上声', '上声', '平声'):
            return 'EXAMPLE_ANNOTATION'
        return 'TEXTUAL'
    if len(a) == 1 and len(b) == 1 and CV.get(a, a) == CV.get(b, b):
        return 'CHAR_VARIANT'
    return 'TEXTUAL'

# ---------- 载入 ----------
examples = {}
con = sqlite3.connect('file:database/poetry.db?mode=ro', uri=True)
for eid, fid, cp, au, text, n in con.execute(
        "SELECT example_id,form_id,cipai_name,author,text,n_chars FROM cipai_form_examples_r2_08"):
    examples[eid] = dict(form_id=fid, cipai=cp, author=au, text=text or '', n=n)

def first_line(t):
    t = (t or '').strip().replace('\n', '')
    m = re.split(r'[。！？，、；：]', t)
    return (m[0] if m and m[0] else t)[:12]

rows208 = list(csv.DictReader(open('reports/tasks/2026-11-16/R2-13/EXAMPLE_LINK_208_RECONCILIATION.csv', encoding='utf-8-sig')))
res1 = {r['example_id']: r for r in json.load(open(f'{D}/LOGS/f4_search_raw.json'))}
res2 = json.load(open(f'{D}/LOGS/f4_search_retry.json'))
r13 = list(csv.DictReader(open('reports/tasks/2026-11-16/R2-13/EXAMPLE_LINK_UNSEARCHED_100_RESEARCH.csv', encoding='utf-8-sig')))
r12 = list(csv.DictReader(open('reports/tasks/2026-11-16/R2-12/EXAMPLE_LINK_100_INDEPENDENT_VERIFICATION.csv', encoding='utf-8-sig')))
r11 = list(csv.DictReader(open('reports/tasks/2026-11-15/R2-11/EXAMPLE_LINK_100_FINAL_AUDIT.csv', encoding='utf-8-sig')))
r10 = [r for r in csv.DictReader(open('reports/tasks/2026-11-15/R2-10/EXAMPLE_100_INDEPENDENT_REVIEW.csv', encoding='utf-8-sig'))
       if r['review_type'] == 'INDEPENDENT_AGENT']

# ---------- 208 行 ----------
out = []
for r in rows208:
    eid = r['example_id']
    hist = '|'.join(x for x in [f"R2-10:{r['r2_10_status']}" if r['r2_10_status'] else '',
                                f"R2-11:{r['r2_11_status']}" if r['r2_11_status'] else '',
                                f"R2-12:{r['r2_12_status']}" if r['r2_12_status'] else ''] if x)
    hist = (hist + '|' if hist else '') + f"R2-13:{r['final_status']}"
    fs = r['final_status']
    ev = r['basis'] + ('；' + r['note'] if r['note'] else '')
    if eid == 'EX-0012':
        fs = 'VERIFIED_EXACT'
        hist += '|R2-14:VERIFIED_EXACT'
        ev = ('R2-11 判 UNVERIFIABLE→R2-13 折算 NOT_SEARCHED，属误判：例词字段混入词谱说明（「用入声，原用入声韵者…」），'
              '其「例一」七绝 28 字「日照澄洲江雾开，淘金女伴满江隈。美人首饰侯王印，尽是沙中浪底来」'
              '与 tang:4ff2660613c2《雜曲歌辭 浪淘沙 六》（劉禹錫）逐字全同（28/28，ratio=1.0），'
              'R2-14 按例一单段复核，改为 VERIFIED_EXACT。')
    DEFECT = {
        'EX-0076': '例词字段 169 字，实为书页串行：首为秦观《行香子·树绕村庄》（库内无此篇，故无候选），夹「58」等垃圾字符，末又接「例三」李清照《行香子》（songci:342b7f4feafc，异文：别恨难穷/别恨无穷、甚一霎儿晴/甚霎儿晴）。SEARCHED_NO_RESULT 就所标首篇成立，原因须记为「库无此篇」。',
        'EX-0088': '标贺铸《水调歌头》，正文实为苏轼「明月几时有」全篇（228 字含串行），故判 AUTHOR_CONFLICT 成立；题目与正文不合属书内错配。',
        'EX-0096': '标姜夔《八声甘州》，正文 372 字：先张炎「记玉关踏雪事清游」（库内无此篇），后接《扬州慢》词谱说明与姜夔「淮左名都」全篇（库内有）。AUTHOR_CONFLICT 只反映串行后的错配，非单篇结论。',
        'EX-0146': '例词正文含书内校记（「（原作匀红）」「（原作秋波转）」），比对时应先剥离括注；POSSIBLE_MATCH 可能因此低估。',
        'EX-0249': '例词 407 字，含「198」等页眉数字与串行；辛弃疾《摸鱼儿》「更能消几番风雨」全库无此篇（LIKE 检索 0 命中），SEARCHED_NO_RESULT 成立。',
        'EX-0308': '标柳永《定风波》，正文实为苏轼「莫听穿林打叶声」全篇并附「——苏轼」署名，属书内错配；AUTHOR_CONFLICT 成立。',
    }
    if eid in DEFECT:
        ev = ev + '｜R2-14 复核：' + DEFECT[eid]
    out.append(dict(example_id=eid, form_id=r['form_id'],
                    example_first_line=r['example_first_line'],
                    work_title=r['work_title'], author=r['author'],
                    status_hist=hist, final_status=fs, evidence=ev,
                    review_round='R2-10/R2-11/R2-12/R2-13/R2-14'))
n208 = len(out)

# ---------- 102 行新增复核 ----------
MANUAL = {
    'EX-0154': ('songci:357fa7478a28', '偷声木兰花', '张先', '楼/桥'),
    'EX-0167': ('songci:e2fb63407753', '凤栖梧・蝶恋花', '柳永', '立/倚'),
}
r13map = {r['example_id']: r for r in r13}
hist_new = []
for eid in sorted(set(res1) | set(res2)):
    e = examples[eid]
    b = res1.get(eid)
    b2 = res2.get(eid)
    ops = []
    wid = b['best_work_id'] if b else ''
    wau = b['best_author'] if b else ''
    wti = b['best_title'] if b else ''
    ratio = b['best_ratio'] if b else 0
    contained = b['contained'] if b else False
    n_cand = b['n_cand'] if b else 0
    diffs = b['ops'] if b else []
    if b2 and b2['cands']:
        r2v = b2['cands'][0][0]
        if r2v > ratio:
            ratio = r2v
            wid, wau, wti = b2['cands'][0][1], b2['cands'][0][2], b2['cands'][0][3]
            diffs = b2['diffs']
            n_cand = max(n_cand, b2['hits'])
    if eid in MANUAL:
        wid, wti, wau, dv = MANUAL[eid]
        ratio = round(difflib.SequenceMatcher(None, key(e['text']), key(
            con.execute('SELECT text_raw FROM works WHERE work_id=?', (wid,)).fetchone()[0]),
            autojunk=False).ratio(), 4)
        diffs = [['replace', dv.split('/')[0], dv.split('/')[1]]]
        n_cand = 1
    kinds = [cls_diff(t, a, bb) for t, a, bb in diffs]
    textual = [d for d, k in zip(diffs, kinds) if k == 'TEXTUAL']
    charv = [d for d, k in zip(diffs, kinds) if k == 'CHAR_VARIANT']
    ann = [d for d, k in zip(diffs, kinds) if k == 'EXAMPLE_ANNOTATION']
    if not wid or ratio == 0:
        fs = 'SEARCHED_NO_RESULT'
    elif nau(e['author']) != nau(wau):
        fs = 'AUTHOR_CONFLICT'
    elif textual:
        fs = 'VERIFIED_VARIANT' if ratio >= 0.95 else 'POSSIBLE_MATCH'
    else:
        fs = 'VERIFIED_EXACT'   # 仅异体字/书内夹注差异
    tag = []
    if charv:
        tag.append('CHARACTER_VARIANT(' + ','.join(f'{a}/{bb}' for _, a, bb in charv) + ')')
    if ann:
        tag.append('EXAMPLE_ANNOTATION_LEAK(' + ','.join(f'{a}{bb}' for _, a, bb in ann) + ')')
    if textual:
        tag.append('异文(' + ','.join(f'{a}>{bb}' if a else f'脱{a}{bb}' for _, a, bb in textual[:6]) + ')')
    ev = (f"R2-14 独立复核：探针「{cjk(e['text'])[:10]}」+ 异体折叠；候选 {n_cand} 条，"
          f"最佳 {wid}《{wti}》（{wau}），ratio={ratio}，例词 {len(key(e['text']))} 字 / 库文 "
          f"{len(key(con.execute('SELECT text_raw FROM works WHERE work_id=?', (wid,)).fetchone()[0])) if wid else 0} 字；"
          + ('；'.join(tag) if tag else '全文逐字相同'))
    hist = '|'.join(x for x in [f"BASE:{r13map[eid]['prior_status']}" if eid in r13map else '',
                                f"R2-13:{r13map[eid]['new_status']}" if eid in r13map else '',
                                f"R2-14:{fs}"] if x)
    out.append(dict(example_id=eid, form_id=e['form_id'],
                    example_first_line=first_line(e['text']),
                    work_title=wti, author=e['author'], status_hist=hist,
                    final_status=fs, evidence=ev, review_round='R2-13/R2-14'))
    hist_new.append((eid, e['text'], wid, wti, ratio, n_cand, fs, ev))

with open(f'{D}/EXAMPLE_LINK_208_STATUS_FINAL.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['example_id', 'form_id', 'example_first_line', 'work_title',
                                      'author', 'status_hist', 'final_status', 'evidence', 'review_round'])
    w.writeheader()
    w.writerows(out)
print('status_final rows', len(out), 'from208', n208)

# ---------- 检索历史 ----------
H = []
for r in r12:
    H.append(dict(example_id=r['example_id'], round='R2-12', search_terms=r['search_terms'],
                  work_len=r['work_len'], best_ratio=r['best_ratio'], best_work_id=r['best_work_id'],
                  result_status=r['new_status'], note=r['verdict']))
for r in r13:
    H.append(dict(example_id=r['example_id'], round='R2-13', search_terms=r['search_terms'],
                  work_len=r['work_len'], best_ratio=r['best_ratio'], best_work_id=r['best_work_id'],
                  result_status=r['new_status'], note=r['verdict'] + '；' + r['diff_points']))
for eid, text, wid, wti, ratio, n_cand, fs, ev in hist_new:
    H.append(dict(example_id=eid, round='R2-14',
                  search_terms=cjk(text)[:10] + '（首句前10字·8/7/6/5/4字递缩探针·异体折叠）',
                  work_len=n_cand, best_ratio=ratio, best_work_id=wid,
                  result_status=fs, note='独立复核；见 STATUS_FINAL.evidence'))
with open(f'{D}/EXAMPLE_LINK_SEARCH_HISTORY.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['example_id', 'round', 'search_terms', 'work_len',
                                      'best_ratio', 'best_work_id', 'result_status', 'note'])
    w.writeheader()
    w.writerows(H)
print('history rows', len(H), collections.Counter(h['round'] for h in H))

print(collections.Counter(r['final_status'] for r in out))
print('新增复核', len(hist_new))
json.dump(hist_new, open(f'{D}/LOGS/f4_new_rows.json', 'w'), ensure_ascii=False, indent=1)
