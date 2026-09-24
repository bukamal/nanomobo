from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from nanomobo.core.device_db import (
    USB_DIR_IN,
    XFER_BULK,
    XFER_CONTROL,
    XFER_INT,
    XFER_ISOC,
    DeviceMode,
    identify,
    vendor_name,
)

USB_SERVICE = "usb"
FLAG_IMMUTABLE = 0x02000000
MAX_BUFFER_BYTES = 1024 * 1024
MAX_CONTROL_BYTES = 16 * 1024

XFER_NAMES = {
    XFER_CONTROL: "control",
    XFER_ISOC: "isochronous",
    XFER_BULK: "bulk",
    XFER_INT: "interrupt",
}

logger = logging.getLogger(__name__)
TransferOperation = Literal[
    "bulk_write", "bulk_read", "bulk_write_all", "control_write", "control_read"
]


class TransferStatus(str, Enum):
    OK = "ok"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TransferResult:
    operation: TransferOperation
    endpoint_address: int
    requested: int
    transferred: int
    status: TransferStatus
    data: bytes = b""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is TransferStatus.OK

    @property
    def remaining(self) -> int:
        return max(0, self.requested - self.transferred)


@dataclass(frozen=True, slots=True)
class Endpoint:
    address: int
    direction: str
    transfer_type: str
    max_packet_size: int
    interval: int = 0

    @property
    def is_in(self) -> bool:
        return self.direction == "in"


@dataclass(slots=True)
class Interface:
    index: int
    interface_class: int
    subclass: int
    protocol: int
    endpoints: list[Endpoint] = field(default_factory=list)

    @property
    def vendor_specific(self) -> bool:
        return self.interface_class == 0xFF

    def bulk_endpoints(self) -> list[Endpoint]:
        return [endpoint for endpoint in self.endpoints if endpoint.transfer_type == "bulk"]


@dataclass(frozen=True, slots=True)
class UsbDeviceInfo:
    device_name: str
    vendor_id: int
    product_id: int
    device_class: int
    manufacturer: str = ""
    product: str = ""
    serial_number: str = ""
    interfaces: list[Interface] = field(default_factory=list)

    @property
    def vendor(self) -> str:
        return vendor_name(self.vendor_id)

    @property
    def mode(self) -> DeviceMode:
        return identify(
            self.vendor_id,
            self.product_id,
            [
                (interface.interface_class, interface.subclass, interface.protocol)
                for interface in self.interfaces
            ],
        )

    @property
    def id_label(self) -> str:
        return f"{self.vendor_id:04X}:{self.product_id:04X}"

    @property
    def display_name(self) -> str:
        return self.product or self.manufacturer or self.vendor

    @property
    def bulk_interfaces(self) -> list[Interface]:
        return [
            interface
            for interface in self.interfaces
            if interface.vendor_specific and interface.bulk_endpoints()
        ]


def is_android() -> bool:
    try:
        from jnius import autoclass

        autoclass("android.os.Build")
        return True
    except Exception:
        logger.debug("Android runtime is unavailable", exc_info=True)
        return False


