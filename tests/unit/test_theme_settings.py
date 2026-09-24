from __future__ import annotations

from collections.abc import Mapping

import pytest

from nanomobo.core.theme_settings import (
    MODE_DARK,
    MODE_LIGHT,
    MODE_SYSTEM,
    SCHEDULE_ENABLED_KEY,
    SCHEDULE_END_KEY,
    SCHEDULE_START_KEY,
    get_mode_preference,
    resolve_effective_mode,
    schedule_hours,
    set_mode_preference,
    set_schedule,
)


class MemorySettings:
    def __init__(self, values: Mapping[str, str] | None = None) -> None:
        self.values = dict(values or {})

    def get(self, key: str, default: str) -> str:
        return self.values.get(key, default)

    def set(self, key: str, value: str) -> None:
        self.values[key] = value

    def set_many(self, values: Mapping[str, str]) -> None:
        self.values.update(values)


def test_mode_preference_normalizes_and_validates() -> None:
    settings = MemorySettings()
    set_mode_preference(settings, " DARK ")
    assert settings.values["theme_mode"] == MODE_DARK
    set_mode_preference(settings, "invalid")
    assert get_mode_preference(settings) == MODE_SYSTEM


def test_schedule_hours_clamp_corrupt_values() -> None:
    settings = MemorySettings(
        {
            SCHEDULE_START_KEY: "-4",
            SCHEDULE_END_KEY: "inf",
        }
    )
    assert schedule_hours(settings) == (0, 6)


def test_overnight_schedule_wraps_midnight() -> None:
    from datetime import datetime

    settings = MemorySettings(
        {
            SCHEDULE_ENABLED_KEY: "1",
            SCHEDULE_START_KEY: "19",
            SCHEDULE_END_KEY: "6",
        }
    )
    assert (
        resolve_effective_mode(
            settings,
            system_is_dark=False,
            now=datetime(2026, 1, 1, 23),
        )
        == MODE_DARK
    )
    assert (
        resolve_effective_mode(
            settings,
            system_is_dark=False,
            now=datetime(2026, 1, 1, 7),
        )
        == MODE_LIGHT
    )


def test_equal_schedule_hours_falls_back_to_preference() -> None:
    settings = MemorySettings(
        {
            SCHEDULE_ENABLED_KEY: "1",
            SCHEDULE_START_KEY: "5",
            SCHEDULE_END_KEY: "5",
        }
    )
    assert (
        resolve_effective_mode(
            settings,
            system_is_dark=False,
        )
        == MODE_LIGHT
    )


def test_schedule_setter_rejects_invalid_ranges() -> None:
    settings = MemorySettings()
    with pytest.raises(ValueError, match="between 0 and 23"):
        set_schedule(settings, enabled=True, start_hour=24, end_hour=6)
    with pytest.raises(ValueError, match="must differ"):
        set_schedule(settings, enabled=True, start_hour=6, end_hour=6)
    with pytest.raises(TypeError, match="integer"):
        set_schedule(settings, enabled=True, start_hour=True, end_hour=6)
