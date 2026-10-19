"""一键启动 GUI 入口（打包为无控制台 exe，双击直接进主窗口）。

与 `py app gui` 等价，但去掉控制台窗口；异常写入同目录 crash.log 而非闪退。
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

# 自举包根路径（源码运行时）；打包后由 PyInstaller 处理
if not getattr(sys, "frozen", False):
    _PKG_ROOT = Path(__file__).resolve().parent
    if str(_PKG_ROOT) not in sys.path:
        sys.path.insert(0, str(_PKG_ROOT))


def _log_crash(exc: BaseException) -> None:
    """把崩溃写到 exe 同目录 crash.log，避免闪退无痕。"""
    try:
        base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
        log = base / "crash.log"
        log.write_text(
            "LeetCode 刷题管理 启动崩溃\n"
            "==========================\n"
            + traceback.format_exc()
            + f"\nPython: {sys.version}\nExecutable: {sys.executable}\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def main() -> int:
    try:
        from app.ui.main_window import run_gui
        return run_gui()
    except Exception as exc:  # noqa: BLE001 —— 任何启动失败都要留痕，不闪退
        _log_crash(exc)
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication(sys.argv)
            QMessageBox.critical(
                None,
                "启动失败",
                f"程序启动时出错：\n\n{exc}\n\n详细信息已写入 crash.log（程序同目录）。",
            )
        except Exception:  # noqa: BLE001 —— 连 Qt 都不可用就静默退出
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
