import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .db import (
    get_conn,
    init_db,
    row_to_checklist,
    row_to_link,
    row_to_memo,
    row_to_operation,
    row_to_snippet,
    row_to_tool,
)
from .seed import seed_if_empty, seed_tools_if_empty
from . import github_top10 as gh_top10
from . import runner as automation_runner

STATIC = Path(__file__).resolve().parent / "static"


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> int:
    return int(time.time() * 1000)


# ---------- Pydantic models ----------

class MemoIn(BaseModel):
    title: str
    content: str = ""
    category: str = "general"
    color: str = "yellow"
    projectId: Optional[int] = None
    pinned: bool = False


class MemoUpdate(MemoIn):
    pass


class LinkIn(BaseModel):
    name: str
    url: str
    icon: str = "🔗"
    projectId: Optional[int] = None
    sortOrder: int = 0


class ChecklistIn(BaseModel):
    text: str
    sortOrder: int = 0


class ChecklistUpdate(BaseModel):
    text: Optional[str] = None
    completed: Optional[bool] = None
    completedAt: Optional[int] = None
    sortOrder: Optional[int] = None


class OperationIn(BaseModel):
    title: str
    description: str = ""
    steps: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    projectId: Optional[int] = None


class SnippetIn(BaseModel):
    title: str
    language: str = "sql"
    code: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    projectId: Optional[int] = None


class SettingsIn(BaseModel):
    theme: str = "light"


class ToolIn(BaseModel):
    name: str
    url: str
    icon: str = "🛠️"
    description: str = ""
    category: str = "utility"
    sortOrder: int = 0


class HealthCheckItem(BaseModel):
    id: int
    url: str


class HealthCheckRequest(BaseModel):
    items: list[HealthCheckItem] = Field(default_factory=list)


class AutomationRunConfig(BaseModel):
    headed: bool = False
    browser: str = "chromium"
    viewportWidth: int = Field(default=1280, ge=320, le=3840)
    viewportHeight: int = Field(default=720, ge=240, le=2160)
    slowMo: int = Field(default=0, ge=0, le=5000)
    timeout: int = Field(default=30000, ge=1000, le=120000)
    device: str = ""
    video: str = "off"
    tracing: str = "off"
    locale: str = "en-US"


class AutomationRunRequest(BaseModel):
    suite: str = "cafepress"
    config: AutomationRunConfig = Field(default_factory=AutomationRunConfig)
    tests: list[str] = Field(default_factory=list)


HEALTH_CHECK_TIMEOUT = 10.0
HEALTH_USER_AGENT = "QA-Home-HealthCheck/1.0"


# ---------- App ----------

app = FastAPI(title="QA Home API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    seed_if_empty()
    seed_tools_if_empty()


# ---------- Settings ----------

@app.get("/api/settings")
def get_settings() -> dict[str, Any]:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    result: dict[str, Any] = {"theme": "light"}
    for row in rows:
        result[row["key"]] = json.loads(row["value"])
    return result


@app.put("/api/settings")
def update_settings(body: SettingsIn) -> dict[str, Any]:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('theme', ?)",
            (json.dumps(body.theme),),
        )
        conn.commit()
    return {"theme": body.theme}


# ---------- Memos ----------

@app.get("/api/memos")
def list_memos() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM memos ORDER BY updated_at DESC").fetchall()
    return [row_to_memo(r) for r in rows]


