"""Provider tests — standalone, no running sidecar required."""
import json
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
import vision_ai

_SIDECAR_DIR = os.path.dirname(os.path.abspath(__file__))


def _ipc(msg: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, os.path.join(_SIDECAR_DIR, "main.py")],
        input=json.dumps(msg) + "\n",
        capture_output=True,
        text=True,
        timeout=15,
    )
    for line in proc.stdout.strip().splitlines():
        line = line.strip()
        if line:
            return json.loads(line)
    raise RuntimeError(f"no response; stderr={proc.stderr[:300]}")


def test_get_available_backends():
    backends = vision_ai.get_available_backends()
    assert isinstance(backends, list), "backends should be list"
    assert set(backends) == {"claude", "openai", "groq", "gemini", "grok"}, f"expected all 5, got {backends}"
    assert len(backends) == 5
    print("Test 1 PASS: get_available_backends returns all 5 backends")


def test_is_vision_available_no_backend():
    db.set_setting("ai_backend", "")
    db.set_setting("vision_backend", "")
    result = vision_ai.is_vision_available()
    assert result is False, f"expected False, got {result}"
    print("Test 2 PASS: is_vision_available returns False when no backend set")


def test_connection_invalid_key_no_raise():
    """Patch _call_backend to raise auth error; verify test_connection returns ok=False for all 5 backends."""
    for backend in ["claude", "openai", "groq", "gemini", "grok"]:
        with patch.object(vision_ai, "_call_backend", side_effect=Exception("invalid api key")):
            result = vision_ai.test_connection(backend, "bad-key-xyz")
        assert isinstance(result, dict), f"{backend}: result should be dict"
        assert result.get("ok") is False, f"{backend}: expected ok=False, got {result}"
        assert "error" in result, f"{backend}: missing error key"
    print("Test 3 PASS: test_connection with invalid key returns ok=False for all 5 backends without raising")


def test_set_vision_config_namespaced_key():
    """IPC set_ai_config stores key under ai_api_key_<backend>."""
    resp = _ipc({"type": "set_ai_config", "backend": "gemini", "api_key": "AIza-test-key-999"})
    assert resp.get("type") == "ok", f"expected ok, got {resp}"

    # Read key directly from DB to verify namespaced storage
    stored = db.get_setting("ai_api_key_gemini", "")
    assert stored == "AIza-test-key-999", f"expected 'AIza-test-key-999', got '{stored}'"

    backend = db.get_setting("ai_backend", "")
    assert backend == "gemini", f"expected 'gemini', got '{backend}'"

    # Cleanup
    _ipc({"type": "set_ai_config", "backend": "", "api_key": ""})
    print("Test 4 PASS: set_ai_config stores key under namespaced key (ai_api_key_gemini)")


def test_switching_backend_updates_check_vision():
    """Switching active backend updates check_ai response correctly."""
    _ipc({"type": "set_ai_config", "backend": "openai", "api_key": "sk-test-openai-456"})
    resp = _ipc({"type": "check_ai"})
    assert resp.get("type") == "ai_status"
    assert resp.get("backend") == "openai", f"expected openai, got {resp.get('backend')}"
    assert "backends" in resp, "backends list missing from check_ai response"
    assert set(resp["backends"]) == {"claude", "openai", "groq", "gemini", "grok"}

    _ipc({"type": "set_ai_config", "backend": "groq", "api_key": "gsk-test-groq-789"})
    resp2 = _ipc({"type": "check_ai"})
    assert resp2.get("backend") == "groq", f"expected groq, got {resp2.get('backend')}"

    # Cleanup
    _ipc({"type": "set_ai_config", "backend": "", "api_key": ""})
    print("Test 5 PASS: switching active backend updates check_ai response correctly")


def test_all_error_types_handled_without_raising():
    """All 5 error categories return structured dict without raising."""
    error_cases = [
        ("invalid api key", "invalid_api_key"),
        ("rate limit exceeded", "rate_limited"),
        ("too many requests 429", "rate_limited"),
        ("connection refused", "network_error"),
        ("not support vision", "vision_not_supported"),
    ]
    for exc_msg, expected_err in error_cases:
        with patch.object(vision_ai, "_call_backend", side_effect=Exception(exc_msg)):
            result = vision_ai.test_connection("claude", "any-key")
        assert isinstance(result, dict), f"result should be dict for '{exc_msg}'"
        assert result.get("ok") is False, f"expected ok=False for '{exc_msg}'"
        assert result.get("error") == expected_err, (
            f"expected error='{expected_err}' for '{exc_msg}', got '{result.get('error')}'"
        )
    print("Test 6 PASS: all 5 error types handled without raising")


if __name__ == "__main__":
    test_get_available_backends()
    test_is_vision_available_no_backend()
    test_connection_invalid_key_no_raise()
    test_set_vision_config_namespaced_key()
    test_switching_backend_updates_check_vision()
    test_all_error_types_handled_without_raising()
    print("\nALL PROVIDER TESTS PASSED")
