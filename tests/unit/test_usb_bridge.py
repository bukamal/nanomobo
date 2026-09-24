from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from nanomobo.core import usb_bridge
from nanomobo.core.usb_bridge import TransferStatus, UsbHost


@dataclass
class FakeEndpoint:
    address: int = 0x02

    def getAddress(self) -> int:
        return self.address


@dataclass
class FakeRawDevice:
    name: str = "1/1"

    def getDeviceName(self) -> str:
        return self.name


class FakeConnection:
    def __init__(self) -> None:
        self.bulk_limit: int | None = None
        self.bulk_failure: int | None = None
        self.read_data = b""
        self.control_failure: int | None = None
        self.claimed: list[tuple[object, bool]] = []
        self.released: list[object] = []
        self.closed = False
        self.reset_called = False
        self.writes: list[bytes] = []
        self.control_writes: list[bytes] = []

    def claimInterface(self, raw_interface: object, force: bool) -> bool:
        self.claimed.append((raw_interface, force))
        return True

    def releaseInterface(self, raw_interface: object) -> bool:
        self.released.append(raw_interface)
        return True

    def close(self) -> None:
        self.closed = True

    def reset(self) -> bool:
        self.reset_called = True
        return True

    def bulkTransfer(
        self,
        endpoint: FakeEndpoint,
        buffer: bytearray,
        offset: int,
        length: int,
        timeout_ms: int,
    ) -> int:
        del endpoint, offset, timeout_ms
        if self.bulk_failure is not None:
            return self.bulk_failure
        if length == 0:
            return 0
        if self.read_data:
            data = self.read_data[:length]
            for index, value in enumerate(data):
                buffer[index] = value
            return len(data)
        if self.bulk_limit is not None:
            count = min(length, self.bulk_limit)
            self.writes.append(bytes(buffer[:count]))
            return count
        self.writes.append(bytes(buffer[:length]))
        return length

    def controlTransfer(
        self,
        request_type: int,
        request: int,
        value: int,
        index: int,
        buffer: bytearray,
        offset: int,
        length: int,
        timeout_ms: int,
    ) -> int:
        del request_type, request, value, index, offset, timeout_ms
        if self.control_failure is not None:
            return self.control_failure
        if length == 0:
            return 0
        if self.read_data:
            for position, byte in enumerate(self.read_data[:length]):
                buffer[position] = byte
            return min(length, len(self.read_data))
        self.control_writes.append(bytes(buffer[:length]))
        return length


@dataclass
class FakeManager:
    connection: FakeConnection | None = field(default_factory=FakeConnection)

    def openDevice(self, raw: FakeRawDevice) -> FakeConnection | None:
        del raw
        return self.connection


@pytest.fixture
def byte_array(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(usb_bridge, "_new_byte_array", lambda size: bytearray(size))


def make_host(connection: FakeConnection | None = None) -> UsbHost:
    host = UsbHost()
    host._manager = FakeManager(connection or FakeConnection())
    return host


def test_bulk_write_reports_partial_progress(byte_array: None) -> None:
    connection = FakeConnection()
    connection.bulk_limit = 2
    host = make_host(connection)
    result = host.bulk_write(connection, FakeEndpoint(), b"abcdef")
    assert result.status is TransferStatus.OK
    assert result.transferred == 2
    assert result.remaining == 4
    assert connection.writes == [b"ab"]


def test_bulk_write_all_stops_when_transfer_fails(byte_array: None) -> None:
    connection = FakeConnection()
    connection.bulk_failure = -1
    host = make_host(connection)
    result = host.bulk_write_all(connection, FakeEndpoint(), b"payload", chunk_size=2)
    assert result.status is TransferStatus.FAILED
    assert result.transferred == 0


def test_bulk_read_preserves_unsigned_bytes(byte_array: None) -> None:
    connection = FakeConnection()
    connection.read_data = b"\x00\x80\xff"
    host = make_host(connection)
    result = host.bulk_read(connection, FakeEndpoint(), 8)
    assert result.ok is True
    assert result.data == b"\x00\x80\xff"
    assert result.remaining == 5


def test_control_transfer_validates_request_fields(byte_array: None) -> None:
    connection = FakeConnection()
    host = make_host(connection)
    with pytest.raises(ValueError, match="request must fit"):
        host.control_write(connection, 0x40, 0x100, 0, 0, b"x")
    with pytest.raises(ValueError, match="read length"):
        host.control_read(connection, 0x80, 1, 0, 0, 0)


def test_session_claims_releases_and_closes(byte_array: None) -> None:
    connection = FakeConnection()
    host = make_host(connection)
    raw = FakeRawDevice()
    interface = object()
    with host.session(raw, interfaces=[interface]) as active:
        assert active is connection
        assert connection.claimed == [(interface, False)]
        with pytest.raises(RuntimeError, match="active session"):
            host.open(raw)
    assert connection.released == [interface]
    assert connection.closed is True


def test_direct_open_is_cached_and_closes(byte_array: None) -> None:
    connection = FakeConnection()
    host = make_host(connection)
    raw = FakeRawDevice()
    assert host.open(raw) is connection
    assert host.open(raw) is connection
    host.close(raw)
    assert connection.closed is True
