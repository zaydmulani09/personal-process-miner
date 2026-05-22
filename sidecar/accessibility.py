"""
Accessibility tree reader using pywinauto (Windows).
Gracefully degrades on macOS/Linux with an error message.
"""
import sys
import os

def get_screen_tree(max_depth: int = 4) -> dict:
    """
    Walk the foreground window's UI element tree up to max_depth.
    Returns dict with window_title, window_rect, elements list.
    Never raises.
    """
    try:
        import pywinauto
        from pywinauto import Desktop
        desktop = Desktop(backend="uia")
        # get foreground window
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return {"ok": False, "error": "no foreground window"}
        app = desktop.window(handle=hwnd)
        title = app.window_text()
        rect = app.rectangle()
        window_rect = {"left": rect.left, "top": rect.top, "right": rect.right, "bottom": rect.bottom}
        elements = []
        _walk_tree(app, elements, depth=0, max_depth=max_depth)
        return {
            "ok": True,
            "window_title": title,
            "window_rect": window_rect,
            "elements": elements,
        }
    except ImportError:
        return {"ok": False, "error": "pywinauto not installed — run: pip install pywinauto"}
    except Exception as e:
        print(f"[accessibility] get_screen_tree error: {repr(e)}", file=sys.stderr)
        return {"ok": False, "error": str(e)}


def _walk_tree(element, results: list, depth: int, max_depth: int):
    if depth > max_depth:
        return
    try:
        ctrl_type = element.element_info.control_type or ""
        name = (element.window_text() or "").strip()
        if not name and not ctrl_type:
            return
        try:
            rect = element.rectangle()
            r = {"left": rect.left, "top": rect.top, "right": rect.right, "bottom": rect.bottom}
            cx = (rect.left + rect.right) // 2
            cy = (rect.top + rect.bottom) // 2
        except Exception:
            r = {"left": 0, "top": 0, "right": 0, "bottom": 0}
            cx, cy = 0, 0
        try:
            visible = element.is_visible()
        except Exception:
            visible = True
        try:
            enabled = element.is_enabled()
        except Exception:
            enabled = True
        value = ""
        try:
            value = element.get_value() or ""
        except Exception:
            pass
        if visible and (name or ctrl_type):
            results.append({
                "name": name,
                "control_type": ctrl_type,
                "rect": r,
                "center": {"x": cx, "y": cy},
                "enabled": enabled,
                "visible": visible,
                "value": value,
            })
        for child in element.children():
            _walk_tree(child, results, depth + 1, max_depth)
    except Exception:
        pass


def get_active_window_title() -> str:
    """Returns title of focused window. Never raises."""
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value
    except Exception as e:
        print(f"[accessibility] get_active_window_title error: {repr(e)}", file=sys.stderr)
        return ""


def find_element_by_description(description: str, tree: dict):
    """
    Find element whose name best matches description.
    Returns element dict or None.
    """
    if not tree or "elements" not in tree:
        return None
    desc_lower = description.lower()
    elements = tree.get("elements", [])
    # exact contains match first
    for el in elements:
        if desc_lower in (el.get("name") or "").lower():
            return el
    # word overlap fallback
    desc_words = set(desc_lower.split())
    best, best_score = None, 0
    for el in elements:
        name_words = set((el.get("name") or "").lower().split())
        score = len(desc_words & name_words)
        if score > best_score:
            best, best_score = el, score
    return best if best_score > 0 else None


def tree_to_text(tree: dict) -> str:
    """
    Convert tree dict to readable text for AI consumption.
    """
    if not tree or not tree.get("ok", True):
        return f"Screen tree unavailable: {tree.get('error', 'unknown error')}"
    title = tree.get("window_title", "Unknown")
    wr = tree.get("window_rect", {})
    w = wr.get("right", 0) - wr.get("left", 0)
    h = wr.get("bottom", 0) - wr.get("top", 0)
    lines = [f"Window: {title} ({w}x{h})"]
    for el in tree.get("elements", []):
        ct = el.get("control_type", "?")
        name = el.get("name", "")
        cx = el.get("center", {}).get("x", 0)
        cy = el.get("center", {}).get("y", 0)
        val = el.get("value", "")
        line = f"[{ct}] {name} | center: ({cx}, {cy})"
        if val:
            line += f' | value: "{val}"'
        lines.append(line)
    return "\n".join(lines)
