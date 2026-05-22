"""Vision replay tests — standalone, no running sidecar required."""
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
import text_ai
import accessibility
import vision_replay


_SAMPLE_STEPS = [
    {"type": "click", "x": 100, "y": 200, "description": "submit button"},
    {"type": "keypress", "key": "enter"},
    {"type": "type", "x": 50, "y": 80, "description": "", "value": "hello"},
]


def test_describe_replay_plan_step_count_and_types():
    result = vision_replay.describe_replay_plan(_SAMPLE_STEPS)
    assert "plan" in result
    assert len(result["plan"]) == 3
    assert result["plan"][0]["type"] == "click"
    assert result["plan"][1]["type"] == "keypress"
    assert result["plan"][2]["type"] == "type"
    print("Test 1 PASS: describe_replay_plan returns correct step count and types")


def test_will_use_ai_false_when_not_configured():
    with patch("vision_replay.is_ai_available", return_value=False):
        result = vision_replay.describe_replay_plan(_SAMPLE_STEPS)
    for item in result["plan"]:
        assert item["will_use_ai"] is False, f"step {item['step']} has will_use_ai=True unexpectedly"
    print("Test 2 PASS: will_use_ai is False when AI not configured")


def test_replay_step_use_ai_false_uses_recorded_coords():
    step = {"type": "click", "x": 150, "y": 250, "description": "some button"}
    mock_pyautogui = MagicMock()
    mock_pyautogui.FAILSAFE = True
    mock_pyautogui.PAUSE = 0.05
    mock_pyautogui.click = MagicMock()
    with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}), \
         patch.object(vision_replay, "_PYAUTOGUI_OK", True), \
         patch.object(vision_replay, "pyautogui", mock_pyautogui):
        result = vision_replay.replay_step(step, use_ai=False)
    assert result["ok"] is True
    assert result["method"] == "recorded"
    mock_pyautogui.click.assert_called_once_with(150, 250)
    print("Test 3 PASS: replay_step use_ai=False falls back to recorded coords, method='recorded'")


def test_replay_session_empty_steps():
    result = vision_replay.replay_session([], use_ai=False, verify_each=False)
    assert result["ok"] is True
    assert result["steps_completed"] == 0
    assert result["total_steps"] == 0
    assert result["results"] == []
    print("Test 4 PASS: replay_session empty steps returns ok=True, steps_completed=0")


def test_replay_session_ok_with_use_ai_false():
    """replay_session with use_ai=False and verify_each=False completes successfully."""
    steps = [{"type": "click", "x": 100, "y": 200, "description": "submit button"}]
    mock_pyautogui = MagicMock()
    mock_pyautogui.click = MagicMock()
    with patch.object(vision_replay, "_PYAUTOGUI_OK", True), \
         patch.object(vision_replay, "pyautogui", mock_pyautogui):
        result = vision_replay.replay_session(steps, use_ai=False, verify_each=False)
    assert result["ok"] is True, f"expected ok=True, got {result}"
    assert result["steps_completed"] == 1
    print("Test 5 PASS: replay_session completes ok with use_ai=False")


if __name__ == "__main__":
    test_describe_replay_plan_step_count_and_types()
    test_will_use_ai_false_when_not_configured()
    test_replay_step_use_ai_false_uses_recorded_coords()
    test_replay_session_empty_steps()
    test_replay_session_ok_with_use_ai_false()
    print("\nALL VISION REPLAY TESTS PASSED")
