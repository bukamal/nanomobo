from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import Enum


class DeviceMode(str, Enum):
    QUALCOMM_EDL = "qualcomm_edl"
    MEDIA_TEK_USB = "mediatek_usb"
    SAMSUNG_FASTBOOT = "samsung_fastboot"
    GOOGLE_FASTBOOT = "google_fastboot"
    ADB = "adb"
    CDC = "cdc"
    MASS_STORAGE = "mass_storage"
    VENDOR_PROTOCOL = "vendor_protocol"
    UNKNOWN = "unknown"


class DeviceModeLabel(str, Enum):
    QUALCOMM_EDL = "Qualcomm EDL 9008"
    MEDIA_TEK_USB = "MediaTek USB"
    SAMSUNG_FASTBOOT = "Samsung Fastboot"
    GOOGLE_FASTBOOT = "Google Fastboot"
    ADB = "ADB"
    CDC = "USB Serial / CDC"
    MASS_STORAGE = "USB Storage"
    VENDOR_PROTOCOL = "Vendor Protocol"
    UNKNOWN = "غير معروف"


USB_DIR_IN = 0x80
XFER_CONTROL = 0
XFER_ISOC = 1
XFER_BULK = 2
XFER_INT = 3

VENDOR_NAMES = {
    0x04E8: "Samsung",
    0x05C6: "Qualcomm",
    0x0E8D: "MediaTek",
    0x12D1: "Huawei",
    0x18D1: "Google",
    0x22B8: "Motorola",
    0x2E04: "Google / Android Composite",
    0x8087: "Intel",
}

_PRODUCT_MODES = {
    (0x05C6, 0x9008): DeviceMode.QUALCOMM_EDL,
    (0x04E8, 0x6601): DeviceMode.SAMSUNG_FASTBOOT,
    (0x18D1, 0x4EE7): DeviceMode.GOOGLE_FASTBOOT,
}

_VENDOR_MODES = {
    0x0E8D: DeviceMode.MEDIA_TEK_USB,
}


def vendor_name(vendor_id: int) -> str:
    value = int(vendor_id)
    if 0 <= value <= 0xFFFF and value in VENDOR_NAMES:
        return VENDOR_NAMES[value]
    return f"Unknown (0x{value:04X})" if 0 <= value <= 0xFFFF else "Invalid USB vendor"


def identify(
    vendor_id: int,
    product_id: int,
    interfaces: Iterable[Sequence[int]],
) -> DeviceMode:
    vendor = int(vendor_id)
    product = int(product_id)
    if not (0 <= vendor <= 0xFFFF and 0 <= product <= 0xFFFF):
        return DeviceMode.UNKNOWN

    known_product = _PRODUCT_MODES.get((vendor, product))
    if known_product is not None:
        return known_product

    normalized = tuple(tuple(int(part) for part in interface) for interface in interfaces)
    if any(len(interface) != 3 for interface in normalized):
        return DeviceMode.UNKNOWN
    if (0xFF, 0x01, 0x01) in normalized:
        return DeviceMode.ADB
    if any(interface[0] == 0x02 for interface in normalized):
        return DeviceMode.CDC
    if any(interface[0] == 0x08 for interface in normalized):
        return DeviceMode.MASS_STORAGE
    if any(interface[0] == 0xFF for interface in normalized):
        return DeviceMode.VENDOR_PROTOCOL

    return _VENDOR_MODES.get(vendor, DeviceMode.UNKNOWN)


__all__ = [
    "USB_DIR_IN",
    "VENDOR_NAMES",
    "XFER_BULK",
    "XFER_CONTROL",
    "XFER_INT",
    "XFER_ISOC",
    "DeviceMode",
    "DeviceModeLabel",
    "identify",
    "vendor_name",
]
