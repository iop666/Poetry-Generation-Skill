#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-12：影印对校样本表、图像复核表、固定样本、字级索引审计等 CSV 的生成。

诚实原则：只把真正看过图并逐字比对过的记为 IMAGE_COLLATED；其余记 SAMPLED_NOT_COLLATED 或
NOT_STARTED 并写明原因，不以「已抽样」冒充「已对校」。
"""
import os, re, csv, json, sqlite3, hashlib

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-12')
IMG = os.path.join(BASE, 'raw/r2_12/facsimile')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# 我在 GY_p011（宋刻本 静嘉堂藏 大宋重修廣韻）上实际读到并核对过的条目
COLLATED = [
    # head, image_fanqie, db_fanqie, image_count, db_count, verdict, note
    ('東', '徳紅切', '徳紅切', '十七', 17, 'IMAGE_MATCH', '卷一叶一右起第一小韵'),
    ('同', '徒紅切', '徒紅切', '', 45, 'IMAGE_MATCH', '收字数在叶末，未逐字核'),
    ('中', '陟弓切', '陟弓切', '', 4, 'IMAGE_MATCH', ''),
    ('蟲', '直弓切', '直弓切', '', 7, 'IMAGE_MATCH', ''),
    ('終', '職戎切', '職戎切', '', 15, 'IMAGE_MATCH', ''),
    ('忡', '敕中切', '敕中切', '', 3, 'IMAGE_MATCH', ''),
    ('嵩', '息弓切', '息弓切', '', 9, 'IMAGE_MATCH', ''),
    ('戎', '如融切', '如融切', '', 9, 'IMAGE_MATCH', ''),
    ('崇', '鋤弓切(?)', '鋤功切', '', 4, 'DIFFERENCE_PENDING',
     '切下字图像作「弓」，转录作「功」；字迹略糊，需再取更高分辨率确认'),
]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # ---------- 1 广韵 100 条对校样本 ----------
    base = list(cur.execute('''SELECT candidate_head_id,volume_id,rhyme_group_id,head_character,raw_fanqie,
        fanqie_structure,count_actual,source_offset,head_kind FROM guangyun_count_crosswalk_r2_12'''))
    strata = {
        'ORDINARY_HEAD': [r for r in base if r[5] == 'TWO_CHAR' and r[6] and r[6] < 10],
        'MULTI_CHAR_HEAD': [r for r in base if r[6] and r[6] >= 10],
        'ALTERNATIVE_READING': [r for r in base if r[8] == 'HEAD_WITH_DISPLACED_FANQIE'],
        'FANQIE_ANOMALY': [r for r in base if r[5] in ('IRREGULAR_LONG', 'NONE')],
        'PLACEHOLDER': [r for r in base if r[3] == '□'],
        'BOUNDARY': [r for r in base if r[7] and r[7] < 1200],
    }
    quota = {'ORDINARY_HEAD': 18, 'MULTI_CHAR_HEAD': 17, 'ALTERNATIVE_READING': 14,
             'FANQIE_ANOMALY': 14, 'PLACEHOLDER': 14, 'BOUNDARY': 14}
    coll_map = {c[0]: c for c in COLLATED}
    rows = []
    n = 0
    # 先纳入实际逐字对校过的条目（东韵 9 条），再分层补齐
    used = set()
    for c in COLLATED:
        for r in base:
            if r[3] == c[0] and r[1] == 'V1' and r[3] not in used:
                used.add(r[3])
                n += 1
                st = 'IMAGE_COLLATED' if c[5] == 'IMAGE_MATCH' else c[5]
                rows.append([f'GYCO-{n:03d}', r[0], 'COLLATED_SAMPLE', r[1], r[2], r[3], r[4], c[1],
                             r[5], c[4] if c[4] else r[6], st, 'SBL015廣韻（静嘉堂藏宋刻）', 'p011',
                             'raw/r2_12/facsimile/GUANGYUN_p011.jpg', c[6]])
                break
    for k, q_ in quota.items():
        pool = strata[k]
        step = max(1, len(pool) // q_)
        picked = pool[::step][:q_]
        for r in picked:
            if r[3] in used:
                continue
            n += 1
            c = coll_map.get(r[3])
            if c and c[2] == r[4]:
                status, img, note = 'IMAGE_COLLATED', c[1], c[6]
            elif c:
                status, img, note = c[5], c[1], c[6]
            else:
                status, img = 'SAMPLED_NOT_COLLATED', ''
                note = '已按分层抽入样本，但宋刻本叶码—卷次映射未建立，尚未逐字对校'
            rows.append([f'GYCO-{n:03d}', r[0], k, r[1], r[2], r[3], r[4], img,
                         r[5], r[6], status, 'SBL015廣韻（静嘉堂藏宋刻）', 'p011',
                         'raw/r2_12/facsimile/GUANGYUN_p011.jpg', note])
    if len(rows) < 100:
        for r in base:
            if len(rows) >= 100:
                break
            if r[3] in used:
                continue
            used.add(r[3])
            rows.append([f'GYCO-{len(rows)+1:03d}', r[0], 'FILL', r[1], r[2], r[3], r[4], '',
                         r[5], r[6], 'SAMPLED_NOT_COLLATED', 'SBL015廣韻（静嘉堂藏宋刻）', '',
                         '', '补足以达 100 条样本；未对校'])
    with open(os.path.join(OUT, 'GUANGYUN_100_IMAGE_COLLATION.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['sample_id', 'candidate_head_id', 'stratum', 'volume', 'rhyme_group', 'head',
                    'db_fanqie', 'image_fanqie', 'structure', 'declared_or_actual_count', 'collation_status',
                    'source_edition', 'printed_page', 'image_path', 'note'])
        w.writerows(rows)
    stat_gy = {'total': len(rows), 'IMAGE_COLLATED': sum(1 for r in rows if r[10] == 'IMAGE_COLLATED'),
               'DIFFERENCE_PENDING': sum(1 for r in rows if r[10] == 'DIFFERENCE_PENDING'),
               'SAMPLED_NOT_COLLATED': sum(1 for r in rows if r[10] == 'SAMPLED_NOT_COLLATED')}

    # ---------- 2 集韵 100 条（未取影印页） ----------
    jy = list(cur.execute('''SELECT id,yun,volume,seq,head,fanqie_raw,declared_chars
                             FROM jiyun_small_rhyme_audit_r2_10 ORDER BY id'''))
    rows2 = []
    step = max(1, len(jy) // 100)
    for i, r in enumerate(jy[::step][:100], 1):
        rows2.append([f'JYCO-{i:03d}', r[0], r[2], r[1], r[3], r[4], r[5] or '', r[6] or '',
                      'NOT_STARTED',
                      'NLC892集韻（國家圖書館藏）第1冊 323 頁，已取得可下載通道但本輪未完成叶码定位',
                      '', '影印页通道已验证可用；叶码—卷次映射未建立，未做逐字对校'])
    with open(os.path.join(OUT, 'JIYUN_100_IMAGE_COLLATION.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['sample_id', 'rhyme_id', 'volume', 'rhyme_group', 'head', 'db_fanqie', 'declared_chars',
                    'collation_status', 'source_edition', 'image_path', 'note'])
        w.writerows(rows2)

    # ---------- 3 独立图像复核 40 ----------
    rows3 = []
    for i in range(1, 12):
        rows3.append([f'IR-{i:03d}', 'CIPAI_SYMBOL', f'R2-11_cipaiF_{i:02d}', 'IMAGE_REVIEWER_B（盲读）',
                      'PENDING', '盲读由独立审查会话执行，结果见 CIPAI_11_DOUBLE_BLIND_REVIEW.csv'])
    for i in range(12, 41):
        rows3.append([f'IR-{i:03d}', 'PENDING_CATEGORY', '', '',
                      'NOT_AVAILABLE', '本类无第二审查者可用；不以主 Agent 判读充数'])
    with open(os.path.join(OUT, 'INDEPENDENT_IMAGE_REVIEW_40.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['review_id', 'category', 'object_ref', 'reviewer', 'status', 'note'])
        w.writerows(rows3)

    # ---------- 4 词谱 20 条全图像控制 ----------
    rows4 = []
    cip = list(cur.execute('SELECT form_id,cipai_name,pdf_page,stored_sentences FROM cipai_symbol_audit_r2_10'))
    for i, r in enumerate(cip[:20], 1):
        rows4.append([f'CC-{i:03d}', r[0], r[1], r[2], r[3], 'NOT_SYMBOL_COLLATED',
                      'R2-11 只做到注类与句段轮廓级；本轮的逐符号图像核验未完成（第二审查者优先做 11 条残缺者）'])
    with open(os.path.join(OUT, 'CIPAI_20_FULL_IMAGE_CONTROL.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['control_id', 'form_id', 'cipai', 'pdf_page', 'stored_sentences', 'status', 'note'])
        w.writerows(rows4)

    # ---------- 5/6 音标 50 条 ----------
    schwa = json.load(open(os.path.join(BASE, 'reports/tasks/2026-11-15/R2-11/LOGS/schwa_images.json')))['items']
    rows5, rows6 = [], []
    for it in schwa:
        rows5.append([it['idx'], it['book'], it['page'], it['char'], it['status'], it.get('context_type', ''),
                      (it.get('left') or '').replace('\n', ' ')[:40], (it.get('right') or '').replace('\n', ' ')[:40],
                      'BLOCKED_MISSING_COORDINATES',
                      'OCR(VL) 只给页级文本，无字符级 bbox；按页内字符偏移比例定位的条带含 6-8 行，'
                      '单符号（ə/e）在缩览后不可辨。需用带 bbox 的 OCR 重跑，或人工目视整页逐字定位。'])
        rows6.append([it['idx'], it['book'], it['page'], it['char'], 'NOT_REVIEWED', 'NOT_REVIEWED',
                      '两审查者均未取得可辨局部图，不作判定'])
    with open(os.path.join(OUT, 'SCHWA_50_LEGIBLE_IMAGE_AUDIT.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['idx', 'book', 'pdf_page', 'char', 'r2_08_status', 'context_type', 'left_context',
                    'right_context', 'status', 'reason'])
        w.writerows(rows5)
    with open(os.path.join(OUT, 'SCHWA_50_DOUBLE_REVIEW.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['idx', 'book', 'pdf_page', 'char', 'reviewer_a', 'reviewer_b', 'note'])
        w.writerows(rows6)

    # ---------- 7 广韵 3,702 对照 ----------
    with open(os.path.join(OUT, 'GUANGYUN_3702_CROSSWALK.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['crosswalk_status', 'project_count', 'external_count', 'delta', 'matched', 'project_only',
                    'external_only', 'note'])
        w.writerow(['BLOCKED_NO_PUBLIC_ITEM_INDEX', 3730, 3702, 28, 'UNKNOWN', 'UNKNOWN', 'UNKNOWN',
                    '文脉项目声明 3,702 小韵/25,332 字头，底本标四库全书本《原本广韵》；'
                    '其逐条索引未公开、且站点禁止自动访问，无法建立逐条 crosswalk。'
                    '28 条差额只能作统计级比较，不得写作「差异已解释」'])
    # ---------- 8 广韵字级索引审计 ----------
    agg = list(cur.execute('''SELECT head,count(*) n,sum(kind IN ('CONFIRMED_XIAOYUN_HEAD','SUPPORTED_HEAD_NO_MARKER',
        'HEAD_WITH_DISPLACED_FANQIE','HEAD_LOST_FANQIE')) heads
        FROM guangyun_head_classification_r2_11 GROUP BY head ORDER BY n DESC LIMIT 2000'''))
    with open(os.path.join(OUT, 'GUANGYUN_CHARACTER_INDEX_AUDIT.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['character', 'n_records_in_transcription', 'n_as_xiaoyun_head', 'note'])
        for ch, n, h in agg:
            w.writerow([ch, n, h, '小韵内成员字无独立反切；韵目由所属小韵区间给出' if h == 0 else ''])
    # ---------- 9 固定样本 30 ----------
    fx = []
    def addf(fid, src, path, off, expect, level):
        p = os.path.join(BASE, path)
        fx.append([fid, src, path, off, expect, level, sha(p) if os.path.exists(p) else 'MISSING'])
    addf('FX-01', 'GUANGYUN', 'raw/books/guangyun/卷1.wikitext', 0, '卷首「一東〈獨用〉」韵目行存在', 'DIGITAL_TRANSCRIPTION')
    addf('FX-02', 'GUANGYUN', 'raw/books/guangyun/卷1.wikitext', 0, '「東〈徳紅切…十七〉」注末有汉字数字', 'DIGITAL_TRANSCRIPTION')
    addf('FX-03', 'GUANGYUN', 'raw/facsimile_missing', 0, '占位', 'PH')
    for i, v in enumerate(range(1, 6), 3):
        fx[-1] = [f'FX-{i+1:02d}', 'GUANGYUN', f'raw/books/guangyun/卷{v}.wikitext', 0,
                  f'卷{v} 首个小韵首存在且带反切', 'DIGITAL_TRANSCRIPTION', sha(os.path.join(BASE, f'raw/books/guangyun/卷{v}.wikitext'))]
    addf('FX-08', 'GUANGYUN_FACSIMILE', 'raw/r2_12/facsimile/GUANGYUN_p011.jpg', 0,
         '宋刻本卷一首页：東=徳紅切，注末「十七」', 'FACSIMILE_IMAGE_DIRECT')
    addf('FX-09', 'GUANGYUN_FACSIMILE', 'raw/r2_12/facsimile/GY_p011_R_z0.png', 0, '局部放大件（目录列）', 'FACSIMILE_IMAGE_DIRECT')
    pages = sorted(os.listdir(os.path.join(BASE, 'raw/r2_08/jiyun_pages')))[:3]
    for i, p in enumerate(pages, 10):
        addf(f'FX-{i:02d}', 'JIYUN', f'raw/r2_08/jiyun_pages/{p}', 0, '页内 ○ 数与 n_xiaoyun_mark 一致', 'DIGITAL_TRANSCRIPTION')
    addf('FX-13', 'ZHONGHUA_XINYUN', 'raw/r2_11/zhonghua_xinyun/ziyexing_zhonghuaxinyun.htm', 0,
         '十三支段含「－i」零韵母标注与四声字表', 'DIGITAL_TRANSCRIPTION')
    addf('FX-14', 'PINGSHUI_YUN', 'raw/r2_09/rhyme/平水韻.json', 0, '上平聲一東韻首行「東同銅…」', 'DIGITAL_TRANSCRIPTION')
    addf('FX-15', 'PINGSHUI_YUN', 'raw/r2_09/rhyme/平水韻.json', 0, 'revid 非空', 'DIGITAL_TRANSCRIPTION')
    addf('FX-16', 'CIPAI_PDF', 'books/唐宋词格律 (龙榆生) (z-library.sk, 1lib.sk, z-lib.sk).pdf', 230,
         'p230 西江月谱行含 ＋｜－ 与括注', 'PRINTED_EDITION_DIRECT')
    addf('FX-17', 'CIPAI_IMAGE', 'raw/r2_11/images/R2-11_cipaiF_01_F07-0181_p230_stack.png', 0,
         '600dpi 谱行图，8 句', 'FACSIMILE_IMAGE_DIRECT')
    addf('FX-18', 'CIPAI_IMAGE', 'raw/r2_11/images/R2-11_cipaiF_05_F07-0065_p88_stack.png', 0,
         '长调 39 句，注类含「句或韵」', 'FACSIMILE_IMAGE_DIRECT')
    for i, (t, n) in enumerate(cur.execute('SELECT bu,count(*) FROM ph_cilin_r2_09 GROUP BY bu ORDER BY bu LIMIT 3').fetchall(), 19):
        fx.append([f'FX-{i:02d}', 'CILIN_ZHENGYUN', 'database/poetry.db#ph_cilin_r2_09', 0, f'{t} 部有 {n} 行', 'DIGITAL_TRANSCRIPTION', sha(os.path.join(BASE, 'database/poetry.db'))])
    for i, (t, n) in enumerate(cur.execute('SELECT bu,count(*) FROM ph_zhongyuan_r2_09 GROUP BY bu LIMIT 3').fetchall(), 22):
        fx.append([f'FX-{i:02d}', 'ZHONGYUAN_YINYUN', 'database/poetry.db#ph_zhongyuan_r2_09', 0, f'{t} 部有 {n} 行', 'DIGITAL_TRANSCRIPTION', sha(os.path.join(BASE, 'database/poetry.db'))])
    for i, f in enumerate(sorted(os.listdir(os.path.join(BASE, 'raw/r2_11/images')))[:3], 25):
        addf(f'FX-{i:02d}', 'CIPAI_IMAGE', f'raw/r2_11/images/{f}', 0, '图像存在且可哈希', 'FACSIMILE_IMAGE_DIRECT')
    addf('FX-28', 'JIYUN', 'raw/r2_08/jiyun_pages/' + pages[0], 0, '页文本含「○」分隔小韵', 'DIGITAL_TRANSCRIPTION')
    addf('FX-29', 'GUANGYUN', 'raw/books/guangyun/卷3.wikitext', 0, '卷三「一董〈獨用〉」', 'DIGITAL_TRANSCRIPTION')
    addf('FX-30', 'ZHONGHUA_XINYUN', 'raw/r2_11/zhonghua_xinyun/ziyexing_zhonghuaxinyun.htm', 0, '十四韵名逐一可检出', 'DIGITAL_TRANSCRIPTION')
    addf('FX-31', 'GUANGYUN_FACSIMILE', 'raw/r2_12/facsimile/GUANGYUN_p012.jpg', 0,
         '宋刻本卷二首页：「送」韵首「鳳 馮貢切」', 'FACSIMILE_IMAGE_DIRECT')
    addf('FX-32', 'JIYUN', 'raw/r2_08/jiyun_pages/' + sorted(os.listdir(os.path.join(BASE, 'raw/r2_08/jiyun_pages')))[-1], 0,
         '集韵卷末页 ○ 数与 n_mark 一致', 'DIGITAL_TRANSCRIPTION')
    addf('FX-33', 'CIPAI_IMAGE', 'raw/r2_11/images/R2-11_cipaiF_11_F07-0029_p42_stack.png', 0,
         '柳梢青定格 12 句', 'FACSIMILE_IMAGE_DIRECT')
    addf('FX-34', 'ZHONGHUA_XINYUN', 'raw/r2_11/zhonghua_xinyun/ziyexing_zhonghuaxinyun.htm', 0,
         '十三支阴平字表含「詩尸师」类零韵母字', 'DIGITAL_TRANSCRIPTION')
    with open(os.path.join(OUT, 'SOURCE_GOLDEN_FIXTURES_R2_12.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['fixture_id', 'source_book', 'source_file', 'offset_or_page', 'expected_observation',
                    'evidence_level', 'source_sha256'])
        w.writerows(fx)
    print(json.dumps({'gy_collation': stat_gy, 'jy': len(rows2), 'img_review': len(rows3),
                      'cipai_ctrl': len(rows4), 'schwa': len(rows5), 'fixtures': len(fx)}, ensure_ascii=False, indent=1))
    con.close()


if __name__ == '__main__':
    main()
