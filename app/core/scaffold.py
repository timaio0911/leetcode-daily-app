"""F1/F6：建目录、模板生成、更新 daily.md（方案 §4.2 scaffold.py）。

新建题目全链路：
1. 元数据（抓取成功 → 直接用；失败/关闭抓取 → 手动填写降级）
2. 建 `problems/<date>/<NNNN-slug>/` + `solution.py` + `README.md`（从 templates/ 渲染）
3. 创建/追加当日 `daily.md` 打卡行
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date as date_cls
from pathlib import Path

from app.core.leetcode import ProblemMeta
from app.core.resources import resolve_template
from app.core.vault import format_inline_list, parse_frontmatter

PROBLEM_TEMPLATE = "problem.md"
DAILY_TEMPLATE = "daily.md"
SOLUTION_TEMPLATE = "solution.py"
NOTES_MARK = "**今日心得**"  # daily.md 中用户手写段落的起点标记


@dataclass
class ScaffoldResult:
    problem_dir: Path
    readme: Path
    solution: Path
    daily: Path
    meta: ProblemMeta
    date: str
    reused: bool = False  # True = 目录已存在，未重复创建


def _render(template: str, mapping: dict[str, str]) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace("{" + key + "}", value)
    return out


def _load_template(vault: Path, name: str) -> str:
    path = resolve_template(vault, name)
    return path.read_text(encoding="utf-8")


def _pad_id(problem_id: str) -> str:
    return problem_id.zfill(4) if problem_id.isdigit() else problem_id


def _daily_rows(day_dir: Path) -> list[str]:
    """从当日各题 README 元数据重建打卡表格行（幂等更新的关键）。"""
    rows: list[str] = []
    for pdir in sorted(day_dir.iterdir()):
        if not pdir.is_dir():
            continue
        readme = pdir / "README.md"
        if not readme.is_file():
            continue
        meta, _ = parse_frontmatter(readme.read_text(encoding="utf-8"))
        pid = _pad_id(str(meta.get("id", "")))
        title = str(meta.get("title", ""))
        difficulty = str(meta.get("difficulty", ""))
        time_spent = str(meta.get("time_spent", "") or "-")
        rows.append(f"| {pid} {title} | {difficulty} | {time_spent} | "
                    f"[[problems/{day_dir.name}/{pdir.name}/README]] |")
    return rows


def _preserve_notes(old_text: str, new_text: str) -> str:
    """重建 daily.md 时保留用户手写的「今日心得」（标记行之后的内容）。"""
    if NOTES_MARK not in old_text or NOTES_MARK not in new_text:
        return new_text
    old_tail = old_text.split(NOTES_MARK, 1)[1]
    new_head = new_text.split(NOTES_MARK, 1)[0]
    return new_head + NOTES_MARK + old_tail


def update_daily(vault: Path, day: str) -> Path:
    """F6：创建/重建当日 daily.md（从题目元数据推导，重复调用安全）。"""
    vault = Path(vault)
    day_dir = vault / "problems" / day
    day_dir.mkdir(parents=True, exist_ok=True)
    rows = _daily_rows(day_dir)
    content = _render(_load_template(vault, DAILY_TEMPLATE), {
        "date": day,
        "count": str(len(rows)),
        "rows": "\n".join(rows) if rows else "| - | - | - | - |",
    })
    daily = day_dir / "daily.md"
    if daily.is_file():  # 打卡表格重建，但用户手写的今日心得不被覆盖
        content = _preserve_notes(daily.read_text(encoding="utf-8"), content)
    daily.write_text(content, encoding="utf-8")
    return daily


def scaffold_problem(
    vault: Path,
    meta: ProblemMeta,
    *,
    day: str | None = None,
) -> ScaffoldResult:
    """F1：按元数据创建题目文件夹 + solution.py + README.md，并更新 daily.md。"""
    vault = Path(vault)
    day = day or date_cls.today().isoformat()
    pad_id = _pad_id(meta.id)
    dir_name = f"{pad_id}-{meta.slug}"
    day_dir = vault / "problems" / day
    problem_dir = day_dir / dir_name

    id_title = f"{pad_id}. {meta.title}"
    mapping = {
        "id": pad_id,
        "id_title": id_title,
        "title": meta.title,
        "url": meta.url,
        "slug": meta.slug,
        "difficulty": meta.difficulty,
        # 模板本身带方括号，故只填列表内容
        "tags": format_inline_list(meta.tags)[1:-1],
        "date": day,
    }

    reused = problem_dir.is_dir()
    problem_dir.mkdir(parents=True, exist_ok=True)

    readme = problem_dir / "README.md"
    solution = problem_dir / "solution.py"
    if not readme.is_file():
        readme.write_text(_render(_load_template(vault, PROBLEM_TEMPLATE), mapping), encoding="utf-8")
    if not solution.is_file():
        solution.write_text(_render(_load_template(vault, SOLUTION_TEMPLATE), mapping), encoding="utf-8")

    daily = update_daily(vault, day)
    return ScaffoldResult(
        problem_dir=problem_dir, readme=readme, solution=solution,
        daily=daily, meta=meta, date=day, reused=reused,
    )


def is_valid_slug(slug: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9-]+", slug))
