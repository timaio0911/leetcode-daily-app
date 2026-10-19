"""主窗口与标签页（方案 §4.2 main_window.py）—— 阶段 2 完整 GUI。

界面（方案 §3.1）：[今日] [题目列表] [统计] + 设置按钮；
题目树 | 选中题目详情（元数据 + 笔记预览 + 跳转按钮）；底部工具条（新建题目 / 提交 GitHub / 状态）。
"""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTabWidget, QTextBrowser,
    QVBoxLayout, QWidget,
)

from app.config import AppConfig, load_config, resolve_vault
from app.core import delete, gitops, scaffold
from app.core.launcher import LaunchError, open_folder, open_idea, open_obsidian
from app.core.vault import DayEntry, ProblemEntry, scan_vault
from app.ui.dashboard import DashboardWidget
from app.ui.dialogs import DeleteProblemsDialog, NewProblemDialog, SettingsDialog
from app.ui.problem_list import FilterBar, ProblemTree, collect_tags, filter_days


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LeetCode 刷题管理")
        self.resize(960, 640)
        self.cfg: AppConfig = load_config()
        self.days: list[DayEntry] = []

        self.tree = ProblemTree()
        self.tree.currentItemChanged.connect(lambda *_: self.show_detail())
        del_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self.tree)
        del_shortcut.setContext(Qt.WidgetWithChildrenShortcut)  # 仅题目树聚焦时生效
        del_shortcut.activated.connect(self.on_delete_selected)
        self.filter_bar = FilterBar()
        self.filter_bar.difficulty.currentIndexChanged.connect(self.apply_filter)
        self.filter_bar.tag.currentIndexChanged.connect(self.apply_filter)
        self.filter_bar.review.currentIndexChanged.connect(self.apply_filter)

        self.detail_title = QLabel("选择左侧题目查看详情")
        self.detail_title.setWordWrap(True)
        self.detail_meta = QLabel("")
        self.detail_meta.setWordWrap(True)
        self.note_preview = QTextBrowser()
        self.btn_idea = QPushButton("用 IDEA 打开代码")
        self.btn_idea.clicked.connect(self.on_open_idea)
        self.btn_obsidian = QPushButton("用 Obsidian 打开笔记")
        self.btn_obsidian.clicked.connect(self.on_open_obsidian)
        self.btn_folder = QPushButton("打开文件夹")
        self.btn_folder.clicked.connect(self.on_open_folder)
        self.btn_review = QPushButton("标记复盘 ✓")
        self.btn_review.clicked.connect(self.on_mark_review)
        self.btn_solution2 = QPushButton("新建二刷代码")
        self.btn_solution2.clicked.connect(self.on_new_solution2)
        self.btn_delete_one = QPushButton("🗑 删除此题")
        self.btn_delete_one.clicked.connect(self.on_delete_selected)

        detail_box = QGroupBox("题目详情")
        detail_layout = QVBoxLayout(detail_box)
        detail_layout.addWidget(self.detail_title)
        detail_layout.addWidget(self.detail_meta)
        detail_layout.addWidget(QLabel("笔记预览（README.md）："))
        detail_layout.addWidget(self.note_preview, 1)
        btn_row = QHBoxLayout()
        for b in (self.btn_idea, self.btn_obsidian, self.btn_folder,
                  self.btn_review, self.btn_solution2, self.btn_delete_one):
            btn_row.addWidget(b)
        btn_row.addStretch(1)
        detail_layout.addLayout(btn_row)

        splitter = QSplitter()
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.filter_bar)
        left_layout.addWidget(self.tree, 1)
        splitter.addWidget(left)
        splitter.addWidget(detail_box)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        self.dashboard = DashboardWidget()
        self.dashboard.on_readme_updated = self.refresh
        self.tab = QTabWidget()
        self.tab.addTab(self._build_today_tab(), "今日")
        self.tab.addTab(splitter, "题目列表")
        self.tab.addTab(self.dashboard, "统计")

        # 底部工具条（方案 §3.1）
        self.new_btn = QPushButton("+ 新建题目")
        self.new_btn.clicked.connect(self.on_new)
        self.delete_btn = QPushButton("🗑 删除题目…")
        self.delete_btn.clicked.connect(self.on_delete)
        self.commit_btn = QPushButton("提交 GitHub ↑")
        self.commit_btn.clicked.connect(self.on_commit)
        self.status_label = QLabel()

        bottom = QHBoxLayout()
        bottom.addWidget(self.new_btn)
        bottom.addWidget(self.delete_btn)
        bottom.addWidget(self.commit_btn)
        bottom.addWidget(self.status_label, 1)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.addWidget(self.tab, 1)
        central_layout.addLayout(bottom)
        self.setCentralWidget(central)

        settings_action = self.menuBar().addMenu("设置")
        settings_action.addAction("设置…", self.on_settings)

        self.refresh()

    # ---------- 数据 ----------

    def refresh(self) -> None:
        self.cfg = load_config()
        try:
            vault = resolve_vault(self.cfg)
        except FileNotFoundError as exc:
            self.status_label.setText(str(exc))
            return
        self.days = scan_vault(vault)
        self.filter_bar.set_tags(collect_tags(self.days))
        self.apply_filter()
        total = sum(len(d.problems) for d in self.days)
        self.status_label.setText(f"共 {total} 题 · 数据目录：{vault}")
        self._refresh_today()
        self.dashboard.refresh(self.days)

    def apply_filter(self) -> None:
        difficulty, tag, review = self.filter_bar.active()
        self.tree.populate(filter_days(self.days, difficulty, tag, review))

    def _build_today_tab(self) -> QWidget:
        self.today_label = QLabel()
        self.today_label.setWordWrap(True)
        self.today_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.today_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self.today_label)
        return widget

    def _refresh_today(self) -> None:
        from datetime import date as date_cls
        from app.core.stats import compute_stats
        today = date_cls.today().isoformat()
        day = next((d for d in self.days if d.date == today), None)
        s = compute_stats(self.days)
        if day is None:
            self.today_label.setText(
                f"{today}\n\n今天还没有刷题记录，点下方「+ 新建题目」开始。\n\n"
                f"连续打卡：{s.streak} 天（最长 {s.best_streak} 天）"
            )
            return
        lines = [f"{today} · 今日 {len(day.problems)} 题", ""]
        for p in day.problems:
            lines.append(f"  {p.id.zfill(4)} {p.title}  [{p.difficulty}]  {p.status}")
        goal = self.cfg.daily_goal
        done = "✅ 已达每日目标" if len(day.problems) >= goal else f"（每日目标 {goal} 题）"
        lines += [
            "",
            f"难度分布：{s.by_difficulty}  {done}",
            f"累计 {s.total} 题 · 连续打卡 {s.streak} 天（最长 {s.best_streak} 天）",
        ]
        self.today_label.setText("\n".join(lines))

    # ---------- 详情 ----------

    def show_detail(self) -> None:
        p = self.tree.selected_problem()
        if p is None:
            self.detail_title.setText("选择左侧题目查看详情")
            self.detail_meta.setText("")
            self.note_preview.clear()
            return
        self.detail_title.setText(p.id_title)
        self.detail_meta.setText(
            f"难度：{p.difficulty or '—'}    标签：{', '.join(p.tags) or '—'}    "
            f"状态：{p.status}    用时：{p.time_spent or '—'}    "
            f"复盘：{', '.join(p.reviewed) or '—'}\n"
            f"链接：{p.url}"
        )
        text = ""
        if p.readme.is_file():
            text = p.readme.read_text(encoding="utf-8", errors="replace")
        self.note_preview.setPlainText(text)

    # ---------- 动作 ----------

    def on_new(self) -> None:
        dialog = NewProblemDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted or dialog.meta is None:
            return
        meta = dialog.meta
        try:
            vault = resolve_vault(self.cfg)
        except FileNotFoundError as exc:
            QMessageBox.critical(self, "数据目录不可用", str(exc))
            return
        if getattr(meta, "pending_fetch", False) and self.cfg.fetch_enabled:
            fetched = self._fetch_with_wait(meta.slug, vault)
            if fetched is not None:
                meta = fetched
        result = scaffold.scaffold_problem(vault, meta)
        self.refresh()
        QMessageBox.information(
            self, "新建完成",
            f"{meta.id_title}\n目录：{result.problem_dir}"
            + ("\n（目录已存在，跳过重复创建）" if result.reused else ""),
        )

    def _fetch_with_wait(self, slug: str, vault):
        """抓取元数据；带等待提示，失败返回 None（上层降级）。"""
        from app.core import leetcode
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.status_label.setText(f"正在抓取 {slug} 的元数据…")
        QApplication.processEvents()
        try:
            meta = leetcode.fetch_meta(slug, vault)
        finally:
            QApplication.restoreOverrideCursor()
            self.status_label.setText("")
        if meta is None:
            QMessageBox.warning(
                self, "抓取失败",
                "元数据抓取失败（限流/离线），已降级为手动填写。\n"
                "请在对话框中勾选「手动填写元数据」重试。",
            )
        return meta

    def on_open_idea(self) -> None:
        p = self.tree.selected_problem()
        if p is None:
            QMessageBox.information(self, "提示", "请先在左侧选择一道题目。")
            return
        solution = p.solution
        if solution is None or not solution.is_file():
            # solution.py 被删除/丢失：按 README 元数据自动重建（scaffold 幂等，不动其余文件）
            solution = self._rebuild_solution(p)
            if solution is None:
                return
        self._launch(lambda: open_idea(self.cfg.idea_path, solution))

    def _rebuild_solution(self, p: ProblemEntry):
        """重建缺失的 solution.py；失败返回 None（已提示用户）。"""
        from app.core.leetcode import ProblemMeta
        try:
            vault = resolve_vault(self.cfg)
            result = scaffold.scaffold_problem(
                vault,
                ProblemMeta(
                    id=p.id, title=p.title, slug=p.slug, url=p.url,
                    difficulty=p.difficulty, tags=list(p.tags),
                ),
                day=p.dir.parent.name,  # 用归档日期保证落回原目录
            )
        except Exception as exc:  # noqa: BLE001 —— 重建失败不崩溃，提示即可
            QMessageBox.warning(self, "重建失败", f"solution.py 缺失，自动重建失败：{exc}")
            return None
        self.refresh()
        return result.solution

    def on_open_obsidian(self) -> None:
        p = self.tree.selected_problem()
        if p is None:
            QMessageBox.information(self, "提示", "请先在左侧选择一道题目。")
            return
        self._launch(lambda: open_obsidian(self.cfg.vault, p.readme, self.cfg.obsidian_path))

    def on_open_folder(self) -> None:
        p = self.tree.selected_problem()
        if p is None:
            QMessageBox.information(self, "提示", "请先在左侧选择一道题目。")
            return
        self._launch(lambda: open_folder(p.dir))

    def on_mark_review(self) -> None:
        """阶段 4：标记复盘（写入 reviewed frontmatter + 生成 review-<date>.md）。"""
        from datetime import date as date_cls
        from app.core.review import mark_reviewed
        p = self.tree.selected_problem()
        if p is None:
            QMessageBox.information(self, "提示", "请先在左侧选择一道题目。")
            return
        today = date_cls.today().isoformat()
        review_file = mark_reviewed(p.dir, today)
        self.refresh()
        QMessageBox.information(
            self, "已标记复盘",
            f"{p.id_title}\n复盘日期：{today}\n复盘笔记：{review_file.name}",
        )

    def on_new_solution2(self) -> None:
        """阶段 4：新建二刷代码 solution-2.py。"""
        from app.core.review import add_solution2
        p = self.tree.selected_problem()
        if p is None:
            QMessageBox.information(self, "提示", "请先在左侧选择一道题目。")
            return
        path = add_solution2(p.dir)
        self.refresh()
        QMessageBox.information(self, "二刷代码", f"已创建：{path.name}")

    # ---------- 删除（新增功能） ----------

    def on_delete(self) -> None:
        """打开删除对话框，勾选要删除的历史题目记录。"""
        if not self.days:
            QMessageBox.information(self, "提示", "还没有可删除的题目记录。")
            return
        dialog = DeleteProblemsDialog(self.days, self.tree.selected_problems(), self)
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.selected:
            return
        self._do_delete(dialog.selected)

    def on_delete_selected(self) -> None:
        """删除题目树当前选中的题目（Delete 键 / 详情区「删除此题」）。"""
        self._do_delete(self.tree.selected_problems())

    def _confirm_delete(self, problems: list[ProblemEntry]) -> bool:
        if not problems:
            QMessageBox.information(self, "提示", "请先在左侧选择要删除的题目。")
            return False
        lines = "\n".join(delete.describe(p) for p in problems[:15])
        if len(problems) > 15:
            lines += f"\n…（共 {len(problems)} 题）"
        answer = QMessageBox.question(
            self, "确认删除",
            f"将永久删除以下 {len(problems)} 题的目录（含代码、笔记、复盘文件）：\n\n{lines}\n\n"
            "删除后 daily.md / 题号索引会自动重建；误删可从 git 提交历史找回。\n\n继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _do_delete(self, problems: list[ProblemEntry]) -> None:
        if not self._confirm_delete(problems):
            return
        try:
            vault = resolve_vault(self.cfg)
        except FileNotFoundError as exc:
            QMessageBox.critical(self, "数据目录不可用", str(exc))
            return
        try:
            result = delete.delete_problems(vault, problems)
        except delete.DeleteError as exc:
            QMessageBox.critical(self, "删除失败", str(exc))
            return
        self.refresh()
        self.status_label.setText(f"已删除 {len(result.deleted)} 题")
        QMessageBox.information(
            self, "删除完成",
            f"已删除 {len(result.deleted)} 题：\n\n"
            + "\n".join(d.name for d in result.deleted)
            + "\n\n已重建 daily.md" + ("、题号索引" if result.index else "")
            + "\n（如需同步 GitHub，点「提交 GitHub」）",
        )

    def _launch(self, action) -> None:
        try:
            self.status_label.setText(action())
        except LaunchError as exc:
            QMessageBox.warning(self, "无法打开", str(exc))

    def on_commit(self) -> None:
        """F5：扫描改动 → commit（约定式信息）→ push。"""
        try:
            vault = resolve_vault(self.cfg)
        except FileNotFoundError as exc:
            QMessageBox.critical(self, "数据目录不可用", str(exc))
            return
        try:
            status = gitops.git_status(vault)
        except gitops.GitError as exc:
            QMessageBox.critical(self, "git 错误", str(exc))
            return
        if status.clean:
            QMessageBox.information(self, "提交 GitHub", "没有改动，无需提交。")
            return

        changed = "\n".join(status.changed[:15])
        if len(status.changed) > 15:
            changed += f"\n…（共 {len(status.changed)} 项）"
        msg = self._commit_message(status)
        answer = QMessageBox.question(
            self, "提交 GitHub",
            f"将提交以下改动：\n\n{changed}\n\n提交信息：{msg}\n\n继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.status_label.setText("git add + commit…")
            QApplication.processEvents()
            result = gitops.commit_all(vault, msg)
            if gitops.has_remote(vault, self.cfg.git_remote):
                self.status_label.setText("git push…")
                QApplication.processEvents()
                result += "\n" + gitops.push(vault, self.cfg.git_remote)
            else:
                result += f"\n（未配置远程 {self.cfg.git_remote}，跳过 push）"
        except gitops.GitError as exc:
            self.status_label.setText("提交失败")
            QMessageBox.critical(
                self, "提交失败",
                f"{exc}\n\n本地 commit 可能已成功，可修复问题后重试 push。",
            )
            return
        self.status_label.setText("已同步")
        QMessageBox.information(self, "提交 GitHub", result)

    def _commit_message(self, status: gitops.GitStatus) -> str:
        """约定式信息：`<归档date>: add <id> <slug>`；多项/非建题改动用汇总式。"""
        from datetime import date as date_cls
        new_dirs = {
            "/".join(p.split("/")[:3])
            for p in status.changed
            if p.startswith("problems/") and len(p.split("/")) == 4  # problems/<date>/<dir>/<file>
        }
        if len(new_dirs) == 1:
            _, archive_date, dirname = next(iter(new_dirs)).split("/")
            parts = dirname.split("-", 1)
            if len(parts) == 2 and parts[0].isdigit():
                return gitops.commit_message_for(archive_date, parts[0], parts[1])
        return f"{date_cls.today().isoformat()}: update vault ({len(status.changed)} files)"

    def on_settings(self) -> None:
        dialog = SettingsDialog(self.cfg, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.refresh()


def run_gui() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()
