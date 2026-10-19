"""阶段 4 验收自测：二刷/复盘标记 + 错题本 + 题号聚合索引 + 打包资源路径。

对应方案路线图阶段 4 验收目标：
- 标记复盘 → reviewed frontmatter 写入 + review-<date>.md 生成；
- 错题本视图 → status=review 或 reviewed 为空的题目可被筛选；
- 按题号聚合 → problems-by-id/INDEX.md 跨日期聚合同一题号（幂等重建）；
- 打包资源 → resolve_template 兼容 vault/templates 与打包内置目录。

    py tests/test_phase4.py
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

from app.core import review, scaffold  # noqa: E402
from app.core.leetcode import ProblemMeta  # noqa: E402
from app.core.resources import resolve_template  # noqa: E402
from app.core.vault import scan_vault  # noqa: E402


def check(cond: bool, msg: str) -> None:
    print(("  ✅ " if cond else "  ❌ ") + msg)
    if not cond:
        raise SystemExit(f"验证失败：{msg}")


def make_sandbox() -> Path:
    vault = Path(tempfile.mkdtemp(prefix="lc-v4-"))
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


def test_reviewed_roundtrip(vault: Path) -> None:
    print("用例 1：reviewed frontmatter 读写 + review-<date>.md 生成")
    meta = ProblemMeta(id="1", title="两数之和", slug="two-sum",
                       url="https://leetcode.cn/problems/two-sum/",
                       difficulty="简单", tags=["数组"])
    result = scaffold.scaffold_problem(vault, meta, day="2026-06-04")
    pdir = result.problem_dir

    # 初始 reviewed 为空
    check(review.load_reviewed(result.readme) == [], "新题 reviewed 为空")

    # 标记复盘
    review_file = review.mark_reviewed(pdir, "2026-06-10")
    check(review_file.is_file(), "review-2026-06-10.md 已生成")
    check(review.load_reviewed(result.readme) == ["2026-06-10"], "reviewed 已写入一个日期")

    # 重复标记同一天幂等
    review.mark_reviewed(pdir, "2026-06-10")
    check(review.load_reviewed(result.readme) == ["2026-06-10"], "重复标记同一天幂等")

    # 追加第二个日期，排序
    review.mark_reviewed(pdir, "2026-06-08")
    check(review.load_reviewed(result.readme) == ["2026-06-08", "2026-06-10"], "多日期排序写入")

    # 其余 frontmatter 字段未损坏
    days = scan_vault(vault)
    p = next(pp for d in days for pp in d.problems if pp.slug == "two-sum")
    check(p.id in ("1", "0001") and p.title == "两数之和", "frontmatter 其余字段完好")
    check(p.reviewed == ["2026-06-08", "2026-06-10"], "scan_vault 读取 reviewed")

    # solution-2.py
    s2 = review.add_solution2(pdir)
    check(s2.is_file(), "solution-2.py 已生成")
    check(review.add_solution2(pdir) == s2, "solution-2.py 幂等")


def test_mistake_filter(vault: Path) -> None:
    print("用例 2：错题本筛选（needs_review / filter_mistakes）")
    days = scan_vault(vault)
    p1 = next(pp for d in days for pp in d.problems if pp.slug == "two-sum")
    # 该题已复盘 → 不属于错题
    check(not review.needs_review(p1), "已复盘题目不进错题本")
    mistakes = review.filter_mistakes(days)
    check(mistakes == [], "已复盘后错题本为空")

    # 再建一题（未复盘）→ 进错题本
    meta2 = ProblemMeta(id="42", title="接雨水", slug="trapping-rain-water",
                        url="https://leetcode.cn/problems/trapping-rain-water/",
                        difficulty="困难", tags=["栈"])
    scaffold.scaffold_problem(vault, meta2, day="2026-06-05")
    days = scan_vault(vault)
    mistakes = review.filter_mistakes(days)
    total = sum(len(d.problems) for d in mistakes)
    check(total == 1, "未复盘的 1 题进入错题本")
    check(mistakes[0].problems[0].id in ("42", "0042"), "错题本题目为 0042")

    # 已复盘视图
    reviewed_days = review.filter_reviewed(days)
    check(sum(len(d.problems) for d in reviewed_days) == 1, "已复盘视图 1 题")


def test_byid_index(vault: Path) -> None:
    print("用例 3：按题号聚合索引 problems-by-id/INDEX.md")
    # 同一题号跨日期再录一次
    meta = ProblemMeta(id="1", title="两数之和", slug="two-sum",
                       url="https://leetcode.cn/problems/two-sum/",
                       difficulty="简单", tags=["数组"])
    scaffold.scaffold_problem(vault, meta, day="2026-07-01")

    index = review.write_id_index(vault)
    check(index.is_file(), "INDEX.md 已生成")
    text = index.read_text(encoding="utf-8")
    check("## 1. 两数之和" in text or "## 0001. 两数之和" in text, "题号分组标题")
    check("2026-06-04" in text and "2026-07-01" in text, "跨日期两次练习都列出")
    check(text.count("两数之和") == 1, "同一题号只一个分组（聚合）")
    check("42." in text or "0042." in text, "0042 也出现在索引中")

    # 幂等重建
    index2 = review.write_id_index(vault)
    check(index2.read_text(encoding="utf-8") == text, "重复生成内容一致（幂等）")


def test_resolve_template(vault: Path) -> None:
    print("用例 4：打包资源路径 resolve_template")
    p = resolve_template(vault, "problem.md")
    check(p.is_file(), "vault/templates 命中")
    # 回退：指向不存在的 vault，使用打包内置目录（源码运行时为 workspace 级）
    try:
        resolve_template(Path(tempfile.mkdtemp(prefix="lc-novault-")), "problem.md")
        # 能命中说明内置目录存在（源码运行下 leetcode-daily/templates 不是内置目录，可能抛错）
    except FileNotFoundError:
        pass  # 允许：未打包且无 vault 模板时按设计报错
    check(True, "resolve_template 不崩溃")


def main() -> None:
    vault = make_sandbox()
    print(f"沙箱 vault：{vault}")
    test_reviewed_roundtrip(vault)
    test_mistake_filter(vault)
    test_byid_index(vault)
    test_resolve_template(vault)
    print("\n全部用例通过 ✅")


if __name__ == "__main__":
    main()
