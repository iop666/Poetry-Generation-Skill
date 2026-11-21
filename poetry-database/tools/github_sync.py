#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把诗词项目的报告与代码同步到公开 GitHub 仓库（严格逐文件白名单 v3，R2-16C 第二轮）。

设计原则（v3，在 v2 基础上按外部审核 2026-11-21 要求强化）
--------
1. 逐文件白名单（默认拒绝）：唯一导出来源是 `tools/public_files.txt` 登记的文件清单。
   任何未登记文件一律不导出；新增文件必须先通过公开审计并在清单登记。
   v2 的目录级 INCLUDE_TREES 已废除。脚本同时扫描原八棵树根，
   把「位于树根下但未登记」的文件列入默认拒绝报告，保证审计可见。
2. 导出前清空：每轮从「除保护文件（README.md / LICENSE）外全部清空」的仓库状态开始，
   只复制白名单文件。不依赖旧 Manifest。
3. 硬排除（HARD_EXCLUDE）：版权/隐私关键路径一旦被登记或收集到，**立即中止整次同步**。
4. 暂停公开（WITHHELD）：ocr_samples.json、theory_locate.json 原件维持本地不公开；
   公开版由 make_public_evidence.py 生成（*_public.json）并单独登记。
5. 导出时改写（REDACTIONS）：public_redactions.json 中的规则只作用于公开副本
   （锚点定位整段替换为原创摘要），本地原始研究文件永不修改；锚点失效即中止（exit 7）。
6. 脱敏：所有文本文件里的本机绝对路径替换为占位符。
7. 可复算：UPLOAD_MANIFEST.csv 的 bytes/SHA-256 一律取脱敏+改写后的最终公开文件。
8. 同步差异报告：每轮生成 SYNC_DIFF.md（本轮导出树 相对 origin/main 的增/改/删清单）。
9. 生成后校验（推送前门禁）：仓库文件 ↔ Manifest 双向对应、全部文件在白名单/保护/生成
   名单内、SHA-256 可复算、硬排除命中为 0。任一失败即中止，不提交、不推送。

用法
----
    python poetry-database/tools/github_sync.py            # 同步并推送
    python poetry-database/tools/github_sync.py --dry-run  # 白名单审计，不建暂存不推送

环境变量（测试与特殊情况用）
----
    GITHUB_SYNC_REPO_URL    覆盖远端地址（默认 GitHub HTTPS；本机凭据走 gh）
    GITHUB_SYNC_STAGING     覆盖暂存根目录（默认 ~/Desktop/workbuddy/<日期>/.tmp/）

提交身份：固定使用 git 全局账户；仓库本地不设 user.*。
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
DBROOT = TOOLS.parent
PROJECT = DBROOT.parent

REPO_URL = os.environ.get(
    "GITHUB_SYNC_REPO_URL",
    "https://github.com/iop666/Poetry-Generation-Skill.git",
)
TODAY = datetime.date.today().isoformat()
_DEFAULT_STAGING = Path.home() / "Desktop" / "workbuddy" / TODAY / ".tmp" / (
    TODAY + "_临时_GitHub同步暂存"
)
STAGING = Path(os.environ.get("GITHUB_SYNC_STAGING", str(_DEFAULT_STAGING)))
CLONE = STAGING / "repo"

# ---------- 逐文件白名单（唯一导出来源，默认拒绝未登记文件） ----------
ALLOWLIST_PATH = TOOLS / "public_files.txt"

# 原目录级包含的八棵树根：仅用于「默认拒绝审计」（谁在树下却未登记）
LEGACY_TREE_ROOTS = [
    "docs",
    "诗词格律引擎",
    "poetry-database/reports",
    "poetry-database/tools",
    "poetry-database/catalog",
    "poetry-database/research",
    "poetry-database/audit",
    "poetry-database/sources",
]

