"""NanoMobo design tokens — port of the nano business-suite design language.

Every color used across the app's views comes from here instead of being
repeated as a raw hex literal. The token set (names + light/dark values) is
the same family as nano so the two apps read as siblings: deep teal primary,
slate neutrals, rounded icons, soft low-opacity shadows, RTL-friendly spacing
and radius scales.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, ClassVar, cast

import flet as ft

# --- Mode state ----------------------------------------------------------#
_state: dict[str, str] = {"mode": "light"}


def get_mode() -> str:
    """The currently active resolved mode: ``"light"`` or ``"dark"``."""
    return _state["mode"]


def is_dark() -> bool:
    return _state["mode"] == "dark"


def set_mode(mode: str) -> None:
    """Set the active mode. Anything other than the literal ``"dark"`` is light."""
    _state["mode"] = "dark" if mode == "dark" else "light"


class _LightTokens:
    """Reference copy of every light-mode value (readable/greppable in one place)."""

    # Brand / primary — deep teal, shared with nano so both apps feel like one
    # family without colliding with success-green or the purple accent.
    PRIMARY = "#0F766E"
    PRIMARY_DARK = "#115E59"
    PRIMARY_BG = "#F0FDFA"
    PRIMARY_BORDER = "#99F6E4"

    # Neutral surfaces
    WHITE = "#FFFFFF"
    BACKGROUND = "#F8FAFC"
    BACKGROUND_ALT = "#F1F5F9"

    # Borders
    BORDER = "#E2E8F0"
    BORDER_ALT = "#E5E7EB"
    BORDER_STRONG = "#CBD5E1"

    # Text
    TEXT_PRIMARY = "#0F172A"
    TEXT_SECONDARY = "#64748B"
    TEXT_MUTED = "#475569"
    TEXT_MUTED_DARK = "#334155"
    TEXT_FAINT = "#94A3B8"

    # Success / green
    SUCCESS = "#16A34A"
    SUCCESS_DARK = "#15803D"
    SUCCESS_ALT = "#059669"
    SUCCESS_DARKER = "#166534"
    SUCCESS_BG = "#ECFDF5"

    # Danger / red
    DANGER = "#EF4444"
    DANGER_DARK = "#DC2626"
    DANGER_DARKER = "#B91C1C"
    DANGER_BG = "#FEF2F2"
    DANGER_BORDER = "#FECACA"

    # Warning / amber
    WARNING = "#F59E0B"
    WARNING_DARK = "#D97706"
    WARNING_DARKER = "#B45309"
    WARNING_BG = "#FFFBEB"
    WARNING_BG_ALT = "#FFF7ED"

    # Orange (distinct accent, e.g. IMEI / risky operations)
    ORANGE = "#EA580C"
    ORANGE_DARK = "#9A3412"

    # Purple (distinct accent, e.g. EFS / reports)
    PURPLE = "#7C3AED"
    PURPLE_LIGHT = "#8B5CF6"
    PURPLE_BG = "#F5F3FF"


_LIGHT: dict[str, str] = {k: v for k, v in vars(_LightTokens).items() if k.isupper()}

# Dark-mode counterpart — same token names, surfaces darker, text/accents
# lighter and slightly desaturated so nothing glows on an OLED screen at night.
_DARK: dict[str, str] = {
    "PRIMARY": "#2DD4BF",
    "PRIMARY_DARK": "#5EEAD4",
    "PRIMARY_BG": "#0F2E2B",
    "PRIMARY_BORDER": "#134E4A",
    "WHITE": "#1E293B",
    "BACKGROUND": "#0F172A",
    "BACKGROUND_ALT": "#1E293B",
    "BORDER": "#334155",
    "BORDER_ALT": "#334155",
    "BORDER_STRONG": "#475569",
    "TEXT_PRIMARY": "#F1F5F9",
    "TEXT_SECONDARY": "#94A3B8",
    "TEXT_MUTED": "#CBD5E1",
    "TEXT_MUTED_DARK": "#E2E8F0",
    "TEXT_FAINT": "#64748B",
    "SUCCESS": "#4ADE80",
    "SUCCESS_DARK": "#22C55E",
    "SUCCESS_ALT": "#34D399",
    "SUCCESS_DARKER": "#86EFAC",
    "SUCCESS_BG": "#0F2E1A",
    "DANGER": "#F87171",
    "DANGER_DARK": "#EF4444",
    "DANGER_DARKER": "#FCA5A5",
    "DANGER_BG": "#3A1214",
    "DANGER_BORDER": "#7F1D1D",
    "WARNING": "#FBBF24",
    "WARNING_DARK": "#F59E0B",
    "WARNING_DARKER": "#FDE68A",
    "WARNING_BG": "#3A2A0A",
    "WARNING_BG_ALT": "#3A230A",
    "ORANGE": "#FB923C",
    "ORANGE_DARK": "#FDBA74",
    "PURPLE": "#A78BFA",
    "PURPLE_LIGHT": "#C4B5FD",
    "PURPLE_BG": "#241A3A",
}

assert set(_DARK) == set(_LIGHT), "dark/light token tables drifted out of sync"


class _ColorsMeta(type):
    def __getattr__(cls, name: str) -> str:
        table = _DARK if _state["mode"] == "dark" else _LIGHT
        try:
            return table[name]
        except KeyError:
            raise AttributeError(name) from None


class Colors(metaclass=_ColorsMeta):
    """Mode-aware color tokens — every ``Colors.X`` access resolves against
    the active mode at read time, so a dark-mode switch repaints on the next
    view rebuild without touching a single call site.
    """


class Spacing:
    """Common spacing scale (px) used for padding/margins/gaps."""

    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 20
    XXL = 24


class Radius:
    """Common corner-radius scale (px)."""

    SM = 10
    MD = 14
    LG = 16
    XL = 20


class IconSize:
    """Icon-only button sizes (px), keyed by the *role* the icon plays."""

    INLINE = 18
    HEADER = 20
    HERO = 34


# Elevation scale (soft, low-opacity shadows) for surface depth, resolved
# against the active mode the same way ``Colors`` is.
_SHADOW_RECIPES: dict[str, tuple[int, int, tuple[int, int], str]] = {
    "SM": (10, 0, (0, 2), "BORDER"),
    "SOFT": (14, 0, (0, 3), "BORDER"),
    "MD": (18, 0, (0, 5), "BORDER"),
    "LG": (26, 0, (0, 9), "BORDER_STRONG"),
}


class _ShadowMeta(type):
    def __getattr__(cls, name: str) -> Any:
        try:
            blur, spread, (dx, dy), border_token = _SHADOW_RECIPES[name]
        except KeyError:
            raise AttributeError(name) from None
        return ft.BoxShadow(
            blur_radius=blur,
            spread_radius=spread,
            color=getattr(Colors, border_token),
            offset=ft.Offset(dx, dy),
        )


class Shadow(metaclass=_ShadowMeta):
    """Mode-aware elevation tokens — see ``Colors`` docstring for the pattern."""


class _SeverityStyles:
    """Lazily-resolved (color, bg, icon) triples keyed by alert severity.

    Shared by the diagnostics panel and the dashboard alerts card so a
    "warning" alert reads the same regardless of which screen renders it.
    """

    _RECIPES: ClassVar[dict[str, tuple[str, str, Any]]] = {
        "urgent": ("DANGER", "DANGER_BG", ft.Icons.PRIORITY_HIGH_ROUNDED),
        "warning": ("WARNING_DARK", "WARNING_BG", ft.Icons.WARNING_AMBER_ROUNDED),
        "info": ("PRIMARY", "PRIMARY_BG", ft.Icons.INFO_OUTLINE_ROUNDED),
    }

    def __getitem__(self, key: str) -> tuple[str, str, Any]:
        color_token, bg_token, icon = self._RECIPES[key]
        return (getattr(Colors, color_token), getattr(Colors, bg_token), icon)

    def get(
        self,
        key: str,
        default: tuple[str, str, Any] | None = None,
    ) -> tuple[str, str, Any] | None:
        try:
            return self[key]
        except KeyError:
            return default


class _StatusStyles:
    """Lazily-resolved (icon, text_color, bg_color, border_color) triples for
    the small inline status pill used across the app.
    """

    _RECIPES: ClassVar[dict[str, tuple[Any, str, str, str]]] = {
        "info": (ft.Icons.INFO_OUTLINE_ROUNDED, "TEXT_SECONDARY", "BACKGROUND_ALT", "BORDER"),
        "success": (ft.Icons.CHECK_CIRCLE_ROUNDED, "SUCCESS_DARKER", "SUCCESS_BG", "SUCCESS"),
        "error": (ft.Icons.ERROR_ROUNDED, "DANGER_DARKER", "DANGER_BG", "DANGER_BORDER"),
        "pending": (ft.Icons.HOURGLASS_TOP_ROUNDED, "TEXT_MUTED", "BACKGROUND_ALT", "BORDER"),
    }

    def __getitem__(self, key: str) -> tuple[Any, str, str, str]:
        icon, color_token, bg_token, border_token = self._RECIPES[key]
        return (
            icon,
            getattr(Colors, color_token),
            getattr(Colors, bg_token),
            getattr(Colors, border_token),
        )

    def get(
        self,
        key: str,
        default: tuple[Any, str, str, str] | None = None,
    ) -> tuple[Any, str, str, str] | None:
        try:
            return self[key]
        except KeyError:
            return default


SEVERITY_STYLE = _SeverityStyles()
STATUS_STYLES = _StatusStyles()


class LazyPalette:
    """A ``list``-like sequence of ``Colors`` tokens resolved on access."""

    def __init__(self, *tokens: str):
        self._tokens = tokens

    def __len__(self) -> int:
        return len(self._tokens)

    def __getitem__(self, index: int) -> str:
        return cast(str, getattr(Colors, self._tokens[index]))

    def __iter__(self) -> Iterator[str]:
        return (cast(str, getattr(Colors, token)) for token in self._tokens)


__all__ = [
    "SEVERITY_STYLE",
    "STATUS_STYLES",
    "Colors",
    "IconSize",
    "LazyPalette",
    "Radius",
    "Shadow",
    "Spacing",
    "get_mode",
    "is_dark",
    "set_mode",
]
