import os
import json
import logging
import subprocess
import sys
import tempfile

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

_UNSAFE_PATTERNS = ["os.system", "subprocess", "shutil.rmtree", "__import__"]


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

    if t == "shutdown":
        logging.info("Shutdown received — stopping capture and exiting")
        capture.stop_capture()
        _write({"type": "ok", "message": "shutting down"})
        sys.exit(0)

    return {"type": "error", "message": "unknown command"}


def main() -> None:
    logging.info("Sidecar started (pid=%d)", os.getpid())
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
