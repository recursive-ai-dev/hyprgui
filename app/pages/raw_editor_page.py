"""Full raw-text access to every config file under ~/.config/hypr - the
guaranteed "low level" escape hatch for anything the structured pages don't
cover. No syntax-highlighting language/style schemes are bundled on this
system (the Debian gtksourceview5-common package ships none), so this uses
GtkSourceView only for its editing niceties (line numbers, current-line
highlight, bracket matching) rather than for colored syntax.
"""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Adw, Gtk, GtkSource

from .. import hypr_backend
from ..config_store import HYPR_DIR


def _discover_files() -> list:
    files = sorted(HYPR_DIR.glob("*.lua")) + sorted(HYPR_DIR.glob("*.conf"))
    return [f for f in files if f.is_file()]


def build_raw_editor_page(ctx) -> Adw.PreferencesPage:
    toolbar_view = Adw.ToolbarView()
    header = Adw.HeaderBar(show_title=False)
    toolbar_view.add_top_bar(header)

    buffer = GtkSource.Buffer()
    view = GtkSource.View(
        buffer=buffer,
        show_line_numbers=True,
        highlight_current_line=True,
        monospace=True,
        top_margin=8,
        left_margin=8,
        bottom_margin=8,
    )
    scroller = Gtk.ScrolledWindow(child=view, vexpand=True)
    toolbar_view.set_content(scroller)

    files = _discover_files()
    names = [f.name for f in files]
    model = Gtk.StringList.new(names)
    file_picker = Gtk.DropDown(model=model)
    header.pack_start(file_picker)

    status_label = Gtk.Label(label="", css_classes=["dim-label"])
    header.pack_start(status_label)

    save_btn = Gtk.Button(label="Save")
    reload_btn = Gtk.Button(label="Reload Hyprland", css_classes=["suggested-action"])
    header.pack_end(reload_btn)
    header.pack_end(save_btn)

    current_path = {"path": None}

    def load_selected(*_a):
        idx = file_picker.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION or idx >= len(files):
            return
        path = files[idx]
        current_path["path"] = path
        buffer.set_text(path.read_text())
        status_label.set_label(str(path))

    def on_save(*_a):
        path = current_path["path"]
        if path is None:
            return
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        path.write_text(text)
        ctx.toast(f"Saved {path.name}")

    def on_reload(*_a):
        on_save()
        ok = hypr_backend.reload()
        ctx.toast("Hyprland reloaded" if ok else "hyprctl reload failed - check for config errors")

    file_picker.connect("notify::selected", load_selected)
    save_btn.connect("clicked", on_save)
    reload_btn.connect("clicked", on_reload)

    if files:
        file_picker.set_selected(0)
        load_selected()

    return toolbar_view
