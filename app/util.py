from gi.repository import GLib


def escape(text) -> str:
    """Adw row title/subtitle properties are Pango markup, unlike a plain
    Gtk.Label - any user- or compositor-supplied text placed there must be
    escaped or a stray '&'/'<' crashes markup parsing (GTK-WARNING, and the
    row silently fails to show its text)."""
    return GLib.markup_escape_text(str(text))
