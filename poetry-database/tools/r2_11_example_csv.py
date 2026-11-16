#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-11 F2: 由 f2_detail.json 生成 EXAMPLE_LINK_100_FINAL_AUDIT.csv（规则表见 LOGS/F2_F3_notes.md）"""
import csv, json, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from r2_11_example_recheck import norm

BASE = '<PROJECT_ROOT>/poetry-database'
OUT = os.path.join(BASE, 'reports/tasks/2026-11-15/R2-11')
D = json.load(open(os.path.join(OUT, 'LOGS/f2_detail.json'), encoding='utf-8'))

# 逐条人工判词覆盖（规则判定后再核过的例外，key=example_id）
NOTE = {
 'EX-0083': '例词栏为合编段落（本词+「例二」秦观《满庭芳》），正文首段与作品苏轼《满庭芳》相似 0.968，但例词作者栏标「秦观」，与作品作者「苏轼」冲突',
 'EX-0308': '例词栏混入「格二」词谱符号与「例三」柳永《定风波》；首段（苏轼《定风波》莫听穿林打叶声）与作品相似 0.968，例词作者栏标「柳永」与作品「苏轼」冲突',
 'EX-0091': '例词与作品为同一阕（同作者同调），属《乐府雅词》一系异文（起来人未梳头/宝奁闲掩/今年瘦/明朝…），相似 0.758，未达 0.80 异文门槛，只宜升到 POSSIBLE_MATCH',
 'EX-0184': '作品 author_name 字段被截断为「张」（应为张昇），作者无法比对；正文相似 0.861 已达异文水平，但作者不可核，维持 POSSIBLE_MATCH',
 'EX-0012': '例词正文非词作文本，而是词谱说明（「用入声，原用入声韵者…」），无法作为作品核验对象',
 'EX-0050': '正文与库内蔡伸《柳梢青》相似 0.898（梨花飞雪/飘雪等），例词作者栏标贺铸，与作品作者冲突',
 'EX-0275': '正文与库内王安石《菩萨蛮》相似 0.727（数间/数家、窄衫/单衫、花是去年红/今日是何朝），差异超出异文门槛，只判 POSSIBLE_MATCH',
 'EX-0002': '正文与库内张孝祥《苍梧谣・归字谣》相似 0.875（西风/薰风、卷/飐），同作者同调别名',
 'EX-0156': '例词正文夹「不叶韵」编例小注，剔除后相似 0.962',
 'EX-0072': '例词正文夹「（“也”是衬字）」小注，剔除后相似 0.939',
 'EX-0022': '例词正文夹「（增字）」小注，剔除后相似 0.947',
 'EX-0021': '例词首字「䴔䴖」在 OCR 中缺失（作品 35 字，例词 33 字），补足后相似 0.943',
 'EX-0177': '全库 works 表无作者「程垓」（作者检索 0 篇），亦无「月挂霜林寒欲坠」文句，NO_MATCH 成立',
 'EX-0033': '辛弃疾名下 257 篇逐一比对，无「北陇田高踏水频」一阕，NO_MATCH 成立',
 'EX-0073': '辛弃疾名下 257 篇无《破阵子》「醉里挑灯看剑」；全库含「挑灯看剑」者仅 7 篇他人诗作（杨冠卿、文天祥、汪元量等），非本词',
 'EX-0097': '姜夔名下 196 篇无《扬州慢》「淮左名都」，全库 instr 检索亦无命中，NO_MATCH 成立',
 'EX-0131': '辛弃疾名下 257 篇无《霜天晓角》「吴头楚尾」，NO_MATCH 成立',
 'EX-0196': '姜夔名下 196 篇无《惜红衣》「簟枕邀凉」，NO_MATCH 成立',
 'EX-0222': '姜夔名下 196 篇无《翠楼吟》「月冷龙沙」，NO_MATCH 成立',
 'EX-0250': '辛弃疾名下 257 篇无《贺新郎》「绿树听鹈鴂」，NO_MATCH 成立',
}


def cls(r):
    if r['ratio'] is None:
        return 'NO_TEXT'
    if r['lev'] == 0 and r['seg_len'] == r['work_len_norm']:
        return 'T0'
    if r['ratio'] >= 0.95:
        return 'T1'
    if r['ratio'] >= 0.80:
        return 'T2'
    if r['ratio'] >= 0.60:
        return 'T3'
    return 'T4'


