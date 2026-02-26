import urwid as uw

from qbittorrentui.events import keybind_context_changed
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
