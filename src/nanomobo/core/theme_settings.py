from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

MODE_KEY = "theme_mode"
SCHEDULE_ENABLED_KEY = "theme_schedule_enabled"
SCHEDULE_START_KEY = "theme_schedule_start_hour"
SCHEDULE_END_KEY = "theme_schedule_end_hour"

MODE_LIGHT = "light"
MODE_DARK = "dark"
MODE_SYSTEM = "system"
VALID_MODES = (MODE_LIGHT, MODE_DARK, MODE_SYSTEM)

DEFAULT_MODE = MODE_SYSTEM
DEFAULT_SCHEDULE_ENABLED = False
DEFAULT_SCHEDULE_START = 19
DEFAULT_SCHEDULE_END = 6

MODE_LABELS = {
    MODE_LIGHT: "فاتح",
    MODE_DARK: "داكن",
    MODE_SYSTEM: "تلقائي حسب النظام",
}


class SettingsStore(Protocol):
    def get(self, key: str, default: str) -> str: ...

    def set(self, key: str, value: str) -> None: ...

    def set_many(self, values: Mapping[str, str]) -> None: ...


def get_mode_preference(settings: SettingsStore) -> str:
    raw = str(settings.get(MODE_KEY, DEFAULT_MODE)).strip().lower()
    return raw if raw in VALID_MODES else DEFAULT_MODE


def set_mode_preference(settings: SettingsStore, mode: str) -> None:
    normalized = str(mode).strip().lower()
    settings.set(MODE_KEY, normalized if normalized in VALID_MODES else DEFAULT_MODE)


def schedule_enabled(settings: SettingsStore) -> bool:
    value = str(
        settings.get(SCHEDULE_ENABLED_KEY, "1" if DEFAULT_SCHEDULE_ENABLED else "0")
    ).strip()
    return value == "1"


def schedule_hours(settings: SettingsStore) -> tuple[int, int]:
    return (
        _coerce_hour(
            settings.get(SCHEDULE_START_KEY, str(DEFAULT_SCHEDULE_START)), DEFAULT_SCHEDULE_START
        ),
        _coerce_hour(
            settings.get(SCHEDULE_END_KEY, str(DEFAULT_SCHEDULE_END)), DEFAULT_SCHEDULE_END
        ),
    )


def set_schedule(
    settings: SettingsStore,
    *,
    enabled: bool,
    start_hour: int,
    end_hour: int,
) -> None:
    if isinstance(start_hour, bool) or not isinstance(start_hour, int):
        raise TypeError("start_hour must be an integer")
    if isinstance(end_hour, bool) or not isinstance(end_hour, int):
        raise TypeError("end_hour must be an integer")
    if not 0 <= start_hour <= 23:
        raise ValueError("start_hour must be between 0 and 23")
    if not 0 <= end_hour <= 23:
        raise ValueError("end_hour must be between 0 and 23")
    if start_hour == end_hour:
        raise ValueError("schedule start and end must differ")
    settings.set_many(
        {
            SCHEDULE_ENABLED_KEY: "1" if enabled else "0",
            SCHEDULE_START_KEY: str(start_hour),
            SCHEDULE_END_KEY: str(end_hour),
        }
    )


def resolve_effective_mode(
    settings: SettingsStore,
    *,
    system_is_dark: bool,
    now: datetime | None = None,
) -> str:
    if schedule_enabled(settings):
        start, end = schedule_hours(settings)
        hour = (now or datetime.now()).hour
        if start != end:
            in_window = (start <= hour < end) if start < end else (hour >= start or hour < end)
            if in_window:
                return MODE_DARK

    preference = get_mode_preference(settings)
    if preference == MODE_SYSTEM:
        return MODE_DARK if system_is_dark else MODE_LIGHT
    return preference


def _coerce_hour(value: str, default: int) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(number):
        return default
    return max(0, min(23, int(number)))


__all__ = [
    "DEFAULT_MODE",
    "DEFAULT_SCHEDULE_ENABLED",
    "DEFAULT_SCHEDULE_END",
    "DEFAULT_SCHEDULE_START",
    "MODE_DARK",
    "MODE_KEY",
    "MODE_LABELS",
    "MODE_LIGHT",
    "MODE_SYSTEM",
    "SCHEDULE_ENABLED_KEY",
    "SCHEDULE_END_KEY",
    "SCHEDULE_START_KEY",
    "VALID_MODES",
    "SettingsStore",
    "get_mode_preference",
    "resolve_effective_mode",
    "schedule_enabled",
    "schedule_hours",
    "set_mode_preference",
    "set_schedule",
]
