"""Standalone IPC smoke-test — run with: python sidecar/test_ipc.py"""
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

        # shutdown → clean exit
        resp = _send(proc, {"type": "shutdown"})
        assert resp.get("type") == "ok", f"shutdown ack failed: {resp}"
        proc.wait(timeout=3)
        assert proc.returncode == 0, f"exit code {proc.returncode}"

    except Exception as exc:
        proc.kill()
        print(f"FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
