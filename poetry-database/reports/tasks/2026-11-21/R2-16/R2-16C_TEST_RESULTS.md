# R2-16C_TEST_RESULTS —— 同步工具 v3 测试与真实推送证据（第三版，含推送后验证）

> 版本说明：本文件第一版为 v2 七项测试（曾名 TEST_RESULTS.md），第二版仅更名未更新正文——
> 该状态经外部审核指出（R2-16C 第二轮独立审核 P1）后，本版为**完整重写**，
> 覆盖：沙盒 T1–T13、三个中止场景、两次真实推送输出、推送后全新克隆路径级验证。
> 更名原因：避免与数据库任务的 R2-16D 混淆（本文件只属于同步工具 R2-16C）。

- 测试与执行日期：2026-11-21
- 被测对象：`poetry-database/tools/github_sync.py` v3（严格逐文件白名单）
- 沙盒环境：`D:\ZCode\zcode\r2_16_workspace\synctest\`（本地 bare origin + 合成项目 + 独立断言脚本 verify_tests.py），通过 `GITHUB_SYNC_REPO_URL` / `GITHUB_SYNC_STAGING` 注入，**不触碰 GitHub**
- 真实推送：从干净克隆 `clean-main`（同步源）执行；远端认证 HTTPS + gh 凭据
- 独立断言：verify_tests.py 不调用被测脚本任何函数，直接读 git 对象复核

## 一、沙盒测试（v3，13 项全 PASS）

沙盒合成项目含毒饵：`database/poetry.db`、`normalized/corpus.jsonl`、
`raw/r2_04_evidence/full/A_015_引言.md`、`raw/r2_04_evidence/chapters/A_017_诗律.md`、
`ocr_samples.json`、`theory_locate.json`、`docs/books/poison.pdf`（Run B 用）、
`docs/unregistered_draft.md`（T10 默认拒绝用）。

| # | 检查 | 结果 | 证据 |
|---|---|---|---|
| T1 | 白名单文件正常导出（含 public_files.txt / public_redactions.json 等治理文件） | PASS | LOGS/verify_t1_t13_v3.log |
| T2 | full/ 与 chapters/ 不导出 | PASS | 公开树 0 命中 |
| T3 | 非白名单文件不残留 | PASS | 种子 origin 的 stray/old_dir/旧公开 JSON 全部清除 |
| T4 | 旧 Manifest 已删文件正确处理 | PASS | v3 完全不读旧 Manifest；旧登记文件被清空逻辑删除 |
| T5 | Manifest 与最终公开目录双向完全对应 | PASS | 树 19 = Manifest 11 + 保护 2 + 生成 6 |
| T6 | SHA-256 按最终公开（脱敏后）文件复算；脱敏生效 | PASS | 8 行逐一 blob 复算一致；占位符替换验证 |
| T7 | 本地数据库/normalized/研究原稿零误删 | PASS | 6 个毒饵原件全部健在 |
| T8 | 保护名单（README/LICENSE）不被清空删除 | PASS | 种子内容原样保留 |
| T9 | 普通 fast-forward 推送推进 origin | PASS | 无 force 参数 |
| T10 | 默认拒绝：未登记文件不导出 | PASS | unregistered_draft.md 未进入公开树，且出现在默认拒绝审计输出 |
| T11 | 导出时改写生效：公开版无逐字原文、本地原件逐字保留、treatment=REDACTED_PUBLIC | PASS | notes_test.md 三重断言 |
| T12 | SYNC_DIFF.md 差异报告生成且内容正确 | PASS | A/M/D 条目与合计齐全 |
| T13 | 白名单文件本身随仓库公开（可审计） | PASS | public_files.txt 在公开树中 |

中止场景（全部按预期非零退出、origin 不变）：

| 场景 | 结果 | 证据 |
|---|---|---|
| Run B：白名单混入硬排除路径（full/ 下文件） | exit 4，ABORT | LOGS/run_b_v3_hard_abort.log |
| Run C：干净 dry-run | exit 0，不建暂存不推送 | LOGS/run_c_v3_dryrun.log |
| Run D：白名单混入暂停公开文件 | exit 4，WITHHELD 守卫 | LOGS/run_d_v3_withheld_guard.log |

首轮（v2 时代）3 项 FAIL 的记录按项目规则保留于 LOGS/verify_t1_t9.log，其中 1 项真实缺陷
（autocrlf 导致 Manifest 哈希≠仓库 blob）已修复并于 v3 固化。

## 二、真实推送（两次，均普通 fast-forward）

### 推送 #1（主变更）

- 执行位置：干净克隆 `clean-main` @ `37ee224d5a09f9e73bf9b785db986bc94e76bf6a`
- 命令：`python poetry-database/tools/github_sync.py`
- 关键输出（LOGS/run_real_push.log）：
  - 白名单登记 887；默认拒绝 1（ocr_vision）；改写规则 4 条；暂停公开 2 件
  - 导出 887 文件 51,543,685 字节；清空导出树删除残留 869
  - REDACTED_PUBLIC：A_02_第二章.md、A_05_附录一.md、C_诗词格律十讲.md
  - 敏感扫描：仅 `researcher@example.org` 占位符
  - VERIFY PASS：895 = Manifest 887 + 保护 2 + 生成 6；硬排除 0；SHA-256 全部可复算
  - SYNC_DIFF：新增 27 / 修改 9 / 删除 4；**PUSH OK**
- 结果：远端 main `37ee224…` → `eba67745d998b3bfd6d559124ca89a1fe58437b8`

### 推送 #2（执行记录入仓）

- 导出 889；VERIFY PASS（897 = 889 + 2 + 6）；SYNC_DIFF 新增 2 / 修改 7 / 删除 1；PUSH OK
- 结果：远端 main → **`26bf0f763153418b59f9b81688f9229b803924ff`**（当前）

已知小瑕疵（如实记录）：SYNC_DIFF.md 将"上一轮的自己"列为本轮删除项（先 diff 后重写的顺序所致），下轮自然消失；其余内容准确。

## 三、推送后全新克隆路径级验证（审核指定动作，LOGS/verify_final_greps.log）

```
git clone https://github.com/iop666/Poetry-Generation-Skill.git verify-final
git rev-parse HEAD
  → 26bf0f763153418b59f9b81688f9229b803924ff
