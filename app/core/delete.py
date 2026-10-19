"""删除题目记录：选择并删除之前记录的题目（新增功能）。

设计约定（与 scaffold 对称、与「daily.md 是重建不是追加」一致）：
- 只删 `problems/<date>/<NNNN-slug>/` 整个题目录（README / 代码 / 复盘笔记一并删除）；
- 严格校验路径，绝不删题目录以外的任何东西（安全红线）；
- 删除后按剩余题目 frontmatter 重建当日 `daily.md`（幂等，等同 scaffold.update_daily）；
- 若生成过 `problems-by-id/INDEX.md` 则同步重建（幂等），避免留下失效链接；
- README 统计段落不自动改（与新建题目一致，走「更新 README 统计段落」按钮）；
- 删除即真删（不做回收站）；误删可用 git 找回（数据仓库有提交历史）。
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from app.core.vault import DATE_DIR_RE, PROBLEM_DIR_RE, ProblemEntry


class DeleteError(Exception):
    """删除失败（路径非法 / 不存在等）。"""


@dataclass
class DeleteResult:
    deleted: list[Path] = field(default_factory=list)            # 被删除的题目录
    dates: list[str] = field(default_factory=list)               # 受影响归档日期（去重）
    daily_files: dict[str, Path] = field(default_factory=dict)   # date -> 重建后的 daily.md
    index: Path | None = None                                    # 重建后的题号索引（未生成过则 None）


def describe(problem: ProblemEntry) -> str:
    """删除确认框/CLI 用的单行描述。"""
    return f"{problem.date}  {problem.id.zfill(4)} {problem.title}  [{problem.difficulty or '?'}]"


def _resolve_problem_dir(vault: Path, problem: ProblemEntry | Path) -> tuple[Path, str]:
    """解析并校验题目录，返回 (题目录绝对路径, 归档日期)；不合规抛 DeleteError。"""
    vault = Path(vault).resolve()
    raw = problem.dir if isinstance(problem, ProblemEntry) else problem
    pdir = Path(raw).resolve()
    problems_root = (vault / "problems").resolve()
    try:
        rel = pdir.relative_to(problems_root)
    except ValueError:
        raise DeleteError(f"拒绝删除：{pdir} 不在数据目录 {problems_root} 下") from None
    if len(rel.parts) != 2:
        raise DeleteError(f"拒绝删除：{pdir} 不是 problems/<date>/<NNNN-slug> 形式的题目录")
    date_name, dir_name = rel.parts
    if not DATE_DIR_RE.match(date_name):
        raise DeleteError(f"拒绝删除：{date_name} 不是合法归档日期目录（YYYY-MM-DD）")
    if not PROBLEM_DIR_RE.match(dir_name):
        raise DeleteError(f"拒绝删除：{dir_name} 不是合法题目目录（NNNN-slug）")
    if not pdir.is_dir():
        raise DeleteError(f"题目目录不存在：{pdir}")
    return pdir, date_name


def delete_problem(vault: Path, problem: ProblemEntry | Path) -> DeleteResult:
    """删除单个题目记录（等同 delete_problems(vault, [problem])）。"""
    return delete_problems(vault, [problem])


def delete_problems(vault: Path, problems: list[ProblemEntry] | list[Path]) -> DeleteResult:
    """批量删除题目记录，并同步重建受影响的 daily.md 与题号索引。"""
    from app.core.review import INDEX_FILENAME, PROBLEMS_BY_ID_DIR, write_id_index
    from app.core.scaffold import update_daily

    vault = Path(vault)
    result = DeleteResult()
    seen: set[Path] = set()
    for problem in problems:
        raw = problem.dir if isinstance(problem, ProblemEntry) else problem
        key = Path(raw).resolve()
        if key in seen:  # 重复选择（同一题既在树里选中又在对话框勾选）只删一次
            continue
        seen.add(key)
        pdir, date_name = _resolve_problem_dir(vault, problem)
        shutil.rmtree(pdir)
        result.deleted.append(pdir)
        if date_name not in result.dates:
            result.dates.append(date_name)

    for date_name in sorted(result.dates):
        result.daily_files[date_name] = update_daily(vault, date_name)

    index = vault / PROBLEMS_BY_ID_DIR / INDEX_FILENAME
    if index.is_file():  # 只在生成过索引时重建，不主动创建
        result.index = write_id_index(vault)
    return result
