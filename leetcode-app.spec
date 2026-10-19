# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec：打包 LeetCode 刷题管理软件。
#
# 产物：
#   dist/leetcode-app/leetcode-app.exe     —— 控制台版（保留 CLI，调试/命令行用）
#   dist/LeetCode刷题管理.exe             —— 一键启动 GUI 版（无控制台窗口，双击即用）
#
# 用法：py -m PyInstaller --noconfirm leetcode-app.spec

import sys
from pathlib import Path

block_cipher = None
workspace = Path(SPECPATH)
templates_dir = workspace / "leetcode-daily" / "templates"
datas = [(str(templates_dir), "templates")] if templates_dir.is_dir() else []

# Conda 环境的运行时 DLL 存在 Library\bin，PyInstaller 解析不到（构建日志
# "Library not found" 警告）。缺 _ssl 的运行时库会让打包后 HTTPS 抓元数据
# 静默失败（GUI 报「抓取失败」，2026-10-15 实测），故显式打入。
_conda_bin = Path(sys.base_prefix) / "Library" / "bin"
_conda_dlls = [
    "libssl-3-x64.dll",     # _ssl.pyd / cryptography 依赖（HTTPS 必需）
    "libcrypto-3-x64.dll",  # libssl 的依赖
    "libmpdec-4.dll",       # _decimal.pyd 依赖
    "libbz2.dll",           # _bz2.pyd 依赖
    "ffi.dll",              # _ctypes.pyd 依赖
]
conda_binaries = [
    (str(_conda_bin / dll), ".")
    for dll in _conda_dlls
    if (_conda_bin / dll).is_file()
]


def make_analysis(entry: str) -> Analysis:
    return Analysis(
        [str(workspace / entry)],
        pathex=[str(workspace)],
        binaries=conda_binaries,
        datas=datas,
        hiddenimports=[],
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
        cipher=block_cipher,
        noarchive=False,
    )


# ---------- 1) 控制台版（CLI + gui 子命令） ----------
a_cli = make_analysis("app/__main__.py")
pyz_cli = PYZ(a_cli.pure, a_cli.zipped_data, cipher=block_cipher)
exe_cli = EXE(
    pyz_cli,
    a_cli.scripts,
    [],
    exclude_binaries=True,
    name="leetcode-app",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll_cli = COLLECT(
    exe_cli,
    a_cli.binaries,
    a_cli.zipfiles,
    a_cli.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="leetcode-app",
)

# ---------- 2) GUI 一键启动版（无控制台，双击直接进主窗口） ----------
a_gui = make_analysis("launcher_gui.py")
pyz_gui = PYZ(a_gui.pure, a_gui.zipped_data, cipher=block_cipher)
exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    [],
    exclude_binaries=True,
    name="LeetCode刷题管理",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll_gui = COLLECT(
    exe_gui,
    a_gui.binaries,
    a_gui.zipfiles,
    a_gui.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="LeetCode刷题管理",
)
