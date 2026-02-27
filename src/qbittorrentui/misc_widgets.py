import os
from pathlib import Path

import urwid as uw

from qbittorrentui.events import FILE_BROWSER_HINTS, keybind_context_changed
from qbittorrentui.formatters import natural_file_size


class ButtonWithoutCursor(uw.Button):
    button_left = "["
    button_right = "]"

    def __init__(self, label, on_press=None, user_data=None):
        self._label = ButtonWithoutCursor.ButtonLabel("")
        cols = uw.Columns(
            [
                ("fixed", len(self.button_left), uw.Text(self.button_left)),
                self._label,
                ("fixed", len(self.button_right), uw.Text(self.button_right)),
            ],
            dividechars=1,
        )
        super(uw.Button, self).__init__(cols)

        if on_press:
            uw.connect_signal(self, "click", on_press, user_data)

        self.set_label(label)

    class ButtonLabel(uw.SelectableIcon):
        def set_text(self, label):
            super().set_text(label)
            self._cursor_position = len(label) + 1


class DownloadProgressBar(uw.ProgressBar):
    def __init__(self, normal, complete, current=0, done=100, satt=None):
        if done == 0:
            done = 100
        super().__init__(
            normal=normal, complete=complete, current=current, done=done, satt=satt
        )

    def get_text(self):
        size = natural_file_size(self.current, gnu=True).rjust(7)
        percent = (" (" + self.get_percentage() + ")").ljust(6)
        return size + percent

    def get_percentage(self):
        try:
            percent = str(int(self.current * 100 / self.done))
        except ZeroDivisionError:
            percent = "unk"

        return (percent + "%") if percent != "unk" else percent


class KeybindHintBar(uw.Text):
    """Context-sensitive keybind hint bar displayed in the application footer."""

    def __init__(self):
        super().__init__("", wrap=uw.CLIP)
        keybind_context_changed.connect(receiver=self.update_hints)

    def update_hints(self, sender, hints=None):
        """Update displayed keybind hints.

        :param sender: signal sender
        :param hints: list of (key_str, description) tuples
        """
        if not hints:
            self.set_text("")
            return

        # auto-append Help hint
        all_hints = list(hints) + [("?", "Help")]

        markup = []
        for i, (key_str, description) in enumerate(all_hints):
            if i > 0:
                markup.append("  ")
            markup.append(("keybind key", f" {key_str} "))
            markup.append(f":{description}")
        self.set_text(markup)

    def selectable(self):
        return False


class SelectableText(uw.Text):
    _selectable = True

    @staticmethod
    def keypress(_, key):
        return key


class _SelectableRow(uw.WidgetDecoration):
    """Thin wrapper that stores name/is_dir metadata on a selectable row."""

    def __init__(self, original_widget, name, is_dir):
        super().__init__(original_widget)
        self.name = name
        self.is_dir = is_dir

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key

    def rows(self, size, focus=False):
        return self._original_widget.rows(size, focus)

    def render(self, size, focus=False):
        return self._original_widget.render(size, focus)


