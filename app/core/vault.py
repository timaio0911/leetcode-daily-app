"""扫描仓库、解析 frontmatter、基础统计（方案 §4.2 vault.py）。

数据即文件系统：problems/<YYYY-MM-DD>/<NNNN-slug>/README.md 的 frontmatter 即数据库。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FM_DELIM = "---"
DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PROBLEM_DIR_RE = re.compile(r"^(\d+)-(.+)$")


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """解析 YAML frontmatter 子集，返回 (meta, body)。

    为避免引入 PyYAML 依赖，仅支持模板用到的语法：
    - `key: value`（字符串/数字/布尔）
    - `key: [a, b]`（行内列表，标签含逗号时用引号包裹）
    - `key: []`（空列表）
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != FM_DELIM:
        return {}, text
    meta: dict[str, Any] = {}
    for i in range(1, len(lines)):
        if lines[i].strip() == FM_DELIM:
            body = "\n".join(lines[i + 1:]).lstrip("\n")
            return meta, body
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        raw = raw.split("  #")[0].strip()  # 去掉行尾注释（如 status: done  # todo/doing/done）
        if raw.startswith("[") and raw.endswith("]"):
            meta[key] = _split_inline_list(raw[1:-1]) if raw[1:-1].strip() else []
        elif raw.lower() in ("true", "false"):
            meta[key] = raw.lower() == "true"
        elif re.fullmatch(r"-?\d+", raw):
            meta[key] = int(raw)
        else:
            meta[key] = raw.strip("'\"")
    return meta, text


def _split_inline_list(inner: str) -> list[str]:
    """行内列表拆分：支持引号包裹的含逗号元素（如 "a, b"）。"""
    items: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    for ch in inner:
        if quote:
            if ch == quote:
                quote = None
            else:
                buf.append(ch)
        elif ch in "'\"":
            quote = ch
        elif ch == ",":
            items.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    items.append("".join(buf).strip())
    return [i for i in items if i]


def format_inline_list(tags: list[str]) -> str:
    """tags 序列化为 frontmatter 行内列表（含方括号）；含逗号/引号的元素加引号。"""
    def fmt(tag: str) -> str:
        return f'"{tag}"' if any(c in tag for c in ',[]"\'') else tag
    return "[" + ", ".join(fmt(t) for t in tags) + "]"


@dataclass
class ProblemEntry:
    id: str
    slug: str
    title: str
    url: str
    difficulty: str
    tags: list[str]
    date: str
    status: str
    time_spent: str
    dir: Path
    readme: Path
    solution: Path | None
    reviewed: list[str] = field(default_factory=list)  # 二刷日期列表

    @property
    def id_title(self) -> str:
        return f"{self.id}. {self.title}" if self.title else self.id


@dataclass
class DayEntry:
    date: str
    problems: list[ProblemEntry] = field(default_factory=list)


def scan_vault(vault: Path) -> list[DayEntry]:
    """扫描 problems/ 下按日期归档的题目，返回按日期倒序的列表。"""
    problems_root = vault / "problems"
    days: list[DayEntry] = []
    if not problems_root.is_dir():
        return days
    for date_dir in sorted(problems_root.iterdir(), reverse=True):
        if not date_dir.is_dir() or not DATE_DIR_RE.match(date_dir.name):
            continue
        day = DayEntry(date=date_dir.name)
        for pdir in sorted(date_dir.iterdir()):
            if not pdir.is_dir():
                continue
            m = PROBLEM_DIR_RE.match(pdir.name)
            if not m:
                continue
            readme = pdir / "README.md"
            meta: dict[str, Any] = {}
            if readme.is_file():
                meta, _ = parse_frontmatter(readme.read_text(encoding="utf-8"))
            solution = pdir / "solution.py"
            day.problems.append(ProblemEntry(
                id=str(meta.get("id", m.group(1))),
                slug=str(meta.get("slug", m.group(2))) if "slug" in meta else m.group(2),
                title=str(meta.get("title", "")),
                url=str(meta.get("url", "")),
                difficulty=str(meta.get("difficulty", "")),
                tags=meta.get("tags") if isinstance(meta.get("tags"), list) else [],
                date=str(meta.get("date", date_dir.name)),
                status=str(meta.get("status", "todo")),
                time_spent=str(meta.get("time_spent", "") or ""),
                dir=pdir,
                readme=readme,
                solution=solution if solution.is_file() else None,
                reviewed=[str(v) for v in meta.get("reviewed", [])]
                    if isinstance(meta.get("reviewed"), list) else [],
            ))
        if day.problems:
            days.append(day)
    return days


def summarize(days: list[DayEntry]) -> dict[str, Any]:
    """基础统计（完整看板 F3 属于阶段 3，这里给 CLI 用的最小集）。"""
    total = sum(len(d.problems) for d in days)
    by_difficulty: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for d in days:
        for p in d.problems:
            by_difficulty[p.difficulty or "未知"] = by_difficulty.get(p.difficulty or "未知", 0) + 1
            by_status[p.status or "todo"] = by_status.get(p.status or "todo", 0) + 1
    return {
        "total": total,
        "days": len(days),
        "by_difficulty": by_difficulty,
        "by_status": by_status,
    }
