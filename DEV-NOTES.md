# LeetCode 刷题管理软件 —— 开发备忘

> 对应方案：`LeetCode刷题管理软件-方案.md`（v2）。本文记录各阶段的实现偏差与运行方式。

## 仓库布局（阶段 0/1 实际落地）

~~~
workspace/leetcode/
├── LeetCode刷题管理软件-方案.md   # 设计方案 v2
├── app/                          # 管理软件源码（方案 §4.2 的 app/，暂放 workspace 级）
│   ├── __main__.py               # CLI 入口（python <path> 形式运行）
│   ├── config.py                 # 设置读写
│   ├── core/
│   │   ├── leetcode.py           # F1 元数据抓取（只抓元数据，红线内）
│   │   ├── scaffold.py           # F1/F6 建目录/模板/daily.md
│   │   └── vault.py              # frontmatter 解析 + 扫描 + 基础统计
│   └── ui/
│       └── main_window.py        # 最简 PySide6 窗口（列表 + 新建按钮）
├── leetcode-daily/               # ★ 数据仓库（= Obsidian vault，git 仓库）
│   ├── templates/{problem.md,daily.md,solution.py}
│   ├── problems/<date>/<NNNN-slug>/{solution.py,README.md,daily.md}
│   ├── dashboard/{stats.json,fetch-cache.json}
│   └── README.md
└── tests/test_phase1.py          # 阶段 1 验收自测
~~~

### 与方案 §2.2 的偏差
- 方案把 `app/` 放在 leetcode-daily 仓库内；当前实现放在 workspace 级 `app/`，
  运行时通过 `config.vault_path`（默认：app/ 的上级 leetcode-daily/）定位数据目录。
  阶段 4 打包 exe 时再决定是否迁入仓库。
- `.gitignore` 已排除 `.obsidian/`、`dashboard/stats.json`、`dashboard/fetch-cache.json`。

## 运行方式

~~~powershell
cd E:\Agent\deepseek\workspace\leetcode

# 命令行（阶段 1 验收主通道）
python app new "https://leetcode.cn/problems/two-sum/"
python app new "two-sum" --title 两数之和 --difficulty 简单 --tags 数组,哈希表   # 手动降级
python app list
python app stats

# 桌面窗口（需已安装 PySide6）
python app gui

# 阶段 1 自测
python tests/test_phase1.py
~~~

> `python app` 等价于 `python -m app`（目录形式调用 `__main__.py`）。
> 若用 `python -m app`，需先 `cd` 到 `workspace/leetcode` 且保证包可导入（当前目录在 sys.path）。

## 配置文件

`~/.leetcode-daily/config.json`（可用环境变量 `LEETCODE_DAILY_HOME` 重定向）：

~~~json
{
  "vault_path": "E:\\...\\leetcode-daily",
  "idea_path": "",
  "obsidian_path": "",
  "git_remote": "origin",
  "daily_goal": 1,
  "fetch_enabled": true
}
~~~

## 版权红线（实现层已遵守）

- `leetcode.py` 的 GraphQL 查询**不含 `content` 字段**，`ProblemMeta` 无题面文本字段；
- 生成的 README 只有「元数据 + 链接 + 待自述的『题目理解』引导」；
- 元数据缓存 `dashboard/fetch-cache.json` 只存 id/title/url/difficulty/tags。

## 阶段状态

- [x] 阶段 0：仓库结构、模板、.gitignore、README，git 仓库已初始化并提交
- [x] 阶段 1：scaffold + leetcode + CLI 全链路 + 最简 GUI，验收自测全通过
- [x] 阶段 2：完整 GUI（详情预览、难度/标签筛选、跳转 IDEA/Obsidian/文件夹、一键提交 GitHub、设置对话框）+ CLI `open/status/commit`；验收自测 + GUI 提交链路烟测全通过
- [x] 阶段 3：看板统计（每日/每周趋势折线、难度分布柱状图、连续打卡、README 统计段落自动生成）+ CLI `stats/readme`；测试 + 图表截图验证通过
- [x] 阶段 4：二刷/复盘标记（`reviewed` frontmatter + `review-<date>.md` + `solution-2.py`）、错题本视图（GUI 筛选 + CLI `review`）、题号聚合索引（`problems-by-id/INDEX.md` + CLI `byid`）、打包 exe（PyInstaller + `sys._MEIPASS` 适配）；测试 + exe 冒烟验证通过

## 阶段 3 模块

- `app/core/stats.py` —— F3 计算（total/active_days/daily/weekly/streak/best_streak）+ README 统计段落
  （`<!-- LEETCODE-STATS:START/END -->` 标记对包裹，重复更新幂等；纯文本表格 + █ 柱状图，GitHub 渲染友好）
- `app/ui/charts.py` —— QtCharts 折线/柱状图（PySide6-Addons 自带，无需 matplotlib），不可用时降级为文本；
  **注意**：单点数据必须 `setPointsVisible(True)`，否则折线图空白
- `app/ui/dashboard.py` —— 看板页：数字卡片 + 三图表 + 「更新 README 统计段落」按钮
- CLI：`py app stats`（含 streak/趋势）、`py app readme`（生成/更新 README 统计段落）

## 阶段 2 模块

