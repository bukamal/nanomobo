from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from nanomobo.core.device_db import DeviceMode


class CapabilityLevel(str, Enum):
    READY = "ready"
    EXPERIMENTAL = "experimental"
    BLOCKED = "blocked"


class CapabilityKey(str, Enum):
    DISCOVERY = "discovery"
    PERMISSION = "permission"
    PROTOCOL = "protocol"
    DEVICE_INFO = "device_info"
    BACKUP = "backup"
    RESTORE = "restore"
    FLASH = "flash"
    IDENTITY_READ = "identity_read"
    IDENTITY_WRITE = "identity_write"


@dataclass(frozen=True, slots=True)
class Capability:
    key: CapabilityKey
    label: str
    level: CapabilityLevel
    detail: str


@dataclass(frozen=True, slots=True)
class DeviceCapabilities:
    mode: DeviceMode
    items: tuple[Capability, ...]

    @property
    def protocol_ready(self) -> bool:
        return any(
            item.key is CapabilityKey.PROTOCOL and item.level is CapabilityLevel.READY
            for item in self.items
        )

    @property
    def summary(self) -> str:
        ready = [item.label for item in self.items if item.level is CapabilityLevel.READY]
        experimental = [
            item.label for item in self.items if item.level is CapabilityLevel.EXPERIMENTAL
        ]
        parts = []
        if ready:
            parts.append("جاهز: " + "، ".join(ready))
        if experimental:
            parts.append("تجريبي: " + "، ".join(experimental))
        if not parts:
            parts.append("لا توجد عمليات جاهزة")
        return " | ".join(parts)


def capabilities_for(mode: DeviceMode) -> DeviceCapabilities:
    protocol_detail = _protocol_detail(mode)
    protocol_level = (
        CapabilityLevel.EXPERIMENTAL
        if mode in {DeviceMode.QUALCOMM_EDL, DeviceMode.MEDIA_TEK_USB}
        else CapabilityLevel.BLOCKED
    )
    return DeviceCapabilities(
        mode=mode,
        items=(
            Capability(
                CapabilityKey.DISCOVERY,
                "اكتشاف USB",
                CapabilityLevel.READY,
                "واجهة USB Host تعمل",
            ),
            Capability(
                CapabilityKey.PERMISSION,
                "طلب صلاحية USB",
                CapabilityLevel.READY,
                "يتطلب موافقة Android",
            ),
            Capability(
                CapabilityKey.PROTOCOL,
                "بروتوكول الجهاز",
                protocol_level,
                protocol_detail,
            ),
            _blocked(CapabilityKey.DEVICE_INFO, "قراءة معلومات الجهاز", "تحتاج بروتوكولًا موثقًا"),
            _blocked(CapabilityKey.BACKUP, "نسخ EFS/البيانات", "غير مفعّل في طبقة البروتوكول"),
            _blocked(CapabilityKey.RESTORE, "استعادة البيانات", "محجوب حتى 검증 سلامة العملية"),
            _blocked(CapabilityKey.FLASH, "فلاش firmware", "غير مفعّل قبل إضافة بروتوكول جهاز"),
            _blocked(CapabilityKey.IDENTITY_READ, "قراءة IMEI/MEID", "تحتاج قناة قراءة معتمدة"),
            _blocked(
                CapabilityKey.IDENTITY_WRITE,
                "كتابة IMEI/MEID",
                "غير مسموح في هذه المرحلة",
            ),
        ),
    )


def _protocol_detail(mode: DeviceMode) -> str:
    if mode is DeviceMode.QUALCOMM_EDL:
        return "Transport EDL متاح، handshake غير مفعّل"
    if mode is DeviceMode.MEDIA_TEK_USB:
        return "Transport USB متاح، BROM/Preloader غير مفعّل"
    if mode is DeviceMode.ADB:
        return "ADB مرئي، لم يتم إضافة parser"
    if mode is DeviceMode.CDC:
        return "CDC مرئي، لم يتم إضافة parser"
    return "الوضع غير معروف"


def _blocked(key: CapabilityKey, label: str, detail: str) -> Capability:
    return Capability(key, label, CapabilityLevel.BLOCKED, detail)


__all__ = [
    "Capability",
    "CapabilityKey",
    "CapabilityLevel",
    "DeviceCapabilities",
    "capabilities_for",
]