class FileBrowserDialog(uw.Pile):
    """Flat-list file browser for selecting .torrent files with path autocomplete."""

    def __init__(self, main, on_select, start_dir=None):
        self.main = main
        self._on_select = on_select
        self._updating = False

        if start_dir and Path(start_dir).is_dir():
            self._cwd = Path(start_dir)
        else:
            self._cwd = Path.home()

        self._path_edit = uw.Edit(caption="Path: ")
        self._walker = uw.SimpleFocusListWalker([])
        self._listbox = uw.ListBox(self._walker)

        self._populate()

        uw.connect_signal(self._path_edit, "postchange", self._on_path_changed)

        super().__init__(
            [
                ("pack", uw.AttrMap(self._path_edit, "bold")),
                ("pack", uw.Divider("\u2500")),
                ("weight", 1, self._listbox),
            ]
        )
        # focus starts on path edit (index 0)
        self.focus_position = 0

        keybind_context_changed.send(self, hints=FILE_BROWSER_HINTS)

    def _populate(self, update_edit=True, name_filter=""):
        if update_edit:
            self._updating = True
            edit_text = str(self._cwd) + "/"
            self._path_edit.set_edit_text(edit_text)
            self._path_edit.set_edit_pos(len(edit_text))
            self._updating = False

        self._walker.clear()

        # ".." entry unless at root (hide when filtering)
        if self._cwd != self._cwd.parent and not name_filter:
            self._walker.append(self._make_row("..", is_dir=True))

        try:
            entries = sorted(self._cwd.iterdir(), key=lambda p: p.name.lower())
        except PermissionError:
            entries = []

        dirs = [e for e in entries if e.is_dir() and not e.name.startswith(".")]
        files = [e for e in entries if e.is_file() and e.suffix.lower() == ".torrent"]

        if name_filter:
            nf = name_filter.lower()
            dirs = [e for e in dirs if e.name.lower().startswith(nf)]
            files = [e for e in files if e.name.lower().startswith(nf)]

        for d in dirs:
            self._walker.append(self._make_row(d.name + "/", is_dir=True))
        for f in files:
            size_str = natural_file_size(f.stat().st_size, gnu=True)
            self._walker.append(
                self._make_row(f"{f.name}  ({size_str})", is_dir=False, raw_name=f.name)
            )

        if self._walker:
            self._walker.set_focus(0)

    def _on_path_changed(self, widget, old_text):
        if self._updating:
            return
        text = self._path_edit.get_edit_text()
        p = Path(text)
        if text.endswith("/") and p.is_dir() and p != self._cwd:
            self._cwd = p
            self._populate(update_edit=False)
        elif not text.endswith("/") and p.parent.is_dir():
            if p.parent != self._cwd:
                self._cwd = p.parent
            self._populate(update_edit=False, name_filter=p.name)

    def _tab_complete(self):
        text = self._path_edit.get_edit_text()
        p = Path(text)

        # If text already points to a valid dir, complete within it
        if p.is_dir() and text.endswith("/"):
            parent_dir = p
            partial = ""
        else:
            parent_dir = p.parent
            partial = p.name

        if not parent_dir.is_dir():
            return

        try:
            candidates = []
            for entry in parent_dir.iterdir():
                if entry.name.startswith(".") and not partial.startswith("."):
                    continue
                if entry.name.lower().startswith(partial.lower()):
                    if entry.is_dir() or entry.suffix.lower() == ".torrent":
                        candidates.append(entry)
        except PermissionError:
            return

        if not candidates:
            return

        if len(candidates) == 1:
            match = candidates[0]
            if match.is_dir():
                completed = str(match) + "/"
                self._cwd = match
                self._updating = True
                self._path_edit.set_edit_text(completed)
                self._path_edit.set_edit_pos(len(completed))
                self._updating = False
                self._populate(update_edit=False)
            else:
                completed = str(match)
                self._updating = True
                self._path_edit.set_edit_text(completed)
                self._path_edit.set_edit_pos(len(completed))
                self._updating = False
        else:
            # bash-style: complete to longest common prefix
            names = [c.name for c in candidates]
            prefix = os.path.commonprefix(names)
            if len(prefix) > len(partial):
                completed = str(parent_dir / prefix)
                self._updating = True
                self._path_edit.set_edit_text(completed)
                self._path_edit.set_edit_pos(len(completed))
                self._updating = False

    def _make_row(self, label, is_dir, raw_name=None):
        name = raw_name if raw_name else label.rstrip("/")
        row = _SelectableRow(uw.Text(label), name=name, is_dir=is_dir)
        return uw.AttrMap(row, "", focus_map="selected")

    def _enter(self, name, is_dir):
        if is_dir:
            if name == "..":
                self._cwd = self._cwd.parent
            else:
                self._cwd = self._cwd / name
            self._populate()
        else:
            path = str(self._cwd / name)
            self._close()
            self._on_select(path)

    def _enter_from_path_edit(self):
        text = self._path_edit.get_edit_text()
        p = Path(text)
        if p.is_file() and p.suffix.lower() == ".torrent":
            self._close()
            self._on_select(str(p))
        elif p.is_dir() and p != self._cwd:
            self._cwd = p
            self._populate()

    def _close(self):
        self.main.loop.widget = self.main.loop.widget.bottom_w

    def keypress(self, size, key):
        if key == "esc":
            self._close()
            return None
        if key == "tab":
            self._tab_complete()
            return None
        # Check if focus is on the path edit (index 0)
        if key == "enter" and self.focus_position == 0:
            self._enter_from_path_edit()
            return None
        key = super().keypress(size, key)
        if key == "enter":
            focus_w = self._walker.get_focus()[0]
            if focus_w is not None:
                row = focus_w.original_widget
                self._enter(row.name, row.is_dir)
            return None
        return key
