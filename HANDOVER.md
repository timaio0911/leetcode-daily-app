# LeetCode 刷题管理软件 —— 项目交接文档

> 交接日期：2026-10-14
> 对应方案：[LeetCode刷题管理软件-方案.md](LeetCode刷题管理软件-方案.md)（v2）
> 当前状态：**阶段 0–4 已完成并实测**；P1/P3 增强项按需
> 运行环境实测：Windows 11 · Python 3.13.9（Miniconda `py`）· PySide6 6.12 · httpx 0.28 · git 2.54 · PyInstaller 6.22

---

## 1. 项目概述

Windows 桌面 GUI 软件 + GitHub 仓库 + Obsidian vault 三位一体的 LeetCode 刷题管理系统：

- **软件**：建题脚手架（拉元数据/建目录/模板/打卡）+ 看板 + 一键跳转 + 一键提交
- **数据仓库** `leetcode-daily/`：按日期归档题目（代码 + 自述化笔记），同时是 Obsidian vault 和 GitHub Public 仓库
- **版权红线（已决策）**：只存「元数据 + 自述化总结 + 链接 + 自己的代码」，**绝不保存题面原文**

**核心设计（方案 §2.1）**：GitHub 仓库 = Obsidian Vault = 软件数据目录，三者指向同一文件夹，无同步成本。

---

## 2. 当前进度（截至 2026-10-14）

| 阶段 | 内容 | 状态 | 验证 |
|---|---|---|---|
| 0 地基 | `leetcode-daily/` 仓库结构、模板、.gitignore、README、git init | ✅ 完成 | 已提交 GitHub |
| 1 MVP | 新建题目全链路（抓元数据→建目录→模板→daily.md）+ CLI + 最简 GUI | ✅ 完成 | [tests/test_phase1.py](tests/test_phase1.py) 26 用例 |
| 2 完整 GUI | 详情预览、难度/标签筛选、跳转 IDEA/Obsidian/文件夹、一键提交、设置 | ✅ 完成 | [tests/test_phase2.py](tests/test_phase2.py) 18 用例 + GUI 提交链路烟测 |
| 3 看板 | 每日/每周趋势、难度分布、连续打卡、README 统计段落自动生成 | ✅ 完成 | [tests/test_phase3.py](tests/test_phase3.py) 18 用例 + 图表截图验证 |
| 4 增强 | 二刷/复盘标记、错题本视图、题号聚合索引、打包 exe | ✅ 完成 | [tests/test_phase4.py](tests/test_phase4.py) 23 用例 + exe 冒烟验证 |
| 新增 | **删除功能**：勾选删除历史题目记录（GUI 多选/对话框 + CLI），联动重建 daily.md/题号索引 | ✅ 完成 | [tests/test_delete.py](tests/test_delete.py) 28 用例 + GUI 离屏烟测 + CLI 沙箱实测 |

**GitHub 已打通**：<https://github.com/timaio0911/leetcode-daily>（Public，`master` 分支，含 4 次提交）。
**软件源码仓库**：<https://github.com/timaio0911/leetcode-daily-app>（`main` 分支；`workspace/leetcode/` 即其工作区，根目录 `.gitignore` 排除 `leetcode-daily/`、`dist/`、`build/`，两仓库互不嵌套）。
**真实数据**：`problems/2026-10-14/` 下已有 3 题（0001 两数之和 / 0003 无重复字符的最长子串 / 0042 接雨水），README 统计段落已生成。

### 近期遗留小项（非开发，一次性操作/体验修复）

