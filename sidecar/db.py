import os
import sqlite3
import threading
from datetime import datetime, timezone

_SIDECAR_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SIDECAR_DIR)
_DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
_DB_PATH = os.path.join(_DATA_DIR, "events.db")

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT NOT NULL,
    event_type   TEXT NOT NULL,
    app_name     TEXT,
    window_title TEXT,
    detail       TEXT,
    x            INTEGER,
    y            INTEGER
)
"""


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(_DATA_DIR, exist_ok=True)
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute(_SCHEMA)
        _conn.commit()
    return _conn


def insert_event(event: dict) -> None:
    conn = _get_conn()
    with _lock:
        conn.execute(
            "INSERT INTO events "
            "(timestamp, event_type, app_name, window_title, detail, x, y) "
            "VALUES (:timestamp, :event_type, :app_name, :window_title, :detail, :x, :y)",
            {
                "timestamp": event.get(
                    "timestamp", datetime.now(timezone.utc).isoformat()
                ),
                "event_type": event["event_type"],
                "app_name": event.get("app_name"),
                "window_title": event.get("window_title"),
                "detail": event.get("detail"),
                "x": event.get("x"),
                "y": event.get("y"),
            },
        )
        conn.commit()


def get_recent_events(limit: int = 100) -> list[dict]:
    conn = _get_conn()
    with _lock:
        rows = conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]
