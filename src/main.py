from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import cast

import flet as ft

from nanomobo.core.settings_store import create_settings_store
from nanomobo.core.theme import Colors, Radius, Shadow, Spacing, set_mode
from nanomobo.core.theme_settings import (
    MODE_DARK,
    MODE_LABELS,
    MODE_SYSTEM,
    VALID_MODES,
    SettingsStore,
    get_mode_preference,
    resolve_effective_mode,
    set_mode_preference,
)
from nanomobo.services.device_service import DeviceService
from nanomobo.views.home_view import HomeView


def create_app(page: ft.Page, settings: SettingsStore | None = None) -> None:
    store = settings if settings is not None else create_settings_store()
    page.title = "NanoMobo"
    page.padding = Spacing.LG
    page.theme_mode = _resolved_theme_mode(page, store)
    _apply_palette(page)

    theme_button: ft.IconButton = ft.IconButton(
        icon=ft.Icons.DARK_MODE_ROUNDED,
        tooltip="الوضع: تلقائي حسب النظام",
        on_click=lambda _event: _cycle_theme_mode(page, store, theme_button),
    )
    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text("N", color=Colors.WHITE, weight=ft.FontWeight.W_700),
                    width=42,
                    height=42,
                    alignment=ft.Alignment.CENTER,
                    border_radius=Radius.MD,
                    bgcolor=Colors.PRIMARY,
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            "NanoMobo",
                            size=20,
                            weight=ft.FontWeight.W_700,
                            color=Colors.TEXT_PRIMARY,
                        ),
                        ft.Text(
                            "Device Service Platform",
                            size=12,
                            color=Colors.TEXT_SECONDARY,
                        ),
                    ],
                    spacing=0,
                ),
                theme_button,
            ],
            spacing=Spacing.MD,
        ),
        padding=Spacing.LG,
        bgcolor=Colors.WHITE,
        border_radius=Radius.LG,
        border=ft.Border.all(1, Colors.BORDER),
        shadow=Shadow.SM,
    )
    content = ft.Column(
        controls=[
            header,
            HomeView(page, DeviceService()),
        ],
        spacing=Spacing.LG,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
    page.add(content)
    home = content.controls[-1]
    if isinstance(home, HomeView):

        def on_disconnect(_event: object) -> None:
            home.close()

        page.on_disconnect = on_disconnect
        home.refresh_devices()


def _apply_palette(page: ft.Page) -> None:
    page.bgcolor = Colors.BACKGROUND
    page.theme = ft.Theme(color_scheme_seed=Colors.PRIMARY, use_material3=True)


def _resolved_theme_mode(page: ft.Page, settings: SettingsStore) -> ft.ThemeMode:
    effective = resolve_effective_mode(
        settings,
        system_is_dark=_system_is_dark(page),
    )
    set_mode(effective)
    if effective == MODE_DARK:
        return ft.ThemeMode.DARK
    return ft.ThemeMode.LIGHT


def _system_is_dark(page: ft.Page) -> bool:
    try:
        return bool(page.platform_brightness == ft.Brightness.DARK)
    except Exception:
        return False


def _cycle_theme_mode(page: ft.Page, settings: SettingsStore, button: ft.IconButton) -> None:
    store = settings
    current = get_mode_preference(store)
    next_mode = VALID_MODES[(VALID_MODES.index(current) + 1) % len(VALID_MODES)]
    set_mode_preference(store, next_mode)
    if next_mode == MODE_SYSTEM:
        effective = resolve_effective_mode(store, system_is_dark=_system_is_dark(page))
    else:
        effective = next_mode
    set_mode(effective)
    page.theme_mode = ft.ThemeMode.DARK if effective == MODE_DARK else ft.ThemeMode.LIGHT
    _apply_palette(page)
    button.tooltip = f"الوضع: {MODE_LABELS[next_mode]}"
    with contextlib.suppress(AssertionError, RuntimeError):
        page.update()


def main(page: ft.Page) -> None:
    create_app(page)


def run() -> None:
    runner = getattr(ft, "run", None)
    if callable(runner):
        runner(main)
        return
    legacy_app = cast(Callable[..., None], ft.app)
    legacy_app(target=main)


if __name__ == "__main__":
    run()


__all__ = ["create_app", "main", "run"]
