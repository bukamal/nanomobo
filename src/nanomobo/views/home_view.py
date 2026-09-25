from __future__ import annotations

import logging
from typing import Any

import flet as ft

from nanomobo.core.capabilities import capabilities_for
from nanomobo.core.device_db import DeviceModeLabel
from nanomobo.core.device_intelligence import ConfidenceBand, analyze_device
from nanomobo.core.identity import (
    IdentityKind,
    IdentityMatch,
    IdentityValidation,
    compare_identity,
    validate_identity,
)
from nanomobo.core.identity_audit import (
    AuditStatus,
    audit_identity,
    create_backup,
    ownership_label,
    plan_restore,
    status_label,
)
from nanomobo.core.repair_assistant import (
    RISK_LABELS,
    SYMPTOMS,
    PlanStep,
    RepairPlan,
    RiskLevel,
    StepKind,
    Symptom,
    create_repair_plan,
)
from nanomobo.core.theme import Colors, Radius, Shadow, Spacing
from nanomobo.core.toast import toast
from nanomobo.core.usb_bridge import UsbDeviceInfo
from nanomobo.protocols.base import ProbeStatus
from nanomobo.services.device_service import DeviceService
from nanomobo.services.protocol_service import ProtocolService

logger = logging.getLogger(__name__)

_STEP_KIND_STYLE: dict[StepKind, tuple[str, str]] = {
    StepKind.CHECK: ("تحقق", Colors.PRIMARY),
    StepKind.SAFE: ("آمن", Colors.SUCCESS),
    StepKind.CAUTION: ("حذر", Colors.WARNING_DARK),
}


