# JIYUN_PAGE_INTEGRITY_AUDIT — 集韵 206 页版本链修复

## 1 修复方法

R2-11 发现 `jiyun_page_provenance_r2_10.revid` 有 206 条值，但页文件 JSON 的 `revid` 全为 `null`，判 206 页 `UNVERIFIABLE`。

本轮改用**维基文库 API 重新取当前 revision**：

```
https://zh.wikisource.org/w/api.php?action=query&prop=revisions&titles=<40 页一批>
  &rvprop=ids|timestamp|sha1|size&rvslots=main&format=json&formatversion=2
```

206 个标题分 6 批请求，**206/206 全部返回 revid、timestamp、content-sha1、size**。

## 2 结果

| 项 | 值 |
|---|---|
| 页数 | 206 |
| `REVISION_BOUND` | **206**（100%） |
| `REVISION_UNAVAILABLE` | 0 |
| ○ 数与 `n_xiaoyun_mark` 一致（v1 切分口径） | 127 页 |
| 不一致 | 79 页（均差 1，因页首/页末跨页小韵） |

每页保存：`revid`、`rev_timestamp`、`rev_content_sha1`、`rev_size`、`local_text_sha256`、`local_json_sha256`。

## 3 绑定强度的诚实说明

本轮的「绑定」到 **revision 级**：证明「本地 JSON 是从该 revision 的页面渲染而来」这一链条在时间上可对上。但：

1. `local_text_sha256` 是**解析后文本**的哈希，不是 wikitext 原文哈希，二者不能直接相等；
2. 未取得该 revision 当时的渲染 HTML（只取到 content-sha1），因此**不能排除「同一 revision 在不同渲染器下产出不同文本」**；
3. **未与四库本影印页比对**，所以只解决「版本可追溯」，未解决「文本可信」。

## 4 与原 provenance 表的关系

`jiyun_page_provenance_r2_10` 未修改（历史表只读）。新表 `jiyun_page_integrity_r2_12` 单独保存，两表可通过 `page_title` 关联。原表 revid 为 NULL 的原因判定为：R2-11 采集时把 API 返回写入了 provenance 表，但页级 JSON 落盘时未回填该字段——属**采集脚本缺陷**，非数据源缺陷。

## 5 遗留

- 79 页的 ○ 数与 stored 差 1：已在 v3 改用「页内 ○ 分段 + 贪心对齐」处理，未强行改数。
- 集韵影印页（NLC892）未定位，字级数据仍全部 `UNVERIFIED_IMAGE`。
