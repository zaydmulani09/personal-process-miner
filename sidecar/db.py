import json
import logging
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

# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------

MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
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
        """,
    ),
    (
        2,
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at   TEXT NOT NULL,
            ended_at     TEXT,
            event_count  INTEGER DEFAULT 0,
            dominant_app TEXT
        )
        """,
    ),
    (
        3,
        """
        CREATE TABLE IF NOT EXISTS workflows (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            name                 TEXT NOT NULL,
            fingerprint          TEXT UNIQUE NOT NULL,
            steps                TEXT NOT NULL,
            frequency            INTEGER DEFAULT 0,
            avg_duration_seconds REAL,
            first_seen           TEXT,
            last_seen            TEXT,
            is_labeled           INTEGER DEFAULT 0,
            created_at           TEXT NOT NULL
        )
        """,
    ),
    (
        4,
        """
        CREATE TABLE IF NOT EXISTS automations (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow_id      INTEGER REFERENCES workflows(id),
            name             TEXT NOT NULL,
            script_type      TEXT NOT NULL,
            script_body      TEXT NOT NULL,
            last_run_at      TEXT,
            run_count        INTEGER DEFAULT 0,
            last_run_status  TEXT,
            created_at       TEXT NOT NULL
        )
        """,
    ),
    (
        5,
        """
        CREATE TABLE IF NOT EXISTS privacy_settings (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
    ),
]

_DEFAULT_SETTINGS: dict[str, str] = {
    "blocklist_apps": "[]",
    "allowlist_apps": "[]",
    "retention_days": "30",
    "capture_mouse_moves": "true",
    "capture_keystrokes": "false",
}


def run_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    conn.commit()

    applied = {
        row[0]
        for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
    }

    # Migration 1 may already be present without schema_migrations tracking.
    existing_tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "events" in existing_tables and 1 not in applied:
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (1, datetime.now(timezone.utc).isoformat()),
        )
        applied.add(1)
        conn.commit()

    for version, sql in MIGRATIONS:
        if version in applied:
            continue
        logging.info("Applying migration %d", version)
        conn.execute(sql)
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (version, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        logging.info("Migration %d applied", version)

    # Seed default privacy settings if not present.
    now = datetime.now(timezone.utc).isoformat()
    for key, value in _DEFAULT_SETTINGS.items():
        conn.execute(
            "INSERT OR IGNORE INTO privacy_settings (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, now),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(_DATA_DIR, exist_ok=True)
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        run_migrations(_conn)
    return _conn


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


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


def get_events_by_ids(event_ids: list[int]) -> list[dict]:
    if not event_ids:
        return []
    conn = _get_conn()
    placeholders = ",".join("?" * len(event_ids))
    with _lock:
        rows = conn.execute(
            f"SELECT * FROM events WHERE id IN ({placeholders}) ORDER BY timestamp ASC",
            event_ids,
        ).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def insert_session(session: dict) -> int:
    conn = _get_conn()
    with _lock:
        cur = conn.execute(
            "INSERT INTO sessions (started_at, ended_at, event_count, dominant_app) "
            "VALUES (:started_at, :ended_at, :event_count, :dominant_app)",
            {
                "started_at": session["started_at"],
                "ended_at": session.get("ended_at"),
                "event_count": session.get("event_count", 0),
                "dominant_app": session.get("dominant_app"),
            },
        )
        conn.commit()
        return cur.lastrowid


_SESSION_COLUMNS = {"started_at", "ended_at", "event_count", "dominant_app"}


def update_session(session_id: int, updates: dict) -> None:
    if not updates:
        return
    safe = {k: v for k, v in updates.items() if k in _SESSION_COLUMNS}
    if not safe:
        return
    conn = _get_conn()
    cols = ", ".join(f"{k} = ?" for k in safe)
    vals = list(safe.values()) + [session_id]
    with _lock:
        conn.execute(f"UPDATE sessions SET {cols} WHERE id = ?", vals)
        conn.commit()


def get_sessions(limit: int = 50) -> list[dict]:
    conn = _get_conn()
    with _lock:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


def insert_workflow(workflow: dict) -> int:
    conn = _get_conn()
    with _lock:
        cur = conn.execute(
            "INSERT INTO workflows "
            "(name, fingerprint, steps, frequency, avg_duration_seconds, "
            " first_seen, last_seen, is_labeled, created_at) "
            "VALUES (:name, :fingerprint, :steps, :frequency, :avg_duration_seconds, "
            "        :first_seen, :last_seen, :is_labeled, :created_at)",
            {
                "name": workflow["name"],
                "fingerprint": workflow["fingerprint"],
                "steps": json.dumps(workflow.get("steps", [])),
                "frequency": workflow.get("frequency", 0),
                "avg_duration_seconds": workflow.get("avg_duration_seconds"),
                "first_seen": workflow.get("first_seen"),
                "last_seen": workflow.get("last_seen"),
                "is_labeled": int(workflow.get("is_labeled", False)),
                "created_at": workflow.get(
                    "created_at", datetime.now(timezone.utc).isoformat()
                ),
            },
        )
        conn.commit()
        return cur.lastrowid


def get_workflows() -> list[dict]:
    conn = _get_conn()
    with _lock:
        rows = conn.execute(
            "SELECT * FROM workflows ORDER BY frequency DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def upsert_workflow(workflow: dict) -> None:
    """Insert workflow or update frequency/last_seen/avg_duration on fingerprint conflict."""
    conn = _get_conn()
    with _lock:
        conn.execute(
            """
            INSERT INTO workflows
                (name, fingerprint, steps, frequency, avg_duration_seconds,
                 first_seen, last_seen, is_labeled, created_at)
            VALUES
                (:name, :fingerprint, :steps, :frequency, :avg_duration_seconds,
                 :first_seen, :last_seen, 0, :created_at)
            ON CONFLICT(fingerprint) DO UPDATE SET
                frequency            = excluded.frequency,
                last_seen            = excluded.last_seen,
                avg_duration_seconds = excluded.avg_duration_seconds
            """,
            {
                "name": workflow.get("name", "Auto-detected workflow"),
                "fingerprint": workflow["fingerprint"],
                "steps": json.dumps(workflow.get("steps", [])),
                "frequency": workflow.get("frequency", 0),
                "avg_duration_seconds": workflow.get("avg_duration_seconds"),
                "first_seen": workflow.get("first_seen"),
                "last_seen": workflow.get("last_seen"),
                "created_at": workflow.get(
                    "created_at", datetime.now(timezone.utc).isoformat()
                ),
            },
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Automations
# ---------------------------------------------------------------------------


def insert_automation(automation: dict) -> int:
    conn = _get_conn()
    with _lock:
        cur = conn.execute(
            "INSERT INTO automations "
            "(workflow_id, name, script_type, script_body, last_run_at, "
            " run_count, last_run_status, created_at) "
            "VALUES (:workflow_id, :name, :script_type, :script_body, :last_run_at, "
            "        :run_count, :last_run_status, :created_at)",
            {
                "workflow_id": automation.get("workflow_id"),
                "name": automation["name"],
                "script_type": automation["script_type"],
                "script_body": automation["script_body"],
                "last_run_at": automation.get("last_run_at"),
                "run_count": automation.get("run_count", 0),
                "last_run_status": automation.get("last_run_status"),
                "created_at": automation.get(
                    "created_at", datetime.now(timezone.utc).isoformat()
                ),
            },
        )
        conn.commit()
        return cur.lastrowid


def label_workflow(workflow_id: int, name: str, steps: list) -> bool:
    conn = _get_conn()
    with _lock:
        cur = conn.execute(
            "UPDATE workflows SET name = ?, steps = ?, is_labeled = 1 WHERE id = ?",
            (name, json.dumps(steps), workflow_id),
        )
        conn.commit()
        return cur.rowcount > 0


def delete_workflow(workflow_id: int) -> bool:
    conn = _get_conn()
    with _lock:
        cur = conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
        conn.commit()
        return cur.rowcount > 0


def get_automations() -> list[dict]:
    conn = _get_conn()
    with _lock:
        rows = conn.execute("SELECT * FROM automations").fetchall()
    return [dict(row) for row in rows]


def get_automation_by_id(automation_id: int) -> dict | None:
    conn = _get_conn()
    with _lock:
        row = conn.execute(
            "SELECT * FROM automations WHERE id = ?", (automation_id,)
        ).fetchone()
    return dict(row) if row else None


def update_automation_script(automation_id: int, script_body: str) -> None:
    conn = _get_conn()
    with _lock:
        conn.execute(
            "UPDATE automations SET script_body = ? WHERE id = ?",
            (script_body, automation_id),
        )
        conn.commit()


def update_automation_run(automation_id: int, status: str) -> None:
    conn = _get_conn()
    with _lock:
        conn.execute(
            "UPDATE automations "
            "SET last_run_at = ?, run_count = run_count + 1, last_run_status = ? "
            "WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), status, automation_id),
        )
        conn.commit()


def update_automation_name(automation_id: int, name: str) -> None:
    conn = _get_conn()
    with _lock:
        conn.execute(
            "UPDATE automations SET name = ? WHERE id = ?",
            (name, automation_id),
        )
        conn.commit()


def delete_automation(automation_id: int) -> bool:
    conn = _get_conn()
    with _lock:
        cur = conn.execute(
            "DELETE FROM automations WHERE id = ?", (automation_id,)
        )
        conn.commit()
        return cur.rowcount > 0


def get_automation_stats() -> dict:
    conn = _get_conn()
    with _lock:
        total = conn.execute(
            "SELECT COUNT(*) FROM automations"
        ).fetchone()[0]
        total_runs = conn.execute(
            "SELECT COALESCE(SUM(run_count), 0) FROM automations"
        ).fetchone()[0]
        successful_runs = conn.execute(
            "SELECT COUNT(*) FROM automations WHERE last_run_status = 'success'"
        ).fetchone()[0]
    return {
        "total_automations": total,
        "total_runs": int(total_runs),
        "successful_runs": successful_runs,
        "estimated_time_saved_seconds": float(total_runs) * 120.0,
    }


# ---------------------------------------------------------------------------
# Privacy Settings
# ---------------------------------------------------------------------------


def get_setting(key: str, default: str = "") -> str:
    conn = _get_conn()
    with _lock:
        row = conn.execute(
            "SELECT value FROM privacy_settings WHERE key = ?", (key,)
        ).fetchone()
    return row[0] if row else default


def set_setting(key: str, value: str) -> None:
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        conn.execute(
            "INSERT INTO privacy_settings (key, value, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value, now),
        )
        conn.commit()


def get_all_settings() -> dict:
    conn = _get_conn()
    with _lock:
        rows = conn.execute("SELECT key, value FROM privacy_settings").fetchall()
    return {row[0]: row[1] for row in rows}


# ---------------------------------------------------------------------------
# Purge helpers
# ---------------------------------------------------------------------------


def purge_old_events(retention_days: int) -> int:
    if retention_days == 0:
        return 0
    conn = _get_conn()
    cutoff = datetime.now(timezone.utc)
    from datetime import timedelta
    cutoff = (cutoff - timedelta(days=retention_days)).isoformat()
    with _lock:
        cur = conn.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))
        conn.commit()
    return cur.rowcount


def purge_all_data() -> dict:
    conn = _get_conn()
    with _lock:
        counts = {}
        for table in ("events", "sessions", "workflows", "automations"):
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            conn.execute(f"DELETE FROM {table}")
            counts[table] = n
        conn.commit()
    return counts
