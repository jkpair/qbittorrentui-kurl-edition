import configparser
import os
from os import path as os_path
from pathlib import Path

XDG_CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
DEFAULT_CONFIG_PATH = XDG_CONFIG_DIR / "qbittorrentui" / "qbtui.conf"
RSS_CONFIG_PATH = XDG_CONFIG_DIR / "qbittorrentui" / "rss.conf"


class Configuration(configparser.ConfigParser):
    def __init__(self):
        super().__init__()
        # load default configuration
        self.read(os_path.join(os_path.split(__file__)[0], "default.ini"))
        self._section = "DEFAULT"
        self.config_path = None

    def set_default_section(self, section: str = ""):
        self._section = section

    def get(self, option: str, section: str = None):
        if section:
            return super().get(section=section, option=option, raw=True)
        return super().get(section=self._section, option=option, raw=True)

    def set(self, option: str, value: str, section: str = None):
        if section:
            super().set(section=section, option=option, value=value)
        else:
            super().set(section=self._section, option=option, value=value)

    def load_file(self, path):
        """Read a config file and track its path for write-back."""
        self.read(path)
        self.config_path = Path(path)

    # Options stored at the DEFAULT level that should be persisted
    _global_options = ("theme", "default_torrent_dir")

    def write_to_disk(self, path=None):
        """Write config sections and global options to disk.

        Uses a fresh ConfigParser to avoid writing DEFAULT values into each
        section on disk.  Global options (like THEME) that live in the
        DEFAULT section are written explicitly so they survive restarts.
        """
        target = Path(path) if path else self.config_path
        if target is None:
            target = DEFAULT_CONFIG_PATH
        target.parent.mkdir(parents=True, exist_ok=True)

        writer = configparser.ConfigParser()

        # persist global DEFAULT-level options
        for option in self._global_options:
            if option in self._defaults:
                writer.set(configparser.DEFAULTSECT, option, self._defaults[option])

        for section in self.sections():
            writer.add_section(section)
            for option in self.options(section):
                # only write options that were explicitly set in this section
                if option in self._sections.get(section, {}):
                    writer.set(
                        section, option, self.get(section=section, option=option)
                    )

        with open(target, "w") as f:
            writer.write(f)

        self.config_path = target

    def save_manual_connection(self, host, port, username, password, section_name=None):
        """Create/update a named section and write to disk."""
        if section_name is None:
            section_name = f"{host}:{port}" if port else host

        if not self.has_section(section_name):
            self.add_section(section_name)

        self.set(section=section_name, option="HOST", value=host)
        self.set(section=section_name, option="PORT", value=port)
        self.set(section=section_name, option="USERNAME", value=username)
        self.set(section=section_name, option="PASSWORD", value=password)

        if self.config_path is None:
            self.config_path = DEFAULT_CONFIG_PATH

        self.write_to_disk()

    def clear_config(self):
        """Remove all non-DEFAULT sections and delete the config file."""
        for section in self.sections():
            self.remove_section(section)

        if self.config_path and self.config_path.exists():
            self.config_path.unlink()

    def import_config(self, path):
        """Read an external INI file and merge its sections into the current config.

        Does NOT write to disk; caller must call write_to_disk().
        """
        external = configparser.ConfigParser()
        external.read(path)
        for section in external.sections():
            if not self.has_section(section):
                self.add_section(section)
            for option in external.options(section):
                if option in external._sections.get(section, {}):
                    self.set(
                        section=section,
                        option=option,
                        value=external.get(section=section, option=option, raw=True),
                    )


class RSSConfiguration:
    """Manages per-feed RSS settings stored in an INI config file."""

    _KEYS = ("url", "auto_download_pattern", "category", "save_path", "refresh_interval")

    def __init__(self):
        self._parser = configparser.ConfigParser()

    def load(self):
        if RSS_CONFIG_PATH.exists():
            self._parser.read(RSS_CONFIG_PATH)

    def save(self):
        RSS_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(RSS_CONFIG_PATH, "w") as f:
            self._parser.write(f)

    def get_feed(self, name):
        result = {}
        for key in self._KEYS:
            result[key] = self._parser.get(name, key, fallback="")
        return result

    def set_feed(self, name, **kwargs):
        if not self._parser.has_section(name):
            self._parser.add_section(name)
        for key in self._KEYS:
            if key in kwargs:
                self._parser.set(name, key, kwargs[key])

    def remove_feed(self, name):
        self._parser.remove_section(name)
        self.save()

    def feeds(self):
        return self._parser.sections()


# CONSTANTS
APPLICATION_NAME = "QBittorrenTUI - Kurl Edition"
# when a count of seconds should just be represented as infinity
SECS_INFINITY = 100 * 24 * 60 * 60  # 100 days
INFINITY = "\u221e"  # ∞
DOWN_TRIANGLE = "\u25bc"  # ▼
UP_TRIANGLE = "\u25b2"  # ▲
UP_ARROW = "\u21d1"  # ⇑
STATE_MAP_FOR_DISPLAY = {
    "pausedUP": "Completed",
    "stoppedUP": "Completed",
    "uploading": "Seeding",
    "stalledUP": "Seeding",
    "forcedUP": "[F] Seeding",
    "queuedDL": "Queued",
    "queuedUP": "Queued",
    "pausedDL": "Paused",
    "stoppedDL": "Paused",
    "checkingDL": "Checking",
    "checkingUP": "Checking",
    "downloading": "Downloading",
    "forcedDL": "[F] Downloading",
    "forcedMetaDL": "[F] Metadata DL",
    "metaDL": "Metadata DL",
    "stalledDL": "Stalled",
    "allocating": "Allocating",
    "moving": "Moving",
    "missingfiles": "Missing Files",
    "error": "Error",
    "queuedForChecking": "Queued for Checking",
    "checkingResumeData": "Checking Resume Data",
}
TORRENT_LIST_FILTERING_STATE_MAP = {
    "downloading": [
        "downloading",
        "forcedMetaDL",
        "metaDL",
        "queuedDL",
        "stalledDL",
        "pausedDL",
        "stoppedDL",
        "forcedDL",
    ],
    "completed": [
        "uploading",
        "stalledUP",
        "checkingUP",
        "pausedUP",
        "stoppedUP",
        "queuedUP",
        "forcedUP",
    ],
    "active": [
        "metaDL",
        "forcedMetaDL",
        "downloading",
        "forcedDL",
        "uploading",
        "forcedUP",
        "moving",
    ],
    "inactive": [
        "pausedUP",
        "stoppedUP",
        "stalledUP",
        "stalledDL",
        "queuedDL",
        "queuedUP",
        "pausedDL",
        "stoppedDL",
        "checkingDL",
        "checkingUP",
        "allocating",
        "missingfiles",
        "error",
        "queuedForChecking",
        "checkingResumeData",
    ],
    "paused": [
        "pausedUP",
        "stoppedUP",
        "queuedDL",
        "queuedUP",
        "pausedDL",
        "stoppedDL",
        "missingfiles",
        "error",
        "queuedForChecking",
        "checkingResumeData",
    ],
    "resumed": [
        "uploading",
        "stalledUP",
        "forcedUP",
        "checkingDL",
        "checkingUP",
        "downloading",
        "forcedDL",
        "metaDL",
        "forcedMetaDL",
        "stalledDL",
        "allocating",
        "moving",
    ],
}

# CONFIGURATION STORE
config = Configuration()
rss_config = RSSConfiguration()
