from __future__ import annotations

from nanomobo.core.capabilities import CapabilityKey, CapabilityLevel, capabilities_for
from nanomobo.core.device_db import DeviceMode


def test_unknown_device_exposes_only_safe_usb_capabilities() -> None:
    capabilities = capabilities_for(DeviceMode.UNKNOWN)
    levels = {item.key: item.level for item in capabilities.items}
    assert levels[CapabilityKey.DISCOVERY] is CapabilityLevel.READY
    assert levels[CapabilityKey.PERMISSION] is CapabilityLevel.READY
    assert levels[CapabilityKey.PROTOCOL] is CapabilityLevel.BLOCKED
    assert levels[CapabilityKey.IDENTITY_WRITE] is CapabilityLevel.BLOCKED
    assert capabilities.protocol_ready is False


def test_known_transport_is_experimental_until_protocol_parser_exists() -> None:
    capabilities = capabilities_for(DeviceMode.QUALCOMM_EDL)
    protocol = next(item for item in capabilities.items if item.key is CapabilityKey.PROTOCOL)
    assert protocol.level is CapabilityLevel.EXPERIMENTAL
    assert "EDL" in protocol.detail
    assert capabilities.protocol_ready is False


def test_capability_summary_never_promotes_blocked_operations() -> None:
    summary = capabilities_for(DeviceMode.VENDOR_PROTOCOL).summary
    assert "اكتشاف USB" in summary
    assert "فلاش" not in summary
