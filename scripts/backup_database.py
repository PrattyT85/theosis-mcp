#!/usr/bin/env python3
"""Create and rotate compressed PostgreSQL backups for Theosis.

The service runs as root so it can write the protected backup directory, while
pg_dump itself runs as the PostgreSQL administrator. Files are written to a
partial name and atomically renamed only after pg_dump succeeds.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKUP_DIR = Path("/root/theosis-backups")
KEEP = 3


def main() -> int:
    BACKUP_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    final = BACKUP_DIR / f"theosis-{stamp}.dump"
    partial = BACKUP_DIR / f".{final.name}.partial"

    try:
        with partial.open("wb") as output:
            result = subprocess.run(
                [
                    "runuser", "-u", "postgres", "--", "pg_dump",
                    "-Fc", "--no-owner", "--no-privileges", "--dbname=theosis",
                ],
                stdout=output,
                stderr=subprocess.PIPE,
                check=False,
                timeout=900,
            )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode(errors="replace").strip())
        if partial.stat().st_size < 100 * 1024 * 1024:
            raise RuntimeError(f"backup is unexpectedly small: {partial.stat().st_size} bytes")
        partial.replace(final)

        backups = sorted(
            BACKUP_DIR.glob("theosis-*.dump"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for old in backups[KEEP:]:
            old.unlink()
        os.chmod(final, 0o600)
        print(f"backup_ok path={final} bytes={final.stat().st_size} kept={min(len(backups), KEEP)}")
        return 0
    except Exception as exc:
        partial.unlink(missing_ok=True)
        print(f"backup_failed error={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
