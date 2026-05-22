import ctypes
import json
import logging
import os
import threading
from ctypes import wintypes
from datetime import datetime, timezone

try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except ImportError:
    gw = None
    HAS_PYGETWINDOW = False

try:
    from pynput import keyboard, mouse
    HAS_PYNPUT = True
except ImportError:
    keyboard = None
    mouse = None
    HAS_PYNPUT = False

import db

_MODIFIER_PREFIXES = ("Key.shift", "Key.ctrl", "Key.alt", "Key.cmd", "Key.meta")

_kb_listener = None
_mouse_listener = None
_poll_thread: threading.Thread | None = None
_stop_event = threading.Event()

# Privacy settings — loaded once at start_capture()
_blocklist: list[str] = []
_allowlist: list[str] = []
_capture_keystrokes: bool = False
_capture_mouse_moves: bool = True


def _app_allowed(app_name: str | None) -> bool:
    name = (app_name or "").lower()
    if _blocklist and any(b in name for b in _blocklist):
        return False
    if _allowlist and not any(a in name for a in _allowlist):
        return False
    return True


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_exe_name(hwnd: int) -> str:
    try:
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value
        )
        if not h:
            return ""
        buf = ctypes.create_unicode_buffer(260)
        size = wintypes.DWORD(260)
        ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
        ctypes.windll.kernel32.CloseHandle(h)
        return os.path.basename(buf.value) if buf.value else ""
    except Exception:
        return ""


def _window_poller() -> None:
    last_title: str | None = None
    while not _stop_event.is_set():
        try:
            if not HAS_PYGETWINDOW:
                _stop_event.wait(1.0)
                continue
            win = gw.getActiveWindow()
            title = win.title if win else ""
            if title != last_title:
                last_title = title
                hwnd = getattr(win, "_hWnd", None)
                app_name = _get_exe_name(hwnd) if hwnd else title
                if _app_allowed(app_name):
                    db.insert_event(
                        {
                            "timestamp": _now(),
                            "event_type": "window_focus",
                            "app_name": app_name or title,
                            "window_title": title,
                        }
                    )
        except Exception:
            logging.exception("Window poll error")
        _stop_event.wait(0.5)


def _on_press(key) -> None:
    try:
        name = str(key)
        if any(name.startswith(p) for p in _MODIFIER_PREFIXES):
            return
        detail = name if _capture_keystrokes else "[key]"
        db.insert_event({"timestamp": _now(), "event_type": "key_press", "detail": detail})
    except Exception:
        logging.exception("Key press handler error")


def _on_move(x: int, y: int) -> None:
    pass  # filtered at listener level via suppress; kept for pynput compat


def _on_click(x: int, y: int, button, pressed: bool) -> None:
    if not pressed:
        return
    try:
        db.insert_event(
            {
                "timestamp": _now(),
                "event_type": "mouse_click",
                "detail": str(button),
                "x": x,
                "y": y,
            }
        )
    except Exception:
        logging.exception("Mouse click handler error")


def start_capture() -> None:
    global _kb_listener, _mouse_listener, _poll_thread
    global _blocklist, _allowlist, _capture_keystrokes, _capture_mouse_moves
    _stop_event.clear()

    # Load privacy settings once.
    _blocklist = [s.lower() for s in json.loads(db.get_setting("blocklist_apps", "[]"))]
    _allowlist = [s.lower() for s in json.loads(db.get_setting("allowlist_apps", "[]"))]
    _capture_keystrokes = db.get_setting("capture_keystrokes", "false") == "true"
    _capture_mouse_moves = db.get_setting("capture_mouse_moves", "true") == "true"

    _poll_thread = threading.Thread(target=_window_poller, daemon=True, name="window-poller")
    _poll_thread.start()

    if HAS_PYNPUT:
        _kb_listener = keyboard.Listener(on_press=_on_press)
        _kb_listener.start()

        _mouse_listener = mouse.Listener(
            on_click=_on_click,
            on_move=None,  # mouse moves never stored
        )
        _mouse_listener.start()
    else:
        logging.warning("pynput not available — keyboard/mouse capture disabled")

    logging.info("Capture started")


def stop_capture() -> None:
    global _kb_listener, _mouse_listener, _poll_thread
    _stop_event.set()

    if _kb_listener:
        _kb_listener.stop()
        _kb_listener = None

    if _mouse_listener:
        _mouse_listener.stop()
        _mouse_listener = None

    if _poll_thread:
        _poll_thread.join(timeout=2.0)
        _poll_thread = None

    logging.info("Capture stopped")
