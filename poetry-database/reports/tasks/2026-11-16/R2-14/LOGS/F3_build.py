#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F3：30 首精读卡 60 条遗留问题的闭环表 + 终审表。本轮不改卡片，只给动作与证据。"""
import csv, re, sqlite3, collections, json

D = 'reports/tasks/2026-11-16/R2-14'
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
cj = lambda s: ''.join(CJK.findall(s or ''))
con = sqlite3.connect('file:database/poetry.db?mode=ro', uri=True)

cards = {r['card_id']: r for r in csv.DictReader(
    open('reports/tasks/2026-11-15/R2-10/THIRTY_CLOSE_READINGS.csv', encoding='utf-8-sig'))}
fin13 = {r['card_id']: r for r in csv.DictReader(
    open('reports/tasks/2026-11-16/R2-13/THIRTY_CLOSE_READINGS_FINAL_R2_13.csv', encoding='utf-8-sig'))}
rev5 = list(csv.DictReader(open('reports/tasks/2026-11-16/R2-13/THIRTY_CLOSE_READINGS_5_REVISION.csv', encoding='utf-8-sig')))
r11 = list(csv.DictReader(open('reports/tasks/2026-11-15/R2-11/THIRTY_CLOSE_READINGS_INDEPENDENT_AUDIT.csv', encoding='utf-8-sig')))
r12 = list(csv.DictReader(open('reports/tasks/2026-11-16/R2-12/THIRTY_CLOSE_READINGS_FINAL_AUDIT.csv', encoding='utf-8-sig')))

DIM11 = {'原文': '原文完整性', '背景': '创作背景', '章法': '章法', '意象': '意象', '炼字': '炼字',
         '用典': '用典', '韵律': '韵脚与声调', '评价': '艺术特点'}

NOVER = '库内 books 仅 13 种（诗词格律／汉语诗律学／唐宋词格律／钦定词谱／词律／切韵／广韵／集韵／词林正韵／中原音韵／文心雕龙／原诗／唐宋诗举要），无集部别集、无年谱、无方志、无史部；works 表 record_locator／juan／base_edition 三列全库皆空（SELECT COUNT(*) FROM works WHERE juan<>\'\' → 0）。'
def nov(what):
    return f'{NOVER}所缺「{what}」不可核，只能标存疑或删。'

# ---- 60 条：(card, dim) -> (verdict, desc, action, evidence, final_status) ----
R = {}
def add(card, dim, verdict, desc, action, ev, final):
    R[(card, dim)] = dict(verdict=verdict, desc=desc, action=action, ev=ev, final=final)

# ---- 5 首 NOT_REVISED：直接取自 R2-13 5_REVISION ----
for r in rev5:
    m = re.match(r'(.+?)／(\w+)：(.+)$', r['prior_issue'], re.S)
    dim = m.group(1) if m else ''
    verdict = m.group(2) if m else 'ISSUE'
    desc = (m.group(3) if m else r['prior_issue']).strip()
    R[(r['card_id'], dim)] = dict(verdict=verdict, desc=desc,
                                 action=r['required_fix'], ev=r['evidence'],
                                 final='UNVERIFIABLE_NO_SOURCE' if verdict == 'UNVERIFIABLE' else 'FIX_SPECIFIED')

# ---- C02 ----
add('C02', '创作背景', 'UNVERIFIABLE',
    '所缺：①《国秀集》卷次与「朱斌」条原文；②宋江邻几（江休复《嘉祐杂志》？）得诗于蒲州之说所出书。二者均非库内可核，亦非卡片可自证。',
    'title_notes 改为「作者有异说：《国秀集》录此诗作朱斌（库内无《国秀集》，据通行说法，待核）；宋江邻几得诗于蒲州之说，出处待考，本文不取证」。',
    nov('《国秀集》《嘉祐杂志》'), 'UNVERIFIABLE_NO_SOURCE')
add('C02', '章法', 'ISSUE',
    '「一横一纵」的对应失据：白日依山是日向西沉，黄河入海是水向东流，二者同为东西向（横）；若以高下言，「依山」为下落、「入海」为下趋，又同为纵向。故横纵之名与所举二景不合。',
    '改为「一西一东、一落一奔」：白日依山是日向西沉，黄河入海是水向东流，方同为横向而方向相反。',
    'text_raw：1 句「白日依山盡」（日向西沉）、2 句「黃河入海流」（水向东流）。两句方向同为东西轴，卡片以「横／纵」分属，与其自述「依山为落、入海为奔」不合；方向可核，横纵之判只可依方向。',
    'FIX_SPECIFIED')
