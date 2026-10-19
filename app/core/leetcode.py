"""力扣 CN 元数据抓取（方案 §3.3）。

版权红线：只抓「事实/元数据」——标题、难度、标签、URL；**不查询 content 字段，不保存题面原文**。
- 优先：`POST https://leetcode.cn/graphql/` 的 questionData 查询
- 降级：接口失败时返回 None，由上层走「手动填元数据」流程，不阻塞建题
- 缓存：dashboard/fetch-cache.json，避免重复请求
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

GRAPHQL_URL = "https://leetcode.cn/graphql/"
URL_RE = re.compile(r"leetcode\.cn/problems/([a-z0-9-]+)")
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "leetcode-daily/0.1 (personal study tool)",
    "Referer": "https://leetcode.cn/",
}

DIFFICULTY_CN = {"Easy": "简单", "Medium": "中等", "Hard": "困难"}

QUERY = """query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId
    questionFrontendId
    title
    translatedTitle
    difficulty
    topicTags { name translatedName }
  }
}"""

_CACHE_NAME = "fetch-cache.json"


@dataclass
class ProblemMeta:
    """只含元数据，绝不含题面原文。"""
    id: str            # 前端题号，如 "1"（scaffold 负责补零）
    title: str
    slug: str
    url: str
    difficulty: str    # 简单/中等/困难（CN 站返回中文）
    tags: list[str] = field(default_factory=list)

    @property
    def id_title(self) -> str:
        pad = self.id.zfill(4) if self.id.isdigit() else self.id
        return f"{pad}. {self.title}" if self.title else pad


def extract_slug(query: str) -> str | None:
    """从 URL 或裸 slug 提取题目 slug。"""
    query = query.strip()
    m = URL_RE.search(query)
    if m:
        return m.group(1)
    if re.fullmatch(r"[a-z0-9-]+", query):
        return query
    parsed = urlparse(query)
    m = URL_RE.search(parsed.path or "")
    return m.group(1) if m else None


def _cache_file(vault: Path) -> Path:
    return vault / "dashboard" / _CACHE_NAME


def _load_cache(vault: Path) -> dict[str, Any]:
    path = _cache_file(vault)
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(vault: Path, cache: dict[str, Any]) -> None:
    path = _cache_file(vault)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_meta(slug: str, vault: Path, *, use_cache: bool = True, timeout: float = 10.0) -> ProblemMeta | None:
    """抓取元数据；失败/离线返回 None（上层降级为手动填写）。"""
    cache = _load_cache(vault)
    if use_cache and slug in cache:
        c = cache[slug]
        try:
            return ProblemMeta(
                id=str(c["id"]), title=str(c["title"]), slug=slug,
                url=str(c.get("url") or f"https://leetcode.cn/problems/{slug}/"),
                difficulty=str(c.get("difficulty", "")),
                tags=[str(t) for t in c.get("tags", [])],
            )
        except KeyError:
            pass  # 缓存损坏则重新抓取

    meta = _fetch_remote(slug, timeout=timeout)
    if meta is not None:
        cache[slug] = {
            "id": meta.id, "title": meta.title, "url": meta.url,
            "difficulty": meta.difficulty, "tags": meta.tags,
        }
        _save_cache(vault, cache)
    return meta


def _fetch_remote(slug: str, *, timeout: float) -> ProblemMeta | None:
    try:
        import httpx  # 优先 httpx（方案 §4.1）
    except ImportError:
        try:
            import requests  # 降级 requests
        except ImportError:
            return None
        return _fetch_remote_requests(slug, timeout=timeout)

    try:
        resp = httpx.post(
            GRAPHQL_URL,
            json={"query": QUERY, "variables": {"titleSlug": slug}},
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception:  # noqa: BLE001 —— 网络/解析任何异常都走降级
        return None
    return _parse_payload(payload, slug)


def _fetch_remote_requests(slug: str, *, timeout: float) -> ProblemMeta | None:
    import requests
    try:
        resp = requests.post(
            GRAPHQL_URL,
            json={"query": QUERY, "variables": {"titleSlug": slug}},
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception:  # noqa: BLE001
        return None
    return _parse_payload(payload, slug)


def _parse_payload(payload: dict[str, Any], slug: str) -> ProblemMeta | None:
    question = ((payload or {}).get("data") or {}).get("question")
    if not question or not question.get("title"):
        return None
    tags = [
        t.get("translatedName") or t.get("name")
        for t in question.get("topicTags") or []
        if t.get("translatedName") or t.get("name")
    ]
    difficulty = str(question.get("difficulty") or "")
    return ProblemMeta(
        id=str(question.get("questionFrontendId") or question.get("questionId") or "0"),
        # 优先中文标题（translatedTitle），英文标题兜底
        title=str(question.get("translatedTitle") or question["title"]),
        slug=slug,
        # QuestionNode 无 url 字段（已验证），按 slug 规则拼接
        url=f"https://leetcode.cn/problems/{slug}/",
        difficulty=DIFFICULTY_CN.get(difficulty, difficulty),
        tags=tags,
    )
