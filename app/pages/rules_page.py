"""Window / layer / workspace rules. Match criteria and rule fields are each
edited as simple `key = value` lines (one per line) rather than per-field
widgets, since the set of valid keys is rule-type-specific and documented on
the wiki - this keeps the editor honest about being a thin wrapper rather
than pretending to validate every possible field."""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ..util import escape

RULE_KINDS = [
    ("window_rules", "Window Rules", "https://wiki.hypr.land/Configuring/Basics/Window-Rules/"),
    ("layer_rules", "Layer Rules", "https://wiki.hypr.land/Configuring/Basics/Layer-Rules/"),
    ("workspace_rules", "Workspace Rules", "https://wiki.hypr.land/Configuring/Basics/Workspace-Rules/"),
]


def _kv_to_text(d: dict) -> str:
    return "\n".join(f"{k} = {v}" for k, v in d.items())


def _text_to_kv(text: str) -> dict:
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def build_rules_page(ctx) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()

    for state_key, title, wiki_url in RULE_KINDS:
        group = Adw.PreferencesGroup(title=title, description=f"See {wiki_url}")
        page.add(group)
        rows: list = []

        def rebuild(state_key=state_key, group=group, rows=rows):
            for row in rows:
                group.remove(row)
            rows.clear()

            for idx, rule in enumerate(ctx.state[state_key]):
                expander = Adw.ExpanderRow(title=escape(rule.get("name") or f"Rule {idx + 1}"))

                name_entry = Adw.EntryRow(title="Name", show_apply_button=True)
                name_entry.set_text(rule.get("name", ""))

                def make_name_handler(i=idx, sk=state_key):
                    def handler(r):
                        ctx.state[sk][i]["name"] = r.get_text()
                        ctx.save()
                    return handler

                name_entry.connect("apply", make_name_handler())
                expander.add_row(name_entry)

                for sub_key, sub_title in (("match", "Match (key = value per line)"), ("fields", "Rule Fields (key = value per line)")):
                    text_view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD)
                    text_view.get_buffer().set_text(_kv_to_text(rule.get(sub_key, {})))
                    frame = Gtk.Frame(child=text_view, margin_top=6, margin_bottom=6, margin_start=12, margin_end=12)
                    label = Gtk.Label(label=sub_title, xalign=0, margin_start=12, margin_top=6)
                    label.add_css_class("caption")
                    action_row = Adw.ActionRow()
                    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                    box.append(label)
                    box.append(frame)
                    action_row.set_child(box)
                    expander.add_row(action_row)

                    def make_buffer_handler(i=idx, sk=state_key, subk=sub_key, buf=text_view.get_buffer()):
                        def handler(*_a):
                            text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
                            ctx.state[sk][i][subk] = _text_to_kv(text)
                            ctx.save()
                        return handler

                    text_view.get_buffer().connect("changed", make_buffer_handler())

                delete_btn = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
                delete_btn.add_css_class("flat")

                def make_delete(i=idx, sk=state_key):
                    def handler(_b):
                        del ctx.state[sk][i]
                        ctx.save()
                        rebuild()
                    return handler

                delete_btn.connect("clicked", make_delete())
                expander.add_action(delete_btn)
                group.add(expander)
                rows.append(expander)

            group.add(add_row)
            rows.append(add_row)

        def on_add(*_a, state_key=state_key, rebuild=rebuild):
            ctx.state[state_key].append({"name": "", "match": {}, "fields": {}})
            ctx.save()
            rebuild()

        add_row = Adw.ButtonRow(title=f"Add {title[:-1]}", start_icon_name="list-add-symbolic")
        add_row.connect("activated", on_add)
        rebuild()

    return page