# ---- C03 ----
add('C03', '创作背景', 'UNVERIFIABLE', '所缺：《辋川集》原序与二十首目次、裴迪同咏之作。库内无集部原书。',
    '删「《辋川集》二十首之一」的目次性描述，或改为「王维辋川组诗之一（组诗目次库内无书可核）」。',
    nov('《辋川集》'), 'UNVERIFIABLE_NO_SOURCE')
# ---- C04 ----
add('C04', '创作背景', 'UNVERIFIABLE',
    '系年（约元和二年前后）、贬所、与《渔翁》同期、宋元绘画接受史，四项库内均无对应字段。',
    '该行降为「写作缘起待考」：删系年与「与《渔翁》同期」之断言，绘画接受史一笔删去或标「据通行画史，待核」。',
    nov('柳宗元年谱、永州地志、画史'), 'UNVERIFIABLE_NO_SOURCE')
# ---- C05 ----
add('C05', '创作背景', 'UNVERIFIABLE', '所缺：李白年谱或《李太白全集》系年、遇赦诏书本事。库内无集部原书。',
    '改为「旧说系于乾元二年（759）遇赦东归时，库内无年谱可核，本文不取证」。',
    nov('李白年谱、《李太白全集》'), 'UNVERIFIABLE_NO_SOURCE')
# ---- C06 ----
add('C06', '创作背景', 'UNVERIFIABLE', '所缺：《樊川文集》《樊川外集》原目与卷次。库内仅存诗文本体，无集目。',
    '删集目卷次，或注「《樊川文集》外集所收（库内无集目，待核）」。',
    nov('《樊川文集》《樊川外集》'), 'UNVERIFIABLE_NO_SOURCE')
add('C06', '语言风格', 'ISSUE',
    '「宋诗『以议论入诗』的先声已在此」无据：以议论入诗杜甫已盛（如《蜀相》颈联），非待杜牧；且「先声」为文学史时序断言，卡片未举一字接受史材料。',
    '删「先声」，改为「与宋诗以议论入诗同一路径（不作先后之判）」。',
    '库内可核之反例：C14《蜀相》「三顧頻煩天下計，兩朝開濟老臣心」即议论入诗，早于杜牧；「先声」属时序判断，库内无诗话、无接受史材料可证。',
    'FIX_SPECIFIED')
# ---- C08 ----
add('C08', '创作背景', 'UNVERIFIABLE', '曲调归属、卷次、二首之次、明人压卷说四项库内无据，均不可核。',
    '删卷次与「明人推为压卷」之具体出处，只留「乐府旧题《出塞》」。',
    nov('《乐府诗集》卷次、明人诗话'), 'UNVERIFIABLE_NO_SOURCE')
add('C08', '意象', 'ISSUE', '「物在人在」与「人未还」互斥，术语与文意相反。',
    '改为「物在（月、关）而人不在（人未还），构成『物是人非』的对照」。',
    'text_raw 第 2 句「萬里長征人未還」明言人未还；卡片同段既云「人却是流动的、不归的」，又结以「物在人在」，自相抵牾。',
    'FIX_SPECIFIED')
add('C08', '艺术特点', 'ISSUE', '②「前三句皆虚（月、关、未还）」与①「明月、关皆实景」自相矛盾，评价链断裂。',
    '②改为「前三句就实景实情铺陈（月、关、人未还），第四句转以虚拟语气收」，删「皆虚」。',
    'text_raw：月、关为实景（1 句），人未还为实情（2 句）；①既判「皆实景」，②又判「皆虚」，同一段内两判相反。',
    'FIX_SPECIFIED')
# ---- C09 ----
add('C09', '创作背景', 'UNVERIFIABLE', '系年与同期作品库内无据，无法核。',
    '补「至德二载（757）春长安」所据（年谱／仇注卷次），或改「作年旧说系于至德二载，库内无据」。',
    nov('杜甫年谱、仇兆鳌注'), 'UNVERIFIABLE_NO_SOURCE')
