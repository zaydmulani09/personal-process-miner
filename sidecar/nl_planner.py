import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
from accessibility import get_window_tree, tree_to_text, execute_action
from text_ai import is_ai_available, _call_ai, _strip_fences

_ACTION_SYSTEM = (
    "You are a desktop automation assistant. You will be given a task and the current UI element tree.\n"
    "Return ONLY a JSON array of actions to complete the task. No markdown, no explanation.\n"
    "Use only these action types: focus_window, click, type, keypress, menu_select, scroll.\n"
    "Target elements by name and control_type from the UI tree. Never use coordinates.\n"
    "Each action must match this schema exactly:\n"
    '{"action": "click", "target": {"name": "Button Name", "control_type": "Button", '
    '"automation_id": "", "window_title_contains": "App Title"}, '
    '"value": "", "key": "", "reason": "why this step"}'
)


def parse_instruction(instruction: str) -> dict:
    try:
        if not is_ai_available():
            return {"ok": False, "error": "AI not configured"}

        tree = get_window_tree()
        tree_txt = tree_to_text(tree)

        prompt = (
            f"UI tree:\n{tree_txt}\n\n"
            f"Task: {instruction}\n\n"
            "Return a JSON array of actions to complete this task."
        )

        raw = _call_ai(prompt, _ACTION_SYSTEM)
        if not raw:
            return {"ok": False, "error": "no response from AI"}

        cleaned = _strip_fences(raw)
        steps = json.loads(cleaned)
        if not isinstance(steps, list):
            return {"ok": False, "error": "AI returned non-list response"}
        if not steps:
            return {"ok": False, "error": "no steps returned"}

        return {
            "ok": True,
            "steps": steps,
            "summary": f"Automation: {instruction}",
            "estimated_steps": len(steps),
        }
    except json.JSONDecodeError as exc:
        logging.warning("parse_instruction JSON error: %s", exc)
        return {"ok": False, "error": f"JSON parse error: {str(exc)[:100]}"}
    except Exception as exc:
        logging.warning("parse_instruction error: %s", exc)
        return {"ok": False, "error": str(exc)}


def execute_instruction(instruction: str) -> dict:
    """
    Parse then execute instruction in a live per-step loop.
    Re-reads UI tree before every step. One corrective retry on element-not-found.
    """
    try:
        plan_result = parse_instruction(instruction)
        if not plan_result.get("ok"):
            return {"ok": False, "error": plan_result.get("error", "plan failed"), "steps_completed": 0, "total": 0, "results": []}

        steps = plan_result["steps"]
        results = []

        for i, step in enumerate(steps):
            # Re-read live tree before every step
            get_window_tree()

            result = execute_action(step)

            if not result.get("ok") and "element not found" in (result.get("error") or ""):
                # One corrective retry: ask AI for alternative action
                try:
                    tree2 = get_window_tree()
                    tree_txt2 = tree_to_text(tree2)
                    corrective_prompt = (
                        f"UI tree:\n{tree_txt2}\n\n"
                        f"Failed action: {json.dumps(step)}\n"
                        f"Error: {result.get('error')}\n"
                        "Return a single corrective action as a JSON object (not array) to achieve the same goal."
                    )
                    raw2 = _call_ai(corrective_prompt, _ACTION_SYSTEM)
                    if raw2:
                        corrective = json.loads(_strip_fences(raw2))
                        if isinstance(corrective, list):
                            corrective = corrective[0] if corrective else step
                        result = execute_action(corrective)
                except Exception as corr_exc:
                    logging.warning("corrective action failed: %s", corr_exc)

            results.append(result)

            if not result.get("ok"):
                return {
                    "ok": False,
                    "steps_completed": i,
                    "total": len(steps),
                    "results": results,
                    "error": result.get("error"),
                }

            if i < len(steps) - 1:
                time.sleep(0.8)

        return {
            "ok": True,
            "steps_completed": len(steps),
            "total": len(steps),
            "results": results,
        }
    except Exception as exc:
        logging.warning("execute_instruction error: %s", exc)
        return {"ok": False, "error": str(exc), "steps_completed": 0, "total": 0, "results": []}


def refine_plan(original_instruction: str, steps: list, feedback: str) -> dict:
    try:
        if not is_ai_available():
            return {"ok": False, "error": "AI not configured", "steps": steps, "summary": original_instruction}

        tree = get_window_tree()
        tree_txt = tree_to_text(tree)

        steps_json = json.dumps(steps, indent=2)
        prompt = (
            f"UI tree:\n{tree_txt}\n\n"
            f"Original task: {original_instruction}\n"
            f"Current steps:\n{steps_json}\n\n"
            f"User feedback: {feedback}\n\n"
            "Return a revised JSON array of actions."
        )

        raw = _call_ai(prompt, _ACTION_SYSTEM)
        if not raw:
            return {"ok": False, "error": "no response from AI", "steps": steps, "summary": original_instruction}

        cleaned = _strip_fences(raw)
        new_steps = json.loads(cleaned)
        if not isinstance(new_steps, list):
            return {"ok": False, "error": "AI returned non-list response", "steps": steps, "summary": original_instruction}

        return {
            "ok": True,
            "steps": new_steps,
            "summary": f"Automation: {original_instruction}",
            "estimated_steps": len(new_steps),
        }
    except json.JSONDecodeError as exc:
        logging.warning("refine_plan JSON error: %s", exc)
        return {"ok": False, "error": f"JSON parse error: {str(exc)[:100]}", "steps": steps, "summary": original_instruction}
    except Exception as exc:
        logging.warning("refine_plan error: %s", exc)
        return {"ok": False, "error": str(exc), "steps": steps, "summary": original_instruction}


def save_nl_automation(instruction: str, steps: list, summary: str) -> int:
    return db.insert_automation({
        "workflow_id": None,
        "name": summary or instruction[:80],
        "script_type": "nl_builder",
        "script_body": json.dumps(steps),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