git ls-tree -r --name-only HEAD > remote-tree.txt        # 897 blob

grep -E 'ocr_samples\.json$|theory_locate\.json$|tools/ocr_vision$' remote-tree.txt
  → （无输出）PASS：三路径均不存在

grep -E 'ocr_samples_public\.json$|theory_locate_public\.json$|public_files\.txt$|public_redactions\.json$' remote-tree.txt
  → 4 路径全部存在 PASS

git rev-list --objects --all | grep -E 'poetry-database/raw/r2_04_evidence/(full|chapters)/'
  → （无输出）PASS：全部可达历史 0 命中
```

远端内容抽查（GitHub contents API）：
- `A_02_第二章.md` 公开版含"公开版改写"标记 = True；含逐字孤平原文 = False

**如实记录的边界**：两份 WITHHELD 原件与 ocr_vision 在**可达历史**中仍存在（公开至 eba6774、于该提交从当前树删除）。当前树已干净，但历史重写与否属审核者决策，本轮未动历史。

## 四、结果总览

- 沙盒：13 项断言 + 3 个中止场景 = **16/16 PASS**
- 真实推送：2 次 PUSH OK，均 fast-forward，VERIFY PASS 前置
- 推送后全新克隆验证：路径级 3 项 PASS + 历史 full/chapters 0 命中
- 覆盖任务要求的七项测试 + 审核追加的默认拒绝/改写/差异报告/白名单公开四项
- 未覆盖：并发推送冲突场景、gh 凭据过期场景（未发生，属异常路径）