# ---------- 暂停公开（R2-16B 审核裁决 2026-11-21：原件维持本地） ----------
WITHHELD = [
    (
        "poetry-database/raw/r2_04_evidence/ocr_samples.json",
        "R2-16B 裁决：维持 WITHHELD。公开版 ocr_samples_public.json 只保留页码/字符统计/质量标记，"
        "不保留 OCR 正文前缀（make_public_evidence.py 生成）",
    ),
    (
        "poetry-database/raw/r2_04_evidence/theory_locate.json",
        "R2-16B 裁决：维持 WITHHELD。公开版 theory_locate_public.json 保留页码/主题/核验状态，"
        "引文以 SHA-256 代替（make_public_evidence.py 生成）",
    ),
]

# ---------- 导出时改写规则（本地原件永不修改） ----------
REDACTIONS_PATH = TOOLS / "public_redactions.json"

# ---------- 硬排除：命中即中止整次同步（优先级最高） ----------
HARD_EXCLUDE_PARTS = [
    "/poetry-database/raw/r2_04_evidence/full/",
    "/poetry-database/raw/r2_04_evidence/chapters/",
    "/books/", "/raw/books",
    "/database/", "/normalized/",
    "/raw/r2_08/cache/", "/raw/r2_09/images/", "/raw/r2_11/images/",
    "/raw/r2_12/facsimile/",
    "/.workbuddy/",
]
HARD_EXCLUDE_SUFFIX = (".db", ".sqlite", ".wal", ".shm", ".pdf", ".epub", ".mobi")

# ---------- 软排除：常规噪声，跳过并记录（一般不应出现在白名单里） ----------
SOFT_EXCLUDE_PARTS = ["/.git/", "/__pycache__/"]
SOFT_EXCLUDE_SUFFIX = (".pyc", ".pyo", ".DS_Store")

MAX_FILE_BYTES = 90 * 1024 * 1024  # GitHub 单文件硬上限 100 MB，留 10 MB 余量

# ---------- 保护名单：清空导出树时保留（仓库级所有者维护内容） ----------
PROTECTED = {"README.md", "LICENSE"}
# ---------- 工具生成名单：每轮由本脚本重新生成，不属于 Manifest ----------
GENERATED = {
    ".gitignore", "UPLOAD_MANIFEST.csv", "UPLOAD_REPORT.md",
    "GITHUB_SYNC.md", "REPORTS_INDEX.md", "SYNC_DIFF.md",
}

