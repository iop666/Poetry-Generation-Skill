# TEST_RESULTS —— R2-16D 同步工具测试

- 测试日期：2026-11-21
- 被测对象：`poetry-database/tools/github_sync.py`（严格白名单 v2，R2-16C 重构版）
- 测试环境：沙盒合成项目 + 本地 bare 仓库冒充远端（`D:\ZCode\zcode\r2_16_workspace\synctest\`），
  通过 `GITHUB_SYNC_REPO_URL` / `GITHUB_SYNC_STAGING` 环境变量注入。
  **测试全程未触碰 GitHub 公开仓库；真实 GitHub 远端仅执行过 `--dry-run`（无网络写入）。**
- 独立断言脚本：`D:\ZCode\zcode\r2_16_workspace\verify_tests.py`（不调用被测脚本的任何函数，
  直接读 origin.git 的 git 对象复核）
- 沙盒合成项目毒饵：`database/poetry.db`、`normalized/corpus.jsonl`、
  `raw/r2_04_evidence/full/A_015_引言.md`、`raw/r2_04_evidence/chapters/A_017_诗律.md`、
  `ocr_samples.json`、`theory_locate.json`、`docs/books/poison.pdf`（Run B 用）

## 任务要求的七项测试

| # | 要求 | 结果 | 证据 |
|---|---|---|---|
| 1 | 白名单文件可以正常导出 | **PASS** | T1：8 个合成白名单文件全部出现在 origin main 树中（LOGS/verify_t1_t9_v2.log）；真实项目 dry-run 826 个候选正常列出（LOGS/run_d_real_dryrun.log） |
| 2 | full/ 和 chapters/ 不会导出 | **PASS** | 双重验证：(a) origin 树 0 命中（T2）；(b) 毒饵 `docs/books/poison.pdf` 位于白名单树内时整次同步 exit 4 中止（Run B），origin/main 保持 `0cdc6fdc` 不变 |
| 3 | 非白名单文件不会残留 | **PASS** | T3：种子 origin 中的 `stray_old.json`、`old_dir/junk.txt`、旧公开的 `ocr_samples.json` 全部被清空导出树逻辑删除 |
| 4 | 旧 Manifest 中的文件已删除时能正确处理 | **PASS** | T4：种子 origin 的旧 UPLOAD_MANIFEST.csv 登记了 `docs/old_report.md`（本地已无此文件）；同步后该文件从公开树删除、无崩溃、新 Manifest 不再含该行。v2 实现完全不再读取旧 Manifest |
| 5 | Manifest 与最终公开目录完全对应 | **PASS** | T5 双向校验：树 15 文件 = Manifest 8 + 保护 2（README/LICENSE）+ 生成 5（.gitignore/UPLOAD_MANIFEST.csv/UPLOAD_REPORT.md/GITHUB_SYNC.md/REPORTS_INDEX.md）；脚本内置 verify_export 在每次真实同步推送前强制执行（verify 不通过 exit 6） |
| 6 | SHA-256 对应最终公开文件，而不是脱敏前源文件 | **PASS** | T6：8 个 Manifest 行逐一用 origin blob 复算 SHA-256 全部一致；脱敏样例 `docs/sanitize_test.md` 中的本机路径样例（macOS 与 Windows 两种形态）已被脱敏规则替换为 `<LOCAL_WORKBUDDY>`/`<HOME>` 占位符；Manifest SHA ≠ 源文件 SHA（即按脱敏后文件计算） |
| 7 | 本地数据库、normalized、研究原稿不被误删 | **PASS** | T7：6 个本地毒饵文件同步后全部健在（含 full/、chapters/、ocr_samples.json、theory_locate.json 原件）；database/normalized 0 进入公开树；源项目其余文件未动 |

## 附加测试（超出七项要求，针对本轮发现的风险）

| # | 检查 | 结果 | 证据 |
|---|---|---|---|
| T8 | 保护名单（README/LICENSE）不被清空逻辑删除 | **PASS** | 种子 origin 的自定义 README.md 与 LICENSE 同步后原样保留。**此项有真实背景：公开仓库的 LICENSE 此前不在白名单、也不在旧删除逻辑保护内，v2 若不加保护名单会在下轮同步误删，已修复** |
| T9 | 推送为普通 fast-forward 推送（非 force） | **PASS** | origin/main 由 seed `2de4bbde` → `0cdc6fdc` 正常推进；脚本仅含 `git push origin main`，无 force 参数 |
| R1 | dry-run 不建暂存、不推送 | **PASS** | Run C2：exit 0，staging/repo 不存在（LOGS/run_c2_dryrun.log） |
| R2 | 硬排除在 dry-run 中同样生效 | **PASS** | Run C（毒饵未清理时）：exit 4，无暂存（LOGS/run_c_dryrun.log） |

## 首轮测试中的失败记录（按项目规则保留，不删除）

首轮（verify_t1_t9.log）3 项 FAIL，全部定位并修复后复测通过：

1. **T6 SHA-256 失配（真实缺陷）**：本机 Git 的换行自动转换（CRLF→LF）使 VERBATIM 复制文件的仓库 blob 与工作树字节不一致。
   修复：`ensure_clone()` 在暂存克隆中固定 `core.autocrlf=false`，保证"Manifest 字节 = 仓库 blob 字节"。
2. T1/T5 失败为断言脚本自身问题（git 默认 `core.quotePath` 转义非 ASCII 路径），非被测脚本缺陷；断言脚本加 `-c core.quotepath=false` 后消除。

## 实际运行的命令（真实输出见 LOGS/）

```bash
# Run A：完整同步（沙盒 origin）
export GITHUB_SYNC_REPO_URL="D:/ZCode/zcode/r2_16_workspace/synctest/origin.git"
export GITHUB_SYNC_STAGING="D:/ZCode/zcode/r2_16_workspace/synctest/staging"
python poetry-database/tools/github_sync.py          # → PUSH OK（run_a2_full_sync.log）

# Run B：硬排除中止
mkdir docs/books && echo poison > docs/books/poison.pdf
python poetry-database/tools/github_sync.py          # → exit 4，ABORT 硬排除命中（run_b_hard_abort.log）

# Run C/C2：dry-run
python poetry-database/tools/github_sync.py --dry-run # → exit 4（毒饵）/ exit 0（干净），无暂存无推送

# 真实项目最终版 dry-run（仅白名单收集，无网络写入）
# 在 D:\Codex\Poetry-Generation-Skill 下执行           # → exit 0，826 文件候选（run_d_real_dryrun.log）

# 独立断言
python verify_tests.py                               # → 9 项全 PASS（verify_t1_t9_v2.log）
```

## 结果总览

- 七项要求测试：**7 PASS / 0 FAIL / 0 BLOCKED / 0 NOT RUN**
- 附加测试：4 PASS
- 首轮失败 3 项：已修复 2 处真实/半真实缺陷（autocrlf；断言脚本），失败日志保留
- 未覆盖项：真实 GitHub 远端的端到端推送未执行（本轮按任务要求不推送；推送涉及凭据与网络，留待审核批准后）
