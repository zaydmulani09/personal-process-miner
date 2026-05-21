import json
import logging
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

_SYSTEM_PROMPT = (
    "You are a computer vision assistant helping automate desktop workflows."
    "You see a screenshot of a user's screen. Analyze it carefully."
    "Always respond in valid JSON only. No markdown, no explanation outside JSON."
)

_MODELS = {
    "claude": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
    "groq": "llama-3.2-90b-vision-preview",
}


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _get_config() -> tuple[str, str, str]:
    backend = db.get_setting("vision_backend", "")
    key = db.get_setting("vision_api_key", "")
    model = _MODELS.get(backend, "")
    return backend, key, model


def is_vision_available() -> bool:
    backend, key, _ = _get_config()
    if not backend:
        logging.debug("vision_backend not set")
        return False
    if not key:
        logging.debug("vision_api_key not set")
        return False
    if backend not in _MODELS:
        logging.debug("unknown vision_backend: %s", backend)
        return False
    return True


def _call_model(screenshot_b64: str, instruction: str) -> str:
    backend, key, model = _get_config()
    if backend == "claude":
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": screenshot_b64,
                        },
                    },
                    {"type": "text", "text": instruction},
                ],
            }],
        )
        return response.content[0].text
    elif backend == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}},
                    {"type": "text", "text": instruction},
                ],
            }],
            max_tokens=1024,
        )
        return response.choices[0].message.content
    elif backend == "groq":
        from groq import Groq
        client = Groq(api_key=key)
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}},
                    {"type": "text", "text": instruction},
                ],
            }],
            max_tokens=1024,
        )
        return response.choices[0].message.content
    else:
        raise ValueError(f"unsupported backend: {backend}")


def analyze_screen(screenshot_b64: str, instruction: str) -> dict:
    try:
        if not is_vision_available():
            return {"ok": False, "error": "vision not configured"}
        raw = _call_model(screenshot_b64, instruction)
        return json.loads(_strip_fences(raw))
    except Exception as exc:
        logging.warning("analyze_screen error: %s", exc)
        return {"ok": False, "error": str(exc)}


def find_element(screenshot_b64: str, description: str) -> dict:
    instruction = (
        f'Find the UI element described as: "{description}"\n'
        "Return ONLY this JSON:\n"
        '{\n'
        '  "found": true/false,\n'
        '  "x": <center x coordinate as integer>,\n'
        '  "y": <center y coordinate as integer>,\n'
        '  "confidence": <0.0 to 1.0>,\n'
        '  "description": "<what you see at that location>"\n'
        '}\n'
        'If not found, return {"found": false, "x": 0, "y": 0, "confidence": 0, "description": "not found"}'
    )
    try:
        if not is_vision_available():
            return {"ok": False, "error": "vision not configured"}
        raw = _call_model(screenshot_b64, instruction)
        result = json.loads(_strip_fences(raw))
        result["x"] = int(result.get("x", 0))
        result["y"] = int(result.get("y", 0))
        return result
    except Exception as exc:
        logging.warning("find_element error: %s", exc)
        return {"ok": False, "error": str(exc)}


def describe_screen(screenshot_b64: str) -> dict:
    instruction = (
        "Describe what you see on this screen in 2-3 sentences. "
        "Then list the top 5 interactive elements you can see.\n"
        "Return ONLY this JSON:\n"
        '{\n'
        '  "description": "<2-3 sentence description>",\n'
        '  "elements": ["element 1", "element 2", "element 3", "element 4", "element 5"]\n'
        '}'
    )
    try:
        if not is_vision_available():
            return {"ok": False, "error": "vision not configured"}
        raw = _call_model(screenshot_b64, instruction)
        return json.loads(_strip_fences(raw))
    except Exception as exc:
        logging.warning("describe_screen error: %s", exc)
        return {"ok": False, "error": str(exc)}


def verify_action(screenshot_b64: str, expected_state: str) -> dict:
    instruction = (
        "I just performed an action. "
        f'I expected: "{expected_state}"\n'
        "Look at the current screen state and tell me if the action succeeded.\n"
        "Return ONLY this JSON:\n"
        '{\n'
        '  "success": true/false,\n'
        '  "confidence": <0.0 to 1.0>,\n'
        '  "observation": "<what you actually see>"\n'
        '}'
    )
    try:
        if not is_vision_available():
            return {"ok": False, "error": "vision not configured"}
        raw = _call_model(screenshot_b64, instruction)
        return json.loads(_strip_fences(raw))
    except Exception as exc:
        logging.warning("verify_action error: %s", exc)
        return {"ok": False, "error": str(exc)}
