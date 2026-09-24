from __future__ import annotations

import logging

import flet as ft

from nanomobo.core.device_db import DeviceModeLabel
from nanomobo.core.theme import Colors, Radius, Shadow, Spacing
from nanomobo.core.usb_bridge import UsbDeviceInfo
from nanomobo.services.device_service import DeviceService

logger = logging.getLogger(__name__)


class HomeView(ft.Column):
    def __init__(self, page: ft.Page, service: DeviceService | None = None) -> None:
        self._page = page
        self._service = service if service is not None else DeviceService()
        self._refresh_generation = 0
        self._closed = False
        self._status = ft.Text("جاهز لاكتشاف الأجهزة", color=Colors.TEXT_SECONDARY)
        self._refresh_button = ft.Button(
            "تحديث الأجهزة",
            on_click=self._on_refresh,
            color=Colors.WHITE,
            bgcolor=Colors.PRIMARY,
        )
        self._devices = ft.Column(spacing=Spacing.MD)

        super().__init__(
            controls=[
                ft.Text(
                    "لوحة الأجهزة",
                    size=28,
                    weight=ft.FontWeight.W_700,
                    color=Colors.TEXT_PRIMARY,
                ),
                ft.Text(
                    "اكتشاف أجهزة USB وتحديد وضع الاتصال قبل تنفيذ أي عملية صيانة.",
                    size=14,
                    color=Colors.TEXT_SECONDARY,
                ),
                self._refresh_button,
                self._status,
                self._devices,
            ],
            spacing=Spacing.MD,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def refresh_devices(self) -> None:
        if self._closed:
            return
        self._refresh_generation += 1
        generation = self._refresh_generation
        if not self._service.supported:
            self._status.value = "اكتشاف USB متاح داخل تطبيق Android فقط"
            self._refresh_button.disabled = True
            self._render_devices([])
            self._safe_update()
            return

        self._refresh_button.disabled = True
        self._status.value = "جارٍ البحث عن الأجهزة..."
        self._safe_update()
        self._page.run_thread(self._load_devices, generation)

    def _on_refresh(self, _event: ft.Event[ft.Button]) -> None:
        self.refresh_devices()

    def _load_devices(self, generation: int) -> None:
        try:
            devices = self._service.list_devices()
        except Exception as exc:
            logger.exception("USB device discovery failed")
            if self._closed or generation != self._refresh_generation:
                return
            self._status.value = f"تعذر اكتشاف الأجهزة: {type(exc).__name__}"
            devices = []
        else:
            if self._closed or generation != self._refresh_generation:
                return
            self._status.value = (
                f"تم العثور على {len(devices)} جهاز" if devices else "لم يتم العثور على أجهزة USB"
            )
        self._render_devices(devices)
        self._refresh_button.disabled = not self._service.supported
        self._safe_update()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._refresh_generation += 1
        self._service.close()

    def _render_devices(self, devices: list[UsbDeviceInfo]) -> None:
        if not devices:
            self._devices.controls = [
                ft.Container(
                    content=ft.Text(
                        "وصّل الجهاز عبر OTG ثم اضغط تحديث.",
                        color=Colors.TEXT_SECONDARY,
                    ),
                    padding=Spacing.XL,
                    alignment=ft.Alignment.CENTER,
                    bgcolor=Colors.WHITE,
                    border_radius=Radius.MD,
                    border=ft.Border.all(1, Colors.BORDER),
                )
            ]
            return
        self._devices.controls = [self._device_card(device) for device in devices]

    def _device_card(self, device: UsbDeviceInfo) -> ft.Container:
        mode = device.mode
        mode_label = DeviceModeLabel[mode.name].value
        metadata = f"VID:PID {device.id_label}  •  {len(device.interfaces)} واجهة"
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        device.display_name,
                        size=17,
                        weight=ft.FontWeight.W_600,
                        color=Colors.TEXT_PRIMARY,
                    ),
                    ft.Text(metadata, size=12.5, color=Colors.TEXT_SECONDARY),
                    ft.Container(
                        content=ft.Text(
                            mode_label,
                            size=12,
                            color=Colors.PRIMARY,
                        ),
                        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                        border_radius=999,
                        bgcolor=Colors.PRIMARY_BG,
                    ),
                ],
                spacing=Spacing.SM,
            ),
            padding=Spacing.LG,
            bgcolor=Colors.WHITE,
            border_radius=Radius.MD,
            border=ft.Border.all(1, Colors.BORDER),
            shadow=Shadow.SM,
        )

    def _safe_update(self) -> None:
        try:
            self.update()
        except (AssertionError, RuntimeError):
            return


__all__ = ["HomeView"]
