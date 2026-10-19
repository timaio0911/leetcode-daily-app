"""阶段 2 验收自测：gitops / launcher / 筛选 / 约定式提交信息。

运行（workspace 根目录）：
    py tests/test_phase2.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from app.core import gitops  # noqa: E402
from app.core.launcher import LaunchError, open_idea  # noqa: E402
from app.core.vault import DayEntry, ProblemEntry  # noqa: E402
from app.ui.problem_list import collect_tags, filter_days  # noqa: E402


def check(cond: bool, msg: str) -> None:
    print(("  ✅ " if cond else "  ❌ ") + msg)
    if not cond:
        raise SystemExit(f"验证失败：{msg}")


def make_repo() -> Path:
    repo = Path(tempfile.mkdtemp(prefix="lc-git-"))
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@local"], cwd=repo, check=True)
    return repo


def test_gitops() -> None:
    print("用例 1：gitops（沙箱仓库）")
    repo = make_repo()

    status = gitops.git_status(repo)
    check(status.clean, "新仓库工作区干净")

    (repo / "a.txt").write_text("hello", encoding="utf-8")
    status = gitops.git_status(repo)
    check(not status.clean and any("a.txt" in p for p in status.changed), "检测到未跟踪文件")

    # 未跟踪目录应展开为具体文件（约定式提交信息依赖文件级路径）
    (repo / "problems" / "2026-06-04" / "0001-two-sum").mkdir(parents=True)
    (repo / "problems" / "2026-06-04" / "0001-two-sum" / "README.md").write_text("x", encoding="utf-8")
    status = gitops.git_status(repo)
    check("problems/2026-06-04/0001-two-sum/README.md" in status.changed, "未跟踪目录展开为文件")

    result = gitops.commit_all(repo, "2026-06-04: add 0001 two-sum")
    check("已提交" in result, "add+commit 成功")
    check(gitops.git_status(repo).clean, "提交后工作区干净")

    result = gitops.commit_all(repo, "empty")
    check("无改动" in result, "空提交不报错")

    proc = subprocess.run(["git", "log", "-1", "--pretty=%s"], cwd=repo,
                          capture_output=True, text=True, check=True)
    check(proc.stdout.strip() == "2026-06-04: add 0001 two-sum", "commit 信息为约定式")

    check(not gitops.has_remote(repo), "无远程时 has_remote=False")
    try:
        gitops.push(repo)
        check(False, "无远程 push 应报错")
    except gitops.GitError as exc:
        check("push" in str(exc), "无远程 push 报 GitError")


def test_commit_message() -> None:
    print("用例 2：约定式提交信息")
    check(gitops.commit_message_for("2026-06-04", "1", "two-sum") == "2026-06-04: add 0001 two-sum",
          "题号补零格式")
    check(gitops.commit_message_for("2026-06-04", "42", "trapping-rain-water")
          == "2026-06-04: add 0042 trapping-rain-water", "多位题号")


def test_launcher_errors() -> None:
    print("用例 3：launcher 错误路径（不实际拉起程序）")
    try:
        open_idea("", Path("x.py"))
        check(False, "未配置 IDEA 应报错")
    except LaunchError as exc:
        check("未配置" in str(exc), "未配置 IDEA 路径报 LaunchError")
    try:
        open_idea("Z:\\not-exist\\idea64.exe", Path("x.py"))
        check(False, "路径不存在应报错")
    except LaunchError as exc:
        check("不存在" in str(exc), "IDEA 路径不存在报 LaunchError")


def _problem(pid: str, title: str, difficulty: str, tags: list[str]) -> ProblemEntry:
    return ProblemEntry(
        id=pid, slug=title, title=title, url="", difficulty=difficulty,
        tags=tags, date="2026-06-04", status="todo", time_spent="",
        dir=Path("."), readme=Path("README.md"), solution=None,
    )


def test_filters() -> None:
    print("用例 4：难度/标签筛选")
    days = [DayEntry(date="2026-06-04", problems=[
        _problem("1", "两数之和", "简单", ["数组", "哈希表"]),
        _problem("42", "接雨水", "困难", ["栈", "数组"]),
    ])]
    check(len(filter_days(days, "简单", None)[0].problems) == 1, "按难度筛选")
    check(len(filter_days(days, None, "数组")[0].problems) == 2, "按标签筛选")
    check(filter_days(days, "困难", "哈希表") == [], "组合筛选无结果返回空")
    check(filter_days(days, None, None) == days, "无筛选返回原数据")
    check(collect_tags(days) == ["哈希表", "数组", "栈"], "标签收集去重排序")


def main() -> None:
    test_gitops()
    test_commit_message()
    test_launcher_errors()
    test_filters()
    print("\n全部用例通过 ✅")


if __name__ == "__main__":
    main()
