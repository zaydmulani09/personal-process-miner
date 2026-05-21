"""Vision replay tests — standalone, no running sidecar required."""
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
import vision_ai
import vision_capture
import vision_replay


_SAMPLE_STEPS = [
    {"type": "click", "x": 100, "y": 200, "description": "submit button"},
    {"type": "keypress", "key": "enter"},
    {"type": "type", "x": 50, "y": 80, "description": "", "value": "hello"},
]


def test_describe_replay_plan_step_count_and_types():
    db.set_setting("vision_backend", "")
    db.set_setting("vision_api_key", "")
    result = vision_replay.describe_replay_plan(_SAMPLE_STEPS)
    assert "plan" in result
    assert len(result["plan"]) == 3
    assert result["plan"][0]["type"] == "click"
    assert result["plan"][1]["type"] == "keypress"
    assert result["plan"][2]["type"] == "type"
    print("Test 1 PASS: describe_replay_plan returns correct step count and types")


def test_will_use_vision_false_when_not_configured():
    db.set_setting("vision_backend", "")
    db.set_setting("vision_api_key", "")
    result = vision_replay.describe_replay_plan(_SAMPLE_STEPS)
    for item in result["plan"]:
        assert item["will_use_vision"] is False, f"step {item['step']} has will_use_vision=True unexpectedly"
    print("Test 2 PASS: will_use_vision is False when vision not configured")


def test_replay_step_vision_false_uses_recorded_coords():
    step = {"type": "click", "x": 150, "y": 250, "description": "some button"}
    with patch("pyautogui.click") as mock_click:
        result = vision_replay.replay_step(step, use_vision=False)
    assert result["ok"] is True
    assert result["method"] == "recorded"
    mock_click.assert_called_once_with(150, 250)
    print("Test 3 PASS: replay_step use_vision=False falls back to recorded coords, method='recorded'")


def test_replay_session_empty_steps():
    result = vision_replay.replay_session([], use_vision=False, verify_each=False)
    assert result["ok"] is True
    assert result["steps_completed"] == 0
    assert result["total_steps"] == 0
    assert result["results"] == []
    print("Test 4 PASS: replay_session empty steps returns ok=True, steps_completed=0")


def test_replay_session_stops_on_failed_verification():
    steps = [{"type": "click", "x": 100, "y": 200, "description": "submit button"}]

    mock_verify = MagicMock(return_value={
        "confidence": 0.1,
        "observation": "nothing happened",
        "success": False,
    })

    with patch("pyautogui.click"), \
         patch.object(vision_capture, "take_screenshot", return_value="fakeb64=="), \
         patch.object(vision_ai, "verify_action", mock_verify):
        result = vision_replay.replay_session(steps, use_vision=False, verify_each=True)

    assert result["ok"] is False, f"expected ok=False, got {result}"
    assert result.get("failed_at") == 0
    assert result.get("reason") == "verification failed"
    print("Test 5 PASS: replay_session stops at step 0 when verify_action returns confidence=0.1")


if __name__ == "__main__":
    test_describe_replay_plan_step_count_and_types()
    test_will_use_vision_false_when_not_configured()
    test_replay_step_vision_false_uses_recorded_coords()
    test_replay_session_empty_steps()
    test_replay_session_stops_on_failed_verification()
    print("\nALL VISION REPLAY TESTS PASSED")
