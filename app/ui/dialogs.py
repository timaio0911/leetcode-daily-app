"""对话框：新建题目（F1）、设置（F7）、删除题目（新增）（方案 §4.2 dialogs.py）。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLineEdit,
    QMessageBox, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

from app.config import AppConfig, save_config
from app.core import leetcode
from app.core.vault import DayEntry, ProblemEntry


class NewProblemDialog(QDialog):
    """输入题目 URL/slug；可选直接填元数据（降级/跳过抓取）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新建题目")
        self.meta: leetcode.ProblemMeta | None = None

        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("https://leetcode.cn/problems/two-sum/ 或 two-sum")
        self.skip_fetch = QCheckBox("手动填写元数据（不抓取）")
        self.skip_fetch.toggled.connect(self._toggle_manual)
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("如 1（可留空）")
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("如 两数之和（手动模式必填）")
        self.difficulty_edit = QLineEdit()
        self.difficulty_edit.setPlaceholderText("简单 / 中等 / 困难（可留空）")
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("逗号分隔，如 数组,哈希表（可留空）")

        form = QFormLayout()
        form.addRow("题目 URL / slug：", self.query_edit)
        form.addRow("", self.skip_fetch)
        form.addRow("题号：", self.id_edit)
        form.addRow("标题：", self.title_edit)
        form.addRow("难度：", self.difficulty_edit)
        form.addRow("标签：", self.tags_edit)
        self._toggle_manual(False)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(QLabel("版权提示：只抓取元数据，不保存题面原文。"))
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _toggle_manual(self, on: bool) -> None:
        for w in (self.id_edit, self.title_edit, self.difficulty_edit, self.tags_edit):
            w.setEnabled(on)

    def _accept(self) -> None:
        query = self.query_edit.text().strip()
        slug = leetcode.extract_slug(query)
        if slug is None:
            QMessageBox.warning(self, "无法识别", f"无法识别题目：{query}\n请粘贴 leetcode.cn 题目 URL 或 slug。")
            return
        if self.skip_fetch.isChecked():
            title = self.title_edit.text().strip()
            if not title:
                QMessageBox.warning(self, "缺少标题", "手动模式需要填写题目标题。")
                return
            self.meta = leetcode.ProblemMeta(
                id=self.id_edit.text().strip() or "0",
                title=title,
                slug=slug,
                url=f"https://leetcode.cn/problems/{slug}/",
                difficulty=self.difficulty_edit.text().strip(),
                tags=[t.strip() for t in self.tags_edit.text().split(",") if t.strip()],
            )
        else:
            self.meta = leetcode.ProblemMeta(
                id=self.id_edit.text().strip() or "0",
                title=self.title_edit.text().strip() or slug,
                slug=slug,
                url=f"https://leetcode.cn/problems/{slug}/",
                difficulty=self.difficulty_edit.text().strip(),
                tags=[t.strip() for t in self.tags_edit.text().split(",") if t.strip()],
            )
            self.meta.pending_fetch = not self.skip_fetch.isChecked()  # 由调用方抓取覆盖
        self.accept()


