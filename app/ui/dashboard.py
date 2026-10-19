"""F3：统计看板（方案 §4.2 dashboard.py）。

上：数字卡片（总数/活跃天数/连续打卡/今日）；下：每日趋势折线 + 难度分布柱状图 + 每周趋势。
图表用 QtCharts（PySide6-Addons 自带），不可用时降级为文本。
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from app.core.stats import compute_stats, update_readme_stats
from app.core.vault import DayEntry
from app.ui.charts import BarChartView, LineChartView


class DashboardWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._days: list[DayEntry] = []

        self.cards = QLabel()
        self.cards.setWordWrap(True)

        self.daily_chart = LineChartView("每日刷题趋势")
        self.weekly_chart = LineChartView("每周刷题趋势")
        self.difficulty_chart = BarChartView("难度分布")

        grid = QGridLayout()
        grid.addWidget(self._wrap("每日趋势", self.daily_chart), 0, 0)
        grid.addWidget(self._wrap("难度分布", self.difficulty_chart), 0, 1)
        grid.addWidget(self._wrap("每周趋势", self.weekly_chart), 1, 0, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)

        self.readme_btn = QPushButton("更新 README 统计段落")
        self.readme_btn.clicked.connect(self.on_update_readme)

        layout = QVBoxLayout(self)
        layout.addWidget(self.cards)
        layout.addLayout(grid, 1)
        row = QHBoxLayout()
        row.addWidget(self.readme_btn)
        row.addStretch(1)
        layout.addLayout(row)

        self.on_readme_updated = None  # 主窗口可挂回调

    @staticmethod
    def _wrap(title: str, widget: QWidget) -> QGroupBox:
        box = QGroupBox(title)
        box_layout = QVBoxLayout(box)
        box_layout.addWidget(widget)
        return box

    def refresh(self, days: list[DayEntry]) -> None:
        self._days = days
        s = compute_stats(days)
        self.cards.setText(
            f"累计 {s.total} 题    活跃 {s.active_days} 天    "
            f"连续打卡 {s.streak} 天（最长 {s.best_streak} 天）    今日 {s.today_count} 题"
        )
        daily_labels = [d for d, _ in s.daily][-14:]
        daily_values = [c for _, c in s.daily][-14:]
        self.daily_chart.set_data(daily_labels, daily_values)

        weekly_labels = [w for w, _ in s.weekly][-8:]
        weekly_values = [c for _, c in s.weekly][-8:]
        self.weekly_chart.set_data(weekly_labels, weekly_values)

        diff_labels = [k for k in ("简单", "中等", "困难", "未知") if k in s.by_difficulty]
        self.difficulty_chart.set_data(diff_labels, [s.by_difficulty[k] for k in diff_labels])

    def on_update_readme(self) -> None:
        from PySide6.QtWidgets import QApplication, QMessageBox
        from app.config import load_config, resolve_vault
        try:
            vault = resolve_vault(load_config())
        except FileNotFoundError as exc:
            QMessageBox.critical(self, "数据目录不可用", str(exc))
            return
        s = compute_stats(self._days)
        readme = update_readme_stats(vault, s)
        QMessageBox.information(self, "README 已更新", f"统计段落已写入：\n{readme}")
        if callable(self.on_readme_updated):
            self.on_readme_updated()
