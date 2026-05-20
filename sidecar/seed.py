"""Seed realistic sample data — run with: py sidecar/seed.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db

_NOW = "2026-05-19T09:00:00+00:00"

_WORKFLOWS = [
    {
        "name": "Morning standup prep",
        "fingerprint": "standup-prep-v1",
        "steps": [
            {"app": "Slack.exe", "action": "open_channel", "detail": "#standup"},
            {"app": "Notion.exe", "action": "open_page", "detail": "Daily notes"},
            {"app": "chrome.exe", "action": "navigate", "detail": "github.com/pulls"},
        ],
        "frequency": 18,
        "avg_duration_seconds": 142.5,
        "first_seen": "2026-02-20T08:47:00+00:00",
        "last_seen": "2026-05-16T08:51:00+00:00",
        "is_labeled": True,
        "created_at": "2026-02-20T08:47:00+00:00",
    },
    {
        "name": "Deploy to staging",
        "fingerprint": "deploy-staging-v1",
        "steps": [
            {"app": "WindowsTerminal.exe", "action": "run", "detail": "git add -A"},
            {"app": "WindowsTerminal.exe", "action": "run", "detail": "git commit"},
            {"app": "WindowsTerminal.exe", "action": "run", "detail": "git push"},
            {"app": "WindowsTerminal.exe", "action": "run", "detail": "ssh deploy"},
            {"app": "chrome.exe", "action": "navigate", "detail": "staging.internal"},
        ],
        "frequency": 12,
        "avg_duration_seconds": 87.0,
        "first_seen": "2026-03-04T14:10:00+00:00",
        "last_seen": "2026-05-14T16:33:00+00:00",
        "is_labeled": True,
        "created_at": "2026-03-04T14:10:00+00:00",
    },
    {
        "name": "Weekly report export",
        "fingerprint": "weekly-report-v1",
        "steps": [
            {"app": "EXCEL.EXE", "action": "open_file", "detail": "weekly_metrics.xlsx"},
            {"app": "EXCEL.EXE", "action": "export", "detail": "PDF"},
            {"app": "OUTLOOK.EXE", "action": "compose", "detail": "Weekly report"},
            {"app": "OUTLOOK.EXE", "action": "attach_and_send", "detail": None},
        ],
        "frequency": 6,
        "avg_duration_seconds": 215.0,
        "first_seen": "2026-03-14T17:00:00+00:00",
        "last_seen": "2026-05-09T17:04:00+00:00",
        "is_labeled": True,
        "created_at": "2026-03-14T17:00:00+00:00",
    },
]

_SESSIONS = [
    {
        "started_at": "2026-05-19T08:45:00+00:00",
        "ended_at": "2026-05-19T09:00:00+00:00",
        "event_count": 312,
        "dominant_app": "chrome.exe",
    },
    {
        "started_at": "2026-05-16T13:20:00+00:00",
        "ended_at": "2026-05-16T14:55:00+00:00",
        "event_count": 487,
        "dominant_app": "WindowsTerminal.exe",
    },
    {
        "started_at": "2026-05-14T09:00:00+00:00",
        "ended_at": "2026-05-14T10:30:00+00:00",
        "event_count": 203,
        "dominant_app": "Notion.exe",
    },
    {
        "started_at": "2026-05-12T16:00:00+00:00",
        "ended_at": "2026-05-12T16:22:00+00:00",
        "event_count": 98,
        "dominant_app": "EXCEL.EXE",
    },
    {
        "started_at": "2026-05-09T17:00:00+00:00",
        "ended_at": "2026-05-09T17:18:00+00:00",
        "event_count": 134,
        "dominant_app": "OUTLOOK.EXE",
    },
]

_EVENT_TEMPLATES = [
    ("key_press", "chrome.exe", "GitHub — Pull Requests", "'a'", None, None),
    ("key_press", "chrome.exe", "GitHub — Pull Requests", "'b'", None, None),
    ("mouse_click", "chrome.exe", "GitHub — Pull Requests", "Button.left", 640, 400),
    ("window_focus", "Notion.exe", "Daily notes — Notion", None, None, None),
    ("key_press", "Notion.exe", "Daily notes — Notion", "'s'", None, None),
    ("mouse_click", "Notion.exe", "Daily notes — Notion", "Button.left", 320, 200),
    ("window_focus", "WindowsTerminal.exe", "Windows PowerShell", None, None, None),
    ("key_press", "WindowsTerminal.exe", "Windows PowerShell", "'g'", None, None),
    ("key_press", "WindowsTerminal.exe", "Windows PowerShell", "'i'", None, None),
    ("mouse_click", "WindowsTerminal.exe", "Windows PowerShell", "Button.right", 150, 300),
]


def main() -> None:
    conn = db._get_conn()

    # Clear existing rows (keep schema).
    with db._lock:
        conn.execute("DELETE FROM automations")
        conn.execute("DELETE FROM workflows")
        conn.execute("DELETE FROM sessions")
        conn.execute("DELETE FROM events")
        conn.commit()

    total = 0

    # Workflows.
    wf_ids = []
    for wf in _WORKFLOWS:
        wf_ids.append(db.insert_workflow(wf))
        total += 1

    # Automation for workflow 1.
    db.insert_automation(
        {
            "workflow_id": wf_ids[0],
            "name": "Auto standup prep",
            "script_type": "pyautogui",
            "script_body": (
                "import pyautogui, time\n"
                "# Open Slack\npyautogui.hotkey('ctrl', 'alt', 's')\n"
                "time.sleep(1)\n"
                "# Navigate to #standup\npyautogui.hotkey('ctrl', 'k')\n"
                "pyautogui.typewrite('standup', interval=0.05)\n"
                "pyautogui.press('enter')\n"
            ),
            "run_count": 3,
            "last_run_at": "2026-05-16T08:50:00+00:00",
            "last_run_status": "success",
            "created_at": "2026-04-01T10:00:00+00:00",
        }
    )
    total += 1

    # Sessions.
    for sess in _SESSIONS:
        db.insert_session(sess)
        total += 1

    # 50 events cycling through templates.
    from datetime import datetime, timedelta, timezone

    base = datetime(2026, 5, 19, 8, 45, 0, tzinfo=timezone.utc)
    for i in range(50):
        tpl = _EVENT_TEMPLATES[i % len(_EVENT_TEMPLATES)]
        evt_type, app, title, detail, x, y = tpl
        ts = (base + timedelta(seconds=i * 15)).isoformat()
        db.insert_event(
            {
                "timestamp": ts,
                "event_type": evt_type,
                "app_name": app,
                "window_title": title,
                "detail": detail,
                "x": x,
                "y": y,
            }
        )
        total += 1

    print(f"SEED COMPLETE — {total} rows inserted")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SEED FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
