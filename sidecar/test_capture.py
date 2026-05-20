"""Standalone capture smoke-test — run with: py sidecar/test_capture.py"""
import os
import sys
import sqlite3
import time

# Ensure sidecar/ is on path when run from project root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import capture
import db

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_PROJECT_ROOT, "data", "events.db")


def main() -> None:
    # Start capture, wait, stop.
    capture.start_capture()
    time.sleep(2)
    capture.stop_capture()

    # DB file must exist.
    assert os.path.exists(_DB_PATH), f"DB not found at {_DB_PATH}"

    # Table must be queryable via sqlite3 directly.
    conn = sqlite3.connect(_DB_PATH)
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'").fetchall()
    assert rows, "events table missing"
    conn.close()

    # get_recent_events must return a list (may be empty in headless env).
    events = db.get_recent_events(limit=10)
    assert isinstance(events, list), f"expected list, got {type(events)}"

    print("ALL CAPTURE TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
