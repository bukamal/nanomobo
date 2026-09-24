from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from nanomobo.core.device_db import DeviceMode, DeviceModeLabel
from nanomobo.core.device_intelligence import (
    ConfidenceBand,
    DeviceIntelligenceReport,
    analyze_device,
)
from nanomobo.core.usb_bridge import UsbDeviceInfo
from nanomobo.protocols.base import ProbeStatus, ProtocolProbe


class Symptom(str, Enum):
    DEVICE_NOT_BOOTING = "device_not_booting"
    STUCK_ON_LOGO = "stuck_on_logo"
    USB_NOT_DETECTED = "usb_not_detected"
    INVALID_IDENTITY = "invalid_identity"
    BATTERY_SENSOR = "battery_sensor"


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"


class StepKind(str, Enum):
    CHECK = "check"
    SAFE = "safe"
    CAUTION = "caution"


@dataclass(frozen=True, slots=True)
class PlanStep:
    title: str
    detail: str
    kind: StepKind


@dataclass(frozen=True, slots=True)
class RepairPlan:
    symptom: Symptom
    device_name: str
    id_label: str
    mode_label: str
    confidence: int
    risk: RiskLevel
    summary: str
    steps: tuple[PlanStep, ...]
    warnings: tuple[str, ...]
    report_text: str
    read_only: bool = True
    writes_locked: bool = True

    @property
    def safe(self) -> bool:
        return self.read_only and self.writes_locked


SYMTOMS: tuple[tuple[Symptom, str], ...] = (
    (Symptom.DEVICE_NOT_BOOTING, "الجهاز لا يشغل"),
    (Symptom.STUCK_ON_LOGO, "معلق على الشعار"),
    (Symptom.USB_NOT_DETECTED, "USB غير مكتشف"),
    (Symptom.INVALID_IDENTITY, "IMEI أو MEID غير صالح"),
    (Symptom.BATTERY_SENSOR, "بطارية أو حساسات"),
)

RISK_LABELS: dict[RiskLevel, str] = {
    RiskLevel.LOW: "منخفضة",
    RiskLevel.MODERATE: "متوسطة",
    RiskLevel.ELEVATED: "مرتفعة",
}

_REPAIR_MODES = {
    DeviceMode.QUALCOMM_EDL,
    DeviceMode.MEDIA_TEK_USB,
    DeviceMode.SAMSUNG_FASTBOOT,
    DeviceMode.GOOGLE_FASTBOOT,
    DeviceMode.ADB,
    DeviceMode.CDC,
    DeviceMode.VENDOR_PROTOCOL,
}

_CRITICAL_SYMPTOMS = {Symptom.DEVICE_NOT_BOOTING, Symptom.STUCK_ON_LOGO}


def create_repair_plan(
    device: UsbDeviceInfo,
    symptom: Symptom,
    intelligence: DeviceIntelligenceReport | None = None,
    probe: ProtocolProbe | None = None,
) -> RepairPlan:
    report = intelligence if intelligence is not None else analyze_device(device)
    risk = _risk_for(report, symptom, probe)
    steps = _steps_for(device, symptom, report, probe)
    warnings = _warnings_for(report, symptom, probe, risk)
    summary = f"خطة قراءة فقط لـ{_symptom_label(symptom)} بثقة {report.confidence}%"
    plan = RepairPlan(
        symptom=symptom,
        device_name=device.device_name,
        id_label=device.id_label,
        mode_label=DeviceModeLabel[report.mode.name].value,
        confidence=report.confidence,
        risk=risk,
        summary=summary,
        steps=steps,
        warnings=warnings,
        report_text="",
    )
    return replace(plan, report_text=_report_text(device, report, probe, plan))


def _symptom_label(symptom: Symptom) -> str:
    for value, label in SYMPTOMS:
        if value is symptom:
            return label
    raise ValueError(f"Unsupported symptom: {symptom}")


def _risk_for(
    report: DeviceIntelligenceReport,
    symptom: Symptom,
    probe: ProtocolProbe | None,
) -> RiskLevel:
    risk = RiskLevel.LOW
    unrecognized_protocol = probe is not None and probe.status is ProbeStatus.UNRECOGNIZED
    if report.band is ConfidenceBand.LOW or unrecognized_protocol:
        risk = RiskLevel.MODERATE
    if symptom in _CRITICAL_SYMPTOMS and report.mode not in _REPAIR_MODES:
        risk = RiskLevel.ELEVATED
    return risk


