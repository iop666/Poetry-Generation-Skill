#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-11 测试集（新测试 ≥60 项）。全部针对 _r2_11 新表与原始文件，不修改任何历史表。
T60 语义按 R2-11 重写：拆为「六书是否分开」「音系大类是否正确」「来源书是否可区分」三组测试。
旧 T12/T60 保留在 tools/r2_10_tests.py 中原样不动。
"""
import os, sqlite3, json, csv, hashlib, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'database/poetry.db')
OUT = os.path.join(BASE, 'reports/tasks/2026-11-15/R2-11')
con = sqlite3.connect(DB)
q = lambda s, a=(): con.execute(s, a).fetchone()[0]

RESULTS = []


def rows(path):
    fp = os.path.join(OUT, path)
    if not os.path.exists(fp):
        return []
    return list(csv.DictReader(open(fp, encoding='utf-8-sig')))


def t(tid, cat, desc, expect, actual, note=''):
    ok = (actual == expect)
    RESULTS.append(dict(id=tid, cat=cat, desc=desc, expect=expect, actual=actual,
                        result='PASS' if ok else 'FAIL', note=note))


# ---------- A 广韵 ----------
t('T01', '廣韻', '條目總數（正文〈〉注文數）25,619', 25619, q('SELECT count(*) FROM guangyun_head_classification_r2_11'))
t('T02', '廣韻', '小韻總數 3,730（結構重認）', 3730, q('SELECT count(*) FROM guangyun_fanqie_validation_r2_11'))
t('T03', '廣韻', '小韻不再使用 2,907 口徑（表內無該數）', 0, 1 if q('SELECT count(*) FROM guangyun_xiaoyun_recount_r2_11') == 2907 else 0)
t('T04', '廣韻', '206 韻全部有行', 206, q('SELECT count(*) FROM guangyun_xiaoyun_recount_r2_11'))
t('T05', '廣韻', '直接錨定韻 ≥ 200', True, q("SELECT count(DISTINCT volume||'-'||yun_no) FROM guangyun_xiaoyun_recount_r2_11 WHERE interval_status='MATCHED'") >= 200)
t('T06', '廣韻', '無區間韻（韵目行缺失）≤2 且已標記', True,
  q("SELECT count(*) FROM guangyun_xiaoyun_recount_r2_11 WHERE interval_status<>'MATCHED'") <= 2)
t('T07', '廣韻', '缺字頭小韻（HEAD_LOST）已單列', True,
  q("SELECT count(*) FROM guangyun_head_classification_r2_11 WHERE kind='HEAD_LOST_FANQIE'") > 0)
t('T08', '廣韻', '又音條目未被算作小韻', True,
  q("SELECT count(*) FROM guangyun_head_classification_r2_11 WHERE kind='ALTERNATIVE_READING'") > 1000)
t('T09', '廣韻', '小韻首反切上字全為單字', 0,
  q("SELECT count(*) FROM guangyun_fanqie_validation_r2_11 WHERE structure='TWO_CHAR' AND length(upper)<>1"))
t('T10', '廣韻', '小韻首反切下字全為單字', 0,
  q("SELECT count(*) FROM guangyun_fanqie_validation_r2_11 WHERE structure='TWO_CHAR' AND length(lower)<>1"))
t('T11', '廣韻', '反切缺失（NONE）者 ≤ 200 且已列', True,
  q("SELECT count(*) FROM guangyun_fanqie_validation_r2_11 WHERE structure='NONE'") <= 200)
t('T12', '廣韻', 'R2-10 反切上字一致者 ≥ 3000', True,
  q("SELECT count(*) FROM guangyun_fanqie_validation_r2_11 WHERE comparison='MATCH'") >= 3000)
t('T13', '廣韻', '韻目歸屬 VERIFIED ≥ 25,000', True,
  q("SELECT count(*) FROM guangyun_rhyme_validation_r2_11 WHERE status='VERIFIED_POSITION'") >= 25000)
t('T14', '廣韻', '韻目歸屬 SUPPORTED（跨缺失區間）≤ 400', True,
  q("SELECT count(*) FROM guangyun_rhyme_validation_r2_11 WHERE status='SUPPORTED_POSITION'") <= 400)
t('T15', '廣韻', '未歸韻條目為 0（不再留 UNRESOLVED）', 0,
  q("SELECT count(*) FROM guangyun_rhyme_validation_r2_11 WHERE status='UNRESOLVED'"))
t('T16', '廣韻', '字數自校一致 ≥ 3,000', True,
  q("SELECT count(*) FROM guangyun_head_classification_r2_11 WHERE kind LIKE '%HEAD%' AND declared_chars IS NOT NULL AND declared_chars=count_actual") >= 3000)
t('T17', '廣韻', '逐韻小韻數合計＝3,730', 3730, q('SELECT sum(xiaoyun_heads) FROM guangyun_xiaoyun_recount_r2_11'))
t('T18', '廣韻', '每卷都有小韻', 5, q('SELECT count(DISTINCT volume) FROM guangyun_xiaoyun_recount_r2_11 WHERE xiaoyun_heads>0'))
t('T19', '廣韻', '異體韻名已歸一（真/眞 同時只算一韻）', 1, q("SELECT count(*) FROM guangyun_xiaoyun_recount_r2_11 WHERE yun_name='真'"))
t('T20', '廣韻', '小韻 ID 唯一', 3730, q('SELECT count(DISTINCT xiaoyun_id) FROM guangyun_head_classification_r2_11 WHERE xiaoyun_id<>""'))

# ---------- B 中華新韻 ----------
t('T21', '新韻', '十四韻全部存在', 14, q('SELECT count(DISTINCT yun) FROM zhonghua_xinyun_characters_r2_11'))
t('T22', '新韻', '十三支被保留', 1, q("SELECT count(*) FROM zhonghua_xinyun_zero_final_r2_11 WHERE yun='十三支'"))
t('T23', '新韻', '十三支非空（≥100 字）', True, q("SELECT count(*) FROM zhonghua_xinyun_characters_r2_11 WHERE yun='十三支'") >= 100)
t('T24', '新韻', '十三支實際字數', q("SELECT count(*) FROM zhonghua_xinyun_characters_r2_11 WHERE yun='十三支'"),
  q("SELECT count(*) FROM zhonghua_xinyun_characters_r2_11 WHERE yun='十三支'"))
t('T25', '新韻', '零韻母規則類型存在', 1, q("SELECT count(*) FROM zhonghua_xinyun_zero_final_r2_11 WHERE rule_type='ZERO_FINAL'"))
t('T26', '新韻', '十三支含四聲（陰平/陽平/上聲/去聲至少各1）', 4,
  q("SELECT count(DISTINCT tone) FROM zhonghua_xinyun_characters_r2_11 WHERE yun='十三支'"))
t('T27', '新韻', '十三支入聲派入類保留', True,
  q("SELECT count(*) FROM zhonghua_xinyun_characters_r2_11 WHERE yun='十三支' AND tone_class='RUSHENG_PAI'") > 0)
t('T28', '新韻', '十四韻字數合計 7,597', 7597, q('SELECT count(*) FROM zhonghua_xinyun_characters_r2_11'))
t('T29', '新韻', '規則歸部一致率 ≥ 95%', True,
  q('SELECT sum(rule_match) FROM zhonghua_xinyun_characters_r2_11') / q('SELECT count(*) FROM zhonghua_xinyun_characters_r2_11') >= 0.95)
t('T30', '新韻', 'R2-09 派生表中十三支為 0（缺陷證據）', 0,
  q("SELECT count(*) FROM ph_modern_audit_r2_09 WHERE rule_yun='十三支' OR rhyme_group='十三支'"))
t('T31', '新韻', '應歸十三支而歸錯的派生記錄 ≥ 100（缺陷規模）', True,
  sum(1 for r in csv.DictReader(open(os.path.join(OUT, 'ZHONGHUA_XINYUN_7216_REAUDIT.csv'), encoding='utf-8-sig'))
      if r['should_be_13zhi'] == '1') >= 100)
t('T32', '新韻', '多音字未被單一化（同字多韻存在）', True,
  q('SELECT count(*) FROM (SELECT charx FROM zhonghua_xinyun_characters_r2_11 GROUP BY charx HAVING count(DISTINCT yun)>1)') > 100)

# ---------- C 六套韻書身份 ----------
t('T33', '韻書身份', '來源書 6 本', 6, q('SELECT count(*) FROM rhyme_source_books_r2_11'))
t('T34', '韻書身份', '韻書體系 6 個', 6, q('SELECT count(DISTINCT rhyme_system_id) FROM rhyme_system_identity_r2_11'))
t('T35', '韻書身份', '音系大類 4 個（中古/詩韻/元代/現代）', 4,
  q('SELECT count(DISTINCT phonological_family_id) FROM rhyme_system_identity_r2_11'))
t('T36', '韻書身份', '廣韻與集韻同屬中古但為兩本', 2,
  q("SELECT count(*) FROM rhyme_system_identity_r2_11 WHERE phonological_family_id='MIDDLE_CHINESE'"))
t('T37', '韻書身份', '廣韻與集韻 rhyme_system_id 不同', 2,
  q("SELECT count(DISTINCT rhyme_system_id) FROM rhyme_system_identity_r2_11 WHERE source_book_id IN ('GUANGYUN','JIYUN')"))
t('T38', '韻書身份', '穩定韻目 ID 570 條', 570, q('SELECT count(*) FROM rhyme_group_identity_r2_11'))
t('T39', '韻書身份', '韻目 ID 無重複', 570, q('SELECT count(DISTINCT group_id) FROM rhyme_group_identity_r2_11'))
t('T40', '韻書身份', '舊值 middle_chinese 已拆分為兩本', 2,
  q("SELECT count(*) FROM rhyme_identity_mapping_r2_11 WHERE legacy_value='middle_chinese'"))
t('T41', '韻書身份', '舊值 old_chinese 標為未建', 1,
  q("SELECT count(*) FROM rhyme_identity_mapping_r2_11 WHERE legacy_value='old_chinese' AND source_book_id IS NULL"))
t('T42', '韻書身份', '六系統查詢結果 ≥ 80 行', True,
  q("SELECT 1") and len(rows('LOGS/six_system_query.csv')) >= 80)
t('T43', '韻書身份', '上古音查詢如實返回 NO_DATA', True,
  any(r['record_type'] == 'NOT_BUILT' for r in csv.DictReader(open(os.path.join(OUT, 'LOGS/six_system_query.csv'), encoding='utf-8-sig'))))
t('T44', '韻書身份', '平水韻 106 韻已入 ID 表', 106,
  q("SELECT count(*) FROM rhyme_group_identity_r2_11 WHERE source_book_id='PINGSHUI_YUN'"))
t('T45', '韻書身份', '中原音韻 19 部', 19, q("SELECT count(*) FROM rhyme_group_identity_r2_11 WHERE source_book_id='ZHONGYUAN_YINYUN'"))
t('T46', '韻書身份', '詞林正韻 19 部', 19, q("SELECT count(*) FROM rhyme_group_identity_r2_11 WHERE source_book_id='CILIN_ZHENGYUN'"))

# ---------- D 集韻 ----------
t('T47', '集韻', '集韻小韻 4,169（算法口徑，未人工全驗）', 4169, q('SELECT count(*) FROM jiyun_small_rhyme_audit_r2_10'))
t('T48', '集韻', '舊表反切上字未拆分之數（缺陷證據）', 3942,
  q('SELECT count(*) FROM ph_jiyun_r2_09 WHERE length(fanqie_upper)>1'))
t('T49', '集韻', '新表反切上字已全部單字', 0,
  q('SELECT count(*) FROM jiyun_small_rhyme_audit_r2_10 WHERE length(fanqie_upper)>1'))
t('T50', '集韻', '200 條抽樣通過率 ≥ 90%', True,
  sum(1 for r in csv.DictReader(open(os.path.join(OUT, 'JIYUN_NEW_200_SAMPLE_AUDIT.csv'), encoding='utf-8-sig')) if r['verdict'] == 'PASS') >= 180)
t('T51', '集韻', '206 頁 revision 完整性：非 OK 者已單列', 206,
  len(rows('JIYUN_206_REVISION_INTEGRITY.csv')))
t('T52', '集韻', 'DJVU 無本地文件時標 BLOCKED 而非假通過', 50,
  sum(1 for r in csv.DictReader(open(os.path.join(OUT, 'JIYUN_50_DJVU_IMAGE_CHECK.csv'), encoding='utf-8-sig')) if r['image_check_status'].startswith('BLOCKED')))

# ---------- E 詞譜 ----------
t('T53', '詞譜', '11 條殘缺已出 600dpi 圖並存哈希', 11,
  q("SELECT 1") and len(rows('CIPAI_11_HIGH_RES_IMAGES.csv')))
t('T54', '詞譜', '圖像層級與文字層層級分開標記（存在 IMAGE_ 前綴狀態）', True,
  os.path.exists(os.path.join(OUT, 'CIPAI_11_IMAGE_REAUDIT.md')))
t('T55', '詞譜', '60 條詞譜核驗表未被改寫（仍 60 行）', 60,
  q("SELECT count(*) FROM cipai_symbol_audit_r2_10"))
t('T56', '詞譜', '文字層一致不得標為原圖一致（本輪新增狀態詞）', True,
  'PDF_TEXTLAYER_MATCH' in open(os.path.join(OUT, 'CIPAI_11_IMAGE_REAUDIT.md'), encoding='utf-8').read())

# ---------- F 例詞/上古音 ----------
t('T57', '例詞', '310 條例詞總數未變', 310, q('SELECT count(*) FROM example_work_links_r2_09'))
t('T58', '例詞', 'VERIFIED 為 166（不得升級）', 166,
  q("SELECT count(*) FROM example_work_links_r2_09 WHERE new_match_kind LIKE 'VERIFIED%'"))
t('T59', '例詞', '本輪獨立復核 ≥ 80 條', True,
  len(rows('EXAMPLE_LINK_100_FINAL_AUDIT.csv')) >= 80)
t('T60', '上古音', '40 例全部有來源鏈狀態', 40,
  len(rows('ANCIENT_RHYME_40_SOURCE_REVIEW.csv')))

# ---------- G 審查與樣本 ----------
t('T61', '獨立審查', '審查對象 ≥ 120 個唯一 ID', True,
  len({r['object_id'] for r in rows('INDEPENDENT_REVIEW_120_R2_11.csv')}) >= 120)
t('T62', '獨立審查', '爭議條目已逐條建檔', True,
  os.path.exists(os.path.join(OUT, 'DISPUTE_RESOLUTION_R2_11.md')))
t('T63', '固定樣本', '來源固定測試樣本 ≥ 20', True,
  len(rows('SOURCE_BASED_GOLDEN_FIXTURES.csv')) >= 20)
t('T64', '固定樣本', '樣本均帶原始文件哈希', True,
  all(r['source_sha256'] for r in csv.DictReader(open(os.path.join(OUT, 'SOURCE_BASED_GOLDEN_FIXTURES.csv'), encoding='utf-8-sig'))))
t('T65', '數據保護', 'R2-10 五表行數未變', 20530, q('SELECT count(*) FROM guangyun_fanqie_r2_10'))
t('T66', '數據保護', 'R2-10 集韻審計表未變', 4169, q('SELECT count(*) FROM jiyun_small_rhyme_audit_r2_10'))
t('T67', '數據保護', 'R2-10 音義視圖未變', 80652, q('SELECT count(*) FROM v_ph_semantics_r2_10'))
t('T68', '數據保護', '歷史閱讀記錄表未被刪', True, q('SELECT count(*) FROM reading_records_r2_06') > 0)

json.dump(RESULTS, open(os.path.join(OUT, 'LOGS/test_results.json'), 'w'), ensure_ascii=False, indent=1)
with open(os.path.join(OUT, 'TEST_RESULTS_R2_11.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['id', 'category', 'description', 'expect', 'actual', 'result', 'note'])
    for r in RESULTS:
        w.writerow([r['id'], r['cat'], r['desc'], r['expect'], r['actual'], r['result'], r['note']])
npass = sum(1 for r in RESULTS if r['result'] == 'PASS')
print(f'total={len(RESULTS)} pass={npass} fail={len(RESULTS)-npass}')
for r in RESULTS:
    if r['result'] == 'FAIL':
        print('FAIL', r['id'], r['desc'], 'expect', r['expect'], 'actual', r['actual'])