class HomeView(ft.Column):
    def __init__(self, page: ft.Page, service: DeviceService | None = None) -> None:
        self._page = page
        self._service = service if service is not None else DeviceService()
        self._protocol_service = ProtocolService()
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
        self._details = ft.Column(spacing=Spacing.SM)
        self._details_panel = ft.Container(
            content=self._details,
            visible=False,
            padding=Spacing.LG,
            bgcolor=Colors.WHITE,
            border_radius=Radius.MD,
            border=ft.Border.all(1, Colors.BORDER),
        )
        self._permission_status = ft.Text("", color=Colors.TEXT_SECONDARY)
        self._permission_button: ft.Button | None = None
        self._protocol_result = ft.Text("", color=Colors.TEXT_SECONDARY)
        self._protocol_button: ft.Button | None = None
        self._selected_device: UsbDeviceInfo | None = None
        self._selected_device_name: str | None = None
        self._symptom_dropdown = ft.Dropdown(
            label="العَرَض الملاحظ",
            text_size=13,
            options=[
                ft.DropdownOption(key=symptom.value, text=label) for symptom, label in SYMPTOMS
            ],
            on_select=self._on_symptom_selected,
        )
        self._repair_result = ft.Column(spacing=Spacing.SM)
        self._repair_panel = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "مساعد الإصلاح",
                        size=18,
                        weight=ft.FontWeight.W_700,
                        color=Colors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "خطة قراءة فقط: تحقق ووثّق الحالة دون أي كتابة أو فلاش أو تعديل معرفات.",
                        size=12.5,
                        color=Colors.TEXT_SECONDARY,
                    ),
                    self._symptom_dropdown,
                    self._repair_result,
                ],
                spacing=Spacing.SM,
            ),
            padding=Spacing.LG,
            bgcolor=Colors.WHITE,
            border_radius=Radius.MD,
            border=ft.Border.all(1, Colors.BORDER),
        )
        self._identity_primary = ft.TextField(
            label="IMEI/MEID الأساسي",
            hint_text="أدخل الرقم للقراءة أو المقارنة فقط",
            text_size=13,
        )
        self._identity_secondary = ft.TextField(
            label="IMEI/MEID الاحتياطي",
            hint_text="اختياري",
            text_size=13,
        )
        self._identity_result = ft.Text("", color=Colors.TEXT_SECONDARY)
        self._identity_owner_verified = ft.Checkbox(
            label="تم إثبات ملكية الجهاز",
            value=False,
        )
        self._identity_audit_result = ft.Text("", color=Colors.TEXT_SECONDARY)
        self._identity_restore_result = ft.Text("", color=Colors.TEXT_SECONDARY)
        self._identity_panel = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "تشخيص الهوية",
                        size=18,
                        weight=ft.FontWeight.W_700,
                        color=Colors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "تحقق من الصيغة ومقارنة النسخ فقط؛ لا يتم تعديل أي IMEI أو MEID.",
                        size=12.5,
                        color=Colors.TEXT_SECONDARY,
                    ),
                    self._identity_primary,
                    self._identity_secondary,
                    ft.Button(
                        "تحقق وقارن",
                        on_click=self._on_identity_check,
                        color=Colors.WHITE,
                        bgcolor=Colors.PRIMARY,
                    ),
                    self._identity_result,
                    ft.Text(
                        "تدقيق الهوية",
                        size=16,
                        weight=ft.FontWeight.W_700,
                        color=Colors.TEXT_PRIMARY,
                    ),
                    self._identity_owner_verified,
                    ft.Button(
                        "تدقيق ومقارنة بالأصل",
                        on_click=self._on_identity_audit,
                        color=Colors.PRIMARY,
                        bgcolor=Colors.BACKGROUND_ALT,
                    ),
                    self._identity_audit_result,
                    self._identity_restore_result,
                ],
                spacing=Spacing.SM,
            ),
            padding=Spacing.LG,
            bgcolor=Colors.WHITE,
            border_radius=Radius.MD,
            border=ft.Border.all(1, Colors.BORDER),
        )

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
                self._details_panel,
                self._repair_panel,
                self._identity_panel,
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
            toast(self._page, self._status.value or "", kind="error")
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
        self._clear_details()
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
                    ft.Button(
                        "عرض التفاصيل",
                        on_click=lambda _event, selected=device: self._select_device(selected),
                        color=Colors.PRIMARY,
                        bgcolor=Colors.BACKGROUND_ALT,
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

    def _select_device(self, device: UsbDeviceInfo) -> None:
        self._selected_device = device
        self._selected_device_name = device.device_name
        self._permission_status.value = "لم يتم طلب صلاحية USB بعد"
        self._permission_button = ft.Button(
            "طلب صلاحية USB",
            on_click=lambda _event: self._request_permission(device.device_name),
            color=Colors.WHITE,
            bgcolor=Colors.PRIMARY,
        )
        details: list[Any] = [
            ft.Text(
                device.display_name,
                size=18,
                weight=ft.FontWeight.W_700,
                color=Colors.TEXT_PRIMARY,
            ),
            ft.Text(
                f"VID:PID {device.id_label}  •  Manufacturer: {device.manufacturer or 'غير متاح'}",
                size=12.5,
                color=Colors.TEXT_SECONDARY,
            ),
            ft.Text(
                f"Serial: {device.serial_number or 'غير متاح'}",
                size=12.5,
                color=Colors.TEXT_SECONDARY,
            ),
            ft.Text(
                f"الوضع: {DeviceModeLabel[device.mode.name].value}",
                size=12.5,
                color=Colors.PRIMARY,
            ),
        ]
        capabilities = capabilities_for(device.mode)
        details.extend(
            [
                ft.Text(
                    f"القدرات: {capabilities.summary}",
                    size=12.5,
                    color=Colors.TEXT_PRIMARY,
                ),
                ft.Text(
                    "الفلاش والكتابة غير مفعّلين حتى توثيق البروتوكول والتحقق من الجهاز.",
                    size=12,
                    color=Colors.WARNING_DARK,
                ),
            ]
        )
        self._protocol_result.value = "لم يتم فحص البروتوكول بعد"
        self._protocol_button = ft.Button(
            "فحص البروتوكول",
            on_click=lambda _event, selected=device: self._probe_protocol(selected),
            color=Colors.PRIMARY,
            bgcolor=Colors.BACKGROUND_ALT,
        )
        details.extend([self._protocol_result, self._protocol_button])
        for interface in device.interfaces:
            endpoints = ", ".join(
                f"{endpoint.direction}:{endpoint.transfer_type}" for endpoint in interface.endpoints
            )
            details.append(
                ft.Text(
                    f"Interface {interface.index}: "
                    f"class=0x{interface.interface_class:02X}, "
                    f"subclass=0x{interface.subclass:02X}, "
                    f"protocol=0x{interface.protocol:02X}, "
                    f"endpoints={endpoints or 'لا يوجد'}",
                    size=11.5,
                    color=Colors.TEXT_SECONDARY,
                )
            )
        details.append(self._intelligence_panel(device))
        self._details.controls = [*details, self._permission_button, self._permission_status]
        self._details_panel.visible = True
        self._safe_update()

    def _request_permission(self, device_name: str) -> None:
        if self._closed or not self._service.supported:
            return
        if self._permission_button is None:
            return
        self._refresh_generation += 1
        generation = self._refresh_generation
        self._permission_button.disabled = True
        self._permission_status.value = "جارٍ انتظار موافقة Android..."
        self._safe_update()
        self._page.run_thread(self._load_permission, device_name, generation)

    def _load_permission(self, device_name: str, generation: int) -> None:
        try:
            granted = self._service.request_permission(device_name)
        except Exception:
            logger.exception("USB permission request failed")
            if self._closed or generation != self._refresh_generation:
                return
            self._permission_status.value = "تعذر طلب صلاحية USB"
            toast(self._page, self._permission_status.value or "", kind="error")
        else:
            if self._closed or generation != self._refresh_generation:
                return
            if granted:
                self._permission_status.value = "تم منح صلاحية USB"
                toast(self._page, self._permission_status.value or "", kind="success")
            else:
                self._permission_status.value = "تم رفض أو انتهاء صلاحية الطلب"
                toast(self._page, self._permission_status.value or "", kind="warning")
        if self._permission_button is not None:
            self._permission_button.disabled = False
        self._safe_update()

    def _probe_protocol(self, device: UsbDeviceInfo) -> None:
        result = self._protocol_service.inspect(device)
        self._protocol_result.value = f"{result.label}: {result.detail}"
        if result.status is ProbeStatus.RECOGNIZED:
            self._protocol_result.color = Colors.SUCCESS
        elif result.status is ProbeStatus.EXPERIMENTAL:
            self._protocol_result.color = Colors.WARNING_DARK
        else:
            self._protocol_result.color = Colors.TEXT_SECONDARY
        self._safe_update()

    def _intelligence_panel(self, device: UsbDeviceInfo) -> ft.Container:
        report = analyze_device(device)
        band_text = {
            ConfidenceBand.HIGH: "عالية",
            ConfidenceBand.MEDIUM: "متوسطة",
            ConfidenceBand.LOW: "منخفضة",
        }[report.band]
        band_color = {
            ConfidenceBand.HIGH: Colors.SUCCESS,
            ConfidenceBand.MEDIUM: Colors.WARNING_DARK,
            ConfidenceBand.LOW: Colors.DANGER,
        }[report.band]
        controls: list[Any] = [
            ft.Text(
                "التحليل الذكي",
                size=18,
                weight=ft.FontWeight.W_700,
                color=Colors.TEXT_PRIMARY,
            ),
            ft.Text(report.summary, size=13, color=Colors.TEXT_MUTED),
            ft.Row(
                controls=[
                    ft.Text(
                        f"الثقة: {report.confidence}%",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=band_color,
                    ),
                    ft.Container(
                        content=ft.Text(f"مستوى: {band_text}", size=12, color=band_color),
                        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                        border_radius=999,
                        bgcolor=Colors.BACKGROUND_ALT,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.ProgressBar(
                value=report.confidence / 100,
                bar_height=8,
                color=band_color,
                bgcolor=Colors.BACKGROUND_ALT,
                border_radius=8,
            ),
            ft.Text(
                "أسباب التصنيف",
                size=14,
                weight=ft.FontWeight.W_600,
                color=Colors.TEXT_PRIMARY,
            ),
        ]
        controls.extend(
            ft.Text(
                f"• {item.title}: {item.detail}",
                size=11.5,
                color=Colors.TEXT_SECONDARY,
            )
            for item in report.evidence
        )
        controls.append(
            ft.Text(
                "التوصيات الآمنة",
                size=14,
                weight=ft.FontWeight.W_600,
                color=Colors.TEXT_PRIMARY,
            )
        )
        controls.extend(
            ft.Text(
                f"• {item.title}: {item.detail}",
                size=11.5,
                color=Colors.TEXT_MUTED,
            )
            for item in report.recommendations
        )
        return ft.Container(
            content=ft.Column(controls, spacing=Spacing.XS),
            padding=Spacing.LG,
            bgcolor=Colors.WHITE,
            border_radius=Radius.MD,
            border=ft.Border.all(1, Colors.BORDER),
            shadow=Shadow.SM,
        )

    def _on_symptom_selected(self, _event: ft.Event[ft.Dropdown]) -> None:
        self._render_repair_plan()

    def _render_repair_plan(self) -> None:
        device = self._selected_device
        raw_key = self._symptom_dropdown.value
        if device is None:
            self._repair_result.controls = [
                ft.Text(
                    "اختر جهازًا من القائمة أولًا لعرض خطة الإصلاح.",
                    color=Colors.TEXT_SECONDARY,
                )
            ]
            self._safe_update()
            return
        if not raw_key:
            self._repair_result.controls = [
                ft.Text("اختر العَرَض الملاحظ لإنشاء الخطة.", color=Colors.TEXT_SECONDARY)
            ]
            self._safe_update()
            return
        try:
            symptom = Symptom(raw_key)
        except ValueError:
            logger.warning("Unknown symptom key: %s", raw_key)
            self._repair_result.controls = [ft.Text("عرض غير معروف.", color=Colors.DANGER)]
            self._safe_update()
            return
        plan = create_repair_plan(device, symptom)
        self._repair_result.controls = self._plan_controls(plan)
        self._safe_update()

    def _plan_controls(self, plan: RepairPlan) -> list[Any]:
        risk_color = {
            RiskLevel.LOW: Colors.SUCCESS,
            RiskLevel.MODERATE: Colors.WARNING_DARK,
            RiskLevel.ELEVATED: Colors.DANGER,
        }[plan.risk]
        controls: list[Any] = [
            ft.Text(plan.summary, size=13, color=Colors.TEXT_PRIMARY),
            ft.Container(
                content=ft.Text(
                    f"المخاطر: {RISK_LABELS[plan.risk]}",
                    size=12,
                    color=risk_color,
                ),
                padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                border_radius=999,
                bgcolor=Colors.BACKGROUND_ALT,
            ),
            ft.Text("الخطوات", size=14, weight=ft.FontWeight.W_600, color=Colors.TEXT_PRIMARY),
        ]
        for index, step in enumerate(plan.steps, start=1):
            controls.append(self._plan_step_row(index, step))
        if plan.warnings:
            controls.append(
                ft.Text(
                    "تحذيرات",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=Colors.WARNING_DARK,
                )
            )
            controls.extend(
                ft.Text(f"• {warning}", size=11.5, color=Colors.WARNING_DARK)
                for warning in plan.warnings
            )
        controls.append(
            ft.Text(
                "التقرير الكامل (قابل للنسخ)",
                size=14,
                weight=ft.FontWeight.W_600,
                color=Colors.TEXT_PRIMARY,
            )
        )
        controls.append(
            ft.Container(
                content=ft.Text(plan.report_text, size=11.5, selectable=True, no_wrap=False),
                padding=Spacing.MD,
                bgcolor=Colors.BACKGROUND_ALT,
                border_radius=Radius.SM,
            )
        )
        return controls

    @staticmethod
    def _plan_step_row(index: int, step: PlanStep) -> ft.Row:
        kind_label, kind_color = _STEP_KIND_STYLE[step.kind]
        return ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(
                        f"{index}",
                        size=12,
                        weight=ft.FontWeight.W_700,
                        color=Colors.WHITE,
                    ),
                    width=24,
                    height=24,
                    alignment=ft.Alignment.CENTER,
                    border_radius=12,
                    bgcolor=kind_color,
                ),
                ft.Column(
                    [
                        ft.Text(
                            f"{step.title}  •  {kind_label}",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=kind_color,
                        ),
                        ft.Text(step.detail, size=12, color=Colors.TEXT_MUTED),
                    ],
                    spacing=2,
                ),
            ],
            spacing=Spacing.SM,
        )

    def _on_identity_check(self, _event: ft.Event[ft.Button]) -> None:
        primary = self._identity_primary.value or ""
        secondary = self._identity_secondary.value or ""
        if not primary.strip():
            self._identity_result.value = "أدخل IMEI/MEID الأساسي أولًا"
            self._identity_result.color = Colors.WARNING_DARK
            toast(self._page, self._identity_result.value or "", kind="warning")
            self._safe_update()
            return

        primary_validation = validate_identity(primary)
        messages = [self._identity_message(primary_validation)]
        result_color = Colors.SUCCESS if primary_validation.valid_format else Colors.DANGER
        if secondary.strip():
            secondary_validation = validate_identity(secondary)
            messages.append(self._identity_message(secondary_validation))
            comparison = compare_identity(primary, secondary)
            if comparison.result is IdentityMatch.MATCH:
                messages.append("النسختان متطابقتان")
            elif comparison.result is IdentityMatch.MISMATCH:
                messages.append("توجد اختلافات بين النسختين")
                result_color = Colors.DANGER
            else:
                messages.append("لا يمكن مقارنة قيمة ناقصة")
                result_color = Colors.WARNING_DARK
        self._identity_result.value = "  •  ".join(messages)
        self._identity_result.color = result_color
        self._safe_update()

    def _on_identity_audit(self, _event: ft.Event[ft.Button]) -> None:
        primary = self._identity_primary.value or ""
        secondary = self._identity_secondary.value or ""
        if not primary.strip():
            self._identity_audit_result.value = "أدخل القيمة الحالية أولًا"
            self._identity_audit_result.color = Colors.WARNING_DARK
            toast(self._page, self._identity_audit_result.value or "", kind="warning")
            self._safe_update()
            return

        owner_verified = bool(self._identity_owner_verified.value)
        audit = audit_identity(primary, secondary, owner_verified=owner_verified)
        status_color = {
            AuditStatus.CLEAN: Colors.SUCCESS,
            AuditStatus.TAMPERED: Colors.DANGER,
            AuditStatus.INVALID: Colors.DANGER,
            AuditStatus.INCOMPLETE: Colors.WARNING_DARK,
        }[audit.status]
        self._identity_audit_result.value = (
            f"الحالة: {status_label(audit.status)}"
            f"  •  الملكية: {ownership_label(audit.ownership)}"
            f"  •  النتائج: {len(audit.findings)}"
        )
        self._identity_audit_result.color = status_color

        backup = create_backup(
            self._selected_device_name or "unknown",
            primary,
            secondary,
            owner_verified=owner_verified,
        )
        plan = plan_restore(backup, owner_verified=owner_verified)
        self._identity_restore_result.value = (
            f"خطة استعادة الأصل: محجوبة ({plan.reason}) — لا كتابة من التطبيق"
        )
        self._identity_restore_result.color = Colors.WARNING_DARK
        self._safe_update()

    @staticmethod
    def _identity_message(validation: IdentityValidation) -> str:
        if validation.kind is IdentityKind.IMEI:
            if validation.valid_format:
                return "IMEI: الصيغة ورقم التحقق صحيحة"
            return "IMEI: الصيغة أو رقم التحقق غير صالح"
        if validation.kind is IdentityKind.MEID:
            return "MEID: الطول صالح؛ لا يثبت ذلك المصدر أو الأصالة"
        return "المعرّف: الطول أو الصيغة غير معروفة"

    def _clear_details(self) -> None:
        self._selected_device = None
        self._selected_device_name = None
        self._details.controls = []
        self._details_panel.visible = False
        self._permission_status.value = ""
        self._permission_button = None
        self._protocol_result.value = ""
        self._protocol_button = None
        self._repair_result.controls = [
            ft.Text(
                "اختر جهازًا من القائمة أولًا لعرض خطة الإصلاح.",
                color=Colors.TEXT_SECONDARY,
            )
        ]

    def _safe_update(self) -> None:
        try:
            self.update()
        except (AssertionError, RuntimeError):
            return


__all__ = ["HomeView"]
