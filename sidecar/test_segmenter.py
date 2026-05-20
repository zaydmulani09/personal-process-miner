"""Standalone segmenter test — run with: py sidecar/test_segmenter.py"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import segmenter


def _evt(id: int, ts: datetime, app: str | None = "Chrome") -> dict:
    return {
        "id": id,
        "timestamp": ts.isoformat(),
        "app_name": app,
        "event_type": "key_press",
    }


def _ts(base: datetime, delta_minutes: float = 0) -> datetime:
    return base + timedelta(minutes=delta_minutes)


_BASE = datetime(2026, 5, 19, 10, 0, 0, tzinfo=timezone.utc)
_MIDNIGHT = datetime(2026, 5, 18, 23, 58, 0, tzinfo=timezone.utc)


def test_idle_gap_split() -> None:
    evts = [
        _evt(1, _ts(_BASE, 0)),
        _evt(2, _ts(_BASE, 1)),
        _evt(3, _ts(_BASE, 2)),
        # 6-minute gap → new session
        _evt(4, _ts(_BASE, 8)),
        _evt(5, _ts(_BASE, 9)),
        _evt(6, _ts(_BASE, 10)),
    ]
    sessions = segmenter.segment_events(evts)
    assert len(sessions) == 2, f"Expected 2 sessions, got {len(sessions)}: {sessions}"
    assert sessions[0]["event_count"] == 3
    assert sessions[1]["event_count"] == 3


def test_midnight_boundary_split() -> None:
    evts = [
        _evt(1, _MIDNIGHT),                                       # 2026-05-18
        _evt(2, _MIDNIGHT + timedelta(minutes=4)),                # 2026-05-19 00:02
    ]
    sessions = segmenter.segment_events(evts)
    assert len(sessions) == 2, f"Expected 2 sessions (midnight split), got {len(sessions)}"


def test_dominant_app() -> None:
    evts = [
        _evt(1, _ts(_BASE, 0), "Chrome"),
        _evt(2, _ts(_BASE, 1), "VSCode"),
        _evt(3, _ts(_BASE, 2), "Chrome"),
        _evt(4, _ts(_BASE, 3), "VSCode"),
        _evt(5, _ts(_BASE, 4), "Chrome"),
    ]
    sessions = segmenter.segment_events(evts)
    assert len(sessions) == 1, f"Expected 1 session, got {len(sessions)}"
    assert sessions[0]["dominant_app"] == "Chrome", (
        f"Expected dominant Chrome, got {sessions[0]['dominant_app']}"
    )
    assert sessions[0]["apps_seen"][0] == "Chrome"


def test_empty_and_single() -> None:
    assert segmenter.segment_events([]) == [], "Empty input should return []"
    assert segmenter.segment_events([_evt(1, _BASE)]) == [], (
        "Single-event input should return []"
    )


def test_run_segmentation_on_seed_data() -> None:
    result = segmenter.run_segmentation()
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    # Seed has 50 events ~15s apart within ~12.5 min → should produce 1 session.
    # Don't assert exact count; just assert no exception and list returned.


def main() -> None:
    test_idle_gap_split()
    test_midnight_boundary_split()
    test_dominant_app()
    test_empty_and_single()
    test_run_segmentation_on_seed_data()
    print("ALL SEGMENTER TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
