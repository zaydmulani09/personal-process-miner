"""
Test suite for accessibility.py, text_ai.py, and db migration 7.
All tests are offline-safe.
"""
import os
import sys
import sqlite3
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_1_get_screen_tree_never_raises():
    """get_screen_tree returns dict with window_title key OR {"ok": False} — never raises."""
    from accessibility import get_screen_tree
    result = get_screen_tree()
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    # Must have either ok=True with window_title, or ok=False with error
    if result.get("ok", True):
        assert "window_title" in result, f"ok=True but no window_title: {result}"
    else:
        assert "error" in result, f"ok=False but no error: {result}"
    print("  Test 1 PASSED: get_screen_tree never raises")


def test_2_tree_to_text_format():
    """tree_to_text with a mock tree returns non-empty string containing 'Window:'"""
    from accessibility import tree_to_text
    mock_tree = {
        "ok": True,
        "window_title": "Notepad",
        "window_rect": {"left": 0, "top": 0, "right": 800, "bottom": 600},
        "elements": [
            {
                "name": "File",
                "control_type": "MenuItem",
                "center": {"x": 50, "y": 30},
                "rect": {"left": 0, "top": 0, "right": 100, "bottom": 60},
                "enabled": True,
                "visible": True,
                "value": "",
            }
        ],
    }
    text = tree_to_text(mock_tree)
    assert isinstance(text, str) and len(text) > 0, "tree_to_text returned empty"
    assert "Window:" in text, f"'Window:' not in text: {text[:100]}"
    assert "Notepad" in text, f"'Notepad' not in text: {text[:100]}"
    print("  Test 2 PASSED: tree_to_text produces correct format")


def test_3_find_element_by_description():
    """find_element_by_description finds element by partial name match."""
    from accessibility import find_element_by_description
    mock_tree = {
        "ok": True,
        "window_title": "Test",
        "window_rect": {"left": 0, "top": 0, "right": 800, "bottom": 600},
        "elements": [
            {"name": "Save Button", "control_type": "Button", "center": {"x": 100, "y": 200}, "enabled": True, "visible": True, "value": ""},
            {"name": "Open File", "control_type": "Button", "center": {"x": 200, "y": 200}, "enabled": True, "visible": True, "value": ""},
        ],
    }
    result = find_element_by_description("save", mock_tree)
    assert result is not None, "Expected to find 'save' element"
    assert result["name"] == "Save Button", f"Wrong element: {result}"

    result2 = find_element_by_description("open file", mock_tree)
    assert result2 is not None, "Expected to find 'open file' element"
    assert result2["name"] == "Open File", f"Wrong element: {result2}"

    result3 = find_element_by_description("nonexistent xyz123", mock_tree)
    assert result3 is None, f"Expected None for nonexistent, got: {result3}"
    print("  Test 3 PASSED: find_element_by_description works correctly")


def test_4_test_connection_invalid_key():
    """test_connection with invalid key returns {"ok": False} for all 5 backends — never raises."""
    from text_ai import test_connection
    backends = ["claude", "openai", "groq", "gemini", "grok"]
    for backend in backends:
        try:
            result = test_connection(backend, "invalid_key_12345")
            assert isinstance(result, dict), f"Expected dict for {backend}"
            assert result.get("ok") is False, f"Expected ok=False for {backend} with invalid key, got: {result}"
        except Exception as exc:
            raise AssertionError(f"test_connection raised for {backend}: {exc}")
    print("  Test 4 PASSED: test_connection returns ok=False for all backends with invalid key")


def test_5_plan_automation_no_ai():
    """plan_automation with no AI configured returns {"ok": False} gracefully."""
    # Temporarily use an in-memory DB without ai_backend set
    import db as db_module
    import text_ai as tai_module

    # Save original _get_config and replace
    original_get_config = tai_module._get_config

    def mock_get_config():
        return "", ""

    tai_module._get_config = mock_get_config
    try:
        result = tai_module.plan_automation("click save button", "Window: Notepad (800x600)")
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert result.get("ok") is False, f"Expected ok=False when AI not configured: {result}"
    finally:
        tai_module._get_config = original_get_config
    print("  Test 5 PASSED: plan_automation returns ok=False gracefully when no AI configured")


def test_6_db_migration_7():
    """DB migration 7 copies vision_api_key_groq -> ai_api_key_groq."""
    import db as db_module

    # Use an in-memory DB
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Create privacy_settings table
    conn.execute(
        """CREATE TABLE privacy_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    now = datetime.now(timezone.utc).isoformat()
    # Insert old vision key
    conn.execute(
        "INSERT INTO privacy_settings (key, value, updated_at) VALUES (?, ?, ?)",
        ("vision_api_key_groq", "gsk_test_key", now),
    )
    conn.execute(
        "INSERT INTO privacy_settings (key, value, updated_at) VALUES (?, ?, ?)",
        ("vision_backend", "groq", now),
    )
    conn.commit()

    # Run migration 7
    db_module._run_migration_7(conn, now)

    # Check new keys were created
    row = conn.execute("SELECT value FROM privacy_settings WHERE key = 'ai_api_key_groq'").fetchone()
    assert row is not None, "ai_api_key_groq not created by migration 7"
    assert row[0] == "gsk_test_key", f"Wrong value for ai_api_key_groq: {row[0]}"

    row_backend = conn.execute("SELECT value FROM privacy_settings WHERE key = 'ai_backend'").fetchone()
    assert row_backend is not None, "ai_backend not created by migration 7"
    assert row_backend[0] == "groq", f"Wrong value for ai_backend: {row_backend[0]}"

    # Ensure running migration again does NOT overwrite an existing ai_api_key_groq
    conn.execute(
        "UPDATE privacy_settings SET value = 'existing_key' WHERE key = 'ai_api_key_groq'"
    )
    conn.commit()
    db_module._run_migration_7(conn, now)
    row2 = conn.execute("SELECT value FROM privacy_settings WHERE key = 'ai_api_key_groq'").fetchone()
    assert row2[0] == "existing_key", f"Migration 7 overwrote existing ai_api_key_groq: {row2[0]}"

    conn.close()
    print("  Test 6 PASSED: DB migration 7 copies vision keys to ai keys correctly")


if __name__ == "__main__":
    print("Running accessibility & text AI tests...")
    tests = [
        test_1_get_screen_tree_never_raises,
        test_2_tree_to_text_format,
        test_3_find_element_by_description,
        test_4_test_connection_invalid_key,
        test_5_plan_automation_no_ai,
        test_6_db_migration_7,
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
