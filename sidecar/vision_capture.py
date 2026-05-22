import base64
import logging
import tempfile
import os

try:
    import mss
    import mss.tools
except Exception:
    mss = None


def take_screenshot() -> str | None:
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            img = sct.grab(monitor)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                tmp = f.name
            mss.tools.to_png(img.rgb, img.size, output=tmp)
            with open(tmp, "rb") as f:
                data = f.read()
            os.unlink(tmp)
            return base64.b64encode(data).decode("utf-8")
    except Exception as exc:
        logging.warning("take_screenshot failed: %s", exc)
        return None


def take_region_screenshot(x: int, y: int, w: int, h: int) -> str | None:
    try:
        with mss.mss() as sct:
            region = {"top": y, "left": x, "width": w, "height": h}
            img = sct.grab(region)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                tmp = f.name
            mss.tools.to_png(img.rgb, img.size, output=tmp)
            with open(tmp, "rb") as f:
                data = f.read()
            os.unlink(tmp)
            return base64.b64encode(data).decode("utf-8")
    except Exception as exc:
        logging.warning("take_region_screenshot failed: %s", exc)
        return None


def get_screen_size() -> dict:
    try:
        with mss.mss() as sct:
            m = sct.monitors[1]
            return {"width": m["width"], "height": m["height"]}
    except Exception as exc:
        logging.warning("get_screen_size failed: %s", exc)
        return {"width": 1920, "height": 1080}
