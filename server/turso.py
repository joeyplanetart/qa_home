"""Turso libSQL HTTP client — sqlite3-compatible subset for serverless."""

from __future__ import annotations

import base64
import json
import os
from typing import Any, Iterator, Sequence
from urllib.parse import parse_qs, urlparse

import httpx


class TursoError(RuntimeError):
    pass


class TursoRow:
    __slots__ = ("_data",)

    def __init__(self, columns: list[str], values: list[Any]) -> None:
        self._data = dict(zip(columns, values))

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            return list(self._data.values())[key]
        return self._data[key]

    def keys(self) -> list[str]:
        return list(self._data.keys())


class TursoCursor:
    __slots__ = ("_rows", "rowcount")

    def __init__(self, rows: list[TursoRow], affected: int) -> None:
        self._rows = rows
        self.rowcount = affected

    def fetchone(self) -> TursoRow | None:
        if not self._rows:
            return None
        return self._rows[0]

    def fetchall(self) -> list[TursoRow]:
        return self._rows


class TursoConnection:
    def __init__(self, pipeline_url: str, auth_token: str) -> None:
        self._pipeline_url = pipeline_url
        self._auth_token = auth_token
        self._client = httpx.Client(timeout=30.0)

    def __enter__(self) -> TursoConnection:
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def commit(self) -> None:
        pass

    def execute(self, sql: str, params: Sequence[Any] = ()) -> TursoCursor:
        return self._run(sql, list(params))

    def executemany(self, sql: str, seq_of_params: Sequence[Sequence[Any]]) -> TursoCursor:
        total = 0
        for params in seq_of_params:
            cur = self._run(sql, list(params))
            total += cur.rowcount
        return TursoCursor([], total)

    def executescript(self, script: str) -> TursoCursor:
        for stmt in _split_script(script):
            self._run(stmt, [])
        return TursoCursor([], 0)

    def _run(self, sql: str, params: list[Any]) -> TursoCursor:
        payload = {
            "requests": [
                {
                    "type": "execute",
                    "stmt": {
                        "sql": sql,
                        "args": [_to_arg(v) for v in params],
                    },
                },
                {"type": "close"},
            ]
        }
        res = self._client.post(
            self._pipeline_url,
            headers={
                "Authorization": f"Bearer {self._auth_token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if res.status_code == 401:
            raise TursoError(_auth_error_message())
        res.raise_for_status()
        body = res.json()
        return _parse_result(body)


def turso_enabled() -> bool:
    url, token = _turso_config()
    return bool(url and token)


def connect_turso() -> TursoConnection:
    url, token = _turso_config()
    if not url or not token:
        raise TursoError("缺少 TURSO_DATABASE_URL 或 TURSO_AUTH_TOKEN")
    _validate_token_claims(token)
    pipeline = _to_pipeline_url(url)
    return TursoConnection(pipeline, token)


def _turso_config() -> tuple[str, str]:
    url = os.environ.get("TURSO_DATABASE_URL", "").strip()
    token = os.environ.get("TURSO_AUTH_TOKEN", "").strip()

    if "?" in url:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        for key in ("authToken", "auth_token"):
            if qs.get(key):
                token = token or qs[key][0].strip()
        url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

    return url, token


def _validate_token_claims(token: str) -> None:
    try:
        payload_b64 = token.split(".")[1]
        padding = "=" * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))
    except (IndexError, json.JSONDecodeError, ValueError):
        return

    # 组织 API token 只有 org_id，不能用于 /v2/pipeline SQL 查询
    if "org_id" in claims and "a" not in claims:
        raise TursoError(_auth_error_message())


def _auth_error_message() -> str:
    return (
        "Turso 认证失败：当前 TURSO_AUTH_TOKEN 不是数据库 token。"
        "请在 Turso 控制台打开数据库 qa → Create Token，"
        "或运行 `turso db tokens create qa`，将生成的 token 写入 .env"
    )


def _to_pipeline_url(url: str) -> str:
    if url.startswith("libsql://"):
        url = "https://" + url[len("libsql://") :]
    url = url.rstrip("/")
    if not url.endswith("/v2/pipeline"):
        url += "/v2/pipeline"
    return url


def _to_arg(value: Any) -> dict[str, str]:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "integer", "value": "1" if value else "0"}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": str(value)}
    if isinstance(value, bytes):
        return {"type": "blob", "value": base64.b64encode(value).decode()}
    return {"type": "text", "value": str(value)}


def _parse_result(body: dict[str, Any]) -> TursoCursor:
    results = body.get("results") or []
    for item in results:
        if item.get("type") == "error":
            msg = item.get("error", {}).get("message", "Turso query failed")
            raise TursoError(msg)
        if item.get("type") != "ok":
            continue
        response = item.get("response") or {}
        if response.get("type") != "execute":
            continue
        result = response.get("result") or {}
        cols = [c.get("name", f"col{i}") for i, c in enumerate(result.get("cols") or [])]
        rows = [TursoRow(cols, _decode_row(row)) for row in result.get("rows") or []]
        affected = int(result.get("affected_row_count") or 0)
        return TursoCursor(rows, affected)
    return TursoCursor([], 0)


def _decode_row(row: list[Any]) -> list[Any]:
    out: list[Any] = []
    for cell in row:
        if isinstance(cell, dict):
            t = cell.get("type")
            if t == "null":
                out.append(None)
            elif t == "integer":
                out.append(int(cell["value"]))
            elif t == "float":
                out.append(float(cell["value"]))
            elif t == "blob":
                out.append(base64.b64decode(cell["value"]))
            else:
                out.append(cell.get("value"))
        else:
            out.append(cell)
    return out


def _split_script(script: str) -> Iterator[str]:
    for part in script.split(";"):
        stmt = part.strip()
        if stmt:
            yield stmt
