"""打包脚本（统一入口）：py package.py [--skip-tests]

打包策略（用户约定）：
- dist/ 只保留本次打包的新版本：打包前清空 dist/（旧版本不留档）。
- build/ 为 PyInstaller 中间产物，每次打包前清空（不留旧打包文件）。
- 打包前先跑全套测试（--skip-tests 可跳过），测试不过不打包。
- 打包前检查 exe 是否正在运行（运行中会锁文件导致 PyInstaller 删除旧目录失败）。

产物（见 leetcode-app.spec）：
- dist/LeetCode刷题管理/LeetCode刷题管理.exe  —— 一键启动 GUI（无控制台）
- dist/leetcode-app/leetcode-app.exe          —— 控制台版 CLI（调试用）
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "leetcode-app.spec"
PRODUCTS = ("LeetCode刷题管理", "leetcode-app")
TESTS = tuple(ROOT / "tests" / f"test_phase{i}.py" for i in (1, 2, 3, 4)) + (ROOT / "tests" / "test_delete.py",)

# Windows GBK 控制台打印 ✅/中文会崩（HANDOVER §5-8），统一转 UTF-8
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def run(cmd: list[str]) -> None:
    print("$ " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        raise SystemExit(f"❌ 命令失败（exit {proc.returncode}）：{' '.join(cmd)}")


def ensure_not_running() -> None:
    """exe 运行中会锁住 dist 目录文件，导致 PyInstaller 删旧目录失败。"""
    for name in PRODUCTS:
        exe_name = f"{name}.exe"
        proc = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if exe_name.lower() in (proc.stdout or "").lower():
            raise SystemExit(f"❌ {exe_name} 正在运行，请先关闭再打包（否则文件被占用）。")


def run_tests() -> None:
    print("== 打包前测试 ==", flush=True)
    for test in TESTS:
        run([sys.executable, str(test)])


def clean_dist() -> None:
    """打包前清空 dist/：只留本次打包的新版本（旧版本不留档）。"""
    if DIST.exists():
        print("清空 dist/（只留本次新版本）", flush=True)
        shutil.rmtree(DIST, ignore_errors=True)


def clean_build() -> None:
    if BUILD.exists():
        print("清空 build/（PyInstaller 中间产物）", flush=True)
        shutil.rmtree(BUILD, ignore_errors=True)


def fix_integrity_level() -> None:
    """把 dist 产物的完整性标签重置为 Medium。

    工作区由沙箱创建时会被打上 Low Mandatory Label（继承给新构建的 exe），
    Windows 会把带 Low 标签的 exe 以低完整性运行 → ShellExecute 被拒、
    子进程（explorer/Obsidian/PyCharm）全部异常（2026-10-15 实测踩坑）。
    """
    print("重置 dist 完整性标签为 Medium", flush=True)
    subprocess.run(
        ["icacls", str(DIST), "/setintegritylevel", "(OI)(CI)M", "/T", "/C"],
        cwd=ROOT, capture_output=True,
    )


def report() -> None:
    print("\n✅ 打包完成：", flush=True)
    for name in PRODUCTS:
        exe = DIST / name / f"{name}.exe"
        if exe.is_file():
            size_mb = exe.stat().st_size / 1024 / 1024
            print(f"   {exe.relative_to(ROOT)}  ({size_mb:.1f} MB)", flush=True)
        else:
            print(f"   ⚠ 未找到 {exe.relative_to(ROOT)}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="打包 LeetCode 刷题管理（自动测试 + 只留一份上一版）")
    ap.add_argument("--skip-tests", action="store_true", help="跳过打包前的测试")
    args = ap.parse_args()

    ensure_not_running()
    if not args.skip_tests:
        run_tests()
    clean_dist()
    clean_build()
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC)])
    fix_integrity_level()
    report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