class SettingsDialog(QDialog):
    """F7：仓库路径、IDEA/Obsidian 路径、git 远程、每日目标、抓取开关。"""

    def __init__(self, cfg: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.cfg = cfg

        self.vault_edit = QLineEdit(cfg.vault_path)
        self.idea_edit = QLineEdit(cfg.idea_path)
        self.obsidian_edit = QLineEdit(cfg.obsidian_path)
        self.remote_edit = QLineEdit(cfg.git_remote)
        self.goal_edit = QLineEdit(str(cfg.daily_goal))
        self.fetch_check = QCheckBox("新建题目时抓取力扣元数据")
        self.fetch_check.setChecked(cfg.fetch_enabled)

        form = QFormLayout()
        form.addRow("仓库（vault）路径：", self.vault_edit)
        form.addRow("IDEA 路径（idea64.exe）：", self.idea_edit)
        form.addRow("Obsidian 路径（可选）：", self.obsidian_edit)
        form.addRow("git 远程：", self.remote_edit)
        form.addRow("每日目标数：", self.goal_edit)
        form.addRow("", self.fetch_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    @staticmethod
    def _clean_path(text: str) -> str:
        """容忍复制粘贴带的引号/空白（如引号包裹的 exe 完整路径）。"""
        return text.strip().strip('"').strip("'").strip()

    def _save(self) -> None:
        vault = self._clean_path(self.vault_edit.text())
        if not vault or not (Path(vault) / "templates").is_dir():
            QMessageBox.warning(self, "路径无效", "仓库路径必须存在且包含 templates/ 目录。")
            return
        goal_text = self.goal_edit.text().strip()
        if not goal_text.isdigit() or int(goal_text) <= 0:
            QMessageBox.warning(self, "输入无效", "每日目标数必须是正整数。")
            return
        self.cfg.vault_path = vault
        self.cfg.idea_path = self._clean_path(self.idea_edit.text())
        self.cfg.obsidian_path = self._clean_path(self.obsidian_edit.text())
        self.cfg.git_remote = self.remote_edit.text().strip() or "origin"
        self.cfg.daily_goal = int(goal_text)
        self.cfg.fetch_enabled = self.fetch_check.isChecked()
        save_config(self.cfg)
        self.accept()


class DeleteProblemsDialog(QDialog):
    """删除题目：勾选要删除的历史记录（按日期分组的复选列表）。

    本对话框只负责「选择」，最终删除前的确认与执行由主窗口完成（`selected` 为勾选结果）。
    """

    def __init__(self, days: list[DayEntry], preselect: list[ProblemEntry] | None = None,
                 parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("删除题目")
        self.resize(560, 420)
        self.selected: list[ProblemEntry] = []
        self._syncing = False  # 级联勾选时屏蔽 itemChanged
        preselect_keys = {str(p.dir) for p in (preselect or [])}

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["题目（勾选要删除的记录）", "难度", "状态"])
        self.tree.setColumnWidth(0, 320)
        for day in days:
            day_item = QTreeWidgetItem([f"{day.date}  ({len(day.problems)} 题)", "", ""])
            day_item.setFlags(day_item.flags() | Qt.ItemIsUserCheckable)
            self.tree.addTopLevelItem(day_item)
            for p in day.problems:
                child = QTreeWidgetItem([f"{p.id.zfill(4)} {p.title}", p.difficulty, p.status])
                child.setData(0, 0x0100, p)  # Qt.UserRole
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Checked if str(p.dir) in preselect_keys else Qt.Unchecked)
                day_item.addChild(child)
            day_item.setExpanded(True)
            self._sync_day_state(day_item)
        self.tree.itemChanged.connect(self._on_item_changed)

        self.count_label = QLabel()
        select_all = QPushButton("全选")
        select_all.clicked.connect(lambda: self._set_all(True))
        select_none = QPushButton("全不选")
        select_none.clicked.connect(lambda: self._set_all(False))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("删除选中…")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        top = QHBoxLayout()
        top.addWidget(select_all)
        top.addWidget(select_none)
        top.addStretch(1)
        top.addWidget(self.count_label)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("选择要删除的题目记录（删除后可从 git 提交历史找回）："))
        layout.addLayout(top)
        layout.addWidget(self.tree, 1)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self._update_count()

    # ---------- 勾选状态 ----------

    def _set_all(self, checked: bool) -> None:
        self._syncing = True
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.tree.topLevelItemCount()):
            day_item = self.tree.topLevelItem(i)
            day_item.setCheckState(0, state)
            for j in range(day_item.childCount()):
                day_item.child(j).setCheckState(0, state)
        self._syncing = False
        self._update_count()

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._syncing or column != 0:
            return
        self._syncing = True
        if item.parent() is None:  # 日期节点：级联到子题目
            state = item.checkState(0)
            for j in range(item.childCount()):
                item.child(j).setCheckState(0, state)
        else:  # 题目节点：回推日期节点的三态
            self._sync_day_state(item.parent())
        self._syncing = False
        self._update_count()

    @staticmethod
    def _sync_day_state(day_item: QTreeWidgetItem) -> None:
        states = [day_item.child(j).checkState(0) for j in range(day_item.childCount())]
        if not states:
            day_item.setCheckState(0, Qt.Unchecked)
        elif all(s == Qt.Checked for s in states):
            day_item.setCheckState(0, Qt.Checked)
        elif all(s == Qt.Unchecked for s in states):
            day_item.setCheckState(0, Qt.Unchecked)
        else:
            day_item.setCheckState(0, Qt.PartiallyChecked)

    def _checked_problems(self) -> list[ProblemEntry]:
        out: list[ProblemEntry] = []
        for i in range(self.tree.topLevelItemCount()):
            day_item = self.tree.topLevelItem(i)
            for j in range(day_item.childCount()):
                child = day_item.child(j)
                if child.checkState(0) == Qt.Checked:
                    data = child.data(0, 0x0100)
                    if isinstance(data, ProblemEntry):
                        out.append(data)
        return out

    def _update_count(self) -> None:
        total = sum(self.tree.topLevelItem(i).childCount()
                    for i in range(self.tree.topLevelItemCount()))
        self.count_label.setText(f"已选 {len(self._checked_problems())} / {total} 题")

    # ---------- 确认 ----------

    def _accept(self) -> None:
        problems = self._checked_problems()
        if not problems:
            QMessageBox.information(self, "提示", "请先勾选要删除的题目。")
            return
        self.selected = problems
        self.accept()