def _steps_for(
    device: UsbDeviceInfo,
    symptom: Symptom,
    report: DeviceIntelligenceReport,
    probe: ProtocolProbe | None,
) -> tuple[PlanStep, ...]:
    mode_label = DeviceModeLabel[report.mode.name].value
    probe_detail = probe.detail if probe is not None else "لم يتم فحص البروتوكول بعد"
    steps: list[PlanStep] = [
        PlanStep(
            "افحص USB وOTG",
            "تأكد من الكابل والمنفذ ثم حدّث قائمة الأجهزة",
            StepKind.CHECK,
        ),
        PlanStep(
            "افحص وضع الجهاز",
            f"الوضع الحالي {mode_label} بثقة {report.confidence}%",
            StepKind.CHECK,
        ),
        PlanStep(
            "اطلب صلاحية USB",
            "استخدم زر الطلب في التفاصيل قبل أي قراءة",
            StepKind.SAFE,
        ),
        PlanStep(
            "نفّذ فحص البروتوكول",
            f"{probe_detail}",
            StepKind.SAFE,
        ),
    ]
    steps.append(_symptom_step(symptom))
    steps.append(
        PlanStep(
            "وثّق الحالة",
            "انسخ التقرير أو احتفظ باللقطة للاختبار التالي",
            StepKind.SAFE,
        )
    )
    return tuple(steps)


def _symptom_step(symptom: Symptom) -> PlanStep:
    if symptom is Symptom.DEVICE_NOT_BOOTING:
        return PlanStep(
            "اختر وضع الصيانة المناسب",
            "EDL أو Fastboot أو BROM حسب المعالج، دون أوامر غير موثقة",
            StepKind.CAUTION,
        )
    if symptom is Symptom.STUCK_ON_LOGO:
        return PlanStep(
            "تحقق من وضع التشخيص",
            "تحقق من توفر ADB أو Fastboot ثم وثّق شاشة التوقف",
            StepKind.CHECK,
        )
    if symptom is Symptom.USB_NOT_DETECTED:
        return PlanStep(
            "غيّر مسار USB",
            "جرب كابلًا أو منفذًا أو محول OTG آخر ثم أعد اكتشاف الجهاز",
            StepKind.CHECK,
        )
    if symptom is Symptom.INVALID_IDENTITY:
        return PlanStep(
            "افحص المعرفات",
            "استخدم التحقق من IMEI أو MEID للقراءة والمقارنة فقط",
            StepKind.SAFE,
        )
    return PlanStep(
        "افحص العتاد",
        "افحص حالة البطارية والحساسات عبر ADB diagnostics لاحقًا",
        StepKind.CHECK,
    )


def _warnings_for(
    report: DeviceIntelligenceReport,
    symptom: Symptom,
    probe: ProtocolProbe | None,
    risk: RiskLevel,
) -> tuple[str, ...]:
    warnings: list[str] = [
        "الخطة قراءة فقط؛ لا كتابة ولا فلاش ولا تعديل معرفات",
    ]
    if risk is RiskLevel.ELEVATED:
        warnings.append("المخاطر مرتفعة؛ توقف حتى رفع الثقة أو توثيق البروتوكول")
    if report.mode is DeviceMode.MASS_STORAGE:
        warnings.append("وضع التخزين الحالي لا يدعم التشخيص العميق")
    if probe is not None and probe.status is ProbeStatus.UNRECOGNIZED:
        warnings.append("البروتوكول غير موثق حتى الآن")
    if symptom is Symptom.INVALID_IDENTITY:
        warnings.append("التحقق من الصيغة لا يثبت الأصالة أو الملكية")
    return tuple(warnings)


def _report_text(
    device: UsbDeviceInfo,
    report: DeviceIntelligenceReport,
    probe: ProtocolProbe | None,
    plan: RepairPlan,
) -> str:
    protocol_label = probe.label if probe is not None else "Not inspected"
    lines = [
        "NanoMobo Repair Assistant",
        f"Device: {device.display_name}",
        f"ID: {device.id_label}",
        f"Mode: {plan.mode_label}",
        f"Confidence: {plan.confidence}%",
        f"Protocol: {protocol_label}",
        f"Symptom: {_symptom_label(plan.symptom)}",
        f"Risk: {RISK_LABELS[plan.risk]}",
        f"Summary: {plan.summary}",
        "Steps:",
    ]
    lines.extend(
        f"{index}. {step.title}: {step.detail}"
        for index, step in enumerate(plan.steps, start=1)
    )
    lines.append("Warnings:")
    lines.extend(f"- {warning}" for warning in plan.warnings)
    lines.append("Safety: read-only; no writing, flashing, or IMEI modification.")
    return "\n".join(lines)


__all__ = [
    "PlanStep",
    "RepairPlan",
    "RISK_LABELS",
    "RiskLevel",
    "StepKind",
    "SYMTOMS",
    "Symptom",
    "create_repair_plan",
    "_symptom_label",
    "_risk_for",
    "_steps_for",
    "_warnings_for",
    "_report_text",
]
