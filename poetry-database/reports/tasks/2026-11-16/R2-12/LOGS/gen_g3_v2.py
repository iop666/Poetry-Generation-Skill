#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G3: 例词关联 100 条真正独立复核（与上一轮 88 条 + 20 条零交集）

检索与判定：
 - 归一化 = 转简(t2s) + 去标点/非汉字。若不转简，「蘋/苹」「簾/帘」等会把公共子串切碎，
   实测会使 1 字之差的 54 字词 LCS 从 1.000 掉到 0.552（见 LOGS/G_notes.md）。
 - 检索词级联：首句前10字 → 前8 → 前6 → 中段8字(1/3) → 中段8字(2/3)；
   分别在 works.text_norm 与 works.text_raw 中做子串检索（繁体底本另检繁体形式）。
 - lcs_ratio = 最长公共子串 / 例词长度（按任务要求逐条报告，写入 evidence）；
 - sim = 1 - 编辑差异字数 / 较长文本长度（用于判态；长调中数处散点异文会使 LCS 天然切碎，
   如 133 字 4 处异文时 LCS 仅 0.40 而 sim=0.97，故不能单用 LCS 判态）；
 - 升级三条件：①全部异文逐处列出 ②作者规范化后一致 ③同词牌（含 cipai_specs 异名）。
