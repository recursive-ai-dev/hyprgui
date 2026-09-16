"""Manages hl.monitor() rules. Import seeds sensible defaults from the
monitors Hyprland currently sees (hyprctl -j monitors); edits here are
regenerated into hyprgui.lua in full each time."""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from .. import hypr_backend
from ..util import escape

FIELDS = ["output", "mode", "position", "scale", "transform"]


def build_monitors_page(ctx) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()
    group = Adw.PreferencesGroup(
        title="Monitors",
        description="Rules applied via hl.monitor(). 'output' is the connector name "
        "(e.g. eDP-1, DP-1) or empty for \"all monitors\".",
    )
    page.add(group)
    row_widgets: list = []

    def rebuild():
        for row in row_widgets:
            group.remove(row)
        row_widgets.clear()

        for idx, mon in list(enumerate(ctx.state["monitors"])):
            expander = Adw.ExpanderRow(
                title=escape(mon.get("output") or "(all monitors)"),
                subtitle=escape(mon.get("mode", "")),
            )
            for field in FIELDS:
                entry = Adw.EntryRow(title=field, show_apply_button=True)
                entry.set_text(mon.get(field, ""))

                def make_handler(i=idx, f=field):
                    def handler(r):
                        ctx.state["monitors"][i][f] = r.get_text()
                        ctx.save()
                        ctx.toast("Monitor rule updated - reload to apply")
                    return handler

                entry.connect("apply", make_handler())
                expander.add_row(entry)

            delete_btn = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
            delete_btn.add_css_class("flat")

            def make_delete(i=idx):
                def handler(_b):
                    del ctx.state["monitors"][i]
                    ctx.save()
                    rebuild()
                return handler

            delete_btn.connect("clicked", make_delete())
            expander.add_action(delete_btn)
            group.add(expander)
            row_widgets.append(expander)

        group.add(add_row)
        group.add(import_row)
        row_widgets.append(add_row)
        row_widgets.append(import_row)

    def on_add(*_a):
        ctx.state["monitors"].append({"output": "", "mode": "preferred", "position": "auto", "scale": "auto"})
        ctx.save()
        rebuild()

    def on_import(*_a):
        live = hypr_backend.list_monitors()
        ctx.state["monitors"] = [
            {
                "output": m.get("name", ""),
                "mode": f"{m.get('width', 0)}x{m.get('height', 0)}@{m.get('refreshRate', 60):.2f}",
                "position": f"{m.get('x', 0)}x{m.get('y', 0)}",
                "scale": str(m.get("scale", 1.0)),
                "transform": str(m.get("transform", 0)),
            }
            for m in live
        ]
        ctx.save()
        ctx.toast(f"Imported {len(live)} monitor(s)")
        rebuild()

    add_row = Adw.ButtonRow(title="Add Monitor Rule", start_icon_name="list-add-symbolic")
    add_row.connect("activated", on_add)
    import_row = Adw.ButtonRow(title="Import Currently Connected Monitors", start_icon_name="view-refresh-symbolic")
    import_row.connect("activated", on_import)

    rebuild()
    return page
