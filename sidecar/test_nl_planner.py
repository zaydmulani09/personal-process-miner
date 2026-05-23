"""NL planner tests — standalone, no running sidecar required."""
import json
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
import text_ai
import accessibility
import nl_planner


def test_parse_instruction_no_vision():
    # Ensure AI is not configured
    with patch("nl_planner.is_ai_available", return_value=False):
        result = nl_planner.parse_instruction("open Discord and say hello")
    assert result.get("ok") is False
    assert "error" in result
    print("Test 1 PASS: parse_instruction returns ok=False when AI not available")


def test_refine_plan_empty_steps_no_raise():
    with patch("nl_planner.is_ai_available", return_value=False):
        result = nl_planner.refine_plan("open Discord", [], "add a wait step")
    assert isinstance(result, dict)
    assert "steps" in result
    print("Test 2 PASS: refine_plan with empty steps returns valid dict without raising")


def test_save_nl_automation_returns_int_id():
    steps = [{"type": "click", "description": "Click Discord icon"}]
    automation_id = nl_planner.save_nl_automation(
        "open discord",
        steps,
        "Open Discord and navigate to channel",
    )
    assert isinstance(automation_id, int)
    assert automation_id > 0
    print(f"Test 3 PASS: save_nl_automation returns integer id={automation_id}")


def test_saved_automation_source_is_nl_builder():
    steps = [{"type": "type", "description": "Type message", "value": "hello"}]
    automation_id = nl_planner.save_nl_automation(
        "type hello in slack",
        steps,
        "Type hello in Slack",
    )
    automation = db.get_automation_by_id(automation_id)
    assert automation is not None
    assert automation["script_type"] == "nl_builder"
    stored_steps = json.loads(automation["script_body"])
    assert isinstance(stored_steps, list)
    assert len(stored_steps) == 1
    print("Test 4 PASS: saved automation has script_type='nl_builder' in DB")


def test_parse_instruction_returns_nl_plan_shape():
    import json as _json
    mock_steps = [
        {"action": "focus_window", "target": {"name": "", "control_type": "", "automation_id": "", "window_title_contains": "Discord"}, "value": "", "key": "", "reason": "Focus Discord"},
        {"action": "type", "target": {"name": "message box", "control_type": "Edit", "automation_id": "", "window_title_contains": "Discord"}, "value": "hello", "key": "", "reason": "Type hello"},
    ]
    mock_tree = {
        "ok": True,
        "window_title": "Desktop",
        "elements": [],
    }

    with patch("nl_planner.is_ai_available", return_value=True), \
         patch("nl_planner.get_window_tree", return_value=mock_tree), \
         patch("nl_planner._call_ai", return_value=_json.dumps(mock_steps)):
        result = nl_planner.parse_instruction("open discord and say hello")

    assert result.get("ok") is True, f"expected ok=True, got {result}"
    assert "steps" in result
    assert "summary" in result
    assert isinstance(result["steps"], list)
    assert len(result["steps"]) == 2
    print("Test 5 PASS: parse_instruction returns nl_plan shape when AI mocked")


if __name__ == "__main__":
    test_parse_instruction_no_vision()
    test_refine_plan_empty_steps_no_raise()
    test_save_nl_automation_returns_int_id()
    test_saved_automation_source_is_nl_builder()
    test_parse_instruction_returns_nl_plan_shape()
    print("\nALL NL PLANNER TESTS PASSED")
