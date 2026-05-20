import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

import db

_IDLE_GAP = timedelta(minutes=5)
_MAX_SESSION = timedelta(hours=4)


def _parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _build_session(events: list[dict]) -> dict:
    t_start = _parse(events[0]["timestamp"])
    t_end = _parse(events[-1]["timestamp"])
    app_counts = Counter(e.get("app_name") for e in events if e.get("app_name"))
    ordered = [app for app, _ in app_counts.most_common()]
    return {
        "started_at": events[0]["timestamp"],
        "ended_at": events[-1]["timestamp"],
        "duration_seconds": (t_end - t_start).total_seconds(),
        "event_count": len(events),
        "dominant_app": ordered[0] if ordered else "",
        "apps_seen": ordered,
        "event_ids": [e["id"] for e in events],
    }


def segment_events(events: list[dict]) -> list[dict]:
    """Split a flat event list into session dicts using gap/boundary/length rules."""
    if len(events) < 2:
        return []
    try:
        sorted_evts = sorted(events, key=lambda e: e["timestamp"])
        sessions: list[dict] = []
        current = [sorted_evts[0]]
        session_start_ts = _parse(sorted_evts[0]["timestamp"])

        for evt in sorted_evts[1:]:
            prev_ts = _parse(current[-1]["timestamp"])
            curr_ts = _parse(evt["timestamp"])

            split = False
            # Rule 1: idle gap > 5 min.
            if curr_ts - prev_ts > _IDLE_GAP:
                split = True
            # Rule 2: crossed midnight (UTC date boundary).
            elif prev_ts.date() != curr_ts.date():
                split = True
            # Rule 3: session exceeds 4 hours.
            elif curr_ts - session_start_ts > _MAX_SESSION:
                split = True

            if split:
                sessions.append(_build_session(current))
                current = [evt]
                session_start_ts = curr_ts
            else:
                current.append(evt)

        sessions.append(_build_session(current))
        return sessions

    except Exception:
        logging.exception("segment_events error")
        return []


def run_segmentation() -> list[dict]:
    """Fetch all events, segment them, persist sessions, return session list."""
    try:
        # get_recent_events returns DESC; sort ascending happens inside segment_events.
        events = db.get_recent_events(limit=10_000)
        sessions = segment_events(events)
        logging.info("Segmentation found %d session(s)", len(sessions))
        for sess in sessions:
            db.insert_session(
                {
                    "started_at": sess["started_at"],
                    "ended_at": sess["ended_at"],
                    "event_count": sess["event_count"],
                    "dominant_app": sess["dominant_app"],
                }
            )
        return sessions
    except Exception:
        logging.exception("run_segmentation error")
        return []
