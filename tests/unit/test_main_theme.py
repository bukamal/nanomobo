from __future__ import annotations

from typing import Any, cast

import flet as ft

import main
from nanomobo.core.settings_store import MemorySettingsStore
from nanomobo.core.theme import get_mode, set_mode
from nanomobo.core.theme_settings import MODE_DARK, MODE_LIGHT, MODE_SYSTEM


class FakeThemePage:
    def __init__(self, brightness: ft.Brightness = ft.Brightness.LIGHT) -> None:
        self.bgcolor: Any = None
        self.theme: Any = None
        self.theme_mode: Any = None
        self.platform_brightness: Any = brightness
        self.updates = 0

    def update(self) -> None:
        self.updates += 1


class NoBrightnessPage:
    pass


def test_system_is_dark_reads_platform_brightness() -> None:
    dark_page = cast(ft.Page, FakeThemePage(ft.Brightness.DARK))
    light_page = cast(ft.Page, FakeThemePage(ft.Brightness.LIGHT))

    assert main._system_is_dark(dark_page) is True
    assert main._system_is_dark(light_page) is False


def test_system_is_dark_falls_back_when_brightness_missing() -> None:
    assert main._system_is_dark(cast(ft.Page, NoBrightnessPage())) is False


def test_apply_palette_sets_surface_and_theme() -> None:
    page = FakeThemePage()

    main._apply_palette(cast(ft.Page, page))

    assert page.bgcolor is not None
    assert isinstance(page.theme, ft.Theme)


def test_resolved_theme_mode_uses_saved_preference() -> None:
    store = MemorySettingsStore({"theme_mode": MODE_DARK})
    page = FakeThemePage(ft.Brightness.LIGHT)

    result = main._resolved_theme_mode(cast(ft.Page, page), store)

    assert result is ft.ThemeMode.DARK
    assert get_mode() == "dark"


def test_cycle_theme_mode_walks_light_dark_system() -> None:
    set_mode(MODE_LIGHT)
    store = MemorySettingsStore({"theme_mode": MODE_LIGHT})
    page = FakeThemePage(ft.Brightness.LIGHT)
    button = ft.IconButton()

    main._cycle_theme_mode(cast(ft.Page, page), store, button)
    assert store.get("theme_mode", "") == MODE_DARK
    observed: Any = page.theme_mode
    assert observed is ft.ThemeMode.DARK

    main._cycle_theme_mode(cast(ft.Page, page), store, button)
    assert store.get("theme_mode", "") == MODE_SYSTEM
    observed = page.theme_mode
    assert observed is ft.ThemeMode.LIGHT

    main._cycle_theme_mode(cast(ft.Page, page), store, button)
    assert store.get("theme_mode", "") == MODE_LIGHT
    observed = page.theme_mode
    assert observed is ft.ThemeMode.LIGHT
    assert page.updates == 3


def test_run_uses_modern_runner_when_available(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    def fake_run(target: Any) -> None:
        captured["target"] = target

    monkeypatch.setattr(ft, "run", fake_run)

    main.run()

    assert captured["target"] is main.main


def test_run_falls_back_to_legacy_app(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    monkeypatch.delattr(ft, "run", raising=False)

    def fake_app(target: Any) -> None:
        captured["target"] = target

    monkeypatch.setattr(ft, "app", fake_app, raising=False)

    main.run()

    assert captured["target"] is main.main
