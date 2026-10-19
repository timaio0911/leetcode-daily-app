"""F2：题目树/列表（方案 §4.2 problem_list.py）。"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QWidget,
)

from app.core.vault import DayEntry, ProblemEntry


class ProblemTree(QTreeWidget):
    """按日期分组的题目树；保存 ProblemEntry 到条目数据。支持多选（供批量删除）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(["题目 / 日期", "难度", "状态"])
        self.setColumnWidth(0, 320)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def populate(self, days: list[DayEntry]) -> None:
        self.clear()
        for day in days:
            day_item = QTreeWidgetItem([f"{day.date}  ({len(day.problems)} 题)", "", ""])
            self.addTopLevelItem(day_item)
            for p in day.problems:
                child = QTreeWidgetItem([f"{p.id.zfill(4)} {p.title}", p.difficulty, p.status])
                child.setData(0, 0x0100, p)  # Qt.UserRole
                day_item.addChild(child)
            day_item.setExpanded(True)

    def selected_problem(self) -> ProblemEntry | None:
        item = self.currentItem()
        if item is None:
            return None
        data = item.data(0, 0x0100)
        return data if isinstance(data, ProblemEntry) else None

    def selected_problems(self) -> list[ProblemEntry]:
        """所有选中条目对应的题目（多选）；选中日期节点则展开为其下全部题目。"""
        out: list[ProblemEntry] = []
        seen: set[str] = set()

        def add(p: ProblemEntry) -> None:
            key = str(p.dir)
            if key not in seen:
                seen.add(key)
                out.append(p)

        for item in self.selectedItems():
            data = item.data(0, 0x0100)
            if isinstance(data, ProblemEntry):
                add(data)
            else:  # 日期节点：取其子题目
                for i in range(item.childCount()):
                    child = item.child(i).data(0, 0x0100)
                    if isinstance(child, ProblemEntry):
                        add(child)
        return out


class FilterBar(QWidget):
    """按难度/标签/复盘状态筛选（方案 F2 + 阶段 4 错题本）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.difficulty = QComboBox()
        self.difficulty.addItem("全部难度", None)
        for d in ("简单", "中等", "困难"):
            self.difficulty.addItem(d, d)
        self.tag = QComboBox()
        self.tag.addItem("全部标签", None)
        self.tag.setMinimumWidth(120)
        self.review = QComboBox()
        self.review.addItem("全部", "all")
        self.review.addItem("错题本（需复盘）", "mistake")
        self.review.addItem("已复盘", "reviewed")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("筛选："))
        layout.addWidget(self.difficulty)
        layout.addWidget(self.tag)
        layout.addWidget(self.review)
        layout.addStretch(1)

    def set_tags(self, tags: list[str]) -> None:
        current = self.tag.currentData()
        self.tag.clear()
        self.tag.addItem("全部标签", None)
        for t in tags:
            self.tag.addItem(t, t)
        idx = self.tag.findData(current)
        self.tag.setCurrentIndex(idx if idx >= 0 else 0)

    def active(self) -> tuple[str | None, str | None, str]:
        return self.difficulty.currentData(), self.tag.currentData(), self.review.currentData()


def filter_days(days: list[DayEntry], difficulty: str | None, tag: str | None,
                review: str = "all") -> list[DayEntry]:
    """返回筛选后的副本（不改动原数据）。review: all/mistake/reviewed。"""
    from app.core.review import needs_review
    if difficulty is None and tag is None and review == "all":
        return days
    out: list[DayEntry] = []
    for day in days:
        kept = [
            p for p in day.problems
            if (difficulty is None or p.difficulty == difficulty)
            and (tag is None or tag in p.tags)
            and (review == "all"
                 or (review == "mistake" and needs_review(p))
                 or (review == "reviewed" and bool(p.reviewed)))
        ]
        if kept:
            out.append(DayEntry(date=day.date, problems=kept))
    return out


def collect_tags(days: list[DayEntry]) -> list[str]:
    seen: dict[str, None] = {}
    for day in days:
        for p in day.problems:
            for t in p.tags:
                seen.setdefault(t, None)
    return sorted(seen)
