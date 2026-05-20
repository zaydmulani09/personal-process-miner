"""Scheduler module unit tests."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scheduler import get_platform, list_scheduled, schedule_automation, unschedule_automation
from main import is_script_safe

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
SKIP = "\033[33mSKIP\033[0m"

failures = 0


def assert_true(cond: bool, msg: str) -> None:
    global failures
    if cond:
        print(f"  {PASS} {msg}")
    else:
        print(f"  {FAIL} {msg}")
        failures += 1


# Test 1 — get_platform
print("Test 1 — get_platform")
pf = get_platform()
assert_true(pf in ("windows", "darwin", "linux"), f"platform is one of expected values (got {pf!r})")

# Test 2 — schedule_automation (Windows-only)
print("Test 2 — schedule_automation")
if pf == "windows":
    dummy_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "__init__.py"))
    result = schedule_automation(
        automation_id=9999,
        name="test_ppm_sched_unit",
        script_path=dummy_script,
        schedule={"frequency": "daily", "time": "09:00", "day_of_week": None},
    )
    assert_true(isinstance(result, dict), "returns a dict")
    assert_true("ok" in result, "result has 'ok' key")
    if not result.get("ok"):
        assert_true(isinstance(result.get("error"), str), "error is a string on failure")
    else:
        assert_true(result.get("platform") == "windows", "platform is windows")
else:
    print(f"  {SKIP} (not Windows)")

# Test 3 — unschedule_automation (Windows-only)
print("Test 3 — unschedule_automation")
if pf == "windows":
    result = unschedule_automation("test_ppm_sched_unit")
    assert_true(isinstance(result, dict), "returns a dict")
    assert_true("ok" in result, "result has 'ok' key")
else:
    print(f"  {SKIP} (not Windows)")

# Test 4 — list_scheduled
print("Test 4 — list_scheduled")
result = list_scheduled()
assert_true(isinstance(result, list), "returns a list")
for item in result:
    assert_true("name" in item, "each item has 'name'")
    assert_true("schedule_id" in item, "each item has 'schedule_id'")

# Test 5 — is_script_safe
print("Test 5 — is_script_safe")
assert_true(
    not is_script_safe("import os; os.system('echo bad')"),
    "os.system detected as unsafe",
)
assert_true(
    not is_script_safe("import subprocess; subprocess.run(['ls'])"),
    "subprocess detected as unsafe",
)
assert_true(
    not is_script_safe("shutil.rmtree('/tmp/foo')"),
    "shutil.rmtree detected as unsafe",
)
assert_true(
    not is_script_safe("x = __import__('os')"),
    "__import__ detected as unsafe",
)
assert_true(
    is_script_safe("import pyautogui\npyautogui.click(100, 200)"),
    "pyautogui script is safe",
)
assert_true(
    is_script_safe("from playwright.sync_api import sync_playwright\nwith sync_playwright() as p: pass"),
    "playwright script is safe",
)

if failures == 0:
    print("\nALL SCHEDULER TESTS PASSED")
    sys.exit(0)
else:
    print(f"\n{failures} test(s) FAILED")
    sys.exit(1)
