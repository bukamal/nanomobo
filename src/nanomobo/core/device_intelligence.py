from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

from nanomobo.core.device_db import VENDOR_NAMES, DeviceMode, DeviceModeLabel
from nanomobo.core.usb_bridge import UsbDeviceInfo


class ConfidenceBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidencePolarity(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    CAUTION = "caution"


@dataclass(frozen=True, slots=True)
class Evidence:
    title: str
    detail: str
    weight: int
    polarity: EvidencePolarity


@dataclass(frozen=True, slots=True)
class Recommendation:
    title: str
    detail: str


@dataclass(frozen=True, slots=True)
class DeviceIntelligenceReport:
    device_name: str
    id_label: str
    fingerprint: str
    mode: DeviceMode
    confidence: int
    band: ConfidenceBand
    summary: str
    evidence: tuple[Evidence, ...]
    recommendations: tuple[Recommendation, ...]
    read_only: bool = True
    writes_locked: bool = True


_BASE_CONFIDENCE: dict[DeviceMode, int] = {
    DeviceMode.QUALCOMM_EDL: 88,
    DeviceMode.SAMSUNG_FASTBOOT: 86,
    DeviceMode.GOOGLE_FASTBOOT: 86,
    DeviceMode.ADB: 82,
    DeviceMode.CDC: 58,
    DeviceMode.MASS_STORAGE: 94,
    DeviceMode.MEDIA_TEK_USB: 62,
    DeviceMode.VENDOR_PROTOCOL: 42,
    DeviceMode.UNKNOWN: 12,
}

_KNOWN_PRODUCT_MODES = {
    DeviceMode.QUALCOMM_EDL,
    DeviceMode.SAMSUNG_FASTBOOT,
    DeviceMode.GOOGLE_FASTBOOT,
}


def analyze_device(device: UsbDeviceInfo) -> DeviceIntelligenceReport:
    mode = device.mode
    score = _BASE_CONFIDENCE[mode]
    evidence: list[Evidence] = []
    known_vendor = device.vendor_id in VENDOR_NAMES
    vendor_label = f"0x{device.vendor_id:04X}"
    mode_label = DeviceModeLabel[mode.name].value

    polarity = (
        EvidencePolarity.POSITIVE if mode is not DeviceMode.UNKNOWN else EvidencePolarity.CAUTION
    )
    evidence.append(
        Evidence(
            "وضع USB",
            mode_label,
            _BASE_CONFIDENCE[mode],
            polarity,
        )
    )

    if known_vendor:
        score += 6
        evidence.append(Evidence("Vendor", f"{vendor_label} موثق", 6, EvidencePolarity.POSITIVE))
    else:
        score -= 4
        evidence.append(
            Evidence(
                "Vendor",
                f"{vendor_label} غير موثق في القاعدة",
                -4,
                EvidencePolarity.NEUTRAL,
            )
        )

    if mode in _KNOWN_PRODUCT_MODES:
        score += 8
        evidence.append(
            Evidence("Product", "مطابقة قاعدة منتج معروفة", 8, EvidencePolarity.POSITIVE)
        )

    if device.serial_number:
        score += 4
        evidence.append(Evidence("Serial", "رقم التسلسل متاح", 4, EvidencePolarity.POSITIVE))

    if device.product or device.manufacturer:
        score += 4
        evidence.append(Evidence("التسمية", device.display_name, 4, EvidencePolarity.POSITIVE))

    bulk_endpoint_count = sum(len(interface.bulk_endpoints()) for interface in device.interfaces)
    if bulk_endpoint_count:
        score += 10
        evidence.append(
            Evidence(
                "Bulk",
                f"{bulk_endpoint_count} نقطة bulk",
                10,
                EvidencePolarity.POSITIVE,
            )
        )
    elif not device.interfaces:
        score -= 12
        evidence.append(
            Evidence(
                "Interfaces",
                "لا توجد interfaces معروفة",
                -12,
                EvidencePolarity.CAUTION,
            )
        )

    if device.device_class == 0xFF:
        evidence.append(
            Evidence(
                "Device class",
                "Composite/vendor-specific",
                0,
                EvidencePolarity.NEUTRAL,
            )
        )

    confidence = _clamp(score)
    band = _band_for(confidence)
    summary = (
        f"تم تصنيف {device.display_name} كـ{mode_label} بثقة {_band_label(band)} ({confidence}%)"
    )
    recommendations = _recommendations(mode, band, known_vendor)

    return DeviceIntelligenceReport(
        device_name=device.device_name,
        id_label=device.id_label,
        fingerprint=_fingerprint(device),
        mode=mode,
        confidence=confidence,
        band=band,
        summary=summary,
        evidence=tuple(evidence),
        recommendations=recommendations,
    )


def _fingerprint(device: UsbDeviceInfo) -> str:
    parts = [
        f"{device.vendor_id:04X}:{device.product_id:04X}",
        f"device_class=0x{device.device_class:02X}",
        device.product,
        device.manufacturer,
    ]
    for interface in device.interfaces:
        parts.append(
            f"i{interface.index}:0x{interface.interface_class:02X}-"
            f"0x{interface.subclass:02X}-0x{interface.protocol:02X}"
        )
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _clamp(score: int) -> int:
    return max(5, min(98, int(score)))


def _band_for(confidence: int) -> ConfidenceBand:
    if confidence >= 80:
        return ConfidenceBand.HIGH
    if confidence >= 45:
        return ConfidenceBand.MEDIUM
    return ConfidenceBand.LOW


def _band_label(band: ConfidenceBand) -> str:
    return {
        ConfidenceBand.LOW: "منخفضة",
        ConfidenceBand.MEDIUM: "متوسطة",
        ConfidenceBand.HIGH: "عالية",
    }[band]


def _recommendations(
    mode: DeviceMode,
    band: ConfidenceBand,
    known_vendor: bool,
) -> tuple[Recommendation, ...]:
    recommendations: list[Recommendation] = [
        Recommendation(
            "وضع القراءة فقط",
            "لا يتم إرسال أوامر كتابة أو فلاش قبل توثيق البروتوكول",
        )
    ]

    if mode is DeviceMode.QUALCOMM_EDL:
        recommendations.append(
            Recommendation(
                "خطوة آمنة",
                "اطلب صلاحية USB ثم راقب EDL transport دون إرسال أوامر",
            )
        )
    elif mode is DeviceMode.MEDIA_TEK_USB:
        recommendations.append(
            Recommendation(
                "خطوة آمنة",
                "وثّق BROM/Preloader signatures قبل أي تشغيل تجريبي",
            )
        )
    elif mode is DeviceMode.ADB:
        recommendations.append(
            Recommendation(
                "خطوة آمنة",
                "أضف ADB diagnostics عبر parser آمن لاحقًا",
            )
        )
    elif mode is DeviceMode.CDC:
        recommendations.append(
            Recommendation(
                "خطوة آمنة",
                "أضف serial protocol analyzer لقراءة البيانات فقط",
            )
        )
    elif mode is DeviceMode.MASS_STORAGE:
        recommendations.append(
            Recommendation(
                "تنبيه",
                "هذا وضع تخزين وليس وضع صيانة؛ تحقق من وضع الجهاز المطلوب",
            )
        )
    elif mode in {DeviceMode.SAMSUNG_FASTBOOT, DeviceMode.GOOGLE_FASTBOOT}:
        recommendations.append(
            Recommendation(
                "تحقق",
                "تحقق من حالة ownership/unlock قبل أي خطوة لاحقة",
            )
        )
    elif mode is DeviceMode.VENDOR_PROTOCOL:
        recommendations.append(
            Recommendation(
                "تحقق",
                "وثّق بيانات الواجهات وقارن القاعدة قبل دعم البروتوكول",
            )
        )
    else:
        recommendations.append(
            Recommendation(
                "تحفظ",
                "الاعتماد على descriptors فقط حتى توثيق القاعدة",
            )
        )

    if not known_vendor:
        recommendations.append(
            Recommendation(
                "قاعدة بيانات",
                "أضف معرف الجهاز محليًا بعد التحقق من المصدر",
            )
        )

    if band is ConfidenceBand.LOW:
        recommendations.append(
            Recommendation(
                "مستوى الثقة",
                "لا تفعّل أي تشغيل تجريبي قبل رفع مستوى الثقة",
            )
        )
    elif band is ConfidenceBand.MEDIUM:
        recommendations.append(
            Recommendation(
                "مستوى الثقة",
                "قارن القاعدة بالوثائق قبل المتابعة",
            )
        )

    return tuple(recommendations)


__all__ = [
    "ConfidenceBand",
    "DeviceIntelligenceReport",
    "Evidence",
    "EvidencePolarity",
    "Recommendation",
    "analyze_device",
]
