#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把诗词项目的报告与代码同步到公开 GitHub 仓库（可复跑）。

设计原则
--------
1. 报告全量上传：reports/ 下的每一轮 COMPLETE_REPORT.md 与交付件都进仓库。
2. 只上传白名单：数据库、规范化语料、版权书全文、OCR 图像一律排除。
3. 脱敏：所有文本文件里的本机绝对路径替换为占位符，不写入用户名/家目录。
4. 可复算：生成 UPLOAD_MANIFEST.csv（逐文件字节 + SHA-256）与 UPLOAD_REPORT.md。
5. 可重复执行：上一轮清单里的文件若已不在白名单，会在仓库中删除。

用法
----
    python3 tools/github_sync.py            # 同步并推送
    python3 tools/github_sync.py --dry-run  # 只生成本地暂存与清单，不推送

认证：本机 GitHub SSH key（ssh -T git@github.com 能认证）。
提交身份：按用户要求固定使用 git 全局账户（git config --global user.name / user.email），
脚本不以 -c 临时身份覆盖；仓库本地也不应设 user.*。
"""
import argparse
import csv
import datetime
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
DBROOT = TOOLS.parent
PROJECT = DBROOT.parent
REPO_URL = "git@github.com:iop666/Poetry-Generation-Skill.git"
TODAY = datetime.date.today().isoformat()
STAGING = Path.home() / "Desktop" / "workbuddy" / TODAY / ".tmp" / (
    TODAY + "_临时_GitHub同步暂存"
)
CLONE = STAGING / "repo"

# ---------- 白名单：这些目录整体上传（报告优先，全量） ----------
INCLUDE_TREES = [
    "docs",
    "诗词格律引擎",
    "poetry-database/reports",
    "poetry-database/tools",
    "poetry-database/catalog",
    "poetry-database/research",
    "poetry-database/audit",
    "poetry-database/sources",
]
INCLUDE_FILES = [
    "AGENTS.md",
    "AGENT_REPORTING_STANDARD.md",
    "poetry-database/README.md",
    # 小型原始证据（非书全文、非大语料）
    "poetry-database/raw/r2_04_cipai_index.json",
    "poetry-database/raw/r2_04_evidence",
    "poetry-database/raw/r2_05_notes",
    "poetry-database/raw/r2_06_notes",
    "poetry-database/raw/r2_07_finalize.json",
    "poetry-database/raw/r2_07_external.json",
    "poetry-database/raw/r2_07_forms.json",
]

# ---------- 黑名单：命中即排除（优先级高于白名单） ----------
EXCLUDE_PARTS = [
    "/.git/", "/.workbuddy/", "/__pycache__/", "/.DS_Store",
    "/database/", "/normalized/", "/books/",
    "/raw/books", "/raw/poetry/", "/raw/r2_08/cache/",
    "/raw/r2_09/images/", "/raw/r2_11/images/", "/raw/r2_12/facsimile/",
]
EXCLUDE_SUFFIX = (".pyc", ".pyo", ".db", ".sqlite", ".wal", ".shm")
MAX_FILE_BYTES = 90 * 1024 * 1024  # GitHub 单文件硬上限 100 MB，留 10 MB 余量

# ---------- 脱敏规则 ----------
SANITIZE = [
    # 本机桌面工作区（含中文项目名）
    (re.compile(r"/Users/[^/\s\"']+/Desktop/任务列表/诗词"), "<PROJECT_ROOT>"),
    (re.compile(r"~/Desktop/任务列表/诗词"), "<PROJECT_ROOT>"),
    # 本机文件归置目录
    (re.compile(r"/Users/[^/\s\"']+/Desktop/workbuddy"), "<LOCAL_WORKBUDDY>"),
    (re.compile(r"~/Desktop/workbuddy"), "<LOCAL_WORKBUDDY>"),
    # 任何残留家目录
    (re.compile(r"/Users/[^/\s\"']+"), "<HOME>"),
    (re.compile(r"C:\\Users\\[^\\\s\"']+"), "<HOME>"),
]
TEXT_SUFFIX = (
    ".md", ".py", ".json", ".jsonl", ".csv", ".txt", ".html", ".htm",
    ".yaml", ".yml", ".sql", ".sh", ".js", ".ts", ".xml", ".ini",
)


def log(*a):
    print(*a, flush=True)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def is_excluded(rel):
    s = "/" + rel.replace(os.sep, "/")
    if any(x in s for x in EXCLUDE_PARTS):
        return True
    if s.endswith(".DS_Store") or s.endswith(tuple(
        "/" + x if not x.startswith("/") else x for x in EXCLUDE_SUFFIX
    )):
        return True
    if rel.lower().endswith(TEXT_SUFFIX + EXCLUDE_SUFFIX):
        pass
    return False


def collect():
    picked = []
    seen = set()
    for item in INCLUDE_FILES + INCLUDE_TREES:
        src = PROJECT / item
        if not src.exists():
            log("WARN 白名单项不存在:", item)
            continue
        files = [src] if src.is_file() else [
            p for p in src.rglob("*") if p.is_file()
        ]
        for p in files:
            rel = p.relative_to(PROJECT).as_posix()
            if rel in seen:
                continue
            if is_excluded(rel):
                continue
            size = p.stat().st_size
            if size > MAX_FILE_BYTES:
                log("SKIP 超限", size, rel)
                continue
            seen.add(rel)
            picked.append((rel, p, size))
    picked.sort()
    return picked


# 这些文件含脱敏规则自身的字面量（/Users/ 等），不能再被脱敏，
# 否则正则会失效、工具在远端变成坏代码。它们本身不含真实本机路径。
NO_SANITIZE = {"github_sync.py"}


def sanitize_copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.name in NO_SANITIZE:
        shutil.copy2(src, dst)
        return "VERBATIM"
    if src.suffix.lower() in TEXT_SUFFIX or src.name in ("Makefile", "Dockerfile"):
        try:
            txt = src.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            shutil.copy2(src, dst)
            return "BINARY_FALLBACK"
        new = txt
        for pat, rep in SANITIZE:
            new = pat.sub(rep, new)
        dst.write_text(new, encoding="utf-8")
        return "SANITIZED" if new != txt else "CLEAN"
    shutil.copy2(src, dst)
    return "COPIED"


def git(args, check=True):
    return subprocess.run(
        ["git", "-C", str(CLONE)] + args,
        check=check, capture_output=True, text=True,
    )


def sensitive_scan():
    """推送前硬门禁：残留本机路径 / 手机号 / 凭据就中止。"""
    blockers = []
    emails = set()
    pats = [
        ("本机家目录", re.compile(r"/Users/")),
        # 必须是独立 token；哈希/ID 里的 11 位数字串不算手机号
        ("手机号", re.compile(r"(?<![A-Za-z0-9])1[3-9]\d{9}(?![A-Za-z0-9])")),
        ("API 凭据", re.compile(r"(?:Bearer\s+[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,})")),
    ]
    for p in CLONE.rglob("*"):
        if (not p.is_file() or ".git" in p.parts
                or p.name in ("UPLOAD_MANIFEST.csv", "github_sync.py")):
            # github_sync.py 自身含脱敏正则字面量，不含真实本机路径
            continue
        if p.suffix.lower() not in TEXT_SUFFIX:
            continue
        try:
            t = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pat in pats:
            m = pat.search(t)
            if m:
                blockers.append((p.relative_to(CLONE).as_posix(), label, m.group()[:40]))
        for m in re.finditer(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", t):
            emails.add(m.group())
    for x in blockers[:20]:
        log("BLOCK 敏感残留:", x)
    log("文本中出现的邮箱（仅供人工确认）:", sorted(emails)[:20])
    if blockers:
        log(f"共 {len(blockers)} 处敏感残留，已中止推送。")
        sys.exit(3)
    return sorted(emails)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    STAGING.mkdir(parents=True, exist_ok=True)
    picked = collect()
    log("白名单文件数:", len(picked), "合计字节:", sum(x[2] for x in picked))

    if not args.dry_run:
        if (CLONE / ".git").exists():
            git(["fetch", "origin", "main"], check=False)
            git(["reset", "--hard", "origin/main"], check=False)
        else:
            if CLONE.exists():
                shutil.rmtree(CLONE)
            subprocess.run(["git", "clone", REPO_URL, str(CLONE)], check=True)

        # 清掉上一轮由本工具生成、但本轮已不再白名单内的文件
        old_manifest = CLONE / "UPLOAD_MANIFEST.csv"
        if old_manifest.exists():
            with open(old_manifest, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    old = CLONE / row["path"]
                    if old.exists() and not (PROJECT / row["path"]).exists():
                        old.unlink()
        keep = {".git", ".gitignore", "README.md"}
        for p in list(CLONE.rglob("*")):
            if p.is_dir() or CLONE not in p.parents:
                continue
            rel = p.relative_to(CLONE).as_posix()
            if rel in keep or rel.startswith(".git/"):
                continue
            # 只删本工具上轮记录过的文件，避免误删人工维护内容
            if old_manifest.exists() and rel not in {
                x[0] for x in picked
            }:
                p.unlink()

    rows = []
    stats = {}
    for rel, src, size in picked:
        if not args.dry_run:
            dst = CLONE / rel
            kind = sanitize_copy(src, dst)
            stats[kind] = stats.get(kind, 0) + 1
            rows.append({
                "path": rel,
                "bytes": str((dst).stat().st_size),
                "sha256": sha256(dst),
                "treatment": kind,
            })
        else:
            rows.append({"path": rel, "bytes": str(size), "sha256": "",
                         "treatment": "DRY_RUN"})

    if args.dry_run:
        log("DRY RUN 完成。首 5 项:", [r["path"] for r in rows[:5]])
        return

    # 上传策略与清单
    (CLONE / ".gitignore").write_text(
        "\n".join([
            ".DS_Store", "__pycache__/", "*.pyc", "*.pyo",
            "# 以下内容按项目规则永不上传：",
            "# poetry-database/database/  (732 MB SQLite，含本机绝对路径)",
            "# poetry-database/normalized/ (395 MB 语料，超 GitHub 单文件上限)",
            "# books/, poetry-database/raw/books* (现代版权书全文与 OCR)",
            "# poetry-database/raw/*/images/, */facsimile/ (书页图像)",
            "# .workbuddy/ (本机记忆与临时数据)",
            "",
        ]), encoding="utf-8"
    )

    found_emails = sensitive_scan()

    with open(CLONE / "UPLOAD_MANIFEST.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "bytes", "sha256", "treatment"])
        w.writeheader()
        w.writerows(rows)

    # README 由项目所有者维护，本工具绝不覆盖。
    # 上传策略与同步说明单独放在 UPLOAD_REPORT.md / GITHUB_SYNC.md。
    readme_path = CLONE / "README.md"
    generated_marker = "项目资料仓库"
    need_restore = (not readme_path.exists()) or (
        generated_marker in readme_path.read_text(encoding="utf-8", errors="ignore")
    )
    if need_restore:
        original = PROJECT / "docs/README_ORIGINAL.md"
        if original.exists():
            shutil.copy2(original, readme_path)
            log("README 缺失或曾被工具覆盖，已从 docs/README_ORIGINAL.md 恢复")
        else:
            log("WARN README 需恢复但无备份，请人工检查")
    (CLONE / "GITHUB_SYNC.md").write_text("""# 仓库同步说明（工具生成，勿手改）

