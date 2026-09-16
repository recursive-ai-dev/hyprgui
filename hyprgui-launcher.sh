#!/bin/sh
# hyprgui launcher - GTK4/LibAdwaita Hyprland settings app.
# venv uses --system-site-packages so system python3-gi is visible.
# Runs as `-m app` (not a direct file path) because the app's modules use
# package-relative imports (from . import schema, etc).
cd "$HOME/.local/share/hyprgui" || exit 1
exec "$HOME/.local/share/hyprgui/.venv/bin/python" -m app "$@"