# ---- C10 ----
add('C10', '创作背景', 'UNVERIFIABLE', '所缺：王维年谱、辋川集作品编年。库内无集部原书。',
    '删系年与编年性描述，或标「辋川期作（编年库内无据）」。',
    nov('王维年谱'), 'UNVERIFIABLE_NO_SOURCE')
# ---- C11 ----
add('C11', '韵脚与声调', 'ISSUE',
    '「首句入韵（城）」不成立：首句为「青山橫北郭」，末字「郭」入声铎韵（卡片 prosody 栏自标「平平平仄仄」，即以郭为仄），并不叶韵；「城」是第二句韵脚。',
    '改为「首句不入韵（郭，入声铎韵，仄收）；二、四、六、八句叶下平八庚」。',
    'text_raw 1 句末字＝郭（入声），2 句末字＝城；卡片 prosody 栏自标「青山横北郭（平平平仄仄）」，以郭为仄，与其 rhyme 栏「首句入韵（城）」自相抵牾；「城」在第 2 句，非首句。',
    'FIX_SPECIFIED')
# ---- C13 ----
add('C13', '创作背景', 'UNVERIFIABLE', '系年与《诗薮》评语库内无据。',
    '补系年所据与《诗薮》卷次，或删「古今七律第一」的出处归属，只作「明人推为七律第一（出处待核）」。',
    nov('《诗薮》、杜甫年谱'), 'UNVERIFIABLE_NO_SOURCE')
add('C13', '艺术特点', 'ISSUE', '所举「千」「三」二数字不在本篇，属误举（字频核为 0）。',
    '改为「数字（万、百）的运用使抽象身世可量」，「无边／不尽」的夸张语另举为证。',
    'text_raw 全篇 56 字，逐字检索「千」「三」字频＝0（万 1、百 1）；卡片③「数字（万、百、千、三）」二例不在本篇。',
    'FIX_SPECIFIED')
# ---- C14 ----
add('C14', '原文完整性', 'ISSUE',
    '字数控不成立：库 char_count=58，正文 56，含校记 62；58 既不等于 56 也不等于 62，无法由任何口径推出。卡片 note 称「差额 2 系校记」，而校记实 6 字，若全计应为 62。另校记嵌在颈联与尾联之间，割裂八句。',
    'note 改为「text_raw 62 字（含校记『（頻煩 一作：頻繁）』6 字）／去括注正文 56 字／库 char_count=58 与二者皆不合，属库字段缺陷」；校记移入 note，正文只留八句。',
    '复算：cj(text_raw)=62，去括注 cj=56，char_count=58；58−56=2，而校记 6 字，58 无法由「正文＋校记」推出。校记位于库文第 3 行末（颈联与尾联之间）。',
    'FIX_SPECIFIED')
add('C14', '创作背景', 'UNVERIFIABLE', '所缺：杜甫年谱（如闻一多《少陵先生年谱会笺》）或仇兆鳌注系年。库内无集部原书。',
    '改为「作年旧说系于上元元年（760）春，库内无年谱可核，本文不取证」。',
    nov('杜甫年谱、仇注'), 'UNVERIFIABLE_NO_SOURCE')
# ---- C15 ----
add('C15', '艺术特点', 'ISSUE',
    '②「开『朦胧』一路，李商隐之后千余年无人能学」为绝对化的影响论，无文献支撑，且西昆体、清代虞山诗派皆学李商隐，与文学史事实相左。',
    '改为「为后世朦胧一路所自出；西昆、虞山皆有取焉」，「无人能学」之语删。',
    '「无人能学」为不可证的全称否定；库内可核之反例：西昆体（宋初）与虞山诗派（清）皆宗李商隐，属通行文学史事实，「千余年无人能学」与接受史相左。',
    'FIX_SPECIFIED')
# ---- C17 ----
add('C17', '创作背景', 'UNVERIFIABLE', '组诗小序库内无文本，引文无从比对；其余为解诗之论。',
    '小序改述为「组诗小序大意（库内无小序文本，据通行本，待核）」，不作逐字引文。',
    nov('《饮酒》二十首小序（逯钦立校本一类）'), 'UNVERIFIABLE_NO_SOURCE')
