"""Autostart programs (hl.exec_cmd inside hl.on("hyprland.start", ...)) and
environment variables (hl.env)."""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ..util import escape


def build_autostart_env_page(ctx) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()

    autostart_group = Adw.PreferencesGroup(
        title="Autostart Programs",
        description="Each entry runs as its own shell command when Hyprland starts.",
    )
    page.add(autostart_group)
    autostart_rows: list = []

    def rebuild_autostart():
        for row in autostart_rows:
            autostart_group.remove(row)
        autostart_rows.clear()

        for idx, cmd in enumerate(ctx.state["autostart"]):
            entry = Adw.EntryRow(title=f"Command {idx + 1}", show_apply_button=True)
            entry.set_text(cmd)

            def make_apply(i=idx):
                def handler(r):
                    ctx.state["autostart"][i] = r.get_text()
                    ctx.save()
                return handler

            entry.connect("apply", make_apply())

            delete_btn = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
            delete_btn.add_css_class("flat")

            def make_delete(i=idx):
                def handler(_b):
                    del ctx.state["autostart"][i]
                    ctx.save()
                    rebuild_autostart()
                return handler

            delete_btn.connect("clicked", make_delete())
            entry.add_suffix(delete_btn)
            autostart_group.add(entry)
            autostart_rows.append(entry)

        autostart_group.add(add_autostart_row)
        autostart_rows.append(add_autostart_row)

    def on_add_autostart(*_a):
        ctx.state["autostart"].append("")
        ctx.save()
        rebuild_autostart()

    add_autostart_row = Adw.ButtonRow(title="Add Autostart Command", start_icon_name="list-add-symbolic")
    add_autostart_row.connect("activated", on_add_autostart)
    rebuild_autostart()

    env_group = Adw.PreferencesGroup(
        title="Environment Variables",
        description="Set via hl.env(NAME, VALUE). Takes effect on the next full Hyprland restart.",
    )
    page.add(env_group)
    env_rows: list = []

    def rebuild_env():
        for row in env_rows:
            env_group.remove(row)
        env_rows.clear()

        for name, value in list(ctx.state["env"].items()):
            expander = Adw.ExpanderRow(title=escape(name) or "(unnamed)", subtitle=escape(value))

            name_entry = Adw.EntryRow(title="Name", show_apply_button=True)
            name_entry.set_text(name)
            value_entry = Adw.EntryRow(title="Value", show_apply_button=True)
            value_entry.set_text(value)

            def make_rename(old_name=name):
                def handler(r):
                    new_name = r.get_text().strip()
                    if not new_name or new_name == old_name:
                        r.set_text(old_name)
                        return
                    if new_name in ctx.state["env"]:
                        ctx.toast(f"{new_name} already exists")
                        r.set_text(old_name)
                        return
                    ctx.state["env"][new_name] = ctx.state["env"].pop(old_name)
                    ctx.save()
                    rebuild_env()
                return handler

            def make_value_apply(n=name):
                def handler(r):
                    ctx.state["env"][n] = r.get_text()
                    ctx.save()
                return handler

            name_entry.connect("apply", make_rename())
            value_entry.connect("apply", make_value_apply())
            expander.add_row(name_entry)
            expander.add_row(value_entry)

            delete_btn = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
            delete_btn.add_css_class("flat")

            def make_delete(n=name):
                def handler(_b):
                    del ctx.state["env"][n]
                    ctx.save()
                    rebuild_env()
                return handler

            delete_btn.connect("clicked", make_delete())
            expander.add_action(delete_btn)
            env_group.add(expander)
            env_rows.append(expander)

        env_group.add(add_env_row)
        env_rows.append(add_env_row)

    def on_add_env(*_a):
        new_key = "NEW_VAR"
        n = 1
        while new_key in ctx.state["env"]:
            n += 1
            new_key = f"NEW_VAR_{n}"
        ctx.state["env"][new_key] = ""
        ctx.save()
        rebuild_env()

    add_env_row = Adw.ButtonRow(title="Add Environment Variable", start_icon_name="list-add-symbolic")
    add_env_row.connect("activated", on_add_env)
    rebuild_env()

    return page
