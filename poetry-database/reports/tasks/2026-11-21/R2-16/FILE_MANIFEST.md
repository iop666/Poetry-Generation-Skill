# FILE_MANIFEST —— R2-16 产出与变更清单（第二轮终版）

- 日期：2026-11-21（第二轮收尾后刷新）
- SHA-256 计算对象为文件最终字节；`FILE_MANIFEST.md` 自身不列哈希（自引用）。
- 项目根（报告与治理文件本体）：`D:\Codex\Poetry-Generation-Skill`；
  **待批准变更集同步副本：`D:\ZCode\zcode\r2_16_workspace\clean-main`（干净克隆，HEAD `37ee224`）。**
- 白名单最终版：**887 个文件**（两份副本一致；干净克隆为今后同步源）。

## 1. 本轮修改 / 新增（项目内）

| 文件 | 状态 | 字节 | SHA-256 |
|---|---|---:|---|
| `poetry-database/tools/github_sync.py` | 修改（v3 严格逐文件白名单，30,299 字节） | 30,299 | `2180d93245505a2c38047ac3070280a69553e67aa3ebfd3e8b0f11461ecc4dc7` |
| `poetry-database/tools/public_files.txt` | 新增（逐文件白名单，887 登记） | — | `c94497fe065594bfbd936f5faf1268d409b5d6cf8c53da3acc988b9fc5b98b30` |
| `poetry-database/tools/public_redactions.json` | 新增（导出时改写规则 4 条） | — | `a98f3c226753be07cf7c84aff7eaf3f06ab8d570ca8a99d90ae80ec9776bb9b6` |
| `poetry-database/tools/make_public_evidence.py` | 新增（公开证据生成器） | — | `b94930d151230f2d23dd0dbca723790f897303da0ed9fa470f941b7acf5ca383` |
| `poetry-database/raw/r2_04_evidence/ocr_samples_public.json` | 新增（WITHHELD 公开版：去 head） | 6,488 | `41ea6237c61dc0fd6342d6fb875103607408a781f9a6a7fd0dd5e99536d91a8e` |
| `poetry-database/raw/r2_04_evidence/theory_locate_public.json` | 新增（WITHHELD 公开版：quote→SHA-256） | 3,941 | `f15cddf48db25f05d49e038cc765ffa5f36de04375456728a12d06a03c1c9c4d` |
| `poetry-database/raw/r2_04_evidence/README_CHARCOUNT.md` | 回填（第一轮，来源公开 main 37ee224，LF） | 1,372 | `ddb4637928f0d2a078afc223687fb85dd628084eca69c15b7dbd5bff54d0f967` |
| `<R16>/COMPLETE_REPORT.md` | 新增（十三章 + 第二轮附录 §14 + §15 推送执行记录） | — | `51a36842413af1bc7f2a710e84e2a8375b575857f34561abe3daf9fc2cfd295c` |
| `<R16>/SOURCE_AUDIT.md` | 新增（R2-16B 逐条审查；含 C 文件 114 字跨度位置更正说明） | — | `41c58fc69e4f3d094193220aa7dcebd2ff0180291249f33350d618fbf4a7fcd2` |
| `<R16>/R2-16C_TEST_RESULTS.md` | 新增（第一轮 TEST_RESULTS.md 按审核要求更名；推送前修订一处测试样例表述，清除本机路径字面量） | — | `2a128714cbf531c24e977f4b0dcea7934ede5cd0ee29c6c2792a3a3de703e525` |
| `<R16>/PUBLIC_TREES_AUDIT.md` | 新增（八棵树文件级审计 + §6 回填登记；推送前同步修订扫描项表述） | — | `0c9389a8af2754bc3be123c2ddd8de3502ae2eb7cd9c252f83b07891e50de81f` |
| `<R16>/FINAL_CHANGE_REPORT.md` | 新增（变更集与远端差异预览 + §5 执行结果） | — | `8e441b229683b3b7d0079ce0fda54b8b1a5f227967b4b0a051ca8572c6853ef3` |
| `<R16>/FILE_MANIFEST.md` | 新增（本文件） | — | — |

## 2. 归档日志（LOGS/，16 件，含保留的失败日志）

