"""Standalone macro recorder tests — run with: py sidecar/test_macro_recorder.py"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db
import macro_recorder


# ---------------------------------------------------------------------------
# Test 1 — start/stop recording
# ---------------------------------------------------------------------------

result = macro_recorder.start_recording(None)
assert result.get("ok") is True, f"start_recording failed: {result}"
assert result.get("state") == "recording", f"Expected recording state: {result}"

time.sleep(0.1)

result = macro_recorder.stop_recording()
assert result.get("ok") is True, f"stop_recording failed: {result}"
assert result.get("state") == "stopped", f"Expected stopped state: {result}"

print("Test 1 passed: start_recording / stop_recording")


# ---------------------------------------------------------------------------
# Test 2 — double-start guard
# ---------------------------------------------------------------------------

result = macro_recorder.start_recording(None)
assert result.get("ok") is True, f"First start failed: {result}"

result2 = macro_recorder.start_recording(None)
assert result2.get("ok") is False, f"Second start should return ok=False: {result2}"
assert "error" in result2, f"Second start should include error key: {result2}"

macro_recorder.stop_recording()

print("Test 2 passed: double-start guard")


# ---------------------------------------------------------------------------
# Test 3 — generate_pyautogui_script with synthetic events
# ---------------------------------------------------------------------------

events = [
    {"type": "key_press",   "timestamp": 1000.0, "detail": "'a'",          "x": None, "y": None},
    {"type": "mouse_click", "timestamp": 1001.5, "detail": "Button.left",  "x": 100,  "y": 200},
    {"type": "mouse_move",  "timestamp": 1002.0, "detail": "move",         "x": 200,  "y": 300},
]
script = macro_recorder.generate_pyautogui_script(events, "Test Macro")
assert "import pyautogui" in script, f"Missing import pyautogui: {script}"
assert "pyautogui.FAILSAFE = True" in script, f"Missing FAILSAFE: {script}"
assert "pyautogui.click" in script or "pyautogui.press" in script, f"Missing action: {script}"

print("Test 3 passed: generate_pyautogui_script with events")


# ---------------------------------------------------------------------------
# Test 4 — empty events script
# ---------------------------------------------------------------------------

script_empty = macro_recorder.generate_pyautogui_script([], "Empty")
assert "# No events recorded" in script_empty, f"Missing no-events comment: {script_empty}"
assert "import pyautogui" in script_empty, f"Missing import in empty script: {script_empty}"

print("Test 4 passed: empty events script")


# ---------------------------------------------------------------------------
# Test 5 — save_macro writes file and DB row
# ---------------------------------------------------------------------------

macro_recorder._state["buffer"] = [
    {"type": "key_press",   "timestamp": 2000.0, "detail": "'x'",         "x": None, "y": None},
    {"type": "mouse_click", "timestamp": 2001.0, "detail": "Button.left", "x": 50,   "y": 75},
]

result = macro_recorder.save_macro("Test Macro", None)
assert result.get("ok") is True, f"save_macro failed: {result}"
assert os.path.exists(result["script_path"]), f"File not created: {result['script_path']}"

automation_id = result["automation_id"]
automations = db.get_automations()
matching = [a for a in automations if a["id"] == automation_id]
assert len(matching) == 1, f"Automation id={automation_id} not found in DB"

print("Test 5 passed: save_macro writes file and DB row")

print()
print("ALL MACRO RECORDER TESTS PASSED")
