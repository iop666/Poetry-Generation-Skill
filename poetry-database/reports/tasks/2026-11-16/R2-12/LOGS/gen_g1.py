#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G1 runner: 执行 part1（15 首 165 行），追加上一轮 5 首的修订核验行，写出 CSV。"""
import os, csv
BASE = '<PROJECT_ROOT>/poetry-database'
os.chdir(BASE)
exec(open('reports/tasks/2026-11-16/R2-12/LOGS/gen_g1_part1.py', encoding='utf-8').read())

# ============ 上一轮已审 5 首：修订核验（逐句核对现文件，md5 未变）============
# 文件 reports/tasks/2026-11-15/R2-10/THIRTY_CLOSE_READINGS.csv mtime 2026-11-15 21:28:01，
# md5=7e59f96f94f4718fbe542d5e0b97c156；R2-11 审核 23:14:56 之后无新版本文件。
REV = 'NOT_REVISED'
add('C01','意象','ISSUE',
    "现文件 imagery 栏仍作：「全篇色调极冷，唯『故乡』是潜在的暖色，而它始终不出场，只以『思』字指涉。」（逐字核对，与 R2-11 所审文本同）",
    "旧问题未改：「故乡始终不出场」与原文「低頭思故鄉」直接矛盾——故乡以「思」的宾语出场；且同段既把故乡列为核心意象，又言其不出场，自相抵牾。应改「故乡之景始终不出场，仅以『思故乡』三字点出」。",
    prior='ISSUE', rev=REV)
add('C01','韵脚与声调','ISSUE',
    "现文件 prosody 栏仍作：「『床前明月光』为平平平仄平，第三字当平面用仄（月）」；rhyme 栏「韵脚：光、霜、乡。同属下平七阳」与库内平水韵表合（光/霜/乡均下平聲七陽）。",
    "旧问题未改：第三字为「明」（平声），非「月」；「月」是第四字（入声作仄）。原句「第三字当平面用仄（月）」把字位与字都指错，且「当平面用仄」的方向与事实相反（第三字实为平声，是当仄而用平）。应改为「第三字『明』当仄而用平，第四字『月』入声作仄合律」。",
    prior='ISSUE', rev=REV)
add('C07','原文完整性','ISSUE',
    "现文件 note 栏仍作：「库作『远近高低总不同』，通行本多作『各不同』，属异文……字数 28，与库一致。」全篇无「無一同」三字（逐字检索确认）。",
    "旧问题未改：对勘表（R2-10 no.6，同一 work_id songshi:afc90d0ab2ec）已确认源2（東坡全集四庫本卷13）作「逺近髙低無一同」，是两字异文（總不／無一），卡片只记「各不同」且称「通行本」，未记已核之四库本读法。应补「源2作『無一同』，异文 2 字」。",
    prior='ISSUE', rev=REV)
add('C07','创作背景','UNVERIFIABLE',
    "现文件无任何系年或年谱出处语；《题西林壁》条下亦无西林寺沿革。",
    "旧问题未改：元丰七年（1084）系年、西林寺沿革仍无据可核（库内 works 无系年字段，无释氏书、无年谱）。缺：苏轼年谱与《庐山记》一类地志。",
    prior='UNVERIFIABLE', rev=REV)
add('C12','原文完整性','ISSUE',
    "现文件 note 栏仍全句为：「字数 40，与库一致。」（逐字核对）",
    "旧问题未改：对勘表 no.4 已确认三处异文（曲徑/竹逕、俱/都、唯聞/但餘，合 4 字）及四库本字形（髙/處/恱等），note 一字未记，仅报字数。应补三处异文与取库文之由。",
    prior='ISSUE', rev=REV)
add('C12','创作背景','UNVERIFIABLE',
    "现文件无寺址、建寺因缘的出处语；库内 works 无相关字段。",
    "旧问题未改：破山寺（兴福寺）寺址沿革、建寺因缘无据。缺：常熟方志或寺志。",
    prior='UNVERIFIABLE', rev=REV)
add('C12','艺术特点','ISSUE',
    "现文件 artistry ③ 仍作：「……是王维一路『以动词通禅』的先声。」（逐字核对）",
    "旧问题未改：「先声」为时序断言，而常建生卒与王维年辈先后无据，且「以动词通禅」之评本为后人对王维的追认，以常建为其先声属循环论证。应删「先声」，改为「与王维山水诗『以动词通禅』同一路径」。",
    prior='ISSUE', rev=REV)
