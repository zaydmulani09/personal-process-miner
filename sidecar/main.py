import base64
import io
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer

_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sidecar.log")
logging.basicConfig(
    filename=_log_path,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)

import capture
import db
import fingerprinter
import llm_explainer
import macro_recorder
import playwright_gen
import ranker
import scheduler
import segmenter
import vision_capture
import vision_ai
import vision_replay
import nl_planner

_UNSAFE_PATTERNS = ["os.system", "subprocess", "shutil.rmtree", "__import__"]

_HTTP_PORT = 7834
_CHROME_EXT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "chrome-extension")


class _HTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logging.debug("HTTP %s", fmt % args)

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/status":
            self._send_json(200, {"ok": True, "version": "1.0.0"})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/dom-events":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                payload = json.loads(body)
                events = payload.get("events", [])
                if events:
                    db.insert_dom_events(events)
                self._send_json(200, {"ok": True, "count": len(events)})
            except Exception as exc:
                logging.exception("POST /dom-events error")
                self._send_json(500, {"error": str(exc)})
        else:
            self._send_json(404, {"error": "not found"})


def _start_http_server() -> None:
    try:
        server = HTTPServer(("127.0.0.1", _HTTP_PORT), _HTTPHandler)
        server.serve_forever()
    except Exception:
        logging.exception("HTTP server failed to start on port %d", _HTTP_PORT)


def is_script_safe(script_body: str) -> bool:
    """Return False if script_body contains any known-dangerous patterns."""
    for pattern in _UNSAFE_PATTERNS:
        if pattern in script_body:
            return False
    return True


