from __future__ import annotations

import json
from pathlib import Path

import pytest

import nanomobo.core.settings_store as settings_store
from nanomobo.core.settings_store import (
    ENV_SETTINGS_PATH,
    FileSettingsStore,
    MemorySettingsStore,
    create_settings_store,
    default_settings_path,
)


def test_memory_store_get_set_and_set_many() -> None:
    store = MemorySettingsStore({"a": "1"})
    assert store.get("a", "x") == "1"
    assert store.get("missing", "fallback") == "fallback"

    store.set("a", "2")
    store.set_many({"b": "3"})

    assert store.get("a", "x") == "2"
    assert store.get("b", "x") == "3"


def test_file_store_persists_and_reloads(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "settings.json"
    store = FileSettingsStore(path)
    store.set("theme_mode", "dark")
    store.set_many({"a": "1", "b": "2"})

    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["theme_mode"] == "dark"

    reloaded = FileSettingsStore(path)
    assert reloaded.get("theme_mode", "") == "dark"
    assert reloaded.get("b", "") == "2"


def test_file_store_ignores_corrupted_json(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{not-json", encoding="utf-8")

    store = FileSettingsStore(path)

    assert store.get("theme_mode", "default") == "default"


def test_file_store_ignores_non_object_json(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")

    store = FileSettingsStore(path)

    assert store.get("theme_mode", "default") == "default"


def test_file_store_persist_failure_does_not_raise(tmp_path: Path) -> None:
    store = FileSettingsStore(tmp_path)
    store.set("k", "v")

    assert store.get("k", "") == "v"


def test_default_settings_path_honors_env_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    custom = tmp_path / "custom.json"
    monkeypatch.setenv(ENV_SETTINGS_PATH, str(custom))

    assert default_settings_path() == custom


def test_default_settings_path_falls_back_to_home(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ENV_SETTINGS_PATH, raising=False)

    path = default_settings_path()

    assert path.name == "settings.json"
    assert path.parent.name == ".nanomobo"


def test_create_settings_store_returns_file_store(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(ENV_SETTINGS_PATH, str(tmp_path / "settings.json"))

    store = create_settings_store()

    assert isinstance(store, FileSettingsStore)


def test_create_settings_store_falls_back_to_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom() -> Path:
        raise RuntimeError("no settings path")

    monkeypatch.setattr(settings_store, "default_settings_path", boom)

    store = create_settings_store()

    assert isinstance(store, MemorySettingsStore)
