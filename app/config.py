"""配置读写。

配置文件位置（按优先级）：
1. 环境变量 `LEETCODE_DAILY_HOME` 指定的目录下的 config.json（测试/开发用）
2. `~/.leetcode-daily/config.json`（默认，方案 §4.2）
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_ENV = "LEETCODE_DAILY_HOME"
DEFAULT_CONFIG_DIR = Path.home() / ".leetcode-daily"
CONFIG_NAME = "config.json"


def default_vault_path() -> Path:
    """默认数据目录 = leetcode-daily/（= Obsidian vault）。

    优先 app/ 同级的 leetcode-daily/（阶段 4 迁入仓库后则是包内的上级目录）。
    """
    pkg_root = Path(__file__).resolve().parent.parent
    candidate = pkg_root / "leetcode-daily"
    return candidate if candidate.is_dir() else pkg_root


@dataclass
class AppConfig:
    vault_path: str = field(default_factory=lambda: str(default_vault_path()))
    idea_path: str = ""          # F4：idea64.exe 路径（阶段 2 使用）
    obsidian_path: str = ""      # F4：Obsidian URI / exe（阶段 2 使用）
    git_remote: str = "origin"
    daily_goal: int = 1          # 每日目标数
    fetch_enabled: bool = True   # 抓取开关（关闭则每次手动填元数据）

    @property
    def vault(self) -> Path:
        return Path(self.vault_path).expanduser().resolve()


def config_dir() -> Path:
    env = os.environ.get(CONFIG_ENV)
    return Path(env).expanduser() if env else DEFAULT_CONFIG_DIR


def config_file() -> Path:
    return config_dir() / CONFIG_NAME


def resolve_vault(cfg: AppConfig) -> Path:
    """校验数据目录（= Obsidian vault）可用；不可用时抛出带指引的错误。"""
    vault = cfg.vault
    if not (vault / "templates").is_dir():
        raise FileNotFoundError(
            f"数据目录不可用：{vault}\n"
            "请确认 leetcode-daily/ 仓库存在（含 templates/），"
            "或在配置 ~/.leetcode-daily/config.json 中修改 vault_path。"
        )
    return vault


def load_config() -> AppConfig:
    path = config_file()
    if not path.is_file():
        return AppConfig()
    try:
        # utf-8-sig：容忍记事本等工具保存的 BOM（有 BOM 时 json.loads 会静默失败）
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return AppConfig()
    cfg = AppConfig()
    for key in ("vault_path", "idea_path", "obsidian_path", "git_remote"):
        if isinstance(data.get(key), str):
            setattr(cfg, key, data[key])
    if isinstance(data.get("daily_goal"), int) and data["daily_goal"] > 0:
        cfg.daily_goal = data["daily_goal"]
    if isinstance(data.get("fetch_enabled"), bool):
        cfg.fetch_enabled = data["fetch_enabled"]
    return cfg


def save_config(cfg: AppConfig) -> Path:
    path = config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "vault_path": cfg.vault_path,
        "idea_path": cfg.idea_path,
        "obsidian_path": cfg.obsidian_path,
        "git_remote": cfg.git_remote,
        "daily_goal": cfg.daily_goal,
        "fetch_enabled": cfg.fetch_enabled,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
