import configparser
import os
from os import path as os_path
from pathlib import Path

XDG_CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
DEFAULT_CONFIG_PATH = XDG_CONFIG_DIR / "qbittorrentui" / "qbtui.conf"


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

    def write_to_disk(self, path=None):
        """Write non-DEFAULT sections to disk.

        Uses a fresh ConfigParser to avoid writing DEFAULT values into each
        section on disk.
        """
        target = Path(path) if path else self.config_path
        if target is None:
            target = DEFAULT_CONFIG_PATH
        target.parent.mkdir(parents=True, exist_ok=True)

        writer = configparser.ConfigParser()
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


# CONSTANTS
APPLICATION_NAME = "qBittorrenTUI"
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
