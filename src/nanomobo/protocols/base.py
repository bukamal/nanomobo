from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from nanomobo.core.device_db import DeviceMode
from nanomobo.core.usb_bridge import UsbDeviceInfo


class ProbeStatus(str, Enum):
    RECOGNIZED = "recognized"
    EXPERIMENTAL = "experimental"
    UNRECOGNIZED = "unrecognized"


@dataclass(frozen=True, slots=True)
class ProtocolProbe:
    mode: DeviceMode
    status: ProbeStatus
    label: str
    detail: str
    interface_indexes: tuple[int, ...]
    bulk_endpoint_count: int
    requires_permission: bool = True
    read_only: bool = True


class ReadOnlyProtocolProbe(Protocol):
    def inspect(self, device: UsbDeviceInfo) -> ProtocolProbe: ...


__all__ = ["ProbeStatus", "ProtocolProbe", "ReadOnlyProtocolProbe"]
