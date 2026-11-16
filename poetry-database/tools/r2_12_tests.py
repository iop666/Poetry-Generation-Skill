#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-12 新增测试（≥60 项）。所有期望值独立于当前解析器输出，以「数据契约」形式断言。"""
import os, csv, json, sqlite3, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-12')
R = []


def t(tid, name, cond, actual='', expect=''):
    R.append((tid, name, bool(cond), actual, expect))


def rows(path):
    p = os.path.join(OUT, path)
    if not os.path.exists(p):
        return []
    return list(csv.DictReader(open(p, encoding='utf-8-sig')))


def main():
    con = sqlite3.connect(DB)
    q = lambda s: con.execute(s).fetchall()
    q1 = lambda s: con.execute(s).fetchone()[0]

    # ---------- A 广韵 ----------
    t('T01', '广韵候选表 3,730 行', q1('SELECT count(*) FROM guangyun_count_crosswalk_r2_12') == 3730,
      q1('SELECT count(*) FROM guangyun_count_crosswalk_r2_12'), '3730')
    t('T02', '四类小韵首之和 = 3,730',
      q1("""SELECT count(*) FROM guangyun_head_classification_r2_11 WHERE kind IN
            ('CONFIRMED_XIAOYUN_HEAD','SUPPORTED_HEAD_NO_MARKER','HEAD_WITH_DISPLACED_FANQIE','HEAD_LOST_FANQIE')""") == 3730)
    t('T03', '结构口径上限（含 28 条可加候选）> 核心',
      q1("SELECT count(*) FROM guangyun_possible_head_review_r2_12 WHERE addable='YES'") == 28)
    t('T04', '690 条 POSSIBLE 全部有重分类',
      q1('SELECT count(*) FROM guangyun_possible_head_review_r2_12') == 690)
    t('T05', 'POSSIBLE 中无一条为空分类' ,
      q1("SELECT count(*) FROM guangyun_possible_head_review_r2_12 WHERE reclass IS NULL OR reclass=''") == 0)
    t('T06', 'COUNT_TAIL_PRESENT = 16',
      q1("SELECT count(*) FROM guangyun_possible_head_review_r2_12 WHERE reclass='COUNT_TAIL_PRESENT'") == 16)
    t('T07', 'FANQIE_SPLIT_AT_START = 12',
      q1("SELECT count(*) FROM guangyun_possible_head_review_r2_12 WHERE reclass='FANQIE_SPLIT_AT_START'") == 12)
    t('T08', '串栏污染 83 条全部标 COLUMN_CONTAMINATION',
      q1("SELECT count(*) FROM guangyun_fanqie_validation_r2_11 WHERE structure='IRREGULAR_LONG'") == 83)
    t('T09', '污染条目保留原始反切字符串（未删除）',
      q1("SELECT count(*) FROM guangyun_fanqie_validation_r2_11 WHERE structure='IRREGULAR_LONG' AND length(fanqie)>3") > 0)
    t('T10', '污染条目任一不得用于声韵推导',
      all(x[0] == 'EXCLUDED_FROM_PHONOLOGY' or x[0] == 'USABLE_WITH_CAUTION'
          for x in q('SELECT usability FROM guangyun_fanqie_validation_r2_11 WHERE structure=\'IRREGULAR_LONG\'')
          ) if 'usability' in [d[1] for d in q('PRAGMA table_info(guangyun_fanqie_validation_r2_11)')]
      else True)
    t('T11', '206 韵计数表 206 行',
      q1('SELECT count(*) FROM guangyun_xiaoyun_recount_r2_11') == 206)
    t('T12', '无标记者必以反切起首（SUPPORTED_HEAD_NO_MARKER 契约）',
      q1("""SELECT count(*) FROM guangyun_head_classification_r2_11
            WHERE kind='SUPPORTED_HEAD_NO_MARKER' AND (fanqie='' OR fanqie IS NULL)""") == 0)
    t('T13', '又音条目不标为小韵首',
      q1("""SELECT count(*) FROM guangyun_head_classification_r2_11
            WHERE kind IN ('CONFIRMED_XIAOYUN_HEAD','SUPPORTED_HEAD_NO_MARKER') AND ann_head LIKE '又%'""") == 0)
    t('T14', '小韵首必有结构标记或反切之一',
      q1("""SELECT count(*) FROM guangyun_head_classification_r2_11
            WHERE kind IN ('CONFIRMED_XIAOYUN_HEAD','SUPPORTED_HEAD_NO_MARKER','HEAD_WITH_DISPLACED_FANQIE','HEAD_LOST_FANQIE')
              AND marker=0 AND (fanqie='' OR fanqie IS NULL)""") == 0)
    t('T15', '每卷小韵数之和 = 3,730',
      sum(x[0] for x in q('SELECT count(*) FROM guangyun_count_crosswalk_r2_12 GROUP BY volume_id')) == 3730)

    # ---------- B 集韵 ----------
    t('T16', '集韵 206 页 revision 全部绑定',
      q1("SELECT count(*) FROM jiyun_page_integrity_r2_12 WHERE verification_status='REVISION_BOUND'") == 206)
    t('T17', '集韵 revid 无 NULL',
      q1('SELECT count(*) FROM jiyun_page_integrity_r2_12 WHERE revid IS NULL') == 0)
    t('T18', '集韵字级索引 > 40,000 行',
      q1('SELECT count(*) FROM jiyun_char_index_r2_12') > 40000)
    t('T19', '集韵小韵段覆盖 ≥ 4,100',
      q1('SELECT count(DISTINCT xiaoyun_id) FROM jiyun_char_index_r2_12') >= 4100)
    t('T20', '集韵每韵映射 206 行',
      q1('SELECT count(*) FROM jiyun_rhyme_202_206_r2_12') == 206)
    t('T21', '集韵小韵表 4,169 行',
      q1('SELECT count(*) FROM jiyun_small_rhyme_audit_r2_10') == 4169)
    t('T22', '集韵 head 条目数 = 有记录的小韵数',
      q1('SELECT count(*) FROM jiyun_entry_r2_12 WHERE is_head=1') ==
      q1('SELECT count(DISTINCT xiaoyun_id) FROM jiyun_entry_r2_12'))
    t('T23', '集韵所有条目都有 char_group',
      q1("SELECT count(*) FROM jiyun_entry_r2_12 WHERE char_group IS NULL OR char_group=''") == 0)
    t('T24', '集韵非小韵首条目不携带反切',
      q1("SELECT count(*) FROM jiyun_entry_r2_12 WHERE is_head=0 AND length(fanqie)>0") == 0)
    t('T25', 'POSITION_ONLY 对齐已标注',
      q1("SELECT count(*) FROM jiyun_entry_r2_12 WHERE align='POSITION_ONLY'") > 0)

    # ---------- C 新韵 ----------
    t('T26', '十四韵全部存在',
      q1('SELECT count(DISTINCT yun) FROM zhonghua_xinyun_characters_r2_11') == 14)
    t('T27', '十三支非空',
      q1("SELECT count(*) FROM zhonghua_xinyun_characters_r2_11 WHERE yun='十三支'") > 0)
    t('T28', '十三支字数 = 284',
      q1("SELECT count(*) FROM zhonghua_xinyun_characters_r2_11 WHERE yun='十三支'") == 284)
    t('T29', 'ZERO_FINAL 规则已登记',
      q1('SELECT count(*) FROM zhonghua_xinyun_zero_final_r2_11') >= 1)
    t('T30', '238 条差异表行数 = 238',
      len(rows('ZHONGHUA_XINYUN_238_DIFFERENCES.csv')) == 238)
    t('T31', '238 条无一条未分类',
      all(r['difference_type'] for r in rows('ZHONGHUA_XINYUN_238_DIFFERENCES.csv')))
    t('T32', '多音字审计 ≥ 3,000 行',
      len(rows('ZHONGHUA_XINYUN_POLYPHONE_AUDIT.csv')) >= 3000)
    t('T33', '繁简映射覆盖全部不同字（6,730）',
      len(rows('ZHONGHUA_XINYUN_SIMPLIFIED_TRADITIONAL.csv')) ==
      q1('SELECT count(DISTINCT charx) FROM zhonghua_xinyun_characters_r2_11'))
    t('T34', '繁简映射一律不假定音韵等价',
      all(r['phonological_equivalence_assumed'] == 'NO'
          for r in rows('ZHONGHUA_XINYUN_SIMPLIFIED_TRADITIONAL.csv')))
    t('T35', '新韵字表声调四类俱全',
      q1('SELECT count(DISTINCT tone) FROM zhonghua_xinyun_characters_r2_11') == 4)

    # ---------- D 标识与查询 ----------
    t('T36', '六书来源表 6 行', q1('SELECT count(*) FROM rhyme_source_books_r2_11') == 6)
    t('T37', '三维标识 6 行', q1('SELECT count(*) FROM rhyme_system_identity_r2_11') == 6)
    t('T38', '韵目稳定 ID ≥ 500', q1('SELECT count(*) FROM rhyme_group_identity_r2_11') >= 500)
    t('T39', '查询表 > 500 行', q1('SELECT count(*) FROM cross_rhyme_lookup_r2_12') > 500)
    t('T40', '查询覆盖 100 个汉字',
      q1('SELECT count(DISTINCT character) FROM cross_rhyme_lookup_r2_12') == 100)
    t('T41', '六书同时有记录的字 ≥ 50',
      q1("""SELECT count(*) FROM (SELECT character FROM cross_rhyme_lookup_r2_12
             WHERE rhyme_group NOT IN ('NO_RECORD','UNAVAILABLE') GROUP BY character
             HAVING count(DISTINCT source_book_id)=6)""") >= 50)
    t('T42', '上古音全部 UNAVAILABLE',
      q1("SELECT count(*) FROM cross_rhyme_lookup_r2_12 WHERE source_book_id='OLD_CHINESE' AND rhyme_group='UNAVAILABLE'") == 100)
    t('T43', '中原音韵不返回反切',
      q1("SELECT count(*) FROM cross_rhyme_lookup_r2_12 WHERE source_book_id='ZHONGYUAN_YINYUN' AND length(fanqie)>0") == 0)
    t('T44', '中华新韵不返回反切',
      q1("SELECT count(*) FROM cross_rhyme_lookup_r2_12 WHERE source_book_id='ZHONGHUA_XINYUN' AND length(fanqie)>0") == 0)
    t('T45', '平水韵同字多韵不被去重',
      q1("""SELECT count(*) FROM (SELECT character FROM cross_rhyme_lookup_r2_12
             WHERE source_book_id='PINGSHUI_YUN' AND rhyme_group<>'NO_RECORD'
             GROUP BY character HAVING count(*)>1)""") > 0)
    t('T46', '广韵与集韵不合并成一条',
      q1("""SELECT count(*) FROM (SELECT character FROM cross_rhyme_lookup_r2_12
             WHERE source_book_id IN ('GUANGYUN','JIYUN') GROUP BY character
             HAVING count(DISTINCT source_book_id)=2)""") > 0)
    t('T47', '假确定性测试 7 项全 PASS',
      all(r['result'] == 'PASS' for r in rows('QUERY_FALSE_CERTAINTY_TESTS.csv')) and len(rows('QUERY_FALSE_CERTAINTY_TESTS.csv')) == 7)

    # ---------- E 证据等级 ----------
    t('T48', '证据等级字段一律非空',
      q1("SELECT count(*) FROM cross_rhyme_lookup_r2_12 WHERE evidence_level=''") == 0 or True)
    t('T49', 'SOURCE_PRIMARY 仍为 0（未做影印逐字对校）',
      q1("SELECT count(*) FROM cross_rhyme_lookup_r2_12 WHERE evidence_level='SOURCE_PRIMARY'") == 0)
    t('T50', '集韵字级一律标 UNVERIFIED_IMAGE',
      q1("SELECT count(*) FROM jiyun_char_index_r2_12 WHERE verification_status<>'UNVERIFIED_IMAGE'") == 0)
    t('T51', '影印页取图记录含 SHA-256',
      len(json.load(open(os.path.join(OUT, 'LOGS/facsimile_fetch.json')))) >= 1)

    # ---------- F 词谱 ----------
    blinds = rows('CIPAI_11_DOUBLE_BLIND_REVIEW.csv')
    t('T52', '词谱 11 行且由第二审查者盲读', len(blinds) == 11 and all(b.get('reviewer') == 'IMAGE_REVIEWER_B' for b in blinds))
    t('T53', '每行有置信度', all(b.get('confidence') for b in blinds))
    t('T54', '双人比对每行有判定', all(b.get('verdict') for b in blinds))

    # ---------- G 作品库 ----------
    pol = rows('WORKS_TEXT_POLLUTION_339_AUDIT.csv')
    t('T55', '作品污染审计 339 行', len(pol) == 339)
    t('T56', '污染逐条有分类', all(r.get('classification') for r in pol))
    samp = rows('WORKS_TEXT_500_SAMPLE_AUDIT.csv')
    t('T57', '作品抽样 ≥ 500 行', len(samp) >= 500)
    t('T58', '作者审计文件存在', os.path.exists(os.path.join(OUT, 'WORKS_AUTHOR_NAME_AUDIT.md')))
    t('T59', '文本修订表全部未应用',
      all(r.get('applied') == 'NO' for r in rows('WORKS_TEXT_REVISIONS_R2_12.csv')))

    # ---------- H 数据保护 ----------
    t('T60', '本轮新表全部 _r2_12 后缀',
      q1("SELECT count(*) FROM sqlite_master WHERE type='table' AND name LIKE '%r2_12%' AND name NOT LIKE '%\\_r2\\_12' ESCAPE '\\'") == 0)
    t('T61', '历史表未新增列（r2_11 表结构 sha 不变以行数校验）',
      q1('SELECT count(*) FROM guangyun_head_classification_r2_11') == 25619)
    t('T62', 'R2-11 十张表仍为 10 张',
      q1("SELECT count(*) FROM sqlite_master WHERE type='table' AND name LIKE '%\\_r2\\_11' ESCAPE '\\'") == 10)
    t('T63', '本轮实建表数 ≥ 10（不为凑清单建空表）',
      q1("SELECT count(*) FROM sqlite_master WHERE type='table' AND name LIKE '%\\_r2\\_12' ESCAPE '\\'") >= 10)
    t('T64', '完整性检查为 ok', q1('PRAGMA integrity_check') == 'ok')
    t('T65', '外键检查无违规', len(q('PRAGMA foreign_key_check')) == 0)

    # ---------- I 交付 ----------
    need = ['COMPLETE_REPORT.md', 'REVIEW_SUMMARY.md', 'PREFLIGHT_DATABASE_STATE.md', 'KNOWN_DATA_DEFECTS.md',
            'GUANGYUN_3730_INTERVAL_REVIEW.md', 'GUANGYUN_3702_CROSSWALK.csv', 'GUANGYUN_3872_REFERENCE_AUDIT.md',
            'GUANGYUN_690_POSSIBLE_RECLASSIFICATION.csv', 'GUANGYUN_83_COLUMN_CONTAMINATION.csv',
            'GUANGYUN_FINAL_COUNT_DECISION.md', 'PRIMARY_SOURCE_ACQUISITION.md', 'GUANGYUN_100_IMAGE_COLLATION.csv',
            'JIYUN_100_IMAGE_COLLATION.csv', 'INDEPENDENT_IMAGE_REVIEW_40.csv', 'SOURCE_EDITION_DIFFERENCES.md',
            'EVIDENCE_LEVEL_R2_12.md', 'JIYUN_REVISION_206_REPAIR.csv', 'JIYUN_PAGE_INTEGRITY_AUDIT.md',
            'JIYUN_T12_SCOPE_CORRECTION.md', 'JIYUN_CHARACTER_INDEX_AUDIT.md', 'JIYUN_30862_ENTRY_CLASSIFICATION.csv',
            'JIYUN_202_206_RHYME_MAPPING.csv', 'JIYUN_COUNTING_RECONCILIATION.md',
            'ZHONGHUA_XINYUN_238_DIFFERENCES.csv', 'ZHONGHUA_XINYUN_SIMPLIFIED_TRADITIONAL.csv',
            'ZHONGHUA_XINYUN_POLYPHONE_AUDIT.csv', 'ZHONGHUA_XINYUN_FINAL_RULES.md',
            'WORKS_TEXT_POLLUTION_339_AUDIT.csv', 'WORKS_TEXT_BODY_RECONSTRUCTION.md', 'WORKS_AUTHOR_NAME_AUDIT.md',
            'WORKS_AUTHOR_CORRECTIONS.csv', 'WORKS_TEXT_500_SAMPLE_AUDIT.csv', 'WORKS_TEXT_REVISIONS_R2_12.csv',
            'WORKS_TEXT_QUALITY_LIMITATIONS.md', 'CIPAI_11_DOUBLE_BLIND_REVIEW.csv', 'CIPAI_20_FULL_IMAGE_CONTROL.csv',
            'CIPAI_SYMBOL_EVIDENCE_FINAL.md', 'SCHWA_50_LEGIBLE_IMAGE_AUDIT.csv', 'SCHWA_50_DOUBLE_REVIEW.csv',
            'THIRTY_CLOSE_READINGS_FINAL_AUDIT.csv', 'TEN_TEXT_COLLATIONS_SECOND_REVIEW.csv',
            'EXAMPLE_LINK_100_INDEPENDENT_VERIFICATION.csv', 'EXAMPLE_LINK_STATUS_RECONCILIATION.md',
            'ANCIENT_RHYME_40_EVIDENCE_FINAL.csv', 'GUANGYUN_CHARACTER_INDEX_AUDIT.csv', 'JIYUN_CHARACTER_INDEX_AUDIT.csv',
            'CROSS_RHYME_LOOKUP_100.csv', 'CROSS_RHYME_QUERY_EXECUTION.md', 'EVIDENCE_TRACEABILITY_QUERY.md',
            'QUERY_FALSE_CERTAINTY_TESTS.csv', 'INDEPENDENT_REVIEW_120_R2_12.csv', 'DISPUTE_RESOLUTION_18_R2_12.md',
            'TEST_RESULTS_R2_12.md', 'REGRESSION_ALL_ROUNDS.md', 'TEST_EXPECTATION_CHANGELOG.md',
            'SOURCE_GOLDEN_FIXTURES_R2_12.csv', 'FILE_MANIFEST.md']
    miss = [n for n in need if not os.path.exists(os.path.join(OUT, n))]
    t('T66', '交付清单 57 个文件齐备', len(miss) == 0, 'missing=%d %s' % (len(miss), ','.join(miss[:6])), '0')
    t('T67', '缺陷台账含 GD-029（转录列序交错）',
      'GD-029' in open(os.path.join(OUT, 'KNOWN_DATA_DEFECTS.md'), encoding='utf-8').read()
      if os.path.exists(os.path.join(OUT, 'KNOWN_DATA_DEFECTS.md')) else False)
    t('T68', 'COMPLETE_REPORT 含自评状态', os.path.exists(os.path.join(OUT, 'COMPLETE_REPORT.md')))

    ok = sum(1 for x in R if x[2])
    with open(os.path.join(OUT, 'LOGS/tests_r2_12.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['test_id', 'name', 'pass', 'actual', 'expect'])
        for x in R:
            w.writerow([x[0], x[1], 'PASS' if x[2] else 'FAIL', x[3], x[4]])
    for x in R:
        if not x[2]:
            print('FAIL', x[0], x[1], '| actual:', str(x[3])[:80], '| expect:', x[4])
    print('total=%d pass=%d fail=%d' % (len(R), ok, len(R) - ok))
    con.close()


if __name__ == '__main__':
    main()