class UsbHost:
    def __init__(self) -> None:
        self._context: Any | None = None
        self._manager: Any | None = None
        self._connections: dict[str, Any] = {}
        self._connection_names: dict[int, str] = {}
        self._claimed: dict[str, list[Any]] = {}
        self._active_sessions: set[str] = set()
        self._lock = threading.RLock()

    def _get_context(self) -> Any:
        if self._context is not None:
            return self._context

        from jnius import autoclass

        try:
            activity_thread = autoclass("android.app.ActivityThread")
            app = activity_thread.currentApplication()
            if app is not None:
                self._context = app
                return self._context
        except Exception:
            logger.debug("Unable to resolve Android application context", exc_info=True)

        host_name = os.environ.get("MAIN_ACTIVITY_HOST_CLASS_NAME")
        if host_name:
            host = autoclass(host_name)
            self._context = host.mActivity
            return self._context

        raise RuntimeError("Android Context is unavailable")

    @property
    def manager(self) -> Any:
        if self._manager is None:
            from jnius import cast

            context = self._get_context()
            service = context.getSystemService(USB_SERVICE)
            self._manager = cast("android.hardware.usb.UsbManager", service)
        return self._manager

    def list_devices(self) -> list[UsbDeviceInfo]:
        from jnius import cast

        raw_map = self.manager.getDeviceList()
        values = cast("java.util.Collection", raw_map.values())
        array = values.toArray()
        devices = [
            self._describe(cast("android.hardware.usb.UsbDevice", array[index]))
            for index in range(len(array))
        ]
        return sorted(devices, key=lambda device: (device.display_name.casefold(), device.id_label))

    def find_device(self, device_name: str) -> Any | None:
        from jnius import cast

        raw_map = self.manager.getDeviceList()
        for index in range(raw_map.size()):
            key = raw_map.keyAt(index)
            if str(key) == device_name:
                return cast("android.hardware.usb.UsbDevice", raw_map.get(key))
        return None

    def _describe(self, raw: Any) -> UsbDeviceInfo:
        from jnius import cast

        interfaces: list[Interface] = []
        for index in range(raw.getInterfaceCount()):
            usb_interface = cast("android.hardware.usb.UsbInterface", raw.getInterface(index))
            endpoints = [
                Endpoint(
                    address=endpoint.getAddress(),
                    direction="in" if endpoint.getAddress() & USB_DIR_IN else "out",
                    transfer_type=XFER_NAMES.get(endpoint.getType(), "unknown"),
                    max_packet_size=int(endpoint.getMaxPacketSize()),
                    interval=int(endpoint.getInterval()),
                )
                for endpoint in (
                    cast(
                        "android.hardware.usb.UsbEndpoint",
                        usb_interface.getEndpoint(endpoint_index),
                    )
                    for endpoint_index in range(usb_interface.getEndpointCount())
                )
            ]
            interfaces.append(
                Interface(
                    index=index,
                    interface_class=int(usb_interface.getInterfaceClass()),
                    subclass=int(usb_interface.getInterfaceSubclass()),
                    protocol=int(usb_interface.getInterfaceProtocol()),
                    endpoints=endpoints,
                )
            )

        return UsbDeviceInfo(
            device_name=str(raw.getDeviceName()),
            vendor_id=int(raw.getVendorId()),
            product_id=int(raw.getProductId()),
            device_class=int(raw.getDeviceClass()),
            manufacturer=_safe_str(raw, "getManufacturerName"),
            product=_safe_str(raw, "getProductName"),
            serial_number=_safe_str(raw, "getSerialNumber"),
            interfaces=interfaces,
        )

    def has_permission(self, raw: Any) -> bool:
        return bool(self.manager.hasPermission(raw))

    def request_permission(self, raw: Any, timeout: float = 20.0) -> bool:
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if self.has_permission(raw):
            return True

        self.manager.requestPermission(raw, self._permission_intent())
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.has_permission(raw):
                return True
            time.sleep(0.25)
        return False

    def _permission_intent(self) -> Any:
        from jnius import autoclass

        context = self._get_context()
        intent_class = autoclass("android.content.Intent")
        pending_intent_class = autoclass("android.app.PendingIntent")
        version = autoclass("android.os.Build$VERSION")
        package = str(context.getPackageName())
        intent = intent_class(package + ".USB_PERMISSION")
        intent.setPackage(package)
        flags = int(pending_intent_class.FLAG_UPDATE_CURRENT)
        if int(version.SDK_INT) >= 31:
            flags |= FLAG_IMMUTABLE
        return pending_intent_class.getBroadcast(context, 0, intent, flags)

    def open(self, raw: Any) -> Any:
        name = str(raw.getDeviceName())
        with self._lock:
            if name in self._active_sessions:
                raise RuntimeError("USB device already has an active session")
            connection = self._connections.get(name)
            if connection is not None:
                return connection
            return self._open_connection(raw)

    def _open_connection(self, raw: Any) -> Any:
        name = str(raw.getDeviceName())
        connection = self.manager.openDevice(raw)
        if connection is None:
            raise RuntimeError("Unable to open USB device")
        with self._lock:
            self._connections[name] = connection
            self._connection_names[id(connection)] = name
        return connection

    def claim(self, connection: Any, raw_interface: Any, force: bool = False) -> bool:
        claimed = bool(connection.claimInterface(raw_interface, bool(force)))
        if claimed:
            with self._lock:
                name = self._connection_names.get(id(connection))
                if name is not None:
                    interfaces = self._claimed.setdefault(name, [])
                    if not any(interface is raw_interface for interface in interfaces):
                        interfaces.append(raw_interface)
        return claimed

    def release(self, connection: Any, raw_interface: Any) -> bool:
        released = bool(connection.releaseInterface(raw_interface))
        if released:
            with self._lock:
                name = self._connection_names.get(id(connection))
                if name is not None:
                    interfaces = self._claimed.get(name, [])
                    self._claimed[name] = [
                        interface for interface in interfaces if interface is not raw_interface
                    ]
                    if not self._claimed[name]:
                        self._claimed.pop(name, None)
        return released

    def close(self, raw: Any) -> None:
        name = str(raw.getDeviceName())
        with self._lock:
            if name in self._active_sessions:
                raise RuntimeError("Cannot close a USB device with an active session")
        self._close_name(name)

    def _close_name(self, name: str) -> None:
        with self._lock:
            connection = self._connections.pop(name, None)
            interfaces = self._claimed.pop(name, [])
            if connection is not None:
                self._connection_names.pop(id(connection), None)

        for raw_interface in interfaces:
            if connection is None:
                break
            try:
                connection.releaseInterface(raw_interface)
            except Exception:
                logger.warning("Failed to release USB interface for %s", name, exc_info=True)
        if connection is not None:
            try:
                connection.close()
            except Exception:
                logger.warning("Failed to close USB device %s", name, exc_info=True)

    def close_all(self) -> None:
        with self._lock:
            names = [name for name in self._connections if name not in self._active_sessions]
        for name in names:
            self._close_name(name)

    @contextmanager
    def session(
        self,
        raw: Any,
        interfaces: Sequence[Any] = (),
        force: bool = False,
    ) -> Iterator[Any]:
        name = str(raw.getDeviceName())
        with self._lock:
            if name in self._active_sessions:
                raise RuntimeError("USB device already has an active session")
            self._active_sessions.add(name)
        connection: Any | None = None
        claimed: list[Any] = []
        try:
            connection = self._open_connection(raw)
            for raw_interface in interfaces:
                if not self.claim(connection, raw_interface, force=force):
                    raise RuntimeError("Unable to claim USB interface")
                claimed.append(raw_interface)
            yield connection
        finally:
            if connection is not None:
                for raw_interface in reversed(claimed):
                    try:
                        self.release(connection, raw_interface)
                    except Exception:
                        logger.warning(
                            "Failed to release USB interface during cleanup", exc_info=True
                        )
                self._close_name(name)
            with self._lock:
                self._active_sessions.discard(name)

    def reset_device(self, raw: Any) -> bool:
        try:
            with self.session(raw) as connection:
                return bool(connection.reset())
        except Exception:
            logger.warning("USB port reset failed for %s", raw.getDeviceName(), exc_info=True)
            return False

    def bulk_write(
        self,
        connection: Any,
        endpoint: Any,
        payload: bytes,
        timeout_ms: int = 5000,
    ) -> TransferResult:
        data = bytes(payload)
        _validate_buffer_size(len(data), MAX_BUFFER_BYTES)
        _validate_timeout(timeout_ms)
        if not data:
            return TransferResult("bulk_write", int(endpoint.getAddress()), 0, 0, TransferStatus.OK)

        buffer = _write_byte_array(data)
        count = int(
            connection.bulkTransfer(
                endpoint,
                buffer,
                0,
                len(data),
                timeout_ms,
            )
        )
        if count < 0:
            return TransferResult(
                "bulk_write",
                int(endpoint.getAddress()),
                len(data),
                0,
                TransferStatus.FAILED,
                error="USB bulk transfer failed",
            )
        return TransferResult(
            "bulk_write",
            int(endpoint.getAddress()),
            len(data),
            min(count, len(data)),
            TransferStatus.OK,
        )

    def bulk_write_all(
        self,
        connection: Any,
        endpoint: Any,
        payload: bytes,
        chunk_size: int = 64 * 1024,
        timeout_ms: int = 5000,
    ) -> TransferResult:
        data = bytes(payload)
        if not 0 < chunk_size <= MAX_BUFFER_BYTES:
            raise ValueError("chunk_size must be between 1 and MAX_BUFFER_BYTES")
        total = 0
        while total < len(data):
            chunk = data[total : total + chunk_size]
            result = self.bulk_write(connection, endpoint, chunk, timeout_ms)
            total += result.transferred
            if not result.ok or result.transferred == 0:
                return TransferResult(
                    "bulk_write_all",
                    result.endpoint_address,
                    len(data),
                    total,
                    TransferStatus.FAILED,
                    error=result.error or "USB bulk write made no progress",
                )
        return TransferResult(
            "bulk_write_all",
            int(endpoint.getAddress()),
            len(data),
            total,
            TransferStatus.OK,
        )

    def bulk_read(
        self,
        connection: Any,
        endpoint: Any,
        length: int,
        timeout_ms: int = 5000,
    ) -> TransferResult:
        _validate_read_size(length, MAX_BUFFER_BYTES)
        _validate_timeout(timeout_ms)
        buffer = _new_byte_array(length)
        count = int(connection.bulkTransfer(endpoint, buffer, 0, length, timeout_ms))
        if count < 0:
            return TransferResult(
                "bulk_read",
                int(endpoint.getAddress()),
                length,
                0,
                TransferStatus.FAILED,
                error="USB bulk transfer failed",
            )
        count = min(count, length)
        return TransferResult(
            "bulk_read",
            int(endpoint.getAddress()),
            length,
            count,
            TransferStatus.OK,
            data=_read_byte_array(buffer, count),
        )

    def control_write(
        self,
        connection: Any,
        request_type: int,
        request: int,
        value: int,
        index: int,
        payload: bytes = b"",
        timeout_ms: int = 1000,
    ) -> TransferResult:
        data = bytes(payload)
        _validate_control_request(request_type, request, value, index)
        _validate_buffer_size(len(data), MAX_CONTROL_BYTES)
        _validate_timeout(timeout_ms)
        buffer = _write_byte_array(data)
        count = int(
            connection.controlTransfer(
                request_type,
                request,
                value,
                index,
                buffer,
                0,
                len(data),
                timeout_ms,
            )
        )
        if count < 0:
            return TransferResult(
                "control_write",
                -1,
                len(data),
                0,
                TransferStatus.FAILED,
                error="USB control transfer failed",
            )
        return TransferResult(
            "control_write",
            -1,
            len(data),
            min(count, len(data)),
            TransferStatus.OK,
        )

    def control_read(
        self,
        connection: Any,
        request_type: int,
        request: int,
        value: int,
        index: int,
        length: int,
        timeout_ms: int = 1000,
    ) -> TransferResult:
        _validate_control_request(request_type, request, value, index)
        _validate_read_size(length, MAX_CONTROL_BYTES)
        _validate_timeout(timeout_ms)
        buffer = _new_byte_array(length)
        count = int(
            connection.controlTransfer(
                request_type,
                request,
                value,
                index,
                buffer,
                0,
                length,
                timeout_ms,
            )
        )
        if count < 0:
            return TransferResult(
                "control_read",
                -1,
                length,
                0,
                TransferStatus.FAILED,
                error="USB control transfer failed",
            )
        count = min(count, length)
        return TransferResult(
            "control_read",
            -1,
            length,
            count,
            TransferStatus.OK,
            data=_read_byte_array(buffer, count),
        )


