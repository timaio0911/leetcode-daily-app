"""命令行入口（阶段 1 验证：CLI 先跑通新建题目全链路）。

用法：
    python app new "https://leetcode.cn/problems/two-sum/"   # 新建题目
    python app new "two-sum" --title 两数之和 --difficulty 简单   # 手动元数据（降级）
    python app list                                          # 题目列表
    python app delete 1 two-sum                              # 删除题目记录（可多个，-y 跳过确认）
    python app stats                                         # 基础统计
    python app open 1 code                                   # IDEA 打开代码（note/dir 可选）
    python app status                                        # git 改动
    python app commit -m "msg" --push                        # 一键提交
    python app gui                                           # 启动完整 GUI
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 支持 `python app ...` 目录形式调用（此时 cwd 不在 sys.path，包根需手动加入）
_PKG_ROOT = Path(__file__).resolve().parent.parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from app.config import load_config, resolve_vault
from app.core import leetcode, scaffold, vault as vault_mod


def cmd_new(args: argparse.Namespace) -> int:
    cfg = load_config()
    vault = resolve_vault(cfg)
    slug = leetcode.extract_slug(args.query)
    if slug is None:
        print(f"无法识别题目：{args.query!r}（请粘贴 leetcode.cn 题目 URL 或 slug）", file=sys.stderr)
        return 2

    meta: leetcode.ProblemMeta | None = None
    if cfg.fetch_enabled and not args.no_fetch:
        meta = leetcode.fetch_meta(slug, vault, use_cache=not args.no_cache)
        if meta is None:
            print("⚠ 抓取元数据失败/离线，降级为手动填写。")

    if meta is None:
        if not args.title:
            print("手动模式需要 --title（如：--title 两数之和），可选 --id/--difficulty/--tags", file=sys.stderr)
            return 2
        meta = leetcode.ProblemMeta(
            id=args.id or "0",
            title=args.title,
            slug=slug,
            url=f"https://leetcode.cn/problems/{slug}/",
            difficulty=args.difficulty or "",
            tags=[t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else [],
        )

    result = scaffold.scaffold_problem(vault, meta, day=args.date)
    tag = "（目录已存在，跳过重复创建）" if result.reused else ""
    print(f"✅ 新建完成{tag}")
    print(f"   题目：{meta.id_title}  [{meta.difficulty}]")
    print(f"   目录：{result.problem_dir}")
    print(f"   打卡：{result.daily}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    cfg = load_config()
    days = vault_mod.scan_vault(resolve_vault(cfg))
    if not days:
        print("（还没有题目，先 `python app new <题目链接>`）")
        return 0
    for day in days:
        print(f"{day.date}  ({len(day.problems)} 题)")
        for p in day.problems:
            print(f"   {p.id.zfill(4)}  {p.title:<20}  [{p.difficulty or '?'}]  {p.status}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    from app.core.stats import compute_stats
    cfg = load_config()
    days = vault_mod.scan_vault(resolve_vault(cfg))
    s = compute_stats(days)
    print(f"累计题目：{s.total}  活跃天数：{s.active_days}  今日：{s.today_count}")
    print(f"连续打卡：{s.streak} 天（最长 {s.best_streak} 天）")
    print(f"难度分布：{s.by_difficulty}")
    print(f"状态分布：{s.by_status}")
    if s.daily:
        print("每日趋势：" + "  ".join(f"{d}={c}" for d, c in s.daily[-7:]))
    return 0


def cmd_readme(args: argparse.Namespace) -> int:
    from app.core.stats import compute_stats, update_readme_stats
    cfg = load_config()
    vault = resolve_vault(cfg)
    days = vault_mod.scan_vault(vault)
    readme = update_readme_stats(vault, compute_stats(days))
    print(f"✅ 统计段落已写入 {readme}")
    return 0


def cmd_gui(args: argparse.Namespace) -> int:
    from app.ui.main_window import run_gui
    return run_gui()


def _find_problem(vault, query: str):
    """按题号/slug/标题查找题目（供 open/commit 定位）。"""
    days = vault_mod.scan_vault(vault)
    q = query.strip().lower()
    qn = q.lstrip("0") or "0"  # frontmatter 数字 id 会丢前导零（"0049"→"49"），双向归一
    for day in days:
        for p in day.problems:
            pid = p.id.lstrip("0") or "0"
            if qn == pid or q in (p.id, p.slug.lower(), p.title.lower()):
                return day, p
    return None, None


def cmd_open(args: argparse.Namespace) -> int:
    from app.core.launcher import LaunchError, open_folder, open_idea, open_obsidian
    cfg = load_config()
    vault = resolve_vault(cfg)
    _, p = _find_problem(vault, args.query)
    if p is None:
        print(f"未找到题目：{args.query}", file=sys.stderr)
        return 2
    try:
        if args.target == "code":
            if p.solution is None:
                print(f"{p.id_title} 没有 solution.py", file=sys.stderr)
                return 1
            print(open_idea(cfg.idea_path, p.solution))
        elif args.target == "note":
            print(open_obsidian(vault, p.readme, cfg.obsidian_path))
        else:
            print(open_folder(p.dir))
    except LaunchError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    """删除题目记录（按题号/slug/标题，可多个；-y 跳过确认）。"""
    from app.core.delete import DeleteError, delete_problems, describe
    cfg = load_config()
    vault = resolve_vault(cfg)
    problems = []
    seen: set[str] = set()
    for q in args.query:
        _, p = _find_problem(vault, q)
        if p is None:
            print(f"未找到题目：{q}", file=sys.stderr)
            return 2
        if str(p.dir) not in seen:  # 同一题重复匹配只删一次
            seen.add(str(p.dir))
            problems.append(p)

    print("将删除以下题目记录（目录整体删除，含代码/笔记/复盘）：")
    for p in problems:
        print(f"   {describe(p)}")
    if not args.yes:
        answer = input("确认删除？[y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("已取消。")
            return 0

    try:
        result = delete_problems(vault, problems)
    except DeleteError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    print(f"✅ 已删除 {len(result.deleted)} 题")
    for d in result.deleted:
        print(f"   {d}")
    for daily in result.daily_files.values():
        print(f"   打卡已重建：{daily}")
    if result.index:
        print(f"   题号索引已重建：{result.index}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    from app.core import gitops
    cfg = load_config()
    vault = resolve_vault(cfg)
    status = gitops.git_status(vault)
    print(f"分支：{status.branch or '?'}")
    if status.clean:
        print("工作区干净，无改动。")
        return 0
    for path in status.changed:
        print(f"  改动：{path}")
    return 0


def cmd_commit(args: argparse.Namespace) -> int:
    from app.core import gitops
    from datetime import date as date_cls
    cfg = load_config()
    vault = resolve_vault(cfg)
    status = gitops.git_status(vault)
    if status.clean:
        print("没有改动，无需提交。")
        return 0
    message = args.message or f"{date_cls.today().isoformat()}: update vault ({len(status.changed)} files)"
    try:
        print(gitops.commit_all(vault, message))
        if args.push:
            if gitops.has_remote(vault, cfg.git_remote):
                print(gitops.push(vault, cfg.git_remote))
            else:
                print(f"（未配置远程 {cfg.git_remote}，跳过 push）")
    except gitops.GitError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    """阶段 4：标记复盘（reviewed frontmatter + review-<date>.md），或列出错题本。"""
    from datetime import date as date_cls
    from app.core.review import filter_mistakes, mark_reviewed
    cfg = load_config()
    vault = resolve_vault(cfg)
    if args.query is None:
        # 列出错题本
        days = filter_mistakes(vault_mod.scan_vault(vault))
        if not days:
            print("错题本为空 ✅")
            return 0
        for day in days:
            for p in day.problems:
                print(f"   {p.id.zfill(4)}  {p.title:<20}  [{p.difficulty or '?'}]  {p.status}")
        return 0
    _, p = _find_problem(vault, args.query)
    if p is None:
        print(f"未找到题目：{args.query}", file=sys.stderr)
        return 2
    today = args.date or date_cls.today().isoformat()
    review_file = mark_reviewed(p.dir, today)
    print(f"✅ 已标记复盘：{p.id_title}  日期 {today}")
    print(f"   复盘笔记：{review_file}")
    return 0


def cmd_byid(args: argparse.Namespace) -> int:
    """阶段 4：生成/更新按题号聚合索引 problems-by-id/INDEX.md。"""
    from app.core.review import write_id_index
    cfg = load_config()
    vault = resolve_vault(cfg)
    index = write_id_index(vault)
    print(f"✅ 题号索引已生成：{index}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app", description="LeetCode 刷题管理")
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="新建题目（抓元数据 → 建目录 → 模板 → 更新打卡）")
    p_new.add_argument("query", help="题目 URL 或 slug")
    p_new.add_argument("--date", help="归档日期 YYYY-MM-DD（默认今天）")
    p_new.add_argument("--no-fetch", action="store_true", help="跳过网络抓取，直接手动填写")
    p_new.add_argument("--no-cache", action="store_true", help="忽略抓取缓存，强制重新请求")
    p_new.add_argument("--id", help="手动元数据：题号")
    p_new.add_argument("--title", help="手动元数据：标题（降级模式必填）")
    p_new.add_argument("--difficulty", help="手动元数据：难度（简单/中等/困难）")
    p_new.add_argument("--tags", help="手动元数据：标签，逗号分隔")
    p_new.set_defaults(func=cmd_new)

    p_list = sub.add_parser("list", help="按日期列出题目")
    p_list.set_defaults(func=cmd_list)

    p_delete = sub.add_parser("delete", help="删除题目记录（按题号/slug/标题，可多个）")
    p_delete.add_argument("query", nargs="+", help="题号 / slug / 标题")
    p_delete.add_argument("-y", "--yes", action="store_true", help="跳过确认直接删除")
    p_delete.set_defaults(func=cmd_delete)

    p_stats = sub.add_parser("stats", help="基础统计")
    p_stats.set_defaults(func=cmd_stats)

    p_readme = sub.add_parser("readme", help="生成/更新 README 统计段落")
    p_readme.set_defaults(func=cmd_readme)

    p_gui = sub.add_parser("gui", help="启动桌面窗口")
    p_gui.set_defaults(func=cmd_gui)

    p_open = sub.add_parser("open", help="打开题目（code=IDEA / note=Obsidian / dir=文件夹）")
    p_open.add_argument("query", help="题号 / slug / 标题")
    p_open.add_argument("target", nargs="?", default="dir", choices=["code", "note", "dir"])
    p_open.set_defaults(func=cmd_open)

    p_status = sub.add_parser("status", help="查看 git 改动")
    p_status.set_defaults(func=cmd_status)

    p_commit = sub.add_parser("commit", help="git add + commit（可选 push）")
    p_commit.add_argument("-m", "--message", help="提交信息（默认汇总式）")
    p_commit.add_argument("--push", action="store_true", help="提交后 push 到远程")
    p_commit.set_defaults(func=cmd_commit)

    p_review = sub.add_parser("review", help="标记复盘 / 列出错题本")
    p_review.add_argument("query", nargs="?", help="题号 / slug / 标题（缺省则列出错题本）")
    p_review.add_argument("--date", help="复盘日期 YYYY-MM-DD（默认今天）")
    p_review.set_defaults(func=cmd_review)

    p_byid = sub.add_parser("byid", help="生成/更新按题号聚合索引 problems-by-id/INDEX.md")
    p_byid.set_defaults(func=cmd_byid)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # Windows 控制台（GBK）也能打印中文/符号
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
