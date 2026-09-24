from __future__ import annotations

from typing import cast

from nanomobo.core.usb_bridge import UsbDeviceInfo, UsbHost
from nanomobo.services.device_service import DeviceService, UnsupportedPlatformError


class FakeHost:
    def __init__(self) -> None:
        self.devices = [
            UsbDeviceInfo(
                device_name="1/1",
                vendor_id=0x05C6,
                product_id=0x9008,
                device_class=0xFF,
            )
        ]
        self.closed = False
        self.permission = False
        self.requested_device = ""

    def find_device(self, device_name: str) -> object:
        self.requested_device = device_name
        return object()

    def has_permission(self, raw: object) -> bool:
        del raw
        return self.permission

    def request_permission(self, raw: object, timeout: float) -> bool:
        del raw, timeout
        self.permission = True
        return True

    def list_devices(self) -> list[UsbDeviceInfo]:
        return self.devices

    def close_all(self) -> None:
        self.closed = True


def test_device_service_rejects_desktop_without_creating_host() -> None:
    created = False

    def provider() -> UsbHost:
        nonlocal created
        created = True
        return cast(UsbHost, FakeHost())

    service = DeviceService(provider=provider, platform_detector=lambda: False)
    assert service.supported is False
    try:
        service.list_devices()
    except UnsupportedPlatformError:
        pass
    else:
        raise AssertionError("desktop discovery should be rejected")
    assert created is False


def test_device_service_reuses_and_closes_host() -> None:
    host = FakeHost()
    providers = 0

    def provider() -> UsbHost:
        nonlocal providers
        providers += 1
        return cast(UsbHost, host)

    service = DeviceService(provider=provider, platform_detector=lambda: True)
    assert service.list_devices() == host.devices
    assert service.list_devices() == host.devices
    assert providers == 1
    service.close()
    assert host.closed is True
    service.close()


def test_device_service_requests_permission_for_named_device() -> None:
    host = FakeHost()
    service = DeviceService(
        provider=lambda: cast(UsbHost, host),
        platform_detector=lambda: True,
    )
    assert service.has_permission("1/1") is False
    assert service.request_permission("1/1", timeout=0.1) is True
    assert service.has_permission("1/1") is True
    assert host.requested_device == "1/1"
    service.close()
