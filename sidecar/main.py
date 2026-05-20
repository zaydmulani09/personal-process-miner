import sys
import json
import logging
import os

_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sidecar.log")
logging.basicConfig(
    filename=_log_path,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)

import capture
import db
import fingerprinter
import segmenter


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
