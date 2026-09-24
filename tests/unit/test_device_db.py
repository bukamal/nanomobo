from __future__ import annotations

import pytest

from nanomobo.core.device_db import DeviceMode, identify, vendor_name


@pytest.mark.parametrize(
    ("vendor_id", "product_id", "interfaces", "expected"),
    [
        (0x05C6, 0x9008, [], DeviceMode.QUALCOMM_EDL),
        (0x04E8, 0x6601, [], DeviceMode.SAMSUNG_FASTBOOT),
        (0x18D1, 0x4EE7, [], DeviceMode.GOOGLE_FASTBOOT),
        (0x0E8D, 0x1234, [(0xFF, 0x01, 0x01)], DeviceMode.ADB),
        (0x0E8D, 0x1234, [(0x02, 0x02, 0x01)], DeviceMode.CDC),
        (0x0E8D, 0x1234, [(0x08, 0x06, 0x50)], DeviceMode.MASS_STORAGE),
        (0x0E8D, 0x1234, [(0xFF, 0x01, 0x02)], DeviceMode.VENDOR_PROTOCOL),
        (0x0E8D, 0x1234, [], DeviceMode.MEDIA_TEK_USB),
        (0xFFFF, 0xFFFF, [], DeviceMode.UNKNOWN),
        (0x10000, 0, [], DeviceMode.UNKNOWN),
    ],
)
def test_identifies_known_usb_modes(
    vendor_id: int,
    product_id: int,
    interfaces: list[tuple[int, int, int]],
    expected: DeviceMode,
) -> None:
    assert identify(vendor_id, product_id, interfaces) is expected


def test_rejects_malformed_interface_signature() -> None:
    assert identify(0x1234, 0x5678, [(0xFF, 0x01)]) is DeviceMode.UNKNOWN


def test_vendor_names_are_normalized() -> None:
    assert vendor_name(0x05C6) == "Qualcomm"
    assert vendor_name(0x0E8D) == "MediaTek"
    assert vendor_name(0xFFFF) == "Unknown (0xFFFF)"
    assert vendor_name(-1) == "Invalid USB vendor"
