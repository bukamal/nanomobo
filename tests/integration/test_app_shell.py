from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import flet as ft

from main import create_app
from nanomobo.core.usb_bridge import UsbDeviceInfo
from nanomobo.views.home_view import HomeView


class FakePage:
    def __init__(self) -> None:
        self.title = ""
        self.padding: Any = None
        self.bgcolor: Any = None
        self.theme: Any = None
        self.theme_mode: Any = None
        self.controls: list[Any] = []
        self.overlay: list[Any] = []
        self.width = 500
        self.on_disconnect: Callable[[object], None] | None = None

    def add(self, *controls: Any) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        return

    def run_thread(self, handler: Callable[..., Any], *args: Any) -> None:
        handler(*args)


def test_create_app_builds_flet_control_tree_and_closes_service() -> None:
    page = FakePage()
    typed_page = cast(ft.Page, page)
    create_app(typed_page)
    assert page.title == "NanoMobo"
    assert len(page.controls) == 1
    content = page.controls[0]
    home = content.controls[-1]
    assert isinstance(home, HomeView)
    assert home._refresh_button.disabled is True
    assert page.on_disconnect is not None
    page.on_disconnect(object())
    assert home._closed is True


def test_device_card_uses_stable_mode_labels() -> None:
    page = cast(ft.Page, FakePage())
    view = HomeView(page)
    device = UsbDeviceInfo(
        device_name="1/1",
        vendor_id=0x05C6,
        product_id=0x9008,
        device_class=0xFF,
        product="Test Device",
    )
    card = view._device_card(device)
    assert isinstance(card, ft.Container)
    assert isinstance(card.content, ft.Column)
    mode_badge = card.content.controls[2]
    assert isinstance(mode_badge, ft.Container)
    assert isinstance(mode_badge.content, ft.Text)
    assert mode_badge.content.value == "Qualcomm EDL 9008"


def test_device_details_expose_interfaces_and_permission_action() -> None:
    page = cast(ft.Page, FakePage())
    view = HomeView(page)
    device = UsbDeviceInfo(
        device_name="1/1",
        vendor_id=0x0E8D,
        product_id=0x1234,
        device_class=0xFF,
        interfaces=[],
    )
    view._select_device(device)
    assert view._details_panel.visible is True
    assert view._permission_button is not None
    assert view._permission_status.value == "لم يتم طلب صلاحية USB بعد"
    assert view._selected_device_name == "1/1"


def test_identity_panel_validates_and_compares_without_writing() -> None:
    page = cast(ft.Page, FakePage())
    view = HomeView(page)
    view._identity_primary.value = "490154203237518"
    view._identity_secondary.value = "490154203237518"
    view._on_identity_check(cast(ft.Event[ft.Button], object()))
    assert "IMEI" in str(view._identity_result.value)
    assert "متطابقتان" in str(view._identity_result.value)
    assert "تعديل" not in str(view._identity_result.value)