def _write(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _handle(msg: dict) -> dict | None:
    t = msg.get("type")

    if t == "ping":
        return {"type": "pong"}

    if t == "status":
        return {"type": "status", "state": "running"}

    if t == "start_capture":
        capture.start_capture()
        return {"type": "ok", "message": "capture started"}

    if t == "stop_capture":
        capture.stop_capture()
        return {"type": "ok", "message": "capture stopped"}

    if t == "get_events":
        limit = msg.get("limit", 100)
        return {"type": "events", "data": db.get_recent_events(limit=limit)}

    if t == "get_sessions":
        limit = msg.get("limit", 50)
        return {"type": "sessions", "data": db.get_sessions(limit=limit)}

    if t == "get_workflows":
        return {"type": "workflows", "data": db.get_workflows()}

    if t == "get_automations":
        return {"type": "automations", "data": db.get_automations()}

    if t == "run_segmentation":
        sessions = segmenter.run_segmentation()
        return {"type": "segmentation_complete", "session_count": len(sessions), "sessions": sessions}

    if t == "run_fingerprinting":
        patterns = fingerprinter.run_fingerprinting()
        return {"type": "fingerprinting_complete", "pattern_count": len(patterns), "patterns": patterns}

    if t == "label_workflow":
        workflow_id = msg.get("workflow_id")
        name = msg.get("name", "")
        steps = msg.get("steps", [])
        if not isinstance(workflow_id, int):
            return {"type": "error", "message": "workflow_id must be an integer"}
        if not name or not isinstance(name, str):
            return {"type": "error", "message": "name must be a non-empty string"}
        if not steps or not isinstance(steps, list):
            return {"type": "error", "message": "steps must be a non-empty list"}
        if not db.label_workflow(workflow_id, name, steps):
            return {"type": "error", "message": "workflow not found"}
        return {"type": "ok", "workflow_id": workflow_id, "name": name}

    if t == "delete_workflow":
        workflow_id = msg.get("workflow_id")
        if not isinstance(workflow_id, int):
            return {"type": "error", "message": "workflow_id must be an integer"}
        if not db.delete_workflow(workflow_id):
            return {"type": "error", "message": "workflow not found"}
        return {"type": "ok", "workflow_id": workflow_id}

    if t == "start_recording":
        workflow_id = msg.get("workflow_id")
        result = macro_recorder.start_recording(workflow_id)
        return result

    if t == "stop_recording":
        result = macro_recorder.stop_recording()
        return result

    if t == "save_macro":
        name = msg.get("name", "")
        workflow_id = msg.get("workflow_id")
        if not name or not isinstance(name, str):
            return {"type": "error", "message": "name must be a non-empty string"}
        result = macro_recorder.save_macro(name, workflow_id)
        return result

    if t == "get_recording_status":
        status = macro_recorder.get_recording_status()
        return {"type": "recording_status", **status}

    if t == "generate_playwright":
        workflow_id = msg.get("workflow_id")
        name = msg.get("name", "")
        if not isinstance(workflow_id, int):
            return {"type": "error", "message": "workflow_id must be an integer"}
        workflows = db.get_workflows()
        workflow = next((w for w in workflows if w["id"] == workflow_id), None)
        if workflow is None:
            return {"type": "error", "message": "workflow not found"}
        raw_events = db.get_recent_events(limit=10_000)
        sessions = segmenter.segment_events(raw_events)
        all_events: list[dict] = []
        for sess in sessions:
            ids = sess.get("event_ids", [])
            all_events.extend(db.get_events_by_ids(ids) if ids else [])
        script_name = name or workflow.get("name") or f"workflow_{workflow_id}"
        result = playwright_gen.save_playwright_script(all_events, script_name, workflow_id)
        if not result.get("ok"):
            return {"type": "error", "message": result.get("error", "unknown error")}
        return {
            "type": "playwright_ready",
            "automation_id": result["automation_id"],
            "script_path": result["script_path"],
            "step_count": result["step_count"],
        }

    if t == "preview_playwright":
        workflow_id = msg.get("workflow_id")
        if not isinstance(workflow_id, int):
            return {"type": "error", "message": "workflow_id must be an integer"}
        workflows = db.get_workflows()
        workflow = next((w for w in workflows if w["id"] == workflow_id), None)
        if workflow is None:
            return {"type": "error", "message": "workflow not found"}
        raw_events = db.get_recent_events(limit=10_000)
        sessions = segmenter.segment_events(raw_events)
        all_events: list[dict] = []
        for sess in sessions:
            ids = sess.get("event_ids", [])
            all_events.extend(db.get_events_by_ids(ids) if ids else [])
        script_name = workflow.get("name") or f"workflow_{workflow_id}"
        script = playwright_gen.generate_playwright_script(all_events, script_name)
        step_count = script.count("page.")
        return {"type": "playwright_preview", "script": script, "step_count": step_count}

    if t == "run_automation":
        automation_id = msg.get("automation_id")
        if not isinstance(automation_id, int):
            return {"type": "error", "message": "automation_id must be an integer"}
        try:
            automation = db.get_automation_by_id(automation_id)
            if automation is None:
                return {"type": "error", "message": "automation not found"}
            script_body = automation.get("script_body") or ""
            script_type = automation.get("script_type", "pyautogui")

            if not is_script_safe(script_body):
                return {
                    "type": "run_result",
                    "automation_id": automation_id,
                    "status": "error",
                    "script_type": script_type,
                    "stdout": "",
                    "stderr": "Script contains unsafe patterns and was not executed",
                }

            timeout = 120 if script_type == "playwright" else 60
            _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".py", delete=False, encoding="utf-8"
                ) as f:
                    f.write(script_body)
                    tmp_path = f.name
                result = subprocess.run(
                    ["py", tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=_project_root,
                )
                run_status = "success" if result.returncode == 0 else "error"
                stdout = result.stdout
                stderr = result.stderr
            except subprocess.TimeoutExpired:
                run_status = "error"
                stdout = ""
                stderr = f"Script timed out after {timeout} seconds"
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
            db.update_automation_run(automation_id, run_status)
            return {
                "type": "run_result",
                "automation_id": automation_id,
                "status": run_status,
                "script_type": script_type,
                "stdout": stdout,
                "stderr": stderr,
            }
        except Exception as exc:
            logging.exception("run_automation error")
            return {"type": "error", "message": str(exc)}

    if t == "update_automation_name":
        automation_id = msg.get("automation_id")
        name = msg.get("name", "")
        if not isinstance(automation_id, int):
            return {"type": "error", "message": "automation_id must be an integer"}
        if not name or not isinstance(name, str):
            return {"type": "error", "message": "name must be a non-empty string"}
        db.update_automation_name(automation_id, name)
        return {"type": "ok", "automation_id": automation_id}

    if t == "delete_automation":
        automation_id = msg.get("automation_id")
        if not isinstance(automation_id, int):
            return {"type": "error", "message": "automation_id must be an integer"}
        # Attempt to remove associated script file from data/macros/
        automation = db.get_automation_by_id(automation_id)
        if automation is None:
            return {"type": "error", "message": "automation not found"}
        auto_name = automation.get("name", "")
        script_type = automation.get("script_type", "")
        name_slug = "".join(
            c if (c.isalnum() or c == "_") else "_"
            for c in auto_name.lower().replace(" ", "_")
        )
        _macros_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "data", "macros"
        )
        if script_type == "playwright":
            script_file = os.path.join(_macros_dir, f"{name_slug}_playwright.py")
        else:
            script_file = os.path.join(_macros_dir, f"{name_slug}.py")
        if os.path.exists(script_file):
            try:
                os.unlink(script_file)
            except OSError:
                pass
        db.delete_automation(automation_id)
        return {"type": "ok", "automation_id": automation_id}

    if t == "get_automation_stats":
        return {"type": "automation_stats", "data": db.get_automation_stats()}

    if t == "check_llm":
        available = llm_explainer.is_llm_available()
        backend_val = os.environ.get("PPM_LLM_BACKEND", "").strip().lower() or None
        return {"type": "llm_status", "available": available, "backend": backend_val if available else None}

    if t == "improve_automation":
        automation_id = msg.get("automation_id")
        if not isinstance(automation_id, int):
            return {"type": "error", "message": "automation_id must be an integer"}
        result = llm_explainer.improve_automation(automation_id)
        return {
            "type": "automation_improved",
            "automation_id": automation_id,
            "explanation": result.get("explanation", ""),
            "ok": result.get("ok", False),
            "error": result.get("error") if not result.get("ok") else None,
        }

    if t == "get_ranked_workflows":
        return {"type": "ranked_workflows", "data": ranker.get_ranked_workflows()}

    if t == "get_summary_stats":
        return {"type": "summary_stats", "data": ranker.get_summary_stats()}

    if t == "get_onboarding_state":
        complete = db.get_setting("onboarding_complete", "false") == "true"
        step = int(db.get_setting("onboarding_step", "0"))
        return {"type": "onboarding_state", "complete": complete, "step": step}

    if t == "set_onboarding_complete":
        db.set_setting("onboarding_complete", "true")
        return {"type": "ok"}

    if t == "set_onboarding_step":
        step = msg.get("step", 0)
        if not isinstance(step, int):
            return {"type": "error", "message": "step must be an integer"}
        db.set_setting("onboarding_step", str(step))
        return {"type": "ok"}

    if t == "check_accessibility":
        import platform as _platform
        _os = _platform.system().lower()
        if _os != "darwin":
            return {"type": "accessibility_status", "granted": True, "platform": _os if _os in ("windows", "linux") else _os}
        # macOS: attempt to create keyboard listener; failure = no permission
        try:
            from pynput import keyboard as _kb
            _l = _kb.Listener(on_press=lambda k: None)
            _l.start()
            _l.stop()
            granted = True
        except Exception:
            granted = False
        return {"type": "accessibility_status", "granted": granted, "platform": "darwin"}

    if t == "get_settings":
        return {"type": "settings", "data": db.get_all_settings()}

    if t == "set_setting":
        key = msg.get("key", "")
        value = msg.get("value", "")
        if not key or not isinstance(key, str):
            return {"type": "error", "message": "key must be a non-empty string"}
        db.set_setting(key, str(value))
        return {"type": "ok"}

    if t == "purge_old_events":
        retention = int(db.get_setting("retention_days", "30"))
        deleted = db.purge_old_events(retention)
        return {"type": "purge_result", "deleted": deleted}

    if t == "purge_all_data":
        counts = db.purge_all_data()
        return {"type": "purge_result", "counts": counts}

    if t == "get_blocklist":
        import json as _json
        apps = _json.loads(db.get_setting("blocklist_apps", "[]"))
        return {"type": "blocklist", "apps": apps}

    if t == "add_to_blocklist":
        import json as _json
        app = msg.get("app", "").strip()
        if not app:
            return {"type": "error", "message": "app must be non-empty"}
        apps = _json.loads(db.get_setting("blocklist_apps", "[]"))
        if app not in apps:
            apps.append(app)
            db.set_setting("blocklist_apps", _json.dumps(apps))
        return {"type": "ok"}

    if t == "remove_from_blocklist":
        import json as _json
        app = msg.get("app", "").strip()
        apps = _json.loads(db.get_setting("blocklist_apps", "[]"))
        apps = [a for a in apps if a != app]
        db.set_setting("blocklist_apps", _json.dumps(apps))
        return {"type": "ok"}

    if t == "schedule_automation":
        automation_id = msg.get("automation_id")
        schedule = msg.get("schedule", {})
        if not isinstance(automation_id, int):
            return {"type": "error", "message": "automation_id must be an integer"}
        automation = db.get_automation_by_id(automation_id)
        if automation is None:
            return {"type": "error", "message": "automation not found"}
        name = automation.get("name", f"automation_{automation_id}")
        script_body = automation.get("script_body", "")
        # Write script to macros dir for persistent scheduling
        _macros_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "data", "macros"
        )
        os.makedirs(_macros_dir, exist_ok=True)
        name_slug = "".join(
            c if (c.isalnum() or c == "_") else "_"
            for c in name.lower().replace(" ", "_")
        )
        script_path = os.path.abspath(os.path.join(_macros_dir, f"{name_slug}_sched.py"))
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_body)
        except OSError as e:
            return {"type": "error", "message": f"Could not write script: {e}"}
        result = scheduler.schedule_automation(automation_id, name_slug, script_path, schedule)
        return {"type": "schedule_result", **result}

    if t == "unschedule_automation":
        automation_id = msg.get("automation_id")
        if not isinstance(automation_id, int):
            return {"type": "error", "message": "automation_id must be an integer"}
        automation = db.get_automation_by_id(automation_id)
        if automation is None:
            return {"type": "error", "message": "automation not found"}
        name = automation.get("name", f"automation_{automation_id}")
        name_slug = "".join(
            c if (c.isalnum() or c == "_") else "_"
            for c in name.lower().replace(" ", "_")
        )
        result = scheduler.unschedule_automation(name_slug)
        return {"type": "unschedule_result", **result}

    if t == "list_scheduled":
        data = scheduler.list_scheduled()
        return {"type": "scheduled_list", "data": data}

    if t == "parse_nl_instruction":
        instruction = msg.get("instruction", "")
        if not instruction:
            return {"type": "error", "message": "instruction must be non-empty"}
        result = nl_planner.parse_instruction(instruction)
        if not result.get("ok"):
            return {"type": "error", "message": result.get("error", "parse failed")}
        return {"type": "nl_plan", "steps": result["steps"], "summary": result.get("summary", "")}

    if t == "refine_nl_plan":
        instruction = msg.get("instruction", "")
        steps = msg.get("steps", [])
        feedback = msg.get("feedback", "")
        if not isinstance(steps, list):
            return {"type": "error", "message": "steps must be a list"}
        result = nl_planner.refine_plan(instruction, steps, feedback)
        if not result.get("ok"):
            return {"type": "error", "message": result.get("error", "refine failed")}
        return {"type": "nl_plan", "steps": result["steps"], "summary": result.get("summary", "")}

    if t == "save_nl_automation":
        instruction = msg.get("instruction", "")
        steps = msg.get("steps", [])
        summary = msg.get("summary", "")
        if not isinstance(steps, list):
            return {"type": "error", "message": "steps must be a list"}
        automation_id = nl_planner.save_nl_automation(instruction, steps, summary)
        return {"type": "ok", "id": automation_id}

    if t == "replay_session":
        steps = msg.get("steps", [])
        use_vision = msg.get("use_vision", True)
        verify_each = msg.get("verify_each", False)
        if not isinstance(steps, list):
            return {"type": "error", "message": "steps must be a list"}
        result = vision_replay.replay_session(steps, use_vision=use_vision, verify_each=verify_each)
        return {"type": "replay_result", "result": result}

    if t == "describe_replay_plan":
        steps = msg.get("steps", [])
        if not isinstance(steps, list):
            return {"type": "error", "message": "steps must be a list"}
        plan = vision_replay.describe_replay_plan(steps)
        return {"type": "replay_plan", "plan": plan["plan"]}

    if t == "replay_step":
        step = msg.get("step", {})
        use_vision = msg.get("use_vision", True)
        if not isinstance(step, dict):
            return {"type": "error", "message": "step must be a dict"}
        result = vision_replay.replay_step(step, use_vision=use_vision)
        return {"type": "step_result", "result": result}

    if t == "get_automation_steps":
        automation_id = msg.get("automation_id")
        if not isinstance(automation_id, int):
            return {"type": "error", "message": "automation_id must be an integer"}
        automation = db.get_automation_by_id(automation_id)
        if automation is None:
            return {"type": "error", "message": "automation not found"}
        steps = vision_replay.parse_steps_from_pyautogui(automation.get("script_body", ""))
        return {"type": "automation_steps", "steps": steps}

    if t == "check_vision":
        available = vision_ai.is_vision_available()
        backend, _, model = vision_ai._get_config()
        return {
            "type": "vision_status",
            "available": available,
            "backend": backend if available else None,
            "model": model if available else None,
            "backends": vision_ai.get_available_backends(),
        }

    if t == "set_vision_config":
        backend = msg.get("backend", "")
        api_key = msg.get("api_key", "")
        db.set_setting("vision_backend", backend)
        if backend:
            db.set_setting(f"vision_api_key_{backend}", api_key)
        return {"type": "ok"}

    if t == "test_vision_connection":
        backend = msg.get("backend", "")
        api_key = msg.get("api_key", "")
        result = vision_ai.test_connection(backend, api_key)
        return {
            "type": "connection_test",
            "ok": result.get("ok", False),
            "error": result.get("error"),
            "model": result.get("model"),
        }

    if t == "take_screenshot":
        data = vision_capture.take_screenshot()
        return {"type": "screenshot", "data": data}

    if t == "analyze_screen":
        instruction = msg.get("instruction", "")
        screenshot = vision_capture.take_screenshot()
        if not screenshot:
            return {"type": "error", "message": "screenshot failed"}
        result = vision_ai.analyze_screen(screenshot, instruction)
        return {"type": "analysis", "result": result}

    if t == "find_element":
        description = msg.get("description", "")
        screenshot = vision_capture.take_screenshot()
        if not screenshot:
            return {"type": "error", "message": "screenshot failed"}
        result = vision_ai.find_element(screenshot, description)
        return {"type": "element_location", "result": result}

    if t == "describe_screen":
        screenshot = vision_capture.take_screenshot()
        if not screenshot:
            return {"type": "error", "message": "screenshot failed"}
        result = vision_ai.describe_screen(screenshot)
        return {"type": "screen_description", "result": result}

    if t == "verify_action":
        expected_state = msg.get("expected_state", "")
        screenshot = vision_capture.take_screenshot()
        if not screenshot:
            return {"type": "error", "message": "screenshot failed"}
        result = vision_ai.verify_action(screenshot, expected_state)
        return {"type": "verification", "result": result}

    if t == "generate_dom_playwright":
        session_id = msg.get("session_id", "")
        script = playwright_gen.generate_from_dom_events(session_id)
        return {"type": "dom_playwright_script", "script": script}

    if t == "get_extension_zip":
        try:
            buf = io.BytesIO()
            ext_dir = os.path.abspath(_CHROME_EXT_DIR)
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _dirs, files in os.walk(ext_dir):
                    for fname in files:
                        full = os.path.join(root, fname)
                        arcname = os.path.relpath(full, ext_dir)
                        zf.write(full, arcname)
            data = base64.b64encode(buf.getvalue()).decode()
            return {"type": "extension_zip", "data": data}
        except Exception as exc:
            logging.exception("get_extension_zip error")
            return {"type": "error", "message": str(exc)}

    if t == "shutdown":
        logging.info("Shutdown received — stopping capture and exiting")
        capture.stop_capture()
        _write({"type": "ok", "message": "shutting down"})
        sys.exit(0)

    return {"type": "error", "message": "unknown command"}


def main() -> None:
    logging.info("Sidecar started (pid=%d)", os.getpid())
    t = threading.Thread(target=_start_http_server, daemon=True, name="http-server")
    t.start()
    logging.info("HTTP server started on port %d", _HTTP_PORT)
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
            resp = _handle(msg)
            if resp is not None:
                _write(resp)
        except Exception as exc:
            logging.exception("Error handling %r", raw)
            _write({"type": "error", "message": str(exc)})


if __name__ == "__main__":
    main()
