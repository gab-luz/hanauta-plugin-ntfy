#!/usr/bin/env python3
from __future__ import annotations

import sys
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


def _save_settings(window) -> None:
    module = sys.modules.get(window.__class__.__module__)
    save_function = (
        getattr(module, "save_settings_state", None) if module is not None else None
    )
    if callable(save_function):
        save_function(window.settings_state)
        return
    callback = getattr(window, "_save_settings", None)
    if callable(callback):
        callback()


def _parse_topics(value: object) -> list[str]:
    raw = str(value or "")
    parsed: list[str] = []
    for part in raw.split(","):
        topic = part.strip()
        if topic and topic not in parsed:
            parsed.append(topic)
    return parsed


def _topics_csv(ntfy: dict) -> str:
    topics = [
        str(item).strip()
        for item in ntfy.get("topics", [])
        if isinstance(item, str) and str(item).strip()
    ]
    legacy_topic = str(ntfy.get("topic", "")).strip()
    if legacy_topic and legacy_topic not in topics:
        topics.insert(0, legacy_topic)
    return ", ".join(topics)


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
    _save_settings(window)


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
    _save_settings(window)


def _set_ntfy_poll_interval(window, seconds: object) -> float:
    ntfy = window.settings_state.setdefault("ntfy", {})
    if not isinstance(ntfy, dict):
        ntfy = {}
        window.settings_state["ntfy"] = ntfy
    normalized = _normalize_poll_interval(seconds)
    ntfy["poll_interval_seconds"] = normalized
    _save_settings(window)
    return normalized


def _set_ntfy_topics(window, topic_csv: object) -> list[str]:
    ntfy = window.settings_state.setdefault("ntfy", {})
    if not isinstance(ntfy, dict):
        ntfy = {}
        window.settings_state["ntfy"] = ntfy
    topics = _parse_topics(topic_csv)
    ntfy["topics"] = topics
    ntfy["topic"] = topics[0] if topics else ""
    ntfy["all_topics"] = False
    _save_settings(window)
    return topics


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
    ntfy.setdefault("topic", "")
    ntfy.setdefault("topics", [])

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

    topic_wrap = QWidget()
    topic_layout = QHBoxLayout(topic_wrap)
    topic_layout.setContentsMargins(0, 0, 0, 0)
    topic_layout.setSpacing(8)
    topic_input = QLineEdit(_topics_csv(ntfy))
    topic_input.setPlaceholderText("topic-one, topic-two")
    save_topic_button = QPushButton("Save topics")
    save_topic_button.setObjectName("secondaryButton")
    save_topic_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _save_topics() -> None:
        topics = _set_ntfy_topics(window, topic_input.text())
        topic_input.setText(", ".join(topics))
        if topics:
            status.setText(
                f"Topics saved: {', '.join(topics)}. "
                "Use the built-in ntfy section to configure auth/privacy advanced options."
            )
        else:
            status.setText(
                "Topics cleared. Configure at least one topic to receive notifications."
            )

    save_topic_button.clicked.connect(_save_topics)
    topic_input.returnPressed.connect(_save_topics)
    topic_layout.addWidget(topic_input)
    topic_layout.addWidget(save_topic_button)
    layout.addWidget(
        SettingsRow(
            material_icon("notifications"),
            "Receive topics",
            "Comma-separated list of incoming ntfy topics used by desktop alerts.",
            window.icon_font,
            window.ui_font,
            topic_wrap,
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
