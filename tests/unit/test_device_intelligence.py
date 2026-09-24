from __future__ import annotations

from nanomobo.core.device_db import DeviceMode
from nanomobo.core.device_intelligence import ConfidenceBand, analyze_device
from nanomobo.core.usb_bridge import Endpoint, Interface, UsbDeviceInfo


def make_device(
    vendor_id: int = 0x1234,
    product_id: int = 0x5678,
    interfaces: list[Interface] | None = None,
    serial_number: str = "",
    product: str = "",
) -> UsbDeviceInfo:
    return UsbDeviceInfo(
        device_name="1/1",
        vendor_id=vendor_id,
        product_id=product_id,
        device_class=0xFF,
        serial_number=serial_number,
        product=product,
        interfaces=interfaces if interfaces is not None else [],
    )


def test_known_edl_device_is_high_confidence_and_read_only() -> None:
    device = make_device(
        0x05C6,
        0x9008,
        serial_number="ABC123",
        product="EDL Test",
    )
    report = analyze_device(device)

    assert report.mode is DeviceMode.QUALCOMM_EDL
    assert report.band is ConfidenceBand.HIGH
    assert 80 <= report.confidence <= 100
    assert report.read_only is True
    assert report.writes_locked is True
    assert report.fingerprint == analyze_device(device).fingerprint
    assert any(item.title == "Product" for item in report.evidence)
    assert any("Qualcomm" in item.detail for item in report.evidence)


def test_unknown_vendor_device_stays_conservative() -> None:
    device = make_device(0x0A9D, 0xFF40)
    report = analyze_device(device)

    assert report.mode is DeviceMode.UNKNOWN
    assert report.band is ConfidenceBand.LOW
    assert report.confidence < 45
    assert report.writes_locked is True
    assert any("قراءة فقط" in item.title for item in report.recommendations)


def test_bulk_vendor_protocol_reaches_medium_confidence() -> None:
    interfaces = [
        Interface(
            0,
            0xFF,
            0,
            0,
            endpoints=[
                Endpoint(0x81, "in", "bulk", 512),
                Endpoint(0x02, "out", "bulk", 512),
            ],
        )
    ]
    device = make_device(0x0A9D, 0xFF40, interfaces=interfaces)
    report = analyze_device(device)

    assert report.mode is DeviceMode.VENDOR_PROTOCOL
    assert report.band is ConfidenceBand.MEDIUM
    assert report.confidence >= 45


def test_mass_storage_device_is_recognized_as_high_confidence() -> None:
    interfaces = [Interface(0, 0x08, 0x06, 0x50)]
    device = make_device(0x1234, 0x5678, interfaces=interfaces)
    report = analyze_device(device)

    assert report.mode is DeviceMode.MASS_STORAGE
    assert report.band is ConfidenceBand.HIGH
    assert report.confidence >= 80


def test_recommendations_never_suggest_identity_or_firmware_writes() -> None:
    device = make_device(0x05C6, 0x9008, product="EDL Test")
    report = analyze_device(device)
    recommendation_text = " ".join(item.detail for item in report.recommendations)

    assert "كتابة" in recommendation_text or "فلاش" in recommendation_text
    assert "IMEI" not in recommendation_text
    assert "تعديل" not in recommendation_text
