# SOURCE_AUDIT —— R2-03 来源审计

状态词表：FOUND → ACCESSIBLE → ACQUIRED → PARSED → READ → EXTRACTED → VERIFIED。
**本轮无一条达到 VERIFIED**（未与任何印本影印件对勘）。

## 一、六本实体书

| 书 | 取得 | 解析 | 阅读 | 提取 | 核验 |
|---|---|---|---|---|---|
| 唐宋词格律（龙榆生，上海古籍 PDF） | ACQUIRED | **PARSED**（270 页，文字层） | READ_PARTIAL（体例＋16 调） | **EXTRACTED**（3 条 claim ＋ 76 调谱） | 无 |
| 词学十讲（龙榆生，EPUB） | ACQUIRED | **PARSED**（33 章） | READ_PARTIAL（6 章） | **EXTRACTED**（5 条 claim） | 无 |
| 诗词格律·概要（王力，中华书局 2014） | ACQUIRED | **PARSED**（432 页 OCR） | READ_PARTIAL（18 页） | **EXTRACTED**（8 条 claim） | 无 |
| 汉语音韵学（王力） | ACQUIRED | **PARSED**（476 页 OCR） | 未读 | 无 | 无 |
| 同源字典（王力） | ACQUIRED | **PARSED**（783 页 OCR） | 未读 | 无 | 无 |
| 古代汉语常识（王力，EPUB） | ACQUIRED | **PARSED**（16 章） | 未读 | 无 | 无 |

## 二、缺失

| 项 | 状态 | 证据 |
|---|---|---|
| 诗经韵读·楚辞韵读（王力） | **MISSING** | `books/` 内只有 341 字节的 `.textClipping`（macOS Finder 剪贴），内容是文件名字符串，非 PDF 本体 |

## 三、版权与使用边界

| 项 | 说明 |
|---|---|
| 文件来源 | 用户自行提供的本地文件（文件名含第三方站点标识），本轮**未联网抓取任何一本书** |
| 使用范围 | 仅在用户授权的本地项目内解析、索引、引用 |
| 是否再分发 | **否**。本轮未把任何书籍全文打包进交付包；交付包内只有 `pages.jsonl`/`chapters.jsonl`（解析产物），且仅在本地 |
| 报告引用 | 引用均为短句（每条 ≤ 100 字），用于核对，不构成替代阅读 |

> 提示：若日后对外发布数据库，须先解决这六本书的授权问题——它们是现代出版物，**不是公版古籍**。

## 四、OCR 引擎来源

| 项 | 说明 |
|---|---|
| 引擎 | Apple Vision（`VNRecognizeTextRequest`，revision 2），随 macOS 提供 |
| 是否联网 | 否，完全本地 |
| 是否使用 PaddleOCR-VL-1.6 | **否**（环境内无可用端点，详见 OCR_QUALITY_REPORT §1） |
| 记录 | 每页 `engine="macos-vision-rev2"`，可与未来 PaddleOCR 结果区分 |

## 五、页码引用规范

- 所有 `theory_claims.page` / `cipai_specs.page` 均为 **PDF 物理页**；
- 原因：本书版心页码常被 OCR/文本层拆成两段（如「23」变「3」），不可靠；
- 复核方式：打开 `books/` 同名 PDF，跳到该物理页即可。

## 六、结论

- 6/7 项取得并解析，1 项缺文件；
- 阅读覆盖：唐宋词格律（体例）、词学十讲（6/11 讲）、诗词格律（18/432 页）；
- **提取 16 条理论条目，全部带引文与页码**；
- `VERIFIED` = 0，`EDITION_VERIFIED` = 0，原因一致：**没有影印本可比对**。
