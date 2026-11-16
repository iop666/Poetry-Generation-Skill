#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G4: 上古音 40 例证据最终审查

评分口径（7 要素，逐条只依据输入文件中已有的信息，不补造任何书名/页码）：
 E1 学者姓名      —— scholar 有负责主体（个人或署名的机构）＝1；未署名／（無）／無責任作者＝0
 E2 著作或论文名  —— work_title 具体可识＝1；否则 0
 E3 出版信息      —— 出现「出版社＋年份」或「刊名＋年期」＝1；只有刊名无年期、或全无＝0
 E4 页码或段落位置—— locator 给出 页/卷/条/章/段 等可定位单位＝1；仅 URL 或明言「缺」＝0
 E5 对应诗句      —— 引文标注篇/章名，或直接引原诗句＝1；只列韵脚字而不注所出篇＝0
 E6 韵脚字        —— 具体列出韵脚字（非仅位置编号）＝1
 E7 韵部判断      —— 引文给出古韵部名（幽部/阳部/之部…）＝1；无部名（UNATTRIBUTED）＝0
门槛：≥5 → CITATION_COMPLETE；3–4 → CITATION_PARTIAL；≤2 → UNVERIFIED_CITATION
另：claim_status=SCHOLAR_IDENTIFIED_RHYME 而 E7=0 → semantic_flag=STATUS_SEMANTIC_CONFLICT
"""
import csv, os

BASE = '<PROJECT_ROOT>/poetry-database'
os.chdir(BASE)
SRC = 'reports/tasks/2026-11-15/R2-11/ANCIENT_RHYME_40_SOURCE_REVIEW.csv'
OUT = 'reports/tasks/2026-11-16/R2-12/ANCIENT_RHYME_40_EVIDENCE_FINAL.csv'
rows = list(csv.DictReader(open(SRC, encoding='utf-8-sig')))

# case_id -> (E1..E7, publication, 说明)
S = {
 'SJ-01': ((1,1,0,1,1,1,1), '（缺：仅机构教材 PDF，无出版社/刊名与年期）',
           '机构署名（教育局课程发展处）＋文件名＋PDF 地址＋「韻腳說明段」＋逐字韻腳＋幽/職/之部，6/7。缺出版信息（非出版社、无年期），故 6/7 而非 7/7；且属「机构教材」一级，非学术考證。'),
 'SJ-03': ((0,1,0,0,0,1,1), '（缺）',
           '有讲议名与逐组韻腳＋部名（阳/微/鱼），但无作者、无出版信息、无页码；引文只出韻腳字组，未标所出篇（四组实皆《卷耳》，引文本身不注明），故 E5=0。3/7。另：末章「吁」不在引文。'),
 'SJ-04': ((0,1,0,0,0,1,1), '（缺）',
           '同 SJ-03 讲议：无作者、无出版、无页码、未标篇名；且引文作「采、友」而《芣苡》无「友」字（表列作「有」），引文本身有讹字，故之部依据实际是「采、有」。3/7。'),
 'SJ-06': ((0,1,0,0,0,1,1), '（缺）',
           '同讲议：6 韻腳字与表列完全对应、部名齐（侯/元/微/脂/職/之），但无作者、无出版、无页码、未标篇名。3/7。'),
 'SJ-07': ((0,1,0,0,0,1,1), '（缺）',
           '同讲议：有「瓜、琚、魚部；報、好、幽部」逐字与部名，但引文未标篇名、未引原句，按 E5 口径（须标篇/章或引原句）记 0；仍缺作者/出版/页码。3/7。'),
 'SJ-08': ((1,1,0,0,0,1,1), '刊名有（《語文教學通訊》A 版）、年期缺',
           '程翔具名＋篇名（论文题）＋之/元部逐字列出，4/7 → PARTIAL。引文虽明指「第二章和第六章」，却始终未出所论之篇名，且表列 34 位韻腳只具体列首章 5 位，余 29 位属作者自行推定；无年期页码，严格核验不可复现。'),
 'SJ-09': ((0,1,0,0,0,1,1), '（缺）',
           '同讲议：歌/宵/幽/真四部逐字列出，并明言「前四句交韻」，但未标篇名与章次，E5=0；无作者/出版/页码。3/7。「穗、醉、實、噎」四字不在引文，且「穗/醉」部属有争。'),
 'SJ-10': ((0,1,0,0,0,1,1), '（缺）',
           '同讲议：之部/月部逐字齐，但未标篇名、无作者/出版/页码。3/7。'),
 'SJ-11': ((0,1,0,0,1,1,1), '（缺：网站题解）',
           '中华诗词网题解：有篇名（蒹葭）、12 位韻腳全覆盖、阳/脂微/之三部齐，但无责任作者、非学术出版物、无页码。按 7 要素计 4/7 → PARTIAL；然「学者认定」之「学者」要件实质不成立（网站题解），若按 status 语义应另降，不能因 4/7 而视同「部分可核的学者结论」。'),
 'SJ-14': ((0,1,0,1,1,1,1), '（缺：仅 PDF 论文，无刊物年期）',
           '有论文名＋PDF＋「第三章段」定位＋《采薇》原文引用＋阳部判定，5/7 → COMPLETE。但作者栏为「未署名」，即无学者姓名；且无刊物年期。引文只覆盖 28 位中的 8 位（表已标「仅第三章可考」，未外推，处理正确）。'),
 'SJ-27': ((1,1,0,1,0,1,1), '（缺：影印本，无出版社/年份）',
           '刘师培具名＋书名卷四＋影印 PDF＋卷次定位＋逐组韻腳与部名（魚/侵/諄/之/祭/宵/脂/陽/耕），5/7 → COMPLETE。引文未标篇名（E5=0）；无出版社与年份；刘氏部名自成系统（祭部/諄部）不可与王力三十部互换。'),
 'SJ-28': ((1,1,0,1,0,1,1), '（缺：同 SJ-27）',
           '同 SJ-27，5/7 → COMPLETE；「至部」在王力系统并入质部，体系差异已在输入中标注。'),
 'SJ-30': ((0,1,0,1,1,1,1), '（缺：仅 PDF 论文，无刊物年期）',
           '有论文名＋PDF＋「首章段」定位＋《閟宮》原文引用＋阳部判定，5/7 → COMPLETE；作者未署名、无刊物年期；引文只覆盖 75 位中的 6 位（表已标「仅首章可考」）。'),
 'CC-01': ((1,1,1,1,1,1,0), '上海古籍出版社 2019 于淑娟点校本，ISBN 9787532591381',
           '蒋骥具名＋书名卷首篇条＋版本与 ISBN＋「離騷」条定位＋逐段韻腳，6/7 → COMPLETE。唯 E7=0：蒋骥只分韻段、不出部名；「庸/降」之王力东冬合韵系转引公开课件、无书页，不足为独立依据。故 SCHOLAR_IDENTIFIED_RHYME 与 韻部 UNATTRIBUTED 并存——学者认定的是韻段位置，不是韻部。'),
 'CC-02': ((1,1,1,1,1,1,0), '上海古籍出版社 2019 于淑娟点校本，ISBN 9787532591381',
           '同上，6/7 → COMPLETE。E7=0：全条无部名（输入 note 已明言「部名一律 UNATTRIBUTED」）。表列 201 位，引文首尾可核 20 位。'),
 'CC-04': ((1,1,1,1,1,1,0), '上海古籍出版社 2019 于淑娟点校本，ISBN 9787532591381',
           '同上，6/7 → COMPLETE。E7=0（无部名）。表列 160 位，引文可核 27 位（节引）。'),
 'CC-05': ((1,1,1,1,1,1,0), '上海古籍出版社 2019 于淑娟点校本，ISBN 9787532591381',
           '同上，6/7 → COMPLETE。E7=0（无部名）。表列 33 位，仅「鄣、忘」2 字不在引文，覆盖率最好。'),
 'CC-06': ((1,1,1,1,1,1,0), '上海古籍出版社 2019 于淑娟点校本，ISBN 9787532591381',
           '同上，6/7 → COMPLETE。E7=0（无部名）。表列 35 位，引文无省略号却缺 9 字（螭、壽、皋、皇、鵲、夷、御、位、傺），即这 9 位在蒋骥韻段中无对应，属作者自增。'),
 'CC-07': ((1,1,1,1,1,1,0), '上海古籍出版社 2019 于淑娟点校本，ISBN 9787532591381',
           '同上，6/7 → COMPLETE。E7=0（无部名）。表列 44 位缺 14 位，其中 12 位为「也」；蒋骥未以「也」为韻腳，表却大量取「也」入韻，与其「虚字不入韻」通例冲突，须逐位交代。'),
 'CC-08': ((1,1,1,1,1,1,0), '上海古籍出版社 2019 于淑娟点校本，ISBN 9787532591381',
           '同上，6/7 → COMPLETE。E7=0（无部名）。表列 43 位缺 20 位（含 6 个「也」）；「明」是否入韻，蒋骥与王力不一。'),
 'CC-09': ((1,1,1,1,1,1,0), '上海古籍出版社 2019 于淑娟点校本，ISBN 9787532591381',
           '同上，6/7 → COMPLETE。E7=0（无部名）。表列 38 位缺 14 位，蒋骥九段仅列 24 字；缺者属作者依句末补入，无学者依据。'),
 'CC-10': ((1,1,1,1,1,1,0), '上海古籍出版社 2019 于淑娟点校本，ISBN 9787532591381',
           '同上，6/7 → COMPLETE。E7=0（无部名）。表列 27 位缺 9 位，均为蒋骥明确不取者，表已声明「不代为解释」，处理诚实。'),
}

out = []
for r in rows:
    cid = r['case_id']
    if cid in S:
        e, pub, note = S[cid]
        n = sum(e)
        status = 'CITATION_COMPLETE' if n >= 5 else ('CITATION_PARTIAL' if n >= 3 else 'UNVERIFIED_CITATION')
        flag = 'STATUS_SEMANTIC_CONFLICT' if (r['claim_status'] == 'SCHOLAR_IDENTIFIED_RHYME' and e[6] == 0) else '—'
        note2 = note + f"　要素明细：{'学者' if e[0] else '（缺学者）'}、{'书名' if e[1] else '（缺书名）'}、{'出版' if e[2] else '（缺出版）'}、{'定位' if e[3] else '（缺页码/段）'}、{'诗句' if e[4] else '（未标篇/句）'}、{'韵脚字' if e[5] else '（缺韵脚）'}、{'韵部' if e[6] else '（韵部UNATTRIBUTED）'} = {n}/7。"
        if flag.startswith('STATUS'):
            note2 += '　★语义冲突：claim 称学者认定，而学者所认定者仅为韻段位置（何字与何字相叶），非古韻部归属；把「韻段」写成「韻部」是层级错置。'
    else:
        e, pub, note, status, flag = (0,)*7, '（缺）', '', 'NOT_APPLICABLE', '—'
        if cid == 'CC-03':
            pub = '上海古籍出版社 2019 于淑娟点校本（仅 note 提及，未进 attribution_source）'
            note = ('claim_status=LINE_END_CANDIDATE，未宣称「学者认定韻位」，故不适用 7 要素门槛，记 NOT_APPLICABLE。'
                    '若强行计分：仅有学者姓名与书名，2/7，与输入 UNVERIFIED_CITATION 一致。'
                    '「蒋骥《说韻》不收《九辩》」一语有书名而无版本页码，不足以排除他本韻谱。')
        else:
            note = ('claim_status=%s，输入档 source_text=NOT_FOUND，未宣称任何学者依据，不适用引用要素审查，记 NOT_APPLICABLE。'
                    '此不构成虚假引用，但也不构成任何可核证据：该例的韻位仅为由句式推定的候选。' % r['claim_status'])
    out.append(dict(case_id=cid, source_text=r['source_text'], rhyme_position=r['rhyme_position'],
                    claim_status=r['claim_status'], scholar=r['scholar'], work_title=r['work_title'],
                    publication=pub, locator=r['locator'], citation_elements_count=sum(e),
                    final_citation_status=status, semantic_flag=flag,
                    note=(note2 if cid in S else note)))

FIELDS = ['case_id','source_text','rhyme_position','claim_status','scholar','work_title','publication','locator',
          'citation_elements_count','final_citation_status','semantic_flag','note']
with open(OUT, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    for r in out: w.writerow(r)

import collections
sch = [r for r in out if r['claim_status'] == 'SCHOLAR_IDENTIFIED_RHYME']
print('total', len(out), 'scholar', len(sch))
print('status', collections.Counter(r['final_citation_status'] for r in sch))
print('flags', collections.Counter(r['semantic_flag'] for r in sch))
print('elements dist', collections.Counter(r['citation_elements_count'] for r in sch))
print('changes vs input:', [(r['case_id'], r['final_citation_status']) for r in sch])
