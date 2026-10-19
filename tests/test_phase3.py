"""阶段 3 验收自测：统计计算 + README 统计段落生成。

运行（workspace 根目录）：
    py tests/test_phase3.py
"""
from __future__ import annotations

import sys
import tempfile
from datetime import date as date_cls
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from app.core.stats import (  # noqa: E402
    MARKER_END, MARKER_START, compute_stats, render_stats_section, update_readme_stats,
)
from app.core.vault import DayEntry, ProblemEntry  # noqa: E402


def check(cond: bool, msg: str) -> None:
    print(("  ✅ " if cond else "  ❌ ") + msg)
    if not cond:
        raise SystemExit(f"验证失败：{msg}")


def _problem(pid: str, title: str, difficulty: str) -> ProblemEntry:
    return ProblemEntry(
        id=pid, slug=title, title=title, url="", difficulty=difficulty,
        tags=[], date="x", status="todo", time_spent="",
        dir=Path("."), readme=Path("README.md"), solution=None,
    )


def _day(date: str, n: int = 1, difficulty: str = "简单") -> DayEntry:
    return DayEntry(date=date, problems=[
        _problem(str(i + 1), f"题{i}", difficulty) for i in range(n)
    ])


def test_compute_stats() -> None:
    print("用例 1：统计计算")
    days = [
        _day("2026-06-01", 1),
        _day("2026-06-02", 2, "中等"),
        _day("2026-06-04", 1, "困难"),  # 断档 06-03
        _day("2026-06-05", 1),
    ]
    s = compute_stats(days, today=date_cls(2026, 6, 5))
    check(s.total == 5, "total=5")
    check(s.active_days == 4, "active_days=4")
    check(s.by_difficulty == {"简单": 2, "中等": 2, "困难": 1}, "难度分布正确")
    check(s.streak == 2, "连续打卡：06-04、06-05 → 2 天")
    check(s.best_streak == 2, "最长连续：06-01..02 或 06-04..05 → 2")
    check(s.today_count == 1, "今日 1 题")
    check(s.daily[0] == ("2026-06-01", 1) and s.daily[-1] == ("2026-06-05", 1), "daily 升序")

    # 今天没打卡时从昨天起算
    s2 = compute_stats(days, today=date_cls(2026, 6, 6))
    check(s2.streak == 2, "今天未打卡时 streak 从昨天起算")

    # 全部连续 → best_streak
    s3 = compute_stats([_day("2026-06-01"), _day("2026-06-02"), _day("2026-06-03")],
                       today=date_cls(2026, 6, 3))
    check(s3.streak == 3 and s3.best_streak == 3, "连续 3 天")

    # 每周聚合
    check(any(w.startswith("2026-W") for w, _ in s.weekly), "weekly 使用 ISO 周")
    check(sum(c for _, c in s.weekly) == s.total, "weekly 总和 = total")


def test_readme_section() -> None:
    print("用例 2：README 统计段落")
    days = [_day("2026-06-01", 2), _day("2026-06-02", 1, "困难")]
    s = compute_stats(days, today=date_cls(2026, 6, 2))
    section = render_stats_section(s, today=date_cls(2026, 6, 2))
    check(section.startswith(MARKER_START) and section.endswith(MARKER_END), "标记对包裹")
    check("累计 3 题" in section, "累计数正确")
    check("| 简单 | 2 |" in section and "| 困难 | 1 |" in section, "难度表格")

    vault = Path(tempfile.mkdtemp(prefix="lc-rm-"))
    readme = update_readme_stats(vault, s, today=date_cls(2026, 6, 2))
    text = readme.read_text(encoding="utf-8")
    check(MARKER_START in text and "累计 3 题" in text, "首次写入 README")

    # 重复更新幂等：不叠加段落
    s2 = compute_stats(days + [_day("2026-06-03", 1)], today=date_cls(2026, 6, 3))
    update_readme_stats(vault, s2, today=date_cls(2026, 6, 3))
    text = readme.read_text(encoding="utf-8")
    check(text.count(MARKER_START) == 1, "重复更新不叠加段落")
    check("累计 4 题" in text, "更新后数字刷新")
    check("## 学习记录" in text, "无标记时追加学习记录章节")


def main() -> None:
    test_compute_stats()
    test_readme_section()
    print("\n全部用例通过 ✅")


if __name__ == "__main__":
    main()
