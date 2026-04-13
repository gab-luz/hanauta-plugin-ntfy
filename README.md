# Hanauta NTFY Plugin

NTFY popup plugin for Hanauta.

## Files
- `ntfy_popup.py`: PyQt6 popup used by the bar button.
- `hanauta_plugin.py`: plugin entrypoint metadata.
- `hanauta_bar_plugin.py`: bar integration that keeps the ntfy receiver daemon running when ntfy is enabled.
- `ntfy_receiver_daemon.py`: incoming ntfy listener that polls every 1 second and shows desktop notifications.
- `icon.svg`: plugin icon.

## Notes
- This plugin reuses Hanauta shared theme/font helpers from `hanauta/src/pyqt/shared`.
- Runtime settings are read from:
  - `~/.local/state/hanauta/notification-center/settings.json`

## Local run
```bash
python3 ntfy_popup.py
```
