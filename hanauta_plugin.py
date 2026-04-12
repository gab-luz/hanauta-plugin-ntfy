#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

PLUGIN_ROOT = Path(__file__).resolve().parent
SERVICE_KEY = "ntfy_widget"


def _set_ntfy_enabled(window, enabled: bool) -> None:
    if hasattr(window, "_set_ntfy_enabled") and callable(window._set_ntfy_enabled):
        window._set_ntfy_enabled(bool(enabled))
        return
    ntfy = window.settings_state.setdefault("ntfy", {})
    if not isinstance(ntfy, dict):
        ntfy = {}
        window.settings_state["ntfy"] = ntfy
    ntfy["enabled"] = bool(enabled)
    if not bool(enabled):
        ntfy["show_in_bar"] = False
    if hasattr(window, "_save_settings"):
        window._save_settings()


def _set_ntfy_show_in_bar(window, enabled: bool) -> None:
    if hasattr(window, "_set_ntfy_show_in_bar") and callable(window._set_ntfy_show_in_bar):
        window._set_ntfy_show_in_bar(bool(enabled))
        return
    ntfy = window.settings_state.setdefault("ntfy", {})
    if not isinstance(ntfy, dict):
        ntfy = {}
        window.settings_state["ntfy"] = ntfy
    if not bool(ntfy.get("enabled", False)):
        ntfy["show_in_bar"] = False
    else:
        ntfy["show_in_bar"] = bool(enabled)
    if hasattr(window, "_save_settings"):
        window._save_settings()


def build_ntfy_service_section(window, api: dict[str, object]) -> QWidget:
    SettingsRow = api["SettingsRow"]
    SwitchButton = api["SwitchButton"]
    ExpandableServiceSection = api["ExpandableServiceSection"]
    material_icon = api["material_icon"]
    icon_candidate = PLUGIN_ROOT / "assets" / "icon.svg"
    icon_path = (
        str(icon_candidate)
        if icon_candidate.exists()
        else str(api.get("plugin_icon_path", "")).strip()
    )

    ntfy = window.settings_state.setdefault("ntfy", {})
    if not isinstance(ntfy, dict):
        ntfy = {}
        window.settings_state["ntfy"] = ntfy
    ntfy.setdefault("enabled", False)
    ntfy.setdefault("show_in_bar", False)

    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)

    enable_switch = SwitchButton(bool(ntfy.get("enabled", False)))
    enable_switch.toggledValue.connect(lambda enabled: _set_ntfy_enabled(window, enabled))
    layout.addWidget(
        SettingsRow(
            material_icon("notifications"),
            "Enable ntfy integration",
            "Turn on ntfy publisher integration inside Hanauta.",
            window.icon_font,
            window.ui_font,
            enable_switch,
        )
    )

    bar_switch = SwitchButton(bool(ntfy.get("show_in_bar", False)))
    bar_switch.toggledValue.connect(
        lambda enabled: _set_ntfy_show_in_bar(window, enabled)
    )
    layout.addWidget(
        SettingsRow(
            material_icon("widgets"),
            "Show ntfy icon on bar",
            "Display the ntfy publish icon on the bar for quick access.",
            window.icon_font,
            window.ui_font,
            bar_switch,
        )
    )

    status = QLabel(
        "Use the built-in ntfy section to configure server URL, auth, topics, and privacy options."
    )
    status.setWordWrap(True)
    status.setStyleSheet("color: rgba(246,235,247,0.72);")
    layout.addWidget(status)

    section = ExpandableServiceSection(
        SERVICE_KEY,
        "ntfy",
        "Push notifications publishing service with optional bar quick access.",
        material_icon("notifications"),
        window.icon_font,
        window.ui_font,
        content,
        bool(ntfy.get("enabled", False)),
        lambda enabled: _set_ntfy_enabled(window, enabled),
        icon_path=icon_path,
    )
    window.service_sections[SERVICE_KEY] = section
    return section


def register_hanauta_plugin() -> dict[str, object]:
    return {
        "id": SERVICE_KEY,
        "name": "ntfy",
        "api_min_version": 1,
        "service_sections": [
            {
                "key": SERVICE_KEY,
                "builder": build_ntfy_service_section,
                "supports_show_on_bar": True,
            }
        ],
    }
