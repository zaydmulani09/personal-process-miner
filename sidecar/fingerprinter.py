import hashlib
import logging
from collections import Counter

import db
import segmenter


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


def extract_app_sequence(events: list[dict]) -> list[str]:
    """Collapse consecutive duplicate app names into a single-transition list."""
    result: list[str] = []
    for evt in events:
        app = evt.get("app_name") or ""
        if app and (not result or result[-1] != app):
            result.append(app)
    return result


def sliding_windows(
    sequence: list[str], min_len: int = 3, max_len: int = 8
) -> list[tuple]:
    """All contiguous subsequences of length in [min_len, max_len]."""
    windows = []
    n = len(sequence)
    for length in range(min_len, min(max_len, n) + 1):
        for start in range(n - length + 1):
            windows.append(tuple(sequence[start : start + length]))
    return windows


def fingerprint(sequence: tuple) -> str:
    """Stable MD5 hex digest of the joined sequence."""
    raw = "|".join(sequence)
    return hashlib.md5(raw.encode()).hexdigest()


def edit_distance(a: list, b: list) -> int:
    """Standard Levenshtein edit distance between two lists."""
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


# ---------------------------------------------------------------------------
# Pattern detection
# ---------------------------------------------------------------------------


def find_patterns(
    sessions: list[dict],
    events_by_session: dict,
    min_frequency: int = 2,
) -> list[dict]:
    """
    Detect repeated N-step app-switch sequences across sessions.

    sessions          – list of session dicts (need started_at, duration_seconds)
    events_by_session – {session_index: [event dicts]} mapping
    """
    if not sessions:
        return []
    try:
        # Phase 1: extract windows per session, accumulate per-fingerprint counts.
        fp_to_seq: dict[str, list[str]] = {}
        fp_to_sess: dict[str, set[int]] = {}

        for i, _sess in enumerate(sessions):
            evts = events_by_session.get(i, [])
            seq = extract_app_sequence(evts)
            windows = sliding_windows(seq)
            seen = set()
            for w in windows:
                fp = fingerprint(w)
                if fp in seen:
                    continue
                seen.add(fp)
                fp_to_seq.setdefault(fp, list(w))
                fp_to_sess.setdefault(fp, set()).add(i)

        if not fp_to_seq:
            return []

        # Phase 2: fuzzy dedup — group fingerprints with edit distance ≤ 1.
        all_fps = list(fp_to_seq.keys())
        groups: list[set[str]] = []
        used: set[str] = set()

        for fp in all_fps:
            if fp in used:
                continue
            group: set[str] = {fp}
            used.add(fp)
            for other in all_fps:
                if other in used:
                    continue
                if edit_distance(fp_to_seq[fp], fp_to_seq[other]) <= 1:
                    group.add(other)
                    used.add(other)
            groups.append(group)

        # Phase 3: build pattern dicts, filter by min_frequency.
        patterns: list[dict] = []
        for group in groups:
            all_sess_idx: set[int] = set()
            for fp in group:
                all_sess_idx |= fp_to_sess[fp]

            frequency = len(all_sess_idx)
            if frequency < min_frequency:
                continue

            # Canonical sequence = from the fingerprint that appears in the most sessions.
            canonical_fp = max(group, key=lambda fp: len(fp_to_sess[fp]))
            canonical_seq = fp_to_seq[canonical_fp]

            valid_idx = [i for i in all_sess_idx if i < len(sessions)]
            starts = [sessions[i]["started_at"] for i in valid_idx]
            durations = [sessions[i].get("duration_seconds", 0.0) for i in valid_idx]
            avg_dur = sum(durations) / len(durations) if durations else 0.0

            patterns.append(
                {
                    "fingerprint": canonical_fp,
                    "steps": canonical_seq,
                    "frequency": frequency,
                    "avg_duration_seconds": avg_dur,
                    "first_seen": min(starts) if starts else "",
                    "last_seen": max(starts) if starts else "",
                    "step_count": len(canonical_seq),
                }
            )

        return sorted(patterns, key=lambda p: p["frequency"], reverse=True)

    except Exception:
        logging.exception("find_patterns error")
        return []


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------


def run_fingerprinting() -> list[dict]:
    """Segment events, detect patterns, upsert workflows, return patterns."""
    try:
        # Re-segment to get sessions with event_ids (DB sessions table lacks them).
        raw_events = db.get_recent_events(limit=10_000)
        sessions = segmenter.segment_events(raw_events)

        events_by_session: dict[int, list[dict]] = {}
        for i, sess in enumerate(sessions):
            ids = sess.get("event_ids", [])
            events_by_session[i] = db.get_events_by_ids(ids) if ids else []

        patterns = find_patterns(sessions, events_by_session)
        logging.info("Fingerprinting found %d pattern(s)", len(patterns))

        now = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat()

        for pat in patterns:
            db.upsert_workflow(
                {
                    "name": " → ".join(pat["steps"][:3])
                    + ("…" if len(pat["steps"]) > 3 else ""),
                    "fingerprint": pat["fingerprint"],
                    "steps": pat["steps"],
                    "frequency": pat["frequency"],
                    "avg_duration_seconds": pat["avg_duration_seconds"],
                    "first_seen": pat["first_seen"],
                    "last_seen": pat["last_seen"],
                    "created_at": now,
                }
            )

        return patterns

    except Exception:
        logging.exception("run_fingerprinting error")
        return []
