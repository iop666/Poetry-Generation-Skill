#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-14 交付清单生成：逐文件字节数 + SHA-256。

用法：python3 tools/r2_14_manifest.py
输出：reports/tasks/2026-11-16/R2-14/FILE_MANIFEST.md
注意：清单自身不计入哈希（自引用），其字节数与 SHA-256 在生成后由命令另行记录。
"""
import os, hashlib, csv, datetime, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'reports/tasks/2026-11-16/R2-14')
SELF = 'FILE_MANIFEST.md'


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def rows_of(p):
    if not p.lower().endswith('.csv'):
        return ''
    try:
        with open(p, encoding='utf-8-sig', newline='') as f:
            return str(sum(1 for _ in csv.reader(f)) - 1)
    except Exception:
        return '?'


def kind(name):
    if name.startswith('LOGS/'):
        return '日志'
    if name.endswith('.csv'):
        return '数据'
    if name.endswith('.md'):
        return '文档'
    return '其他'


def main():
    files = []
    for root, dirs, fs in os.walk(OUT):
        dirs.sort()
        for n in sorted(fs):
            if n == '.DS_Store':
                continue
            rel = os.path.relpath(os.path.join(root, n), OUT)
            if rel == SELF:
                continue
            p = os.path.join(root, n)
            files.append((rel, os.path.getsize(p), sha256(p), rows_of(p)))
    files.sort()

    by_kind = collections.Counter(kind(r[0]) for r in files)
    total_bytes = sum(r[1] for r in files)

    L = []
    A = L.append
    A('# FILE_MANIFEST — R2-14 交付清单')
    A('')
    A('- 生成时间：%s' % datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
    A('- 目录：`reports/tasks/2026-11-16/R2-14/`')
    A('- 文件数：**%d**（不含本清单）' % len(files))
    A('- 合计字节：**%s**' % format(total_bytes, ','))
    A('- 哈希算法：SHA-256（整文件读入分块计算，未做任何规范化）')
    A('')
    A('## 0 自引用说明')
    A('')
    A('本清单不列表自身，因为写入自身哈希会改变自身内容（自引用悖论）。')
    A('本清单自身的字节数与 SHA-256 在生成后用命令单独计算，写入 `COMPLETE_REPORT.md` 第 17 节与最终回复。')
    A('')
    A('## 1 分类统计')
    A('')
    A('| 类别 | 文件数 | 合计字节 |')
    A('|---|---|---|')
    for k in ('数据', '文档', '日志', '其他'):
        if by_kind.get(k):
            sub = [r for r in files if kind(r[0]) == k]
            A('| %s | %d | %s |' % (k, len(sub), format(sum(r[1] for r in sub), ',')))
    A('| **合计** | **%d** | **%s** |' % (len(files), format(total_bytes, ',')))
    A('')
    A('## 2 逐文件清单')
    A('')
    A('| # | 相对路径 | 字节 | 行数 | SHA-256 |')
    A('|---|---|---|---|---|')
    for i, (rel, size, h, n) in enumerate(files, 1):
        A('| %d | `%s` | %s | %s | `%s` |' % (i, rel, format(size, ','), n or '-', h))
    A('')
    A('## 3 复算方法')
    A('')
    A('```bash')
    A('cd %s' % BASE)
    A("shasum -a 256 reports/tasks/2026-11-16/R2-14/*.csv reports/tasks/2026-11-16/R2-14/*.md | sort")
    A('python3 tools/r2_14_manifest.py   # 重算本清单')
    A('```')
    A('')
    A('任一行字节数或 SHA-256 与上表不符，说明该文件在清单生成后又被改动，需重新生成清单。')

    with open(os.path.join(OUT, SELF), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    print('files=%d bytes=%d -> %s' % (len(files), total_bytes, SELF))
    print('manifest bytes=%d sha256=%s' % (
        os.path.getsize(os.path.join(OUT, SELF)),
        sha256(os.path.join(OUT, SELF))))


if __name__ == '__main__':
    main()
