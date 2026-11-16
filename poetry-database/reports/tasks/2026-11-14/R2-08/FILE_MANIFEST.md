# 文件清單與校驗（R2-08）

## 一、資料檔（`poetry-database/raw/r2_08/`）

| 檔案 | 大小(B) | SHA-256 前 16 位 |
|---|---|---|
| reading_records_all.jsonl | 847414 | 7b2aa28a12272cda… |
| reading_verification.json | 29497 | 0b1156f5dd78b84b… |
| page_ledger.json | 166780 | e9f905d95e4fd327… |
| schwa_index.json | 288883 | 8f2b1535b370a143… |
| jiyun_xiaoyun.jsonl | 2498077 | 28d7109bace51da3… |
| jiyun_stats.json | 709 | 7bb9d816ec6e2345… |
| jiyun_manifest.json | 3196 | 10aa64b9b96b1362… |
| guangyun_xiaoyun.jsonl | 6933428 | 0d702110f73ea0eb… |
| guangyun_yunmu.json | 24406 | 0313e2d0c4122b52… |
| guangyun_audit.json | 2401 | acc3e16dc0786be7… |
| ph_audit.json | 421 | f437432949915252… |
| cipai_audit.json | 191198 | 8df4e9cd7042a498… |
| cipai_examples.jsonl | 202645 | ada5ba435a5d16b8… |
| cipai_examples_stats.json | 943 | 3741af88ca2e8a7c… |
| example_links.json | 107920 | 119feadf7ad6384f… |
| rhyme_mode_cases.json | 156320 | 47efded20e5c518d… |
| works_study.json | 44912 | 2d7bf56fdeff6ba6… |
| image_sample.json | 20005 | 9388cf2ac59fdba3… |
| band_manifest.json | 11910 | a343a6871123303c… |
| test_results.json | 11452 | 2d388e8b0cb521cd… |

另有：
- `jiyun_pages/`：集韻韻頁 206 個 JSON
- `cache/`：API 響應緩存
- `images/`：詞格原圖 60 張（300dpi）
- `bands/`：譜行裁切拼圖 30 張
- `zhongyuan/`：中原音韻正文
- `branches/`：18 個閱讀單元的原始記錄

## 二、工具（`poetry-database/tools/`）

| 腳本 | 大小(B) | SHA-256 前 16 位 |
|---|---|---|
| r2_08_bands.py | 2952 | 6ebfcc0ff3721160… |
| r2_08_cipai_audit.py | 11189 | 945651ff5cf599c3… |
| r2_08_example_links.py | 6253 | 8f0004872ca035f7… |
| r2_08_examples.py | 7863 | 9afca97b159b582a… |
| r2_08_guangyun.py | 7126 | 94109f259525702d… |
| r2_08_image_sample.py | 5472 | 7e3775ca1f228757… |
| r2_08_jiyun_fetch.py | 7929 | 3d09d8e36ebca1e5… |
| r2_08_jiyun_parse.py | 6939 | 2c95dfd94f79819f… |
| r2_08_page_ledger.py | 2963 | 65b7098cd3018f61… |
| r2_08_reports.py | 32638 | b86862a72e7cab93… |
| r2_08_rhyme_books.py | 13416 | 89fad94a27eb15c5… |
| r2_08_rhyme_cases.py | 7530 | 2c01a65d809c6912… |
| r2_08_schwa.py | 5605 | 3f24d218316e496c… |
| r2_08_tests.py | 11254 | 09cb86ab6820bf14… |
| r2_08_verify_reading.py | 7695 | e4cf7aa88a2e98b3… |
| r2_08_works_study.py | 19166 | adb104e3b8201b5a… |

## 三、資料庫新增表（12）

`cipai_audit2_r2_08`、`cipai_form_examples_r2_08`、`cipai_image_checks_r2_08`、`cipai_rhyme_dual_r2_08`、`classical_works_study_r2_08`、`example_work_links_r2_08`、`ph_audit_r2_08`、`ph_readings_r2_08`、`ph_rhyme_groups_r2_08`、`ph_systems_r2_08`、`ph_variants_r2_08`、`rhyme_mode_cases_r2_08`

未改動：`cipai_specs`(76)、`cipai_forms_r2_07`(196)、`works`(375,399)、`book_pages_paddle`(1,691)、`gedou.py`。
