#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path


SERVICE_KEY = "ntfy_widget"
SETTINGS_FILE = (
    Path.home()
    / ".local"
    / "state"
    / "hanauta"
    / "notification-center"
    / "settings.json"
)


def _load_ntfy_settings(bar) -> dict:
    runtime = getattr(bar, "runtime_settings", {})
    if isinstance(runtime, dict):
        ntfy = runtime.get("ntfy", {})
        if isinstance(ntfy, dict):
            return ntfy
    try:
        payload = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    ntfy = payload.get("ntfy", {})
    return ntfy if isinstance(ntfy, dict) else {}


def register_hanauta_bar_plugin(bar, api: dict[str, object]) -> None:
    plugin_dir = Path(str(api.get("plugin_dir", ""))).expanduser()
    daemon_script = plugin_dir / "ntfy_receiver_daemon.py"
    if not daemon_script.exists():
        return

    register_hook = api.get("register_hook")
    python_bin_fn = api.get("python_bin")
    daemon_attr = "_ntfy_receiver_daemon_process"

    def _python_bin() -> str:
        if callable(python_bin_fn):
            try:
                value = str(python_bin_fn()).strip()
                if value:
                    return value
            except Exception:
                pass
        return "python3"

    def _ensure_running() -> None:
        process = getattr(bar, daemon_attr, None)
        if process is not None and process.poll() is None:
            return
        try:
            process = subprocess.Popen(
                [_python_bin(), str(daemon_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            setattr(bar, daemon_attr, process)
        except Exception:
            setattr(bar, daemon_attr, None)

    def _stop_running() -> None:
        process = getattr(bar, daemon_attr, None)
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except Exception:
                pass
        setattr(bar, daemon_attr, None)

    def _sync_daemon_state() -> None:
        ntfy = _load_ntfy_settings(bar)
        enabled = bool(ntfy.get("enabled", False))
        if enabled:
            _ensure_running()
        else:
            _stop_running()

    def _on_close() -> None:
        _stop_running()

    if callable(register_hook):
        register_hook("poll", _sync_daemon_state)
        register_hook("settings_reloaded", _sync_daemon_state)
        register_hook("close", _on_close)

    _sync_daemon_state()

