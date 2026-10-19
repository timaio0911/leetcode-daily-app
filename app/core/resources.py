"""资源路径解析：兼容 PyInstaller 打包（sys._MEIPASS）与源码运行。

模板 `templates/` 需随包分发或内置；打包后从 sys._MEIPASS 读取，
源码运行时从 `app/../templates` 或 vault 的 templates/ 目录读取。
"""
from __future__ import annotations

import sys
from pathlib import Path


def bundle_dir() -> Path:
    """PyInstaller 的资源根目录，或源码运行时的 workspace 根目录。

    - PyInstaller 6.x onedir 模式：datas 落在 `sys._MEIPASS`（exe 同级 _internal/）；
    - PyInstaller 旧版 onedir / 单文件解包：`sys._MEIPASS` 同样有效；
    - 若 `_MEIPASS` 不存在（异常情形），回退到 exe 所在目录及其 `_internal/` 子目录。
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        exe_dir = Path(sys.executable).parent
        internal = exe_dir / "_internal"
        return internal if internal.is_dir() else exe_dir
    return Path(__file__).resolve().parent.parent.parent


def bundled_templates_dir() -> Path | None:
    """打包内置的 templates/ 目录（若存在）。"""
    candidate = bundle_dir() / "templates"
    return candidate if candidate.is_dir() else None


def resolve_template(vault: Path, name: str) -> Path:
    """定位模板文件：优先 vault/templates/，回退到打包内置目录。"""
    vault_tpl = Path(vault) / "templates" / name
    if vault_tpl.is_file():
        return vault_tpl
    bundled = bundled_templates_dir()
    if bundled is not None:
        bundled_tpl = bundled / name
        if bundled_tpl.is_file():
            return bundled_tpl
    raise FileNotFoundError(f"模板文件未找到：{name}（vault/templates 或打包内置目录）")
