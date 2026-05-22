import json
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
from accessibility import get_screen_tree, tree_to_text
from text_ai import plan_automation, is_ai_available


def parse_instruction(instruction: str) -> dict:
    try:
        if not is_ai_available():
            return {"ok": False, "error": "AI not configured"}

        tree = get_screen_tree()
        tree_txt = tree_to_text(tree)

        result = plan_automation(instruction, tree_txt)
        if not result.get("ok"):
            return {"ok": False, "error": result.get("error", "no steps returned")}

        steps = result.get("steps", [])
        if not steps:
            return {"ok": False, "error": "no steps returned"}

        return {
            "ok": True,
            "steps": steps,
            "summary": result.get("summary", instruction),
            "estimated_steps": len(steps),
        }
    except Exception as exc:
        logging.warning("parse_instruction error: %s", exc)
        return {"ok": False, "error": str(exc)}


def refine_plan(original_instruction: str, steps: list, feedback: str) -> dict:
    try:
        if not is_ai_available():
            return {"ok": False, "error": "AI not configured", "steps": steps, "summary": original_instruction}

        tree = get_screen_tree()
        tree_txt = tree_to_text(tree)

        steps_json = json.dumps(steps, indent=2)
        combined_instruction = (
            f"{original_instruction}\n\n"
            f"Current steps:\n{steps_json}\n\n"
            f"User feedback: {feedback}\n\n"
            "Revise the steps based on the feedback."
        )

        result = plan_automation(combined_instruction, tree_txt)
        if not result.get("ok"):
            return {
                "ok": False,
                "error": result.get("error", "no steps returned"),
                "steps": steps,
                "summary": original_instruction,
            }

        return {
            "ok": True,
            "steps": result["steps"],
            "summary": result.get("summary", original_instruction),
            "estimated_steps": len(result["steps"]),
        }
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
