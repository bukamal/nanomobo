from __future__ import annotations

from nanomobo.core.device_db import DeviceMode
from nanomobo.core.usb_bridge import UsbDeviceInfo
from nanomobo.protocols.base import ProbeStatus, ProtocolProbe


class DescriptorProtocolProbe:
    def inspect(self, device: UsbDeviceInfo) -> ProtocolProbe:
        mode = device.mode
        interface_indexes = tuple(interface.index for interface in device.bulk_interfaces)
        bulk_endpoint_count = sum(
            len(interface.bulk_endpoints()) for interface in device.bulk_interfaces
        )
        label, status, detail = _describe(mode)
        return ProtocolProbe(
            mode=mode,
            status=status,
            label=label,
            detail=detail,
            interface_indexes=interface_indexes,
            bulk_endpoint_count=bulk_endpoint_count,
        )


def _describe(mode: DeviceMode) -> tuple[str, ProbeStatus, str]:
    if mode is DeviceMode.QUALCOMM_EDL:
        return (
            "Qualcomm EDL",
            ProbeStatus.EXPERIMENTAL,
            "تم التعرف على VID/PID؛ لم يتم تشغيل handshake أو إرسال أوامر",
        )
    if mode is DeviceMode.MEDIA_TEK_USB:
        return (
            "MediaTek USB",
            ProbeStatus.EXPERIMENTAL,
            "تم التعرف على USB؛ BROM/Preloader لم يتم تفعيله",
        )
    if mode is DeviceMode.ADB:
        return "ADB", ProbeStatus.EXPERIMENTAL, "واجهة ADB مرئية؛ parser لم يتم إضافته"
    if mode is DeviceMode.CDC:
        return "USB CDC", ProbeStatus.EXPERIMENTAL, "واجهة CDC مرئية؛ parser لم يتم إضافته"
    if mode in {DeviceMode.SAMSUNG_FASTBOOT, DeviceMode.GOOGLE_FASTBOOT}:
        return "Fastboot", ProbeStatus.EXPERIMENTAL, "تم التعرف على Fastboot؛ العمليات مقفلة"
    if mode is DeviceMode.MASS_STORAGE:
        return "USB Storage", ProbeStatus.RECOGNIZED, "وضع تخزين، وليس بروتوكول صيانة"
    return (
        "بروتوكول غير معروف",
        ProbeStatus.UNRECOGNIZED,
        "لا توجد قاعدة موثقة لهذا VID/PID؛ لم يتم إرسال أي أمر",
    )


__all__ = ["DescriptorProtocolProbe"]
