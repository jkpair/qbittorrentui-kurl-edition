"""Theme engine for qBittorrenTUI.

Provides built-in color themes and custom theme loading from INI files.

Each theme entry is a 5-tuple: (fg_16, bg_16, mono, fg_256, bg_256).
The 16-color values are fallbacks for terminals without 256-color support.
The 256-color values use #RGB hex codes from the 6x6x6 color cube, which
are NOT remapped by terminal color schemes — making themes look consistent
regardless of the user's terminal palette.
"""

import configparser
import logging

from qbittorrentui.config import XDG_CONFIG_DIR

logger = logging.getLogger(__name__)

# Semantic palette entry names used across the app
PALETTE_ENTRIES = [
    "selected",
    "reversed",
    "pg normal",
    "pg complete",
    "light red on default",
    "dark blue on default",
    "dark cyan on default",
    "dark green on default",
    "dark magenta on default",
    "dirmark",
    "title bar",
    "status bar",
    "keybind bar",
    "keybind key",
    "column header",
]

# Each theme maps palette name -> (fg_16, bg_16, mono, fg_256, bg_256)
# fg_16/bg_16: named colors for 16-color fallback
# fg_256/bg_256: #RGB hex codes for 256-color mode (terminal-independent)
BUILTIN_THEMES = {
    "default": {
        "selected": ("white,bold", "dark blue", "standout", "#fff,bold", "#009"),
        "reversed": ("standout", "", "", "standout", ""),
        "pg normal": ("white", "", "", "#fff", ""),
        "pg complete": ("white", "dark blue", "", "#fff", "#009"),
        "light red on default": ("light red", "", "", "#f66", ""),
        "dark blue on default": ("dark blue", "", "", "#08d", ""),
        "dark cyan on default": ("dark cyan", "", "", "#0ad", ""),
        "dark green on default": ("dark green", "", "", "#0b0", ""),
        "dark magenta on default": ("dark magenta", "", "", "#a0d", ""),
        "dirmark": ("dark green,bold", "", "bold", "#0b0,bold", ""),
        "title bar": ("white,bold", "dark blue", "standout", "#fff,bold", "#009"),
        "status bar": ("", "", "", "", ""),
        "keybind bar": ("light gray", "dark gray", "", "#bbb", "#333"),
        "keybind key": ("white,bold", "dark gray", "bold", "#fff,bold", "#333"),
        "column header": ("white,bold", "dark blue", "standout", "#fff,bold", "#009"),
    },
    "solarized-dark": {
        "selected": ("white,bold", "dark cyan", "standout", "#eee,bold", "#024"),
        "reversed": ("standout", "", "", "standout", ""),
        "pg normal": ("white", "", "", "#eee", ""),
        "pg complete": ("white", "dark cyan", "", "#eee", "#28d"),
        "light red on default": ("light red", "", "", "#d32", ""),
        "dark blue on default": ("dark blue", "", "", "#28d", ""),
        "dark cyan on default": ("dark cyan", "", "", "#2a9", ""),
        "dark green on default": ("dark green", "", "", "#890", ""),
        "dark magenta on default": ("dark magenta", "", "", "#d38", ""),
        "dirmark": ("dark green,bold", "", "bold", "#890,bold", ""),
        "title bar": ("white,bold", "dark cyan", "standout", "#eee,bold", "#024"),
        "status bar": ("dark cyan", "", "", "#2a9", ""),
        "keybind bar": ("light gray", "dark blue", "", "#9aa", "#012"),
        "keybind key": ("yellow,bold", "dark blue", "bold", "#b80,bold", "#012"),
        "column header": ("white,bold", "dark cyan", "standout", "#eee,bold", "#024"),
    },
    "solarized-light": {
        "selected": ("white,bold", "dark blue", "standout", "#ffe,bold", "#28d"),
        "reversed": ("standout", "", "", "standout", ""),
        "pg normal": ("black", "", "", "#234", ""),
        "pg complete": ("white", "dark blue", "", "#ffe", "#28d"),
        "light red on default": ("dark red", "", "", "#d32", ""),
        "dark blue on default": ("dark blue", "", "", "#28d", ""),
        "dark cyan on default": ("dark cyan", "", "", "#2a9", ""),
        "dark green on default": ("dark green", "", "", "#890", ""),
        "dark magenta on default": ("dark magenta", "", "", "#d38", ""),
        "dirmark": ("dark green,bold", "", "bold", "#890,bold", ""),
        "title bar": ("white,bold", "dark blue", "standout", "#ffe,bold", "#28d"),
        "status bar": ("dark blue", "", "", "#28d", ""),
        "keybind bar": ("dark gray", "light gray", "", "#678", "#eee"),
        "keybind key": ("black,bold", "light gray", "bold", "#234,bold", "#eee"),
        "column header": ("white,bold", "dark blue", "standout", "#ffe,bold", "#28d"),
    },
    "gruvbox": {
        "selected": ("white,bold", "dark red", "standout", "#edb,bold", "#800"),
        "reversed": ("standout", "", "", "standout", ""),
        "pg normal": ("white", "", "", "#edb", ""),
        "pg complete": ("black,bold", "dark green", "", "#221,bold", "#991"),
        "light red on default": ("light red", "", "", "#f44", ""),
        "dark blue on default": ("dark blue", "", "", "#458", ""),
        "dark cyan on default": ("dark cyan", "", "", "#6a6", ""),
        "dark green on default": ("dark green", "", "", "#991", ""),
        "dark magenta on default": ("dark magenta", "", "", "#b68", ""),
        "dirmark": ("yellow,bold", "", "bold", "#d91,bold", ""),
        "title bar": ("yellow,bold", "dark red", "standout", "#d91,bold", "#800"),
        "status bar": ("yellow", "", "", "#d91", ""),
        "keybind bar": ("light gray", "dark red", "", "#edb", "#400"),
        "keybind key": ("yellow,bold", "dark red", "bold", "#d91,bold", "#400"),
        "column header": ("yellow,bold", "dark red", "standout", "#d91,bold", "#800"),
    },
    "dracula": {
        "selected": ("white,bold", "dark magenta", "standout", "#fff,bold", "#529"),
        "reversed": ("standout", "", "", "standout", ""),
        "pg normal": ("white", "", "", "#fff", ""),
        "pg complete": ("black,bold", "dark magenta", "", "#214,bold", "#b9f"),
        "light red on default": ("light red", "", "", "#f55", ""),
        "dark blue on default": ("light blue", "", "", "#8ef", ""),
        "dark cyan on default": ("dark cyan", "", "", "#8ef", ""),
        "dark green on default": ("dark green", "", "", "#5f7", ""),
        "dark magenta on default": ("light magenta", "", "", "#f7c", ""),
        "dirmark": ("dark cyan,bold", "", "bold", "#8ef,bold", ""),
        "title bar": ("white,bold", "dark magenta", "standout", "#fff,bold", "#529"),
        "status bar": ("dark cyan", "", "", "#8ef", ""),
        "keybind bar": ("light gray", "dark magenta", "", "#ccc", "#418"),
        "keybind key": ("white,bold", "dark magenta", "bold", "#fff,bold", "#418"),
        "column header": (
            "white,bold",
            "dark magenta",
            "standout",
            "#fff,bold",
            "#529",
        ),
    },
    "nord": {
        "selected": ("white,bold", "dark blue", "standout", "#eef,bold", "#348"),
        "reversed": ("standout", "", "", "standout", ""),
        "pg normal": ("white", "", "", "#eef", ""),
        "pg complete": ("white", "dark blue", "", "#eef", "#58a"),
        "light red on default": ("light red", "", "", "#b66", ""),
        "dark blue on default": ("light blue", "", "", "#58a", ""),
        "dark cyan on default": ("dark cyan", "", "", "#8cd", ""),
        "dark green on default": ("dark green", "", "", "#ab8", ""),
        "dark magenta on default": ("dark magenta", "", "", "#b68", ""),
        "dirmark": ("dark cyan,bold", "", "bold", "#8cd,bold", ""),
        "title bar": ("white,bold", "dark blue", "standout", "#eef,bold", "#348"),
        "status bar": ("dark cyan", "", "", "#8cd", ""),
        "keybind bar": ("white", "dark blue", "", "#dde", "#236"),
        "keybind key": ("white,bold", "dark blue", "bold", "#eef,bold", "#236"),
        "column header": ("white,bold", "dark blue", "standout", "#eef,bold", "#348"),
    },
    "monokai": {
        "selected": ("white,bold", "dark green", "standout", "#fff,bold", "#460"),
        "reversed": ("standout", "", "", "standout", ""),
        "pg normal": ("white", "", "", "#fff", ""),
        "pg complete": ("black,bold", "dark green", "", "#221,bold", "#ae2"),
        "light red on default": ("light red", "", "", "#f27", ""),
        "dark blue on default": ("light blue", "", "", "#6de", ""),
        "dark cyan on default": ("dark cyan", "", "", "#6de", ""),
        "dark green on default": ("dark green", "", "", "#ae2", ""),
        "dark magenta on default": ("light magenta", "", "", "#a8f", ""),
        "dirmark": ("dark green,bold", "", "bold", "#ae2,bold", ""),
        "title bar": ("white,bold", "dark green", "standout", "#fff,bold", "#460"),
        "status bar": ("dark green", "", "", "#ae2", ""),
        "keybind bar": ("light gray", "dark green", "", "#ccc", "#340"),
        "keybind key": ("yellow,bold", "dark green", "bold", "#ed7,bold", "#340"),
        "column header": ("white,bold", "dark green", "standout", "#fff,bold", "#460"),
    },
    "everforest": {
        "selected": ("white,bold", "dark green", "standout", "#dca,bold", "#354"),
        "reversed": ("standout", "", "", "standout", ""),
        "pg normal": ("white", "", "", "#dca", ""),
        "pg complete": ("black,bold", "dark green", "", "#232,bold", "#8c9"),
        "light red on default": ("light red", "", "", "#e78", ""),
        "dark blue on default": ("dark cyan", "", "", "#7bb", ""),
        "dark cyan on default": ("dark cyan", "", "", "#8c9", ""),
        "dark green on default": ("dark green", "", "", "#ac8", ""),
        "dark magenta on default": ("dark magenta", "", "", "#d9b", ""),
        "dirmark": ("dark green,bold", "", "bold", "#ac8,bold", ""),
        "title bar": ("white,bold", "dark green", "standout", "#dca,bold", "#354"),
        "status bar": ("dark green", "", "", "#ac8", ""),
        "keybind bar": ("light gray", "dark green", "", "#dca", "#243"),
        "keybind key": ("white,bold", "dark green", "bold", "#dca,bold", "#243"),
        "column header": ("white,bold", "dark green", "standout", "#dca,bold", "#354"),
    },
}


