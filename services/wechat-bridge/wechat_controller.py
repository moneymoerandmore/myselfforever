"""Focused-input sender for the personal Weixin client.

This module intentionally does not activate Weixin, move the mouse, click, or
search for an input box. The user must keep the target group input focused.
"""

from __future__ import annotations

import time
from typing import Any

import win32api
import win32clipboard
import win32con
import win32gui


def clipboard_set(text: str) -> str | None:
    previous = None
    win32clipboard.OpenClipboard()
    try:
        try:
            previous = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        except Exception:
            previous = None
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    finally:
        win32clipboard.CloseClipboard()
    return previous


def clipboard_restore(previous: str | None) -> None:
    if previous is None:
        return
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, previous)
    finally:
        win32clipboard.CloseClipboard()


def key_combo(modifier: int, key: int) -> None:
    win32api.keybd_event(modifier, 0, 0, 0)
    win32api.keybd_event(key, 0, 0, 0)
    win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(modifier, 0, win32con.KEYEVENTF_KEYUP, 0)


def send_to_focused_input(text: str, commit: bool = True) -> dict[str, Any]:
    """Paste into the current foreground Weixin input without moving focus."""
    if not text.strip():
        raise ValueError("text is required")
    foreground = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(foreground)
    if title != "微信":
        raise RuntimeError(f"foreground window is not personal Weixin: {title or foreground}")
    previous = clipboard_set(text)
    try:
        key_combo(win32con.VK_CONTROL, ord("V"))
        time.sleep(0.2)
        if commit:
            win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
            win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
    finally:
        clipboard_restore(previous)
    return {"foreground": foreground, "title": title, "committed": commit}
