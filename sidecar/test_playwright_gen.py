"""Standalone playwright generator tests — run with: py sidecar/test_playwright_gen.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import playwright_gen


# ---------------------------------------------------------------------------
# Test 1 — is_browser_event
# ---------------------------------------------------------------------------

assert playwright_gen.is_browser_event({"app_name": "Google Chrome"}) is True
assert playwright_gen.is_browser_event({"app_name": "Mozilla Firefox"}) is True
assert playwright_gen.is_browser_event({"app_name": "Notepad"}) is False
assert playwright_gen.is_browser_event({"app_name": None}) is False
assert playwright_gen.is_browser_event({}) is False

print("Test 1 passed: is_browser_event")


# ---------------------------------------------------------------------------
# Test 2 — extract_url_from_title
# ---------------------------------------------------------------------------

assert playwright_gen.extract_url_from_title("My Page - https://example.com") == "https://example.com"
assert playwright_gen.extract_url_from_title("Dashboard - Google Chrome") is None
assert playwright_gen.extract_url_from_title("https://example.com - Google Chrome") == "https://example.com"
assert playwright_gen.extract_url_from_title("") is None
assert playwright_gen.extract_url_from_title(None) is None  # type: ignore[arg-type]

print("Test 2 passed: extract_url_from_title")


# ---------------------------------------------------------------------------
# Test 3 — classify_event
# ---------------------------------------------------------------------------

assert playwright_gen.classify_event({"event_type": "window_focus", "app_name": "Google Chrome"}) == "navigate"
assert playwright_gen.classify_event({"event_type": "window_focus", "app_name": "Notepad"}) == "unknown"
assert playwright_gen.classify_event({"event_type": "mouse_click"}) == "click"
assert playwright_gen.classify_event({"event_type": "key_press", "detail": "'a'"}) == "type"
assert playwright_gen.classify_event({"event_type": "key_press", "detail": "Key.space"}) == "unknown"
assert playwright_gen.classify_event({"event_type": "mouse_scroll"}) == "scroll"
assert playwright_gen.classify_event({"event_type": "unknown_type"}) == "unknown"

print("Test 3 passed: classify_event")


# ---------------------------------------------------------------------------
# Test 4 — group_keystrokes merges consecutive type events
# ---------------------------------------------------------------------------

events = [
    {"event_type": "key_press", "detail": "'h'", "timestamp": 1000.0},
    {"event_type": "key_press", "detail": "'i'", "timestamp": 1000.1},
    {"event_type": "mouse_click", "detail": "", "timestamp": 1001.0, "x": 10, "y": 20},
    {"event_type": "key_press", "detail": "'a'", "timestamp": 1002.0},
    {"event_type": "key_press", "detail": "'b'", "timestamp": 1004.5},  # gap > 2s — separate
]

grouped = playwright_gen.group_keystrokes(events)
# First two key presses should merge into "hi"
assert len(grouped) == 4, f"Expected 4 groups, got {len(grouped)}: {grouped}"
assert grouped[0]["detail"] == "hi", f"Expected 'hi', got '{grouped[0]['detail']}'"
assert grouped[1]["event_type"] == "mouse_click"
assert grouped[2]["detail"] == "a"
assert grouped[3]["detail"] == "b"

print("Test 4 passed: group_keystrokes merges consecutive type events")


# ---------------------------------------------------------------------------
# Test 5 — generate_playwright_script with no browser events
# ---------------------------------------------------------------------------

non_browser = [
    {"event_type": "mouse_click", "app_name": "Notepad", "timestamp": 1000.0, "x": 50, "y": 60},
]
script = playwright_gen.generate_playwright_script(non_browser, "Empty Test")
assert "# No browser events detected" in script, f"Missing no-events comment: {script}"
assert "from playwright.sync_api import sync_playwright" in script

print("Test 5 passed: generate_playwright_script with no browser events")


# ---------------------------------------------------------------------------
# Test 6 — generate_playwright_script produces valid structure
# ---------------------------------------------------------------------------

browser_events = [
    {
        "event_type": "window_focus",
        "app_name": "Google Chrome",
        "window_title": "Dashboard - https://example.com",
        "timestamp": 2000.0,
    },
    {
        "event_type": "mouse_click",
        "app_name": "Google Chrome",
        "timestamp": 2001.0,
        "x": 300,
        "y": 400,
    },
    {
        "event_type": "key_press",
        "app_name": "Google Chrome",
        "detail": "'s'",
        "timestamp": 2001.5,
    },
    {
        "event_type": "key_press",
        "app_name": "Google Chrome",
        "detail": "'e'",
        "timestamp": 2001.6,
    },
    {
        "event_type": "mouse_scroll",
        "app_name": "Google Chrome",
        "timestamp": 2003.0,
        "y": 120,
    },
]

script = playwright_gen.generate_playwright_script(browser_events, "My Flow")
assert "from playwright.sync_api import sync_playwright" in script, "Missing import"
assert "import time" in script, "Missing time import"
assert "def run():" in script, "Missing run() function"
assert 'page.goto("https://example.com")' in script, f"Missing goto: {script}"
assert "page.mouse.click(300, 400)" in script, f"Missing click: {script}"
assert 'page.keyboard.type("se")' in script, f"Missing merged type: {script}"
assert "page.mouse.wheel(0, 120)" in script, f"Missing scroll: {script}"
assert "browser.close()" in script, "Missing browser.close()"
assert '# Steps:' in script, "Missing steps count header"
step_line = [l for l in script.splitlines() if l.startswith("# Steps:")][0]
step_count = int(step_line.split(":")[1].strip())
assert step_count >= 4, f"Expected at least 4 steps, got {step_count}"

print("Test 6 passed: generate_playwright_script produces valid structure")


print()
print("ALL PLAYWRIGHT GEN TESTS PASSED")
