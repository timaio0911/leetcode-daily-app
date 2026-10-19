# LeetCode 刷题管理软件

Windows 桌面 GUI + GitHub 仓库 + Obsidian 知识库「三位一体」的 LeetCode 刷题管理系统。

- **本仓库**：软件源码（Python + PySide6），含测试、打包脚本与设计文档
- **学习记录仓库**：[timaio0911/leetcode-daily](https://github.com/timaio0911/leetcode-daily) —— 每天的刷题记录、笔记、打卡与统计（同时是 Obsidian vault）
- **核心设计**：GitHub 仓库 = Obsidian Vault = 软件数据目录，三者指向同一文件夹，无同步成本

> 版权红线：软件只抓取并保存「元数据 + 自述化总结 + 链接 + 自己的代码」，**绝不保存题面原文**。

## 功能

- **新建题目**：粘贴力扣 CN 链接/slug → 自动抓元数据（标题/难度/标签）→ 生成题目目录、`solution.py` 代码模板、`README.md` 笔记模板 → 更新当日 `daily.md` 打卡；离线/限流可手动填写降级
- **题目列表**：按日期分组的题目树，难度/标签/复盘状态筛选，笔记预览，一键跳转 IDEA / Obsidian / 文件夹
- **删除题目**：勾选历史记录批量删除（GUI 对话框 / 多选 + Delete 键 / CLI），自动重建打卡表与题号索引；安全红线——只允许删除 `problems/<date>/<NNNN-slug>/` 题目目录
- **二刷 / 复盘**：标记复盘（写 `reviewed` frontmatter + 生成复盘笔记）、新建二刷代码、错题本视图、按题号跨日期聚合索引
- **统计看板**：每日/每周趋势、难度分布、连续打卡（streak）、README 统计段落一键生成
- **一键提交 GitHub**：约定式提交信息 `<归档date>: add <id> <slug>`，提交 + push 一步完成
- **打包发布**：PyInstaller 双产物（无控制台一键启动 GUI + 控制台 CLI）

## 快速开始

~~~powershell
# 环境：Windows 11 · Python 3.13 · PySide6 · httpx · git

py app gui                                          # 启动桌面窗口
py app new "https://leetcode.cn/problems/two-sum/"  # 新建题目（抓元数据 → 建目录 → 打卡）
py app list                                         # 按日期列出题目
py app delete 1 two-sum                             # 删除题目记录（可多个，-y 跳过确认）
py app stats                                        # 统计（含 streak/趋势）
py app readme                                       # 生成/更新 README 统计段落
py app open 1 code                                  # IDEA 打开代码（note=Obsidian 笔记 / dir=文件夹）
py app review                                       # 错题本；`py app review 1` 标记复盘
py app byid                                         # 生成/更新题号聚合索引
py app status                                       # git 改动清单
py app commit -m "msg" --push                       # 一键提交学习记录仓库
~~~

桌面窗口三个标签页：`[今日]` `[题目列表]` `[统计]`，底部工具条含新建题目 / 删除题目 / 提交 GitHub。

## 配置

配置文件 `~/.leetcode-daily/config.json`（测试/开发可用环境变量 `LEETCODE_DAILY_HOME` 重定向）：

| 键 | 说明 |
|---|---|
| `vault_path` | 数据目录（= Obsidian vault = leetcode-daily 仓库），默认自动探测 |
| `idea_path` | `idea64.exe` 路径（一键打开代码用） |
| `obsidian_path` | 可选，Obsidian 路径 |
| `git_remote` | git 远程名，默认 `origin` |
| `daily_goal` | 每日目标题数 |
| `fetch_enabled` | 新建题目时是否抓取力扣元数据 |

## 测试

五套验收自测，全部自带沙箱（临时目录运行，不污染真实数据）：

~~~powershell
py tests/test_phase1.py    # 建题全链路 + frontmatter 边界 + 抓取降级
py tests/test_phase2.py    # gitops / 跳转 / 筛选 / 约定式提交信息
py tests/test_phase3.py    # 统计计算 + README 段落幂等
py tests/test_phase4.py    # 二刷/复盘 + 错题本 + 题号索引 + 打包资源
py tests/test_delete.py    # 删除功能（安全红线 + 联动重建）
~~~

## 打包

~~~powershell
py package.py    # 先跑全部测试 → 清 dist/build → PyInstaller 双产物
~~~

产物（`dist/` 每次只保留最新版，不进 git）：

| 产物 | 用途 |
|---|---|
| `dist\LeetCode刷题管理\LeetCode刷题管理.exe` | 一键启动 GUI（无控制台，双击即用，崩溃写 crash.log） |
| `dist\leetcode-app\leetcode-app.exe` | 控制台版（CLI + `gui` 子命令，调试用） |

## 仓库结构

~~~
app/
├── __main__.py          # CLI 入口（argparse 子命令）
├── config.py            # 配置读写
├── core/
│   ├── leetcode.py      # 力扣 CN 元数据抓取（GraphQL，只抓元数据）
│   ├── scaffold.py      # 建目录/模板渲染/daily.md 重建（幂等）
│   ├── vault.py         # frontmatter 解析、扫描、基础统计
│   ├── delete.py        # 删除题目记录（安全校验 + 联动重建）
│   ├── review.py        # 二刷/复盘标记、错题本、题号聚合索引
│   ├── gitops.py        # git status/add/commit/push、约定式提交
│   ├── launcher.py      # IDEA/Obsidian/文件夹跳转
│   ├── stats.py         # 统计计算 + README 统计段落生成
│   └── resources.py     # 打包资源路径（sys._MEIPASS 适配）
├── ui/
│   ├── main_window.py   # 主窗口：[今日][题目列表][统计] + 底部工具条
│   ├── problem_list.py  # 题目树（多选）+ 筛选
│   ├── dashboard.py     # 看板页
│   ├── charts.py        # QtCharts 图表（不可用时降级文本）
│   └── dialogs.py       # 新建题目 / 设置 / 删除选择框
tests/                   # 五套验收自测（沙箱运行）
leetcode-app.spec        # PyInstaller 打包脚本（双产物）
package.py               # 打包统一入口（自动测试 + 只留新版本）
launcher_gui.py          # 一键启动 GUI 入口（无控制台）
LeetCode刷题管理软件-方案.md / HANDOVER.md / DEV-NOTES.md  # 设计与交接文档
~~~

## 文档

- [LeetCode刷题管理软件-方案.md](LeetCode刷题管理软件-方案.md) —— 设计方案（需求/架构/路线图/版权策略）
- [DEV-NOTES.md](DEV-NOTES.md) —— 开发备忘（运行方式/实现要点/偏差）
- [HANDOVER.md](HANDOVER.md) —— 交接文档（进度/代码地图/踩坑备忘/后续规划）
