#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-11 F3: 上古音 40 例来源链复核（只依据输入文件已有出处，不联网）"""
import csv, os, re, sqlite3, opencc

BASE = '<PROJECT_ROOT>/poetry-database'
R2_10 = os.path.join(BASE, 'reports/tasks/2026-11-15/R2-10')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-15/R2-11')
T2S = opencc.OpenCC('t2s')
CJK = re.compile(r'[\u3400-\u9fff\uf900-\ufaff]')


def n(s):
    return T2S.convert(''.join(CJK.findall(s or '')))


# 逐例判定的出处要素（人工核对 attribution_source 后填写）
META = {
 'SJ-01': dict(scholar='香港特別行政區教育局課程發展處（機構）', work='《國風·關雎》教材（高中中國語文指定篇章）',
               locator='該 PDF 課文「韻腳」說明段', cs='CONFIRMED_CITATION',
               note='機構+文件+PDF 網址+逐字韻腳，四要素齊；唯附檔案為課程文件而非學者論文，屬「機構教材」一級，非學術考證。'),
 'SJ-03': dict(scholar='未署名', work='《古代漢語通論·詩經韻例》講義',
               locator='缺（僅文檔分享站 URL，無章節/頁碼）', cs='PARTIAL_CITATION',
               note='有書名與逐篇標部，但無作者、無出版信息，鏈接為 yidocs 文檔分享站，無法定位到具體頁；末章「吁」未見於引文（表列 10 韻字，引文可核 9）。'),
 'SJ-04': dict(scholar='未署名', work='《古代漢語通論·詩經韻例》講義',
               locator='缺（同上）', cs='PARTIAL_CITATION',
               note='引文作「采、友」，而《芣苡》全文無「友」字，表列亦作「有」；引文本身有訛字，該例之部依據實際上是「采、有」。'),
 'SJ-06': dict(scholar='未署名', work='《古代漢語通論·詩經韻例》講義',
               locator='缺（同上）', cs='PARTIAL_CITATION',
               note='引文與表列 6 韻字完全對應；但無作者/出版信息，且次章「元微脂」三部連用是否算換韻，講義與他本不一。'),
 'SJ-07': dict(scholar='未署名', work='《古代漢語通論·詩經韻例》講義',
               locator='缺（同上）', cs='PARTIAL_CITATION',
               note='表列 6 韻字中「瑤、玖」未見於引文（引文只列瓜琚報好），屬同部推定；「報/好」是否句中韻有異說。'),
 'SJ-08': dict(scholar='程翔', work='《〈詩經〉韻例》（《語文教學通訊》A 版轉載）',
               locator='缺年份、期號、頁碼；鏈接為 ima.qq.com 分享頁', cs='PARTIAL_CITATION',
               note='有作者與篇名，但無年期頁；且引文只具體列出首章韻腳（表列 34 位，引文可核僅 5 位），其餘 29 位屬作者自行推定，引文不足以支撐全篇。'),
 'SJ-09': dict(scholar='未署名', work='《古代漢語通論·詩經韻例》講義（另參 doosho.com）',
               locator='缺（同上）', cs='PARTIAL_CITATION',
               note='「前四句交韻」一語可核；但表列 15 韻字中「穗、醉、實、噎」未見引文，且「穗/醉」部屬本身有爭（質+物 vs 脂）。'),
 'SJ-10': dict(scholar='未署名', work='《古代漢語通論·詩經韻例》講義',
               locator='缺（同上）', cs='PARTIAL_CITATION',
               note='引文與表列 10 韻字完全對應；缺作者與出版信息。'),
 'SJ-11': dict(scholar='無責任作者（網站題解）', work='中華詩詞網《國風·秦風·蒹葭》題解',
               locator='網頁題解（無章節/頁碼）', cs='UNVERIFIED_CITATION',
               note='引文覆蓋表列 12/12 韻字，但出處為詩詞網站題解，既無作者亦非學術出版物，不足以支撐 SCHOLAR_IDENTIFIED_RHYME 之「學者」要件；宜降為 UNVERIFIED_CITATION 或改引他書。'),
 'SJ-14': dict(scholar='未署名（中國高校人文社會科學信息網論文 PDF）', work='《用系聯法考察〈詩經〉陽部韻字》',
               locator='該文《采薇》第三章段（無頁碼）', cs='PARTIAL_CITATION',
               note='論文名+PDF 可核，但無作者、無刊物年期；且只覆蓋第三章「剛/陽」（表列 28 位，引文可核 8 位），表已標「僅第三章可考」，未外推，處理正確。'),
 'SJ-27': dict(scholar='劉師培', work='《毛詩正韻》卷四（影印本）',
               locator='卷四（Wikimedia Commons 影印 PDF）', cs='CONFIRMED_CITATION',
               note='學者+書名+卷次+影印本 PDF，四要素齊，是 40 例中載體最硬的一條；惟劉氏部名（祭部、諄部等）自成系統，不可與王力三十部互換，表已標明。'),
 'SJ-28': dict(scholar='劉師培', work='《毛詩正韻》卷四（影印本）',
               locator='卷四（同上影印 PDF）', cs='CONFIRMED_CITATION',
               note='同 SJ-27；「至部」在王力系統併入質部，表已標明體系差異。'),
 'SJ-30': dict(scholar='未署名（中國高校人文社會科學信息網論文 PDF）', work='《用系聯法考察〈詩經〉陽部韻字》',
               locator='該文《閟宮》首章段（無頁碼）', cs='PARTIAL_CITATION',
               note='只覆蓋首章「王/陽/商」（表列 75 位，引文可核 6 位）；表已標「僅首章可考」，未外推，處理正確。'),
 'CC-01': dict(scholar='蔣驥（清）', work='《山帶閣注楚辭》卷首《楚辭說韻》',
               locator='卷首「離騷」條（上海古籍出版社 2019 于淑娟點校本，ISBN 9787532591381）；無頁碼',
               cs='CONFIRMED_CITATION',
               note='學者+書名+版本+篇條齊備，但無頁碼，且所附鏈接為中華典藏電子本，與所標 2019 點校本非同一載體；引文以「……」節引（表列 188 位，引文可核 4 位），中段 184 位無法由引文核對。另有「王力以庸降為東冬合韻（轉引自公開課件）」，屬轉引且無書頁，不宜作獨立依據。'),
 'CC-02': dict(scholar='蔣驥（清）', work='《山帶閣注楚辭》卷首《楚辭說韻》',
               locator='卷首「天問」條（同版本）；無頁碼', cs='CONFIRMED_CITATION',
               note='引文首尾可核（表列 201 位，可核 20 位），中段以「……」節引；部名一律 UNATTRIBUTED，與 status「SCHOLAR_IDENTIFIED_RHYME」並存，實指「韻段位置」而非「韻部」，語義須收窄。'),
 'CC-04': dict(scholar='蔣驥（清）', work='《山帶閣注楚辭》卷首《楚辭說韻》',
               locator='卷首「招魂」條（同版本）；無頁碼', cs='CONFIRMED_CITATION',
               note='表列 160 位，引文可核 27 位（節引）；「些」字句韻腳位置的異說已在 dispute 標明。'),
 'CC-05': dict(scholar='蔣驥（清）', work='《山帶閣注楚辭》卷首《楚辭說韻》',
               locator='卷首「九章·哀郢」條（同版本）；無頁碼', cs='CONFIRMED_CITATION',
               note='引文未用節引省略，表列 33 位中僅「鄣、忘」2 字不見於引文，覆蓋最好的一例。'),
 'CC-06': dict(scholar='蔣驥（清）', work='《山帶閣注楚辭》卷首《楚辭說韻》',
               locator='卷首「九章·涉江」條（同版本）；無頁碼', cs='CONFIRMED_CITATION',
               note='表列 35 位，引文無「……」而缺「螭、壽、皋、皇、鵲、夷、御、位、傺」9 字，即這 9 個韻位在蔣驥韻段中無對應，屬作者自增，不能同列為學者結論。'),
 'CC-07': dict(scholar='蔣驥（清）', work='《山帶閣注楚辭》卷首《楚辭說韻》',
               locator='卷首「九章·惜誦」條（同版本）；無頁碼', cs='CONFIRMED_CITATION',
               note='表列 44 位，缺 14 位（其中 12 位為「也」）。蔣驥未以「也」為韻腳，表卻大量取「也」入韻，與其自訂「虛字不入韻」通例相衝突，須逐位交代。'),
 'CC-08': dict(scholar='蔣驥（清）', work='《山帶閣注楚辭》卷首《楚辭說韻》',
               locator='卷首「九章·懷沙」條（同版本）；無頁碼', cs='CONFIRMED_CITATION',
               note='表列 43 位，缺 20 位（含 6 個「也」）。「明」是否入韻，蔣驥與王力不一，已在 dispute 標明。'),
 'CC-09': dict(scholar='蔣驥（清）', work='《山帶閣注楚辭》卷首《楚辭說韻》',
               locator='卷首「九歌·湘君」條（同版本）；無頁碼', cs='CONFIRMED_CITATION',
               note='表列 38 位，缺 14 位（洲、修、波、綢、湲、中、勞、長、閒、皋、上、中、若、得），蔣驥九段僅列 24 字；缺者屬作者依句末補入，無學者依據。'),
 'CC-10': dict(scholar='蔣驥（清）', work='《山帶閣注楚辭》卷首《楚辭說韻》',
               locator='卷首「九歌·山鬼」條（同版本）；無頁碼', cs='CONFIRMED_CITATION',
               note='表列 27 位，缺 9 位（狸、衡、天、上、晦、歸、歸、閒、冥），均為蔣驥明確不取者；表已於 dispute 聲明「不代為解釋」，處理誠實。'),
 'CC-03': dict(scholar='蔣驥（清）', work='《山帶閣注楚辭》卷首《楚辭說韻》（僅提及不收《九辯》）',
               locator='缺版本與頁碼（引文僅見於 note，未進 attribution_source）', cs='UNVERIFIED_CITATION',
               note='status 為 LINE_END_CANDIDATE，未宣稱韻位；但「蔣驥《說韻》不收《九辯》」一語有書名而無版本/頁碼，只能算 UNVERIFIED，不足以完全排除他本韻譜。'),
}