# ---- C18 ----
add('C18', '创作背景', 'UNVERIFIABLE', '台址、筑台本事、系年（万岁通天元年）库内无据。',
    '改「台址与筑台本事旧说如此，系年（万岁通天元年）出自后人编年，库内无据，本文不取证」。',
    nov('《陈子昂集》校注、两唐书、幽州地志'), 'UNVERIFIABLE_NO_SOURCE')
# ---- C19 ----
add('C19', '创作背景', 'UNVERIFIABLE', '系年、饮宴地点、曲调归属库内无据（呼名之语可内证）。',
    '补系年所据（詹锳《李白诗文系年》一类），或标「系年待考」；饮宴地点不指定。',
    nov('李白年谱'), 'UNVERIFIABLE_NO_SOURCE')
add('C19', '韵脚与声调', 'ISSUE', '「十言」无对应句，属句式归纳失实。',
    '改为「三言、五言、七言交错，另有『君不见』三字领＋七言的长句」，删「十言」；三处校记括注移出正文。',
    '复算句长集合＝[3,5,7]，最长 7 字：库文「君不見，黃河之水天上來」有逗断开，若以「君不见」为三字领，则其后为七言，全篇无 10 字之句。',
    'FIX_SPECIFIED')
# ---- C20 ----
add('C20', '原文完整性', 'ISSUE',
    '字数控不成立：库 char_count=290，正文 285，含校记 294；290 与 285 差 5、与 294 差 4，均无法由校记 9 字解释。两条校记嵌在诗句之间，割裂句读。',
    'note 改为「text_raw 294 字（含校记『（四萬 一作：一萬）』『（度 通：渡）』共 9 字）／去括注正文 285／库 char_count=290 与二者皆不合，属库字段缺陷」；校记移入 note。',
    '复算：cj(text_raw)=294，去括注=285，char_count=290；294−285=9＝两条校记字数，而 290 不落在 285 与 294 之间的任何可解释位置。',
    'FIX_SPECIFIED')
add('C20', '创作背景', 'UNVERIFIABLE', '所缺：李白年谱（詹锳《李白诗文系年》等）。库内无集部原书。',
    '改为「旧说系于天宝四载（745）将离东鲁时，库内无年谱可核，本文不取证」。', nov('李白年谱'), 'UNVERIFIABLE_NO_SOURCE')
add('C20', '韵脚与声调', 'ISSUE',
    '三处失实：①「越／月」标作「入声月／屑」——越＝入声六月（兼七曷）、月＝入声六月，并无「屑」；②「然」不是韵脚（「訇然中開」句尾为「開」，上平十灰）；③遗漏「摧／開／臺」一整个上平十灰韵段。另卡片自称「个别处标 UNKNOWN」，全表并无 UNKNOWN。',
    '①越、月皆入声六月，删「屑」；②删「然」为韵脚；③补「摧／開／臺」（上平十灰）一韵段；删「个别处标 UNKNOWN」自述。',
    'text_raw 逐字核对：越（越人語天姥／夢吳越）、月（鏡湖月／湖月照我影）皆入声六月；「訇然中開」之「然」居句中，句尾为「開」，与「丘巒崩摧」「金銀臺」同属上平十灰；卡片韵表无 UNKNOWN 字样。',
    'FIX_SPECIFIED')
# ---- C21 ----
add('C21', '创作背景', 'ISSUE',
    'dynasty 与库冲突且未举可核依据：「十四首」之数库内不可核。',
    '朝代不改卡片、也不改库：注「温庭筠（约 812—约 870）当系晚唐；库 dynasty=五代系由 huajianji 集合推定，非作者断代」。数字「十四首」删或标「今存《菩萨蛮》十四首（据通行本，待核）」。',
    'SELECT dynasty,collection FROM works WHERE work_id=\'huajianji:ef15b41ce616\' → 五代／huajianji；库 dynasty 由集合归并而来（《花间集》为五代选本），不能反推作者朝代；温庭筠卒年早于五代。故记 CONFLICT_DB_INFERRED，不作卡片纠错。',
    'FIX_SPECIFIED')
# ---- C22 ----
add('C22', '创作背景', 'UNVERIFIABLE', '降宋本事与赐药传说库内无据。',
    '改为「相传为南渡降宋后所作，赐牵机药之说见宋人笔记，库内无书可核，本文不取证」。',
    nov('《默记》《南唐书》一类'), 'UNVERIFIABLE_NO_SOURCE')
