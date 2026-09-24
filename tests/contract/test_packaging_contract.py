from __future__ import annotations

from pathlib import Path
from typing import Any, cast

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import main

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config() -> dict[str, Any]:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as handle:
        return cast(dict[str, Any], tomllib.load(handle))


def test_entrypoint_matches_flet_configuration() -> None:
    config = load_config()
    app = config["tool"]["flet"]["app"]
    assert app == {"path": "src", "module": "main"}
    assert (PROJECT_ROOT / "src" / "main.py").is_file()
    assert callable(main.main)
    assert callable(main.run)


def test_android_packaging_contract() -> None:
    config = load_config()
    android = config["tool"]["flet"]["android"]
    assert "pyjnius" in android["dependencies"]
    assert android["feature"]["android.hardware.usb.host"] is True
    assert android["manifest_application"]["allowBackup"] == "false"


def test_runtime_dependency_is_reproducible() -> None:
    config = load_config()
    assert config["project"]["dependencies"] == ["flet==0.85.2"]
    assert "flet-cli==0.85.2" in config["project"]["optional-dependencies"]["dev"]
