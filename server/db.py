import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Union

from .turso import TursoConnection, connect_turso, turso_enabled

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "qa.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memos (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    content    TEXT NOT NULL DEFAULT '',
    category   TEXT NOT NULL DEFAULT 'general',
    color      TEXT NOT NULL DEFAULT 'yellow',
    project_id INTEGER,
    pinned     INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS quick_links (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    url        TEXT NOT NULL,
    icon       TEXT NOT NULL DEFAULT '🔗',
    project_id INTEGER,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS checklist_items (
    id           TEXT PRIMARY KEY,
    text         TEXT NOT NULL,
    completed    INTEGER NOT NULL DEFAULT 0,
    completed_at INTEGER,
    sort_order   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS operations (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    steps       TEXT NOT NULL DEFAULT '[]',
    tags        TEXT NOT NULL DEFAULT '[]',
    project_id  INTEGER
);

CREATE TABLE IF NOT EXISTS snippets (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    language    TEXT NOT NULL DEFAULT 'sql',
    code        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    tags        TEXT NOT NULL DEFAULT '[]',
    project_id  INTEGER
);

CREATE TABLE IF NOT EXISTS tools (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    url         TEXT NOT NULL,
    icon        TEXT NOT NULL DEFAULT '🛠️',
    description TEXT NOT NULL DEFAULT '',
    category    TEXT NOT NULL DEFAULT 'utility',
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS github_top10 (
    period       TEXT NOT NULL,
    rank_num     INTEGER NOT NULL,
    full_name    TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    url          TEXT NOT NULL,
    language     TEXT DEFAULT '',
    stars        INTEGER NOT NULL DEFAULT 0,
    stars_delta  TEXT NOT NULL DEFAULT '',
    fetched_at   INTEGER NOT NULL,
    PRIMARY KEY (period, rank_num)
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS automation_runs (
    id           TEXT PRIMARY KEY,
    suite        TEXT NOT NULL,
    suite_name   TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'pending',
    total        INTEGER NOT NULL DEFAULT 0,
    passed       INTEGER NOT NULL DEFAULT 0,
    failed       INTEGER NOT NULL DEFAULT 0,
    skipped      INTEGER NOT NULL DEFAULT 0,
    duration_ms  INTEGER NOT NULL DEFAULT 0,
    started_at   INTEGER NOT NULL,
    finished_at  INTEGER,
    log_summary  TEXT NOT NULL DEFAULT '',
    log_text     TEXT NOT NULL DEFAULT '',
    report_path  TEXT NOT NULL DEFAULT '',
    config_json  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS automation_results (
    id            TEXT PRIMARY KEY,
    run_id        TEXT NOT NULL,
    test_name     TEXT NOT NULL,
    class_name    TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL,
    duration_ms   INTEGER NOT NULL DEFAULT 0,
    error_message TEXT NOT NULL DEFAULT '',
    screenshot    TEXT NOT NULL DEFAULT ''
);
"""


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ[key] = value


_load_dotenv()


def get_conn() -> Union[sqlite3.Connection, TursoConnection]:
    if turso_enabled():
        return connect_turso()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migrate_db(conn) -> None:
    rows = conn.execute("PRAGMA table_info(automation_runs)").fetchall()
    cols = {row[1] for row in rows}
    if "config_json" not in cols:
        conn.execute(
            "ALTER TABLE automation_runs ADD COLUMN config_json TEXT NOT NULL DEFAULT ''"
        )


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrate_db(conn)


def is_seeded() -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM meta WHERE key = 'seeded_v2'"
        ).fetchone()
        return row is not None


def mark_seeded() -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('seeded_v2', '1')"
        )
        conn.commit()


def row_to_memo(row: Any) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "category": row["category"],
        "color": row["color"],
        "projectId": row["project_id"],
        "pinned": bool(row["pinned"]),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def row_to_link(row: Any) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "url": row["url"],
        "icon": row["icon"],
        "projectId": row["project_id"],
        "sortOrder": row["sort_order"],
    }


def row_to_checklist(row: Any) -> dict:
    return {
        "id": row["id"],
        "text": row["text"],
        "completed": bool(row["completed"]),
        "completedAt": row["completed_at"],
        "sortOrder": row["sort_order"],
    }


def row_to_operation(row: Any) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "steps": json.loads(row["steps"]),
        "tags": json.loads(row["tags"]),
        "projectId": row["project_id"],
    }


def row_to_snippet(row: Any) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "language": row["language"],
        "code": row["code"],
        "description": row["description"],
        "tags": json.loads(row["tags"]),
        "projectId": row["project_id"],
    }


def row_to_tool(row: Any) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "url": row["url"],
        "icon": row["icon"],
        "description": row["description"],
        "category": row["category"],
        "sortOrder": row["sort_order"],
    }