add('C22', '意象', 'ISSUE', '「暖」无文本依据，且与同段「冷白为主」互斥。',
    '删「暖」，改为「『一江春水』是全篇唯一具方向与动能的意象」。',
    'text_raw 56 字内「暖」字频＝0；若以「暖流」为比喻亦无色语支撑，且与同段「冷白为主」并置读者易生歧解，宜就「方向＋动能」立说。',
    'FIX_SPECIFIED')
add('C22', '艺术特点', 'ISSUE', '「皆由此出」的影响论无据，且所举二例与「以水喻愁」不同型。',
    '改为「为后世以水喻愁提供范式」，删「皆由此出」。',
    '「愁如海」（秦观「飞红万点愁如海」为「愁如海」型，以海喻愁）与「愁似雨」不同型；库内无接受史材料可证「皆由此出」，属不可证的全称判断。',
    'FIX_SPECIFIED')
# ---- C24 ----
add('C24', '创作背景', 'UNVERIFIABLE', '所缺：《明皇杂录》原文与卷次。库内无子部杂家书。',
    '改为「调名本事见《明皇杂录》（库内无此书，据通行说法，待核）」。', nov('《明皇杂录》'), 'UNVERIFIABLE_NO_SOURCE')
add('C24', '韵脚与声调', 'ISSUE',
    '字数与句数与库谱不合且未标所据：库内词谱作 103 字、23 句，实际文本 102 字；卡片作「一百二字、上九下八」共 17 句（《钦定词谱》口径），未注明所据。',
    '补注「此本实 102 字；龙榆生《唐宋词格律》作 103 字、23 句；《钦定词谱》作 17 句（三字领独立成句之分句口径不同）」，并标明所据。',
    'cipai_forms_r2_07（雨霖铃 form_seq=1）：total_characters=103、sentence_count=23、sentence_lengths 含 4,4,4,6,4,4,6,5,3,4,7,7,3,5,6,3,4,4,2,6,3,4,5；库文 cj=102。库内确有《唐宋词格律》《钦定词谱》二书，故应标所据而非并置不注。',
    'FIX_SPECIFIED')
# ---- C25 ----
add('C25', '创作背景', 'UNVERIFIABLE', '小序不在库内文本，无从比对；系年无据。',
    '注「小序据通行本（《东坡乐府》一卷本系统），库内 text_raw 无小序，不逐字比对；系年（熙宁九年）库内无据」。',
    nov('《东坡乐府》'), 'UNVERIFIABLE_NO_SOURCE')
add('C25', '韵脚与声调', 'ISSUE', '「两个五字句」实为两个六字句（库谱句长 6,6）。',
    '改「上片『我欲乘风归去，又恐琼楼玉宇』为两个六字句对，与下片『人有悲欢离合，月有阴晴圆缺』同为六言对起」。',
    'text_raw：我欲乘风归去＝6 字，又恐琼楼玉宇＝6 字；cipai_forms_r2_07（水调歌头）：sentence_lengths=5,5,6,5,6,6,5,5,5,…，第 5、6 句即 6,6。卡片 prosody 栏称「两个五字句」，与文本与库谱皆不合。',
    'FIX_SPECIFIED')
# ---- C26 ----
add('C26', '创作背景', 'UNVERIFIABLE', '所缺：贺铸行实（《宋史》本传、墓志）与横塘地志。库内无史部书。',
    '删行实与地志的具体断言，或注「贺铸晚岁退居苏州，横塘在苏州（库内无史部、方志可核）」。',
    nov('《宋史》本传、苏州方志'), 'UNVERIFIABLE_NO_SOURCE')
add('C26', '韵脚与声调', 'ISSUE', '韵脚漏列二字：「户」（去声七遇，第 4 部）、「絮」（去声六御，第 4 部）均为句尾韵位。',
    '补「户」「絮」，韵脚十：路、去、度、户、处、暮、句、许、絮、雨。',
    'text_raw 有「瑣窗朱戶」「滿城風絮」二句尾；cipai_forms_r2_07（青玉案）rhyme_positions=1,3,4,6,7,8,9,10,12,13、rhyme_count=10，正合十韵。卡片只列 8 字，漏第 4、9 位。',
    'FIX_SPECIFIED')
