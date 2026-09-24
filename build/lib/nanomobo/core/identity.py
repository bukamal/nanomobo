from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class IdentityKind(str, Enum):
    IMEI = "imei"
    MEID = "meid"
    UNKNOWN = "unknown"


class IdentityMatch(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class IdentityValidation:
    value: str
    kind: IdentityKind
    valid_length: bool
    valid_check_digit: bool | None

    @property
    def checksum_valid(self) -> bool:
        return self.valid_check_digit is not False

    @property
    def valid_format(self) -> bool:
        return self.valid_length and self.checksum_valid


@dataclass(frozen=True, slots=True)
class IdentityComparison:
    primary: str
    secondary: str
    result: IdentityMatch

    @property
    def identical(self) -> bool:
        return self.result is IdentityMatch.MATCH


def validate_identity(value: str) -> IdentityValidation:
    normalized = _normalize(value)
    if len(normalized) == 15 and normalized.isdigit():
        kind = IdentityKind.IMEI
        valid_length = True
        check_digit = _imei_check_digit_valid(normalized)
    elif len(normalized) == 14 and all(character in "0123456789ABCDEF" for character in normalized):
        kind = IdentityKind.MEID
        valid_length = True
        check_digit = None
    else:
        kind = IdentityKind.UNKNOWN
        valid_length = False
        check_digit = None
    return IdentityValidation(
        value=normalized,
        kind=kind,
        valid_length=valid_length,
        valid_check_digit=check_digit,
    )


def compare_identity(primary: str, secondary: str) -> IdentityComparison:
    primary_normalized = _normalize(primary)
    secondary_normalized = _normalize(secondary)
    if not primary_normalized or not secondary_normalized:
        result = IdentityMatch.MISSING
    elif primary_normalized == secondary_normalized:
        result = IdentityMatch.MATCH
    else:
        result = IdentityMatch.MISMATCH
    return IdentityComparison(primary_normalized, secondary_normalized, result)


def _normalize(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", value).upper()


def _imei_check_digit_valid(value: str) -> bool:
    if len(value) != 15 or not value.isdigit():
        return False
    total = 0
    for index, character in enumerate(value[:14]):
        digit = int(character)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return (10 - total % 10) % 10 == int(value[-1])


__all__ = [
    "IdentityComparison",
    "IdentityKind",
    "IdentityMatch",
    "IdentityValidation",
    "compare_identity",
    "validate_identity",
]
