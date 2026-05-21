import base64
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
    "groq": "meta-llama/llama-4-scout-17b-16e-instruct",
    "gemini": "gemini-2.0-flash",
    "grok": "grok-2-vision-1212",
}

_SUPPORTED_BACKENDS = ["claude", "openai", "groq", "gemini", "grok"]

# 1x1 white PNG base64 for connection testing
_TEST_IMAGE_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _get_config() -> tuple[str, str, str]:
    backend = db.get_setting("vision_backend", "")
    key = db.get_setting(f"vision_api_key_{backend}", "") if backend else ""
    model = _MODELS.get(backend, "")
    return backend, key, model


def get_available_backends() -> list:
    return list(_SUPPORTED_BACKENDS)


def is_vision_available() -> bool:
    backend, key, _ = _get_config()
    if backend not in _SUPPORTED_BACKENDS:
        logging.debug("unknown vision_backend: %s", backend)
        return False
    if not key:
        logging.debug("vision_api_key_%s not set", backend)
        return False
    return True


def _classify_error(exc: Exception) -> str:
    exc_name = type(exc).__name__
    msg = str(exc).lower()
    if any(x in exc_name for x in ["Authentication", "Unauthorized", "PermissionDenied"]):
        return "invalid_api_key"
    if any(x in exc_name for x in ["RateLimit", "ResourceExhausted"]):
        return "rate_limited"
    if any(x in msg for x in [
        "invalid api key", "incorrect api key", "authentication", "unauthorized",
        "api_key_invalid", "invalid_api_key", "permission denied", "401",
        "api key", "credentials",
    ]):
        return "invalid_api_key"
    if any(x in msg for x in ["rate limit", "rate_limit", "too many requests", "429", "quota"]):
        return "rate_limited"
    if any(x in msg for x in [
        "connection", "timeout", "network", "unreachable",
        "connection refused", "failed to connect", "name resolution",
    ]):
        return "network_error"
    if any(x in msg for x in ["not support", "vision not", "image not", "multimodal"]):
        return "vision_not_supported"
    return "network_error"


def _call_backend(backend: str, key: str, model: str, screenshot_b64: str, instruction: str) -> str:
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

    elif backend in ("openai", "grok"):
        from openai import OpenAI
        kwargs: dict = {"api_key": key}
        if backend == "grok":
            kwargs["base_url"] = "https://api.x.ai/v1"
        client = OpenAI(**kwargs)
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

    elif backend == "gemini":
        import google.generativeai as genai
        from PIL import Image
        import io
        genai.configure(api_key=key)
        genai_model = genai.GenerativeModel(model)
        img_bytes = base64.b64decode(screenshot_b64)
        img = Image.open(io.BytesIO(img_bytes))
        response = genai_model.generate_content([instruction, img])
        return response.text

    else:
        raise ValueError(f"unsupported backend: {backend}")


def _call_model(screenshot_b64: str, instruction: str) -> str:
    backend, key, model = _get_config()
    return _call_backend(backend, key, model, screenshot_b64, instruction)


def test_connection(backend: str, api_key: str) -> dict:
    model = _MODELS.get(backend, "")
    if not model:
        return {"ok": False, "error": "invalid_api_key", "model": None}
    try:
        _call_backend(
            backend, api_key, model, _TEST_IMAGE_B64,
            'Describe this image in one word. Return JSON: {"description": "word"}'
        )
        return {"ok": True, "error": None, "model": model}
    except Exception as exc:
        err = _classify_error(exc)
        logging.debug("test_connection %s error: %s", backend, exc)
        return {"ok": False, "error": err, "model": model}


def analyze_screen(screenshot_b64: str, instruction: str) -> dict:
    try:
        if not is_vision_available():
            return {"ok": False, "error": "vision not configured"}
        raw = _call_model(screenshot_b64, instruction)
        return json.loads(_strip_fences(raw))
    except Exception as exc:
        err = _classify_error(exc)
        logging.warning("analyze_screen error: %s", exc)
        return {"ok": False, "error": err}


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
        err = _classify_error(exc)
        logging.warning("find_element error: %s", exc)
        return {"ok": False, "error": err}


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
        err = _classify_error(exc)
        logging.warning("describe_screen error: %s", exc)
        return {"ok": False, "error": err}


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
        err = _classify_error(exc)
        logging.warning("verify_action error: %s", exc)
        return {"ok": False, "error": err}
