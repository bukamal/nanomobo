from __future__ import annotations

from nanomobo.core.identity import (
    IdentityKind,
    IdentityMatch,
    compare_identity,
    validate_identity,
)


def test_validates_imei_checksum_without_claiming_authenticity() -> None:
    result = validate_identity("49 015420 323751 8")
    assert result.kind is IdentityKind.IMEI
    assert result.valid_length is True
    assert result.valid_check_digit is True
    assert result.valid_format is True


def test_rejects_invalid_imei_checksum() -> None:
    result = validate_identity("490154203237517")
    assert result.kind is IdentityKind.IMEI
    assert result.valid_check_digit is False
    assert result.valid_format is False


def test_recognizes_meid_and_unknown_length() -> None:
    meid = validate_identity("A00000-12345678")
    unknown = validate_identity("123")
    assert meid.kind is IdentityKind.MEID
    assert meid.valid_format is True
    assert unknown.kind is IdentityKind.UNKNOWN
    assert unknown.valid_format is False


def test_compares_identity_slots() -> None:
    matching = compare_identity("490154203237518", "490154203237518")
    mismatching = compare_identity("490154203237518", "490154203237519")
    missing = compare_identity("", "490154203237518")
    assert matching.result is IdentityMatch.MATCH
    assert mismatching.result is IdentityMatch.MISMATCH
    assert missing.result is IdentityMatch.MISSING


def test_compares_hex_meid_case_insensitively() -> None:
    result = compare_identity("a0000012345678", "A00000-12345678")
    assert result.identical is True
