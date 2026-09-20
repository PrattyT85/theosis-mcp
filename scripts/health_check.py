#!/usr/bin/env python3
"""Read-only health and backup verification for the Theosis deployment."""

from __future__ import annotations

import http.client
import json
import subprocess
import sys
import time
from pathlib import Path

HOST = "192.168.1.130"
PORT = 8000
BACKUP_DIR = Path("/root/theosis-backups")
MAX_BACKUP_AGE_SECONDS = 3 * 24 * 60 * 60


def command(*args: str) -> tuple[int, str]:
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    return result.returncode, result.stdout.strip() or result.stderr.strip()


def db_value(sql: str) -> str:
    code, output = command(
        "runuser", "-u", "postgres", "--",
        "psql", "-d", "theosis", "-At", "-v", "ON_ERROR_STOP=1", "-c", sql,
    )
    if code:
        raise RuntimeError(output)
    return output


def check_mcp() -> None:
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "theosis-healthcheck", "version": "1"},
        },
    })
    last_error = "unknown error"
    for attempt in range(5):
        connection = None
        try:
            connection = http.client.HTTPConnection(HOST, PORT, timeout=10)
            connection.request(
                "POST", "/mcp", payload,
                {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
            )
            response = connection.getresponse()
            body = response.read().decode(errors="replace")
            if response.status == 200 and '"result"' in body:
                return
            last_error = f"HTTP {response.status}"
        except OSError as exc:
            last_error = str(exc)
        finally:
            if connection is not None:
                connection.close()
        if attempt < 4:
            time.sleep(2)
    raise RuntimeError(f"MCP initialize failed after retries: {last_error}")


def check_backup() -> str:
    backups = sorted(BACKUP_DIR.glob("theosis-*.dump"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not backups:
        raise RuntimeError("no automated Theosis backup found")
    latest = backups[0]
    age = time.time() - latest.stat().st_mtime
    if age > MAX_BACKUP_AGE_SECONDS:
        raise RuntimeError(f"latest backup is too old: {latest}")
    code, output = command("pg_restore", "--list", str(latest))
    if code or "TABLE" not in output:
        raise RuntimeError(f"backup archive verification failed: {latest}")
    return f"{latest.name} age_seconds={int(age)}"


def main() -> int:
    failures: list[str] = []
    try:
        if db_value("SELECT current_setting('server_encoding');") != "UTF8":
            raise RuntimeError("database encoding is not UTF8")
        if db_value("SELECT extname FROM pg_extension WHERE extname='vector';") != "vector":
            raise RuntimeError("pgvector extension is unavailable")
        for table, minimum in (("bible_translations", 1), ("bible_verses", 1), ("theological_works", 1)):
            count = int(db_value(f"SELECT count(*) FROM {table};"))
            if count < minimum:
                raise RuntimeError(f"{table} has only {count} rows")
        code, output = command("systemctl", "is-active", "--quiet", "theosis-mcp.service")
        if code:
            raise RuntimeError("theosis-mcp.service is not active")
        check_mcp()
    except Exception as exc:
        failures.append(str(exc))

    try:
        backup = check_backup()
    except Exception as exc:
        failures.append(str(exc))
        backup = "unavailable"

    if failures:
        print("THEOSIS_HEALTH_FAIL", " | ".join(failures), file=sys.stderr)
        return 1
    print(f"THEOSIS_HEALTH_OK backup={backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
