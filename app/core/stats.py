"""F3 统计计算（方案 §4.2 vault.py 的统计部分独立出来）。

frontmatter 即数据库：扫描 problems/ 下的 README.md 元数据，推导：
- 累计总数、每日/每周趋势、难度分布、连续打卡天数（streak）
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_cls, timedelta
from pathlib import Path

from app.core.vault import DayEntry


@dataclass
class Stats:
    total: int
    active_days: int
    by_difficulty: dict[str, int]
    by_status: dict[str, int]
    daily: list[tuple[str, int]]        # [(date, count)] 升序
    weekly: list[tuple[str, int]]       # [(ISO周, count)] 升序
    streak: int                         # 连续打卡天数（含今天或昨天起算）
    best_streak: int
    today_count: int


def _iso_week(date_str: str) -> str:
    d = date_cls.fromisoformat(date_str)
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def compute_stats(days: list[DayEntry], today: date_cls | None = None) -> Stats:
    today = today or date_cls.today()
    by_difficulty: dict[str, int] = {}
    by_status: dict[str, int] = {}
    daily_map: dict[str, int] = {}
    for day in days:
        daily_map[day.date] = len(day.problems)
        for p in day.problems:
            by_difficulty[p.difficulty or "未知"] = by_difficulty.get(p.difficulty or "未知", 0) + 1
            by_status[p.status or "todo"] = by_status.get(p.status or "todo", 0) + 1

    daily = sorted(daily_map.items())
    weekly_map: dict[str, int] = {}
    for d, count in daily:
        weekly_map[_iso_week(d)] = weekly_map.get(_iso_week(d), 0) + count

    # 连续打卡：从今天（或昨天，今天还没打卡）往前数连续有记录的天数
    streak = 0
    cursor = today
    if cursor.isoformat() not in daily_map:
        cursor -= timedelta(days=1)
    while cursor.isoformat() in daily_map:
        streak += 1
        cursor -= timedelta(days=1)

    best = current = 0
    for i, (d, _) in enumerate(daily):
        if i > 0:
            prev = date_cls.fromisoformat(daily[i - 1][0])
            gap = (date_cls.fromisoformat(d) - prev).days
            current = current + 1 if gap == 1 else 1
        else:
            current = 1
        best = max(best, current)

    return Stats(
        total=sum(daily_map.values()),
        active_days=len(daily_map),
        by_difficulty=by_difficulty,
        by_status=by_status,
        daily=daily,
        weekly=sorted(weekly_map.items()),
        streak=streak,
        best_streak=best,
        today_count=daily_map.get(today.isoformat(), 0),
    )


# ---------- README 统计段落（方案 §5 阶段 3：仓库 README 自动生成） ----------

MARKER_START = "<!-- LEETCODE-STATS:START -->"
MARKER_END = "<!-- LEETCODE-STATS:END -->"


def _bar(value: int, scale: int, width: int = 12) -> str:
    n = round(width * value / scale) if scale else 0
    return "█" * n


def render_stats_section(stats: Stats, today: date_cls | None = None) -> str:
    """生成 README 里的统计段落（纯文本表格 + 文本柱状图，GitHub 渲染友好）。"""
    today = today or date_cls.today()
    lines = [
        MARKER_START,
        f"> 最后更新：{today.isoformat()} · 由刷题管理软件自动生成",
        "",
        f"**累计 {stats.total} 题** · 活跃 {stats.active_days} 天 · "
        f"连续打卡 {stats.streak} 天（最长 {stats.best_streak} 天）",
        "",
        "### 难度分布",
        "",
        "| 难度 | 题数 | |",
        "|---|---|---|",
    ]
    scale = max(stats.by_difficulty.values(), default=0)
    for label in ("简单", "中等", "困难", "未知"):
        if label in stats.by_difficulty:
            v = stats.by_difficulty[label]
            lines.append(f"| {label} | {v} | {_bar(v, scale)} |")
    lines += [
        "",
        "### 最近每日刷题",
        "",
        "| 日期 | 题数 | |",
        "|---|---|---|",
    ]
    scale = max((c for _, c in stats.daily), default=0)
    for d, c in stats.daily[-10:]:
        lines.append(f"| {d} | {c} | {_bar(c, scale)} |")
    lines += [
        "",
        "### 每周趋势",
        "",
        "| 周 | 题数 | |",
        "|---|---|---|",
    ]
    scale = max((c for _, c in stats.weekly), default=0)
    for w, c in stats.weekly[-8:]:
        lines.append(f"| {w} | {c} | {_bar(c, scale)} |")
    lines.append(MARKER_END)
    return "\n".join(lines)


def update_readme_stats(vault: Path, stats: Stats, today: date_cls | None = None) -> Path:
    """把统计段落写入仓库 README.md（用标记对包裹，可重复更新）。"""
    readme = Path(vault) / "README.md"
    section = render_stats_section(stats, today)
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
    else:
        text = "# LeetCode Daily\n"
    if MARKER_START in text and MARKER_END in text:
        head = text.split(MARKER_START)[0]
        tail = text.split(MARKER_END)[1]
        text = head + section + tail
    else:
        text = text.rstrip("\n") + "\n\n## 学习记录\n\n" + section + "\n"
    readme.write_text(text, encoding="utf-8")
    return readme
