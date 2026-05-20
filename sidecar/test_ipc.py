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

        # shutdown → clean exit
        resp = _send(proc, {"type": "shutdown"})
        assert resp.get("type") == "ok", f"shutdown ack failed: {resp}"
        proc.wait(timeout=5)
        assert proc.returncode == 0, f"exit code {proc.returncode}"

    except Exception as exc:
        proc.kill()
        print(f"FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
