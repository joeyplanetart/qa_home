"""UI 自动化测试执行器"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

from .db import get_conn

ROOT = Path(__file__).resolve().parent.parent
AUTOMATION_DIR = ROOT / "automation"
SUITES_DIR = AUTOMATION_DIR / "suites"
REPORTS_DIR = ROOT / "reports"

SUITE_LABELS = {
    "cafepress": "CafePress 冒烟",
    "sti": "STI 冒烟",
}

DEFAULT_RUN_CONFIG: dict[str, Any] = {
    "headed": False,
    "browser": "chromium",
    "viewportWidth": 1280,
    "viewportHeight": 720,
    "slowMo": 0,
    "timeout": 30000,
    "device": "",
    "video": "off",
    "tracing": "off",
    "locale": "en-US",
}

VALID_BROWSERS = {"chromium", "firefox", "webkit"}
VALID_CAPTURE_MODES = {"off", "on", "retain-on-failure"}

_running: Optional[str] = None
MAX_LOG_CHARS = 120_000


def get_default_run_config() -> dict[str, Any]:
    return dict(DEFAULT_RUN_CONFIG)


def normalize_run_config(config: Optional[dict[str, Any]]) -> dict[str, Any]:
    merged = dict(DEFAULT_RUN_CONFIG)
    if not config:
        return merged

    if "headed" in config:
        merged["headed"] = bool(config["headed"])
    if "browser" in config and config["browser"] in VALID_BROWSERS:
        merged["browser"] = config["browser"]
    if "viewportWidth" in config:
        merged["viewportWidth"] = max(320, min(3840, int(config["viewportWidth"])))
    if "viewportHeight" in config:
        merged["viewportHeight"] = max(240, min(2160, int(config["viewportHeight"])))
    if "slowMo" in config:
        merged["slowMo"] = max(0, min(5000, int(config["slowMo"])))
    if "timeout" in config:
        merged["timeout"] = max(1000, min(120000, int(config["timeout"])))
    if "device" in config:
        merged["device"] = str(config["device"] or "").strip()
    if "video" in config and config["video"] in VALID_CAPTURE_MODES:
        merged["video"] = config["video"]
    if "tracing" in config and config["tracing"] in VALID_CAPTURE_MODES:
        merged["tracing"] = config["tracing"]
    if "locale" in config:
        merged["locale"] = str(config["locale"] or "en-US").strip() or "en-US"
    return merged


def _parse_run_config(row: Any) -> dict[str, Any]:
    raw = ""
    try:
        raw = row["config_json"] or ""
    except (KeyError, IndexError, TypeError):
        pass
    if not raw:
        return dict(DEFAULT_RUN_CONFIG)
    try:
        data = json.loads(raw)
        parsed = normalize_run_config(data)
        if isinstance(data.get("selectedTests"), list):
            parsed["selectedTests"] = data["selectedTests"]
        return parsed
    except (json.JSONDecodeError, TypeError, ValueError):
        return dict(DEFAULT_RUN_CONFIG)


def _apply_run_config(cmd: list[str], env: dict[str, str], config: dict[str, Any]) -> None:
    cmd.extend(["--browser", config["browser"]])

    if config["headed"]:
        cmd.append("--headed")

    if config["slowMo"] > 0:
        cmd.extend(["--slowmo", str(config["slowMo"])])

    if config["device"]:
        cmd.extend(["--device", config["device"]])
    else:
        env["AUTOMATION_VIEWPORT_WIDTH"] = str(config["viewportWidth"])
        env["AUTOMATION_VIEWPORT_HEIGHT"] = str(config["viewportHeight"])

    if config["video"] != "off":
        cmd.extend(["--video", config["video"]])

    if config["tracing"] != "off":
        cmd.extend(["--tracing", config["tracing"]])

    env["AUTOMATION_TIMEOUT"] = str(config["timeout"])
    if config["locale"]:
        env["AUTOMATION_LOCALE"] = config["locale"]
MAX_LOG_CHARS = 120_000


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> int:
    return int(time.time() * 1000)


def is_vercel() -> bool:
    return os.environ.get("VERCEL") == "1"


def can_run() -> bool:
    return not is_vercel() and SUITES_DIR.is_dir()


def is_running() -> bool:
    return _running is not None


def check_playwright_browsers() -> tuple[bool, str]:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
        return True, ""
    except Exception as exc:
        msg = str(exc)
        if "Executable doesn't exist" in msg or "browserType.launch" in msg:
            return False, (
                "Playwright 浏览器未安装。请在项目根目录运行: "
                "./scripts/install-playwright.sh"
            )
        return False, f"Playwright 不可用: {msg[:200]}"


def install_playwright_browsers() -> bool:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
        return proc.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def ensure_playwright_browsers() -> None:
    ready, message = check_playwright_browsers()
    if ready:
        return
    if install_playwright_browsers():
        ready, message = check_playwright_browsers()
        if ready:
            return
    raise RuntimeError(message)


def get_status() -> dict[str, Any]:
    if is_vercel():
        return {
            "canRun": False,
            "running": False,
            "currentRunId": _running,
            "needsBrowserInstall": False,
            "message": "Vercel 线上环境不支持执行 UI 自动化，请在本地运行 ./scripts/run.sh",
        }
    if not SUITES_DIR.is_dir():
        return {
            "canRun": False,
            "running": False,
            "currentRunId": _running,
            "needsBrowserInstall": False,
            "message": "未找到 automation/suites 目录",
        }
    browser_ready, browser_msg = check_playwright_browsers()
    if not browser_ready:
        return {
            "canRun": False,
            "running": is_running(),
            "currentRunId": _running,
            "needsBrowserInstall": True,
            "message": browser_msg,
        }
    return {
        "canRun": True,
        "running": is_running(),
        "currentRunId": _running,
        "needsBrowserInstall": False,
        "message": "就绪" if not is_running() else "测试运行中…",
    }


def _load_suite_meta(suite_id: str) -> dict[str, Any]:
    meta_path = SUITES_DIR / suite_id / "meta.json"
    meta: dict[str, Any] = {
        "id": suite_id,
        "name": SUITE_LABELS.get(suite_id, suite_id.upper()),
        "description": "",
        "projectId": None,
    }
    if meta_path.is_file():
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            meta.update({k: v for k, v in data.items() if k in ("name", "description", "projectId")})
        except (json.JSONDecodeError, OSError):
            pass
    return meta


def _count_test_functions(suite_path: Path) -> int:
    count = 0
    if not suite_path.is_dir():
        return 0
    for file_path in suite_path.glob("**/test_*.py"):
        try:
            text = file_path.read_text(encoding="utf-8")
        except OSError:
            continue
        count += len(re.findall(r"^\s*def test_", text, re.MULTILINE))
    return count


def get_project_test_counts() -> dict[int, int]:
    """按 meta.json 中的 projectId 汇总各项目的自动化用例数。"""
    counts: dict[int, int] = {}
    if not SUITES_DIR.is_dir():
        return counts
    for entry in sorted(SUITES_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        meta = _load_suite_meta(entry.name)
        project_id = meta.get("projectId")
        if project_id is None:
            continue
        try:
            pid = int(project_id)
        except (TypeError, ValueError):
            continue
        counts[pid] = counts.get(pid, 0) + _count_test_functions(entry)
    return counts


def list_suites() -> list[dict[str, Any]]:
    if not SUITES_DIR.is_dir():
        return []
    suites: list[dict[str, Any]] = []
    for entry in sorted(SUITES_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        meta = _load_suite_meta(entry.name)
        suites.append({
            **meta,
            "id": entry.name,
            "testCount": _count_test_functions(entry),
        })
    return suites


def _resolve_suite_dir(suite_id: str) -> Path:
    if suite_id == "all":
        raise ValueError("不能浏览「全部套件」的用例，请选择具体套件")
    path = (SUITES_DIR / suite_id).resolve()
    if not str(path).startswith(str(SUITES_DIR.resolve())) or not path.is_dir():
        raise ValueError(f"未知测试套件: {suite_id}")
    return path


def _resolve_suite_file(suite_id: str, rel_path: str) -> Path:
    suite_dir = _resolve_suite_dir(suite_id)
    target = (suite_dir / rel_path).resolve()
    if not str(target).startswith(str(suite_dir)):
        raise ValueError("非法文件路径")
    if not target.is_file() or target.suffix != ".py":
        raise ValueError("仅支持读取 .py 测试文件")
    return target


def _parse_module_doc(text: str) -> str:
    match = re.match(r'^\s*"""(.*?)"""', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.match(r"^\s*'''(.*?)'''", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _parse_markers_above(lines: list[str], test_line_index: int) -> list[str]:
    markers: list[str] = []
    i = test_line_index - 1
    while i >= 0:
        line = lines[i].strip()
        if not line:
            i -= 1
            continue
        if line.startswith("@"):
            for match in re.finditer(r"@pytest\.mark\.(\w+)", line):
                markers.append(match.group(1))
            i -= 1
            continue
        break
    markers.reverse()
    return markers


def _parse_test_cases(text: str) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        match = re.match(r"^\s*def (test_\w+)\s*\(", line)
        if not match:
            continue
        name = match.group(1)
        doc = ""
        j = idx
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j < len(lines) and lines[j].strip().startswith(('"""', "'''")):
            quote = lines[j].strip()[:3]
            doc_lines: list[str] = []
            if lines[j].strip().count(quote) >= 2:
                doc = lines[j].strip()[3:-3].strip()
            else:
                doc_lines.append(lines[j].strip()[3:])
                j += 1
                while j < len(lines):
                    if quote in lines[j]:
                        doc_lines.append(lines[j].split(quote)[0].strip())
                        break
                    doc_lines.append(lines[j].strip())
                    j += 1
                doc = "\n".join(doc_lines).strip()
        markers = _parse_markers_above(lines, idx - 1)
        start_line = idx
        k = idx - 2
        while k >= 0:
            stripped = lines[k].strip()
            if not stripped:
                k -= 1
                continue
            if stripped.startswith("@"):
                start_line = k + 1
                k -= 1
                continue
            break
        cases.append({
            "name": name,
            "line": start_line,
            "defLine": idx,
            "doc": doc,
            "markers": markers,
            "selected": "selected" in markers,
        })
    return cases


