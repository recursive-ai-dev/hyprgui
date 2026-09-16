"""Builds one Adwaita preference row per schema option, picking the widget
from its declared kind (bool/int/float/string/color/vec2/cssgap). Every row
calls on_change(serialized_value: str) - the exact string form that both
`hyprctl keyword` and the generated Lua accept, so live-apply and
persistence never disagree.
"""
import re

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk


def humanize(leaf: str) -> str:
    return leaf.replace("_", " ").title()


def _color_to_rgba_string(rgba: Gdk.RGBA) -> str:
    r, g, b, a = (round(c * 255) for c in (rgba.red, rgba.green, rgba.blue, rgba.alpha))
    return f"rgba({r:02x}{g:02x}{b:02x}{a:02x})"


def _parse_color_str(value: str) -> Gdk.RGBA:
    rgba = Gdk.RGBA()
    m = re.search(r"rgba?\(?([0-9a-fA-F]{6,8})\)?", value or "")
    hexdigits = m.group(1) if m else "ffffffff"
    if len(hexdigits) == 6:
        hexdigits += "ff"
    r, g, b, a = (int(hexdigits[i:i + 2], 16) / 255 for i in (0, 2, 4, 6))
    rgba.red, rgba.green, rgba.blue, rgba.alpha = r, g, b, a
    return rgba


def build_row(option: dict, current_value, on_change) -> Gtk.Widget:
    kind = option["widget"]
    title = humanize(option["leaf"])
    subtitle = option["key"]

    if kind == "bool":
        row = Adw.SwitchRow(title=title, subtitle=subtitle)
        row.set_active(bool(current_value))
        row.connect("notify::active", lambda r, _p: on_change("true" if r.get_active() else "false"))
        return row

    if kind in ("int", "cssgap"):
        adj = Gtk.Adjustment(value=float(current_value or 0), lower=-100000, upper=100000, step_increment=1)
        row = Adw.SpinRow(title=title, subtitle=subtitle, adjustment=adj, digits=0)
        row.connect("notify::value", lambda r, _p: on_change(str(int(r.get_value()))))
        return row

    if kind == "float":
        adj = Gtk.Adjustment(value=float(current_value or 0), lower=-1000, upper=1000, step_increment=0.01)
        row = Adw.SpinRow(title=title, subtitle=subtitle, adjustment=adj, digits=4)
        row.connect("notify::value", lambda r, _p: on_change(f"{r.get_value():.6g}"))
        return row

    if kind == "vec2":
        try:
            x_val, y_val = (float(p) for p in str(current_value).strip("[]").replace(",", " ").split())
        except ValueError:
            x_val = y_val = 0.0
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        box = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        x_spin = Gtk.SpinButton.new_with_range(-100000, 100000, 1)
        y_spin = Gtk.SpinButton.new_with_range(-100000, 100000, 1)
        x_spin.set_value(x_val)
        y_spin.set_value(y_val)

        def emit(*_a):
            on_change(f"{int(x_spin.get_value())} {int(y_spin.get_value())}")

        x_spin.connect("value-changed", emit)
        y_spin.connect("value-changed", emit)
        box.append(x_spin)
        box.append(y_spin)
        row.add_suffix(box)
        return row

    if kind == "color":
        row = Adw.EntryRow(title=title, show_apply_button=True)
        row.set_text(str(current_value) if current_value is not None else "")
        row.connect("apply", lambda r: on_change(r.get_text()))

        dialog = Gtk.ColorDialog(with_alpha=True)
        button = Gtk.ColorDialogButton(dialog=dialog, valign=Gtk.Align.CENTER)
        button.set_rgba(_parse_color_str(str(current_value)))

        def on_picked(btn, _param):
            text = _color_to_rgba_string(btn.get_rgba())
            row.set_text(text)
            on_change(text)

        button.connect("notify::rgba", on_picked)
        row.add_suffix(button)
        return row

    # string fallback
    row = Adw.EntryRow(title=title, show_apply_button=True)
    row.set_text(str(current_value) if current_value is not None else "")
    row.connect("apply", lambda r: on_change(r.get_text()))
    return row
