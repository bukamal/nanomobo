from __future__ import annotations

from nanomobo.core.usb_bridge import UsbDeviceInfo
from nanomobo.protocols.base import ProtocolProbe, ReadOnlyProtocolProbe
from nanomobo.protocols.descriptor_probe import DescriptorProtocolProbe


class ProtocolService:
    def __init__(self, probe: ReadOnlyProtocolProbe | None = None) -> None:
        self._probe = probe or DescriptorProtocolProbe()

    def inspect(self, device: UsbDeviceInfo) -> ProtocolProbe:
        return self._probe.inspect(device)


__all__ = ["ProtocolService"]