add('C16','原文完整性','ISSUE',
    "现文件 note 栏仍全句为：「字数 56，与库一致。」（逐字核对）",
    "旧问题未改：库 verify_status=TEXT_CONFLICT，对勘表 no.5 另录 王/西、濬/晉（西晉/王濬）与 江/寒 等异文及两条别作，note 一字未披露。应补两处异文及取库文之由。",
    prior='ISSUE', rev=REV)
add('C16','创作背景','UNVERIFIABLE',
    "现文件无西塞山山址、长庆四年（824）途经之系年出处。",
    "旧问题未改：山址（湖北大冶？浙江吴兴？两说）与系年无据。缺：刘禹锡年谱、《元和郡县图志》一类地志。",
    prior='UNVERIFIABLE', rev=REV)
add('C16','艺术特点','ISSUE',
    "现文件 artistry ① 仍作「前四句纯用史笔，不加评断」，② 仍作「『千寻』是虚数，『一片』是实数，虚实相形」；affect 栏又言「最后连悲也不剩」。",
    "旧问题未改：①诗有「金陵王气黯然收」，「黯然」即评断语，与「不加评断」相悖；②「一片」是数量而非「实数」，与「千寻」之夸张对举，二者皆非可计量之实，定性为「实数」无据。",
    prior='ISSUE', rev=REV)
add('C23','原文完整性','ISSUE',
    "现文件 note 栏仍全句为：「库文作『如今有谁忺摘』，『忺』为异文（通行本多作『堪』）……字数 97，与库一致。」（逐字核对）",
    "旧问题未改：对勘表 no.9 已确认「晚／曉」（SIGNIFICANT，改变全词时间设定）与「忺／堪」两处，note 只记其一。应补「晚／曉」并说明取「晚」之由。",
    prior='ISSUE', rev=REV)
add('C23','创作背景','UNVERIFIABLE',
    "现文件无选本题名与系年出处。",
    "旧问题未改：《花庵词选》题名、系年（南渡后）无据。缺：《花庵词选》卷次与《李清照集校注》系年。",
    prior='UNVERIFIABLE', rev=REV)
add('C23','意象','ISSUE',
    "现文件 imagery 栏仍作：「全篇几乎无色彩，只有温度（寒）、声音（雁、雨）、时间（黄昏、黑）。」（逐字核对）",
    "旧问题未改：原文有「滿地黄花堆积」，「黄」为明确色语，与「几乎无色彩」冲突。应改「全篇仅『黄花』一处着色」。",
    prior='ISSUE', rev=REV)
add('C23','韵脚与声调','ISSUE',
    "现文件仍作：rhyme「韵脚：觅、戚、息、急、识、积、摘、黑、滴、得……词韵第十七部（陌麦昔锡职）」；prosody「上片起三句用四字叠字句……全篇多用齿音、舌音（寻、清、凄、惨、戚、急、摘、滴）」；genre_form「上片九句、下片八句」。",
    "旧问题未改：①句数与库谱（21 句）、钦定（10+8）均不合；②「急」为见母牙音，非齿音或舌音，举例失实；③韵部括注「陌麦昔锡职」与「第十七部」之名未给出《词林正韵》部次出处。",
    prior='ISSUE', rev=REV)
add('C23','艺术特点','ISSUE',
    "现文件 artistry ③ 仍作：「以『雁』『黄花』『梧桐细雨』三个秋日意象层层叠加，皆是『旧时相识』而人已非。」",
    "旧问题未改：原文「旧时相识」紧承「雁过也」，只系于雁；扩为三物（雁、黄花、梧桐细雨）无文本依据。",
    prior='ISSUE', rev=REV)

# ============ 写出 ============
FIELDS = ['card_id','title','author','dimension','verdict','evidence','issue_detail','prior_status','revised_check']
OUT = 'reports/tasks/2026-11-16/R2-12/THIRTY_CLOSE_READINGS_FINAL_AUDIT.csv'
with open(OUT,'w',encoding='utf-8-sig',newline='') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k,'') for k in FIELDS})

import collections
print('rows', len(rows))
print(collections.Counter(r['verdict'] for r in rows))
print(collections.Counter(r['card_id'] for r in rows if r['verdict']!='PASS'))
bad = [r for r in rows if r['verdict']!='PASS' and not r['issue_detail']]
print('non-pass without issue_detail:', len(bad))