def list_suite_cases(suite_id: str) -> dict[str, Any]:
    suite_dir = _resolve_suite_dir(suite_id)
    meta = _load_suite_meta(suite_id)
    files: list[dict[str, Any]] = []
    for file_path in sorted(suite_dir.glob("**/test_*.py")):
        rel = file_path.relative_to(suite_dir).as_posix()
        try:
            text = file_path.read_text(encoding="utf-8")
        except OSError:
            continue
        files.append({
            "path": rel,
            "name": file_path.name,
            "moduleDoc": _parse_module_doc(text),
            "cases": _parse_test_cases(text),
            "lineCount": len(text.splitlines()),
        })
    return {
        "suiteId": suite_id,
        "suiteName": meta.get("name", suite_id),
        "description": meta.get("description", ""),
        "files": files,
        "testCount": sum(len(f["cases"]) for f in files),
    }


def get_test_file(suite_id: str, rel_path: str) -> dict[str, Any]:
    target = _resolve_suite_file(suite_id, rel_path)
    text = target.read_text(encoding="utf-8")
    suite_dir = _resolve_suite_dir(suite_id)
    return {
        "suiteId": suite_id,
        "path": target.relative_to(suite_dir).as_posix(),
        "name": target.name,
        "content": text,
        "language": "python",
        "lineCount": len(text.splitlines()),
        "cases": _parse_test_cases(text),
        "moduleDoc": _parse_module_doc(text),
    }


