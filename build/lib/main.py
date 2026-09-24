from __future__ import annotations

from collections.abc import Callable
from typing import cast

import flet as ft

from nanomobo.core.theme import Colors, Radius, Shadow, Spacing
from nanomobo.services.device_service import DeviceService
from nanomobo.views.home_view import HomeView


def create_app(page: ft.Page) -> None:
    page.title = "NanoMobo"
    page.padding = Spacing.LG
    page.bgcolor = Colors.BACKGROUND
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=Colors.PRIMARY, use_material3=True)

    content = ft.Column(
        controls=[
            ft.Container(
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
                    ],
                    spacing=Spacing.MD,
                ),
                padding=Spacing.LG,
                bgcolor=Colors.WHITE,
                border_radius=Radius.LG,
                border=ft.Border.all(1, Colors.BORDER),
                shadow=Shadow.SM,
            ),
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
