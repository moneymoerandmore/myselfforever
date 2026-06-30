"""Read-only capture helpers for the custom-rendered desktop Weixin window."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def list_weixin_windows() -> list[dict[str, Any]]:
    import win32gui
    import win32process

    windows: list[dict[str, Any]] = []

    def collect(hwnd: int, _: Any) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).strip()
        class_name = win32gui.GetClassName(hwnd)
        _, process_id = win32process.GetWindowThreadProcessId(hwnd)
        if title in {"微信", "Weixin"} or class_name in {"Qt51514QWindowIcon", "MMUIRenderSubWindowHW"}:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            windows.append(
                {
                    "hwnd": hwnd,
                    "title": title,
                    "class_name": class_name,
                    "process_id": process_id,
                    "rect": [left, top, right, bottom],
                    "width": right - left,
                    "height": bottom - top,
                }
            )

    win32gui.EnumWindows(collect, None)
    return sorted(windows, key=lambda item: item["width"] * item["height"], reverse=True)


def capture_weixin(output: Path) -> dict[str, Any]:
    from PIL import ImageGrab

    windows = [item for item in list_weixin_windows() if item["width"] > 500 and item["height"] > 400]
    if not windows:
        raise RuntimeError("visible Weixin window not found")
    window = windows[0]
    left, top, right, bottom = window["rect"]
    image = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return {**window, "output": str(output), "image_size": list(image.size)}


def capture_weixin_offscreen(output: Path) -> dict[str, Any]:
    import ctypes
    import win32gui
    import win32ui
    from PIL import Image

    windows = [item for item in list_weixin_windows() if item["width"] > 500 and item["height"] > 400]
    if not windows:
        raise RuntimeError("visible Weixin window not found")
    window = windows[0]
    hwnd = window["hwnd"]
    width, height = window["width"], window["height"]
    window_dc = win32gui.GetWindowDC(hwnd)
    source_dc = win32ui.CreateDCFromHandle(window_dc)
    memory_dc = source_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(source_dc, width, height)
    memory_dc.SelectObject(bitmap)
    result = ctypes.windll.user32.PrintWindow(hwnd, memory_dc.GetSafeHdc(), 2)
    info = bitmap.GetInfo()
    bits = bitmap.GetBitmapBits(True)
    image = Image.frombuffer(
        "RGB",
        (info["bmWidth"], info["bmHeight"]),
        bits,
        "raw",
        "BGRX",
        0,
        1,
    )
    win32gui.DeleteObject(bitmap.GetHandle())
    memory_dc.DeleteDC()
    source_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, window_dc)
    if result != 1:
        raise RuntimeError(f"PrintWindow failed: {result}")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return {**window, "output": str(output), "image_size": list(image.size), "capture": "PrintWindow"}
