# FINAL_CHANGE_REPORT —— R2-16C 第二轮最终变更与远端差异预览

- 日期：2026-11-21
- 基准：远端 main `37ee224d5a09f9e73bf9b785db986bc94e76bf6a`（本轮执行前后均未变，`ls-remote` 多次复核）
- 干净克隆（待批准变更集所在）：`D:\ZCode\zcode\r2_16_workspace\clean-main`
- **本报告描述"批准后将要发生"的变更；本轮未执行任何推送。**
- 推送执行方式：批准后在干净克隆运行 `python poetry-database/tools/github_sync.py`
  （普通 fast-forward 推送，推送时会生成正式的 SYNC_DIFF.md，本表为预览）。

## 1. 干净克隆 pending 状态（git status 快照）

```
 M poetry-database/tools/github_sync.py          （v1 → v3，严格逐文件白名单）
?? poetry-database/raw/r2_04_evidence/ocr_samples_public.json
?? poetry-database/raw/r2_04_evidence/theory_locate_public.json
?? poetry-database/tools/make_public_evidence.py
?? poetry-database/tools/public_files.txt
?? poetry-database/tools/public_redactions.json
?? poetry-database/reports/tasks/2026-11-21/R2-16/…（R2-16 报告目录，随迁移带入）
```

## 2. 远端差异预览（相对 37ee224）

### 新增（A）
| 路径 | 说明 |
|---|---|
| `poetry-database/raw/r2_04_evidence/ocr_samples_public.json` | WITHHELD 公开版：页码/字符统计/质量标记，无 OCR 正文前缀 |
| `poetry-database/raw/r2_04_evidence/theory_locate_public.json` | WITHHELD 公开版：页码/主题/核验状态 + quote_sha256 |
| `poetry-database/tools/make_public_evidence.py` | 公开证据生成器 |
| `poetry-database/tools/public_files.txt` | 逐文件公开白名单（842 文件，默认拒绝） |
| `poetry-database/tools/public_redactions.json` | 导出时改写规则（4 条） |
| `poetry-database/reports/tasks/2026-11-21/R2-16/*` | 本轮全部报告与日志 |

### 修改（M）
| 路径 | 说明 |
|---|---|
| `poetry-database/tools/github_sync.py` | v1 → v3 |
| `GITHUB_SYNC.md` / `UPLOAD_MANIFEST.csv` / `UPLOAD_REPORT.md` / `REPORTS_INDEX.md` / `SYNC_DIFF.md` | 工具每轮重新生成 |

### 删除（D）
| 路径 | 依据 |
|---|---|
| `poetry-database/raw/r2_04_evidence/ocr_samples.json` | R2-16B 裁决：维持 WITHHELD |
| `poetry-database/raw/r2_04_evidence/theory_locate.json` | R2-16B 裁决：维持 WITHHELD |
| `poetry-database/tools/ocr_vision` | PUBLIC_TREES_AUDIT：macOS 二进制，不公开 |

### 不变
其余 886 白名单文件（含 R2-15 交付件等 36 个公开文件回填登记，见 PUBLIC_TREES_AUDIT §6）内容与公开现状一致（逐文件哈希比对确认；3 个本地过期文件已按"公开版为准"处理，见 COMPLETE_REPORT §14.2）。

## 3. 执行核对清单（批准后同步时应满足）

1. `--dry-run` 先行：842 登记、默认拒绝审计可见、无 ABORT。
2. 真实同步：VERIFY PASS → commit `Sync project reports and tools <日期>` → PUSH OK。
3. 推送后复核：`git ls-remote` main SHA 前进；远端 `raw/r2_04_evidence/ocr_samples.json`、`theory_locate.json`、`tools/ocr_vision` 计数为 0。
4. SYNC_DIFF.md / UPLOAD_REPORT.md / UPLOAD_MANIFEST.csv 与实际推送一致。
5. 若上传遇 HTTP 408/超时：先核实远端 SHA 未变，再按 R2-16A 记录的处理方式（postBuffer 为仓库级临时配置）重试；不得 force。

## 4. 边界声明

- 本变更集只涉及公开仓库文件与同步工具；生产 SQLite、作品数据、作者归属、元曲数据（R2-16D/E/F）不在本 Agent 职责内，本轮零触碰。
- 本地原始研究材料（`raw/r2_04_evidence/full|chapters`、两份 JSON 原件）零删除、零修改，保留在受控本地目录。

## 5. 执行结果（2026-11-21，用户批准后）

- 已执行普通 fast-forward 同步：远端 main `37ee224…` → **`eba67745d998b3bfd6d559124ca89a1fe58437b8`**（单提交）。
- §2 预览与实际 SYNC_DIFF 一致：新增 27 / 修改 9 / 删除 4；删除三条路径（两份 WITHHELD 原件、ocr_vision）远端计数已核验为 0。
- 本报告与 COMPLETE_REPORT §15 执行记录、执行日志（LOGS/run_real_push.log）经第二次小同步入仓。
