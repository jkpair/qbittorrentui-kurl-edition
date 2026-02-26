QBittorrenTUI - Kurl Edition
============================
[![PyPI](https://img.shields.io/pypi/v/qbittorrentui?style=flat-square)](https://pypi.org/project/qbittorrentui/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/qbittorrentui?style=flat-square)

Console UI for qBittorrent. Fork of [qBittorrenTUI](https://github.com/rmartin16/qbittorrentui) with additional features including quick-action shortcuts, a help screen, theme support, quit confirmation, and in-app configuration management.

![qbittorrentui screenshot 1](https://i.imgur.com/Uy7DK37.png)

![qbittorrentui screenshot 2](https://i.imgur.com/E6I9q4V.png)

Key Map
-------
A context-sensitive keybind hint bar is displayed at the bottom of the screen. Press `?` at any time to open the full help overlay.

### Any Window
* `q` : quit (with confirmation)
* `n` : open connection dialog
* `c` : open configuration manager
* `?` : open help screen

### Torrent List
* `p` : pause focused torrent
* `r` : resume focused torrent
* `d` : delete focused torrent (with confirmation)
* `F` : force resume focused torrent
* `a` : open add torrent dialog
* `s` : open sort dialog
* `Enter` : open torrent options dialog
* `Right` : open torrent details window
* `Left` / `Right` : switch status filter tabs

### Torrent Details
* `Esc` / `Left` : return to torrent list
* `Up` / `Down` : navigate tabs or content
* `Right` : enter content area

### Content Tab
* `Space` : cycle file priority
* `Esc` / `Left` : return to torrent list

### Dialogs
* `Tab` : next field
* `Shift+Tab` : previous field
* `Esc` : close dialog

Themes
------
QBittorrenTUI includes several built-in color themes: `default`, `solarized-dark`, `solarized-light`, `gruvbox`, `dracula`, `nord`, and `monokai`. Change themes via the configuration manager (`c` key) under the Theme section.

Custom themes can be created as INI files and placed in `~/.config/qbittorrentui/themes/` or imported through the config manager. See `src/qbittorrentui/themes.py` for the format.

Installation
------------
Install from source:
```bash
git clone https://github.com/jkpair/qbittorrentui-kurl-edition.git
cd qbittorrentui-kurl-edition
pip install .
```

Or install in development mode:
```bash
pip install -e ".[dev]"
```

In most cases, this should allow you to run the application simply with the `qbittorrentui` command. Alternatively, you can specify a specific python binary with `./venv/bin/python -m qbittorrentui` or similar.

Configuration
-------------
Connections can be pre-defined within a configuration file (modeled after default.ini). Specify the configuration file using --config_file. Each section in the file will be presented as a separate instance to connect to.

Connections and settings can also be managed in-app via the configuration manager (`c` key).

Sample configuration file section:
```
[localhost:8080]
HOST = localhost
PORT = 8080
USERNAME = admin
PASSWORD = adminadmin
CONNECT_AUTOMATICALLY = 1
TIME_AFTER_CONNECTION_FAILURE_THAT_CONNECTION_IS_CONSIDERED_LOST = 5
TORRENT_CONTENT_MAX_FILENAME_LENGTH = 75
TORRENT_LIST_MAX_TORRENT_NAME_LENGTH = 60
TORRENT_LIST_PROGRESS_BAR_LENGTH = 40
DO_NOT_VERIFY_WEBUI_CERTIFICATE = 1
THEME = default
```

Only HOST, USERNAME, AND PASSWORD are required.
DO_NOT_VERIFY_WEBUI_CERTIFICATE is necessary if the certificate is untrusted (e.g. self-signed).

Kurl Edition Changes
--------------------
Changes from the [upstream project](https://github.com/rmartin16/qbittorrentui):
 - Quick-action keybindings (`p`/`r`/`d`/`F`) directly from the torrent list
 - `?` help screen overlay listing all keybindings by context
 - Quit confirmation dialog
 - In-app configuration manager (`c` key)
 - Theme system with 7 built-in themes and custom theme import
 - Torrent list sorting (`s` key)
 - Context-sensitive keybind hint bar with auto-appended `?:Help`
 - Config persistence improvements for global options

TODO/Wishlist
-------------
Application
 - [x] Figure out the theme(s)
 - [x] Configuration for connections
 - [ ] Log/activity output (likely above status bar)
 - [ ] Implement window for editing qBittorrent settings

Torrent List Window
 - [x] Torrent sorting
 - [ ] Additional torrent filtering mechanisms
 - [ ] Torrent searching
 - [ ] Torrent status icon in torrent name
 - [ ] Torrent name color coding
 - [ ] Torrent list column configuration

Torrent Window
 - [ ] Make focus more obvious when switching between tabs list and a display
 - [ ] Scrollbar in the displays
 - [ ] Speed graph display

Torrent Window Content Display
 - [ ] Left key should return to tab list
