from __future__ import annotations

import asyncio
from typing import Any, Literal
from weakref import WeakKeyDictionary

import flet as ft

from nanomobo.core.theme import Colors, Shadow

ToastKind = Literal["success", "error", "warning", "info"]

_STYLE: dict[ToastKind, tuple[ft.IconData, str, str]] = {
    "success": (ft.Icons.CHECK_CIRCLE_ROUNDED, "SUCCESS", "SUCCESS_BG"),
    "error": (ft.Icons.ERROR_ROUNDED, "DANGER", "DANGER_BG"),
    "warning": (ft.Icons.WARNING_ROUNDED, "WARNING_DARK", "WARNING_BG"),
    "info": (ft.Icons.INFO_ROUNDED, "PRIMARY", "PRIMARY_BG"),
}

_TOASTS: WeakKeyDictionary[ft.Page, ft.Container] = WeakKeyDictionary()
_TASKS: WeakKeyDictionary[ft.Page, Any] = WeakKeyDictionary()
_HIDDEN_BOTTOM = -120.0
_MOBILE_BAR_HEIGHT = 78
_EDGE_MARGIN = 18
_ANIMATION_DURATION_MS = 260
_ANIMATION = ft.Animation(_ANIMATION_DURATION_MS, ft.AnimationCurve.EASE_OUT)
_SUCCESS_MARKERS = ("تم ", "تمت ", "✔", "بنجاح")
_ERROR_MARKERS = (
    "خطأ",
    "تعذر",
    "فشل",
    "غير مهيأ",
    "غير موجود",
    "غير مطابق",
    "لا توجد",
    "لا يمكن",
    "انقطع",
)
_WARNING_MARKERS = ("يجب", "اختر", "أولاً", "أولًا", "الرجاء", "فارغ", "تأكد")


def _infer_kind(text: str) -> ToastKind:
    normalized = text.strip()
    if any(marker in normalized for marker in _SUCCESS_MARKERS):
        return "success"
    if any(marker in normalized for marker in _ERROR_MARKERS):
        return "error"
    if any(marker in normalized for marker in _WARNING_MARKERS):
        return "warning"
    return "info"


def _visible_bottom(page: ft.Page) -> float:
    is_desktop = bool(page.width and page.width >= 900)
    return _EDGE_MARGIN if is_desktop else _MOBILE_BAR_HEIGHT + _EDGE_MARGIN


def toast(page: ft.Page, text: str, kind: ToastKind | None = None, duration: int = 2600) -> None:
    if not text.strip():
        raise ValueError("text must not be empty")
    if duration <= 0:
        raise ValueError("duration must be greater than zero")
    resolved_kind = kind or _infer_kind(text)
    if resolved_kind not in _STYLE:
        raise ValueError(f"unsupported toast kind: {resolved_kind}")

    icon_name, accent_token, tint_token = _STYLE[resolved_kind]
    accent = getattr(Colors, accent_token)
    tint = getattr(Colors, tint_token)
    pill = ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    ft.Icon(icon_name, color=accent, size=18),
                    width=30,
                    height=30,
                    border_radius=15,
                    bgcolor=tint,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(
                    text,
                    size=12.5,
                    weight=ft.FontWeight.W_600,
                    color=Colors.TEXT_PRIMARY,
                    max_lines=4,
                ),
            ],
            spacing=10,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=Colors.WHITE,
        border=ft.Border.all(1, Colors.BORDER),
        border_radius=999,
        padding=ft.Padding.only(left=14, right=16, top=8, bottom=8),
        shadow=Shadow.LG,
    )
    wrapper = ft.Container(
        content=ft.Row([pill], alignment=ft.MainAxisAlignment.CENTER),
        left=0,
        right=0,
        bottom=_HIDDEN_BOTTOM,
        opacity=0,
        animate_position=_ANIMATION,
        animate_opacity=_ANIMATION,
    )

    previous_wrapper = _TOASTS.get(page)
    if previous_wrapper is not None and previous_wrapper in page.overlay:
        page.overlay.remove(previous_wrapper)
    previous_task = _TASKS.get(page)
    if previous_task is not None and not previous_task.done():
        previous_task.cancel()

    _TOASTS[page] = wrapper
    page.overlay.append(wrapper)
    _safe_update(page)
    wrapper.bottom = _visible_bottom(page)
    wrapper.opacity = 1
    _safe_update(page)
    _TASKS[page] = page.run_task(_auto_dismiss, page, wrapper, duration)


async def _auto_dismiss(page: ft.Page, wrapper: ft.Container, duration: int) -> None:
    try:
        await asyncio.sleep(duration / 1000)
        if _TOASTS.get(page) is not wrapper:
            return
        wrapper.bottom = _HIDDEN_BOTTOM
        wrapper.opacity = 0
        _safe_update(page)
        await asyncio.sleep(_ANIMATION_DURATION_MS / 1000)
        if wrapper in page.overlay:
            page.overlay.remove(wrapper)
            _safe_update(page)
        if _TOASTS.get(page) is wrapper:
            _TOASTS.pop(page, None)
    except asyncio.CancelledError:
        return


def _safe_update(page: ft.Page) -> None:
    try:
        page.update()
    except (AssertionError, RuntimeError):
        return


__all__ = ["ToastKind", "toast"]
