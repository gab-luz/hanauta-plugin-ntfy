#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import tempfile
import time
import urllib.parse as parse
import urllib.request as request
from pathlib import Path
from typing import Any

import fcntl
import subprocess


SETTINGS_FILE = (
    Path.home()
    / ".local"
    / "state"
    / "hanauta"
    / "notification-center"
    / "settings.json"
)
STATE_DIR = Path.home() / ".local" / "state" / "hanauta" / "ntfy"
STATE_FILE = STATE_DIR / "receiver_state.json"
LOCK_FILE = STATE_DIR / "receiver.lock"
NOTIFICATION_ICON = Path(__file__).resolve().parent / "assets" / "icon.svg"
USER_AGENT = "Hanauta/ntfy-receiver/1.0"
DEFAULT_SERVER = "https://ntfy.sh"
POLL_INTERVAL_SECONDS = 1.0
TOPICS_REFRESH_INTERVAL_SECONDS = 30.0


def _normalize_poll_interval(value: object) -> float:
    try:
        parsed = float(value)
    except Exception:
        parsed = POLL_INTERVAL_SECONDS
    return max(1.0, min(60.0, parsed))


def _load_settings() -> dict[str, Any]:
    try:
        payload = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    ntfy = payload.get("ntfy", {})
    if not isinstance(ntfy, dict):
        ntfy = {}
    topics = [
        str(item).strip()
        for item in ntfy.get("topics", [])
        if isinstance(item, str) and str(item).strip()
    ]
    topic = str(ntfy.get("topic", "")).strip()
    if topic and topic not in topics:
        topics.append(topic)
    return {
        "enabled": bool(ntfy.get("enabled", False)),
        "server_url": str(ntfy.get("server_url", DEFAULT_SERVER)).strip().rstrip("/"),
        "topics": topics,
        "all_topics": bool(ntfy.get("all_topics", False)),
        "hide_notification_content": bool(ntfy.get("hide_notification_content", False)),
        "poll_interval_seconds": _normalize_poll_interval(
            ntfy.get("poll_interval_seconds", POLL_INTERVAL_SECONDS)
        ),
        "token": str(ntfy.get("token", "")),
        "username": str(ntfy.get("username", "")),
        "password": str(ntfy.get("password", "")),
        "auth_mode": str(ntfy.get("auth_mode", "token")).strip().lower(),
    }


def _normalize_auth_mode(raw: str, has_token: bool = False) -> str:
    mode = (raw or "").strip().lower()
    if mode in {"token", "bearer"}:
        return "token"
    if mode in {"basic", "username_password", "username-password", "userpass"}:
        return "basic"
    return "token" if has_token else "basic"


def _build_headers(settings: dict[str, Any]) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT}
    token = str(settings.get("token", "")).strip()
    username = str(settings.get("username", "")).strip()
    password = str(settings.get("password", ""))
    auth_mode = _normalize_auth_mode(
        str(settings.get("auth_mode", "token")), has_token=bool(token)
    )
    if auth_mode == "token" and token:
        headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "basic" and username:
        encoded = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode(
            "ascii"
        )
        headers["Authorization"] = f"Basic {encoded}"
    return headers


def _load_state() -> dict[str, Any]:
    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    last_ids = payload.get("last_ids", {})
    if not isinstance(last_ids, dict):
        last_ids = {}
    return {
        "last_ids": {str(k): str(v) for k, v in last_ids.items() if str(k).strip()},
        "missing_topic_warned": bool(payload.get("missing_topic_warned", False)),
    }


def _save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(STATE_DIR),
            prefix="receiver-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(json.dumps(state, indent=2))
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        os.replace(str(temp_path), str(STATE_FILE))
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _request_json(url: str, headers: dict[str, str], timeout: float) -> Any:
    req = request.Request(url, headers=headers)
    with request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
    if not body.strip():
        return None
    try:
        return json.loads(body)
    except Exception:
        events: list[dict[str, Any]] = []
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except Exception:
                continue
            if isinstance(payload, dict):
                events.append(payload)
        return events


def _fetch_topics(settings: dict[str, Any], headers: dict[str, str]) -> list[str]:
    server = str(settings.get("server_url", "")).strip().rstrip("/")
    if not server:
        return list(settings.get("topics", []))
    fallback = [str(item).strip() for item in settings.get("topics", []) if str(item).strip()]
    try:
        payload = _request_json(f"{server}/topics", headers, timeout=1.2)
    except Exception:
        return fallback
    parsed: list[str] = []
    if isinstance(payload, dict):
        raw = payload.get("topics", [])
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    value = str(item.get("topic", "")).strip()
                else:
                    value = str(item).strip()
                if value and value not in parsed:
                    parsed.append(value)
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                value = str(item.get("topic", "")).strip()
            else:
                value = str(item).strip()
            if value and value not in parsed:
                parsed.append(value)
    return parsed or fallback


