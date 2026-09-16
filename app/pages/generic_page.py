"""Builds a full Adw.PreferencesPage for one schema section (e.g.
"decoration"), auto-rendering every option Hyprland's own type manifest
declares for it - grouped by the option's sub-table (blur, shadow, ...).
"""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw

from .. import hypr_backend, schema
from ..widgets.rows import build_row, humanize


def build_section_page(ctx, section: str) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()
    options = [o for o in schema.OPTIONS if o["section"] == section]

    groups: dict[str, list[dict]] = {}
    for opt in options:
        groups.setdefault(opt["group"], []).append(opt)

    def group_sort_key(g):
        return (g != "", g)

    for group_name in sorted(groups, key=group_sort_key):
        group_options = sorted(groups[group_name], key=lambda o: o["leaf"])
        title = humanize(group_name) if group_name else humanize(section)
        pref_group = Adw.PreferencesGroup(title=title)
        for opt in group_options:
            current = hypr_backend.get_option(opt["key"])
            row = build_row(
                opt,
                current,
                lambda value, key=opt["key"], kind=opt["widget"]: ctx.set_option(key, kind, value),
            )
            pref_group.add(row)
        page.add(pref_group)

    return page
