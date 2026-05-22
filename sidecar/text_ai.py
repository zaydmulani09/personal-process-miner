"""
Text-only AI backend for desktop automation planning.
No screenshots needed — uses accessibility tree text.
"""
import json
import logging
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

_MODELS = {
    "groq": "moonshotai/kimi-k2-instruct",
    "claude": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
    "grok": "grok-3-mini",
}

_SUPPORTED_BACKENDS = ["claude", "openai", "groq", "gemini", "grok"]


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _get_config() -> tuple:
    """Returns (backend, api_key) from DB settings."""
    backend = db.get_setting("ai_backend", "")
    key = db.get_setting(f"ai_api_key_{backend}", "") if backend else ""
    return backend, key


def _call_ai(prompt: str, system: str = "") -> str:
    """Calls configured backend text-only. Never raises."""
    try:
        backend, key = _get_config()
        if not backend or backend not in _SUPPORTED_BACKENDS:
            return ""
        if not key:
            return ""
        model = _MODELS[backend]

        if backend == "claude":
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            kwargs = {"model": model, "max_tokens": 2048, "messages": [{"role": "user", "content": prompt}]}
            if system:
                kwargs["system"] = system
            response = client.messages.create(**kwargs)
            return response.content[0].text

        elif backend in ("openai", "grok"):
            from openai import OpenAI
            kwargs = {"api_key": key}
            if backend == "grok":
                kwargs["base_url"] = "https://api.x.ai/v1"
            client = OpenAI(**kwargs)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=model, messages=messages, max_tokens=2048)
            return response.choices[0].message.content

        elif backend == "groq":
            from groq import Groq
            client = Groq(api_key=key)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=model, messages=messages, max_tokens=2048)
            return response.choices[0].message.content

        elif backend == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=key)
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            genai_model = genai.GenerativeModel(model)
            response = genai_model.generate_content(full_prompt)
            return response.text

        return ""
    except Exception as exc:
        print(f"[text_ai] _call_ai error: {repr(exc)}", file=sys.stderr)
        logging.warning("text_ai._call_ai error: %s", exc)
        return ""


def plan_automation(instruction: str, tree_text: str) -> dict:
    """
    Returns {"ok": True, "steps": [...], "summary": str} or {"ok": False, "error": str}.
    """
    if not is_ai_available():
        return {"ok": False, "error": "AI not configured"}

    system = (
        f"You are a desktop automation assistant. The user wants to: {instruction}\n\n"
        f"Here is the current state of the screen as UI elements:\n{tree_text}\n\n"
        'Return a JSON array of steps to complete the task. Each step:\n'
        '{"type": "click"|"type"|"keypress"|"scroll", "target": "element name", "x": int, "y": int, '
        '"value": "text to type", "key": "key name", "description": "what this step does"}\n\n'
        "Use the exact coordinates from the UI tree above. Return ONLY the JSON array, no other text."
    )
    prompt = f"Plan the automation for: {instruction}"

    try:
        raw = _call_ai(prompt, system)
        if not raw:
            return {"ok": False, "error": "no response from AI"}
        cleaned = _strip_fences(raw)
        steps = json.loads(cleaned)
        if not isinstance(steps, list):
            return {"ok": False, "error": "AI returned non-list response"}
        return {
            "ok": True,
            "steps": steps,
            "summary": f"Automation: {instruction}",
        }
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"JSON parse error: {str(exc)[:100]}"}
    except Exception as exc:
        logging.warning("plan_automation error: %s", exc)
        return {"ok": False, "error": str(exc)}


def answer_screen_question(question: str, tree_text: str) -> str:
    """
    Answers a question about the current screen state.
    Returns answer string (never raises).
    """
    if not is_ai_available():
        return "AI not configured. Please add an API key in Settings."

    system = (
        "You are a helpful assistant that answers questions about the current screen state. "
        "You will be given the UI element tree as text. Answer concisely and accurately."
    )
    prompt = (
        f"Here is the current screen's UI element tree:\n{tree_text}\n\n"
        f"Question: {question}"
    )
    try:
        result = _call_ai(prompt, system)
        return result or "No response from AI."
    except Exception as exc:
        logging.warning("answer_screen_question error: %s", exc)
        return f"Error: {str(exc)}"


def is_ai_available() -> bool:
    """Returns True if AI backend is configured with a key."""
    backend, key = _get_config()
    return bool(backend and backend in _SUPPORTED_BACKENDS and key)


def get_available_backends() -> list:
    """Returns list of supported backend names."""
    return list(_SUPPORTED_BACKENDS)


def test_connection(backend: str, api_key: str) -> dict:
    """
    Sends a simple test message to the backend.
    Returns {"ok": bool, "error": str|None, "model": str}.
    Never raises.
    """
    model = _MODELS.get(backend, "")
    if not model:
        return {"ok": False, "error": "unknown backend", "model": None}

    test_prompt = "Reply with just the word OK"
    try:
        if backend == "claude":
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model, max_tokens=10,
                messages=[{"role": "user", "content": test_prompt}]
            )
            text = response.content[0].text
            return {"ok": bool(text), "error": None, "model": model}

        elif backend in ("openai", "grok"):
            from openai import OpenAI
            kwargs = {"api_key": api_key}
            if backend == "grok":
                kwargs["base_url"] = "https://api.x.ai/v1"
            client = OpenAI(**kwargs)
            response = client.chat.completions.create(
                model=model, max_tokens=10,
                messages=[{"role": "user", "content": test_prompt}]
            )
            text = response.choices[0].message.content
            return {"ok": bool(text), "error": None, "model": model}

        elif backend == "groq":
            from groq import Groq
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model=model, max_tokens=10,
                messages=[{"role": "user", "content": test_prompt}]
            )
            text = response.choices[0].message.content
            return {"ok": bool(text), "error": None, "model": model}

        elif backend == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            genai_model = genai.GenerativeModel(model)
            response = genai_model.generate_content(test_prompt)
            text = response.text
            return {"ok": bool(text), "error": None, "model": model}

        return {"ok": False, "error": "unsupported backend", "model": model}

    except Exception as exc:
        print(f"[text_ai] test_connection {backend} error: {repr(exc)}", file=sys.stderr)
        logging.debug("test_connection %s error: %s", backend, exc)
        err_msg = _classify_error(exc)
        return {"ok": False, "error": err_msg, "model": model}


def _classify_error(exc: Exception) -> str:
    exc_name = type(exc).__name__
    msg = str(exc).lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "http_status", None)
    if status == 401 or status == 403:
        return "invalid_api_key"
    if status == 429:
        return "rate_limited"
    if any(x in exc_name for x in ["Authentication", "Unauthorized", "PermissionDenied"]):
        return "invalid_api_key"
    if any(x in exc_name for x in ["RateLimit", "ResourceExhausted", "TooManyRequests"]):
        return "rate_limited"
    if any(x in exc_name for x in ["Connection", "Timeout", "Network", "Socket"]):
        return "network_error"
    if any(x in msg for x in ["invalid api key", "incorrect api key", "authentication", "unauthorized", "api_key"]):
        return "invalid_api_key"
    if any(x in msg for x in ["rate limit", "too many requests", "quota"]):
        return "rate_limited"
    if any(x in msg for x in ["connection", "timeout", "network", "unreachable"]):
        return "network_error"
    raw = str(exc)[:80].replace("\n", " ")
    return f"unknown_error: {raw}"