"""
import csv, re, sqlite3, difflib, os, collections
from opencc import OpenCC

BASE = '<PROJECT_ROOT>/poetry-database'
os.chdir(BASE)
t2s, s2t = OpenCC('t2s'), OpenCC('s2t')
CJK = re.compile(r'[^\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0003ffff]')
def nkey(s): return CJK.sub('', t2s.convert(s or ''))
norm = nkey

conn = sqlite3.connect('database/poetry.db')
conn.row_factory = sqlite3.Row

ALIAS = {}
for r in conn.execute("select raw_name,canonical from author_alias"):
    ALIAS[nkey(r['raw_name'])] = nkey(r['canonical'])
SAME_PERSON = {'后主煜': '李煜'}      # 库内 A:7ca996ca82(後主煜) 与 A:5fdb58af57(李煜) 同人未并
def nauth(s):
    k = ALIAS.get(nkey(s), nkey(s))
    return SAME_PERSON.get(k, k)

CIPAI_GROUP, GROUP_KEYS = {}, {}
for r in conn.execute("select name,aliases from cipai_specs where name is not null"):
    keys = {nkey(r['name'])} | {nkey(a) for a in re.findall(r'《([^》]+)》', r['aliases'] or '')}
    keys.discard('')
    gid = nkey(r['name'])
    for k in keys:
        CIPAI_GROUP.setdefault(k, gid)
        GROUP_KEYS.setdefault(gid, set()).add(k)
def _strip_seq(s):
    s = re.sub(r'\s+', '', s or '')
    return re.sub(r'[一二三四五六七八九十百零〇0-9]+$', '', s)
def same_cipai(ex_cp, w):
    """同词牌判定：①例词名整体出现在作品题名/词牌中 ②词牌异名组相同 ③组内任一异名出现在题名中"""
    a = _strip_seq(nkey(ex_cp))
    if len(a) < 2: return False
    gid = CIPAI_GROUP.get(a)
    keys = GROUP_KEYS.get(gid, {a}) if gid else {a}
    for field in (w['cipai'] or '', w['title_raw'] or ''):
        f = nkey(field)
        if not f: continue
        if a in f: return True
        if gid and CIPAI_GROUP.get(_strip_seq(f)) == gid: return True
        for tok in re.split(r'[・·／/\s]+', field):
            t = _strip_seq(nkey(tok))
            if not t: continue
            if gid and CIPAI_GROUP.get(t) == gid: return True
            if any(k in t for k in keys if len(k) >= 2): return True
    return False

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
W = []
for w in works:
    tn = CJK.sub('', w['text_norm'] or '')
    tr = CJK.sub('', w['text_raw'] or '')
    if tn or tr:
        W.append((w, tn, tr))
print('works', len(W), flush=True)

def search(term):
    trad = CJK.sub('', s2t.convert(term))
    return [w for w, tn, tr in W if (term in tn) or (trad in tn) or (trad in tr)]

def opcodes(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return [(tag, i1 + 1, a[i1:i2] or '∅', b[j1:j2] or '∅')
            for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != 'equal']

def lcs_len(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b)).size

rows = []
for eid in sel:
    e = ex[eid]; st = status[eid]
    et = norm(e['text']); L = len(et)
    cands = [('首句前10字', et[:min(10, L)]), ('首句前8字', et[:min(8, L)]),
             ('首句前6字', et[:min(6, L)]), ('中段8字(1/3处)', et[L // 3:L // 3 + 8]),
             ('中段8字(2/3处)', et[2 * L // 3:2 * L // 3 + 8])]
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
        used, how = ' ／ '.join(attempted), '全部落空'

    best, best_sim, best_lcs, best_cov, best_diffs, best_wt = None, 0.0, 0, 0.0, [], ''
    for w in hits:
        wt = norm(w['text_norm'] or w['text_raw'] or '')
        if not wt: continue
        sm = difflib.SequenceMatcher(None, et, wt, autojunk=False)
        nd = sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != 'equal')
        sim = 1 - nd / max(len(et), len(wt))
        if sim > best_sim:
            best, best_sim, best_wt = w, sim, wt
            best_lcs = lcs_len(et, wt)
            best_cov = best_lcs / len(et)
            best_diffs = opcodes(et, wt)

    auth_ok = cp_ok = None
    if best is not None:
        auth_ok = (nauth(best['author_canonical'] or best['author_name'] or '') == nauth(e['author']))
        cp_ok = same_cipai(e['cipai_name'], best)

    if not hits:
        new, verdict, why = 'SEARCHED_NO_RESULT', 'CONFIRMED_NO_MATCH', '五级检索词在 text_norm/text_raw 均 0 命中'
    elif best_sim >= 0.999 and auth_ok and cp_ok:
        new = 'VERIFIED_EXACT'
        verdict = 'UPGRADED' if st['new_match_kind'] != 'VERIFIED_EXACT' else 'CONFIRMED'
        why = '逐字全同（0 异文）+ 作者规范化后一致 + 同词牌'
    elif best_sim >= 0.95 and auth_ok and cp_ok:
        new = 'VERIFIED_VARIANT'
        verdict = 'UPGRADED' if st['new_match_kind'] == 'NO_MATCH' else 'CONFIRMED'
        why = f'异文 {len(best_diffs)} 处已逐处列出 + 作者一致 + 同词牌，相似 {best_sim:.4f}'
    elif best_sim >= 0.95 and auth_ok is False:
        new = 'AUTHOR_CONFLICT'
        verdict = 'UPGRADED' if st['new_match_kind'] == 'NO_MATCH' else 'CONFIRMED'
        why = f'文本相似 {best_sim:.4f} 但作者不一致（{e["author"]} vs {best["author_name"]}）'
    elif best_sim >= 0.5:
        new = 'POSSIBLE_MATCH'
        verdict = 'UPGRADED' if st['new_match_kind'] == 'NO_MATCH' else 'DOWNGRADED'
        fail = []
        if best_sim < 0.95: fail.append(f'相似 {best_sim:.4f} 未达 0.95')
        if auth_ok is False: fail.append('作者不一致')
        if cp_ok is False: fail.append('词牌名不一致（含异名仍未对上）')
        why = '未升级：' + '、'.join(fail)
    elif cp_ok:
        new = 'TITLE_ONLY'
        verdict = 'DOWNGRADED' if st['new_match_kind'] != 'TITLE_ONLY' else 'CONFIRMED'
        why = f'仅词牌/题名相合，文本相似仅 {best_sim:.3f}'
    else:
        new, verdict, why = 'SEARCHED_NO_RESULT', 'CONFIRMED_NO_MATCH', f'命中候选但相似仅 {best_sim:.3f} 且词牌不同，视为无关命中'

    dp = '；'.join(f"{p[1]}:{p[2]}/{p[3]}" for p in best_diffs[:20]) + (f'；…共{len(best_diffs)}处' if len(best_diffs) > 20 else '')
    ev = (f"检索「{used}」（{how}）：归一化后 text_norm/text_raw 子串命中 {len(hits)} 条。"
          if hits else f"已检索：{used}（五级检索词）——text_norm 与 text_raw 均 0 命中。")
    if best is not None:
        ev += (f"最佳 {best['work_id']}《{best['title_raw']}》({best['author_name']})："
               f"例词 {len(et)} 字／作品 {len(best_wt)} 字，最长公共子串 {best_lcs} 字（覆盖 {best_cov:.3f}），"
               f"逐字相似 {best_sim:.4f}，异文 {len(best_diffs)} 处；作者一致={auth_ok}，词牌一致={cp_ok}。判定：{why}。")
    else:
        ev += '无候选。判定：' + why + '。'

    rows.append(dict(
        example_id=eid, form_id=e['form_id'],
        example_first_line=re.split(r'[，。？；！]', e['text'])[0][:30],
        work_title=(best['title_raw'] if best else ''), author=(best['author_name'] if best else ''),
        prior_status=st['new_match_kind'], search_terms=f"{used}（{how}）", work_len=len(hits),
        best_ratio=round(best_sim, 4), best_work_id=(best['work_id'] if best else ''),
        diff_points=dp, new_status=new, verdict=verdict, evidence=ev))

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
print('zero-overlap |sel ∩ prior| =', len(set(sel) & prior_all))
print('hit method', collections.Counter(r['search_terms'].split('（')[1].rstrip('）') if '（' in r['search_terms'] else '?' for r in rows))
