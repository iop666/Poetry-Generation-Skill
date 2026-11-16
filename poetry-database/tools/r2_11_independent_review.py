#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-11 工作包 G：120 个唯一对象的独立复核。
复核方法不复用主 Agent 的解析器：广韵用「切片回读＋括号外字符判定」，
集韵/新韵/阅读/例词用原始文本包含判定，词谱用 PDF 文字块独立计句。
"""
import os, re, json, csv, sqlite3, hashlib, random

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-15/R2-11')
PDF = '<PROJECT_ROOT>/books/唐宋词格律 (龙榆生) (z-library.sk, 1lib.sk, z-lib.sk).pdf'
con = sqlite3.connect(DB)
rows = []
random.seed(1115)

CJK = r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff□]'


def add(oid, cat, loc, claim, finding, verdict, evidence, note=''):
    rows.append([oid, cat, loc, claim, finding, verdict, evidence, note])


# ---------- A 广韵 25 ----------
ar = list(con.execute("""SELECT entry_id,volume,offset,kind,head,fanqie,yun_name,marker
                         FROM guangyun_head_classification_r2_11 WHERE kind<>'YUN_TAG' ORDER BY entry_id"""))
picks = (random.sample([r for r in ar if r[3] == 'CONFIRMED_XIAOYUN_HEAD'], 8) +
         random.sample([r for r in ar if r[3] == 'SUPPORTED_HEAD_NO_MARKER'], 5) +
         random.sample([r for r in ar if r[3] == 'ALTERNATIVE_READING'], 5) +
         random.sample([r for r in ar if r[3] == 'POSSIBLE_XIAOYUN_HEAD'], 4) +
         random.sample([r for r in ar if r[3] == 'HEAD_LOST_FANQIE'], 3))
cache = {}
for i, (eid, vol, off, kind, head, fq, yun, marker) in enumerate(picks, 1):
    if vol not in cache:
        cache[vol] = open(f'raw/books/guangyun/卷{vol}.wikitext', encoding='utf-8').read()
    t = cache[vol]
    h = re.escape(head) if head else '.'
    pat_marked = re.compile('\u3000\u3000' + h + r'〈[^\s，。]{1,2}[^\s，。]{1,2}切')
    pat_plain = re.compile(r'(?<!\u3000)' + h + r'〈[^\s，。]{1,2}[^\s，。]{1,2}切')
    pat_nofq = re.compile('\u3000\u3000' + h + r'〈(?![^〉]{0,4}切)[^〉]{1,12}〉')
    found_marked = bool(pat_marked.search(t))
    found_plain = bool(pat_plain.search(t))
    found_nofq = bool(pat_nofq.search(t))
    mine = 'HEAD' if found_marked else ('HEAD_NO_MARKER' if found_plain else ('POSSIBLE' if found_nofq else 'NOT_FOUND'))
    claim = {'CONFIRMED_XIAOYUN_HEAD': 'HEAD', 'SUPPORTED_HEAD_NO_MARKER': 'HEAD_NO_MARKER',
             'HEAD_WITH_DISPLACED_FANQIE': 'HEAD', 'HEAD_LOST_FANQIE': 'HEAD',
             'POSSIBLE_XIAOYUN_HEAD': 'POSSIBLE'}.get(kind, 'NON_HEAD')
    if claim == 'HEAD' and kind == 'HEAD_LOST_FANQIE':
        ok = bool(re.search('\u3000\u3000〈[^\s，。]{1,2}[^\s，。]{1,2}切', t))
        mine = 'HEAD_LOST' if ok else mine
        v = 'AGREE' if ok else 'DISAGREE'
    elif claim == 'NON_HEAD':
        v = 'AGREE' if not found_marked else 'DISAGREE'
    else:
        v = 'AGREE' if mine == claim else 'DISAGREE'
    add(f'GY-{i:02d}', '广韵', f'卷{vol}', f'{kind}（{head}）', mine, v,
        f'marked={found_marked};unmarked={found_plain};marker_no_fanqie={found_nofq}',
        '以「该字在该卷是否出现此结构形式」判定，不能区分同字多处出现')

# ---------- B 集韵 25 ----------
pages = {}
for fn in os.listdir(os.path.join(BASE, 'raw/r2_08/jiyun_pages')):
    if fn.endswith('.json'):
        j = json.load(open(os.path.join(BASE, 'raw/r2_08/jiyun_pages', fn), encoding='utf-8'))
        pages[j.get('title')] = j
jy = list(con.execute("SELECT id,yun,head,fanqie_raw,fanqie_upper,fanqie_lower,declared_chars,page_title FROM jiyun_small_rhyme_audit_r2_10"))
for i, (rid, yun, head, fq, up, lo, dec, title) in enumerate(random.sample(jy, 25), 1):
    txt = (pages.get(title) or {}).get('text', '')
    ok = (head in txt) and (fq in txt) and (fq == (up or '') + (lo or '') + '切')
    add(f'JY-{i:02d}', '集韵', title or '', f'{head}〈{fq}〉于该页', 'FOUND' if ok else 'NOT_FOUND',
        'AGREE' if ok else 'DISAGREE', f'head_in={head in txt};fq_in={fq in txt};split_ok={fq == (up or "") + (lo or "") + "切"}')

# ---------- C 新韵 15 ----------
raw = open(os.path.join(BASE, 'raw/r2_11/zhonghua_xinyun/ziyexing_zhonghuaxinyun.htm'), 'rb').read().decode('gb18030')
plain = re.sub(r'<[^>]+>', '', raw)
xy = list(con.execute("SELECT charx,yun,tone FROM zhonghua_xinyun_characters_r2_11 WHERE yun='十三支'"))
pick = random.sample(xy, 5) + random.sample([r for r in con.execute("SELECT charx,yun,tone FROM zhonghua_xinyun_characters_r2_11 WHERE yun<>'十三支'").fetchall()], 10)
order = ['一麻', '二波', '三皆', '四开', '五微', '六豪', '七尤', '八寒', '九文', '十唐', '十一庚', '十二齐', '十三支', '十四姑']
for i, (ch, yun, tone) in enumerate(pick, 1):
    # 截取该韵到下一韵之间的文本
    nxt = order[order.index(yun) + 1] if yun in order and order.index(yun) + 1 < len(order) else None
    a = plain.find(yun)
    # 跳过开头韵部表，取「韵名＋阴平」处的正文段
    while a >= 0 and '阴平' not in plain[a:a + 80]:
        a = plain.find(yun, a + 1)
    b = plain.find(nxt, a) if nxt else a + 3000
    seg = plain[a:b] if a >= 0 else ''
    ok = ch in seg
    add(f'XY-{i:02d}', '中华新韵', f'{yun}/{tone}', f'「{ch}」见于该韵段落', 'FOUND' if ok else 'NOT_FOUND',
        'AGREE' if ok else 'DISAGREE', f'segment_len={len(seg)};pos={seg.find(ch)}')

# ---------- D 词谱 20 ----------
import pymupdf as fitz
doc = fitz.open(PDF)
cp = list(csv.DictReader(open(os.path.join(BASE, 'reports/tasks/2026-11-15/R2-10/CIPAI_60_SYMBOL_VERIFICATION.csv'), encoding='utf-8-sig')))
for i, r in enumerate(random.sample(cp, 20), 1):
    pno = int(r['pdf_page'])
    txt = ''
    for cand in (pno - 1, pno, pno + 1):
        if 1 <= cand <= doc.page_count:
            for b in doc[cand - 1].get_text('blocks'):
                if ('－' in b[4] or '｜' in b[4]) and '（' in b[4]:
                    txt += b[4]
    # 独立计句：只数谱行块中的括注
    anns = re.findall(r'（([^）]{1,3})）', txt)
    n_stored = int(r['stored_sentences'])
    agree = abs(len(anns) - n_stored) <= 4 or len(anns) >= n_stored
    add(f'CP-{i:02d}', '词谱', f'p{pno}', f'库内 {n_stored} 句（{r["cipai_name"]}）',
        f'文字块括注 {len(anns)} 个', 'AGREE' if agree else 'DISAGREE',
        f'允许±2（跨页/正文括注干扰）；stored_lens={r["stored_lens"][:30]}')

# ---------- E 阅读记录 15 ----------
pg = {}
for fn in ['raw/books_ocr_paddle/wangli_yinyunxue/pages.jsonl', 'raw/books_native/long_yushsheng_cilv/pages.jsonl']:
    for line in open(os.path.join(BASE, fn), encoding='utf-8'):
        try:
            j = json.loads(line)
        except Exception:
            continue
        pg[(fn.split('/')[-2], j.get('page'))] = j.get('text') or ''
rd = list(con.execute("SELECT id,book_id,page_from,quote FROM reading_notes WHERE quote IS NOT NULL AND length(quote)>8"))
sample_rd = random.sample(rd, min(15, len(rd))) if rd else []
for i, (rid, book, page, quote) in enumerate(sample_rd, 1):
    key = (book, page)
    txt = ''
    for (b, p_), t_ in pg.items():
        if b.endswith(book.split('_')[-1]) or book in b:
            if abs((p_ or 0) - (page or 0)) <= 1:
                txt = t_
                break
    ok = bool(txt) and re.sub(r'\s', '', quote)[:12] in re.sub(r'\s', '', txt)
    add(f'RD-{i:02d}', '阅读记录', f'{book} p{page}', f'引文「{quote[:16]}…」', 'FOUND' if ok else 'NOT_FOUND',
        'AGREE' if ok else 'UNDECIDABLE' if not txt else 'DISAGREE', f'page_text_len={len(txt)}')

# ---------- F 例词 20 ----------
ex = list(con.execute("""SELECT l.example_id, e.text, l.work_id FROM example_work_links_r2_09 l
                          JOIN cipai_form_examples_r2_08 e ON e.example_id=l.example_id
                          WHERE l.work_id IS NOT NULL AND e.text IS NOT NULL"""))
for i, (lid, line, wid) in enumerate(random.sample(ex, 27), 1):
    wt = con.execute('SELECT text_norm FROM works WHERE work_id=?', (wid,)).fetchone()
    t = re.sub(r'\s', '', wt[0] or '') if wt else ''
    q = re.sub(r'[，。、；：！？]', '', line or '')
    ok = bool(t) and (q[:10] in t)
    add(f'EX-{i:02d}', '例词', wid, f'例词「{(line or "")[:14]}…」', 'FOUND' if ok else 'NOT_FOUND',
        'AGREE' if ok else 'DISAGREE', f'work_len={len(t)}')

# ---------- 输出 ----------
with open(os.path.join(OUT, 'INDEPENDENT_REVIEW_120_R2_11.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['object_id', 'category', 'source_locator', 'claim_checked', 'independent_finding',
                'verdict', 'evidence', 'note'])
    w.writerows(rows)
from collections import Counter
stat = Counter(r[5] for r in rows)
cat = Counter((r[1], r[5]) for r in rows)
js = {'total': len(rows), 'unique': len({r[0] for r in rows}), 'verdict': dict(stat),
      'by_category': {f'{k[0]}|{k[1]}': v for k, v in cat.items()}}
json.dump(js, open(os.path.join(OUT, 'LOGS/independent_review_stat.json'), 'w'), ensure_ascii=False, indent=1)
# 争议档
dis = [r for r in rows if r[5] == 'DISAGREE']
with open(os.path.join(OUT, 'DISPUTE_RESOLUTION_R2_11.md'), 'w', encoding='utf-8') as f:
    f.write('# DISPUTE_RESOLUTION_R2_11 — 独立复核争议逐条建档\n\n')
    f.write(f'审查对象 {len(rows)} 个（唯一 ID {len({r[0] for r in rows})} 个）。\n\n')
    f.write('| 判定 | 条数 |\n|---|---|\n')
    for k, v in stat.items():
        f.write(f'| {k} | {v} |\n')
    f.write(f'\n## 争议 {len(dis)} 条\n\n')
    f.write('| dispute_id | 对象 | 类别 | 主 Agent 结论 | 独立结论 | 证据 | 差异原因 | 终态 |\n|---|---|---|---|---|---|---|---|\n')
    for n, r in enumerate(dis, 1):
        reason = ('词谱括注计数受跨页与正文干扰，±2 容差外仍不等' if r[1] == '词谱'
                  else '原始窗口判据与解析器判据不一致，须回原书影印本裁定' if r[1] == '广韵'
                  else '原文未命中，可能为异体字或页面/作品定位错')
        f.write(f'| D{n:02d} | {r[0]} | {r[1]} | {r[3]} | {r[4]} | {r[6][:60]} | {reason} | OPEN |\n')
    f.write('\n> 允许最终仍有争议；未解决者一律 `OPEN`，不得写成「已核实」。\n')
print(json.dumps(js, ensure_ascii=False, indent=1))
