"""
Accessibility tree reader and UIA-native execution engine (Windows).
pyautogui used ONLY for keypress and scroll.
Gracefully degrades on macOS/Linux.
"""
import sys
import os

try:
    from pywinauto import Application, Desktop
    _HAS_PYWINAUTO = True
except Exception:
    Application = None
    Desktop = None
    _HAS_PYWINAUTO = False

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    _HAS_PYAUTOGUI = True
except Exception:
    pyautogui = None
    _HAS_PYAUTOGUI = False


def get_window_tree(window_title_re: str = None) -> dict:
    """
    Walk UI element tree up to 4 levels deep using UIA backend.
    If window_title_re given: connect by title regex.
    Otherwise: uses foreground window.
    Filters elements where both name and automation_id are empty.
    Never raises.
    """
    if not _HAS_PYWINAUTO:
        return {"ok": False, "error": "pywinauto not installed — run: pip install pywinauto"}
    try:
        if window_title_re:
            app = Application(backend="uia").connect(title_re=window_title_re)
            win = app.top_window()
        else:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return {"ok": False, "error": "no foreground window"}
            desktop = Desktop(backend="uia")
            win = desktop.window(handle=hwnd)

        title = ""
        try:
            title = win.window_text()
        except Exception:
            pass

        elements = []
        _walk_tree_uia(win, elements, depth=0, max_depth=4)

        return {
            "ok": True,
            "window_title": title,
            "elements": elements,
        }
    except ImportError:
        return {"ok": False, "error": "pywinauto not installed — run: pip install pywinauto"}
    except Exception as e:
        print(f"[accessibility] get_window_tree error: {repr(e)}", file=sys.stderr)
        return {"ok": False, "error": str(e)}


def _walk_tree_uia(element, results: list, depth: int, max_depth: int):
    if depth > max_depth:
        return
    try:
        el_info = element.element_info
        ctrl_type = el_info.control_type or ""
        name = (element.window_text() or "").strip()
        try:
            automation_id = el_info.automation_id or ""
        except Exception:
            automation_id = ""
        try:
            class_name = el_info.class_name or ""
        except Exception:
            class_name = ""

        if not name and not automation_id:
            for child in element.children():
                _walk_tree_uia(child, results, depth + 1, max_depth)
            return

        try:
            rect = element.rectangle()
            cx = (rect.left + rect.right) // 2
            cy = (rect.top + rect.bottom) // 2
            r = {"left": rect.left, "top": rect.top, "right": rect.right, "bottom": rect.bottom}
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

        results.append({
            "name": name,
            "control_type": ctrl_type,
            "automation_id": automation_id,
            "class_name": class_name,
            "enabled": enabled,
            "visible": visible,
            "rect": r,
            "center": {"x": cx, "y": cy},
        })

        for child in element.children():
            _walk_tree_uia(child, results, depth + 1, max_depth)
    except Exception:
        pass


def _find_control(win, automation_id: str, name: str, ctrl_type: str):
    """Fallback chain: automation_id → name+type → name only → type+index=0. Returns control or None."""
    if automation_id:
        try:
            ctrl = win.child_window(auto_id=automation_id)
            ctrl.wait("exists", timeout=2)
            return ctrl
        except Exception:
            pass

    if name and ctrl_type:
        try:
            ctrl = win.child_window(title=name, control_type=ctrl_type)
            ctrl.wait("exists", timeout=2)
            return ctrl
        except Exception:
            pass

    if name:
        try:
            ctrl = win.child_window(title=name)
            ctrl.wait("exists", timeout=2)
            return ctrl
        except Exception:
            pass

    if ctrl_type:
        try:
            ctrl = win.child_window(control_type=ctrl_type, found_index=0)
            ctrl.wait("exists", timeout=2)
            return ctrl
        except Exception:
            pass

    return None


