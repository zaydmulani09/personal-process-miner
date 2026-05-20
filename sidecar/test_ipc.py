"""Standalone IPC smoke-test — run with: py sidecar/test_ipc.py"""
import json
import subprocess
import sys
import os

PYTHON = sys.executable
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")


def _send(proc: subprocess.Popen, msg: dict) -> dict:
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("Sidecar closed stdout unexpectedly")
    return json.loads(line)


def main() -> None:
    proc = subprocess.Popen(
        [PYTHON, SCRIPT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        # ping → pong
        resp = _send(proc, {"type": "ping"})
        assert resp == {"type": "pong"}, f"ping failed: {resp}"

        # status → running
        resp = _send(proc, {"type": "status"})
        assert resp == {"type": "status", "state": "running"}, f"status failed: {resp}"

        # unknown → error
        resp = _send(proc, {"type": "doesnotexist"})
        assert resp.get("type") == "error", f"unknown-cmd failed: {resp}"

        # start_capture → ok
        resp = _send(proc, {"type": "start_capture"})
        assert resp == {"type": "ok", "message": "capture started"}, f"start_capture failed: {resp}"

        # get_events → events list
        resp = _send(proc, {"type": "get_events", "limit": 5})
        assert resp.get("type") == "events", f"get_events type failed: {resp}"
        assert isinstance(resp.get("data"), list), f"get_events data not list: {resp}"

        # stop_capture → ok
        resp = _send(proc, {"type": "stop_capture"})
        assert resp == {"type": "ok", "message": "capture stopped"}, f"stop_capture failed: {resp}"

        # get_sessions → sessions list
        resp = _send(proc, {"type": "get_sessions", "limit": 5})
        assert resp.get("type") == "sessions", f"get_sessions type failed: {resp}"
        assert isinstance(resp.get("data"), list), f"get_sessions data not list: {resp}"

        # get_workflows → workflows list
        resp = _send(proc, {"type": "get_workflows"})
        assert resp.get("type") == "workflows", f"get_workflows type failed: {resp}"
        assert isinstance(resp.get("data"), list), f"get_workflows data not list: {resp}"

        # get_automations → automations list
        resp = _send(proc, {"type": "get_automations"})
        assert resp.get("type") == "automations", f"get_automations type failed: {resp}"
        assert isinstance(resp.get("data"), list), f"get_automations data not list: {resp}"

        # label_workflow with empty name → error
        resp = _send(proc, {"type": "label_workflow", "workflow_id": 1, "name": "", "steps": ["A"]})
        assert resp.get("type") == "error", f"label empty name should error: {resp}"

        # label_workflow / delete_workflow with valid data
        resp = _send(proc, {"type": "get_workflows"})
        assert resp.get("type") == "workflows"
        workflows = resp.get("data", [])
        assert len(workflows) > 0, "No workflows in DB — run `py sidecar/seed.py` first"
        wf_id = workflows[0]["id"]

        resp = _send(proc, {"type": "label_workflow", "workflow_id": wf_id, "name": "Test Label", "steps": ["A", "B"]})
        assert resp.get("type") == "ok", f"label_workflow valid failed: {resp}"

        resp = _send(proc, {"type": "delete_workflow", "workflow_id": wf_id})
        assert resp.get("type") == "ok", f"delete_workflow valid failed: {resp}"

        # delete_workflow with nonexistent id → error
        resp = _send(proc, {"type": "delete_workflow", "workflow_id": 999999})
        assert resp.get("type") == "error", f"delete nonexistent should error: {resp}"

        # --- Automation management tests ---

        # Fetch existing automations (need at least one — run test_macro_recorder.py first)
        resp = _send(proc, {"type": "get_automations"})
        assert resp.get("type") == "automations"
        automations = resp.get("data", [])
        assert len(automations) > 0, (
            "No automations in DB — run py sidecar/test_macro_recorder.py first"
        )
        auto_id = automations[0]["id"]

        # run_automation → run_result (script may fail; just check response type)
        resp = _send(proc, {"type": "run_automation", "automation_id": auto_id})
        assert resp.get("type") == "run_result", f"run_automation type failed: {resp}"
        assert "status" in resp, f"run_result missing status: {resp}"
        assert resp.get("automation_id") == auto_id

        # update_automation_name → ok
        resp = _send(proc, {
            "type": "update_automation_name",
            "automation_id": auto_id,
            "name": "Renamed Automation",
        })
        assert resp.get("type") == "ok", f"update_automation_name failed: {resp}"
        assert resp.get("automation_id") == auto_id

        # delete_automation with valid id → ok
        resp = _send(proc, {"type": "delete_automation", "automation_id": auto_id})
        assert resp.get("type") == "ok", f"delete_automation valid failed: {resp}"

        # delete_automation with nonexistent id → error
        resp = _send(proc, {"type": "delete_automation", "automation_id": 999999})
        assert resp.get("type") == "error", f"delete nonexistent automation should error: {resp}"

        # get_automation_stats → automation_stats with all 4 keys
        resp = _send(proc, {"type": "get_automation_stats"})
        assert resp.get("type") == "automation_stats", f"get_automation_stats type failed: {resp}"
        data = resp.get("data", {})
        for key in ("total_automations", "total_runs", "successful_runs",
                    "estimated_time_saved_seconds"):
            assert key in data, f"automation_stats missing key {key!r}: {data}"

        # --- Privacy settings IPC tests ---

        # get_settings → type: settings, all 5 default keys present
        resp = _send(proc, {"type": "get_settings"})
        assert resp.get("type") == "settings", f"get_settings type failed: {resp}"
        data = resp.get("data", {})
        for key in ("blocklist_apps", "allowlist_apps", "retention_days",
                    "capture_mouse_moves", "capture_keystrokes"):
            assert key in data, f"get_settings missing key {key!r}: {data}"

        # set_setting → ok
        resp = _send(proc, {"type": "set_setting", "key": "retention_days", "value": "7"})
        assert resp.get("type") == "ok", f"set_setting failed: {resp}"

        # add_to_blocklist → ok, remove_from_blocklist → ok
        resp = _send(proc, {"type": "add_to_blocklist", "app": "test_app_xyz"})
        assert resp.get("type") == "ok", f"add_to_blocklist failed: {resp}"

        resp = _send(proc, {"type": "get_blocklist"})
        assert resp.get("type") == "blocklist", f"get_blocklist type failed: {resp}"
        assert "test_app_xyz" in resp.get("apps", []), f"blocklist missing added app: {resp}"

        resp = _send(proc, {"type": "remove_from_blocklist", "app": "test_app_xyz"})
        assert resp.get("type") == "ok", f"remove_from_blocklist failed: {resp}"

        resp = _send(proc, {"type": "get_blocklist"})
        assert "test_app_xyz" not in resp.get("apps", []), f"blocklist still has removed app: {resp}"

        # shutdown → clean exit
        resp = _send(proc, {"type": "shutdown"})
        assert resp.get("type") == "ok", f"shutdown ack failed: {resp}"
        proc.wait(timeout=5)
        assert proc.returncode == 0, f"exit code {proc.returncode}"

    except Exception as exc:
        proc.kill()
        print(f"FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

    print("ALL IPC TESTS PASSED")


if __name__ == "__main__":
    main()
