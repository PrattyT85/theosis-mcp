from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from restore_smoke_test import latest_backup  # noqa: E402


def test_latest_backup_selects_newest_dump(tmp_path):
    older = tmp_path / "theosis-20260101T000000Z.dump"
    newer = tmp_path / "theosis-20260102T000000Z.dump"
    older.write_bytes(b"old")
    newer.write_bytes(b"new")
    older.touch()
    newer.touch()

    assert latest_backup(tmp_path) == newer


def test_latest_backup_requires_a_dump(tmp_path):
    try:
        latest_backup(tmp_path)
    except RuntimeError as exc:
        assert "no backup" in str(exc)
    else:
        raise AssertionError("latest_backup should reject an empty directory")
