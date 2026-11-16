# TEST_RESULTS —— R2-03-R1 实际验证记录

所有结果均来自真实执行，失败与误判一并保留。

| # | 命令 / 操作 | 退出码 | 实际输出要点 |
|---|---|---:|---|
| 1 | `python3 ~/.workbuddy/skills/paddleocr-vl/scripts/paddleocr_vl.py check`（首次） | 0 | `isCloudApi=true`, `token.configured=false`, `ready=false` |
| 2 | 全盘检索历史凭据（58 个文件） | 0 | 未找到 AI Studio token；会话里的 43 字符 token 属内置 VLM 代理 |
| 3 | `paddle_rerun.py plan` | 0 | 3 本待重跑；286 疑似页（**后证明含重复填充虚增，已修正**）；`ready=false` |
| 4 | `paddleocr_vl.py run ... --dry-run` | 0 | 列出 3 个待上传文件，`tokenConfigured=false`，未联网 |
| 5 | `setup-token --stdin` | 0 | `ok=true`, `mode=0600`, `tokenLength=40` |
| 6 | `check`（复检） | 0 | `ready=true`，`token.source=~/.workbuddy/.credentials/paddleocr_vl.json` |
| 7 | `ls -l` 凭据文件 | 0 | `-rw-------`（0600） |
| 8 | `python3 -m py_compile tools/paddle_rerun.py` | 0 | OK（多次，含修改后复检） |
| 9 | `paddle_rerun.py all --allow-upload` | 0 | 3 任务全 OK：432 + 476 + 783 = 1,691 页，0 失败，26 m 10 s |
| 10 | 任务 1 `114676397850828800` | 0 | 432 页，空页 7，图片 4 |
| 11 | 任务 2 `114676687443656704` | 0 | 476 页，空页 1，图片 13，608.5 s |
| 12 | 任务 3 `114679491062239232` | 0 | 783 页，空页 1，图片 4，729.8 s |
| 13 | `paddle_rerun.py compare`（首版） | 0 | 1,691 页对照；均值相似 0.253 / 0.207 / 0.340 |
| 14 | `paddle_rerun.py ingest`（首版） | 0 | 1,691 + 1,691 行 |
| 15 | 自测：`compare` / `ingest` 指向临时库 | **1（首次）** | `no such table: ocr_runs` → 补自包含建表 |
| 16 | 自测重跑 | 0 | 2 页对照、2 行入库、engine 校验通过 |
| 17 | `paddle_rerun.py compare`（加 han_ratio / circled） | 0 | 汉字相似 0.322 / 0.230 / 0.314 |
| 18 | `paddle_rerun.py ingest`（幂等重跑） | 0 | 1,691 行；`ocr_runs` 仍 3 条；18 列 |
| 19 | 页码偏移诊断 | 0 | 曾显示 +3～+15 → **后判定为假象，已撤回** |
| 20 | 下载 API 原始 jsonl ×3 | 0 | 分片 144×3 / 119×4 / 195×4+3，总数与 PDF 页数一致 |
| 21 | `paddle_align.py`（逐页贪心） | 0 | 覆盖 20.1% / 8.6% / 6.8% |
| 22 | `paddle_align.py`（降序贪心） | 0 | 覆盖率未改善，偏移全 +0 → 引出数据完整性怀疑 |
| 23 | 相邻重复页检验 | 0 | **Vision 337 / 431 / 719 页重复；Paddle 全 0** |
| 24 | 去重后符号统计 | 0 | 误识 93→5；入声点 0→4,368；⑨/⑩ 482 次 |
| 25 | pymupdf 渲染 PDF p35 / p100 / p200 | 0 | 3 张 PNG（110 dpi） |
| 26 | 原图人工核验 | 0 | 三页均与 Paddle 同号页吻合 → 页序正确 |
| 27 | `python3 -m py_compile tools/paddle_align.py` | 0 | OK |
| 28 | `python3 -m py_compile tools/finalize_r2_03_r1.py` | 0 | OK |
| 29 | `finalize_r2_03_r1.py` | 0 | `baseline_valid` 1,691 行全 0；7 条发现；两个 JSON 标记 INVALID |
| 30 | 数据库终检 | 0 | `book_pages` 2,010（未动）；`book_pages_paddle` 1,691；engine 单一 |

## 失败与误判（保留）

1. 第 15 项：临时库缺 `ocr_runs` 表 → 脚本改为自包含 `CREATE TABLE IF NOT EXISTS`。
2. 第 19 项：把 Vision 重复填充造成的匹配失真，误判为「PaddleOCR 页码漂移」→ 经原图核验撤回，
   `alignment.json` 标记 `INVALID`。
3. 第 21–22 项：两次对齐尝试覆盖率均低，最终根因是基线数据损坏，非算法阈值问题。
4. 第 3 项的「286 疑似页」按名义页统计，含重复填充虚增 → 在 `ERRATA.md` §2 修正为
   「《诗词格律》94 份不同文本中 19 份命中」。

## 未做的验证（如实登记）

- 未对全部 1,691 页逐页与影印原图核对（只核 3 页页序 + 若干符号页）。
- 未验证 4,368 处入声点 LaTeX 标记逐字准确。
- 未回查 16 条 `theory_claims` 的引文与页码。
