"""F5：一键提交 GitHub（方案 §4.2 gitops.py）。

用 subprocess 调本机 git（方案选型：行为最贴近手敲命令，不做凭据管理）。
commit 信息约定式：`<date>: add <id> <slug>`（如 `2026-06-04: add 0001 two-sum`）。
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class GitError(RuntimeError):
    """git 命令失败（含 stderr 输出）。"""


@dataclass
class GitStatus:
    branch: str
    changed: list[str] = field(default_factory=list)
    staged: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.changed and not self.staged


def _run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise GitError("未找到 git 命令，请确认本机已安装 git 并在 PATH 中。") from exc
    if check and proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} 失败：\n{proc.stderr.strip() or proc.stdout.strip()}")
    return proc


def ensure_repo(repo: Path) -> None:
    proc = _run_git(repo, "rev-parse", "--is-inside-work-tree", check=False)
    if proc.returncode != 0 or proc.stdout.strip() != "true":
        raise GitError(f"{repo} 不是 git 仓库（先 git init）")


def git_status(repo: Path) -> GitStatus:
    """扫描改动（untracked + modified + staged）。"""
    ensure_repo(repo)
    proc = _run_git(repo, "status", "--porcelain", "--branch")
    changed: list[str] = []
    staged: list[str] = []
    branch = ""
    for line in proc.stdout.splitlines():
        if line.startswith("##"):
            branch = line[2:].split("...")[0].strip()
            continue
        if len(line) < 4:
            continue
        index_state, worktree_state, path = line[0], line[1], line[3:]
        if index_state in ("?", "!") or worktree_state in ("?", "!"):
            # 未跟踪目录会展开为目录下全部文件（含忽略文件已被 git 自动排除）
            expanded = _expand_untracked(repo, path)
            changed.extend(expanded)
            continue
        if index_state != " ":
            staged.append(path)
        if worktree_state != " ":
            changed.append(path)
    return GitStatus(branch=branch, changed=changed, staged=staged)


def _expand_untracked(repo: Path, path: str) -> list[str]:
    """把未跟踪的目录展开为具体文件列表。"""
    target = repo / path
    if path.endswith("/") or (target.is_dir() and not target.is_file()):
        out: list[str] = []
        for f in sorted(target.rglob("*")):
            if f.is_file():
                out.append(f.relative_to(repo).as_posix())
        return out
    return [path]


def commit_all(repo: Path, message: str) -> str:
    """git add -A + commit；无可提交内容时返回说明而非报错。"""
    ensure_repo(repo)
    _run_git(repo, "add", "-A")
    proc = _run_git(repo, "diff", "--cached", "--quiet", check=False)
    if proc.returncode == 0:
        return "无改动可提交。"
    _run_git(repo, "commit", "-m", message)
    return f"已提交：{message}"


def push(repo: Path, remote: str = "origin") -> str:
    ensure_repo(repo)
    proc = _run_git(repo, "push", remote, check=False)
    if proc.returncode != 0:
        raise GitError(f"git push {remote} 失败：\n{proc.stderr.strip() or proc.stdout.strip()}")
    return f"已推送到 {remote}。"


def commit_message_for(date: str, problem_id: str, slug: str) -> str:
    """约定式提交信息：`<date>: add <id> <slug>`。

    date 用**归档日期**（题目录所在日期），与方案 §3.2 示例一致。
    """
    pad = problem_id.zfill(4) if problem_id.isdigit() else problem_id
    return f"{date}: add {pad} {slug}"


def has_remote(repo: Path, remote: str = "origin") -> bool:
    proc = _run_git(repo, "remote", check=False)
    return any(r.strip() == remote for r in proc.stdout.splitlines())


def remote_url(repo: Path, remote: str = "origin") -> str | None:
    proc = _run_git(repo, "remote", "get-url", remote, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None
