# FILE_MANIFEST —— ROUND 1 文件变更清单

生成时间：2026-11-11 00:35:37
工作目录：`<PROJECT_ROOT>/诗词格律引擎`

说明：SHA-256 取前 16 位（完整值可用 `shasum -a 256 <文件>` 复算）。
`reports/round-1-audit/*.md`（10 份专题报告）与 `reports/execution-history/` 自身不计入本表。

| 路径 | 类别 | 字节 | SHA-256(16) |
|---|---|---|---|
| `README.md` | 知识库/其他 | 5,507 | `7c622944db19e4c4` |
| `engine/cilin.py` | 代码 | 6,871 | `46c063241fce05e2` |
| `engine/gedou.py` | 代码 | 37,169 | `d7404a87e2b97b23` |
| `engine/run_acceptance.py` | 代码 | 12,812 | `30aacf1e78c2e198` |
| `engine/run_tests.py` | 代码 | 9,395 | `9556078956a903aa` |
| `engine/yunshu.py` | 代码 | 5,257 | `c8456a4bcecdefda` |
| `reports/round-1-audit/01_问题清单.md` | 报告/日志 | 3,895 | `bc063f760586c9a9` |
| `reports/round-1-audit/02_浣溪沙模板审计.md` | 报告/日志 | 6,822 | `6224f8ff8ab1fe36` |
| `reports/round-1-audit/03_词林正韵完整性审计.md` | 报告/日志 | 5,749 | `8e65029c22a454fd` |
| `reports/round-1-audit/04_多音字机制审计.md` | 报告/日志 | 7,694 | `60ffb7857336f2c7` |
| `reports/round-1-audit/05_逐字校验输出审计.md` | 报告/日志 | 7,574 | `e1f44f9a1cca7e07` |
| `reports/round-1-audit/06_独立测试集报告.md` | 报告/日志 | 7,352 | `127658d8e8e74450` |
| `reports/round-1-audit/07_对仗审查报告.md` | 报告/日志 | 4,948 | `289bc970883b06f5` |
| `reports/round-1-audit/08_平水韵数据审计.md` | 报告/日志 | 7,741 | `f98a32dfb9f25564` |
| `reports/round-1-audit/09_代码修复记录.md` | 报告/日志 | 11,005 | `e7d9d27f32f1f45b` |
| `reports/round-1-audit/10_完整实施与验收报告.md` | 报告/日志 | 36,658 | `61a799a3830ece0b` |
| `reports/round-1-audit/logs/baseline/probe_before.txt` | 报告/日志 | 13,317 | `dbca0c3f69b3deea` |
| `reports/round-1-audit/logs/independent_test_console.txt` | 报告/日志 | 4,798 | `52714a06b22cc5d7` |
| `reports/round-1-audit/logs/independent_test_results.json` | 报告/日志 | 71,358 | `4781f4666a949c33` |
| `reports/round-1-audit/logs/polyphone_pending.json` | 报告/日志 | 8,663 | `6328d7f0c282e70c` |
| `reports/round-1-audit/logs/polyphone_pending.md` | 报告/日志 | 3,670 | `ac01965e782995b7` |
| `reports/round-1-audit/logs/probe_after.err` | 报告/日志 | 0 | `e3b0c44298fc1c14` |
| `reports/round-1-audit/logs/probe_after.txt` | 报告/日志 | 21,969 | `561955e852d74a6a` |
| `tests/01_golden_poems.json` | 测试样本 | 2,979 | `8caa9f655004e93b` |
| `tests/02_error_injection.json` | 测试样本 | 3,547 | `d7a62380b52759cb` |
| `tests/03_variants_legal.json` | 测试样本 | 3,332 | `33b09161d9bfac92` |
| `tests/04_polyphone_boundary.json` | 测试样本 | 2,623 | `9b2b7d74d39954c7` |
| `tests/05_rhyme_boundary.json` | 测试样本 | 1,692 | `2cc02592f1cae880` |
| `tests/06_cipai.json` | 测试样本 | 3,173 | `b53d4a5c31f48667` |
| `tools/build_cilin.py` | 代码 | 5,209 | `4c704334e0439e94` |
| `tools/build_lexicon.py` | 代码 | 8,591 | `cf0354d2bd291dad` |
| `tools/capture_probe.py` | 代码 | 4,651 | `9969acd738e915ab` |
| `tools/collect_polyphones.py` | 代码 | 4,292 | `44da36d3b06b24c7` |
| `报告/实施报告.md` | 报告/日志 | 7,656 | `7a708001716ad6d0` |
| `报告/实施汇报.html` | 报告/日志 | 17,103 | `e46d4c1f4605bdf1` |
| `计划/五阶段实施计划.md` | 知识库/其他 | 4,498 | `ca412930dee48b19` |
| `诗歌知识库/01_基础库/典故库.md` | 知识库/其他 | 3,489 | `af7ce98d47233558` |
| `诗歌知识库/01_基础库/对仗句式.md` | 知识库/其他 | 3,349 | `f41ec0e6d3a2b7af` |
| `诗歌知识库/01_基础库/意象词典.md` | 知识库/其他 | 3,966 | `3abaeb6f38575916` |
| `诗歌知识库/01_基础库/格律规则.md` | 知识库/其他 | 4,641 | `78ac5fd8e6f8f7d7` |
| `诗歌知识库/02_作品库/唐诗精选_标注.json` | 知识库/其他 | 7,382 | `b9253e85d592f213` |
| `诗歌知识库/03_鉴赏库/诗话摘录.md` | 知识库/其他 | 3,285 | `8e638438debd4b26` |
| `诗歌知识库/04_韵书/中华新韵_十四韵.md` | 韵书数据 | 1,936 | `4aeb9a19cc76cd36` |
| `诗歌知识库/04_韵书/平水韵_全表_繁体.json` | 韵书数据 | 39,714 | `4d67d0bde7b2aa11` |
| `诗歌知识库/04_韵书/平水韵_数据审计.json` | 韵书数据 | 33,170 | `b4ae0d80bd685cac` |
| `诗歌知识库/04_韵书/平水韵_索引.json` | 韵书数据 | 536,631 | `923a46828e105ca5` |
| `诗歌知识库/04_韵书/词林正韵_十九部.json` | 韵书数据 | 6,402 | `ed78029874fbd799` |
| `诗歌知识库/04_韵书/词林正韵_十九部.md` | 韵书数据 | 3,185 | `2b678fca256f03c4` |
| `诗歌知识库/05_创作库/客舍.md` | 知识库/其他 | 3,567 | `85351a3be58a014f` |
| `诗歌知识库/05_创作库/浣溪沙.md` | 知识库/其他 | 2,031 | `4ac1904ee437ba5b` |
| `诗歌知识库/05_创作库/病例·秋夜.md` | 知识库/其他 | 2,196 | `b3c725f504cdbebc` |
| `诗歌知识库/05_创作库/秋山.md` | 知识库/其他 | 2,003 | `e73b51349b77e33e` |
| `诗歌知识库/05_创作库/秋日登楼.md` | 知识库/其他 | 3,255 | `8457efd218f71bcf` |
| `诗歌知识库/05_创作库/秋望·婉约.md` | 知识库/其他 | 1,791 | `a27cab0979dd9636` |
| `诗歌知识库/05_创作库/秋望·清远.md` | 知识库/其他 | 1,557 | `b4eb00c6c3b1728b` |
| `诗歌知识库/05_创作库/秋望·豪放.md` | 知识库/其他 | 1,878 | `127fcc80b6249fa9` |
| `诗歌知识库/06_迭代记录/验收测试结果.json` | 知识库/其他 | 95,446 | `170a0ee09e2ae158` |
| `诗歌知识库/06_迭代记录/验收测试记录.md` | 知识库/其他 | 16,580 | `b77b96f1a3240547` |

