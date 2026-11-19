# R2-04 勘误：公开同步边界（2026-11-20 追加）

## 原结论

`SOURCE_AUDIT.md` 与本轮其他文档声明：现代版权著作只做书目登记与合法渠道记录，
未将全文纳入交付材料。

## 事实更正

该结论**对「本地研究交付」成立，对「公开发布」不成立**。

2026-11-16 首次 GitHub 同步时，`tools/github_sync.py` 的白名单写的是目录
`poetry-database/raw/r2_04_evidence`，导致：

- `full/` 17 个完整章节正文（107,351 字符 / 290,894 字节）
- `chapters/` 17 个章节连续正文摘录（47,436 字符 / 129,806 字节）

被推送到公开仓库。2026-11-20 已从最新快照删除（远端 `full|chapters` 计数为 0），
Git 历史仍含旧提交，处置方案见
`reports/tasks/2026-11-20/R2-15/COPYRIGHT_HISTORY_IMPACT.md`。

## 影响

- 本轮的**阅读结论与页码证据不受影响**：`manifest.json`、`theory_locate.json`
  仍在，页码与引文定位可复核。
- 受影响的是**分发边界**，不是研究结论。

## 责任

同步工具白名单设计缺陷，非 R2-04 阅读流程缺陷。修复与防复发测试见
`reports/tasks/2026-11-20/R2-15/COPYRIGHT_SYNC_AUDIT.md`。
