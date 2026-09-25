"""Key/value settings stores backing ``theme_settings`` preferences.

``theme_settings`` defines the ``SettingsStore`` protocol; this module provides
two concrete implementations: an in-memory store (tests, fallbacks) and a
JSON-file store (desktop/Android persistence). Every filesystem access is
guarded so an unwritable or corrupted store degrades to defaults instead of
crashing the app shell.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from pathlib import Path

from nanomobo.core.theme_settings import SettingsStore

logger = logging.getLogger(__name__)

ENV_SETTINGS_PATH = "NANOMOBO_SETTINGS_PATH"


class MemorySettingsStore:
    """In-memory ``SettingsStore`` — process-local and non-persistent."""

    def __init__(self, initial: Mapping[str, str] | None = None) -> None:
        self._data: dict[str, str] = {
            str(key): str(value) for key, value in (initial or {}).items()
        }

    def get(self, key: str, default: str) -> str:
        return self._data.get(key, default)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value
        self._persist()

    def set_many(self, values: Mapping[str, str]) -> None:
        self._data.update({str(key): str(value) for key, value in values.items()})
        self._persist()

    def _persist(self) -> None:
        return


class FileSettingsStore(MemorySettingsStore):
    """``SettingsStore`` persisted as a small JSON file under a private path."""

    def __init__(self, path: Path) -> None:
        self._path = path
        super().__init__(_load_json(path))

    def _persist(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
        except OSError:
            logger.warning("Unable to persist settings to %s", self._path, exc_info=True)


def default_settings_path() -> Path:
    override = os.environ.get(ENV_SETTINGS_PATH, "").strip()
    if override:
        return Path(override)
    return Path.home() / ".nanomobo" / "settings.json"


def create_settings_store() -> SettingsStore:
    """Create the default store; falls back to memory when the FS is unusable."""
    try:
        path = default_settings_path()
    except Exception:
        logger.warning("Unable to resolve a settings path; using memory store", exc_info=True)
        return MemorySettingsStore()
    return FileSettingsStore(path)


def _load_json(path: Path) -> dict[str, str]:
    try:
        if not path.is_file():
            return {}
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("Ignoring unreadable settings file %s", path, exc_info=True)
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items()}


__all__ = [
    "ENV_SETTINGS_PATH",
    "FileSettingsStore",
    "MemorySettingsStore",
    "create_settings_store",
    "default_settings_path",
]
