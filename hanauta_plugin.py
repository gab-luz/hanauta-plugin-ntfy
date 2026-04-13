#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

PLUGIN_ROOT = Path(__file__).resolve().parent
SERVICE_KEY = "ntfy_widget"


def _normalize_poll_interval(value: object) -> float:
    try:
        parsed = float(value)
    except Exception:
        parsed = 1.0
    return max(1.0, min(60.0, parsed))


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


def _set_ntfy_poll_interval(window, seconds: object) -> float:
    ntfy = window.settings_state.setdefault("ntfy", {})
    if not isinstance(ntfy, dict):
        ntfy = {}
        window.settings_state["ntfy"] = ntfy
    normalized = _normalize_poll_interval(seconds)
    ntfy["poll_interval_seconds"] = normalized
    if hasattr(window, "_save_settings"):
        window._save_settings()
    return normalized


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
    ntfy.setdefault("poll_interval_seconds", 1.0)

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

    poll_wrap = QWidget()
    poll_layout = QHBoxLayout(poll_wrap)
    poll_layout.setContentsMargins(0, 0, 0, 0)
    poll_layout.setSpacing(8)
    poll_input = QLineEdit(
        f"{_normalize_poll_interval(ntfy.get('poll_interval_seconds', 1.0)):g}"
    )
    poll_input.setPlaceholderText("1")
    poll_input.setFixedWidth(90)
    save_poll_button = QPushButton("Save interval")
    save_poll_button.setObjectName("secondaryButton")
    save_poll_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _save_poll_interval() -> None:
        saved = _set_ntfy_poll_interval(window, poll_input.text())
        poll_input.setText(f"{saved:g}")
        status.setText(
            f"Polling interval saved: every {saved:g}s. "
            "Use the built-in ntfy section to configure server URL, auth, topics, and privacy options."
        )

    save_poll_button.clicked.connect(_save_poll_interval)
    poll_layout.addWidget(poll_input)
    poll_layout.addWidget(save_poll_button)
    poll_layout.addStretch(1)
    layout.addWidget(
        SettingsRow(
            material_icon("timer"),
            "Incoming check interval (seconds)",
            "How often ntfy checks for new messages. Range: 1 to 60 seconds.",
            window.icon_font,
            window.ui_font,
            poll_wrap,
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
