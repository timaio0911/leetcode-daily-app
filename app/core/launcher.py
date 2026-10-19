"""F4：一键跳转 IDEA / Obsidian（方案 §4.2 launcher.py）。

- IDEA：`<idea_path> <file>` 直接打开文件（路径在设置中配置）
- Obsidian：优先 `obsidian://open?vault=<vault名>&file=<相对路径>` URI（无需配置 exe），
  配置了 obsidian_path 时也可直接调 exe
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from urllib.parse import quote


class LaunchError(RuntimeError):
    pass


def _open_uri(uri: str) -> None:
    """用系统默认程序打开 URI（Windows: os.startfile 走 ShellExecute）。"""
    try:
        os.startfile(uri)  # noqa: S606 —— 打开受控 URI
    except OSError as exc:  # 无关联程序 / 系统拒绝
        raise LaunchError(f"无法打开 URI {uri}：{exc}") from exc


def _clean_path(raw: str) -> str:
    """容忍用户复制粘贴时带的引号/空白（如引号包裹的 exe 完整路径）。"""
    return (raw or "").strip().strip('"').strip("'").strip()


def open_idea(idea_path: str, file: Path) -> str:
    cleaned = _clean_path(idea_path)
    if not cleaned:
        raise LaunchError(
            "未配置 IDEA/PyCharm 路径，请在「设置」中填写 pycharm64.exe 或 idea64.exe 完整路径。"
        )
    exe = Path(cleaned)
    if exe.is_dir():
        # 容错：填了 bin/ 目录就自动找 IDE 可执行文件
        for name in ("pycharm64.exe", "idea64.exe", "pycharm.exe", "idea.exe"):
            cand = exe / name
            if cand.is_file():
                exe = cand
                break
    if not exe.is_file():
        raise LaunchError(
            f"IDEA/PyCharm 路径不存在：{cleaned}（应指向 pycharm64.exe / idea64.exe 的完整路径）"
        )
    if not file.is_file():
        raise LaunchError(f"文件不存在：{file}")
    subprocess.Popen([str(exe), str(file)])
    return f"已用 IDE 打开 {file.name}"


def _obsidian_exe_from_registry() -> str:
    """从注册表 obsidian:// 处理器解析 Obsidian.exe 路径；找不到返回空串。"""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"obsidian\shell\open\command") as key:
            cmd, _ = winreg.QueryValueEx(key, "")
    except OSError:
        return ""
    cmd = (cmd or "").strip()
    if cmd.startswith('"'):
        end = cmd.find('"', 1)
        return cmd[1:end] if end > 1 else ""
    return cmd.split("%1")[0].strip().split(" ")[0]


def open_obsidian(vault: Path, file: Path, obsidian_path: str = "") -> str:
    if not file.is_file():
        raise LaunchError(f"文件不存在：{file}")
    # vault 名 = 目录名（Obsidian URI 按 vault 名定位）
    vault_name = vault.name
    rel = file.relative_to(vault).as_posix()
    # Obsidian URI：带 .md 后缀的 file 参数兼容性最好
    uri = f"obsidian://open?vault={quote(vault_name)}&file={quote(rel)}"
    # 直启 Obsidian.exe + URI（与系统 URI 处理器的命令行一致），绕开
    # ShellExecute 在打包 exe 里可能被系统静默拦截的问题；失败再回退系统 URI
    exe = _clean_path(obsidian_path) or _obsidian_exe_from_registry()
    if exe and Path(exe).is_file():
        try:
            subprocess.Popen([exe, uri])
            return f"已用 Obsidian 打开 {rel}"
        except OSError:
            pass
    _open_uri(uri)
    return f"已用 Obsidian 打开 {rel}"


def open_folder(folder: Path) -> str:
    if not folder.is_dir():
        raise LaunchError(f"目录不存在：{folder}")
    try:
        os.startfile(str(folder))  # noqa: S606
    except OSError:
        # 打包 exe 里 ShellExecute 打开目录可能被系统拒绝（WinError 5），
        # 回退直接启动 explorer.exe（CreateProcess，实测不受影响）
        try:
            subprocess.Popen(["explorer.exe", str(folder)])
        except OSError as exc:
            raise LaunchError(
                f"无法打开文件夹 {folder}：{exc}"
                "\n（若杀毒软件/SmartScreen 拦截了本软件，请将其加入白名单后重试）"
            ) from exc
    return f"已打开文件夹 {folder}"