# ---- C27 ----
add('C27', '创作背景', 'UNVERIFIABLE', '所缺：①《四库提要辨证》《词学季刊》所载余、夏二文；②邓广铭、王曾瑜论著。库内无近人论著。',
    '改为「真伪之争，余嘉锡、夏承焘二家之说及邓广铭、王曾瑜诸家论著（库内无近人论著可核），本文只据文本立论」。',
    nov('余嘉锡、夏承焘、邓广铭、王曾瑜论著'), 'UNVERIFIABLE_NO_SOURCE')
# ---- C28 ----
add('C28', '题目', 'ISSUE',
    'title_notes 存留未清理的疑问句与错误引证：「后以陆游此词首句『可怜孤似钗头凤』? 实以调中『钗头凤』句改名」——半角「?」孤悬，属未定稿痕迹；且本词首句为「红酥手」，非「可怜孤似钗头凤」（此句出无名氏《撷芳词》），张冠李戴。',
    '删「首句『可怜孤似钗头凤』?」一语，改为「调本名《撷芳词》；通行说法以无名氏《撷芳词》『可怜孤似钗头凤』句改称《钗头凤》，此句非陆游词句（改称之说待核）」。',
    'text_raw 首句＝「紅酥手」；「可怜孤似钗头凤」全篇字频＝0（逐字检索无此句）；卡片 title_notes 原文含半角「?」，同句先问后答，属未定稿残留。',
    'FIX_SPECIFIED')
add('C28', '创作背景', 'UNVERIFIABLE', '所缺：《齐东野语》卷一原文；《剑南诗稿》沈园诸诗编年。库内无集部、子部书。',
    '改为「本事见周密《齐东野语》（库内无此书，据通行说法），沈园诸诗编年库内无据，本文只据文本立论」。',
    nov('《齐东野语》《剑南诗稿》'), 'UNVERIFIABLE_NO_SOURCE')
add('C28', '意象', 'ISSUE',
    '「暖色写昔，冷绿写今，色彩即时间」不成立：下片「泪痕红浥鲛绡透」之「红」为今日之泪、「桃花落」之桃亦在今日，皆暖色而属今。',
    '改为「暖色两见于昔（手、酒）亦两见于今（泪、桃花）；冷绿（宫墙柳）独系于不变之春——色彩之用不在分今昔，而在以不变衬人变」。',
    'text_raw：上片「紅酥手」「黃縢酒」（昔）＋「滿城春色宮牆柳」（绿）；下片「淚痕紅浥」「桃花落」（今，红）；同一「红」跨昔／今，故暖／冷不能与昔／今一一对应。',
    'FIX_SPECIFIED')
add('C28', '用典', 'ISSUE',
    '「皆语典，非事典」之判自相抵牾：卡片上文既云「锦书用苏蕙织锦回文事」，苏蕙织锦回文正是事典；鲛人泣珠亦属传说之事。',
    '改为「鲛绡、锦书为事典，山盟为语典」。',
    '卡片 allusion 栏同段先出「锦书用苏蕙织锦回文事」「鲛绡用鲛人泣珠事」，二事皆有事相，与结论「皆语典，非事典」相悖；文本可核者为「錦書難托」「淚痕紅浥鮫綃透」。',
    'FIX_SPECIFIED')
add('C28', '韵脚与声调', 'ISSUE',
    '句式归纳失实：「上下片各以三个三字句起（红酥手／黄縢酒／满城春色宫墙柳）」——「满城春色宫墙柳」为七字句。',
    '改为「上下片皆以三、三、七起（红酥手／黄縢酒／满城春色宫墙柳；春如旧／人空瘦／泪痕红浥鲛绡透）」。',
    '复算句长集合＝[3,4,7]：满城春色宫墙柳＝7 字（逐字计数），泪痕红浥鲛绡透＝7 字；卡片称三句皆三字，与文本不合。',
    'FIX_SPECIFIED')
# ---- C29 ----
add('C29', '创作背景', 'UNVERIFIABLE', '所缺：《尊前集》原书与卷次；《宋史》《十国春秋》欧阳炯传。库内无集部、史部书。',
    '删卷次与传记细节；朝代不改卡片、也不改库：注「欧阳炯（896—971）仕后蜀入宋，当系五代；库 dynasty=唐系由 tang 集合归并，非作者断代」。',
    nov('《尊前集》《宋史》《十国春秋》') + ' 另：SELECT dynasty,collection FROM works WHERE work_id=\'tang:0578b1afec4f\' → 唐／tang，与卡片「五代」冲突，记 CONFLICT_DB_INFERRED，库值不得反推作者断代。',
    'UNVERIFIABLE_NO_SOURCE')
