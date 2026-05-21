"""Vision module tests — standalone, no running sidecar required."""
import base64
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
import vision_ai
import vision_capture


def test_is_vision_available_when_disabled():
    db.set_setting("vision_backend", "")
    db.set_setting("vision_api_key", "")
    assert vision_ai.is_vision_available() is False
    print("Test 1 PASS: is_vision_available returns False when disabled")


def test_take_screenshot_returns_base64():
    result = vision_capture.take_screenshot()
    assert result is not None, "take_screenshot returned None"
    assert isinstance(result, str) and len(result) > 0
    decoded = base64.b64decode(result)
    assert decoded[:4] == b"\x89PNG", "screenshot is not a PNG"
    print("Test 2 PASS: take_screenshot returns valid base64 PNG")


def test_get_screen_size():
    size = vision_capture.get_screen_size()
    assert isinstance(size, dict)
    assert "width" in size and "height" in size
    assert isinstance(size["width"], int) and size["width"] > 0
    assert isinstance(size["height"], int) and size["height"] > 0
    print("Test 3 PASS: get_screen_size returns valid dimensions")


def test_find_element_no_backend_graceful():
    db.set_setting("vision_backend", "")
    db.set_setting("vision_api_key", "")
    result = vision_ai.find_element("fake_screenshot_b64", "the login button")
    assert isinstance(result, dict)
    assert result.get("ok") is False
    print("Test 4 PASS: find_element returns ok=False without raising when no backend")


def test_set_vision_config_ipc_roundtrip():
    _sidecar_dir = os.path.dirname(os.path.abspath(__file__))

    def ipc(msg: dict) -> dict:
        proc = subprocess.run(
            ["py", os.path.join(_sidecar_dir, "main.py")],
            input=json.dumps(msg) + "\n",
            capture_output=True,
            text=True,
            timeout=10,
        )
        for line in proc.stdout.strip().splitlines():
            line = line.strip()
            if line:
                return json.loads(line)
        raise RuntimeError(f"no response; stderr={proc.stderr[:200]}")

    resp = ipc({"type": "set_vision_config", "backend": "claude", "api_key": "test-key-123"})
    assert resp.get("type") == "ok", f"expected ok, got {resp}"

    resp2 = ipc({"type": "check_vision"})
    assert resp2.get("type") == "vision_status"
    assert resp2.get("backend") == "claude", f"expected claude, got {resp2.get('backend')}"

    ipc({"type": "set_vision_config", "backend": "", "api_key": ""})
    print("Test 5 PASS: set_vision_config IPC round-trip")


if __name__ == "__main__":
    test_is_vision_available_when_disabled()
    test_take_screenshot_returns_base64()
    test_get_screen_size()
    test_find_element_no_backend_graceful()
    test_set_vision_config_ipc_roundtrip()
    print("\nALL VISION TESTS PASSED")
