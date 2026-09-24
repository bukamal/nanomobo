from __future__ import annotations

import threading
from collections.abc import Callable

from nanomobo.core.usb_bridge import UsbDeviceInfo, UsbHost, is_android


class UnsupportedPlatformError(RuntimeError):
    pass


class DeviceService:
    def __init__(
        self,
        provider: Callable[[], UsbHost] = UsbHost,
        platform_detector: Callable[[], bool] = is_android,
    ) -> None:
        self._provider = provider
        self._platform_detector = platform_detector
        self._host: UsbHost | None = None
        self._lock = threading.RLock()

    @property
    def supported(self) -> bool:
        return self._platform_detector()

    def list_devices(self) -> list[UsbDeviceInfo]:
        if not self.supported:
            raise UnsupportedPlatformError("Android USB Host is required")
        with self._lock:
            if self._host is None:
                self._host = self._provider()
            return self._host.list_devices()

    def close(self) -> None:
        with self._lock:
            if self._host is None:
                return
            self._host.close_all()
            self._host = None


__all__ = ["DeviceService", "UnsupportedPlatformError"]
