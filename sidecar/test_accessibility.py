"""
Test suite for accessibility.py, text_ai.py, and db migration 7.
All tests are offline-safe and headless-safe.
"""
import os
import sys
import sqlite3
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_1_get_window_tree_never_raises():
    """get_window_tree returns dict with elements key OR {"ok": False} — never raises."""
    from accessibility import get_window_tree
    result = get_window_tree()
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    if result.get("ok", True):
        assert "elements" in result, f"ok=True but no elements key: {result}"
    else:
        assert "error" in result, f"ok=False but no error: {result}"
    print("  Test 1 PASSED: get_window_tree never raises")


def test_2_tree_to_text_format():
    """tree_to_text with mock tree returns string with Window: prefix."""
    from accessibility import tree_to_text
    mock_tree = {
        "ok": True,
        "window_title": "Notepad",
        "window_rect": {"left": 0, "top": 0, "right": 800, "bottom": 600},
        "elements": [
            {
                "name": "File",
                "control_type": "MenuItem",
                "automation_id": "fileMenu",
                "class_name": "MenuItem",
                "center": {"x": 50, "y": 30},
                "rect": {"left": 0, "top": 0, "right": 100, "bottom": 60},
                "enabled": True,
                "visible": True,
            }
        ],
    }
    text = tree_to_text(mock_tree)
    assert isinstance(text, str) and len(text) > 0, "tree_to_text returned empty"
    assert text.startswith("Window:"), f"text does not start with 'Window:': {text[:60]}"
    assert "Notepad" in text, f"'Notepad' not in text: {text[:100]}"
    print("  Test 2 PASSED: tree_to_text produces correct format")


def test_3_execute_action_no_pywinauto():
    """execute_action with _HAS_PYWINAUTO=False returns {"ok": False} gracefully."""
    import accessibility as acc_mod
    original = acc_mod._HAS_PYWINAUTO
    acc_mod._HAS_PYWINAUTO = False
    try:
        result = acc_mod.execute_action({
            "action": "click",
            "target": {"name": "OK", "control_type": "Button", "window_title_contains": "Test"},
            "value": "",
            "key": "",
            "reason": "test",
        })
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert result.get("ok") is False, f"Expected ok=False without pywinauto: {result}"
    finally:
        acc_mod._HAS_PYWINAUTO = original
    print("  Test 3 PASSED: execute_action returns ok=False when pywinauto unavailable")


def test_4_parse_instruction_no_ai():
    """parse_instruction with no AI configured returns {"ok": False} gracefully."""
    import nl_planner
    with patch("nl_planner.is_ai_available", return_value=False):
        result = nl_planner.parse_instruction("click save button")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("ok") is False, f"Expected ok=False when AI not configured: {result}"
    assert "error" in result
    print("  Test 4 PASSED: parse_instruction returns ok=False when no AI configured")


def test_5_execute_instruction_no_ai():
    """execute_instruction with no AI configured returns {"ok": False} gracefully."""
    import nl_planner
    with patch("nl_planner.is_ai_available", return_value=False):
        result = nl_planner.execute_instruction("click save button")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("ok") is False, f"Expected ok=False when AI not configured: {result}"
    print("  Test 5 PASSED: execute_instruction returns ok=False when no AI configured")


def test_6_execute_action_missing_key():
    """execute_action with missing action key returns {"ok": False}."""
    from accessibility import execute_action
    result = execute_action({"target": {"name": "OK"}, "value": ""})
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("ok") is False, f"Expected ok=False for missing action key: {result}"
    assert "error" in result
    print("  Test 6 PASSED: execute_action returns ok=False for missing action key")


def test_7_db_migration_7():
    """DB migration 7 copies vision_api_key_groq -> ai_api_key_groq."""
    import db as db_module

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE privacy_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO privacy_settings (key, value, updated_at) VALUES (?, ?, ?)",
        ("vision_api_key_groq", "gsk_test_key", now),
    )
    conn.execute(
        "INSERT INTO privacy_settings (key, value, updated_at) VALUES (?, ?, ?)",
        ("vision_backend", "groq", now),
    )
    conn.commit()

    db_module._run_migration_7(conn, now)

    row = conn.execute("SELECT value FROM privacy_settings WHERE key = 'ai_api_key_groq'").fetchone()
    assert row is not None, "ai_api_key_groq not created by migration 7"
    assert row[0] == "gsk_test_key", f"Wrong value for ai_api_key_groq: {row[0]}"

    row_backend = conn.execute("SELECT value FROM privacy_settings WHERE key = 'ai_backend'").fetchone()
    assert row_backend is not None, "ai_backend not created by migration 7"
    assert row_backend[0] == "groq", f"Wrong value for ai_backend: {row_backend[0]}"

    conn.execute("UPDATE privacy_settings SET value = 'existing_key' WHERE key = 'ai_api_key_groq'")
    conn.commit()
    db_module._run_migration_7(conn, now)
    row2 = conn.execute("SELECT value FROM privacy_settings WHERE key = 'ai_api_key_groq'").fetchone()
    assert row2[0] == "existing_key", f"Migration 7 overwrote existing ai_api_key_groq: {row2[0]}"

    conn.close()
    print("  Test 7 PASSED: DB migration 7 copies vision keys to ai keys correctly")


if __name__ == "__main__":
    print("Running accessibility & text AI tests...")
    tests = [
        test_1_get_window_tree_never_raises,
        test_2_tree_to_text_format,
        test_3_execute_action_no_pywinauto,
        test_4_parse_instruction_no_ai,
        test_5_execute_instruction_no_ai,
        test_6_execute_action_missing_key,
        test_7_db_migration_7,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as exc:
            print(f"  FAILED {test.__name__}: {exc}")
            failed += 1

    print(f"\n{passed}/{len(tests)} tests passed, {failed} failed")
    if failed == 0:
        print("ALL ACCESSIBILITY TESTS PASSED")
    else:
        sys.exit(1)
