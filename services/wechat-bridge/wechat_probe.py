"""Read-only Windows UI Automation diagnostics for the desktop Weixin client."""

from __future__ import annotations

from typing import Any


def probe_weixin(max_controls: int = 160) -> dict[str, Any]:
    try:
        from pywinauto import Desktop
    except ImportError:
        return {
            "available": False,
            "error": "pywinauto is not installed",
            "install": "python -m pip install -r services/wechat-bridge/requirements.txt",
        }

    windows = []
    try:
        candidates = Desktop(backend="uia").windows(process=None)
        for window in candidates:
            try:
                process_id = window.element_info.process_id
                title = window.window_text().strip()
                class_name = window.element_info.class_name or ""
                if "微信" not in title and "Weixin" not in title and "WeChat" not in title:
                    continue
                controls = []
                for control in window.descendants()[:max_controls]:
                    info = control.element_info
                    name = (info.name or "").strip()
                    if name:
                        controls.append(
                            {
                                "name": name[:240],
                                "control_type": info.control_type,
                                "automation_id": info.automation_id,
                                "class_name": info.class_name,
                            }
                        )
                windows.append(
                    {
                        "title": title,
                        "process_id": process_id,
                        "class_name": class_name,
                        "controls": controls,
                    }
                )
            except Exception:
                continue
    except Exception as exc:
        return {"available": True, "error": str(exc), "windows": []}
    weixin_windows = [item for item in windows if item["title"] == "微信"]
    custom_rendered = bool(weixin_windows) and all(
        not any(control["control_type"] in {"Text", "ListItem", "Edit"} for control in item["controls"])
        for item in weixin_windows
    )
    return {
        "available": True,
        "windows": windows,
        "message_text_accessible": not custom_rendered,
        "recommended_adapter": "uia" if not custom_rendered else "window_capture_ocr",
    }
