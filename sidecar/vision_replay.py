import logging
import re
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from accessibility import get_screen_tree, find_element_by_description
from text_ai import is_ai_available

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    _PYAUTOGUI_OK = True
except Exception:
    pyautogui = None
    _PYAUTOGUI_OK = False

# Step types that cannot be meaningfully replayed — skip gracefully
_SKIP_TYPES = {"window", "unknown", "wait", "comment"}


def _execute_step(step: dict, x: int, y: int) -> dict:
    """
    Execute one step using pyautogui.
    Returns {"ok": bool, "skipped": bool, "error": str|None}
    Never raises.
    """
    if not _PYAUTOGUI_OK:
        return {"ok": False, "skipped": False, "error": "pyautogui not available"}

    stype = (step.get("type") or "").strip().lower()

    # Gracefully skip unexecutable step types
    if stype in _SKIP_TYPES or not stype:
        return {"ok": True, "skipped": True, "error": None}

    try:
        if stype == "click":
            if x or y:
                pyautogui.click(x, y)

        elif stype == "type":
            if x and y:
                pyautogui.click(x, y)
            value = step.get("value", "") or ""
            if value:
                pyautogui.write(value, interval=0.05)

        elif stype in ("keypress", "hotkey", "key"):
            key = (step.get("key") or step.get("value") or "").strip()
            if key:
                if "+" in key:
                    # Combo like Ctrl+Shift+T or win+up
                    parts = [p.strip().lower() for p in key.split("+") if p.strip()]
                    pyautogui.hotkey(*parts)
                else:
                    pyautogui.press(key.lower())

        elif stype == "scroll":
            try:
                amount = int(step.get("value") or step.get("clicks") or 3)
            except (ValueError, TypeError):
                amount = 3
            pyautogui.scroll(amount, x=x or None, y=y or None)

        else:
            # Unknown type — skip gracefully rather than fail
            return {"ok": True, "skipped": True, "error": None}

        return {"ok": True, "skipped": False, "error": None}

    except Exception as exc:
        logging.warning("_execute_step failed (type=%s): %s", stype, exc)
        return {"ok": False, "skipped": False, "error": str(exc)}


def replay_step(step: dict, use_ai: bool = True) -> dict:
    if not _PYAUTOGUI_OK:
        return {"ok": False, "method": "recorded", "confidence": None, "error": "pyautogui not available"}

    stype = (step.get("type") or "").strip().lower()

    # Skip non-executable types immediately — don't bother with AI lookup
    if stype in _SKIP_TYPES or not stype:
        return {"ok": True, "method": "skipped", "confidence": None, "error": None}

    x = int(step.get("x") or 0)
    y = int(step.get("y") or 0)
    description = step.get("description") or ""
    method = "recorded"
    confidence = None

    # AI-assisted coordinate resolution for click steps
    if use_ai and description and stype == "click":
        try:
            tree = get_screen_tree()
            if tree.get("ok"):
                element = find_element_by_description(description, tree)
                if element:
                    cx = element.get("center", {}).get("x", 0)
                    cy = element.get("center", {}).get("y", 0)
                    if cx or cy:
                        x = cx
                        y = cy
                        method = "accessibility"
                        confidence = 1.0
        except Exception as exc:
            logging.warning("accessibility find_element failed in replay_step: %s", exc)

    result = _execute_step(step, x, y)
    if result.get("skipped"):
        return {"ok": True, "method": "skipped", "confidence": None, "error": None}
    return {
        "ok": result["ok"],
        "method": method,
        "confidence": confidence,
        "error": result.get("error"),
    }


def replay_session(steps: list, use_ai: bool = True, verify_each: bool = False) -> dict:
    results = []
    for i, step in enumerate(steps):
        result = replay_step(step, use_ai=use_ai)
        results.append(result)

        if not result.get("ok"):
            return {
                "ok": False,
                "steps_completed": i,
                "total_steps": len(steps),
                "results": results,
            }

        if verify_each:
            try:
                tree = get_screen_tree()
                if not tree.get("ok"):
                    logging.warning("verify_each: could not get screen tree at step %d", i)
            except Exception as exc:
                logging.warning("verify_each get_screen_tree failed: %s", exc)

        if i < len(steps) - 1:
            time.sleep(0.5)

    return {
        "ok": True,
        "steps_completed": len(steps),
        "total_steps": len(steps),
        "results": results,
    }


def describe_replay_plan(steps: list) -> dict:
    ai_ok = is_ai_available()
    plan = []
    for i, step in enumerate(steps):
        stype = (step.get("type") or "unknown").strip().lower()
        description = step.get("description") or ""
        skippable = stype in _SKIP_TYPES
        will_use_ai = ai_ok and bool(description) and stype == "click"
        plan.append({
            "step": i,
            "type": stype,
            "description": description or f"{stype} at ({step.get('x', 0)}, {step.get('y', 0)})",
            "will_use_ai": will_use_ai,
            "skippable": skippable,
        })
    return {"plan": plan}


def parse_steps_from_pyautogui(script_body: str) -> list:
    steps = []
    for line in script_body.splitlines():
        line = line.strip()
        if m := re.match(r"pyautogui\.click\((\d+),\s*(\d+)\)", line):
            steps.append({"type": "click", "x": int(m.group(1)), "y": int(m.group(2))})
        elif m := re.match(r"pyautogui\.hotkey\((.+)\)", line):
            keys = "+".join(k.strip().strip("'\"") for k in m.group(1).split(","))
            steps.append({"type": "hotkey", "key": keys})
        elif m := re.match(r"pyautogui\.press\('(.+)'\)", line):
            steps.append({"type": "keypress", "key": m.group(1)})
        elif m := re.match(r"pyautogui\.(?:typewrite|write)\('(.*?)'\)", line):
            steps.append({"type": "type", "value": m.group(1)})
        elif m := re.match(r"pyautogui\.scroll\((-?\d+)", line):
            steps.append({"type": "scroll", "value": m.group(1)})
    return steps