def get_custom_themes_dir():
    """Return the directory for custom theme INI files."""
    return XDG_CONFIG_DIR / "qbittorrentui" / "themes"


def get_theme(name):
    """Return a theme dict by name, falling back to 'default'.

    Checks built-in themes first, then custom themes directory.
    """
    if name in BUILTIN_THEMES:
        return BUILTIN_THEMES[name]

    # check custom themes directory
    themes_dir = get_custom_themes_dir()
    theme_file = themes_dir / f"{name}.ini"
    if theme_file.exists():
        try:
            return load_custom_theme(str(theme_file))
        except Exception:
            logger.warning("Failed to load custom theme '%s', using default", name)

    return BUILTIN_THEMES["default"]


def theme_to_palette(theme):
    """Convert a theme dict to a list of urwid palette tuples.

    Supports both 3-tuple (fg, bg, mono) and 5-tuple
    (fg_16, bg_16, mono, fg_256, bg_256) theme entries.
    When 256-color values are present, generates 6-element urwid palette
    tuples so urwid uses the hex colors from the 256-color cube.
    """
    palette = []
    for entry_name in PALETTE_ENTRIES:
        if entry_name in theme:
            entry = theme[entry_name]
            if len(entry) == 5:
                fg, bg, mono, fg_256, bg_256 = entry
                palette.append((entry_name, fg, bg, mono, fg_256, bg_256))
            else:
                fg, bg, mono = entry
                palette.append((entry_name, fg, bg, mono))

    # legacy palette entries that some widgets still reference
    legacy = [
        ("body", "black", "light gray", "standout"),
        ("header", "white", "dark red", "bold"),
        ("screen edge", "light blue", "dark cyan"),
        ("main shadow", "dark gray", "black"),
        ("line", "black", "light gray", "standout"),
        ("bg background", "light gray", "black"),
        ("bg 1", "black", "dark blue", "standout"),
        ("bg 1 smooth", "dark blue", "black"),
        ("bg 2", "black", "dark cyan", "standout"),
        ("bg 2 smooth", "dark cyan", "black"),
        ("button normal", "light gray", "dark blue", "standout"),
        ("button select", "white", "dark green"),
        ("pg smooth", "", ""),
    ]
    palette.extend(legacy)

    return palette