@app.post("/api/memos", status_code=201)
def create_memo(body: MemoIn) -> dict:
    memo_id = _uid()
    ts = _now()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO memos (id, title, content, category, color, project_id, pinned, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (memo_id, body.title, body.content, body.category, body.color,
             body.projectId, int(body.pinned), ts, ts),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM memos WHERE id = ?", (memo_id,)).fetchone()
    return row_to_memo(row)


@app.put("/api/memos/{memo_id}")
def update_memo(memo_id: str, body: MemoUpdate) -> dict:
    ts = _now()
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM memos WHERE id = ?", (memo_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Memo not found")
        conn.execute(
            """UPDATE memos SET title=?, content=?, category=?, color=?, project_id=?, pinned=?, updated_at=?
               WHERE id=?""",
            (body.title, body.content, body.category, body.color,
             body.projectId, int(body.pinned), ts, memo_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM memos WHERE id = ?", (memo_id,)).fetchone()
    return row_to_memo(row)


@app.delete("/api/memos/{memo_id}")
def delete_memo(memo_id: str) -> dict:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM memos WHERE id = ?", (memo_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Memo not found")
    return {"ok": True}


# ---------- Quick Links ----------

@app.get("/api/links")
def list_links() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM quick_links ORDER BY sort_order").fetchall()
    return [row_to_link(r) for r in rows]


@app.post("/api/links", status_code=201)
def create_link(body: LinkIn) -> dict:
    link_id = _uid()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO quick_links (id, name, url, icon, project_id, sort_order) VALUES (?,?,?,?,?,?)",
            (link_id, body.name, body.url, body.icon, body.projectId, body.sortOrder),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM quick_links WHERE id = ?", (link_id,)).fetchone()
    return row_to_link(row)


@app.put("/api/links/{link_id}")
def update_link(link_id: str, body: LinkIn) -> dict:
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM quick_links WHERE id = ?", (link_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Link not found")
        conn.execute(
            "UPDATE quick_links SET name=?, url=?, icon=?, project_id=?, sort_order=? WHERE id=?",
            (body.name, body.url, body.icon, body.projectId, body.sortOrder, link_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM quick_links WHERE id = ?", (link_id,)).fetchone()
    return row_to_link(row)


@app.delete("/api/links/{link_id}")
def delete_link(link_id: str) -> dict:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM quick_links WHERE id = ?", (link_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Link not found")
    return {"ok": True}


# ---------- Checklist ----------

@app.get("/api/checklist")
def list_checklist() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM checklist_items ORDER BY sort_order").fetchall()
    return [row_to_checklist(r) for r in rows]


@app.post("/api/checklist", status_code=201)
def create_checklist_item(body: ChecklistIn) -> dict:
    item_id = _uid()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO checklist_items (id, text, completed, completed_at, sort_order) VALUES (?,?,0,NULL,?)",
            (item_id, body.text, body.sortOrder),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM checklist_items WHERE id = ?", (item_id,)).fetchone()
    return row_to_checklist(row)


@app.put("/api/checklist/{item_id}")
def update_checklist_item(item_id: str, body: ChecklistUpdate) -> dict:
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM checklist_items WHERE id = ?", (item_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Checklist item not found")

        text = body.text if body.text is not None else existing["text"]
        completed = int(body.completed) if body.completed is not None else existing["completed"]
        completed_at = body.completedAt if body.completedAt is not None else existing["completed_at"]
        sort_order = body.sortOrder if body.sortOrder is not None else existing["sort_order"]

        conn.execute(
            "UPDATE checklist_items SET text=?, completed=?, completed_at=?, sort_order=? WHERE id=?",
            (text, completed, completed_at, sort_order, item_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM checklist_items WHERE id = ?", (item_id,)).fetchone()
    return row_to_checklist(row)


@app.delete("/api/checklist/{item_id}")
def delete_checklist_item(item_id: str) -> dict:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM checklist_items WHERE id = ?", (item_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Checklist item not found")
    return {"ok": True}


@app.post("/api/checklist/reset")
def reset_checklist() -> dict:
    with get_conn() as conn:
        conn.execute("UPDATE checklist_items SET completed=0, completed_at=NULL")
        conn.commit()
        rows = conn.execute("SELECT * FROM checklist_items ORDER BY sort_order").fetchall()
    return {"items": [row_to_checklist(r) for r in rows]}


# ---------- Operations ----------

@app.get("/api/operations")
def list_operations() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM operations ORDER BY title").fetchall()
    return [row_to_operation(r) for r in rows]


@app.post("/api/operations", status_code=201)
def create_operation(body: OperationIn) -> dict:
    op_id = _uid()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO operations (id, title, description, steps, tags, project_id) VALUES (?,?,?,?,?,?)",
            (op_id, body.title, body.description, json.dumps(body.steps), json.dumps(body.tags), body.projectId),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM operations WHERE id = ?", (op_id,)).fetchone()
    return row_to_operation(row)


@app.put("/api/operations/{op_id}")
def update_operation(op_id: str, body: OperationIn) -> dict:
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM operations WHERE id = ?", (op_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Operation not found")
        conn.execute(
            "UPDATE operations SET title=?, description=?, steps=?, tags=?, project_id=? WHERE id=?",
            (body.title, body.description, json.dumps(body.steps), json.dumps(body.tags), body.projectId, op_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM operations WHERE id = ?", (op_id,)).fetchone()
    return row_to_operation(row)


@app.delete("/api/operations/{op_id}")
def delete_operation(op_id: str) -> dict:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM operations WHERE id = ?", (op_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Operation not found")
    return {"ok": True}


# ---------- Snippets ----------

@app.get("/api/snippets")
def list_snippets() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM snippets ORDER BY title").fetchall()
    return [row_to_snippet(r) for r in rows]


@app.post("/api/snippets", status_code=201)
def create_snippet(body: SnippetIn) -> dict:
    snippet_id = _uid()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO snippets (id, title, language, code, description, tags, project_id) VALUES (?,?,?,?,?,?,?)",
            (snippet_id, body.title, body.language, body.code, body.description, json.dumps(body.tags), body.projectId),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM snippets WHERE id = ?", (snippet_id,)).fetchone()
    return row_to_snippet(row)


@app.put("/api/snippets/{snippet_id}")
def update_snippet(snippet_id: str, body: SnippetIn) -> dict:
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM snippets WHERE id = ?", (snippet_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Snippet not found")
        conn.execute(
            "UPDATE snippets SET title=?, language=?, code=?, description=?, tags=?, project_id=? WHERE id=?",
            (body.title, body.language, body.code, body.description, json.dumps(body.tags), body.projectId, snippet_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM snippets WHERE id = ?", (snippet_id,)).fetchone()
    return row_to_snippet(row)


@app.delete("/api/snippets/{snippet_id}")
def delete_snippet(snippet_id: str) -> dict:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM snippets WHERE id = ?", (snippet_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Snippet not found")
    return {"ok": True}


# ---------- Tools ----------

@app.get("/api/tools")
def list_tools() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM tools ORDER BY sort_order, name").fetchall()
    return [row_to_tool(r) for r in rows]


@app.post("/api/tools", status_code=201)
def create_tool(body: ToolIn) -> dict:
    tool_id = _uid()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO tools (id, name, url, icon, description, category, sort_order)
               VALUES (?,?,?,?,?,?,?)""",
            (tool_id, body.name, body.url, body.icon, body.description, body.category, body.sortOrder),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
    return row_to_tool(row)


@app.put("/api/tools/{tool_id}")
def update_tool(tool_id: str, body: ToolIn) -> dict:
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Tool not found")
        conn.execute(
            """UPDATE tools SET name=?, url=?, icon=?, description=?, category=?, sort_order=?
               WHERE id=?""",
            (body.name, body.url, body.icon, body.description, body.category, body.sortOrder, tool_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
    return row_to_tool(row)


@app.delete("/api/tools/{tool_id}")
def delete_tool(tool_id: str) -> dict:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Tool not found")
    return {"ok": True}


# ---------- Health Check ----------

async def _check_url_health(client: httpx.AsyncClient, item: HealthCheckItem) -> dict[str, Any]:
    started = time.time()
    try:
        resp = await client.get(item.url)
        latency_ms = int((time.time() - started) * 1000)
        healthy = resp.status_code < 400
        return {
            "id": item.id,
            "status": "healthy" if healthy else "unhealthy",
            "statusCode": resp.status_code,
            "latencyMs": latency_ms,
        }
    except Exception as exc:
        latency_ms = int((time.time() - started) * 1000)
        return {
            "id": item.id,
            "status": "unhealthy",
            "statusCode": None,
            "latencyMs": latency_ms,
            "error": str(exc)[:120],
        }


@app.post("/api/health-check")
async def health_check(body: HealthCheckRequest) -> dict[str, Any]:
    if not body.items:
        return {}
    if len(body.items) > 50:
        raise HTTPException(400, "Too many URLs to check")

    headers = {"User-Agent": HEALTH_USER_AGENT}
    async with httpx.AsyncClient(
        timeout=HEALTH_CHECK_TIMEOUT,
        follow_redirects=True,
        headers=headers,
    ) as client:
        results = await asyncio.gather(*[_check_url_health(client, item) for item in body.items])

    return {str(r["id"]): r for r in results}


# ---------- Project Stats ----------

@app.get("/api/projects/stats")
def project_stats() -> dict[str, dict[str, int]]:
    """按 project_id 统计各项目的备忘录、流程、片段数量（不含通用/跨项目）"""
    stats: dict[int, dict[str, int]] = {}
    queries = [
        ("memos", "memos"),
        ("operations", "ops"),
        ("snippets", "snippets"),
    ]
    with get_conn() as conn:
        for table, key in queries:
            rows = conn.execute(
                f"SELECT project_id, COUNT(*) AS cnt FROM {table} "
                "WHERE project_id IS NOT NULL GROUP BY project_id"
            ).fetchall()
            for row in rows:
                pid = row["project_id"]
                if pid not in stats:
                    stats[pid] = {"memos": 0, "ops": 0, "snippets": 0}
                stats[pid][key] = row["cnt"]
    return {str(k): v for k, v in stats.items()}


# ---------- GitHub Top10 ----------

@app.get("/api/github-top10")
def get_github_top10(
    period: str = Query("weekly", pattern="^(weekly|monthly)$"),
    refresh: bool = False,
) -> dict[str, Any]:
    try:
        return gh_top10.get_trending(period, force_refresh=refresh)  # type: ignore[arg-type]
    except Exception as exc:
        raise HTTPException(502, f"GitHub Top10 获取失败: {exc}") from exc


@app.post("/api/github-top10/refresh")
def refresh_github_top10(period: Optional[str] = None) -> dict[str, Any]:
    try:
        if period in ("weekly", "monthly"):
            return gh_top10.refresh_period(period)  # type: ignore[arg-type]
        return gh_top10.refresh_all()
    except Exception as exc:
        raise HTTPException(502, f"GitHub Top10 刷新失败: {exc}") from exc


@app.get("/api/cron/github-top10")
def cron_github_top10(request: Request) -> dict[str, Any]:
    secret = os.environ.get("CRON_SECRET", "").strip()
    if secret:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {secret}":
            raise HTTPException(403, "Forbidden")
    try:
        gh_top10.refresh_all()
        return {"ok": True, "refreshedAt": int(time.time() * 1000)}
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc


# ---------- UI Automation ----------

@app.get("/api/automation/status")
def automation_status() -> dict[str, Any]:
    return automation_runner.get_status()


@app.get("/api/automation/suites")
def automation_suites() -> list[dict[str, Any]]:
    return automation_runner.list_suites()


@app.get("/api/automation/suites/{suite_id}/cases")
def automation_suite_cases(suite_id: str) -> dict[str, Any]:
    try:
        return automation_runner.list_suite_cases(suite_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/automation/suites/{suite_id}/files/{file_path:path}")
def automation_test_file(suite_id: str, file_path: str) -> dict[str, Any]:
    try:
        return automation_runner.get_test_file(suite_id, file_path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(404, "文件不存在") from exc


@app.get("/api/automation/runs")
def automation_runs(limit: int = Query(50, ge=1, le=200)) -> list[dict[str, Any]]:
    return automation_runner.list_runs(limit=limit)


@app.get("/api/automation/runs/{run_id}")
def automation_run_detail(run_id: str) -> dict[str, Any]:
    data = automation_runner.get_run(run_id)
    if not data:
        raise HTTPException(404, "Run not found")
    return data


@app.get("/api/automation/runs/{run_id}/log")
def automation_run_log(run_id: str) -> dict[str, str]:
    log = automation_runner.get_run_log(run_id)
    if log is None:
        raise HTTPException(404, "Run not found")
    return {"log": log}


@app.get("/api/automation/runs/{run_id}/report")
def automation_run_report(run_id: str) -> FileResponse:
    path = automation_runner.get_report_path(run_id)
    if not path:
        raise HTTPException(404, "Report not found")
    return FileResponse(path, media_type="text/html")


@app.get("/api/automation/runs/{run_id}/screenshots/{filename}")
def automation_screenshot(run_id: str, filename: str) -> FileResponse:
    path = automation_runner.get_screenshot_path(run_id, filename)
    if not path:
        raise HTTPException(404, "Screenshot not found")
    return FileResponse(path, media_type="image/png")


@app.get("/api/automation/run-config")
def automation_run_config() -> dict[str, Any]:
    return automation_runner.get_default_run_config()


@app.post("/api/automation/run", status_code=202)
def automation_start_run(body: AutomationRunRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    if not automation_runner.can_run():
        raise HTTPException(503, automation_runner.get_status()["message"])
    if automation_runner.is_running():
        raise HTTPException(409, "已有测试任务在运行")
    run_config = body.config.model_dump()
    selected_tests = [t.strip() for t in body.tests if t and t.strip()]
    try:
        run = automation_runner.create_run(body.suite, run_config, selected_tests)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    background_tasks.add_task(
        automation_runner.execute_run,
        run["runId"],
        body.suite,
        run_config,
        selected_tests,
    )
    return run


# ---------- Static files ----------

def _static_file(base: Path, rel: str) -> Path:
    target = (base / rel).resolve()
    if not str(target).startswith(str(base.resolve())):
        raise HTTPException(404, "Not found")
    if not target.is_file():
        raise HTTPException(404, "Not found")
    return target


if (STATIC / "index.html").is_file():
    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(_static_file(STATIC, "index.html"))

    @app.get("/automation")
    def automation_page() -> FileResponse:
        return FileResponse(_static_file(STATIC, "automation.html"))

    @app.get("/assets/{path:path}")
    def serve_assets(path: str) -> FileResponse:
        return FileResponse(_static_file(STATIC / "assets", path))

    @app.get("/design/{path:path}")
    def serve_design(path: str) -> FileResponse:
        return FileResponse(_static_file(STATIC / "design", path))