def _notify(title: str, body: str) -> None:
    icon_name = "notifications"
    try:
        subprocess.Popen(
            [
                "gdbus",
                "call",
                "--session",
                "--dest",
                "org.freedesktop.Notifications",
                "--object-path",
                "/org/freedesktop/Notifications",
                "--method",
                "org.freedesktop.Notifications.Notify",
                "Hanauta ntfy",
                "0",
                icon_name,
                title,
                body,
                "[]",
                "{}",
                "5000",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


def _handle_event(
    event: dict[str, Any], topic: str, settings: dict[str, Any], state: dict[str, Any]
) -> bool:
    event_id = str(event.get("id", "")).strip()
    if not event_id:
        return False
    event_type = str(event.get("event", "")).strip().lower()
    if event_type and event_type != "message":
        state["last_ids"][topic] = event_id
        return False
    if str(state["last_ids"].get(topic, "")).strip() == event_id:
        return False
    state["last_ids"][topic] = event_id
    hide_content = bool(settings.get("hide_notification_content", False))
    raw_title = str(event.get("title", "")).strip()
    raw_message = str(event.get("message", "")).strip()
    if hide_content:
        title = "ntfy"
        body = f"New message on {topic}"
    else:
        title = raw_title or f"ntfy • {topic}"
        body = raw_message or "New message received."
    _notify(title, body)
    return True


def _poll_topic(
    settings: dict[str, Any], headers: dict[str, str], topic: str, state: dict[str, Any]
) -> bool:
    server = str(settings.get("server_url", "")).strip().rstrip("/")
    if not server or not topic:
        return False
    params = {"poll": "1"}
    since_id = str(state["last_ids"].get(topic, "")).strip()
    if since_id:
        params["since"] = since_id
    query = parse.urlencode(params)
    url = f"{server}/{parse.quote(topic)}/json?{query}"
    try:
        payload = _request_json(url, headers, timeout=0.9)
    except Exception:
        return False

    updated = False
    if isinstance(payload, dict):
        updated = _handle_event(payload, topic, settings, state)
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and _handle_event(item, topic, settings, state):
                updated = True
    return updated


def _acquire_lock() -> object | None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    handle = open(LOCK_FILE, "w", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def main() -> int:
    lock_handle = _acquire_lock()
    if lock_handle is None:
        return 0

    state = _load_state()
    next_topics_refresh = 0.0
    cached_topics: list[str] = []

    while True:
        loop_start = time.monotonic()
        settings = _load_settings()
        poll_interval = _normalize_poll_interval(
            settings.get("poll_interval_seconds", POLL_INTERVAL_SECONDS)
        )
        if not bool(settings.get("enabled", False)):
            time.sleep(poll_interval)
            continue

        server = str(settings.get("server_url", "")).strip().rstrip("/")
        headers = _build_headers(settings)
        if not server:
            time.sleep(poll_interval)
            continue

        if bool(settings.get("all_topics", False)):
            if loop_start >= next_topics_refresh:
                cached_topics = _fetch_topics(settings, headers)
                next_topics_refresh = loop_start + TOPICS_REFRESH_INTERVAL_SECONDS
            topics = list(cached_topics)
        else:
            topics = [str(item).strip() for item in settings.get("topics", []) if str(item).strip()]

        if not topics:
            if not bool(state.get("missing_topic_warned", False)):
                _notify(
                    "ntfy setup needed",
                    "No topic configured. Set a topic in Settings > Services > ntfy.",
                )
                state["missing_topic_warned"] = True
                _save_state(state)
            time.sleep(max(0.0, poll_interval - (time.monotonic() - loop_start)))
            continue
        if bool(state.get("missing_topic_warned", False)):
            state["missing_topic_warned"] = False
            _save_state(state)

        changed = False
        for topic in topics:
            if _poll_topic(settings, headers, topic, state):
                changed = True
        if changed:
            _save_state(state)

        elapsed = time.monotonic() - loop_start
        time.sleep(max(0.0, poll_interval - elapsed))


if __name__ == "__main__":
    raise SystemExit(main())