def load_custom_theme(path):
    """Read a custom theme INI file and return a theme dict.

    Custom theme INI format::

        [meta]
        name = my-theme

        [selected]
        foreground = white,bold
        background = dark blue
        mono = standout
        foreground_256 = #fff,bold
        background_256 = #009

    If foreground_256/background_256 are provided, the entry becomes a
    5-tuple for terminal-independent colors. Otherwise it's a 3-tuple
    using named ANSI colors.
    """
    parser = configparser.ConfigParser()
    parser.read(path)

    theme = {}
    default = BUILTIN_THEMES["default"]

    for entry_name in PALETTE_ENTRIES:
        if parser.has_section(entry_name):
            fg = parser.get(entry_name, "foreground", fallback="")
            bg = parser.get(entry_name, "background", fallback="")
            mono = parser.get(entry_name, "mono", fallback="")
            fg_256 = parser.get(entry_name, "foreground_256", fallback=None)
            bg_256 = parser.get(entry_name, "background_256", fallback=None)
            if fg_256 is not None or bg_256 is not None:
                theme[entry_name] = (
                    fg,
                    bg,
                    mono,
                    fg_256 if fg_256 is not None else "",
                    bg_256 if bg_256 is not None else "",
                )
            else:
                theme[entry_name] = (fg, bg, mono)
        elif entry_name in default:
            theme[entry_name] = default[entry_name]

    return theme


def list_available_themes():
    """Return sorted list of all available theme names (built-in + custom)."""
    names = set(BUILTIN_THEMES.keys())

    themes_dir = get_custom_themes_dir()
    if themes_dir.exists():
        for f in themes_dir.glob("*.ini"):
            names.add(f.stem)

    return sorted(names)
