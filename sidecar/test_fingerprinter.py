"""Standalone fingerprinter test — run with: py sidecar/test_fingerprinter.py"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fingerprinter as fp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE = datetime(2026, 5, 19, 10, 0, 0, tzinfo=timezone.utc)


def _evt(app: str, offset_min: float = 0, id: int = 0) -> dict:
    return {
        "id": id,
        "timestamp": (_BASE + timedelta(minutes=offset_min)).isoformat(),
        "app_name": app,
        "event_type": "key_press",
    }


def _sess(started_at: datetime, duration: float = 120.0) -> dict:
    return {
        "started_at": started_at.isoformat(),
        "ended_at": (started_at + timedelta(seconds=duration)).isoformat(),
        "duration_seconds": duration,
        "event_count": 5,
        "dominant_app": "Chrome",
        "apps_seen": ["Chrome"],
        "event_ids": [],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_extract_app_sequence() -> None:
    evts = [
        _evt("Chrome"), _evt("Chrome"), _evt("VSCode"),
        _evt("VSCode"), _evt("VSCode"), _evt("Slack"),
    ]
    result = fp.extract_app_sequence(evts)
    assert result == ["Chrome", "VSCode", "Slack"], f"Got {result}"


def test_sliding_windows() -> None:
    seq = ["A", "B", "C", "D", "E"]
    windows = fp.sliding_windows(seq, min_len=3, max_len=4)
    assert ("A", "B", "C") in windows, "Missing (A,B,C)"
    assert ("B", "C", "D") in windows, "Missing (B,C,D)"
    assert ("A", "B", "C", "D") in windows, "Missing (A,B,C,D)"
    assert ("B", "C", "D", "E") in windows, "Missing (B,C,D,E)"


def test_fingerprint_stability() -> None:
    h1 = fp.fingerprint(("Chrome", "VSCode", "Slack"))
    h2 = fp.fingerprint(("Chrome", "VSCode", "Slack"))
    assert h1 == h2, "Same sequence must hash to same value"
    h3 = fp.fingerprint(("Chrome", "Slack", "VSCode"))
    assert h1 != h3, "Different sequences must hash differently"


def test_edit_distance() -> None:
    assert fp.edit_distance(["A", "B", "C"], ["A", "B", "C"]) == 0
    assert fp.edit_distance(["A", "B", "C"], ["A", "X", "C"]) == 1
    assert fp.edit_distance(["A", "B"], ["A", "B", "C"]) == 1


def test_find_patterns_frequency() -> None:
    """3 sessions each with Chrome→VSCode→Slack should produce 1 pattern, freq=3."""
    sessions = [
        _sess(_BASE + timedelta(hours=i)) for i in range(3)
    ]
    evts = [_evt("Chrome"), _evt("VSCode"), _evt("Slack")]
    events_by_session = {0: evts, 1: evts, 2: evts}

    patterns = fp.find_patterns(sessions, events_by_session, min_frequency=2)
    assert len(patterns) >= 1, f"Expected ≥1 pattern, got {len(patterns)}"
    top = patterns[0]
    assert top["frequency"] >= 3, f"Expected freq≥3, got {top['frequency']}"
    assert set(top["steps"]) >= {"Chrome", "VSCode", "Slack"}, (
        f"Expected steps to contain the 3 apps, got {top['steps']}"
    )


def test_find_patterns_min_frequency_filter() -> None:
    """1 session with unique sequence → no patterns at min_frequency=2."""
    sessions = [_sess(_BASE)]
    evts = [_evt("X"), _evt("Y"), _evt("Z")]
    events_by_session = {0: evts}

    patterns = fp.find_patterns(sessions, events_by_session, min_frequency=2)
    assert patterns == [], f"Expected [], got {patterns}"


def test_run_fingerprinting_on_real_db() -> None:
    """Should not raise and should return a list (may be empty on seed data)."""
    result = fp.run_fingerprinting()
    assert isinstance(result, list), f"Expected list, got {type(result)}"


def main() -> None:
    test_extract_app_sequence()
    test_sliding_windows()
    test_fingerprint_stability()
    test_edit_distance()
    test_find_patterns_frequency()
    test_find_patterns_min_frequency_filter()
    test_run_fingerprinting_on_real_db()
    print("ALL FINGERPRINTER TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
