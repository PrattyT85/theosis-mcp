#!/usr/bin/env python3
"""Restore the newest Theosis dump into a disposable UTF-8 database."""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BACKUP_DIR = Path("/root/theosis-backups")


def latest_backup(directory: Path = BACKUP_DIR) -> Path:
    backups = sorted(directory.glob("theosis-*.dump"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not backups:
        raise RuntimeError(f"no backup found in {directory}")
    return backups[0]


def run(*args: str, check: bool = True) -> str:
    result = subprocess.run(args, capture_output=True, text=True, timeout=1800)
    output = result.stdout.strip() or result.stderr.strip()
    if check and result.returncode:
        raise RuntimeError(f"{args[0]} failed: {output}")
    return output


def query(database: str, sql: str) -> str:
    return run(
        "runuser", "-u", "postgres", "--", "psql", "-d", database,
        "-At", "-v", "ON_ERROR_STOP=1", "-c", sql,
    )


def main() -> int:
    database = f"theosis_restore_check_{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
    created = False
    try:
        backup_service = subprocess.run(
            ["systemctl", "is-active", "--quiet", "theosis-backup.service"],
            check=False,
        )
        if backup_service.returncode == 0:
            raise RuntimeError("theosis-backup.service is active; retry after the backup completes")
        backup = latest_backup()
        run(
            "runuser", "-u", "postgres", "--", "createdb", "--template=template0",
            "--encoding=UTF8", "--lc-collate=C", "--lc-ctype=C", "--owner=theosis", database,
        )
        created = True
        readable_backup = Path("/var/lib/postgresql") / backup.name
        run("cp", str(backup), str(readable_backup))
        run("chown", "postgres:postgres", str(readable_backup))
        try:
            run("runuser", "-u", "postgres", "--", "pg_restore", "--exit-on-error", "--no-owner", "--no-privileges", "--dbname", database, str(readable_backup))
        finally:
            readable_backup.unlink(missing_ok=True)
        run("runuser", "-u", "postgres", "--", "psql", "-d", database, "-v", "ON_ERROR_STOP=1", "-c", "GRANT USAGE ON SCHEMA public TO theosis; GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO theosis; GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO theosis;")

        if query(database, "SELECT current_setting('server_encoding');") != "UTF8":
            raise RuntimeError("restored database is not UTF8")
        checks = {
            "translations": ("SELECT count(*) FROM bible_translations;", 30),
            "verses": ("SELECT count(*) FROM bible_verses;", 1_000_000),
            "theological_works": ("SELECT count(*) FROM theological_works;", 350),
        }
        for label, (sql, minimum) in checks.items():
            count = int(query(database, sql))
            if count < minimum:
                raise RuntimeError(f"{label} count {count} is below {minimum}")
        if query(database, "SELECT count(*) FROM bible_verses v JOIN bible_books b ON b.id=v.book_id JOIN bible_translations t ON t.id=b.translation_id WHERE t.abbreviation='WLC' AND b.osis_ref='Gen' AND v.chapter=1 AND v.verse=1 AND length(v.text)>0;") != "1":
            raise RuntimeError("Hebrew WLC sample lookup failed")
        if query(database, "SELECT count(*) FROM bible_verses v JOIN bible_books b ON b.id=v.book_id JOIN bible_translations t ON t.id=b.translation_id WHERE t.abbreviation='Vulgate' AND b.osis_ref='Tob' AND v.chapter=1 AND v.verse=1 AND length(v.text)>0;") != "1":
            raise RuntimeError("Vulgate Tobit sample lookup failed")
        print(f"THEOSIS_RESTORE_SMOKE_OK database={database} backup={backup.name}")
        return 0
    except Exception as exc:
        print(f"THEOSIS_RESTORE_SMOKE_FAIL error={exc}", file=sys.stderr)
        return 1
    finally:
        if created:
            run("runuser", "-u", "postgres", "--", "dropdb", "--if-exists", database, check=False)


if __name__ == "__main__":
    raise SystemExit(main())
