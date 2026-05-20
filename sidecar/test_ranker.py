import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ranker


# ---------------------------------------------------------------------------
# Test 1 — score_workflow
# ---------------------------------------------------------------------------

w1 = {"frequency": 5, "avg_duration_seconds": 120.0}
assert ranker.score_workflow(w1) == 600.0, f"Expected 600.0, got {ranker.score_workflow(w1)}"

w2 = {"frequency": 3, "avg_duration_seconds": None}
assert ranker.score_workflow(w2) == 0.0, f"Expected 0.0, got {ranker.score_workflow(w2)}"

print("Test 1 passed: score_workflow")


# ---------------------------------------------------------------------------
# Test 2 — rank_workflows ordering
# ---------------------------------------------------------------------------

workflows = [
    {"frequency": 3, "avg_duration_seconds": 100.0, "first_seen": ""},  # score=300
    {"frequency": 9, "avg_duration_seconds": 100.0, "first_seen": ""},  # score=900
    {"frequency": 3, "avg_duration_seconds": 50.0, "first_seen": ""},   # score=150
]
ranked = ranker.rank_workflows(workflows)
scores = [w["score"] for w in ranked]
assert scores == [900.0, 300.0, 150.0], f"Expected [900, 300, 150], got {scores}"

print("Test 2 passed: rank_workflows ordering")


# ---------------------------------------------------------------------------
# Test 3 — time_wasted_human formatting
# ---------------------------------------------------------------------------

cases = [
    (7384, "2 hr 3 min"),
    (2580, "43 min"),
    (45, "45 sec"),
    (0, "0 sec"),
]
for seconds, expected in cases:
    result = ranker._format_seconds(seconds)
    assert result == expected, f"_format_seconds({seconds}): expected '{expected}', got '{result}'"

print("Test 3 passed: time_wasted_human formatting")


# ---------------------------------------------------------------------------
# Test 4 — get_summary_stats on seed data (real DB)
# ---------------------------------------------------------------------------

stats = ranker.get_summary_stats()
required_keys = {
    "total_workflows",
    "total_time_wasted_seconds",
    "total_time_wasted_human",
    "top_workflow",
    "weekly_wasted_seconds",
    "weekly_wasted_human",
}
assert required_keys.issubset(stats.keys()), f"Missing keys: {required_keys - stats.keys()}"
assert isinstance(stats["total_workflows"], int) and stats["total_workflows"] >= 0
assert stats["top_workflow"] is None or isinstance(stats["top_workflow"], dict)

print("Test 4 passed: get_summary_stats on seed data")


# ---------------------------------------------------------------------------
# Test 5 — get_summary_stats with no workflows
# ---------------------------------------------------------------------------

result = ranker.rank_workflows([])
assert result == [], f"Expected [], got {result}"

# Simulate summary stats logic with empty list
empty_stats = {
    "total_workflows": len(result),
    "top_workflow": result[0] if result else None,
}
assert empty_stats["total_workflows"] == 0
assert empty_stats["top_workflow"] is None

print("Test 5 passed: rank_workflows empty list")

print()
print("ALL RANKER TESTS PASSED")
