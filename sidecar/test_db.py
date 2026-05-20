"""Standalone DB layer test — run with: py sidecar/test_db.py"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db

# ---------------------------------------------------------------------------
# Patch db module to use in-memory connection for isolation.
# ---------------------------------------------------------------------------
_mem = sqlite3.connect(":memory:")
_mem.row_factory = sqlite3.Row
db._conn = _mem
db.run_migrations(_mem)


def _tables() -> set[str]:
    return {
        row[0]
        for row in _mem.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


def main() -> None:
    # All 5 tables must exist after migrations.
    expected = {"schema_migrations", "events", "sessions", "workflows", "automations"}
    missing = expected - _tables()
    assert not missing, f"Missing tables: {missing}"

    # schema_migrations must have 4 rows.
    count = _mem.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    assert count == 4, f"Expected 4 migration rows, got {count}"

    # insert_event.
    db.insert_event(
        {
            "event_type": "key_press",
            "app_name": "test.exe",
            "window_title": "Test Window",
            "detail": "'t'",
        }
    )
    events = db.get_recent_events(limit=10)
    assert len(events) == 1 and events[0]["event_type"] == "key_press", "insert_event failed"

    # insert_session + get_sessions + update_session.
    sid = db.insert_session(
        {"started_at": "2026-05-19T08:00:00+00:00", "event_count": 5, "dominant_app": "test.exe"}
    )
    assert isinstance(sid, int) and sid > 0, "insert_session bad id"
    sessions = db.get_sessions()
    assert len(sessions) == 1, "get_sessions failed"
    db.update_session(sid, {"event_count": 99, "dominant_app": "updated.exe"})
    updated = db.get_sessions()[0]
    assert updated["event_count"] == 99 and updated["dominant_app"] == "updated.exe", "update_session failed"

    # insert_workflow + get_workflows.
    wid = db.insert_workflow(
        {
            "name": "Test workflow",
            "fingerprint": "test-fp-1",
            "steps": [{"action": "open"}],
            "frequency": 7,
        }
    )
    assert isinstance(wid, int) and wid > 0, "insert_workflow bad id"
    workflows = db.get_workflows()
    assert len(workflows) == 1 and workflows[0]["name"] == "Test workflow", "get_workflows failed"

    # insert_automation + get_automations.
    aid = db.insert_automation(
        {
            "workflow_id": wid,
            "name": "Test auto",
            "script_type": "pyautogui",
            "script_body": "pass",
        }
    )
    assert isinstance(aid, int) and aid > 0, "insert_automation bad id"
    autos = db.get_automations()
    assert len(autos) == 1 and autos[0]["script_type"] == "pyautogui", "get_automations failed"

    print("ALL DB TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
