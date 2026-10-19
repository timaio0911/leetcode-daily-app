"""阶段 4：二刷/复盘标记 + 错题本 + 题号聚合索引（方案 §5 阶段 4）。

- frontmatter 已留 `reviewed: []` 字段：记录二刷日期列表。
- 题目录下可追加 `solution-2.py`、`review-<date>.md`（方案 §2.2 备注）。
- `problems-by-id/` 索引：软件生成的虚拟汇总（不复制文件），跨日期聚合同一题号。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.vault import (
    DayEntry,
    ProblemEntry,
    format_inline_list,
    parse_frontmatter,
    scan_vault,
)

REVIEW_TEMPLATE = "review.md"
SOLUTION2_TEMPLATE = "solution-2.py"
PROBLEMS_BY_ID_DIR = "problems-by-id"
INDEX_FILENAME = "INDEX.md"


# ---------- frontmatter reviewed 字段读写 ----------

def parse_reviewed(meta: dict[str, Any]) -> list[str]:
    """从 frontmatter dict 提取 reviewed 列表（兼容旧数据无该字段）。"""
    val = meta.get("reviewed")
    if isinstance(val, list):
        return [str(v) for v in val]
    return []


def load_reviewed(readme: Path) -> list[str]:
    if not readme.is_file():
        return []
    meta, _ = parse_frontmatter(readme.read_text(encoding="utf-8"))
    return parse_reviewed(meta)


def save_reviewed(readme: Path, reviewed: list[str]) -> None:
    """把 reviewed 列表写回 README.md 的 frontmatter（保留其余内容）。"""
    text = readme.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    if not meta:
        raise ValueError(f"frontmatter 缺失：{readme}")
    # 重建 frontmatter（保持原有 key 顺序，替换/追加 reviewed）
    lines = ["---"]
    for k, v in meta.items():
        if k == "reviewed":
            lines.append(f"reviewed: {format_inline_list(reviewed)}")
        else:
            if isinstance(v, bool):
                lines.append(f"{k}: {'true' if v else 'false'}")
            elif isinstance(v, int):
                lines.append(f"{k}: {v}")
            elif isinstance(v, list):
                lines.append(f"{k}: {format_inline_list(v)}")
            else:
                lines.append(f"{k}: {v}")
    if "reviewed" not in meta:
        lines.append(f"reviewed: {format_inline_list(reviewed)}")
    lines.append("---")
    new_text = "\n".join(lines) + "\n" + body
    readme.write_text(new_text, encoding="utf-8")


def mark_reviewed(problem_dir: Path, date: str) -> Path:
    """在题目录 README.md 的 reviewed 列表中追加一个日期（去重），并生成 review-<date>.md 复盘文件。"""
    readme = problem_dir / "README.md"
    reviewed = load_reviewed(readme)
    if date not in reviewed:
        reviewed.append(date)
        reviewed.sort()
        save_reviewed(readme, reviewed)
    review_file = problem_dir / f"review-{date}.md"
    if not review_file.exists():
        review_file.write_text(_review_stub(problem_dir, date), encoding="utf-8")
    return review_file


def _review_stub(problem_dir: Path, date: str) -> str:
    readme = problem_dir / "README.md"
    title = problem_dir.name
    if readme.is_file():
        meta, _ = parse_frontmatter(readme.read_text(encoding="utf-8"))
        title = str(meta.get("title", title))
    return (
        f"# 复盘：{title}\n\n"
        f"> 复盘日期：{date}\n\n"
        "## 卡住的地方\n-\n\n"
        "## 新学到的\n-\n\n"
        "## 下次注意\n-\n"
    )


def add_solution2(problem_dir: Path) -> Path:
    """在题目录下追加 solution-2.py（若不存在）。"""
    path = problem_dir / "solution-2.py"
    if not path.exists():
        path.write_text(
            "# 二刷代码\n"
            "class Solution:\n"
            "    def solve(self):\n"
            "        pass\n\n\n"
            'if __name__ == "__main__":\n'
            "    s = Solution()\n"
            "    s.solve()\n",
            encoding="utf-8",
        )
    return path


# ---------- 错题本 / 复盘筛选 ----------

def needs_review(p: ProblemEntry) -> bool:
    """错题判定：status 为 review 或 reviewed 为空（尚未复盘）。"""
    return p.status == "review" or not p.reviewed


def filter_mistakes(days: list[DayEntry]) -> list[DayEntry]:
    """错题本视图：返回需要复盘/二刷的题目（status=review 或 reviewed 为空）。"""
    out: list[DayEntry] = []
    for day in days:
        kept = [p for p in day.problems if needs_review(p)]
        if kept:
            out.append(DayEntry(date=day.date, problems=kept))
    return out


def filter_reviewed(days: list[DayEntry]) -> list[DayEntry]:
    """已复盘视图：返回 reviewed 非空的题目。"""
    out: list[DayEntry] = []
    for day in days:
        kept = [p for p in day.problems if p.reviewed]
        if kept:
            out.append(DayEntry(date=day.date, problems=kept))
    return out


# ---------- 按题号索引（跨日期聚合） ----------

@dataclass
class IdGroup:
    id: str
    title: str
    problems: list[ProblemEntry] = field(default_factory=list)


def group_by_id(days: list[DayEntry]) -> list[IdGroup]:
    """按题号聚合跨日期的同一题，返回按题号数字升序的分组。"""
    groups: dict[str, IdGroup] = {}
    for day in days:
        for p in day.problems:
            key = p.id
            if key not in groups:
                groups[key] = IdGroup(id=key, title=p.title)
            groups[key].problems.append(p)
    def sort_key(g: IdGroup) -> tuple[int, str]:
        return (int(g.id), g.id) if g.id.isdigit() else (1 << 60, g.id)
    return sorted(groups.values(), key=sort_key)


def render_id_index(groups: list[IdGroup]) -> str:
    lines = [
        "# 按题号索引",
        "",
        "> 由刷题管理软件自动生成（虚拟汇总，不复制文件）",
        "",
    ]
    for g in groups:
        lines.append(f"## {g.id}. {g.title}")
        lines.append("")
        for p in g.problems:
            rel = f"problems/{p.date}/{p.dir.name}/README"
            lines.append(f"- {p.date} — [[{rel}]]")
        lines.append("")
    return "\n".join(lines)


def write_id_index(vault: Path) -> Path:
    """生成/更新 problems-by-id/INDEX.md（幂等重建）。"""
    vault = Path(vault)
    days = scan_vault(vault)
    groups = group_by_id(days)
    out_dir = vault / PROBLEMS_BY_ID_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    index = out_dir / INDEX_FILENAME
    index.write_text(render_id_index(groups), encoding="utf-8")
    return index
