import json
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
import vision_ai
import vision_capture

_STEP_SCHEMA = """{
  "steps": [
    {
      "type": "click|type|keypress|scroll|wait",
      "description": "human readable description of what to click/type",
      "value": "text to type (type steps only)",
      "key": "key name (keypress steps only)",
      "wait_ms": 500
    }
  ],
  "summary": "one sentence describing what this automation does",
  "estimated_steps": 3
}"""


def parse_instruction(instruction: str) -> dict:
    try:
        if not vision_ai.is_vision_available():
            return {"ok": False, "error": "vision not configured"}

        screenshot = vision_capture.take_screenshot()
        if not screenshot:
            return {"ok": False, "error": "screenshot failed"}

        prompt = (
            f'The user wants to automate: "{instruction}"\n\n'
            "Look at the current screen and break this instruction into a precise list of "
            "executable steps.\n"
            f"Return ONLY this JSON schema:\n{_STEP_SCHEMA}"
        )

        result = vision_ai.analyze_screen(screenshot, prompt)
        if not isinstance(result, dict) or not result.get("steps"):
            return {"ok": False, "error": result.get("error", "no steps returned")}

        return {
            "ok": True,
            "steps": result["steps"],
            "summary": result.get("summary", instruction),
            "estimated_steps": result.get("estimated_steps", len(result["steps"])),
        }
    except Exception as exc:
        logging.warning("parse_instruction error: %s", exc)
        return {"ok": False, "error": str(exc)}


def refine_plan(original_instruction: str, steps: list, feedback: str) -> dict:
    try:
        if not vision_ai.is_vision_available():
            return {"ok": False, "error": "vision not configured", "steps": steps, "summary": original_instruction}

        screenshot = vision_capture.take_screenshot()
        if not screenshot:
            return {"ok": False, "error": "screenshot failed", "steps": steps, "summary": original_instruction}

        steps_json = json.dumps(steps, indent=2)
        prompt = (
            f'The user is building an automation for: "{original_instruction}"\n\n'
            f"Current steps:\n{steps_json}\n\n"
            f'User feedback: "{feedback}"\n\n'
            f"Revise the steps based on the feedback. Return ONLY this JSON schema:\n{_STEP_SCHEMA}"
        )

        result = vision_ai.analyze_screen(screenshot, prompt)
        if not isinstance(result, dict) or not result.get("steps"):
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
            "estimated_steps": result.get("estimated_steps", len(result["steps"])),
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
