"""删除功能验收自测：选择并删除之前记录的题目。

验收目标：
- 单题删除 → 题目录整体删除，同日其他题保留，daily.md 打卡表自动重建；
- 整日删空 → daily.md 保留（用户手写「今日心得」不丢），扫描不再显示该日；
- 批量跨日删除 → problems-by-id/INDEX.md 同步重建（不留失效链接）；
- 安全红线 → 只允许删 problems/<date>/<NNNN-slug>/，其余路径一律拒绝；
- 重复选择 → 同一题只删一次。

    py tests/test_delete.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app.core import delete, review, scaffold  # noqa: E402
from app.core.leetcode import ProblemMeta  # noqa: E402
from app.core.vault import scan_vault  # noqa: E402


def check(cond: bool, msg: str) -> None:
    print(("  ✅ " if cond else "  ❌ ") + msg)
    if not cond:
        raise SystemExit(f"验证失败：{msg}")


def make_sandbox() -> Path:
    vault = Path(tempfile.mkdtemp(prefix="lc-del-"))
    (vault / "templates").mkdir()
    real_templates = WORKSPACE / "leetcode-daily" / "templates"
    for name in ("problem.md", "daily.md", "solution.py"):
        src = real_templates / name
        dst = vault / "templates" / name
        if src.is_file():
            shutil.copy(src, dst)
        else:
            dst.write_text(f"# {name}\n", encoding="utf-8")
    return vault


def add(vault: Path, pid: str, title: str, slug: str, day: str, difficulty: str = "简单"):
    meta = ProblemMeta(id=pid, title=title, slug=slug,
                       url=f"https://leetcode.cn/problems/{slug}/",
                       difficulty=difficulty, tags=["数组"])
    return scaffold.scaffold_problem(vault, meta, day=day)


def test_delete_single(vault: Path) -> None:
    print("用例 1：单题删除（同日其他题保留 + daily.md 重建 + 心得保留）")
    r1 = add(vault, "1", "两数之和", "two-sum", "2026-06-04")
    r2 = add(vault, "42", "接雨水", "trapping-rain-water", "2026-06-04", difficulty="困难")
    daily = r1.daily
    head, mark, _ = daily.read_text(encoding="utf-8").partition("**今日心得**")
    daily.write_text(head + mark + "\n今天手感不错\n", encoding="utf-8")

    result = delete.delete_problem(vault, r1.problem_dir)
    check(not r1.problem_dir.exists(), "被删题目录已移除")
    check(r2.problem_dir.is_dir(), "同日其他题目保留")
    check(result.dates == ["2026-06-04"], "受影响日期记录正确")

    text = daily.read_text(encoding="utf-8")
    check("two-sum" not in text, "daily.md 不含被删题目链接")
    check("trapping-rain-water" in text, "daily.md 保留其余题目行")
    check("今天手感不错" in text, "用户手写「今日心得」不被重建覆盖")

    days = scan_vault(vault)
    titles = [p.title for d in days for p in d.problems]
    check("两数之和" not in titles and "接雨水" in titles, "扫描结果同步消失/保留")


def test_delete_all_of_day(vault: Path) -> None:
    print("用例 2：整日删空（daily.md 保留、扫描不再显示该日）")
    r = add(vault, "3", "无重复字符的最长子串", "longest-substring-without-repeating-characters",
            "2026-06-05", difficulty="中等")
    delete.delete_problem(vault, r.problem_dir)

    daily = vault / "problems" / "2026-06-05" / "daily.md"
    check(daily.is_file(), "整日删空后 daily.md 保留（不删用户笔记）")
    text = daily.read_text(encoding="utf-8")
    check("longest-substring" not in text, "daily.md 表格已清空该行")
    check(vault.joinpath("problems", "2026-06-05").is_dir(), "日期目录保留")
    check(all(d.date != "2026-06-05" for d in scan_vault(vault)), "扫描不再显示无题日期")


def test_batch_and_index(vault: Path) -> None:
    print("用例 3：批量跨日删除 + 题号索引同步重建")
    r1 = add(vault, "1", "两数之和", "two-sum", "2026-07-01")
    r2 = add(vault, "1", "两数之和", "two-sum", "2026-07-02")   # 同题号跨日期二刷
    r3 = add(vault, "49", "字母异位词分组", "group-anagrams", "2026-07-02", difficulty="中等")
    index = review.write_id_index(vault)
    before = index.read_text(encoding="utf-8")
    check("2026-07-01" in before and "2026-07-02" in before, "索引含两次练习记录")

    result = delete.delete_problems(vault, [r1.problem_dir, r3.problem_dir])
    check(len(result.deleted) == 2, "批量删除 2 题")
    check(result.dates == ["2026-07-01", "2026-07-02"], "受影响日期去重汇总")
    check(result.index == index and index.is_file(), "题号索引已同步重建")

    after = index.read_text(encoding="utf-8")
    check("2026-07-01" not in after, "索引移除已删记录")
    check("group-anagrams" not in after and "字母异位词分组" not in after, "索引移除已删题目分组")
    check("2026-07-02" in after and "两数之和" in after, "保留记录仍聚合在索引中")
    check(r2.problem_dir.is_dir(), "未选中的题目不受影响")

    # 未生成过索引的 vault 删除时不主动创建
    vault2 = make_sandbox()
    r = add(vault2, "1", "两数之和", "two-sum", "2026-07-01")
    result2 = delete.delete_problem(vault2, r.problem_dir)
    check(result2.index is None, "未生成过索引则删除后不创建 INDEX.md")


def test_safety(vault: Path) -> None:
    print("用例 4：安全红线（只删题目录，其余路径拒绝）")
    outside = Path(tempfile.mkdtemp(prefix="lc-outside-"))
    (outside / "keep.txt").write_text("important", encoding="utf-8")
    bad_date = vault / "problems" / "not-a-date"
    bad_date.mkdir(parents=True, exist_ok=True)
    not_problem = bad_date / "somedir"
    not_problem.mkdir(exist_ok=True)

    for target, label in (
        (outside, "数据目录之外"),
        (vault / "problems", "problems 根目录"),
        (bad_date, "非法日期目录"),
        (not_problem, "非题目名目录"),
        (vault / "problems" / "2026-06-04" / "0999-ghost", "不存在的题目录"),
    ):
        try:
            delete.delete_problem(vault, target)
            check(False, f"{label} 应拒绝删除")
        except delete.DeleteError:
            check(True, f"{label} 被拒绝 ✅")
    check(outside.joinpath("keep.txt").is_file(), "目录外文件安然无恙")
    check(not_problem.is_dir(), "非题目目录安然无恙")


def test_dedup(vault: Path) -> None:
    print("用例 5：重复选择去重")
    r = add(vault, "5", "最长回文子串", "longest-palindromic-substring", "2026-07-03", difficulty="中等")
    result = delete.delete_problems(vault, [r.problem_dir, r.problem_dir])
    check(len(result.deleted) == 1, "同一题重复选择只删一次")


def main() -> None:
    vault = make_sandbox()
    print(f"沙箱 vault：{vault}")
    test_delete_single(vault)
    test_delete_all_of_day(vault)
    test_batch_and_index(vault)
    test_safety(vault)
    test_dedup(vault)
    print("\n全部用例通过 ✅")


if __name__ == "__main__":
    main()