本文件由 `poetry-database/tools/github_sync.py` 生成，说明本仓库的同步边界。
项目介绍见 `README.md`（人工维护，工具不会覆盖）。

## 仓库内容

| 路径 | 内容 |
|---|---|
| `AGENTS.md` / `AGENT_REPORTING_STANDARD.md` | 项目长期指令与汇报制度 |
| `docs/` | 原始方案、历史文档与原 README 备份 |
| `诗词格律引擎/` | 格律引擎代码、独立测试集与执行报告（引擎冻结，仅研究用） |
| `poetry-database/reports/` | **逐轮完整报告**（含每轮 `COMPLETE_REPORT.md` 与全部交付件） |
| `poetry-database/tools/` | 审计与同步工具 |
| `poetry-database/catalog|research|audit|sources/` | 词谱、书目与审计元数据 |
| `UPLOAD_MANIFEST.csv` | 本轮上传文件的逐项字节数与 SHA-256 |
| `UPLOAD_REPORT.md` | 本轮上传说明与排除项 |

## 不上传的内容（硬性）

1. **数据库文件**：`poetry.db`（732 MB）等超过 GitHub 单文件 100 MB 上限的二进制。
2. **版权书全文**：`books/`（z-library 来源的王力、龙榆生著作）及其 OCR 文本/书页图像。
   项目规则：现代版权著作只登记书目与合法渠道，不得抓取或分发全文。
