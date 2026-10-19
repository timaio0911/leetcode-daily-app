"""图表控件：QtCharts 优先，matplotlib 降级，两者都不可用时退化为文本（方案 §4.2 dashboard.py）。"""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    from PySide6.QtCharts import (
        QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView,
        QLineSeries, QValueAxis,
    )
    from PySide6.QtGui import QPainter
    from PySide6.QtCore import QPointF, Qt

    HAS_QTCHARTS = True
except ImportError:  # pragma: no cover
    HAS_QTCHARTS = False


class LineChartView(QWidget):
    """折线图（每日/每周趋势）。无 QtCharts 时降级为文本。"""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.title = title
        self._fallback = QLabel()
        self._fallback.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if HAS_QTCHARTS:
            self._chart = QChart()
            self._chart.setTitle(title)
            self._chart.legend().hide()
            self._view = QChartView(self._chart)
            self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
            layout.addWidget(self._view)
            self._fallback.hide()
        else:
            layout.addWidget(self._fallback)

    def set_data(self, labels: list[str], values: list[int]) -> None:
        if not HAS_QTCHARTS:
            scale = max(values, default=0)
            rows = [f"{l}: {v} {'█' * round(10 * v / scale) if scale else ''}" for l, v in zip(labels, values)]
            self._fallback.setText(self.title + "\n" + ("\n".join(rows) or "（暂无数据）"))
            return
        self._chart.removeAllSeries()
        for axis in self._chart.axes():
            self._chart.removeAxis(axis)
        series = QLineSeries()
        series.setPointsVisible(True)  # 单点/少点时折线不可见，必须显示数据点
        for i, v in enumerate(values):
            series.append(QPointF(i, v))
        self._chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(labels)
        axis_y = QValueAxis()
        axis_y.setLabelFormat("%d")
        top = max(values, default=1)
        axis_y.setRange(0, max(top + 1, 2))
        self._chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self._chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)


class BarChartView(QWidget):
    """柱状图（难度分布）。无 QtCharts 时降级为文本。"""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.title = title
        self._fallback = QLabel()
        self._fallback.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if HAS_QTCHARTS:
            self._chart = QChart()
            self._chart.setTitle(title)
            self._view = QChartView(self._chart)
            self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
            layout.addWidget(self._view)
            self._fallback.hide()
        else:
            layout.addWidget(self._fallback)

    def set_data(self, labels: list[str], values: list[int]) -> None:
        if not HAS_QTCHARTS:
            scale = max(values, default=0)
            rows = [f"{l}: {v} {'█' * round(10 * v / scale) if scale else ''}" for l, v in zip(labels, values)]
            self._fallback.setText(self.title + "\n" + ("\n".join(rows) or "（暂无数据）"))
            return
        self._chart.removeAllSeries()
        for axis in self._chart.axes():
            self._chart.removeAxis(axis)
        bar_set = QBarSet("题数")
        for v in values:
            bar_set.append(v)
        series = QBarSeries()
        series.append(bar_set)
        self._chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(labels)
        axis_y = QValueAxis()
        axis_y.setLabelFormat("%d")
        axis_y.setRange(0, max(max(values, default=0) + 1, 2))
        self._chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self._chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
