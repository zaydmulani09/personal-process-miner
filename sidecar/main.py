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


def _write(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _handle(msg: dict) -> dict | None:
    t = msg.get("type")
    if t == "ping":
        return {"type": "pong"}
    if t == "status":
        return {"type": "status", "state": "running"}
    if t == "shutdown":
        logging.info("Shutdown received — exiting")
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