add('C29', '语言风格', 'ISSUE',
    '「是早期文人词『清空』一路的先声」无据：「清空」为张炎《词源》评姜夔的术语，移用于五代小令须说明涵义转换；「先声」为时序断言，未举接受史材料。',
    '删「先声」，改为「与后世清空一路同其取境（术语借用，非时序之判）」。',
    '「先声」为文学史时序判断；库内无《词源》、无词话、无接受史材料；「清空」原指姜夔词境，移评五代小令属术语挪用，须说明转换。',
    'FIX_SPECIFIED')
add('C29', '韵脚与声调', 'ISSUE',
    '两处失实：①漏列韵脚「多」（下平五歌，与河、波、歌同部）；②韵位描述错误（称第 3、7 句用平韵、第 1、4、5、8 句用仄韵，而库谱 rhyme_positions=2,3,4,6,7,8、rhyme_count=6，第 1、5 句不押韵）。',
    '补「多」为第三平韵；韵位改「第 2、3、4、6、7、8 句押韵（河、多、苇、波、歌、起），第 1、5 句不押」。',
    'text_raw「淺沙汀上白雲多」句尾＝多；cipai_forms_r2_07（西江月 form_seq=1）sentence_lengths=6,6,7,6,6,6,7,6、rhyme_positions=2,3,4,6,7,8、rhyme_count=6；本词韵脚 河(2)、多(3)、苇(4)、波(6)、歌(7)、起(8) 与库谱六韵全合。',
    'FIX_SPECIFIED')
# ---- C30 ----
add('C30', '艺术特点', 'ISSUE',
    '②「句法为『本体＋喻词＋喻体』的倒装……与常序相反」为术语误用：「自在飞花轻似梦」「无边丝雨细如愁」正是常序（飞花—似—梦），句法层面并无倒装。',
    '改为「句法为常序，而喻体取虚——以抽象（梦、愁）喻具体（花、雨），是以虚喻实的颠倒」。',
    'text_raw「自在飛花輕似夢，無邊絲雨細如愁」：本体（飞花／丝雨）＋喻词（似／如）＋喻体（梦／愁），正是常序；倒者只在喻体之虚实，不在句法。',
    'FIX_SPECIFIED')

assert len(R) == 60, len(R)

# ---- 输出闭表 ----
rows = []
for cid in [f'C{i:02d}' for i in range(1, 31)]:
    dims = [d for (c, d) in R if c == cid]
    order = ['原文完整性', '题目', '作者与时代', '创作背景', '章法', '意象', '炼字', '用典', '韵脚与声调', '语言风格', '艺术特点']
    dims.sort(key=lambda d: order.index(d) if d in order else 99)
    for i, d in enumerate(dims, 1):
        v = R[(cid, d)]
        c = cards[cid]
        rows.append(dict(card_id=cid, work_id=c['work_id'], title=c['title'], author=c['author'],
                         issue_id=f'{cid}-I{i:02d}', dimension=d, issue_desc=v['desc'],
                         current_status=v['verdict'], fix_action=v['action'],
                         fixed_in_card='NO', evidence=v['ev'], final_status=v['final']))
assert len(rows) == 60

# 与 R2-13 报的每卡条数对表
cnt = collections.Counter(r['card_id'] for r in rows)
bad = [(c, cnt[c], fin13[c]['n_issues_open']) for c in cnt if str(cnt[c]) != fin13[c]['n_issues_open']]
print('per-card mismatch vs R2-13:', bad)

with open(f'{D}/CLOSE_READINGS_30_ISSUE_CLOSURE.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['card_id', 'work_id', 'title', 'author', 'issue_id', 'dimension',
                                      'issue_desc', 'current_status', 'fix_action', 'fixed_in_card',
                                      'evidence', 'final_status'])
    w.writeheader()
    w.writerows(rows)
print('closure rows', len(rows), collections.Counter(r['final_status'] for r in rows))
json.dump(rows, open(f'{D}/LOGS/f3_closure.json', 'w'), ensure_ascii=False, indent=1)