def row_to_run(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "suite": row["suite"],
        "suiteName": row["suite_name"],
        "status": row["status"],
        "total": row["total"],
        "passed": row["passed"],
        "failed": row["failed"],
        "skipped": row["skipped"],
        "durationMs": row["duration_ms"],
        "startedAt": row["started_at"],
        "finishedAt": row["finished_at"],
        "logSummary": row["log_summary"],
        "hasReport": bool(row["report_path"]),
        "hasLog": bool(row["log_text"]),
        "config": _parse_run_config(row),
    }


def row_to_result(row: Any) -> dict[str, Any]:
    artifacts: dict[str, Any] = {}
    raw_artifacts = ""
    try:
        raw_artifacts = row["artifacts_json"] or ""
    except (KeyError, IndexError, TypeError):
        pass
    if raw_artifacts:
        try:
            parsed = json.loads(raw_artifacts)
            if isinstance(parsed, dict):
                artifacts = parsed
        except json.JSONDecodeError:
            pass
    return {
        "id": row["id"],
        "runId": row["run_id"],
        "testName": row["test_name"],
        "className": row["class_name"],
        "status": row["status"],
        "durationMs": row["duration_ms"],
        "errorMessage": row["error_message"],
        "screenshot": row["screenshot"],
        "artifacts": artifacts,
        "screenshots": [],
    }


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM automation_runs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [row_to_run(r) for r in rows]


