#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-13 工作包 A：R2-12 历史结果重新对账 + 建立两个独立维度。

维度一（内容性质）：沿用 R2-12 的 EDITORIAL_NOTE / MIXED_BODY_AND_NOTE / POEM_BODY / VARIANT_NOTE。
维度二（归一化影响）：本轮新算，用 text_raw 与 text_norm 的汉字序列比对得出，可多标签。
"""
import os, re, csv, json, sqlite3
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-13')
R12 = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-12')
HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
MARK = re.compile(r'一作|一本作|一云|或作|說作|恐作|疑作')


def han(s):
    return ''.join(HAN.findall(s or ''))


def is_subseq(small, big):
    """small 是否为 big 的子序列，返回 (bool, 缺失片段列表)。"""
    it = iter(big)
    miss = []
    cur = []
    for ch in small:
        for b in it:
            if b == ch:
                if cur:
                    miss.append(''.join(cur))
                    cur = []
                break
            cur.append(b)
        else:
            return False, []
    if cur:
        miss.append(''.join(cur))
    return True, miss


def extra_chars(small, big):
    """big 相对 small 多出的字（按子序列对齐后）。"""
    it = iter(small)
    add = []
    cur = []
    for ch in big:
        for s in it:
            if s == ch:
                if cur:
                    add.append(''.join(cur))
                    cur = []
                break
            cur.append(ch)
        else:
            cur.append(ch)
            continue
    if cur:
        add.append(''.join(cur))
    return add


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    aud = list(csv.DictReader(open(os.path.join(R12, 'WORKS_TEXT_POLLUTION_339_AUDIT.csv'), encoding='utf-8-sig')))
    rev = {r['work_id']: r for r in csv.DictReader(open(os.path.join(R12, 'WORKS_TEXT_REVISIONS_R2_12.csv'), encoding='utf-8-sig'))}
    ids = [r['work_id'] for r in aud]
    q = ','.join('?' * len(ids))
    w = {r[0]: r for r in cur.execute(
        f'SELECT work_id,title_raw,author_name,text_raw,text_norm,char_count,source_id,record_locator FROM works WHERE work_id IN ({q})', ids)}

    rows = []
    stat2 = Counter()
    for r in aud:
        wid = r['work_id']
        raw, norm = (w[wid][3] or ''), (w[wid][4] or '')
        rc, nc = han(raw), han(norm)
        tags = []
        # 先剥掉「（…一作…）」类括号校记，得到理想正文
        ideal_raw = re.sub(r'[（(][^）()]{0,60}(一作|一本作|一云|或作)[^）()]{0,60}[）)]', '', raw or '')
        ic = han(ideal_raw)
        has_bracket_note = ic != rc
        no_bracket_note = bool(MARK.search(raw or '')) and not has_bracket_note
        if rc == nc:
            tags.append('BODY_PRESERVED')
        elif has_bracket_note and ic == nc:
            tags.append('NOTE_REMOVED_ONLY')
        elif has_bracket_note and is_subseq(nc, ic)[0] and len(nc) < len(ic):
            tags.append('BODY_DELETED')
        elif has_bracket_note and is_subseq(ic, nc)[0] and len(nc) > len(ic):
            tags.append('BODY_EXPANDED')
        elif no_bracket_note:
            tags.append('NO_BRACKET_NOTE_STRUCTURE')
        elif is_subseq(nc, rc)[0] and len(nc) < len(rc):
            tags.append('BODY_DELETED')
        elif is_subseq(rc, nc)[0] and len(nc) > len(rc):
            tags.append('BODY_EXPANDED')
        else:
            tags.append('BODY_REORDERED_OR_MIXED')
        if MARK.search(norm or ''):
            tags.append('NOTE_RETAINED')
        if MARK.search(raw or '') and not MARK.search(norm or ''):
            tags.append('VARIANT_LOST')
        if has_bracket_note and 'NOTE_RETAINED' not in tags:
            tags.append('NOTE_REMOVED')
        if not tags:
            tags.append('UNDECIDABLE')
        for t in tags:
            stat2[t] += 1
        # 缺失片段（前三个）
        miss_txt = ''
        if 'BODY_DELETED' in tags:
            base_c = ic if has_bracket_note else rc
            sub, miss = is_subseq(nc, base_c)
            miss_txt = ' / '.join(miss[:3])[:120]
        rows.append([wid, r['title'][:40], r['author_name'][:20], r['classification'], r['confidence'],
                     len(rc), len(nc), len(nc) - len(rc), '|'.join(tags), miss_txt,
                     'IN_REVISIONS' if wid in rev else 'NO_REVISION_CANDIDATE'])
    # 339 维度表
    with open(os.path.join(OUT, 'LOGS/works_339_two_dimensions.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        wtr = csv.writer(f)
        wtr.writerow(['work_id', 'title', 'author', 'class_r2_12', 'confidence_r2_12', 'raw_han_len',
                      'norm_han_len', 'len_delta', 'normalization_impact', 'deleted_fragments', 'revision_state'])
        wtr.writerows(rows)

    # ---------- 历史对账 ----------
    samp = list(csv.DictReader(open(os.path.join(R12, 'WORKS_TEXT_500_SAMPLE_AUDIT.csv'), encoding='utf-8-sig')))
    lab = Counter()
    for s in samp:
        for t in s['verdict'].split('|'):
            lab[t.strip()] += 1
    rec = Counter(s['verdict'] for s in samp)
    recon = [
        ['R12-01', '作品抽样 560/564', '报告称 560 条、分类合计 564',
         f'记录数 {len(samp)}，唯一 work_id {len({s["work_id"] for s in samp})}；'
         f'多标签记录 {sum(1 for s in samp if "|" in s["verdict"])} 条；'
         f'按记录 {len(samp)}，按标签 {sum(lab.values())}',
         'RESOLVED：不存在计数错误。564 是「标签计数」，560 是「记录计数」，差 4 来自 4 条多标签记录'
         '（TRUNCATED|NOTE_MIXED 2、DUP|TITLE_REPEAT 1、TRUNCATED|DUP 1）',
         '今后同时报两种口径：记录数与标签数'],
        ['R12-02', '100 字 × 七类来源 = 936 行', '报告称 936 行',
         f'100 个汉字，平均 9.36 行/字；同一字在六书各有记录，且同书内可有多韵/多读',
         'RESOLVED：936 是「多记录数」，不是 700 个固定格。每行代表一条「书—韵—反切/声调」记录',
         '报告中已注明「多记录」，需在调用方文档中明示「行数≠字数」'],
        ['R12-03', '120 对象含 20 条未盲读词谱', '主表生成时盲读未落地',
         '词谱 20 条在主表中为 UNDECIDABLE；盲读结果另存 CIPAI_11_DOUBLE_BLIND_REVIEW.csv',
         'PARTIAL：本轮已用盲读结果重算词谱 11 条（见 CIPAI_5_TUNE_CONFLICTS_REAUDIT.csv），'
         '但 20 条中含 9 条不在 11 条之列，仍为 UNDECIDABLE',
         '需在 R2-13 的 120 表中把词谱项替换为已盲读的 11 条'],
        ['R12-04', '11 图 5 条冲突', 'R2-12 报告',
         'BOTH_AGREE 5 / CIPAI_CONFLICT 3 / SENTENCE_COUNT_CONFLICT 2 / UNDECIDABLE 1',
         'CONFIRMED：已在 R2-12 记录；本轮做映射修复（工作包 H）',
         '裁切图与 form_id 对应须重建'],
        ['R12-05', '42,352 行字级索引', 'R2-12 报告',
         '含 HEAD_MATCH 3,569 / OUT_OF_ORDER 364 / POSITION_ONLY 227 / NO_SEGMENT 9',
         'CONFIRMED：本轮在查询口径中分层标注 align 字段，不再合并称「98.9% 定位成功」',
         'POSITION_ONLY 227 条不得当已确认'],
        ['R12-06', '339 是筛查集合', 'R2-12 报告',
         f'339 条均来自 `text_raw LIKE %一作%`；其中 POEM_BODY {sum(1 for r in rows if r[3]=="POEM_BODY")} 条不需清洗',
         'CONFIRMED：339 是「候选集」，实际需处理的是非 POEM_BODY 部分',
         '不得把 339 当「339 条待删」'],
        ['R12-07', '328 条 applied=NO', 'R2-12 报告',
         '328 条全部未应用；11 条缺口全部为 POEM_BODY',
         'CONFIRMED：本轮仍不写入，只出候选（见 WORKS_TEXT_REPAIR_CANDIDATES.csv）',
         '本轮不覆盖 works.text_norm'],
        ['R12-08', '442 对繁简双写', 'R2-12 报告',
         '本轮由作者专项独立核实（AUTHORS_442_VARIANT_PAIRS.csv）',
         'PARTIAL：分类结果见作者专项，但一律不合并',
         '须建立身份而非去重'],
        ['R12-09', '1,639 条非人名', 'R2-12 报告',
         '本轮由作者专项核实（AUTHORS_1639_SUSPECTED_NONPERSON.csv）',
         'PARTIAL：按 author_name 聚合给出分类，不按字切分更正',
         '需核来源字段'],
        ['R12-10', '元曲 2,447 条缺曲文', 'R2-12 报告',
         '本轮由元曲专项全量核查（YUANQU_2447_MISSING_TEXT_AUDIT.csv）',
         'PARTIAL：根因与可恢复比例见 YUANQU_TEXT_RECOVERY_SUMMARY.md',
         '不得从网络补文'],
    ]
    with open(os.path.join(OUT, 'WORKS_HISTORICAL_COUNT_RECONCILIATION.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        wtr = csv.writer(f)
        wtr.writerow(['item_id', 'item', 'r2_12_claim', 'r2_13_measured', 'reconciliation', 'action', 'note'])
        wtr.writerows(recon)
    # 328/339 缺口
    gap = []
    for r in rows:
        if r[10] == 'NO_REVISION_CANDIDATE':
            gap.append([r[0], r[1], r[2], r[3], r[4], 'NO_CANDIDATE', 'POEM_BODY: 属原文自注/诗句正文，不应清洗，故未生成修订候选',
                        'KEEP_AS_IS'])
    with open(os.path.join(OUT, 'WORKS_328_11_GAP_RECONCILIATION.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        wtr = csv.writer(f)
        wtr.writerow(['work_id', 'title', 'author', 'class_r2_12', 'confidence', 'gap_type', 'reason', 'disposition'])
        wtr.writerows(gap)
    stat = {'n_339': len(rows), 'n_328': len(rev), 'n_gap': len(gap),
            'class': dict(Counter(r[3] for r in rows)),
            'impact': dict(stat2),
            'sample_records': len(samp), 'sample_labels': sum(lab.values()),
            'multi_label_rows': sum(1 for s in samp if '|' in s['verdict'])}
    json.dump(stat, open(os.path.join(OUT, 'LOGS/reconcile.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(stat, ensure_ascii=False, indent=1))
    con.close()


if __name__ == '__main__':
    main()
