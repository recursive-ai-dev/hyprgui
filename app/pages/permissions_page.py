"""Screen-capture / plugin / keyboard permission rules (hl.permission).
Rules are matched in order; a binary matching a "deny" rule gets Hyprland's
built-in blank placeholder instead of real content for that capture -
your own physical display is unaffected, since it never goes through the
screencopy protocol these rules gate."""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ..util import escape

TYPES = ["screencopy", "keyboard", "plugin"]
MODES = ["deny", "allow", "ask"]


def build_permissions_page(ctx) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()
    group = Adw.PreferencesGroup(
        title="Permissions",
        description="Binary is a regex matched against the requesting executable's path "
        "(.* matches everything). Requires a config reload to take effect.",
    )
    page.add(group)
    rows: list = []

    def rebuild():
        for row in rows:
            group.remove(row)
        rows.clear()

        for idx, perm in enumerate(ctx.state["permissions"]):
            expander = Adw.ExpanderRow(
                title=escape(perm.get("binary", "")),
                subtitle=escape(f'{perm.get("type", "")} - {perm.get("mode", "")}'),
            )

            binary_entry = Adw.EntryRow(title="Binary (regex)", show_apply_button=True)
            binary_entry.set_text(perm.get("binary", ""))

            type_model = Gtk.StringList.new(TYPES)
            type_row = Adw.ComboRow(title="Type", model=type_model)
            type_row.set_selected(TYPES.index(perm.get("type", "screencopy")) if perm.get("type") in TYPES else 0)

            mode_model = Gtk.StringList.new(MODES)
            mode_row = Adw.ComboRow(title="Mode", model=mode_model)
            mode_row.set_selected(MODES.index(perm.get("mode", "deny")) if perm.get("mode") in MODES else 0)

            def make_update(i=idx):
                def handler(*_a):
                    ctx.state["permissions"][i] = {
                        "binary": binary_entry.get_text(),
                        "type": TYPES[type_row.get_selected()],
                        "mode": MODES[mode_row.get_selected()],
                    }
                    ctx.save()
                    expander.set_title(escape(binary_entry.get_text()))
                    expander.set_subtitle(escape(f"{TYPES[type_row.get_selected()]} - {MODES[mode_row.get_selected()]}"))
                return handler

            binary_entry.connect("apply", make_update())
            type_row.connect("notify::selected", make_update())
            mode_row.connect("notify::selected", make_update())

            expander.add_row(binary_entry)
            expander.add_row(type_row)
            expander.add_row(mode_row)

            delete_btn = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
            delete_btn.add_css_class("flat")

            def make_delete(i=idx):
                def handler(_b):
                    del ctx.state["permissions"][i]
                    ctx.save()
                    rebuild()
                return handler

            delete_btn.connect("clicked", make_delete())
            expander.add_action(delete_btn)
            group.add(expander)
            rows.append(expander)

        group.add(add_row)
        rows.append(add_row)

    def on_add(*_a):
        ctx.state["permissions"].append({"binary": ".*", "type": "screencopy", "mode": "deny"})
        ctx.save()
        rebuild()

    add_row = Adw.ButtonRow(title="Add Permission Rule", start_icon_name="list-add-symbolic")
    add_row.connect("activated", on_add)
    rebuild()

    return page