def _validate_buffer_size(size: int, maximum: int) -> None:
    if size < 0 or size > maximum:
        raise ValueError(f"buffer size must be between 0 and {maximum}")


def _validate_read_size(size: int, maximum: int) -> None:
    if size <= 0 or size > maximum:
        raise ValueError(f"read length must be between 1 and {maximum}")


def _validate_timeout(timeout_ms: int) -> None:
    if timeout_ms <= 0:
        raise ValueError("timeout_ms must be greater than zero")


def _validate_control_request(request_type: int, request: int, value: int, index: int) -> None:
    if not 0 <= request_type <= 0xFF:
        raise ValueError("request_type must fit in one byte")
    if not 0 <= request <= 0xFF:
        raise ValueError("request must fit in one byte")
    if not 0 <= value <= 0xFFFF:
        raise ValueError("value must fit in two bytes")
    if not 0 <= index <= 0xFFFF:
        raise ValueError("index must fit in two bytes")


def _new_byte_array(size: int) -> Any:
    from jnius import autoclass

    return autoclass("[B")(size)


def _write_byte_array(data: bytes) -> Any:
    buffer = _new_byte_array(max(1, len(data)))
    for index, value in enumerate(data):
        buffer[index] = value & 0xFF
    return buffer


def _read_byte_array(buffer: Any, count: int) -> bytes:
    return bytes(int(buffer[index]) & 0xFF for index in range(count))


def _safe_str(raw: Any, getter: str) -> str:
    try:
        value = getattr(raw, getter)()
        return str(value) if value is not None else ""
    except Exception:
        return ""


__all__ = [
    "Endpoint",
    "Interface",
    "TransferOperation",
    "TransferResult",
    "TransferStatus",
    "UsbDeviceInfo",
    "UsbHost",
    "is_android",
]
