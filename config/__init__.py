# config/__init__.py
"""Configuration management for the transcription application."""

import os
import yaml
from pathlib import Path

CONFIG_DIR = Path(__file__).parent
DEFAULT_CONFIG_PATH = CONFIG_DIR / "settings.yaml"


def load_config(config_path: str = None) -> dict:
    """Load configuration from YAML file."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(config: dict, config_path: str = None) -> None:
    """Save configuration to YAML file."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


__all__ = ['load_config', 'save_config', 'DEFAULT_CONFIG_PATH']