def decide(r):
    claim = r['claim']
    c = cls(r)
    A = r['same_author_calc']
    if claim == 'NO_MATCH':
        f = r['found']
        if not f:
            return 'CONFIRMED', 'NO_MATCH'
        sc, wid, ti, an, ln, cont = f[0]['score'], f[0]['wid'], f[0]['title'], f[0]['author'], f[0]['ln'], f[0]['cont']
        same = norm(an) == norm(r['author'])
        if sc >= 0.80 and same:
            return 'CORRECTED_UP', 'VERIFIED_VARIANT'
        if sc >= 0.85 and not same:
            return 'CORRECTED_UP', 'AUTHOR_CONFLICT'
        if sc >= 0.60 and same:
            return 'CORRECTED_UP', 'POSSIBLE_MATCH'
        return 'CONFIRMED', 'NO_MATCH'
    if c == 'T4':
        return 'CORRECTED_DOWN', 'TITLE_ONLY'
    if claim == 'AUTHOR_CONFLICT':
        return ('CONFIRMED', 'AUTHOR_CONFLICT') if not A else ('CORRECTED_DOWN', 'VERIFIED_VARIANT')
    if claim == 'TITLE_ONLY':
        if c in ('T0', 'T1', 'T2'):
            return ('CORRECTED_UP', 'AUTHOR_CONFLICT') if not A else ('CORRECTED_UP', 'VERIFIED_VARIANT')
        if c == 'T3':
            return ('CORRECTED_UP', 'POSSIBLE_MATCH')
        return 'CONFIRMED', 'TITLE_ONLY'
    if claim == 'POSSIBLE_MATCH':
        if c == 'T0':
            return 'CORRECTED_UP', 'VERIFIED_EXACT'
        if c in ('T1', 'T2') and A:
            return 'CORRECTED_UP', 'VERIFIED_VARIANT'
        return 'CONFIRMED', 'POSSIBLE_MATCH'
    if claim == 'VERIFIED_VARIANT':
        if c == 'T0':
            return 'CORRECTED_UP', 'VERIFIED_EXACT'
        if c in ('T1', 'T2'):
            return 'CONFIRMED', 'VERIFIED_VARIANT'
        if c == 'T3':
            return 'CORRECTED_DOWN', 'POSSIBLE_MATCH'
        return 'CORRECTED_DOWN', 'TITLE_ONLY'
    if claim == 'VERIFIED_EXACT':
        if c == 'T0':
            return 'CONFIRMED', 'VERIFIED_EXACT'
        if c in ('T1', 'T2'):
            return 'CORRECTED_DOWN', 'VERIFIED_VARIANT'
        return 'CORRECTED_DOWN', 'POSSIBLE_MATCH'
    return 'UNVERIFIABLE', claim


def evid(r):
    bits = []
    if r['ratio'] is None:
        bits.append('链接表无 work_id（work_len=0，未产生候选）')
        f = r['found']
        if f:
            b = f[0]
            bits.append('%s 检索命中 %s《%s》作者%s 长%d' % (b['via'], b['wid'], b['title'], b['author'], b['ln']))
            bits.append('例词长%d 与该作品相似 %.4f（Levenshtein）' % (len(r['ex_norm']), b['score']))
            if b['cont']:
                bits.append('例词正文被作品完整包含')
            if len(f) > 1:
                bits.append('另一候选 %s《%s》相似 %.4f' % (f[1]['wid'], f[1]['title'], f[1]['score']))
        else:
            bits.append('该作者名下 %d 篇 + 同词牌作品逐条比对，全库最高相似 <0.45，无同作者同调近文' % r['n_candidate_pool'])
        return '；'.join(bits)
    bits.append('例词 %d 字 / 作品 %d 字（作品 %s《%s》作者%s）' % (
        r['seg_len'], r['work_len_norm'], r['work_id'], r['work_title'], r['work_author']))
    bits.append('lev=%d，相似 %.4f' % (r['lev'], r['ratio']))
    if r['n_seg'] > 1:
        bits.append('例词正文切为 %d 段后取最贴合段（整段相似仅 %.3f）' % (r['n_seg'], r['whole_ratio']))
    if r['dif']:
        bits.append('异文：' + r['dif'])
    else:
        bits.append('规范化后逐字全等')
    bits.append('作者一致' if r['same_author_calc'] else '作者不一致（例词栏「%s」vs 作品「%s」）' % (r['author'], r['work_author']))
    return '；'.join(bits)


rows = []
assert not ({x['example_id'] for x in D['rows']} & set(D['reviewed_r2_10'].values())), '与 R2-10 已复核样本重叠'
for r in D['rows']:
    verdict, final = decide(r)
    if r['example_id'] == 'EX-0012':
        verdict, final = 'DATA_ERROR', 'UNVERIFIABLE'
    note = NOTE.get(r['example_id'], '')
    method = 'Levenshtein+段落切分' + ('+全库instr检索' if r['claim'] in ('NO_MATCH', 'TITLE_ONLY') else '')
    e = evid(r)
    if note:
        e = e + '；' + note
    wt = (r['work_title'] if r['work_id'] else
          ('（未链接；候选《%s》%s %s）' % (r['found'][0]['title'], r['found'][0]['author'],
                                         r['found'][0]['wid']) if r['found'] else '（未链接，无候选）'))
    if r['example_id'] == 'EX-0012':
        wt = '（未链接；例词正文为词谱说明，不作候选）'
    rows.append(dict(
        link_id=r['example_id'], form_id=r['form_id'],
        example_line=re.sub(r'\s+', '', r['ex_text'] or ''),
        work_title=wt,
        claim_status=r['claim'], check_method=method, evidence=e,
        verdict=verdict, final_status=final))

f = os.path.join(OUT, 'EXAMPLE_LINK_100_FINAL_AUDIT.csv')
with open(f, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['link_id', 'form_id', 'example_line', 'work_title',
                                       'claim_status', 'check_method', 'evidence', 'verdict',
                                       'final_status'])
    w.writeheader()
    w.writerows(rows)
print('wrote', f, len(rows))
from collections import Counter
print(Counter(x['claim_status'] for x in rows))
print(Counter(x['verdict'] for x in rows))
print(Counter(x['final_status'] for x in rows))
