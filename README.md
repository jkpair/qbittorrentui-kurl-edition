# QBittorrenTUI - Kurl Edition

[![GitHub release](https://img.shields.io/github/v/release/jkpair/qbittorrentui-kurl-edition?style=flat-square)](https://github.com/jkpair/qbittorrentui-kurl-edition/releases)
![Python Version](https://img.shields.io/badge/python-%3E%3D3.10-blue?style=flat-square)

A terminal UI for managing qBittorrent, built with [urwid](https://urwid.org/). Fork of [qBittorrenTUI](https://github.com/rmartin16/qbittorrentui) with RSS feed support, themes, in-app configuration, and more.

![qbittorrentui screenshot 1](https://i.imgur.com/Uy7DK37.png)

![qbittorrentui screenshot 2](https://i.imgur.com/E6I9q4V.png)

## Features

- **Torrent management** — pause, resume, delete, force resume, add torrents, sort, and filter by status
- **Torrent details** — tabbed view with General, Trackers, Peers, and Content tabs
- **Content browser** — file tree with expand/collapse, priority cycling, and direct file opening
- **RSS feed browser** — browse feeds, search articles, filter by category, add/remove/refresh feeds
- **Theme system** — 7 built-in themes (default, solarized-dark, solarized-light, gruvbox, dracula, nord, monokai) plus custom theme import
- **In-app configuration** — manage connections, settings, default torrent directory, and themes without editing files
- **Context-sensitive keybind hints** — dynamic hint bar at the bottom of the screen, press `?` for full help

## Installation

### pipx (recommended)

[pipx](https://pipx.pypa.io/) installs Python CLI apps in isolated environments. This is the easiest method and works on any Linux distro.

```bash
# Install pipx if you don't have it
# Arch/Manjaro
sudo pacman -S python-pipx

# Ubuntu/Debian
sudo apt install pipx

# Fedora
sudo dnf install pipx

# Or with pip
pip install --user pipx
pipx ensurepath
```

Then install QBittorrenTUI:

```bash
pipx install git+https://github.com/jkpair/qbittorrentui-kurl-edition.git
```

To update to the latest version:

```bash
pipx upgrade qbittorrentui
```

### pip

```bash
pip install git+https://github.com/jkpair/qbittorrentui-kurl-edition.git
```

### From source

```bash
git clone https://github.com/jkpair/qbittorrentui-kurl-edition.git
cd qbittorrentui-kurl-edition
pip install .
```

### Development install

```bash
git clone https://github.com/jkpair/qbittorrentui-kurl-edition.git
cd qbittorrentui-kurl-edition
pip install -e ".[dev]"
```

## Usage

```bash
qbittorrentui
qbittorrentui --config_file /path/to/config.ini
```

## Key Map

A context-sensitive keybind hint bar is displayed at the bottom of the screen. Press `?` at any time to open the full help overlay.

### Any Window
| Key | Action |
|-----|--------|
| `q` | Quit (with confirmation) |
| `n` | Open connection dialog |
| `c` | Open configuration manager |
| `?` | Open help screen |

### Torrent List
| Key | Action |
|-----|--------|
| `p` | Pause focused torrent |
| `r` | Resume focused torrent |
| `d` | Delete focused torrent (with confirmation) |
| `F` | Force resume focused torrent |
| `a` | Open add torrent dialog |
| `s` | Open sort dialog |
| `f` | Open RSS feed browser |
| `Enter` | Open torrent options dialog |
| `Right` | Open torrent details window |
| `Left` / `Right` | Switch status filter tabs |

### Torrent Details
| Key | Action |
|-----|--------|
| `Esc` / `Left` | Return to torrent list |
| `Up` / `Down` | Navigate tabs or content |
| `Right` | Enter content area |

### Content Tab
| Key | Action |
|-----|--------|
| `Enter` | Expand/collapse folder, open file |
| `+` / `-` | Expand / collapse folder |
| `Space` | Cycle file priority |
| `Esc` / `Left` | Return to torrent list |

### RSS Feeds
| Key | Action |
|-----|--------|
| `f` | Focus feed sidebar |
| `F` | Clear feed filter |
| `/` | Search articles by title |
| `t` | Filter by category |
| `a` | Add new RSS feed |
| `d` | Delete selected feed |
| `c` | Configure selected feed |
| `r` | Refresh selected feed |
| `Enter` | Download torrent / select feed |
| `Esc` | Return to torrent list |

### Dialogs
| Key | Action |
|-----|--------|
| `Tab` | Next field |
| `Shift+Tab` | Previous field |
| `Esc` | Close dialog |

## Themes

QBittorrenTUI includes several built-in color themes: `default`, `solarized-dark`, `solarized-light`, `gruvbox`, `dracula`, `nord`, and `monokai`. Change themes via the configuration manager (`c` key) under the Theme section.

Custom themes can be created as INI files and placed in `~/.config/qbittorrentui/themes/` or imported through the config manager.

## Configuration

Connections can be pre-defined in a configuration file and specified with `--config_file`. Each section is a separate connection profile. Connections and settings can also be managed in-app via the configuration manager (`c` key).

Sample configuration file section:
```ini
[localhost:8080]
HOST = localhost
PORT = 8080
USERNAME = admin
PASSWORD = adminadmin
CONNECT_AUTOMATICALLY = 1
THEME = default
```

Only `HOST`, `USERNAME`, and `PASSWORD` are required. Set `DO_NOT_VERIFY_WEBUI_CERTIFICATE = 1` if the certificate is untrusted (e.g. self-signed).

Configuration is stored in `~/.config/qbittorrentui/qbtui.conf`. RSS feed settings are stored in `~/.config/qbittorrentui/rss.conf`.

## Requirements

- Python >= 3.10
- qBittorrent v4.1+ with Web UI enabled

## Kurl Edition Changes

Changes from the [upstream project](https://github.com/rmartin16/qbittorrentui):
- RSS feed browser with search, category filtering, and per-feed configuration
- Content tab: collapsed-by-default directories, folder icons, Enter to expand/collapse, dynamic hints
- Quick-action keybindings (`p`/`r`/`d`/`F`) directly from the torrent list
- `?` help screen overlay listing all keybindings by context
- Quit confirmation dialog
- In-app configuration manager (`c` key) with default torrent directory and live file browser filtering
- Theme system with 7 built-in themes and custom theme import
- Torrent list sorting (`s` key)
- Add torrent dialog
- Context-sensitive keybind hint bar
- Theme-aware backgrounds throughout the UI
