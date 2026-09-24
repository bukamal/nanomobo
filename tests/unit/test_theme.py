from __future__ import annotations

import flet as ft

from nanomobo.core.theme import Colors, Shadow, get_mode, set_mode
from nanomobo.core.toast import _infer_kind


def test_color_tokens_follow_active_mode() -> None:
    set_mode("light")
    light = Colors.BACKGROUND
    set_mode("dark")
    try:
        assert light != Colors.BACKGROUND
        assert get_mode() == "dark"
        assert Shadow.SM.color == Colors.BORDER
    finally:
        set_mode("light")


def test_flet_design_tokens_are_constructible() -> None:
    assert isinstance(ft.Theme(color_scheme_seed=Colors.PRIMARY), ft.Theme)
    assert ft.FontWeight.W_600 in tuple(ft.FontWeight)
    assert ft.Icons.HOURGLASS_TOP_ROUNDED


def test_toast_kind_inference() -> None:
    assert _infer_kind("تمت العملية بنجاح") == "success"
    assert _infer_kind("فشل الاتصال") == "error"
    assert _infer_kind("اختر جهازًا") == "warning"
    assert _infer_kind("Device connected") == "info"