def execute_action(action: dict) -> dict:
    """
    Execute one UIA-native action. Never raises.
    action schema:
      {action: str, target: {name, control_type, automation_id, window_title_contains},
       value: str, key: str, reason: str}
    Returns {"ok": bool, "error": str|None, "method": "uia"|"pyautogui"|"skipped"|"error"}
    """
    if not action or "action" not in action:
        return {"ok": False, "error": "missing action key", "method": "error"}

    atype = (action.get("action") or "").strip().lower()
    target = action.get("target") or {}
    value = action.get("value") or ""
    key = action.get("key") or ""

    if not atype:
        return {"ok": False, "error": "empty action type", "method": "error"}

    # keypress and scroll: only place pyautogui is used
    if atype == "keypress":
        if not _HAS_PYAUTOGUI:
            return {"ok": False, "error": "pyautogui not available", "method": "pyautogui"}
        try:
            k = key.strip()
            if "+" in k:
                parts = [p.strip().lower() for p in k.split("+") if p.strip()]
                pyautogui.hotkey(*parts)
            else:
                pyautogui.press(k.lower() if k else "enter")
            return {"ok": True, "error": None, "method": "pyautogui"}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "method": "pyautogui"}

    if atype == "scroll":
        if not _HAS_PYAUTOGUI:
            return {"ok": False, "error": "pyautogui not available", "method": "pyautogui"}
        try:
            amount = int(value) if value else 3
            pyautogui.scroll(amount)
            return {"ok": True, "error": None, "method": "pyautogui"}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "method": "pyautogui"}

    if not _HAS_PYWINAUTO:
        return {"ok": False, "error": "pywinauto not installed", "method": "uia"}

    window_title = target.get("window_title_contains") or ""
    name = target.get("name") or ""
    ctrl_type = target.get("control_type") or ""
    automation_id = target.get("automation_id") or ""

    try:
        if atype == "focus_window":
            app = Application(backend="uia").connect(title_re=window_title or ".*")
            win = app.top_window()
            win.set_focus()
            return {"ok": True, "error": None, "method": "uia"}

        # Connect to window
        if window_title:
            try:
                app = Application(backend="uia").connect(title_re=window_title)
                win = app.top_window()
            except Exception:
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                desktop = Desktop(backend="uia")
                win = desktop.window(handle=hwnd)
        else:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            desktop = Desktop(backend="uia")
            win = desktop.window(handle=hwnd)

        if atype == "menu_select":
            win.menu_select(value)
            return {"ok": True, "error": None, "method": "uia"}

        ctrl = _find_control(win, automation_id, name, ctrl_type)
        if ctrl is None:
            return {"ok": False, "error": f"element not found: {name or automation_id or ctrl_type}", "method": "uia"}

        ctrl.wait("exists enabled visible", timeout=5)

        if atype == "click":
            ctrl.click_input()
            return {"ok": True, "error": None, "method": "uia"}

        if atype == "type":
            try:
                ctrl.set_edit_text(value)
            except Exception:
                ctrl.type_keys(value)
            return {"ok": True, "error": None, "method": "uia"}

        return {"ok": True, "error": None, "method": "skipped"}

    except Exception as exc:
        print(f"[accessibility] execute_action error ({atype}): {repr(exc)}", file=sys.stderr)
        return {"ok": False, "error": str(exc), "method": "uia"}


def get_screen_tree(max_depth: int = 4) -> dict:
    """Backward-compat shim — delegates to get_window_tree."""
    result = get_window_tree()
    if result.get("ok"):
        result.setdefault("window_rect", {"left": 0, "top": 0, "right": 0, "bottom": 0})
        for el in result.get("elements", []):
            el.setdefault("value", "")
    return result


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
    """Find element whose name best matches description. Returns element dict or None."""
    if not tree or "elements" not in tree:
        return None
    desc_lower = description.lower()
    elements = tree.get("elements", [])
    for el in elements:
        if desc_lower in (el.get("name") or "").lower():
            return el
    desc_words = set(desc_lower.split())
    best, best_score = None, 0
    for el in elements:
        name_words = set((el.get("name") or "").lower().split())
        score = len(desc_words & name_words)
        if score > best_score:
            best, best_score = el, score
    return best if best_score > 0 else None


def tree_to_text(tree: dict) -> str:
    """Convert tree dict to readable text for AI consumption."""
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
        auto_id = el.get("automation_id", "")
        cx = el.get("center", {}).get("x", 0)
        cy = el.get("center", {}).get("y", 0)
        val = el.get("value", "")
        line = f"[{ct}] {name}"
        if auto_id:
            line += f" (id={auto_id})"
        line += f" | center: ({cx}, {cy})"
        if val:
            line += f' | value: "{val}"'
        lines.append(line)
    return "\n".join(lines)
