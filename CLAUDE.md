# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QBittorrenTUI - Kurl Edition is a Python terminal UI (TUI) application for managing qBittorrent, built with urwid. It is a fork of [qBittorrenTUI](https://github.com/rmartin16/qbittorrentui) with additional features. It connects to a qBittorrent Web UI and provides a console-based interface for monitoring and controlling torrents.

## Build & Development Commands

```bash
# Install in development mode
pip install -e ".[dev]"

# Build package
tox -e package

# Run pre-commit hooks (isort, black, flake8, pyupgrade, docformatter)
pre-commit run --all-files

# Run the application
qbittorrentui
qbittorrentui --config_file /path/to/config.ini
```

## Architecture

### Entry Point
`src/qbittorrentui/__main__.py` → parses CLI args → calls `run()` in `main.py` which creates the `Main` class orchestrating everything.

### Core Components

- **`main.py`** — `Main` class: sets up urwid screen, manages startup sequence (splash → connection dialog → app). Also contains `TorrentServer` which maintains local state (torrents, categories, server state) and triggers UI updates.
- **`connector.py`** — `Connector` class: wraps `qbittorrent-api` Client for all API calls (connect, list/pause/resume torrents, etc.).
- **`daemon.py`** — `DaemonManager`: runs background threads (`SyncMainData`, `SyncTorrent`, `ServerDetails`, `Commands`) that poll the qBittorrent API and push updates via pipe file descriptors to the urwid event loop.
- **`events.py`** — blinker signal definitions used throughout for decoupled communication (e.g., `connection_to_server_acquired`, `server_torrents_changed`, `exit_tui`).

### UI Layer (`windows/`)

- **`application.py`** — `AppWindow` (main frame with title/status bars), `ConnectDialog` (connection form with auto-connect support)
- **`torrent_list.py`** — `TorrentListWindow`: filterable torrent list with category tabs (All, Downloading, Completed, etc.), uses panwid for advanced column layout
- **`torrent.py`** — `TorrentWindow`: individual torrent detail view with tabs (General, Trackers, Peers, Content)

### Data Flow

1. Background daemon threads poll qBittorrent API at configurable intervals
2. Daemon signals UI thread via pipe file descriptor (urwid watch_pipe)
3. `TorrentServer` processes updates and fires blinker signals
4. UI widgets listen to signals and update display

### Key Dependencies

| Package | Purpose |
|---------|---------|
| urwid 3.0.3 | Terminal UI framework |
| qbittorrent-api | qBittorrent WebAPI client |
| blinker 1.9.0 | Event/signal system |
| panwid 0.3.5 | Advanced urwid widgets (data tables) |

## Code Style

- **black** formatting, **isort** with black profile
- **flake8** with max line length 127
- **pyupgrade** targeting py38+
- Requires Python >= 3.10
- Pre-commit hooks enforce all of the above

## Configuration

The app uses INI config files (`default.ini` has defaults). Each section is a connection profile with host, port, credentials, and UI settings like progress bar length and polling interval.
