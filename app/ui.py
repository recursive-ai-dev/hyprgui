"""Main window. The sidebar list and the content it opens are built from
ONE data-driven list (NAV_ITEMS), each entry carrying its own page-builder
function - so there is no separate "list of sidebar labels" vs "dict of
pages" to drift out of sync (that mismatch is exactly the bug that made the
project this replaces mostly non-functional)."""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from . import schema
from .context import AppContext
from .ensure_require import ensure_required
from .pages.autostart_env_page import build_autostart_env_page
from .pages.binds_page import build_binds_page
from .pages.generic_page import build_section_page
from .pages.monitors_page import build_monitors_page
from .pages.permissions_page import build_permissions_page
from .pages.raw_editor_page import build_raw_editor_page
from .pages.rules_page import build_rules_page

SECTION_ORDER = [
    "general", "decoration", "animations", "input", "gestures", "group",
    "dwindle", "master", "scrolling", "layout", "misc", "binds", "cursor",
    "render", "opengl", "xwayland", "experimental", "input_capture",
    "quirks", "ecosystem", "debug",
]

SECTION_ICONS = {
    "general": "preferences-system-symbolic",
    "decoration": "applications-graphics-symbolic",
    "animations": "emblem-synchronizing-symbolic",
    "input": "input-keyboard-symbolic",
    "gestures": "input-touchpad-symbolic",
    "group": "view-grid-symbolic",
    "dwindle": "view-app-grid-symbolic",
    "master": "view-column-symbolic",
    "scrolling": "view-continuous-symbolic",
    "layout": "view-dual-symbolic",
    "misc": "preferences-other-symbolic",
    "binds": "preferences-desktop-keyboard-shortcuts-symbolic",
    "cursor": "input-mouse-symbolic",
    "render": "video-display-symbolic",
    "opengl": "video-display-symbolic",
    "xwayland": "window-new-symbolic",
    "experimental": "dialog-warning-symbolic",
    "input_capture": "input-tablet-symbolic",
    "quirks": "dialog-question-symbolic",
    "ecosystem": "network-workgroup-symbolic",
    "debug": "utilities-terminal-symbolic",
}


def _build_nav_items():
    present_sections = {o["section"] for o in schema.OPTIONS}
    ordered = [s for s in SECTION_ORDER if s in present_sections]
    ordered += sorted(present_sections - set(ordered))

    items = []
    for section in ordered:
        items.append({
            "title": schema.SECTION_LABELS.get(section, section.title()),
            "icon": SECTION_ICONS.get(section, "preferences-other-symbolic"),
            "builder": (lambda ctx, s=section: build_section_page(ctx, s)),
        })

    items.append({"title": "Monitors", "icon": "video-display-symbolic", "builder": build_monitors_page, "separator_before": True})
    items.append({"title": "Autostart and Env", "icon": "system-run-symbolic", "builder": build_autostart_env_page})
    items.append({"title": "Keybinds", "icon": "preferences-desktop-keyboard-symbolic", "builder": build_binds_page})
    items.append({"title": "Window / Layer / Workspace Rules", "icon": "view-list-symbolic", "builder": build_rules_page})
    items.append({"title": "Permissions", "icon": "channel-secure-symbolic", "builder": build_permissions_page})
    items.append({"title": "Raw Config Editor", "icon": "text-editor-symbolic", "builder": build_raw_editor_page, "separator_before": True})
    return items


NAV_ITEMS = _build_nav_items()


def _wrap_page(title: str, widget: Gtk.Widget) -> Gtk.Widget:
    if isinstance(widget, Adw.ToolbarView):
        return widget
    toolbar_view = Adw.ToolbarView()
    header = Adw.HeaderBar()
    header.set_title_widget(Adw.WindowTitle(title=title))
    toolbar_view.add_top_bar(header)
    scroller = Gtk.ScrolledWindow(child=widget, vexpand=True)
    toolbar_view.set_content(scroller)
    return toolbar_view


class HyprGuiWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="Hyprland Settings", default_width=980, default_height=680)
        self.ctx = AppContext()

        if not ensure_required():
            banner = Adw.Banner(
                title="~/.config/hypr/hyprland.lua not found - changes will only apply live, not persist.",
                revealed=True,
            )
        else:
            banner = None

        self.split_view = Adw.NavigationSplitView(min_sidebar_width=220, max_sidebar_width=280)

        sidebar_box = Gtk.ListBox(css_classes=["navigation-sidebar"])
        for item in NAV_ITEMS:
            if item.get("separator_before"):
                sep_row = Gtk.ListBoxRow(selectable=False, activatable=False)
                sep_row.set_child(Gtk.Separator())
                sidebar_box.append(sep_row)
            row = Adw.ActionRow(title=item["title"])
            row.add_prefix(Gtk.Image.new_from_icon_name(item["icon"]))
            sidebar_box.append(row)

        sidebar_scroller = Gtk.ScrolledWindow(child=sidebar_box, vexpand=True)
        sidebar_toolbar = Adw.ToolbarView()
        sidebar_toolbar.add_top_bar(Adw.HeaderBar(title_widget=Adw.WindowTitle(title="Hyprland Settings")))
        sidebar_toolbar.set_content(sidebar_scroller)
        sidebar_page = Adw.NavigationPage(title="Hyprland Settings", child=sidebar_toolbar)
        self.split_view.set_sidebar(sidebar_page)

        self.toast_overlay = Adw.ToastOverlay()
        self.ctx.toast_overlay = self.toast_overlay
        self._page_cache: dict[int, Gtk.Widget] = {}
        self.content_nav_page = Adw.NavigationPage(title=NAV_ITEMS[0]["title"], child=self.toast_overlay)
        self.split_view.set_content(self.content_nav_page)

        def on_row_selected(_box, row):
            if row is None:
                return
            index = row.get_index()
            # Selectable rows only - separators are not selectable, but still
            # occupy an index, so map ListBoxRow -> NAV_ITEMS by walking
            # only the rows we actually built as items.
            item = self._item_for_row(sidebar_box, row)
            if item is None:
                return
            if index not in self._page_cache:
                self._page_cache[index] = _wrap_page(item["title"], item["builder"](self.ctx))
            self.toast_overlay.set_child(self._page_cache[index])
            self.content_nav_page.set_title(item["title"])
            self.split_view.set_show_content(True)

        sidebar_box.connect("row-selected", on_row_selected)
        sidebar_box.select_row(sidebar_box.get_row_at_index(0))

        if banner:
            root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            root_box.append(banner)
            root_box.append(self.split_view)
            root_box.set_vexpand(True)
            self.set_content(root_box)
        else:
            self.set_content(self.split_view)

    def _item_for_row(self, listbox: Gtk.ListBox, target_row: Gtk.ListBoxRow):
        item_index = -1
        i = 0
        while True:
            row = listbox.get_row_at_index(i)
            if row is None:
                break
            if row.get_selectable():
                item_index += 1
                if row is target_row:
                    return NAV_ITEMS[item_index]
            i += 1
        return None


class HyprGuiApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.hyprgui.Settings")
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = HyprGuiWindow(self)
        self.window.present()