1. **Obsidian vault 注册**：用户需在 Obsidian 里 "Open folder as vault" 打开 `leetcode-daily/`，否则「用 Obsidian 打开笔记」报 "Vault not found"。
2. **Obsidian URI 已修复但未复测**：`cmd /c start` 被 `&` 拆分的 bug 已改为 `os.startfile()`（见 §5），等用户注册 vault 后复测一次跳转。
3. ~~**应用源码开源（可选）**~~ ✅ 已落地（2026-10-15）：`app/` + `tests/` + 打包脚本 + 文档已独立成仓库 [timaio0911/leetcode-daily-app](https://github.com/timaio0911/leetcode-daily-app)；学习记录继续只在 [timaio0911/leetcode-daily](https://github.com/timaio0911/leetcode-daily)。

---

## 3. 仓库布局与代码地图

~~~
workspace/leetcode/
├── LeetCode刷题管理软件-方案.md    # 设计方案 v2（需求/架构/路线图/版权策略）
├── DEV-NOTES.md                  # 开发备忘（运行方式/实现要点/偏差）
├── HANDOVER.md                   # ★ 本交接文档
├── leetcode-app.spec             # PyInstaller 打包脚本（阶段 4：双产物）
├── launcher_gui.py               # 一键启动 GUI 入口（无控制台 exe，异常写 crash.log）
├── app/                          # 管理软件源码（方案 §4.2；暂在 workspace 级，见偏差）
│   ├── __main__.py               # CLI 入口（argparse 子命令，见 §4）
│   ├── config.py                 # 配置读写 ~/.leetcode-daily/config.json
│   ├── core/
│   │   ├── leetcode.py           # F1 力扣 CN 元数据抓取（GraphQL，只抓元数据）
│   │   ├── scaffold.py           # F1/F6 建目录/模板渲染/daily.md 重建
│   │   ├── vault.py              # frontmatter 子集解析、扫描、基础统计
│   │   ├── gitops.py             # F5 git status/add/commit/push、约定式提交信息
│   │   ├── launcher.py           # F4 IDEA/Obsidian/文件夹跳转
│   │   ├── stats.py              # F3 统计计算 + README 统计段落生成
│   │   ├── review.py             # 阶段 4：二刷/复盘标记、错题本、题号聚合索引
│   │   ├── delete.py             # 新增：删除题目记录（路径安全校验 + daily.md/索引联动重建）
│   │   └── resources.py          # 阶段 4：打包资源路径（sys._MEIPASS 适配）
│   └── ui/
│       ├── main_window.py        # 主窗口：[今日][题目列表][统计] + 底部工具条
│       ├── problem_list.py       # F2 题目树（多选）+ 难度/标签/复盘状态筛选
│       ├── dashboard.py          # F3 看板页（数字卡片 + 图表 + README 按钮）
│       ├── charts.py             # QtCharts 折线/柱状图（不可用时降级文本）
│       └── dialogs.py            # 新建题目 + 设置 + 删除题目选择框（F7/新增）
├── leetcode-daily/               # ★ 数据仓库（= Obsidian vault = GitHub 仓库）
│   ├── templates/{problem.md,daily.md,solution.py}
│   ├── problems/<date>/<NNNN-slug>/{solution.py,README.md,review-<date>.md,solution-2.py}
│   ├── problems/<date>/daily.md  # 当日打卡（表格由 frontmatter 重建，幂等）
│   ├── problems-by-id/INDEX.md   # 阶段 4：题号聚合索引（软件生成，幂等）
│   ├── dashboard/{stats.json,fetch-cache.json}  # 缓存（gitignore）
│   └── README.md                 # 含 LEETCODE-STATS 标记对统计段落
├── dist/
│   ├── LeetCode刷题管理/          # 阶段 4：一键启动 GUI exe（无控制台，双击即用）
│   └── leetcode-app/             # 阶段 4：控制台版 exe（CLI + gui，调试用）
└── tests/
    ├── test_phase1.py            # 建题全链路 + frontmatter 边界 + 抓取降级
    ├── test_phase2.py            # gitops/launcher/筛选/约定式提交信息
    ├── test_phase3.py            # 统计计算 + README 段落幂等
    ├── test_phase4.py            # 二刷/复盘 + 错题本 + 题号索引 + 打包资源
    └── test_delete.py            # 新增：删除功能（安全红线 + 联动重建）
~~~

### 与方案 §2.2 的偏差（已知、可接受）

- `app/` 放在 workspace 级而非 `leetcode-daily/` 仓库内（避免软件源码混入刷题记录仓库）；阶段 4 打包 exe 时再决定归属。
- `.gitignore` 排除：`.obsidian/`、`dashboard/*.json`、`debug_*.py`。

---

## 4. 运行方式（实测可用）

~~~powershell
cd E:\Agent\deepseek\workspace\leetcode

py app gui                    # 桌面窗口（三标签页 + 一键提交）
py app new "<力扣URL或slug>"   # 新建题目（抓元数据→建目录→打卡）
py app new "two-sum" --title 两数之和 --difficulty 简单   # 手动降级
py app list                   # 按日期列出题目
py app delete 1 two-sum       # 删除题目记录（可多个；-y/--yes 跳过确认）
py app stats                  # 统计（含 streak/趋势）
py app readme                 # 生成/更新 README 统计段落
py app open 1 code            # IDEA 打开代码（note=Obsidian 笔记 / dir=文件夹）
py app review                 # 列出错题本
py app review 1 --date 2026-10-15   # 标记复盘（写 reviewed + 生成 review-<date>.md）
py app byid                   # 生成/更新题号聚合索引 problems-by-id/INDEX.md
py app status                 # git 改动清单
py app commit -m "msg" --push # 一键提交
py tests/test_phase1.py       # 四套验收自测（沙箱运行，不污染真实 vault）
py tests/test_phase2.py
py tests/test_phase3.py
py tests/test_phase4.py
py tests/test_delete.py       # 新增：删除功能验收（沙箱运行，不污染真实 vault）
py package.py                      # 打包 exe → dist/（自动测试 + dist 只留本次新版本 + 清 build）
~~~

### 一键启动（打包 exe）

打包产出两个 exe（`py package.py`，内部调 `py -m PyInstaller --noconfirm leetcode-app.spec`）：

| 产物 | 用途 | 启动方式 |
|---|---|---|
| `dist\LeetCode刷题管理\LeetCode刷题管理.exe` | **一键启动 GUI**（无控制台窗口） | **双击即用** |
| `dist\leetcode-app\leetcode-app.exe` | 控制台版（CLI + `gui` 子命令，调试用） | 命令行 `leetcode-app.exe <cmd>` |

- 双击 `LeetCode刷题管理.exe` 直接进主窗口，无黑框闪退；启动崩溃会写 `crash.log`（exe 同目录）并弹窗提示，不留无痕闪退。
- 两个 exe 都是单目录（`_internal/` 含依赖和 `templates/`），移动时需整目录一起移动。
- 若用控制台版直接双击（不带参数），会因缺 `command` 参数打印用法后退出（exit 2）——这是设计行为，GUI 请用 `LeetCode刷题管理.exe`。
~~~

> `py app <cmd>`（目录形式调用）与 `py -m app <cmd>` 均可；`app/__main__.py` 自举包根路径。
> 配置文件：`~/.leetcode-daily/config.json`；开发/测试可用环境变量 `LEETCODE_DAILY_HOME` 重定向配置目录。

**配置项**（`app/config.py::AppConfig`）：`vault_path`（默认自动探测 leetcode-daily/）、`idea_path`、`obsidian_path`（可选）、`git_remote`（默认 origin）、`daily_goal`、`fetch_enabled`。

---

## 5. 实现要点备忘（踩过的坑，后续别重蹈）

1. **力扣 CN GraphQL**（`app/core/leetcode.py`，2026-10 实测）：
   - `QuestionNode` **没有 `url` 字段**（查询会 400）→ URL 按 slug 拼接；
   - 中文标题用 `translatedTitle`，中文标签用 `topicTags.translatedName`；难度 `Easy/Medium/Hard` 自行映射 `简单/中等/困难`；
   - 只查 `questionId/questionFrontendId/title/translatedTitle/difficulty/topicTags`，**绝不查 `content`**（版权红线）；
   - 失败/限流降级手动填写，不阻塞建题；缓存 `dashboard/fetch-cache.json`。
2. **daily.md 是「重建」不是「追加」**：`scaffold.update_daily()` 从当日各题 README 的 frontmatter 推导表格，重复调用幂等；用户手写「今日心得」在表格之外不受影响（`_preserve_notes` 保留标记行之后内容，见 §5-13），但**别手动改打卡表格行**。
3. **frontmatter 行内列表**：模板 `tags: [...]` 的方括号在模板里，scaffold 只填内容；含逗号/引号的标签序列化时加引号，解析器 `_split_inline_list` 按引号切分（round-trip 有测试覆盖）。
4. **git status 未跟踪目录要展开为文件**（`gitops._expand_untracked`）：否则新题目录整体报为 `problems/`，约定式提交信息 `<归档date>: add <id> <slug>` 生成不出来。
5. **约定式提交信息的日期用「归档日期」**（题目录所在日期）而非今天——补录旧题时提交历史与归档一致。
6. **Obsidian URI 不能走 `cmd /c start`**：`&file=` 会被 cmd 当命令连接符拆分（曾产生 `'file' is not recognized` 噪音）。已改为 `os.startfile()`（ShellExecute）。
7. **QtCharts 折线图单点不可见**：必须 `series.setPointsVisible(True)`，否则只有一天数据时图表空白（截图验证发现）。
8. **Windows GBK 控制台**：所有入口 `sys.stdout.reconfigure(encoding="utf-8")`，否则 ✅/中文打印崩溃。
9. **Qt 文本缩进坑**：`QMessageBox.information(...)` 在 `if` 单行内调用时曾被意外缩进进分支内——写 GUI 事件处理时注意别把副作用语句塞进返回值表达式。
10. **PyInstaller 6.x onedir 的 datas 落在 `_internal/`**（`sys._MEIPASS` 指向它，不是 exe 所在目录）；`app/core/resources.py::bundle_dir()` 已处理该差异并回退 `exe_dir/_internal`。打包后实测 `dist/leetcode-app/leetcode-app.exe new ...` 命中内置模板 ✅。
11. **`reviewed` frontmatter 写回不破坏其余字段**：`review.save_reviewed` 重建 frontmatter 时保持原 key 顺序、只替换/追加 `reviewed`；round-trip 有测试覆盖（`test_phase4.py`）。
12. **删除功能的安全红线**（`app/core/delete.py`）：只允许删 `problems/<date>/<NNNN-slug>/` 且先做路径校验（目录必须在 `problems/` 下、日期/目录名符合约定），其余一律 `DeleteError` 拒绝；删除即真删，误删靠 git 历史找回。新增任何删除入口都必须走 `delete_problems()`，不要直接 `shutil.rmtree`。
13. **daily.md 重建曾整文件覆盖**：`update_daily` 从模板重写全文，会把用户手写的「今日心得」抹掉（§5-2 声称不受影响但旧实现并非如此）。已加 `scaffold._preserve_notes` 保留 `**今日心得**` 标记行之后的内容——改重建逻辑时别破坏这一点。
14. **测试/脚本重定向 vault 的正确姿势**：`LEETCODE_DAILY_HOME` 指向临时目录 + 其下 `config.json` 写 `vault_path`；**执行任何写/删操作前必须先断言 `load_config()` 确实指向沙箱**。曾因 config.json 带 BOM 导致 `json.loads` 失败静默回退默认 vault（真实数据目录），误删过真实题目（已用 git 恢复）。`config.py` 现用 `utf-8-sig` 容忍 BOM；写 config 文件仍应无 BOM、JSON 反斜杠只转义一次。

---

## 6. 后续所需开发（按优先级建议）

### P1 用户体验修复（短）

- [ ] **Obsidian 跳转友好化**：检测 `%APPDATA%\obsidian\obsidian.json` 的 vault 注册表；未注册时弹指引（"请先 Open folder as vault"）而非让用户看 Obsidian 的英文报错。
- [ ] **GUI 内编辑元数据**：右键题目改 `status`（todo/doing/done/review）/`time_spent`，写回 frontmatter 并刷新 daily.md（现在只能去 Obsidian 手改 frontmatter）。
- [ ] **新建题目进度反馈**：抓取时已经有等待光标，可加 QProgressDialog + 超时提示。

### P2 阶段 4 增强（方案 §5）——已全部完成

- [x] **二刷/复盘标记与筛选、错题本视图**：frontmatter `reviewed: []` 字段已接入（`app/core/review.py`），题目录下追加 `solution-2.py`、`review-<date>.md`；GUI 筛选栏新增「错题本 / 已复盘」，详情区新增「标记复盘 ✓」「新建二刷代码」按钮。
- [x] **按题号索引视图（跨日期聚合）**：`problems-by-id/INDEX.md` 软件生成索引（不复制文件，幂等重建）；CLI `py app byid`。
- [x] **打包 exe**：PyInstaller 单目录（`leetcode-app.spec`），`templates/` 随包分发，`app/core/resources.py` 适配 `sys._MEIPASS`（PyInstaller 6.x `_internal/`）。产物：`dist/leetcode-app/leetcode-app.exe`。
- [ ] **GitHub Actions 定时刷新 README 统计**（可选，方案 §5 阶段 3 提及）：定期跑 `py app readme` 并 commit。

### P3 架构演进（按需）

- [ ] `app/` 源码开源仓库（`leetcode-daily-app`）+ 独立 README/许可证。
- [ ] 统计数据缓存 `dashboard/stats.json` 落盘（目前每次实时扫描，量级小无感知）。
- [ ] 多端：手机端按方案约定走 GitHub 网页/Obsidian 同步，不做 App（方案 §1.3 非目标）。

---

## 7. 测试与质量约定

- **测试运行方式**：`py tests/test_phaseN.py`，脚本自带沙箱（临时 home + 临时 vault/仓库），**不污染真实数据**。
- **测试即验收标准**：每个测试文件头部注释对应方案路线图的验收目标（阶段 1「点一次按钮得到完整题目文件夹 + 当日打卡更新」等）。
- **GUI 验证方式**：临时 `debug_gui*.py` 烟测脚本 + 截图（已随验证删除，`.gitignore` 排除 `debug_*.py`）；改 GUI 后建议重现一次关键路径（新建题、提交、看板）。
- **回归要求**：改 `core/` 任何模块后跑全部三套测试；改 `gitops.py` 额外手测一次真实仓库 commit+push。

---

## 8. 风险与开放问题（继承方案 §6 + 新增）

1. **力扣接口稳定性**：GraphQL 无官方保障；降级路径（手动填写）已实现，若接口字段再变（如 `translatedTitle` 下线）按 §5-1 的探测方式更新查询。
2. **git 凭据**：push 依赖本机 GitHub 凭据（Credential Manager/SSH）；软件不做凭据管理（方案 §6.2）。
3. **版权红线**：实现层硬约束（`ProblemMeta` 无题面字段、README 只有元数据+链接+自述引导）；测试有断言保护，**任何后续开发不得引入题面原文抓取**。
4. **Obsidian vault 名约定**：URI 按文件夹名定位 vault，`leetcode-daily/` 目录名不能随意改（与 GitHub 仓库名一致）。
5. **`daily.md` 手改表格会被覆盖**：属设计约定（表格从元数据推导），文档已注明；若用户反馈不爽，可改为「只追加新行、不重建」。
6. **日期归档假设**：所有扫描/统计按 `problems/<YYYY-MM-DD>/` 目录约定，破坏该约定会导致统计缺失。

---

## 9. 交接检查清单（接手人 10 分钟上手）

1. 读 [LeetCode刷题管理软件-方案.md](LeetCode刷题管理软件-方案.md) §1–5（需求/结构/功能/架构/路线图）；
2. 读 [DEV-NOTES.md](DEV-NOTES.md)（运行方式速查）与本文 §5（踩坑备忘）；
3. 跑三套测试确认环境正常：`py tests/test_phase1.py` … `test_phase3.py`；
4. 跑 `py app gui` 走一遍动线：新建题目 → 跳转 → 提交 GitHub；
5. 需求/范围问题回方案 v2，实现细节问题先查 §5，再看对应模块 docstring（每个模块顶部都有职责说明）。
