"""Standalone LLM explainer tests — run with: py sidecar/test_llm_explainer.py
All tests must pass without any live LLM backend running.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db
import llm_explainer


# ---------------------------------------------------------------------------
# Test 1 — is_llm_available when backend is empty
# ---------------------------------------------------------------------------

os.environ["PPM_LLM_BACKEND"] = ""
result = llm_explainer.is_llm_available()
assert result is False, f"Expected False when backend empty, got: {result}"

print("Test 1 passed: is_llm_available returns False when backend is empty")


# ---------------------------------------------------------------------------
# Test 2 — is_llm_available with invalid Ollama URL (must resolve in < 3s)
# ---------------------------------------------------------------------------

os.environ["PPM_LLM_BACKEND"] = "ollama"
os.environ["PPM_OLLAMA_URL"] = "http://localhost:19999"

t0 = time.time()
result = llm_explainer.is_llm_available()
elapsed = time.time() - t0

assert result is False, f"Expected False for unreachable Ollama, got: {result}"
assert elapsed < 5.0, f"is_llm_available took too long: {elapsed:.2f}s"

# Restore
os.environ["PPM_LLM_BACKEND"] = ""

print(f"Test 2 passed: is_llm_available returns False for invalid Ollama URL ({elapsed:.2f}s)")


# ---------------------------------------------------------------------------
# Test 3 — explain_script with backend disabled returns ok=False
# ---------------------------------------------------------------------------

os.environ["PPM_LLM_BACKEND"] = ""
result = llm_explainer.explain_script("import pyautogui", "pyautogui")
assert result.get("ok") is False, f"Expected ok=False when disabled, got: {result}"
assert "error" in result, f"Expected 'error' key in result: {result}"

print("Test 3 passed: explain_script returns ok=False when backend disabled")


# ---------------------------------------------------------------------------
# Test 4 — JSON fence stripping
# ---------------------------------------------------------------------------

fenced_inputs = [
    '```json\n{"explanation": "test", "improved_script": "code"}\n```',
    '```\n{"explanation": "test2", "improved_script": "code2"}\n```',
    '{"explanation": "no fences", "improved_script": "plain"}',
]

for fenced in fenced_inputs:
    stripped = llm_explainer._strip_fences(fenced)
    import json as _json
    parsed = _json.loads(stripped)
    assert "explanation" in parsed, f"Missing explanation in parsed: {parsed}"
    assert "improved_script" in parsed, f"Missing improved_script in parsed: {parsed}"

print("Test 4 passed: JSON fence stripping handles markdown code blocks and plain JSON")


# ---------------------------------------------------------------------------
# Test 5 — get_automation_by_id and update_automation_script
# ---------------------------------------------------------------------------

from datetime import datetime, timezone

automation_id = db.insert_automation({
    "workflow_id": None,
    "name": "Test LLM Automation",
    "script_type": "pyautogui",
    "script_body": "import pyautogui\n# original",
    "created_at": datetime.now(timezone.utc).isoformat(),
})

row = db.get_automation_by_id(automation_id)
assert row is not None, f"Expected automation row, got None for id={automation_id}"
assert row["id"] == automation_id
assert row["name"] == "Test LLM Automation"
assert row["script_body"] == "import pyautogui\n# original"

new_body = "import pyautogui\n# improved"
db.update_automation_script(automation_id, new_body)

updated = db.get_automation_by_id(automation_id)
assert updated is not None
assert updated["script_body"] == new_body, (
    f"Expected updated body, got: {updated['script_body']!r}"
)

print("Test 5 passed: get_automation_by_id and update_automation_script")

print()
print("ALL LLM EXPLAINER TESTS PASSED")
