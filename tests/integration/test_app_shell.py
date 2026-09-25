from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import flet as ft

from main import create_app
from nanomobo.core.repair_assistant import Symptom
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
    view._probe_protocol(device)
    assert "MediaTek USB" in str(view._protocol_result.value)


def test_identity_panel_validates_and_compares_without_writing() -> None:
    page = cast(ft.Page, FakePage())
    view = HomeView(page)
    view._identity_primary.value = "490154203237518"
    view._identity_secondary.value = "490154203237518"
    view._on_identity_check(cast(ft.Event[ft.Button], object()))
    assert "IMEI" in str(view._identity_result.value)
    assert "متطابقتان" in str(view._identity_result.value)
    assert "تعديل" not in str(view._identity_result.value)


def test_device_details_include_intelligence_panel_and_safe_recommendations() -> None:
    page = cast(ft.Page, FakePage())
    view = HomeView(page)
    device = UsbDeviceInfo(
        device_name="1/1",
        vendor_id=0x05C6,
        product_id=0x9008,
        device_class=0xFF,
        product="Test Device",
    )
    panel = view._intelligence_panel(device)
    assert isinstance(panel, ft.Container)
    assert isinstance(panel.content, ft.Column)

    texts = [control.value for control in panel.content.controls if isinstance(control, ft.Text)]
    assert any("التحليل الذكي" in value for value in texts)
    assert any("%" in value for value in texts)
    assert any("قراءة فقط" in value for value in texts)


def _collect_texts(control: Any) -> list[str]:
    texts: list[str] = []
    if isinstance(control, ft.Text):
        texts.append(str(control.value))
    content = getattr(control, "content", None)
    if content is not None:
        texts.extend(_collect_texts(content))
    children = getattr(control, "controls", None)
    if isinstance(children, list):
        for child in children:
            texts.extend(_collect_texts(child))
    return texts


def _repair_texts(view: HomeView) -> list[str]:
    return _collect_texts(view._repair_result)


def test_repair_panel_asks_for_a_device_first() -> None:
    page = cast(ft.Page, FakePage())
    view = HomeView(page)
    view._symptom_dropdown.value = Symptom.DEVICE_NOT_BOOTING.value

    view._render_repair_plan()

    assert any("اختر جهازًا" in text for text in _repair_texts(view))


def test_repair_panel_asks_for_a_symptom_after_device_selection() -> None:
    page = cast(ft.Page, FakePage())
    view = HomeView(page)
    view._select_device(
        UsbDeviceInfo(
            device_name="1/1",
            vendor_id=0x05C6,
            product_id=0x9008,
            device_class=0xFF,
            product="Test Device",
        )
    )
    view._symptom_dropdown.value = None

    view._render_repair_plan()

    assert any("اختر العَرَض" in text for text in _repair_texts(view))


def test_repair_panel_builds_report_for_known_symptom() -> None:
    page = cast(ft.Page, FakePage())
    view = HomeView(page)
    device = UsbDeviceInfo(
        device_name="1/1",
        vendor_id=0x05C6,
        product_id=0x9008,
        device_class=0xFF,
        product="Test Device",
    )
    view._select_device(device)
    view._symptom_dropdown.value = Symptom.DEVICE_NOT_BOOTING.value

    view._render_repair_plan()

    texts = _repair_texts(view)
    assert any("خطة قراءة فقط" in text for text in texts)
    assert any("المخاطر" in text for text in texts)
    assert any("التقرير" in text for text in texts)
    report_containers = [
        control for control in view._repair_result.controls if isinstance(control, ft.Container)
    ]
    assert report_containers


def test_repair_panel_rejects_unknown_symptom_key() -> None:
    page = cast(ft.Page, FakePage())
    view = HomeView(page)
    view._select_device(
        UsbDeviceInfo(
            device_name="1/1",
            vendor_id=0x05C6,
            product_id=0x9008,
            device_class=0xFF,
            product="Test Device",
        )
    )
    view._symptom_dropdown.value = "not-a-symptom"

    view._render_repair_plan()

    assert any("عرض غير معروف" in text for text in _repair_texts(view))


def test_clear_details_resets_selected_device_and_prompts_again() -> None:
    page = cast(ft.Page, FakePage())
    view = HomeView(page)
    view._select_device(
        UsbDeviceInfo(
            device_name="1/1",
            vendor_id=0x05C6,
            product_id=0x9008,
            device_class=0xFF,
            product="Test Device",
        )
    )

    view._clear_details()

    assert view._selected_device is None
    assert view._selected_device_name is None
    assert view._details_panel.visible is False
    assert any("اختر جهازًا" in text for text in _repair_texts(view))