合计 58 个文件（不含 10 份专题报告与执行历史目录）。

## 变更性质汇总

| 性质 | 数量 | 文件 |
|---|---|---|
| 新增代码 | 3 | `engine/yunshu.py`、`engine/cilin.py`、`engine/run_tests.py` |
| 新增工具 | 3 | `tools/build_cilin.py`、`tools/collect_polyphones.py`、`tools/capture_probe.py` |
| 新增测试 | 6 | `tests/01`–`06` |
| 新增数据 | 4 | `平水韵_索引.json`、`平水韵_数据审计.json`、`词林正韵_十九部.json/.md` |
| 重写 | 2 | `engine/gedou.py`（521→782 行）、`tools/build_lexicon.py`（85→197 行） |
| 修改 | 2 | `engine/run_acceptance.py`、`README.md` |
| 加警示横幅 | 1 | `报告/实施报告.md`（正文未改） |
| 删除 | 2 | `平水韵_简体索引.json`、`词林正韵_平声十四部.md`（均被取代） |
| 重新生成 | 10 | `05_创作库/*.md`（8 份）、`06_迭代记录/*`（2 份） |

## 原始数据完整性

| 文件 | 是否修改 | 证据 |
|---|---|---|
| `诗歌知识库/04_韵书/平水韵_全表_繁体.json` | **未修改** | SHA `4d67d0bde7b2aa11`，与 v1 一致；污染字符保留在源文件中，仅在构建时清洗 |
| `诗歌知识库/02_作品库/唐诗精选_标注.json` | 未修改 | SHA `b9253e85d592f213` |
| `诗歌知识库/01_基础库/*` | 未修改 | 4 个文件 SHA 同 v1 |
