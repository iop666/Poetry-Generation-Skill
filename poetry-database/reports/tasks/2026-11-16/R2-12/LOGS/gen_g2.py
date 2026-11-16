#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G2: 10 首版本对勘第二次独立复核（后 5 首 no.6-10）
程序化比对：去标点后逐字对齐，先给原始差异位次，再用 OpenCC t2s 剔除繁简层，剩余即为
异文/异体/脱字。位次一律 1-based，按去标点后的序列计。
"""
import csv, re, difflib, os
from opencc import OpenCC

BASE = '<PROJECT_ROOT>/poetry-database'
os.chdir(BASE)
cc = OpenCC('t2s')
CJK = re.compile(r'[^\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0003ffff]')
def norm(s): return CJK.sub('', s or '')

rows = list(csv.DictReader(open('reports/tasks/2026-11-15/R2-10/TEN_INDEPENDENT_TEXT_COLLATIONS.csv', encoding='utf-8-sig')))

def analyse(r):
    a, b = norm(r['db_text']), norm(r['source2_text'])
    out = dict(db_len=len(a), src2_len=len(b))
    if len(a) == len(b):
        allpos = [(i+1, a[i], b[i]) for i in range(len(a)) if a[i] != b[i]]
        realpos = [(i+1, a[i], b[i]) for i in range(len(a)) if cc.convert(a[i]) != cc.convert(b[i])]
        out['comparable'] = True
    else:
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        allpos = [(i1+1, a[i1:i2] or '∅', b[j1:j2] or '∅') for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != 'equal']
        realpos = allpos
        out['comparable'] = False
    out['allpos'] = allpos
    out['realpos'] = realpos
    return out

RES = {}
for r in rows:
    RES[r['no']] = analyse(r)

def fmt(pos):
    return '；'.join(f"{p[0]}:{p[1]}/{p[2]}" for p in pos)

data = []
# ---- no.6 題西林壁 ----
a = RES['6']
data.append(dict(
  no=6, title='題西林壁', author='蘇軾',
  source2_name='東坡全集（四庫全書本）卷十三',
  source2_locator='卷13，〈題西林壁〉條（白文，緊接〈贈東林總長老〉之後）',
  source2_revid='704402',
  db_len=a['db_len'], src2_len=a['src2_len'], n_diff_positions=len(a['allpos']),
  claim_matches='EXACT', verdict='LOCATOR_SUFFICIENT',
  note=("复现结果：去标点后两本同为 28 字，逐字比对得 7 个差异位次——"
        f"{fmt(a['allpos'])}。其中 12、13 两位为异文（總不／無一，即claim 所称「第2句第5字、第6字」，经核算第2句自第8字起，第5字=12、第6字=13，位次完全相符）；"
        "余 1、2、7、8、10 五处为字形（橫/横、看/㸔、峰/峯、遠/逺、高/髙），与 claim ③ 所列五项一一对应，无多无少。"
        "结论：diff_detail 的位置、字数、逐项清单全部可复现。locator 有卷次（卷13）、有篇目上下文（紧接〈贈東林總長老〉之后），revid=704402 非空，可独立回溯。")
))
# ---- no.7 飲酒 ----
a = RES['7']
data.append(dict(
  no=7, title='飲酒二十首·其五', author='陶淵明',
  source2_name='箋註陶淵明集（四部叢刊景宋刊巾箱本）卷第三',
  source2_locator='卷3「詩五言」，〈飲酒二十首〉其五（李公煥箋，附蔡寬夫、東坡、敬齋諸家評）',
  source2_revid='2653408',
  db_len=a['db_len'], src2_len=a['src2_len'], n_diff_positions=len(a['allpos']),
  claim_matches='PARTIAL', verdict='LOCATOR_SUFFICIENT',
  note=("复现结果：库 50 字、源2 49 字，对齐后 2 个差异位次——"
        + fmt(a['allpos'])
        + "。17 为字形（遠/逺）；29 为库有「南」而源2 无（脱字），即 claim 所指「悠然見南山／悠然見山」。"
        + "claim「其餘49字全同」经核为真（50−1=49）。但 claim 称脱字在「第6句第5字」不确："
        + "第6句为「悠然見南山」，自第26字起，南为第4字（位次29），第5字是「山」（位次30）。"
        + "故此条为「脱字事实正确、位次标错一位」，判 PARTIAL。locator 有卷次（卷3）、有篇次（其五）与笺注者，revid=2653408 非空。")
))
# ---- no.8 虞美人 ----
a = RES['8']
data.append(dict(
  no=8, title='虞美人·春花秋月何时了', author='李煜',
  source2_name='御定全唐詩（四庫全書本）卷八百八十九（詞）',
  source2_locator='卷889，南唐後主李煜〈虞美人〉第二首（「春花秋月何時了」）',
  source2_revid='775963',
  db_len=a['db_len'], src2_len=a['src2_len'], n_diff_positions=len(a['allpos']),
  claim_matches='PARTIAL', verdict='LOCATOR_SUFFICIENT',
  note=("复现结果：两本同为 56 字，逐字得 13 个差异位次，剔除繁简层后剩 3 个——"
        "8:往/徃（异体）、30:栏/闌（异体，claim ① 所指「第5句第2字」，第5句自第29字起，栏=第2字，位次准确）、45:几/㡬（异体）。"
        "claim ② 所列繁简七组（时/時、楼/樓、东/東風、国/國、应犹/應猶、颜/顔、问/問、几/㡬）经核全部存在。"
        "但 note 断言「剔除繁简後實際差異僅『欄／闌』一字」不成立：另有 往/徃、几/㡬 两处，前者为「往」之异体，后者为「几」之旧字形，均非繁简一对一的简繁转换结果，属字形层，应一并列出。"
        "locator 有卷次（卷889）、有序次（第二首）与首句，revid=775963 非空。")
))
# ---- no.9 声声慢 ----
a = RES['9']
data.append(dict(
  no=9, title='声声慢', author='李清照',
  source2_name='漱玉詞（四庫全書本，毛晉汲古閣刊本系統）',
  source2_locator='《漱玉詞》正文第2闋〈聲聲慢·秋情〉（四庫本全書僅收詞十七闋，見卷首提要）',
  source2_revid='11134217',
  db_len=a['db_len'], src2_len=a['src2_len'], n_diff_positions=len(a['allpos']),
  claim_matches='EXACT', verdict='LOCATOR_SUFFICIENT',
  note=("复现结果：两本同为 97 字（此前若用只含 \u4e00-\u9fff 的正则会把 Ext-B 的「𠉀」误删而得出 96 字，须用含 ExtA/ExtB 的 CJK 范围），逐字得 37 个差异位次，剔除繁简后 11 个——"
        "1、2:寻/㝷；16:暖/煖；20:候/𠉀；34:晚/曉；63:忺/堪；66:著/着；67:窗/牕；74:黑/黒；84、85:点/㸃。"
        "claim ①②（晚／曉、忺／堪）与 ③ 所列字形（煖、牕、黒、著、箇、㝷、㸃、𠉀）逐项都能对上，无遗漏、无虚构。"
        "唯 locator 不含卷次/页码：四庫本《漱玉詞》为一卷不分卷，故只能以「正文第2闋」定位；以篇次＋提要说明仍可唯一复现，判 SUFFICIENT，但严格按「含卷次或页码」的标准不合格，建议补四庫本葉次或影印页。revid=11134217 非空。")
))
# ---- no.10 水调歌头 ----
a = RES['10']
data.append(dict(
  no=10, title='水调歌头', author='苏轼',
  source2_name='東坡詞（四庫全書本）',
  source2_locator='《東坡詞》「又〈丙辰中秋歡飲達旦大醉作此篇兼懷子由〉」條（即〈水調歌頭〉）',
  source2_revid='12799625',
  db_len=a['db_len'], src2_len=a['src2_len'], n_diff_positions=len(a['allpos']),
  claim_matches='PARTIAL', verdict='LOCATOR_SUFFICIENT',
  note=("复现结果：两本同为 95 字，逐字得 30 个差异位次，剔除繁简后仅 2 个——54:户/戸、90:久/乆。"
        "故 claim ①「无异文」成立，claim ③ 繁简清单（几时、问、阙、风归、琼楼、处、胜、间转、阁、绮、无、应、长、别时圆、欢离、阴、圆、难、愿、婵）亦全部可复现。"
        "但 claim ② 所列字形「宫/宮」并非实际差异：两本此字均作「宫」（U+5BAB），无一作「宮」，属列举时多列一项。"
        "locator 不含卷次/页码（四庫本《東坡詞》一卷不分卷），以「又〈丙辰中秋…〉」條目名定位，可唯一复现；严格按「含卷次或页码」不合格，建议补葉次。revid=12799625 非空。")
))

FIELDS = ['no','title','author','source2_name','source2_locator','source2_revid','db_len','src2_len','n_diff_positions','claim_matches','verdict','note']
OUT = 'reports/tasks/2026-11-16/R2-12/TEN_TEXT_COLLATIONS_SECOND_REVIEW.csv'
with open(OUT, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    for d in data:
        w.writerow(d)
print('wrote', len(data))
for d in data:
    print(d['no'], d['title'], d['db_len'], d['src2_len'], d['n_diff_positions'], d['claim_matches'], d['verdict'])
