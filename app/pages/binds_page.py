"""Keybind manager. Shows currently active binds (read-only, from hyprctl -j
binds, includes ones set elsewhere) plus a list of binds managed by this
app, added through a small templated dialog covering the common dispatcher
shapes - with a raw-Lua-expression escape hatch for anything else."""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from .. import hypr_backend
from ..util import escape

TEMPLATES = {
    "Run Command": ('hl.dsp.exec_cmd({arg!r})', "Shell command, e.g. kitty"),
    "Close Active Window": ("hl.dsp.window.close()", None),
    "Toggle Floating": ('hl.dsp.window.float({{ action = "toggle" }})', None),
    "Focus Direction": ('hl.dsp.focus({{ direction = {arg!r} }})', "left / right / up / down"),
    "Switch to Workspace": ("hl.dsp.focus({{ workspace = {arg} }})", "Workspace number"),
    "Move Window to Workspace": ("hl.dsp.window.move({{ workspace = {arg} }})", "Workspace number"),
    "Toggle Special Workspace": ('hl.dsp.workspace.toggle_special({arg!r})', "Scratchpad name, e.g. magic"),
    "Custom (raw Lua expression)": ("{arg}", 'e.g. hl.dsp.exec_cmd("firefox")'),
}


def build_binds_page(ctx) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()

    live_group = Adw.PreferencesGroup(
        title="Currently Active Binds",
        description="Read-only - includes binds set anywhere (hyprland.lua, hyprgui, etc).",
    )
    page.add(live_group)
    for b in hypr_backend.list_binds()[:200]:
        row = Adw.ActionRow(
            title=escape(b.get("key") or str(b.get("keycode", ""))),
            subtitle=escape(b.get("arg", "") or b.get("handler", "")),
        )
        live_group.add(row)

    managed_group = Adw.PreferencesGroup(
        title="Binds Managed by This App",
        description="Added here, applied via hl.bind() in hyprgui.lua.",
    )
    page.add(managed_group)
    managed_rows: list = []

    def rebuild():
        for row in managed_rows:
            managed_group.remove(row)
        managed_rows.clear()

        for idx, b in enumerate(ctx.state["binds"]):
            row = Adw.ActionRow(title=escape(b["combo"]), subtitle=escape(b["dispatcher_lua"]))
            delete_btn = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
            delete_btn.add_css_class("flat")

            def make_delete(i=idx):
                def handler(_b):
                    del ctx.state["binds"][i]
                    ctx.save()
                    rebuild()
                return handler

            delete_btn.connect("clicked", make_delete())
            row.add_suffix(delete_btn)
            managed_group.add(row)
            managed_rows.append(row)

        managed_group.add(add_row)
        managed_rows.append(add_row)

    def on_add(*_a):
        _open_add_dialog(ctx, page, rebuild)

    add_row = Adw.ButtonRow(title="Add Keybind", start_icon_name="list-add-symbolic")
    add_row.connect("activated", on_add)
    rebuild()

    return page


def _open_add_dialog(ctx, parent_widget, rebuild):
    dialog = Adw.Dialog(title="Add Keybind", content_width=420)
    toolbar_view = Adw.ToolbarView()
    toolbar_view.add_top_bar(Adw.HeaderBar())
    dialog.set_child(toolbar_view)

    page = Adw.PreferencesPage()
    toolbar_view.set_content(page)
    group = Adw.PreferencesGroup()
    page.add(group)

    mods_entry = Adw.EntryRow(title="Modifiers (e.g. SUPER, SUPER SHIFT)")
    mods_entry.set_text("SUPER")
    key_entry = Adw.EntryRow(title="Key (e.g. Q, left, XF86AudioMute)")
    desc_entry = Adw.EntryRow(title="Description (optional)")

    template_model = Gtk.StringList.new(list(TEMPLATES.keys()))
    template_row = Adw.ComboRow(title="Action", model=template_model)
    arg_entry = Adw.EntryRow(title="Argument")

    def on_template_changed(row, _param):
        name = list(TEMPLATES.keys())[row.get_selected()]
        _, placeholder = TEMPLATES[name]
        arg_entry.set_visible(placeholder is not None)
        if placeholder:
            arg_entry.set_title(placeholder)

    template_row.connect("notify::selected", on_template_changed)
    on_template_changed(template_row, None)

    for w in (mods_entry, key_entry, template_row, arg_entry, desc_entry):
        group.add(w)

    def on_add_clicked(_btn):
        name = list(TEMPLATES.keys())[template_row.get_selected()]
        pattern, _ = TEMPLATES[name]
        arg = arg_entry.get_text()
        try:
            dispatcher_lua = pattern.format(arg=arg)
        except (ValueError, IndexError):
            dispatcher_lua = pattern
        mods = mods_entry.get_text().strip()
        key = key_entry.get_text().strip()
        combo = f"{mods} + {key}" if mods else key
        if not key:
            return
        ctx.state["binds"].append({
            "combo": combo,
            "dispatcher_lua": dispatcher_lua,
            "opts": {},
            "desc": desc_entry.get_text(),
        })
        ctx.save()
        rebuild()
        dialog.close()

    add_btn = Gtk.Button(label="Add", css_classes=["suggested-action"])
    add_btn.connect("clicked", on_add_clicked)
    button_box = Gtk.Box(halign=Gtk.Align.END, margin_top=6, margin_bottom=12, margin_end=12)
    button_box.append(add_btn)
    page.add(_wrap_in_group(button_box))

    dialog.present(parent_widget)


def _wrap_in_group(widget) -> Adw.PreferencesGroup:
    group = Adw.PreferencesGroup()
    row = Adw.ActionRow()
    row.set_child(widget)
    group.add(row)
    return group