def get_run(run_id: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM automation_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if not row:
            return None
        results = conn.execute(
            "SELECT * FROM automation_results WHERE run_id = ? ORDER BY test_name",
            (run_id,),
        ).fetchall()
    data = row_to_run(row)
    data["results"] = []
    for r in results:
        result = row_to_result(r)
        artifact_key = _artifact_key(r["class_name"] or "", r["test_name"])
        result["screenshots"] = _merge_test_screenshots(
            run_id,
            artifact_key,
            r["screenshot"] or "",
            result["artifacts"],
        )
        data["results"].append(result)
    _associate_orphan_screenshots(run_id, data["results"])
    return data


def get_run_log(run_id: str) -> Optional[str]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT log_text FROM automation_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if not row:
        return None
    return row["log_text"] or ""


def get_report_path(run_id: str) -> Optional[Path]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT report_path FROM automation_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if not row or not row["report_path"]:
        return None
    path = (REPORTS_DIR / row["report_path"]).resolve()
    if not str(path).startswith(str(REPORTS_DIR.resolve())):
        return None
    return path if path.is_file() else None


def _artifact_key(class_name: str, test_name: str) -> str:
    segments = class_name.split(".")
    if len(segments) >= 2:
        rel_path = "/".join(segments[:-1]) + "/" + segments[-1] + ".py"
    else:
        rel_path = f"{class_name}.py"
    return f"{rel_path}::{test_name}".replace("/", "_").replace("::", "_")


def _load_test_artifacts(artifacts_dir: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    if not artifacts_dir.is_dir():
        return index
    for path in artifacts_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict):
            index[path.stem] = data
    return index


def _merge_test_screenshots(
    run_id: str,
    artifact_key: str,
    failure_screenshot: str,
    artifacts: dict[str, Any],
) -> list[dict[str, str]]:
    screenshots_dir = REPORTS_DIR / run_id / "screenshots"
    seen: set[str] = set()
    merged: list[dict[str, str]] = []

    def add(file_name: str, label: str) -> None:
        if not file_name or file_name in seen:
            return
        if (screenshots_dir / file_name).is_file():
            seen.add(file_name)
            merged.append({"file": file_name, "label": label})

    for item in artifacts.get("screenshots") or []:
        if isinstance(item, dict):
            add(str(item.get("file") or ""), str(item.get("label") or item.get("file") or ""))

    for path in sorted(screenshots_dir.glob(f"{artifact_key}__*.png")):
        step = path.stem[len(artifact_key) + 2:]
        add(path.name, step.replace("_", " "))

    if failure_screenshot:
        add(failure_screenshot, "失败截图")

    return merged


def _associate_orphan_screenshots(run_id: str, results: list[dict[str, Any]]) -> None:
    """兼容未加 test id 前缀的步骤截图（如 cyo_designer_complete.png）。"""
    if len(results) != 1:
        return
    screenshots_dir = REPORTS_DIR / run_id / "screenshots"
    if not screenshots_dir.is_dir():
        return

    assigned = set()
    for result in results:
        for shot in result.get("screenshots") or []:
            assigned.add(shot.get("file", ""))
        if result.get("screenshot"):
            assigned.add(result["screenshot"])

    orphans = sorted(
        path.name
        for path in screenshots_dir.glob("*.png")
        if path.name not in assigned and "__" not in path.stem
    )
    if not orphans:
        return

    shots = list(results[0].get("screenshots") or [])
    for file_name in orphans:
        label = file_name.removesuffix(".png").replace("_", " ")
        shots.append({"file": file_name, "label": label})
    results[0]["screenshots"] = shots


def _resolve_suite_path(suite: str) -> Path:
    if suite == "all":
        return SUITES_DIR
    path = (SUITES_DIR / suite).resolve()
    if not str(path).startswith(str(SUITES_DIR.resolve())) or not path.is_dir():
        raise ValueError(f"未知测试套件: {suite}")
    return path


def _resolve_test_targets(suite: str, tests: list[str]) -> list[str]:
    if not tests:
        return []
    if suite == "all":
        raise ValueError("指定用例时请选择一个具体套件，不能选「全部」")

    suite_dir = _resolve_suite_path(suite)
    targets: list[str] = []
    seen: set[str] = set()

    for item in tests:
        item = item.strip()
        if not item:
            continue
        if "::" in item:
            rel_file, test_name = item.split("::", 1)
            test_name = test_name.strip()
            if not test_name.startswith("test_"):
                raise ValueError(f"无效用例名: {test_name}")
        else:
            rel_file = item
            test_name = None

        file_path = _resolve_suite_file(suite, rel_file.strip())
        if test_name:
            target = f"{file_path}::{test_name}"
        else:
            target = str(file_path)
        if target not in seen:
            seen.add(target)
            targets.append(target)

    if not targets:
        raise ValueError("未指定有效的测试用例")
    return targets


def create_run(
    suite: str,
    config: Optional[dict[str, Any]] = None,
    tests: Optional[list[str]] = None,
) -> dict[str, Any]:
    global _running
    if not can_run():
        raise RuntimeError("当前环境不可运行自动化测试")
    if is_running():
        raise RuntimeError("已有测试任务在运行，请稍后再试")

    selected_tests = [t.strip() for t in (tests or []) if t and t.strip()]
    if selected_tests:
        _resolve_test_targets(suite, selected_tests)

    run_config = normalize_run_config(config)
    _resolve_suite_path(suite)
    meta = _load_suite_meta(suite) if suite != "all" else {
        "name": "全部套件",
        "description": "运行 automation/suites 下所有用例",
    }
    run_id = _uid()
    started = _now()

    suite_display = meta.get("name", suite)
    if selected_tests:
        suite_display = f"{suite_display} · {len(selected_tests)} 个用例"

    stored_config = dict(run_config)
    if selected_tests:
        stored_config["selectedTests"] = selected_tests

    with get_conn() as conn:
        conn.execute(
            """INSERT INTO automation_runs
               (id, suite, suite_name, status, total, passed, failed, skipped,
                duration_ms, started_at, finished_at, log_summary, log_text, report_path, config_json)
               VALUES (?,?,?,?,0,0,0,0,0,?,NULL,'','','',?)""",
            (run_id, suite, suite_display, "running", started, json.dumps(stored_config)),
        )
        conn.commit()

    _running = run_id
    return {
        "runId": run_id,
        "status": "running",
        "suite": suite,
        "config": stored_config,
        "tests": selected_tests,
    }


def _parse_junit(junit_path: Path, screenshots_dir: Path) -> tuple[list[dict], dict]:
    tree = ET.parse(junit_path)
    root = tree.getroot()
    if root.tag == "testsuites":
        suites = root.findall("testsuite")
    else:
        suites = [root]

    results: list[dict] = []
    totals = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration_ms": 0}

    for suite_el in suites:
        for case in suite_el.findall("testcase"):
            name = case.get("name", "")
            classname = case.get("classname", "")
            duration_ms = int(float(case.get("time", "0")) * 1000)
            status = "passed"
            error_message = ""

            if case.find("failure") is not None:
                status = "failed"
                failure = case.find("failure")
                error_message = (failure.text or failure.get("message", "")).strip()
            elif case.find("error") is not None:
                status = "failed"
                err = case.find("error")
                error_message = (err.text or err.get("message", "")).strip()
            elif case.find("skipped") is not None:
                status = "skipped"

            node_id = f"{classname}::{name}" if classname else name
            safe_name = node_id.replace("/", "_").replace("::", "_")
            screenshot = ""
            shot_path = screenshots_dir / f"{safe_name}.png"
            if not shot_path.is_file():
                for candidate in screenshots_dir.glob(f"*{name}*.png"):
                    shot_path = candidate
                    break
            if shot_path.is_file():
                screenshot = shot_path.name

            results.append({
                "test_name": name,
                "class_name": classname,
                "status": status,
                "duration_ms": duration_ms,
                "error_message": error_message[:8000],
                "screenshot": screenshot,
            })

            totals["total"] += 1
            totals["duration_ms"] += duration_ms
            if status == "passed":
                totals["passed"] += 1
            elif status == "failed":
                totals["failed"] += 1
            else:
                totals["skipped"] += 1

    return results, totals


def _finish_run_error(run_id: str, started: int, message: str) -> None:
    finished = _now()
    with get_conn() as conn:
        conn.execute(
            """UPDATE automation_runs SET
               status=?, total=0, passed=0, failed=0, skipped=0,
               duration_ms=?, finished_at=?, log_summary=?, log_text=?, report_path=?
               WHERE id=?""",
            (
                "error",
                finished - started,
                finished,
                message[:500],
                message[:MAX_LOG_CHARS],
                "",
                run_id,
            ),
        )
        conn.commit()


def execute_run(
    run_id: str,
    suite: str,
    config: Optional[dict[str, Any]] = None,
    tests: Optional[list[str]] = None,
) -> None:
    global _running
    started = _now()
    run_config = normalize_run_config(config)
    selected_tests = [t.strip() for t in (tests or []) if t and t.strip()]
    run_dir = REPORTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    junit_path = run_dir / "junit.xml"
    html_path = run_dir / "report.html"
    log_path = run_dir / "output.log"
    screenshots_dir = run_dir / "screenshots"
    artifacts_dir = run_dir / "artifacts"
    screenshots_dir.mkdir(exist_ok=True)
    artifacts_dir.mkdir(exist_ok=True)

    try:
        ensure_playwright_browsers()
    except RuntimeError as exc:
        _finish_run_error(run_id, started, str(exc))
        _running = None
        return

    suite_path = _resolve_suite_path(suite)
    meta = _load_suite_meta(suite) if suite != "all" else {"name": "全部套件"}

    test_targets = _resolve_test_targets(suite, selected_tests) if selected_tests else []
    pytest_targets = test_targets if test_targets else [str(suite_path)]

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *pytest_targets,
        "-c",
        str(AUTOMATION_DIR / "pytest.ini"),
        f"--junitxml={junit_path}",
        f"--html={html_path}",
        "--self-contained-html",
        "-v",
        "--tb=short",
    ]

    env = os.environ.copy()
    env["AUTOMATION_SCREENSHOTS_DIR"] = str(screenshots_dir)
    env["AUTOMATION_ARTIFACTS_DIR"] = str(artifacts_dir)
    _apply_run_config(cmd, env, run_config)

    log_text = ""
    exit_code = 1
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        log_text = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        exit_code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        log_text = (exc.stdout or "") + ("\n" + (exc.stderr or "")) + "\n[超时] 测试运行超过 30 分钟"
        exit_code = 124
    except Exception as exc:
        log_text = f"执行失败: {exc}"
        exit_code = 1

    try:
        log_path.write_text(log_text, encoding="utf-8")
    except OSError:
        pass

    results: list[dict] = []
    totals = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration_ms": 0}

    if junit_path.is_file():
        try:
            results, totals = _parse_junit(junit_path, screenshots_dir)
        except ET.ParseError:
            pass

    if totals["total"] == 0:
        passed_match = re.search(r"(\d+) passed", log_text)
        failed_match = re.search(r"(\d+) failed", log_text)
        if passed_match:
            totals["passed"] = int(passed_match.group(1))
            totals["total"] += totals["passed"]
        if failed_match:
            totals["failed"] = int(failed_match.group(1))
            totals["total"] += totals["failed"]

    finished = _now()
    duration_ms = finished - started

    if totals["failed"] > 0 or exit_code not in (0, 1):
        status = "failed"
    elif totals["total"] == 0:
        status = "error"
    else:
        status = "passed"

    log_summary = log_text.strip().splitlines()[-1][:500] if log_text.strip() else ""
    report_rel = f"{run_id}/report.html" if html_path.is_file() else ""
    stored_log = log_text[:MAX_LOG_CHARS]
    artifacts_index = _load_test_artifacts(artifacts_dir)

    with get_conn() as conn:
        conn.execute(
            """UPDATE automation_runs SET
               status=?, total=?, passed=?, failed=?, skipped=?,
               duration_ms=?, finished_at=?, log_summary=?, log_text=?, report_path=?
               WHERE id=?""",
            (
                status,
                totals["total"],
                totals["passed"],
                totals["failed"],
                totals["skipped"],
                duration_ms,
                finished,
                log_summary,
                stored_log,
                report_rel,
                run_id,
            ),
        )
        for idx, item in enumerate(results):
            artifact_key = _artifact_key(item["class_name"], item["test_name"])
            artifacts = dict(artifacts_index.get(artifact_key, {}))
            screenshots = _merge_test_screenshots(
                run_id,
                artifact_key,
                item["screenshot"],
                artifacts,
            )
            if screenshots:
                artifacts["screenshots"] = screenshots
            conn.execute(
                """INSERT INTO automation_results
                   (id, run_id, test_name, class_name, status, duration_ms, error_message, screenshot, artifacts_json)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    _uid(),
                    run_id,
                    item["test_name"],
                    item["class_name"],
                    item["status"],
                    item["duration_ms"],
                    item["error_message"],
                    item["screenshot"],
                    json.dumps(artifacts, ensure_ascii=False),
                ),
            )
        conn.commit()

    _running = None


def get_screenshot_path(run_id: str, filename: str) -> Optional[Path]:
    if ".." in filename or "/" in filename or "\\" in filename:
        return None
    path = (REPORTS_DIR / run_id / "screenshots" / filename).resolve()
    reports_resolved = REPORTS_DIR.resolve()
    if not str(path).startswith(str(reports_resolved)):
        return None
    return path if path.is_file() else None
