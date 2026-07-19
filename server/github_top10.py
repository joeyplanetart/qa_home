"""GitHub Trending Top10 — 抓取 trending 页并缓存到数据库。"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import httpx

from .db import get_conn

Period = Literal["weekly", "monthly"]

TRENDING_URLS: dict[Period, str] = {
    "weekly": "https://github.com/trending?since=weekly",
    "monthly": "https://github.com/trending?since=monthly",
}

REFRESH_INTERVAL_SEC = 24 * 60 * 60  # 每天更新一次
USER_AGENT = "QA-Home-GitHubTop10/1.0"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _meta_key(period: Period) -> str:
    return f"github_top10_{period}_at"


def _get_last_fetched(period: Period) -> int | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM meta WHERE key = ?", (_meta_key(period),)
        ).fetchone()
    if not row:
        return None
    try:
        return int(row["value"])
    except (TypeError, ValueError):
        return None


def needs_refresh(period: Period) -> bool:
    last = _get_last_fetched(period)
    if last is None:
        return True
    return (time.time() * 1000 - last) > REFRESH_INTERVAL_SEC * 1000


def _parse_trending_html(html: str) -> list[dict[str, Any]]:
    """从 GitHub Trending 页面解析 Top 仓库。"""
    repos: list[dict[str, Any]] = []
    articles = re.split(r"<article\b", html)[1:11]  # 最多 10 条

    for chunk in articles:
        name_match = re.search(
            r'href="/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"[^>]*>\s*([^<]+?)\s*</a>',
            chunk,
        )
        if not name_match:
            continue
        full_name = name_match.group(1).strip()
        display = re.sub(r"\s+", " ", name_match.group(2)).strip()
        if " / " in display:
            full_name = display.replace(" / ", "/").replace(" ", "")

        desc_match = re.search(
            r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>([^<]+)</p>', chunk
        )
        description = desc_match.group(1).strip() if desc_match else ""

        lang_match = re.search(
            r'itemprop="programmingLanguage"[^>]*>([^<]+)<', chunk
        )
        language = lang_match.group(1).strip() if lang_match else ""

        stars_match = re.search(
            r'href="/[^"]+/stargazers"[^>]*>\s*([\d,]+)\s*</a>', chunk
        )
        stars = 0
        if stars_match:
            stars = int(stars_match.group(1).replace(",", ""))

        delta_match = re.search(
            r'class="[^"]*float-sm-right[^"]*"[^>]*>\s*([\d,]+)\s*stars?\s*(?:today|this week|this month)?',
            chunk,
            re.I,
        )
        stars_delta = delta_match.group(1).replace(",", "") + " stars" if delta_match else ""

        repos.append({
            "fullName": full_name,
            "description": description,
            "url": f"https://github.com/{full_name}",
            "language": language,
            "stars": stars,
            "starsDelta": stars_delta,
        })

    return repos[:10]


def _fetch_via_search_api(period: Period) -> list[dict[str, Any]]:
    """GitHub Search API 兜底（trending 页解析失败时）。"""
    days = 7 if period == "weekly" else 30
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    min_stars = 50 if period == "weekly" else 200
    q = f"created:>{since} stars:>{min_stars}"

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(timeout=20.0) as client:
        resp = client.get(
            "https://api.github.com/search/repositories",
            params={"q": q, "sort": "stars", "order": "desc", "per_page": 10},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    return [
        {
            "fullName": item["full_name"],
            "description": item.get("description") or "",
            "url": item["html_url"],
            "language": item.get("language") or "",
            "stars": item.get("stargazers_count", 0),
            "starsDelta": "",
        }
        for item in data.get("items", [])[:10]
    ]


def fetch_trending(period: Period) -> list[dict[str, Any]]:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html"}
    url = TRENDING_URLS[period]

    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            repos = _parse_trending_html(resp.text)
            if len(repos) >= 5:
                return repos
    except Exception:
        pass

    return _fetch_via_search_api(period)


def save_trending(period: Period, repos: list[dict[str, Any]]) -> None:
    fetched_at = _now_ms()
    with get_conn() as conn:
        conn.execute("DELETE FROM github_top10 WHERE period = ?", (period,))
        for i, repo in enumerate(repos[:10], start=1):
            conn.execute(
                """INSERT INTO github_top10
                   (period, rank_num, full_name, description, url, language, stars, stars_delta, fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    period,
                    i,
                    repo["fullName"],
                    repo.get("description", ""),
                    repo["url"],
                    repo.get("language", ""),
                    repo.get("stars", 0),
                    repo.get("starsDelta", ""),
                    fetched_at,
                ),
            )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (_meta_key(period), str(fetched_at)),
        )
        conn.commit()


def load_trending(period: Period) -> dict[str, Any]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT rank_num, full_name, description, url, language, stars, stars_delta, fetched_at
               FROM github_top10 WHERE period = ? ORDER BY rank_num""",
            (period,),
        ).fetchall()

    if not rows:
        return {"period": period, "items": [], "fetchedAt": None}

    return {
        "period": period,
        "fetchedAt": rows[0]["fetched_at"],
        "items": [
            {
                "rank": row["rank_num"],
                "fullName": row["full_name"],
                "description": row["description"],
                "url": row["url"],
                "language": row["language"],
                "stars": row["stars"],
                "starsDelta": row["stars_delta"],
            }
            for row in rows
        ],
    }


def refresh_period(period: Period) -> dict[str, Any]:
    repos = fetch_trending(period)
    if not repos:
        existing = load_trending(period)
        if existing["items"]:
            return existing
        raise RuntimeError(f"Failed to fetch GitHub trending for {period}")
    save_trending(period, repos)
    return load_trending(period)


def refresh_all() -> dict[str, Any]:
    weekly_repos = fetch_trending("weekly")
    monthly_repos = fetch_trending("monthly")
    if weekly_repos:
        save_trending("weekly", weekly_repos)
    if monthly_repos:
        save_trending("monthly", monthly_repos)
    return {
        "weekly": load_trending("weekly"),
        "monthly": load_trending("monthly"),
    }


def get_trending(period: Period, *, force_refresh: bool = False) -> dict[str, Any]:
    cached = load_trending(period)

    if force_refresh:
        return refresh_period(period)

    if not cached["items"]:
        return refresh_period(period)

    if needs_refresh(period):
        try:
            return refresh_period(period)
        except Exception:
            return cached

    return cached