- `app/core/gitops.py` —— F5：`git_status`（未跟踪目录展开为文件）、`commit_all`、`push`、约定式提交信息 `<归档date>: add <id> <slug>`
- `app/core/launcher.py` —— F4：IDEA（配置 exe 路径）、Obsidian（`obsidian://open?vault=<vault名>&file=<相对路径>` URI，免配置）、打开文件夹
- `app/ui/dialogs.py` —— 新建题目对话框（含手动降级）+ 设置对话框（F7）
- `app/ui/problem_list.py` —— F2 题目树 + 难度/标签筛选
- `app/ui/dashboard.py` —— F3 文本汇总卡片（图表在阶段 3）
- `app/ui/main_window.py` —— [今日] [题目列表] [统计] 三标签页 + 底部工具条（新建题目 / 提交 GitHub / 状态）

## 已验证的运行方式（Python 3.13 + PySide6 6.12 + httpx 0.28，2026-10-14 实测）

~~~powershell
cd E:\Agent\deepseek\workspace\leetcode

py app new "https://leetcode.cn/problems/two-sum/"   # 抓取元数据（中文标题/难度/标签）→ 建题 → 更新打卡
py app new "two-sum" --title 两数之和 --difficulty 简单   # 手动降级
py app list
py app stats
py app open 1 code                                   # IDEA 打开代码（note=Obsidian 笔记 / dir=文件夹）
py app status                                        # git 改动清单
py app commit -m "msg" --push                        # 一键提交
py app gui                                           # 完整 GUI（三标签页 + 一键提交）
py app readme                                        # 生成/更新 README 统计段落
py app review                                        # 列出错题本
py app review 1 --date 2026-10-15                    # 标记复盘
py app byid                                          # 生成题号聚合索引
py app delete 1 two-sum -y                           # 删除题目记录（可多个；不带 -y 会先确认）
py tests/test_phase1.py                              # 阶段 1 验收（沙箱）
py tests/test_phase2.py                              # 阶段 2 验收（沙箱）
py tests/test_phase3.py                              # 阶段 3 验收（沙箱）
py tests/test_phase4.py                              # 阶段 4 验收（沙箱）
py tests/test_delete.py                              # 删除功能验收（沙箱）
py package.py                                 # 打包 exe（自动测试 + dist 只留本次新版本 + 清 build）
~~~

## 阶段 4 模块

- `app/core/review.py` —— `reviewed` frontmatter 读写、`mark_reviewed`（生成 `review-<date>.md`）、`add_solution2`（二刷代码）、`needs_review`/`filter_mistakes`/`filter_reviewed`（错题本）、`group_by_id`/`write_id_index`（`problems-by-id/INDEX.md` 幂等重建）
- `app/core/resources.py` —— 打包资源路径（`sys._MEIPASS` / `_internal/` 回退），`scaffold._load_template` 已接入
- `app/ui/problem_list.py` —— 筛选栏新增「全部 / 错题本 / 已复盘」
- `app/ui/main_window.py` —— 详情区新增「标记复盘 ✓」「新建二刷代码」按钮
- CLI：`py app review`（列错题本 / 标记复盘）、`py app byid`（题号索引）
- 打包：`leetcode-app.spec` 双产物 → `dist/LeetCode刷题管理/LeetCode刷题管理.exe`（一键启动 GUI，无控制台，双击即用，崩溃写 `crash.log`）+ `dist/leetcode-app/leetcode-app.exe`（控制台版 CLI）。`launcher_gui.py` 为一键启动入口。

## 删除功能（新增）

- `app/core/delete.py` —— `delete_problem`/`delete_problems`：先做路径安全校验（只允许
  `problems/<date>/<NNNN-slug>/`），删除后重建当日 `daily.md` 与 `problems-by-id/INDEX.md`（若生成过）。
- GUI 三入口：底部「🗑 删除题目…」（勾选对话框，支持按日期级联勾选/全选）、题目树多选 + `Delete` 键、详情区「🗑 删除此题」；执行前均弹确认框。
- CLI：`py app delete <题号/slug/标题…>`（可多个，`-y` 跳过确认）。
- `scaffold.update_daily` 重建打卡表时保留「今日心得」段落（`_preserve_notes`）。
- 删除即真删，误删用 git 历史找回；README 统计段落不自动改（与新建一致，走「更新 README 统计段落」按钮）。

## 实现要点备忘

- 力扣 CN GraphQL `questionData` 实测（2026-10）：**QuestionNode 无 `url` 字段**（URL 按 slug 拼接）；
  中文标题用 `translatedTitle`，中文标签用 `topicTags.translatedName`，难度 Easy/Medium/Hard 自行映射 简单/中等/困难。
- `daily.md` 由当日各题 README 的 frontmatter **重建**（幂等），不是追加；改了元数据后重跑 `new` 即可刷新打卡。
- frontmatter 行内列表支持引号包裹的含逗号标签；模板 `tags: [...]` 的方括号在模板里，scaffold 只填内容。
- `python app <cmd>`（目录形式调用）与 `python -m app <cmd>` 均可；`app/__main__.py` 自举了包根路径。
- 配置 `~/.leetcode-daily/config.json`；测试/开发可用环境变量 `LEETCODE_DAILY_HOME` 重定向配置目录。

## 与方案 §2.2 的偏差

- `app/` 暂放 workspace 级（方案放在仓库内）；阶段 4 打包 exe 时再决定是否迁入。
- .gitignore 已排除 `.obsidian/`、`dashboard/stats.json`、`dashboard/fetch-cache.json`、`debug_*.py`。
