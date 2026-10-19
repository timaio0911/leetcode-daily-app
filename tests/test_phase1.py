"""阶段 1 验证：新建题目全链路（手动元数据降级模式 + 抓取模式）。

运行（仓库外、workspace 根目录）：
    python tests/test_phase1.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Windows 控制台（GBK）也能打印 ✅/❌/中文
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from app.config import AppConfig, save_config, config_file  # noqa: E402
from app.core import leetcode, scaffold, vault as vault_mod  # noqa: E402


def make_sandbox() -> tuple[Path, Path]:
    """临时 home（放 config）+ 临时 vault（复制模板）。"""
    home = Path(tempfile.mkdtemp(prefix="lc-home-"))
    vault = Path(tempfile.mkdtemp(prefix="lc-vault-"))
    os.environ["LEETCODE_DAILY_HOME"] = str(home)
    (vault / "templates").mkdir()
    for name in ("problem.md", "daily.md", "solution.py"):
        (vault / "templates" / name).write_text(
            (WORKSPACE / "leetcode-daily" / "templates" / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    (vault / "problems").mkdir()
    (vault / "dashboard").mkdir()
    save_config(AppConfig(vault_path=str(vault), fetch_enabled=True))
    return home, vault


def check(cond: bool, msg: str) -> None:
    print(("  ✅ " if cond else "  ❌ ") + msg)
    if not cond:
        raise SystemExit(f"验证失败：{msg}")


def test_manual_scaffold(vault: Path) -> None:
    print("用例 1：手动元数据降级建题（不联网）")
    meta = leetcode.ProblemMeta(
        id="1", title="两数之和", slug="two-sum",
        url="https://leetcode.cn/problems/two-sum/",
        difficulty="简单", tags=["数组", "哈希表"],
    )
    result = scaffold.scaffold_problem(vault, meta, day="2026-06-04")

    check(result.problem_dir.name == "0001-two-sum", "目录命名 0001-two-sum")
    check(result.solution.is_file(), "solution.py 已生成")
    check(result.readme.is_file(), "README.md 已生成")
    readme = result.readme.read_text(encoding="utf-8")
    check("id: 0001" in readme, "frontmatter id 补零")
    check("两数之和" in readme, "标题已填入")
    check("[数组, 哈希表]" in readme, "标签已填入")
    meta_parsed, _ = vault_mod.parse_frontmatter(readme)
    check(meta_parsed.get("tags") == ["数组", "哈希表"], "标签 round-trip 一致")
    check("题目原题：[力扣 0001. 两数之和](https://leetcode.cn/problems/two-sum/)" in readme,
          "题面仅存链接（版权红线）")
    check("content" not in readme.split("---")[1], "frontmatter 无 content 字段（版权红线）")
    # 「题目理解」只是自述引导占位，不含任何题面原文（版权红线）
    check("用自己的话总结" in readme, "题目理解为自述化引导占位")

    daily = result.daily.read_text(encoding="utf-8")
    check("count: 1" in daily, "daily.md count=1")
    check("| 0001 两数之和 | 简单 | - |" in daily, "daily.md 打卡行")

    # 重复建题幂等：README 不覆盖、daily 不重复追加
    result2 = scaffold.scaffold_problem(vault, meta, day="2026-06-04")
    check(result2.reused, "重复建题标记 reused，不覆盖已有文件")
    daily2 = result2.daily.read_text(encoding="utf-8")
    check(daily2.count("0001 两数之和") == 1, "重复建题 daily.md 不重复追加")

    # 第二题：daily 行数递增
    meta2 = leetcode.ProblemMeta(
        id="42", title="接雨水", slug="trapping-rain-water",
        url="https://leetcode.cn/problems/trapping-rain-water/",
        difficulty="困难", tags=["栈", "数组"],
    )
    result3 = scaffold.scaffold_problem(vault, meta2, day="2026-06-04")
    daily3 = result3.daily.read_text(encoding="utf-8")
    check(result3.problem_dir.name == "0042-trapping-rain-water", "四位补零 0042-…")
    check("count: 2" in daily3, "daily.md count=2")
    check(daily3.index("0001") < daily3.index("0042"), "打卡行按目录名排序")

    days = vault_mod.scan_vault(vault)
    check(len(days) == 1 and len(days[0].problems) == 2, "scan_vault 扫描到 1 天 2 题")
    s = vault_mod.summarize(days)
    check(s["total"] == 2 and s["by_difficulty"] == {"简单": 1, "困难": 1}, "基础统计正确")


def test_frontmatter_edge(vault: Path) -> None:
    print("用例 4：frontmatter 边界（引号包裹的含逗号标签）")
    meta = leetcode.ProblemMeta(
        id="15", title="三数之和", slug="3sum",
        url="https://leetcode.cn/problems/3sum/",
        difficulty="中等", tags=["数组", "双指针, 排序"],
    )
    result = scaffold.scaffold_problem(vault, meta, day="2026-06-04")
    meta2, _ = vault_mod.parse_frontmatter(result.readme.read_text(encoding="utf-8"))
    check(meta2.get("tags") == ["数组", "双指针, 排序"], "含逗号标签 round-trip 一致")
    daily = result.daily.read_text(encoding="utf-8")
    check("count: 3" in daily, "daily.md count=3")
    check("0015 三数之和" in daily, "第三题打卡行正确")


def test_extract_slug() -> None:
    print("用例 2：URL/slug 识别")
    check(leetcode.extract_slug("https://leetcode.cn/problems/two-sum/") == "two-sum", "标准 URL")
    check(leetcode.extract_slug("https://leetcode.cn/problems/two-sum/description/") == "two-sum", "description URL")
    check(leetcode.extract_slug("trapping-rain-water") == "trapping-rain-water", "裸 slug")
    check(leetcode.extract_slug("不是题目") is None, "非法输入返回 None")


def test_fetch_offline(vault: Path) -> None:
    print("用例 3：抓取降级（网络不可用时返回 None，不抛异常）")
    meta = leetcode.fetch_meta("nonexistent-problem-xyz", vault, use_cache=False, timeout=3.0)
    # 有网且题不存在 → None；无网 → None。两者都应为 None 或元数据（仅当恰好存在该题才非 None）。
    check(meta is None or isinstance(meta, leetcode.ProblemMeta), "fetch_meta 优雅降级，不抛异常")

    # 缓存命中路径
    cache_path = vault / "dashboard" / "fetch-cache.json"
    if meta is not None:
        check(cache_path.is_file(), "抓取成功写入缓存")
        meta2 = leetcode.fetch_meta(meta.slug, vault, use_cache=True)
        check(meta2 is not None and meta2.title == meta.title, "缓存命中返回一致元数据")


def main() -> None:
    _, vault = make_sandbox()
    print(f"沙箱 vault：{vault}")
    test_extract_slug()
    test_manual_scaffold(vault)
    test_frontmatter_edge(vault)
    test_fetch_offline(vault)
    print("\n全部用例通过 ✅")


if __name__ == "__main__":
    main()
