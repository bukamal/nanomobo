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