| 文件 | SHA-256 |
|---|---|
| `LOGS/run_a_full_sync.log`（v2 首轮完整同步） | `c2e909d9cf088ef9ca989f765cba604623bfd5931bd262f44f185aff0548d438` |
| `LOGS/run_a2_full_sync.log`（v2 修复后完整同步，PUSH OK） | `014c8eb403876a1c41996302832980c783cbae428b9f4db982c5cf200a0f2ab2` |
| `LOGS/verify_t1_t9.log`（**v2 首轮断言 3 FAIL，保留不删**） | `ec331891e8fdd1d225d7010d432fd67e7b2ca7db0fa13581d2181ffeecaa3269` |
| `LOGS/verify_t1_t9_v2.log`（v2 复测 9 PASS） | `21aebf78b74f45f1657ea0e76778d5670844bce1f31e3a4827c4323fe7601907` |
| `LOGS/run_b_hard_abort.log`（v2 硬排除中止，exit 4） | `55b3d30a0de5eb5a95e472e096a513a9cd801dbaba73183bc1ff3349221da877` |
| `LOGS/run_c_dryrun.log`（v2 dry-run 毒饵中止，exit 4） | `55b3d30a0de5eb5a95e472e096a513a9cd801dbaba73183bc1ff3349221da877` |
| `LOGS/run_c2_dryrun.log`（v2 干净 dry-run，exit 0） | `2b8a1c902f006728932eea71a57464053e6a7acdfcc63903cd97e41463dda73e` |
| `LOGS/run_d_real_dryrun.log`（v2 真实项目 dry-run，exit 0） | `ef1273f5bb194a75fceab09b10c65fd1585c44f8108900bab22bdfb4846fb899` |
| `LOGS/run_a3_v3_sync.log`（**v3 沙盒完整同步：默认拒绝/改写/SYNC_DIFF/VERIFY PASS/PUSH OK**） | `965aa6c6c80bb510c6b7265ea40b8cbbc57bb28dec9c87ea232d16471bda0a63` |
| `LOGS/verify_t1_t13_v3.log`（**v3 断言 13 项全 PASS**） | `575398f663f5db68dde08366a14d8684c7a6dff0050ab2c45b718f469b96b40d` |
| `LOGS/run_b_v3_hard_abort.log`（v3 白名单混入硬排除 → exit 4） | `1d50e5f64ca32adaa73f092a24291131f5d1ba192b75ac416a104d6896c42d73` |
| `LOGS/run_c_v3_dryrun.log`（v3 干净 dry-run → exit 0） | `0434233109c171283eb7e4321a562ef0acac4c5b41f151999214adc06a99331e` |
| `LOGS/run_d_v3_withheld_guard.log`（v3 白名单混入暂停公开文件 → exit 4） | `781e8ec8d6fe56cc35ba7e7fcb05e07b02adcf5f26240c71b1d5d639a3893951` |
| `LOGS/tree_risk_scan.log`（八棵树 819 文件风险扫描） | `de52cd464fe12eeae31d50ff74a41209a7b5e13c3764da161b21f4329bbb7c96` |
| `LOGS/quote_stats.log`（引文规模统计） | `7f625cff7c44ba0989cbdf8dac590d3fbe36405a901612d8c9f9a7904c1019a9` |
| `LOGS/redaction_dryrun.log`（真实文件改写模拟 4 条全 PASS） | `a82bdb60e392c02cd9190826279c6064f9bdb1d6bf36aecf4342e4628073ff3f` |
| `LOGS/run_e_clean_dryrun.log`（干净克隆首次 dry-run，发现 37 文件回填需求） | `97c3f1acf27b6b3fe3706237d75c53c84ee8ea32e0ab643405af69eb241c5ddd` |
| `LOGS/run_real_push.log`（**真实同步执行日志：887 导出/VERIFY PASS/PUSH OK**） | `7d4c09c1e626d2d6608fb9312a365c7df029d92970e6cbf24cd728bca2c39fb2` |

工作区日志（不入库）：干净克隆 dry-run 共 3 次（run_e/run_f/run_h）位于
`D:\ZCode\zcode\r2_16_workspace\synctest\logs\`，最终版 `run_h_final_confirm.log`
确认：887 登记 / 默认拒绝 1（ocr_vision）/ 改写规则 4 条 / 暂停公开 2 件 / exit 0。

## 3. 未变更（关键声明）

| 文件 | 状态 | SHA-256 |
|---|---|---|
| `poetry-database/raw/r2_04_evidence/ocr_samples.json` | **本地原件未删未改**（维持 WITHHELD，旧项目目录） | `9b8f11cdf587b1e8b15ad5167b91b75ab8e2310af4f44c065a0f5b781b1a24c9` |
| `poetry-database/raw/r2_04_evidence/theory_locate.json` | **本地原件未删未改**（旧项目目录） | `4ba74f22be1381811ef9455119cd3709fce255ee65285877a0bb27230211f1ac` |
| `raw/r2_04_evidence/full|chapters`、`database/`、`normalized/` | 未触碰（硬排除区） | — |

## 4. 三个"本地过期文件"处理记录（R2-16C 第二轮）

哈希比对发现以下文件**公开 main 版本比本地旧项目目录更新**，按"公开版为准"处理（未用本地覆盖）：

| 文件 | 差异性质 |
|---|---|
| `AGENTS.md` | 公开 184 行（含 R2-15 时代公开边界条款与 R2-08~R2-15 成果列表）；本地 170 行为 R2-07 时代快照 |
| `poetry-database/tools/r2_14_tests.py` | 公开版为带数据库 SHA-256 基线断言的真实实现；本地版 T75 为 `True` 占位退化稿 |
| `poetry-database/reports/tasks/2026-11-16/R2-14/LOGS/tests_r2_14.csv` | 与上述测试脚本配套（公开版含 actual/expect 实值） |

> 请项目所有者知悉：`D:\Codex` 本地目录的这三个文件落后于公开版，未来应从干净克隆回补。

## 5. 项目外工作区（不受版本控制，仅供审计）

- `D:\ZCode\zcode\r2_16_workspace\clean-main\` —— **干净克隆（今后同步源）**，pending 变更集见 FINAL_CHANGE_REPORT
- `D:\ZCode\zcode\r2_16_workspace\synctest\` —— 沙盒（origin.git bare + seed + proj + staging + logs）
- `D:\ZCode\zcode\r2_16_workspace\verify_tests.py`（T1–T13 独立断言）、`tree_risk_scan.py`、`quote_stats.py`、`redaction_dryrun.py`
- `D:\ZCode\zcode\r2_16_workspace\backup\github_sync_v1_r2-15.py.bak` —— v1 脚本备份（项目外）
- `D:\GitBackups\Poetry-Generation-Skill-history-cleanup-20261121\` —— R2-16A 三副本，**含旧 OCR 历史，仅存本地**