3. **本机个人信息**：所有文本中的本机家目录与绝对路径已替换为 `<PROJECT_ROOT>` / `<HOME>` / `<LOCAL_WORKBUDDY>`。

## 同步方式

每轮任务完成后，在项目根目录执行：

```bash
python3 poetry-database/tools/github_sync.py
```

工具会重建白名单暂存、脱敏、生成新的清单与上传报告，然后推送到 `main`；
提交身份固定使用 git 全局账户。需要本机已配置 GitHub SSH key。
加 `--dry-run` 只做本地检查不推送。
""", encoding="utf-8")

    total = sum(int(r["bytes"]) for r in rows)
    excluded = [
        ("poetry-database/database/poetry.db", "732 MB，超 GitHub 单文件上限；含本机绝对路径"),
        ("poetry-database/normalized/*.jsonl", "395 MB，超 GitHub 单文件上限"),
        ("books/*.pdf|epub", "z-library 来源的现代版权书全文，项目规则禁止分发"),
        ("poetry-database/raw/books*/**", "上述版权书的 OCR 全文与书页图像"),
        ("poetry-database/raw/*/images|facsimile", "书页影印，版权风险"),
        (".workbuddy/**", "本机记忆与临时数据"),
    ]
    lines = [
        "# GitHub 上传报告",
        "",
        f"- 时间：{datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}",
        f"- 仓库：`{REPO_URL}`（公开）",
        f"- 上传文件：**{len(rows)}** 个，合计 **{total:,}** 字节",
        "- 脱敏处理：" + "、".join(f"{k} {v}" for k, v in sorted(stats.items())),
        f"- 推送前门禁：本机路径 / 手机号 / 凭据残留 **0 处**；邮箱 {len(found_emails)} 个"
        + (f"（{', '.join(found_emails[:10])}）" if found_emails else ""),
        "",
        "## 排除项及原因",
        "",
        "| 路径 | 原因 |",
        "|---|---|",
    ]
    lines += [f"| `{p}` | {why} |" for p, why in excluded]
    lines += [
        "",
        "## 复核",
        "",
        "逐文件 SHA-256 见 `UPLOAD_MANIFEST.csv`。",
        "可用 `python3 poetry-database/tools/github_sync.py --dry-run` 复算白名单。",
        "",
    ]
    (CLONE / "UPLOAD_REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    # 根目录报告索引：让人一眼看到每一轮报告在哪，不用逐层点目录
    reports = []
    for r in rows:
        m = re.match(
            r"poetry-database/reports/tasks/(\d{4}-\d{2}-\d{2})/([^/]+)/COMPLETE_REPORT\.md$",
            r["path"],
        )
        if m:
            reports.append((m.group(2), m.group(1), r["path"], int(r["bytes"])))
    reports.sort()
    idx = [
        "# 逐轮报告索引",
        "",
        f"共 **{len(reports)}** 轮完整报告，每轮含 `COMPLETE_REPORT.md` 与全部交付件（CSV / MD / LOGS）。",
        "",
        "| 轮次 | 日期 | 报告字节 | 完整报告 | 该轮目录 |",
        "|---|---|---|---|---|",
    ]
    for round_id, date, path, size in reports:
        d = f"poetry-database/reports/tasks/{date}/{round_id}"
        idx.append(
            f"| {round_id} | {date} | {size:,} | "
            f"[COMPLETE_REPORT.md]({path}) | [目录]({d}) |"
        )
    idx += [
        "",
        "上传范围与排除项见 [UPLOAD_REPORT.md](UPLOAD_REPORT.md)；"
        "同步机制见 [GITHUB_SYNC.md](GITHUB_SYNC.md)。",
        "",
    ]
    (CLONE / "REPORTS_INDEX.md").write_text("\n".join(idx), encoding="utf-8")
    log("报告索引：", len(reports), "轮")

    # 提交推送
    git(["add", "-A"])
    r = git(["diff", "--cached", "--quiet"], check=False)
    if r.returncode == 0:
        log("无变更需要提交。")
    else:
        # 按用户要求：使用 git 全局账户（git config --global user.name/user.email）提交，
        # 不再用 -c 临时身份覆盖；仓库本地也未设置 user.*，因此提交作者即全局账户。
        git(["commit", "-m", f"Sync project reports and tools {TODAY}"])
        r = git(["push", "origin", "main"], check=False)
        if r.returncode:
            log("PUSH FAILED:", r.stderr[-2000:])
            sys.exit(2)
        log("PUSH OK")

    log("上传完成:", len(rows), "个文件", total, "字节")
    log("暂存目录:", CLONE)
    log("清单:", CLONE / "UPLOAD_MANIFEST.csv")


if __name__ == "__main__":
    main()
