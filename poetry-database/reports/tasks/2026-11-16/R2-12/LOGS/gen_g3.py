#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G3: 例词关联 100 条真正独立复核（与上一轮 88 条 + 20 条零交集）

检索与判定：
 - 归一化 = 转简(t2s) + 去标点/非汉字（不转简会因「蘋/苹」「簾/帘」等把公共子串切碎，见 LOGS 记录）
 - 检索词级联：首句前10字 → 前8 → 前6 → 中段8字(1/3处) → 中段8字(2/3处)，记录实际命中者与候选数
 - lcs_ratio = 最长公共子串 / 例词长度（按任务要求报告）
 - sim = 1 - 编辑差异字数/较长文本长度（用于判定；长调中数处散点异文会把 LCS 切碎，故不能单用 LCS 判态）
 - 升级门槛三条同时成立：全异文清单已列 + 作者规范化后一致 + 同词牌
"""
import csv, re, sqlite3, difflib, os, collections
from opencc import OpenCC

BASE = '<PROJECT_ROOT>/poetry-database'
os.chdir(BASE)
t2s, s2t = OpenCC('t2s'), OpenCC('s2t')
CJK = re.compile(r'[^\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0003ffff]')
def norm(s): return CJK.sub('', t2s.convert(s or ''))      # 去标点 + 转简
def nkey(s): return CJK.sub('', t2s.convert(s or ''))

conn = sqlite3.connect('database/poetry.db')
conn.row_factory = sqlite3.Row
ALIAS = {}
for r in conn.execute("select raw_name,canonical from author_alias"):
    ALIAS[nkey(r['raw_name'])] = nkey(r['canonical'])
# 库内未归并而同人者：李煜＝後主煜（两 author_id：A:5fdb58af57 / A:7ca996ca82）
SAME_PERSON = {'李煜': '李煜', '后主煜': '李煜'}
def nauth(s):
    k = nkey(s)
    k = ALIAS.get(k, k)
    return SAME_PERSON.get(k, k)
ex = {r['example_id']: r for r in conn.execute(
    "select example_id,form_id,cipai_name,author,text,n_chars,pdf_page,printed_page from cipai_form_examples_r2_08")}
status = {r['example_id']: r for r in csv.DictReader(
    open('reports/tasks/2026-11-15/R2-10/EXAMPLE_310_FINAL_STATUS.csv', encoding='utf-8-sig'))}

p88 = {r['link_id'] for r in csv.DictReader(
    open('reports/tasks/2026-11-15/R2-11/EXAMPLE_LINK_100_FINAL_AUDIT.csv', encoding='utf-8-sig'))}

rev = list(csv.DictReader(open('reports/tasks/2026-11-15/R2-10/EXAMPLE_100_INDEPENDENT_REVIEW.csv', encoding='utf-8-sig')))
ag = [r for r in rev if r['review_type'] == 'INDEPENDENT_AGENT']
idx = collections.defaultdict(list)
for eid, e in ex.items():
    idx[norm(e['text'])[:12]].append(eid)
p20, map_log = set(), []
for r in ag:
    m = re.search(r'例詞[「『]([^」』]+)', r['evidence'])
    q = norm(m.group(1)) if m else ''
    hit = None
    for L in (12, 10, 8):
        c = idx.get(q[:L])
        if c:
            hit = sorted(c)[0]; break
    map_log.append((r['item_id'], q[:12], hit))
    if hit: p20.add(hit)
assert len(p20) == 20, len(p20)
assert not (p88 & p20)

prior_all = p88 | p20
remaining = [e for e in sorted(ex) if e not in prior_all]
assert len(remaining) == 202

nm = [e for e in remaining if status[e]['new_match_kind'] == 'NO_MATCH']
vv = [e for e in remaining if status[e]['new_match_kind'] == 'VERIFIED_VARIANT']
extra = [e for e in remaining if status[e]['new_match_kind'] in ('AUTHOR_CONFLICT', 'TITLE_ONLY')]
sel = extra + nm + vv[:max(0, 100 - len(nm) - len(extra))]
assert len(sel) == 100, len(sel)
assert not (set(sel) & prior_all)
assert len(set(sel)) == 100

print('loading works ...', flush=True)
works = conn.execute(
    "select work_id,title_raw,author_name,author_canonical,dynasty,cipai,collection,text_norm,text_raw from works").fetchall()
# 预归一化，避免每次重复转换
W = []
for w in works:
    tn_raw = w['text_norm'] or ''
    tn = CJK.sub('', tn_raw)          # 仅去标点，不作繁简转换
    tr = CJK.sub('', w['text_raw'] or '')
    if tn or tr:
        W.append((w, tn, tr))
print('works', len(W), flush=True)

def search(term):
    """term 为简体无标点串；分别在 works.text_norm 与 works.text_raw 中做子串检索，
    并为繁体底本另检其繁体形式（同一字形的两种写法都算命中）"""
    trad = CJK.sub('', s2t.convert(term))
    return [w for w, tn, tr in W if (term in tn) or (trad in tn) or (trad in tr)]

def opcodes(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != 'equal':
            out.append((tag, i1 + 1, a[i1:i2] or '∅', b[j1:j2] or '∅'))
    return out

def lcs_len(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b)).size

# 词牌别名组：cipai_specs 正名 + aliases 中《…》所列异名
CIPAI_GROUP = {}
for r in conn.execute("select name,aliases from cipai_specs where name is not null"):
    keys = {nkey(r['name'])}
    for a in re.findall(r'《([^》]+)》', r['aliases'] or ''):
        keys.add(nkey(a))
    keys.discard('')
    gid = nkey(r['name'])
    for k in keys:
        CIPAI_GROUP.setdefault(k, gid)
def cipai_gid(name):
    k = nkey(name)
    if not k: return None
    if k in CIPAI_GROUP: return CIPAI_GROUP[k]
    for g in set(CIPAI_GROUP.values()):
        if g and (g in k or k in g): return g
    return None
def same_cipai(ex_cp, w):
    a = cipai_gid(ex_cp)
    for c in (w['cipai'] or '', w['title_raw'] or ''):
        if not c: continue
        if a is not None and cipai_gid(c) == a: return True
        # 题名形如「望江南・忆江南」「長相思 一」，去序次后含别名
        base = re.sub(r'[ 一二三四五六七八九十]+$', '', c)
        if nkey(ex_cp) and nkey(ex_cp) in nkey(base): return True
    return False

rows = []
for eid in sel:
    e = ex[eid]; st = status[eid]
    et = norm(e['text'])
    L = len(et)
    cands = [
        ('首句前10字', et[:min(10, L)]),
        ('首句前8字', et[:min(8, L)]),
        ('首句前6字', et[:min(6, L)]),
        ('中段8字(1/3处)', et[L // 3:L // 3 + 8]),
        ('中段8字(2/3处)', et[2 * L // 3:2 * L // 3 + 8]),
    ]
    seen, attempted = set(), []
    hits, used, how = [], '', ''
    for label, t in cands:
        if len(t) < 4 or t in seen: continue
        seen.add(t); attempted.append(f"{label}「{t}」")
        h = search(t)
        if h:
            hits, used, how = h, t, label
            break
    if not hits:
        used = '／'.join(attempted)
        how = '全部落空'
    best, best_sim, best_lcs, best_cov = None, 0.0, 0.0, 0.0
    for w in hits:
        wt = norm(w['text_norm'] or w['text_raw'] or '')
        if not wt: continue
        ops = opcodes(et, wt)
        ndiff = sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in
                    difflib.SequenceMatcher(None, et, wt, autojunk=False).get_opcodes() if tag != 'equal')
        sim = 1 - ndiff / max(len(et), len(wt))
        l = lcs_len(et, wt)
        if sim > best_sim:
            best, best_sim, best_lcs, best_cov = w, sim, l, l / len(et)
    auth_ok = cp_ok = None; diffs = []
    if best is not None:
        wa = best['author_canonical'] or best['author_name'] or ''
        auth_ok = (nauth(wa) == nauth(e['author']))
        cp_ok = same_cipai(e['cipai_name'], best)
        diffs = opcodes(et, norm(best['text_norm'] or best['text_raw'] or ''))
    if not hits:
        new, verdict = 'SEARCHED_NO_RESULT', 'CONFIRMED_NO_MATCH'
    elif best_sim >= 0.999 and auth_ok and cp_ok:
        new = 'VERIFIED_EXACT'
        verdict = 'UPGRADED' if st['new_match_kind'] != 'VERIFIED_EXACT' else 'CONFIRMED'
    elif best_sim >= 0.95 and auth_ok and cp_ok:
        new = 'VERIFIED_VARIANT'
        verdict = 'UPGRADED' if st['new_match_kind'] == 'NO_MATCH' else 'CONFIRMED'
    elif best_sim >= 0.95 and auth_ok is False:
        new = 'AUTHOR_CONFLICT'
        verdict = 'UPGRADED' if st['new_match_kind'] == 'NO_MATCH' else 'CONFIRMED'
    elif best_sim >= 0.5:
        new = 'POSSIBLE_MATCH'
        verdict = 'UPGRADED' if st['new_match_kind'] == 'NO_MATCH' else 'DOWNGRADED'
    elif best is not None and cp_ok:
        new = 'TITLE_ONLY'
        verdict = 'DOWNGRADED' if st['new_match_kind'] != 'TITLE_ONLY' else 'CONFIRMED'
    else:
        new, verdict = 'SEARCHED_NO_RESULT', 'CONFIRMED_NO_MATCH'
    if new in ('VERIFIED_EXACT', 'VERIFIED_VARIANT') and not (diffs == [] or len(diffs) > 0):
        raise AssertionError
    if len(diffs) > 20:
        dp = '；'.join(f"{p[1]}:{p[2]}/{p[3]}" for p in diffs[:20]) + f'；…共{len(diffs)}处'
    else:
        dp = '；'.join(f"{p[1]}:{p[2]}/{p[3]}" for p in diffs)
    rows.append(dict(
        example_id=eid, form_id=e['form_id'],
        example_first_line=re.split(r'[，。？；]', e['text'])[0][:30],
        work_title=(best['title_raw'] if best else ''), author=(best['author_name'] if best else ''),
        prior_status=st['new_match_kind'], search_terms=f"{used}（{how}）", work_len=len(hits),
        best_ratio=round(best_sim, 4), best_work_id=(best['work_id'] if best else ''),
        diff_points=dp, new_status=new, verdict=verdict,
        evidence=(f"检索「{used}」（{how}）：归一化 text_norm/text_raw 子串命中 {len(hits)} 条；"
                  + (f"最佳 {best['work_id']}《{best['title_raw']}》({best['author_name']})，"
                     f"例词 {len(et)} 字／作品 {len(norm(best['text_norm'] or ''))} 字，"
                     f"LCS最长公共子串覆盖 {best_cov:.3f}，逐字相似 {best_sim:.4f}，异文 {len(diffs)} 处，"
                     f"作者一致={auth_ok}，词牌一致={cp_ok}，三条件{'齐备' if (auth_ok and cp_ok and True) else '不齐'}"
                     if best else "无候选：已依次检索 " + used + "，四/五级检索词在 text_norm 与 text_raw 中均 0 命中")
                  )
    ))

FIELDS = ['example_id','form_id','example_first_line','work_title','author','prior_status','search_terms',
          'work_len','best_ratio','best_work_id','diff_points','new_status','verdict','evidence']
OUT = 'reports/tasks/2026-11-16/R2-12/EXAMPLE_LINK_100_INDEPENDENT_VERIFICATION.csv'
with open(OUT, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    for r in rows: w.writerow(r)

print('selected', len(sel), '| pools: extra', len(extra), 'NO_MATCH', len(nm), 'VERIFIED_VARIANT', len(vv))
print('new_status', collections.Counter(r['new_status'] for r in rows))
print('verdict', collections.Counter(r['verdict'] for r in rows))
print('cross-tab:')
for k, v in sorted(collections.Counter((r['prior_status'], r['new_status']) for r in rows).items()):
    print('  ', k, v)
print('search method', collections.Counter(r['search_terms'].split('（')[1].rstrip('）') for r in rows))
print('zero-overlap |sel ∩ prior| =', len(set(sel) & prior_all))
