import logging
import re
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vision_ai
import vision_capture

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    _PYAUTOGUI_OK = True
except ImportError:
    pyautogui = None
    _PYAUTOGUI_OK = False


def _execute_step(step: dict, x: int, y: int) -> None:
    stype = step.get("type", "")
    if stype == "click":
        pyautogui.click(x, y)
    elif stype == "type":
        if x and y:
            pyautogui.click(x, y)
        pyautogui.typewrite(step.get("value", ""), interval=0.05)
    elif stype == "scroll":
        try:
            amount = int(step.get("value", 3))
        except (ValueError, TypeError):
            amount = 3
        pyautogui.scroll(amount, x=x or None, y=y or None)
    elif stype == "keypress":
        key = step.get("key", "")
        if key:
            pyautogui.press(key)


def replay_step(step: dict, use_vision: bool = True) -> dict:
    if not _PYAUTOGUI_OK:
        return {"ok": False, "method": "recorded", "confidence": None, "error": "pyautogui not available"}

    x = int(step.get("x") or 0)
    y = int(step.get("y") or 0)
    description = step.get("description") or ""
    method = "recorded"
    confidence = None

    if use_vision and description and step.get("type") == "click":
        try:
            screenshot = vision_capture.take_screenshot()
            if screenshot:
                result = vision_ai.find_element(screenshot, description)
                if result.get("found") and float(result.get("confidence", 0)) >= 0.6:
                    x = int(result["x"])
                    y = int(result["y"])
                    method = "vision"
                    confidence = float(result.get("confidence", 0))
        except Exception as exc:
            logging.warning("vision find_element failed in replay_step: %s", exc)

    try:
        _execute_step(step, x, y)
        return {"ok": True, "method": method, "confidence": confidence, "error": None}
    except Exception as exc:
        logging.warning("replay_step execute failed: %s", exc)
        return {"ok": False, "method": method, "confidence": confidence, "error": str(exc)}


def replay_session(steps: list, use_vision: bool = True, verify_each: bool = False) -> dict:
    results = []
    for i, step in enumerate(steps):
        result = replay_step(step, use_vision=use_vision)
        results.append(result)

        if not result.get("ok"):
            return {
                "ok": False,
                "steps_completed": i,
                "total_steps": len(steps),
                "results": results,
            }

        if verify_each:
            description = step.get("description") or f"step {i + 1}"
            try:
                screenshot = vision_capture.take_screenshot()
                if screenshot:
                    verification = vision_ai.verify_action(screenshot, f"completed: {description}")
                    if float(verification.get("confidence", 1.0)) < 0.5:
                        return {
                            "ok": False,
                            "failed_at": i,
                            "reason": "verification failed",
                            "observation": verification.get("observation", ""),
                            "steps_completed": i,
                            "total_steps": len(steps),
                            "results": results,
                        }
            except Exception as exc:
                logging.warning("verify_action failed in replay_session: %s", exc)

        if i < len(steps) - 1:
            time.sleep(0.5)

    return {
        "ok": True,
        "steps_completed": len(steps),
        "total_steps": len(steps),
        "results": results,
    }


def describe_replay_plan(steps: list) -> dict:
    vision_ok = vision_ai.is_vision_available()
    plan = []
    for i, step in enumerate(steps):
        stype = step.get("type", "unknown")
        description = step.get("description") or ""
        will_use_vision = vision_ok and bool(description) and stype == "click"
        plan.append({
            "step": i,
            "type": stype,
            "description": description or f"{stype} at ({step.get('x', 0)}, {step.get('y', 0)})",
            "will_use_vision": will_use_vision,
        })
    return {"plan": plan}


def parse_steps_from_pyautogui(script_body: str) -> list[dict]:
    steps = []
    for line in script_body.splitlines():
        line = line.strip()
        if m := re.match(r"pyautogui\.click\((\d+),\s*(\d+)\)", line):
            steps.append({"type": "click", "x": int(m.group(1)), "y": int(m.group(2))})
        elif m := re.match(r"pyautogui\.press\('(.+)'\)", line):
            steps.append({"type": "keypress", "key": m.group(1)})
        elif m := re.match(r"pyautogui\.typewrite\('(.*?)'\)", line):
            steps.append({"type": "type", "value": m.group(1)})
        elif m := re.match(r"pyautogui\.scroll\((-?\d+)", line):
            steps.append({"type": "scroll", "value": m.group(1)})
    return steps
