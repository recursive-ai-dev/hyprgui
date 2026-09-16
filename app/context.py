"""Shared app state: the persisted config_store state, plus a hook for
showing toast feedback from anywhere in the widget tree.
"""
from . import config_store, hypr_backend


class AppContext:
    def __init__(self):
        self.state = config_store.load_state()
        self.toast_overlay = None  # set by ui.py once the window exists

    def toast(self, message: str) -> None:
        if self.toast_overlay is not None:
            from gi.repository import Adw
            self.toast_overlay.add_toast(Adw.Toast(title=message, timeout=2))

    def set_option(self, key: str, kind: str, value: str) -> None:
        ok = hypr_backend.set_option(key, value)
        self.state["options"][key] = value
        self.state["option_kind"][key] = kind
        config_store.save_state(self.state)
        if not ok:
            self.toast(f"Applied on save, but hyprctl rejected {key} live - check the value")

    def save(self) -> None:
        config_store.save_state(self.state)
