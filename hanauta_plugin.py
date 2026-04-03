#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent
SERVICE_KEY = "ntfy_widget"


def register_hanauta_plugin() -> dict[str, object]:
    """Metadata-only plugin entrypoint for the ntfy popup widget.

    The popup itself is launched by Hanauta bar integration.
    """
    return {
        "id": SERVICE_KEY,
        "name": "ntfy",
        "service_sections": [],
    }