# ---------- 脱敏规则 ----------
SANITIZE = [
    (re.compile(r"/Users/[^/\s\"']+/Desktop/任务列表/诗词"), "<PROJECT_ROOT>"),
    (re.compile(r"~/Desktop/任务列表/诗词"), "<PROJECT_ROOT>"),
    (re.compile(r"/Users/[^/\s\"']+/Desktop/workbuddy"), "<LOCAL_WORKBUDDY>"),
    (re.compile(r"~/Desktop/workbuddy"), "<LOCAL_WORKBUDDY>"),
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


def _norm(rel):
    return "/" + rel.replace(os.sep, "/")


def is_hard_excluded(rel):
    s = _norm(rel)
    if any(x in s for x in HARD_EXCLUDE_PARTS):
        return True
    return rel.lower().endswith(HARD_EXCLUDE_SUFFIX)


def is_soft_excluded(rel):
    s = _norm(rel)
    if any(x in s for x in SOFT_EXCLUDE_PARTS):
        return True
    return rel.endswith(SOFT_EXCLUDE_SUFFIX)


def load_allowlist():
    """读取逐文件白名单。重复登记即失败；硬排除路径混入即失败。"""
    if not ALLOWLIST_PATH.exists():
        log("ABORT 白名单文件不存在:", ALLOWLIST_PATH)
        sys.exit(4)
    entries = []
    seen = set()
    for raw in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rel = line.replace("\\", "/")
        if rel in seen:
            log("ABORT 白名单重复登记:", rel)
            sys.exit(4)
        seen.add(rel)
        if is_hard_excluded(rel):
            log("ABORT 白名单登记了硬排除路径（版权/隐私关键）:", rel)
            sys.exit(4)
        entries.append(rel)
    return entries


def default_deny_audit(allow):
    """默认拒绝审计：原八棵树根下存在、但未登记的文件（不含保护/生成文件本身）。"""
    allowset = set(allow)
    denied = []
    for root in LEGACY_TREE_ROOTS:
        base = PROJECT / root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(PROJECT).as_posix()
            if rel in allowset:
                continue
            denied.append(rel)
    return sorted(denied)


def collect(allow):
    """按白名单收集文件。条目缺失记 WARN；硬/软排除兜底；返回 (picked, excluded)。"""
    picked = []
    excluded = []
    for rel in allow:
        p = PROJECT / rel
        if not p.exists():
            log("WARN 白名单文件本地缺失:", rel)
            excluded.append((rel, "白名单文件本地缺失"))
            continue
        if p.is_dir():
            log("WARN 白名单条目是目录（应为逐文件登记）:", rel)
            excluded.append((rel, "白名单条目是目录"))
            continue
        if is_hard_excluded(rel):
            log("ABORT 硬排除命中:", rel)
            log("同步已中止，未生成、未提交、未推送。")
            sys.exit(4)
        if is_soft_excluded(rel):
            excluded.append((rel, "软排除（噪声文件）"))
            continue
        size = p.stat().st_size
        if size > MAX_FILE_BYTES:
            log("SKIP 超限", size, rel)
            excluded.append((rel, f"超单文件上限 {size} 字节"))
            continue
        picked.append((rel, p, size))
    picked.sort()
    return picked, excluded


def load_redactions():
    if not REDACTIONS_PATH.exists():
        return {}
    data = json.loads(REDACTIONS_PATH.read_text(encoding="utf-8"))
    by_file = {}
    for r in data.get("rules", []):
        by_file.setdefault(r["file"], []).append(r)
    return by_file


def apply_export_copy(src, dst, rel, red_by_file):
    """复制一个白名单文件到导出树：脱敏 +（命中规则的）导出时改写。

    返回 treatment。本地原件只读。改写锚点失效即 exit 7。"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    rules = red_by_file.get(rel, [])
    if src.name in ("github_sync.py",):
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
        treatment = "CLEAN"
        if new != txt:
            treatment = "SANITIZED"
        if rules:
            for r in rules:
                s, e = r["start"], r["end"]
                i = new.find(s)
                if i < 0:
                    log(f"ABORT 改写锚点未找到（规则 {r.get('rule_id')}）: {rel} :: {s[:30]}...")
                    sys.exit(7)
                j = new.find(e, i + len(s))
                if j < 0:
                    log(f"ABORT 改写结束锚点未找到（规则 {r.get('rule_id')}）: {rel} :: {e[:30]}...")
                    sys.exit(7)
                new = new[:i] + r["replacement"] + new[j + len(e):]
                treatment = "REDACTED_PUBLIC"
        dst.write_text(new, encoding="utf-8", newline="\n")
        return treatment
    shutil.copy2(src, dst)
    return "COPIED"


def git(args, check=True):
    return subprocess.run(
        ["git", "-C", str(CLONE)] + args,
        check=check, capture_output=True, text=True,
    )


def ensure_clone():
    """取回远端最新 main 并让工作树与之完全一致。失败立即中止，绝不基于陈旧状态操作。"""
    if (CLONE / ".git").exists():
        git(["fetch", "origin", "main"])
        git(["config", "core.autocrlf", "false"])
        git(["reset", "--hard", "origin/main"])
    else:
        if CLONE.exists():
            shutil.rmtree(CLONE)
        subprocess.run(["git", "clone", REPO_URL, str(CLONE)], check=True)
        git(["config", "core.autocrlf", "false"])
        git(["reset", "--hard", "origin/main"])
    head = git(["rev-parse", "HEAD"]).stdout.strip()
    base = git(["rev-parse", "origin/main"]).stdout.strip()
    if head != base:
        log(f"ABORT 工作树 HEAD {head} != origin/main {base}，状态陈旧，中止。")
        sys.exit(5)


def wipe_stale():
    """清空导出树：除 .git/ 与保护名单外全部删除（「每轮从空目录开始」）。"""
    removed = []
    for p in list(CLONE.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(CLONE).as_posix()
        if rel.startswith(".git/"):
            continue
        if rel in PROTECTED:
            continue
        p.unlink()
        removed.append(rel)
    for dirpath, dirnames, filenames in os.walk(CLONE, topdown=False):
        d = Path(dirpath)
        if d == CLONE or str(d).startswith(str(CLONE / ".git")):
            continue
        try:
            d.rmdir()
        except OSError:
            pass
    return removed


def sensitive_scan():
    """推送前硬门禁：残留本机路径 / 手机号 / 凭据就中止。"""
    blockers = []
    emails = set()
    pats = [
        ("本机家目录", re.compile(r"/Users/")),
        ("手机号", re.compile(r"(?<![A-Za-z0-9])1[3-9]\d{9}(?![A-Za-z0-9])")),
        ("API 凭据", re.compile(r"(?:Bearer\s+[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,})")),
    ]
    for p in CLONE.rglob("*"):
        if (not p.is_file() or ".git" in p.parts
                or p.name in ("UPLOAD_MANIFEST.csv", "github_sync.py")):
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


def verify_export(rows, allow):
    """生成后校验（推送前门禁）。任何失败都以非零码中止。"""
    problems = []
    allowset = set(allow)
    actual = set()
    for p in CLONE.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(CLONE).as_posix()
        if rel.startswith(".git/"):
            continue
        actual.add(rel)
    expected = {r["path"] for r in rows}
    allowed = PROTECTED | GENERATED
    residue = sorted(actual - expected - allowed)
    missing = sorted(expected - actual)
    outside = sorted((actual - allowed) - allowset)
    if residue:
        problems.append("未登记残留文件: " + "; ".join(residue[:20]))
    if missing:
        problems.append("Manifest 登记但磁盘缺失: " + "; ".join(missing[:20]))
    if outside:
        problems.append("导出树中存在白名单外文件: " + "; ".join(outside[:20]))
    mism = []
    for r in rows:
        f = CLONE / r["path"]
        if not f.exists():
            continue
        if sha256(f) != r["sha256"]:
            mism.append(r["path"])
    if mism:
        problems.append("SHA-256 与最终公开文件不符: " + "; ".join(mism[:20]))
    hard_hits = sorted(rel for rel in actual if is_hard_excluded(rel))
    if hard_hits:
        problems.append("最终导出树命中硬排除路径: " + "; ".join(hard_hits[:20]))
    if problems:
        for x in problems:
            log("VERIFY FAIL:", x)
        log("生成后校验未通过，已中止，不提交、不推送。")
        sys.exit(6)
    log(f"VERIFY PASS：导出树 {len(actual)} 文件 = Manifest {len(rows)} + 保护 {len(PROTECTED & actual)} + 生成 {len(GENERATED & actual)}；全部在逐文件白名单内；硬排除 0；SHA-256 全部可复算。")


def write_sync_diff():
    """生成本轮导出树相对 origin/main 的差异报告（增/改/删）。"""
    git(["add", "-A"])
    ns = subprocess.run(
        ["git", "-C", str(CLONE), "diff", "--cached", "--name-status", "origin/main"],
        capture_output=True, text=True, check=True,
    ).stdout
    numstat = subprocess.run(
        ["git", "-C", str(CLONE), "diff", "--cached", "--numstat", "origin/main"],
        capture_output=True, text=True, check=True,
    ).stdout
    counts = {}
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            counts[parts[2]] = f"+{parts[0]}/-{parts[1]}"
    lines_out = [
        "# SYNC_DIFF —— 本轮公开目录相对上一轮（origin/main）的差异",
        "",
        f"- 生成时间：{datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}",
        "- 对比基准：origin/main（导出前 HEAD）",
        "- 状态：A=新增 M=修改 D=删除 R=改名；增/删行数来自 git numstat",
        "",
        "| 状态 | 路径 | 增/删行 |",
        "|---|---|---|",
    ]
    n = {"A": 0, "M": 0, "D": 0, "R": 0}
    for line in ns.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        st = parts[0][0]
        path = parts[-1]
        n[st] = n.get(st, 0) + 1
        lines_out.append(f"| {st} | `{path}` | {counts.get(path, '')} |")
    lines_out += [
        "",
        f"合计：新增 {n.get('A', 0)}、修改 {n.get('M', 0)}、删除 {n.get('D', 0)}、改名 {n.get('R', 0)}。",
        "（SYNC_DIFF.md 自身为每轮重新生成，其自身变更不列入本表。）",
        "",
        "Manifest 与导出树的双向一致性由 github_sync.py verify_export 在推送前强制校验。",
        "",
    ]
    (CLONE / "SYNC_DIFF.md").write_text("\n".join(lines_out), encoding="utf-8", newline="\n")
    log(f"SYNC_DIFF：新增 {n.get('A', 0)} / 修改 {n.get('M', 0)} / 删除 {n.get('D', 0)} / 改名 {n.get('R', 0)}")


def restore_readme():
    """README 由项目所有者维护，本工具绝不覆盖。"""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    allow = load_allowlist()
    log("逐文件白名单登记:", len(allow), "个文件（未登记文件一律不导出）")

    denied = default_deny_audit(allow)
    log("默认拒绝审计：原八棵树下未登记文件", len(denied), "个")
    for rel in denied[:30]:
        log("  默认拒绝:", rel)

    red_by_file = load_redactions()
    if red_by_file:
        log("导出时改写规则:", sum(len(v) for v in red_by_file.values()),
            "条，涉及", len(red_by_file), "个文件")

    for rel, why in WITHHELD:
        log("暂停公开:", rel, "——", why)
        if rel in allow:
            log("ABORT 暂停公开文件被登记进白名单:", rel)
            sys.exit(4)

    picked, excluded = collect(allow)
    log("本轮导出文件数:", len(picked), "合计字节:", sum(x[2] for x in picked))
    if excluded:
        log("白名单异常条目（共 %d 项）:" % len(excluded))
        for rel, why in excluded[:30]:
            log("  -", rel, "——", why)

    if args.dry_run:
        log("DRY RUN 完成。首 10 项:", [r[0] for r in picked[:10]])
        return

    STAGING.mkdir(parents=True, exist_ok=True)
    ensure_clone()

    removed = wipe_stale()
    log("清空导出树：删除上一轮残留 %d 个文件（保护名单除外）" % len(removed))

    rows = []
    stats = {}
    redacted_files = []
    for rel, src, size in picked:
        dst = CLONE / rel
        kind = apply_export_copy(src, dst, rel, red_by_file)
        stats[kind] = stats.get(kind, 0) + 1
        if kind == "REDACTED_PUBLIC":
            redacted_files.append(rel)
        rows.append({
            "path": rel,
            "bytes": str(dst.stat().st_size),
            "sha256": sha256(dst),
            "treatment": kind,
        })
    if redacted_files:
        log("导出时改写生效的文件:")
        for rel in redacted_files:
            log("  REDACTED_PUBLIC:", rel)

    restore_readme()

    (CLONE / ".gitignore").write_text(
        "\n".join([
            ".DS_Store", "__pycache__/", "*.pyc", "*.pyo",
            "# 以下内容按项目规则永不上传（R2-16C 起为硬排除，命中即中止同步）：",
            "# poetry-database/database/  (SQLite，含本机绝对路径)",
            "# poetry-database/normalized/ (超 GitHub 单文件上限的语料)",
            "# books/, poetry-database/raw/books* (现代版权书全文与 OCR)",
            "# poetry-database/raw/r2_04_evidence/full|chapters (现代版权著作连续正文)",
            "# poetry-database/raw/*/images/, */facsimile/ (书页图像)",
            "# .workbuddy/ (本机记忆与临时数据)",
            "",
        ]), encoding="utf-8", newline="\n"
    )

    found_emails = sensitive_scan()

    with open(CLONE / "UPLOAD_MANIFEST.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "bytes", "sha256", "treatment"])
        w.writeheader()
        w.writerows(rows)

    (CLONE / "GITHUB_SYNC.md").write_text("""# 仓库同步说明（工具生成，勿手改）

本文件由 `poetry-database/tools/github_sync.py`（严格逐文件白名单 v3，R2-16C 第二轮）生成。
项目介绍见 `README.md`（人工维护，工具不会覆盖）。

## 同步机制（v3）

- **逐文件白名单，默认拒绝**：唯一导出来源是 `poetry-database/tools/public_files.txt` 登记的文件；
  未登记文件一律不导出。新增文件必须先通过公开审计并登记。
- 每轮导出开始时，仓库工作树除 `README.md`、`LICENSE`（保护名单）外**全部清空**，再复制白名单文件。
- 版权/隐私关键路径为硬排除：白名单或收集阶段命中即中止整次同步。
- **导出时改写**：`tools/public_redactions.json` 声明的逐字段落只作用于公开副本
  （替换为原创摘要），本地原始研究文件永不修改。
- **暂停公开**：`raw/r2_04_evidence/ocr_samples.json`、`theory_locate.json` 原件维持本地（R2-16B 裁决）；
  公开版 `ocr_samples_public.json`、`theory_locate_public.json` 由 `tools/make_public_evidence.py` 生成。
- 每轮生成 `SYNC_DIFF.md`（相对上一轮公开状态的增/改/删清单）与 `UPLOAD_MANIFEST.csv`
  （逐文件 SHA-256，按脱敏+改写后的最终公开文件计算）。
- 推送为普通 fast-forward 推送（非 force）。

## 仓库内容

| 路径 | 内容 |
|---|---|
| `AGENTS.md` / `AGENT_REPORTING_STANDARD.md` | 项目长期指令与汇报制度 |
| `docs/` | 原始方案、历史文档与原 README 备份 |
| `诗词格律引擎/` | 格律引擎代码、独立测试集、原创知识库与执行报告（引擎冻结，仅研究用） |
| `poetry-database/reports/` | **逐轮完整报告**（含每轮 `COMPLETE_REPORT.md` 与全部交付件） |
| `poetry-database/tools/` | 审计与同步工具（逐文件白名单/改写规则/公开证据生成） |
| `poetry-database/catalog|research|audit|sources/` | 词谱、书目与审计元数据（公有领域古籍与事实数据） |
| `poetry-database/raw/` | 经 R2-16B 审查的证据与笔记（公开版/改写版） |
| `SYNC_DIFF.md` | 本轮相对上一轮的公开目录差异 |
| `UPLOAD_MANIFEST.csv` / `UPLOAD_REPORT.md` | 逐文件校验值与上传说明、排除项 |

## 不上传的内容（硬性）

1. **数据库文件**：`poetry.db` 等 SQLite 及超 GitHub 单文件上限的二进制。
2. **版权书全文**：`books/`、`raw/books*`、`raw/r2_04_evidence/full|chapters`（现代版权著作正文）。
3. **暂停公开原件**（R2-16B 裁决）：`ocr_samples.json`、`theory_locate.json`（公开版为 `*_public.json`）。
4. **二进制工具**：`tools/ocr_vision`（macOS Mach-O，公开审计决定不公开）。
5. **本机个人信息**：所有文本中的本机家目录与绝对路径已替换为占位符。

## 同步方式

每轮任务完成后，在项目根目录执行：

```bash
python poetry-database/tools/github_sync.py
```

新产出文件（如新一轮报告）必须先登记进 `tools/public_files.txt` 才会被导出。
远端认证使用 HTTPS + `gh` CLI 凭据；`GITHUB_SYNC_REPO_URL` / `GITHUB_SYNC_STAGING`
可覆盖远端与暂存位置。加 `--dry-run` 只做白名单审计，不建暂存、不推送。
""", encoding="utf-8", newline="\n")

    total = sum(int(r["bytes"]) for r in rows)
    excluded_rows = [(rel, why) for rel, why in WITHHELD]
    excluded_rows += [
        ("poetry-database/database/poetry.db", "SQLite 数据库，含本机绝对路径（硬排除）"),
        ("poetry-database/normalized/*.jsonl", "超 GitHub 单文件上限语料（硬排除）"),
        ("books/*.pdf|epub", "现代版权书全文，项目规则禁止分发（硬排除）"),
        ("poetry-database/raw/r2_04_evidence/full|chapters", "现代版权著作连续正文（硬排除，历史清理对象）"),
        ("poetry-database/raw/*/images|facsimile", "书页影印，版权风险（硬排除）"),
        (".workbuddy/**", "本机记忆与临时数据（硬排除）"),
        ("poetry-database/tools/ocr_vision", "macOS Mach-O 二进制，公开审计决定不公开（R2-16C 第二轮）"),
    ]
    excluded_rows += [(rel, why) for rel, why in excluded]
    if denied:
        excluded_rows.append((f"（原八棵树下未登记文件共 {len(denied)} 个）", "默认拒绝：未通过公开审计登记"))
    lines = [
        "# GitHub 上传报告",
        "",
        f"- 时间：{datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}",
        f"- 仓库：`{REPO_URL}`（公开）",
        "- 同步机制：严格逐文件白名单 v3（默认拒绝未登记文件）——导出树先清空（保护名单除外），"
        "再复制 `tools/public_files.txt` 登记的文件",
        f"- 本轮导出：**{len(rows)}** 个文件，合计 **{total:,}** 字节",
        "- 脱敏处理：" + "、".join(f"{k} {v}" for k, v in sorted(stats.items())),
        f"- 推送前门禁：本机路径 / 手机号 / 凭据残留 **0 处**；邮箱 {len(found_emails)} 个"
        + (f"（{', '.join(found_emails[:10])}）" if found_emails else ""),
        "- 生成后校验：Manifest 双向对应、全部文件在白名单内、SHA-256（脱敏+改写后文件）可复算、硬排除 0。",
        "- 差异报告：见 [SYNC_DIFF.md](SYNC_DIFF.md)。",
        "",
        "## 排除项及原因",
        "",
        "| 路径 | 原因 |",
        "|---|---|",
    ]
    lines += [f"| `{p}` | {why} |" for p, why in excluded_rows]
    lines += [
        "",
        "## 复核",
        "",
        "逐文件 SHA-256 见 `UPLOAD_MANIFEST.csv`。",
        "可用 `python poetry-database/tools/github_sync.py --dry-run` 复算白名单与默认拒绝审计。",
        "",
    ]
    (CLONE / "UPLOAD_REPORT.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")

    # 根目录报告索引
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
        "上传范围与排除项见 [UPLOAD_REPORT.md](UPLOAD_REPORT.md)；差异见 [SYNC_DIFF.md](SYNC_DIFF.md)；"
        "同步机制见 [GITHUB_SYNC.md](GITHUB_SYNC.md)。",
        "",
    ]
    (CLONE / "REPORTS_INDEX.md").write_text("\n".join(idx), encoding="utf-8", newline="\n")
    log("报告索引：", len(reports), "轮")

    # 同步差异报告（在全部生成文件就绪后计算，git add -A 在函数内执行）
    write_sync_diff()

    verify_export(rows, allow)

    git(["add", "-A"])
    r = git(["diff", "--cached", "--quiet"], check=False)
    if r.returncode == 0:
        log("无变更需要提交。")
    else:
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
