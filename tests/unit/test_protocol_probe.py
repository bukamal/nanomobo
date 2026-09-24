from __future__ import annotations

from nanomobo.core.device_db import DeviceMode
from nanomobo.core.usb_bridge import Endpoint, Interface, UsbDeviceInfo
from nanomobo.protocols.base import ProbeStatus
from nanomobo.protocols.descriptor_probe import DescriptorProtocolProbe


def make_device(mode_vendor: int, mode_product: int) -> UsbDeviceInfo:
    return UsbDeviceInfo(
        device_name="1/1",
        vendor_id=mode_vendor,
        product_id=mode_product,
        device_class=0xFF,
        interfaces=[
            Interface(
                index=0,
                interface_class=0xFF,
                subclass=0,
                protocol=0,
                endpoints=[
                    Endpoint(
                        address=0x81,
                        direction="in",
                        transfer_type="bulk",
                        max_packet_size=512,
                    ),
                    Endpoint(
                        address=0x02,
                        direction="out",
                        transfer_type="bulk",
                        max_packet_size=512,
                    ),
                ],
            )
        ],
    )


def test_descriptor_probe_recognizes_edl_without_io() -> None:
    result = DescriptorProtocolProbe().inspect(make_device(0x05C6, 0x9008))
    assert result.mode is DeviceMode.QUALCOMM_EDL
    assert result.status is ProbeStatus.EXPERIMENTAL
    assert result.bulk_endpoint_count == 2
    assert result.read_only is True
    assert "لم يتم تشغيل handshake" in result.detail


def test_descriptor_probe_keeps_unknown_vendor_conservative() -> None:
    result = DescriptorProtocolProbe().inspect(make_device(0x0A9D, 0xFF40))
    assert result.status is ProbeStatus.UNRECOGNIZED
    assert "لم يتم إرسال أي أمر" in result.detail


def test_descriptor_probe_recognizes_adb_signature() -> None:
    device = UsbDeviceInfo(
        device_name="1/1",
        vendor_id=0x1234,
        product_id=0x5678,
        device_class=0xFF,
        interfaces=[Interface(0, 0xFF, 0x01, 0x01)],
    )
    result = DescriptorProtocolProbe().inspect(device)
    assert result.mode is DeviceMode.ADB
    assert result.status is ProbeStatus.EXPERIMENTAL
