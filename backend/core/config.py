from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"


def _substitute_env(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("${") and value.endswith("}"):
            key = value[2:-1].strip()
            return os.getenv(key, "")
        return value
    if isinstance(value, list):
        return [_substitute_env(v) for v in value]
    if isinstance(value, dict):
        return {k: _substitute_env(v) for k, v in value.items()}
    return value


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return _substitute_env(data)


def load_app_config() -> Dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "app.yaml")


def load_providers_config() -> Dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "providers.yaml")