NO_SRC_NOTE = '輸入檔 attribution_source 為「NOT_FOUND（本輪未取得可查來源）」，未宣稱任何學者依據；此處記 MISSING_CITATION 僅表示「無引用可核」，不構成虛假引用。'

def main():
    rows = []
    for fn in ['SHIJING_30_CASES_R2_10.csv', 'CHUCI_10_CASES_R2_10.csv']:
        rows += list(csv.DictReader(open(os.path.join(R2_10, fn), encoding='utf-8-sig')))

    out = []
    for r in rows:
        cid = r['case_id']
        m = META.get(cid)
        pos = [x for x in r['rhyme_positions'].split(';') if x]
        pos_s = ';'.join(pos[:12]) + ('…（共 %d 位）' % len(pos) if len(pos) > 12 else '')
        if m:
            sch, wk, loc, cs, note = m['scholar'], m['work'], m['locator'], m['cs'], m['note']
            src = r['attribution_source']
        else:
            sch, wk, loc = '（無）', '（無）', '（無）'
            cs = 'MISSING_CITATION'
            src = r['attribution_source']
            note = NO_SRC_NOTE
            if r['case_status'] == 'LINE_END_CANDIDATE':
                note += ' 本例為 LINE_END_CANDIDATE：明示不構成韻位判斷，僅給句末候選位。'
            elif r['case_status'] == 'POSSIBLE_RHYME_POSITION':
                note += ' 本例為 POSSIBLE_RHYME_POSITION：韻位由句式推定，未宣稱學者歸部。'
        out.append(dict(case_id=cid, source_text=re.sub(r'\s+', ' ', src)[:400],
                        rhyme_position=pos_s, claim_status=r['case_status'],
                        scholar=sch, work_title=wk, locator=loc,
                        citation_status=cs, note=note))

    f = os.path.join(OUT, 'ANCIENT_RHYME_40_SOURCE_REVIEW.csv')
    with open(f, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['case_id', 'source_text', 'rhyme_position', 'claim_status',
                                           'scholar', 'work_title', 'locator', 'citation_status', 'note'])
        w.writeheader()
        w.writerows(out)
    from collections import Counter
    print('wrote', f, len(out))
    print(Counter(x['citation_status'] for x in out))
    print(Counter(x['claim_status'] for x in out))
    print(Counter((x['claim_status'], x['citation_status']) for x in out))


if __name__ == '__main__':
    main()
