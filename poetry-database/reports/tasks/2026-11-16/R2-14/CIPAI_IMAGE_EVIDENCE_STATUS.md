# CIPAI_IMAGE_EVIDENCE_STATUS — 词谱图像证据状态

## 1 本轮完成

| 项 | 结果 |
|---|---|
| 页面级区域索引 | 每页的标题块与谱行块 bbox 已提取（`CIPAI_PAGE_REGION_INDEX.csv`） |
| 词牌区域 | 11 个 region，含 `x0/y0/x1/y1` 与首末谱行（`CIPAI_11_REGION_MAPPING.csv`） |
| stack 图修复方案 | 1 条需按标题 y 坐标拆切，10 条单表单可整页用（`CIPAI_STACK_IMAGE_REPAIR.csv`） |
| form_id 绑定 | 11 条状态：`AMBIGUOUS_MULTI_FORM` 1 / `BOUND_OK` 10（`CIPAI_FORM_ID_BINDING_AUDIT.csv`） |

## 2 未完成

**`GRADE_UNCONFIRMED`**：词牌级（cipai）与格别级（form，定格/格一/格二）的精确绑定**尚未确认**。
原因：一页含 2–3 个词牌时，标题块的 y 坐标只能粗略划分区域，格别标题（「定格」「格一」）常与正文混在同一条谱行块内，无法可靠切分。

## 3 证据等级

11 幅图仍为 `DIGITAL_PAGE_IMAGE`（矢量重排，非纸本扫描）。本轮只建立了「页面 → 区域」的关系，**没有**升级为「区域 → 格别」的确认。

## 4 为什么不继续做逐符号核验

任务书要求「仅在区域映射确定后进行」。当前格别级未确认，逐符号核验会重演 R2-12 的错误（拿错裁切图去比）。因此 20 条控制样本仍未开始。
