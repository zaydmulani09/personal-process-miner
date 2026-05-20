import json
import logging
import os
import urllib.error
import urllib.request

import db

_BACKEND = os.environ.get("PPM_LLM_BACKEND", "").strip().lower()
_OLLAMA_URL = os.environ.get("PPM_OLLAMA_URL", "http://localhost:11434").rstrip("/")
_OLLAMA_MODEL = os.environ.get("PPM_OLLAMA_MODEL", "llama3")
_CLAUDE_API_KEY = os.environ.get("PPM_CLAUDE_API_KEY", "").strip()
_CLAUDE_MODEL = os.environ.get("PPM_CLAUDE_MODEL", "claude-haiku-4-5-20251001")

_PROMPT_TEMPLATE = (
    "You are an automation assistant. A user recorded a computer workflow and it was"
    " converted into a {script_type} script. Explain what this script does in 2-3 plain"
    " English sentences, then rewrite it with: better variable names, inline comments on"
    " each step, a try/except block around the main logic, and a brief docstring."
    ' Return ONLY valid JSON in this exact format:\n'
    '{"explanation": "...", "improved_script": "..."}\n'
    "Script to improve:\n{script}"
)


def _read_env() -> tuple[str, str, str, str, str]:
    """Re-read env vars at call time so tests can patch os.environ."""
    backend = os.environ.get("PPM_LLM_BACKEND", "").strip().lower()
    ollama_url = os.environ.get("PPM_OLLAMA_URL", "http://localhost:11434").rstrip("/")
    ollama_model = os.environ.get("PPM_OLLAMA_MODEL", "llama3")
    claude_key = os.environ.get("PPM_CLAUDE_API_KEY", "").strip()
    claude_model = os.environ.get("PPM_CLAUDE_MODEL", "claude-haiku-4-5-20251001")
    return backend, ollama_url, ollama_model, claude_key, claude_model


def is_llm_available() -> bool:
    backend, ollama_url, _, claude_key, _ = _read_env()

    if backend == "ollama":
        try:
            req = urllib.request.Request(f"{ollama_url}/api/tags")
            with urllib.request.urlopen(req, timeout=1) as resp:
                return resp.status == 200
        except Exception as exc:
            logging.debug("Ollama unavailable: %s", exc)
            return False

    if backend == "claude":
        if not claude_key:
            logging.debug("Claude backend selected but PPM_CLAUDE_API_KEY is empty")
            return False
        return True

    logging.debug("PPM_LLM_BACKEND not set or unrecognized: %r", backend)
    return False


def _strip_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ``` or ``` ... ```) from LLM output."""
    text = text.strip()
    for prefix in ("```json", "```"):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _call_ollama(prompt: str, ollama_url: str, model: str) -> str:
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{ollama_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode())
    return body.get("response", "")


def _call_claude(prompt: str, api_key: str, model: str) -> str:
    payload = json.dumps({
        "model": model,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode())
    return body["content"][0]["text"]


def explain_script(script: str, script_type: str) -> dict:
    try:
        backend, ollama_url, ollama_model, claude_key, claude_model = _read_env()

        if not is_llm_available():
            return {"ok": False, "error": "LLM backend not available"}

        prompt = _PROMPT_TEMPLATE.format(script_type=script_type, script=script)

        if backend == "ollama":
            raw = _call_ollama(prompt, ollama_url, ollama_model)
        elif backend == "claude":
            raw = _call_claude(prompt, claude_key, claude_model)
        else:
            return {"ok": False, "error": f"Unknown backend: {backend!r}"}

        cleaned = _strip_fences(raw)
        parsed = json.loads(cleaned)
        return {
            "ok": True,
            "explanation": str(parsed.get("explanation", "")),
            "improved_script": str(parsed.get("improved_script", "")),
        }
    except Exception as exc:
        logging.exception("explain_script error")
        return {"ok": False, "error": str(exc)}


def improve_automation(automation_id: int) -> dict:
    try:
        automation = db.get_automation_by_id(automation_id)
        if automation is None:
            return {"ok": False, "error": "automation not found"}

        script_body = automation.get("script_body") or ""
        script_type = automation.get("script_type") or "pyautogui"

        result = explain_script(script_body, script_type)
        if not result.get("ok"):
            return result

        db.update_automation_script(automation_id, result["improved_script"])
        return {
            "ok": True,
            "automation_id": automation_id,
            "explanation": result["explanation"],
            "improved_script": result["improved_script"],
        }
    except Exception as exc:
        logging.exception("improve_automation error")
        return {"ok": False, "error": str(exc)}
