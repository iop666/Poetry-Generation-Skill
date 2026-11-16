#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-11 工作包 B：《中华新韵》十四韵完整恢复。
原文来源：子夜星网站转录《中华新韵（十四韵）常用字简表》（中华诗词学会 2005-05 颁布），
本地保存 raw/r2_11/zhonghua_xinyun/ziyexing_zhonghuaxinyun.htm（SHA-256 见 FILE_MANIFEST）。
要点：十三支为「-i 零韵母」韵部，不是空韵部；规则层必须支持 ZERO_FINAL。
"""
import os, re, csv, json, sqlite3, hashlib
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'reports/tasks/2026-11-15/R2-11')
SRC = os.path.join(BASE, 'raw/r2_11/zhonghua_xinyun/ziyexing_zhonghuaxinyun.htm')
DB = os.path.join(BASE, 'database/poetry.db')

YUN_ORDER = ['一麻', '二波', '三皆', '四开', '五微', '六豪', '七尤', '八寒',
             '九文', '十唐', '十一庚', '十二齐', '十三支', '十四姑']
YUN_FINALS = {
    '一麻': ('a,ia,ua', 'EXPLICIT_FINAL'), '二波': ('o,e,uo', 'EXPLICIT_FINAL'),
    '三皆': ('ie,üe', 'EXPLICIT_FINAL'), '四开': ('ai,uai', 'EXPLICIT_FINAL'),
    '五微': ('ei,ui', 'EXPLICIT_FINAL'), '六豪': ('ao,iao', 'EXPLICIT_FINAL'),
    '七尤': ('ou,iu', 'EXPLICIT_FINAL'), '八寒': ('an,ian,uan,üan', 'EXPLICIT_FINAL'),
    '九文': ('en,in,un,ün', 'EXPLICIT_FINAL'), '十唐': ('ang,iang,uang', 'EXPLICIT_FINAL'),
    '十一庚': ('eng,ing,ong,iong', 'EXPLICIT_FINAL'), '十二齐': ('i,er,ü', 'EXPLICIT_FINAL'),
    '十三支': ('-i(零韵母)', 'ZERO_FINAL'), '十四姑': ('u', 'EXPLICIT_FINAL'),
}
HEAD_RE = re.compile(r'^[　\s]*([一二三四五六七八九十]{1,3})(麻|波|皆|开|微|豪|尤|寒|文|唐|庚|齐|支|姑)[　\s]*(.*)$')
TONE_RE = re.compile(r'^[　\s]*(阴平|阳平|上声|去声)[　\s]*$')
RUSHENG_RE = re.compile(r'^[　\s]*派入(阴平|阳平|上声|去声)的入声字[：:]?[　\s]*(.*)$')
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')


def decode(path):
    raw = open(path, 'rb').read()
    for enc in ('gb18030', 'utf-8', 'big5'):
        try:
            return raw.decode(enc), enc, hashlib.sha256(raw).hexdigest()
        except UnicodeDecodeError:
            continue
    raise SystemExit('decode failed')


def clean_text(html):
    t = re.sub(r'(?is)<(script|style).*?</\1>', '', html)
    t = re.sub(r'(?s)<br\s*/?>', '\n', t)
    t = re.sub(r'(?s)</(p|div|tr|td|h\d)>', '\n', t)
    t = re.sub(r'(?s)<[^>]+>', '', t)
    t = t.replace('\r', '\n').replace('\xa0', '\u3000')
    t = re.sub(r'[━┃┣┫┗┛╋╋]', '', t)
    t = re.sub(r'\n{2,}', '\n', t)
    return t


def parse(text):
    chars = []          # (char, yun, tone, tone_class, note, order)
    cur_yun = None
    cur_tone = None
    cur_class = None
    order = 0
    for line in text.split('\n'):
        line = line.rstrip()
        if not line.strip():
            continue
        m = HEAD_RE.match(line)
        if m and m.group(2) in ('麻', '波', '皆', '开', '微', '豪', '尤', '寒', '文', '唐', '庚', '齐', '支', '姑'):
            name = m.group(1) + m.group(2)
            if name in YUN_ORDER:
                cur_yun, cur_tone, cur_class = name, None, None
                continue
        if cur_yun is None:
            continue
        mr = RUSHENG_RE.match(line)
        if mr:
            cur_tone, cur_class = mr.group(1), 'RUSHENG_PAI'
            payload = mr.group(2)
        else:
            mt = TONE_RE.match(line)
            if mt:
                cur_tone, cur_class = mt.group(1), 'NORMAL'
                continue
            payload = None
        if cur_tone is None:
            continue
        body = payload if payload is not None else line
        # 去掉音标/说明行
        if re.search(r'ㄚ|ㄛ|ㄜ|ㄞ|ㄟ|ㄠ|ㄡ|ㄢ|ㄣ|ㄤ|ㄥ|ㄦ|ㄧ|ㄨ|ㄩ', body) and not CJK.search(body):
            continue
        # 括号注记
        for seg in re.findall(r'([^（）]*)(（[^（）]*）)?', body):
            pass
        pos = 0
        buf = []
        note = ''
        for mm in re.finditer(r'（([^（）]*)）|([\u3400-\u4dbf\u4e00-\u9fff])', body):
            if mm.group(1) is not None:
                note = mm.group(1)
                if buf:
                    order += 1
                    chars.append((buf[-1], cur_yun, cur_tone, cur_class, note, order))
                    note = ''
                continue
            ch = mm.group(2)
            if buf:
                order += 1
                chars.append((buf[-1], cur_yun, cur_tone, cur_class, '', order))
            buf = [ch]
        if buf:
            order += 1
            chars.append((buf[-1], cur_yun, cur_tone, cur_class, note, order))
    return chars


def to_pinyin_map(chars):
    try:
        from pypinyin import pinyin, Style
    except ImportError:
        return {}
    uniq = sorted({c[0] for c in chars})
    out = {}
    for ch in uniq:
        try:
            py = pinyin(ch, style=Style.TONE3, heteronym=True, errors='ignore')[0]
        except Exception:
            py = []
        out[ch] = py
    return out


ZERO_SYL = {'zhi', 'chi', 'shi', 'ri', 'zi', 'ci', 'si'}


def norm_final(syl):
    """把带声调拼音归一为十四韵使用的韵母形式（含 y/w/j/q/x 的介音还原）。"""
    s = re.sub(r'[0-9]', '', syl).lower()
    if s in ZERO_SYL:
        return 'ZERO'
    if s.startswith('y'):
        r = s[1:]
        return {'i': 'i', 'a': 'ia', 'e': 'ie', 'ao': 'iao', 'ou': 'iu', 'an': 'ian',
                'in': 'in', 'ang': 'iang', 'ing': 'ing', 'ong': 'iong', 'u': 'ü',
                'ue': 'üe', 'uan': 'üan', 'un': 'ün'}.get(r, r)
    if s.startswith('w'):
        r = s[1:]
        return {'u': 'u', 'a': 'ua', 'o': 'uo', 'ai': 'uai', 'ei': 'ui', 'an': 'uan',
                'en': 'un', 'ang': 'uang', 'eng': 'ueng'}.get(r, r)
    for ini in ('zh', 'ch', 'sh', 'b', 'p', 'm', 'f', 'd', 't', 'n', 'l',
                'g', 'k', 'h', 'j', 'q', 'x', 'r', 'z', 'c', 's'):
        if s.startswith(ini):
            f = s[len(ini):]
            if ini in ('j', 'q', 'x') and f.startswith('u'):
                f = 'ü' + f[1:]
            return f
    return s


FINAL_TABLE = {
    '一麻': {'a', 'ia', 'ua'}, '二波': {'o', 'e', 'uo', 'ê'},
    '三皆': {'ie', 'üe'}, '四开': {'ai', 'uai'}, '五微': {'ei', 'ui'},
    '六豪': {'ao', 'iao'}, '七尤': {'ou', 'iu'}, '八寒': {'an', 'ian', 'uan', 'üan'},
    '九文': {'en', 'in', 'un', 'ün'}, '十唐': {'ang', 'iang', 'uang'},
    '十一庚': {'eng', 'ing', 'ong', 'iong'}, '十二齐': {'i', 'er', 'ü'},
    '十四姑': {'u'},
}


def rule_yun(syl):
    """按十四韵规则归部；十三支由 ZERO_FINAL 规则处理（舌尖前/後 i）。"""
    f = norm_final(syl)
    if f == 'ZERO':
        return '十三支'
    for y, fs in FINAL_TABLE.items():
        if f in fs:
            return y
    return None


def main():
    html, enc, sha = decode(SRC)
    text = clean_text(html)
    chars = parse(text)
    # 去重（同字同韵同调同注只留一条）
    seen = set()
    uniq = []
    for c in chars:
        k = (c[0], c[1], c[2], c[3])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(c)
    by_yun = Counter(c[1] for c in uniq)
    py = to_pinyin_map(uniq)
    # 规则核验
    check = Counter()
    mism = []
    for ch, yun, tone, cls, note, order in uniq:
        pys = py.get(ch) or []
        hits = [rule_yun(p) for p in pys]
        if not pys:
            check['NO_PINYIN'] += 1
            continue
        if yun in hits:
            check['RULE_MATCH'] += 1
        else:
            check['RULE_MISMATCH'] += 1
            mism.append((ch, yun, tone, '/'.join(pys[:3]), '/'.join(str(h) for h in hits[:3])))
    # 写库
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.executescript('''
    DROP TABLE IF EXISTS zhonghua_xinyun_characters_r2_11;
    CREATE TABLE zhonghua_xinyun_characters_r2_11(
      id INTEGER PRIMARY KEY, charx TEXT, yun TEXT, tone TEXT, tone_class TEXT,
      note TEXT, source_order INT, pinyin TEXT, rule_yun TEXT, rule_match INT);
    DROP TABLE IF EXISTS zhonghua_xinyun_zero_final_r2_11;
    CREATE TABLE zhonghua_xinyun_zero_final_r2_11(
      yun TEXT, rule_type TEXT, final_text TEXT, initial_scope TEXT,
      n_chars INT, n_normal INT, n_rusheng INT, note TEXT);
    ''')
    for i, (ch, yun, tone, cls, note, order) in enumerate(uniq, 1):
        pys = py.get(ch) or []
        hits = {rule_yun(p) for p in pys} if pys else set()
        ry = rule_yun(pys[0]) if pys else None
        match_any = 1 if yun in hits else 0
        cur.execute('INSERT INTO zhonghua_xinyun_characters_r2_11 VALUES (?,?,?,?,?,?,?,?,?,?)',
                    (i, ch, yun, tone, cls, note, order, '/'.join(pys), ry, match_any))
    zhi = [c for c in uniq if c[1] == '十三支']
    cur.execute('INSERT INTO zhonghua_xinyun_zero_final_r2_11 VALUES (?,?,?,?,?,?,?,?)',
                ('十三支', 'ZERO_FINAL', '-i(零韵母)', 'zh/ch/sh/r/z/c/s + i',
                 len(zhi), sum(1 for c in zhi if c[3] == 'NORMAL'),
                 sum(1 for c in zhi if c[3] == 'RUSHENG_PAI'),
                 '舌尖前/後 i，与十二齐的舌面 i 分立；原书标「-i 零韵母」'))
    con.commit()

    # 14 韵规则表
    with open(os.path.join(OUT, 'ZHONGHUA_XINYUN_14_RHYME_RULES.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['yun', 'rule_type', 'final_text', 'initial_scope', 'n_chars', 'n_yinyang_ping',
                    'n_shang', 'n_qu', 'n_rusheng_pai', 'source'])
        for y in YUN_ORDER:
            cs = [c for c in uniq if c[1] == y]
            w.writerow([y, YUN_FINALS[y][1], YUN_FINALS[y][0],
                        'zh/ch/sh/r/z/c/s' if y == '十三支' else '',
                        len(cs), sum(1 for c in cs if c[2] in ('阴平', '阳平')),
                        sum(1 for c in cs if c[2] == '上声'), sum(1 for c in cs if c[2] == '去声'),
                        sum(1 for c in cs if c[3] == 'RUSHENG_PAI'),
                        '中华新韵(十四韵)常用字简表 / ziyexing 转录'])
    # 十三支逐字审计
    with open(os.path.join(OUT, 'ZHONGHUA_XINYUN_13_ZHI_AUDIT.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', 'char', 'tone', 'tone_class', 'note', 'pinyin', 'rule_yun', 'rule_match'])
        for i, (ch, yun, tone, cls, note, order) in enumerate([c for c in uniq if c[1] == '十三支'], 1):
            pys = py.get(ch) or []
            ry = rule_yun(pys[0]) if pys else None
            w.writerow([i, ch, tone, cls, note, '/'.join(pys), ry, 1 if ry == '十三支' else 0])
    # 全字表
    with open(os.path.join(OUT, 'LOGS/zhonghua_chars.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['char', 'yun', 'tone', 'tone_class', 'note'])
        w.writerows(uniq)
    st7216, n7216 = reaudit_7216(uniq, py)
    summary = {'reaudit_7216': st7216, 'reaudit_7216_rows': n7216, 'encoding': enc, 'html_sha256': sha, 'chars_total': len(uniq),
               'by_yun': dict(by_yun), 'zhi_chars': len(zhi), 'rule_check': dict(check),
               'mismatch_sample': mism[:30]}
    json.dump(summary, open(os.path.join(OUT, 'LOGS/xinyun_summary.json'), 'w'), ensure_ascii=False, indent=1)
    con.close()
    print(json.dumps(summary, ensure_ascii=False, indent=1)[:2500])



def reaudit_7216(uniq, py):
    """重审 R2-09 的 7,216 条派生记录：补十三支、查多音字丢失、核规则一致性。"""
    con = sqlite3.connect(DB)
    rows = list(con.execute('SELECT id, charx, rhyme_group, tone, rule_yun, rule_match FROM ph_modern_audit_r2_09'))
    con.close()
    table = defaultdict(set)
    for ch, yun, tone, cls, note, order in uniq:
        table[ch].add(yun)
    TONE_MAP = {'阴平': (1,), '阳平': (2,), '上声': (3,), '去声': (4,), '平': (1, 2), '仄': (3, 4)}
    out = []
    stat = Counter()
    for rid, ch, group, tone, ry, rm in rows:
        pys = py.get(ch) or []
        ry2 = rule_yun(pys[0]) if pys else None
        tones = [int(p[-1]) for p in pys if p and p[-1].isdigit()]
        want = TONE_MAP.get(tone)
        in_table = ch in table
        agrees = group in table.get(ch, set())
        zhi = '十三支' in table.get(ch, set()) or (pys and pys[0].lower().startswith(('zhi', 'chi', 'shi', 'ri', 'zi', 'ci', 'si')))
        tone_ok = (any(w in tones for w in want)) if want and tones else None
        if not in_table:
            stat['CHAR_NOT_IN_JIANBIAO'] += 1
        elif agrees and tone_ok:
            stat['AGREE_YUN_AND_TONE'] += 1
        elif agrees:
            stat['AGREE_YUN_TONE_DIFF'] += 1
        else:
            stat['DISAGREE_YUN'] += 1
        if zhi:
            stat['SHOULD_BE_13ZHI'] += 1
        if len(set(pys)) > 1:
            stat['POLYPHONE'] += 1
        out.append((rid, ch, group, tone, ry, ry2, '/'.join(pys), '|'.join(sorted(table.get(ch, set()))),
                    int(in_table), int(agrees), 1 if zhi else 0, tone_ok))
    path = os.path.join(OUT, 'ZHONGHUA_XINYUN_7216_REAUDIT.csv')
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', 'char', 'r2_09_rhyme_group', 'r2_09_tone', 'r2_09_rule_yun', 'r2_11_rule_yun',
                    'pinyin', 'jianbiao_yun', 'in_jianbiao', 'yun_agree', 'should_be_13zhi', 'tone_consistent'])
        w.writerows(out)
    json.dump(dict(stat), open(os.path.join(OUT, 'LOGS/xinyun_7216_stat.json'), 'w'), ensure_ascii=False, indent=1)
    return dict(stat), len(out)


if __name__ == '__main__':
    main()
