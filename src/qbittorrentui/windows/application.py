import logging
from time import time

import urwid as uw

from qbittorrentui.config import APPLICATION_NAME, DOWN_TRIANGLE, UP_TRIANGLE, config
from qbittorrentui.connector import ConnectorError, LoginFailed
from qbittorrentui.debug import log_keypress, log_timing
from qbittorrentui.events import (
    exit_tui,
    initialize_torrent_list,
    reset_daemons,
    server_details_changed,
    server_state_changed,
)
from qbittorrentui.formatters import natural_file_size
from qbittorrentui.misc_widgets import ButtonWithoutCursor
from qbittorrentui.windows.torrent_list import TorrentListWindow

logger = logging.getLogger(__name__)


class AppWindow(uw.Frame):
    def __init__(self, main):
        self.main = main

        # build app window
        self.title_bar_w = AppTitleBar()
        self.status_bar_w = AppStatusBar()
        self.torrent_list_w = TorrentListWindow(self.main)

        super().__init__(
            body=self.torrent_list_w,
            header=self.title_bar_w,
            footer=self.status_bar_w,
            focus_part="body",
        )

    def keypress(self, size, key):
        log_keypress(logger, self, key)
        if key in ["n", "N"]:
            self.main.loop.widget = uw.Overlay(
                top_w=uw.LineBox(ConnectDialog(self.main)),
                bottom_w=self.main.loop.widget,
                align=uw.CENTER,
                width=(uw.RELATIVE, 50),
                valign=uw.MIDDLE,
                height=(uw.RELATIVE, 50),
            )
        elif key in ["c", "C"]:
            self.main.loop.widget = uw.Overlay(
                top_w=uw.LineBox(ConfigManagerDialog(self.main)),
                bottom_w=self.main.loop.widget,
                align=uw.CENTER,
                width=(uw.RELATIVE, 70),
                valign=uw.MIDDLE,
                height=(uw.RELATIVE, 80),
            )
        return super().keypress(size, key)


class AppTitleBar(uw.Text):
    def __init__(self):
        """Application title bar."""
        super().__init__(
            markup=APPLICATION_NAME, align=uw.CENTER, wrap=uw.CLIP, layout=None
        )
        self.refresh("title bar init")
        server_details_changed.connect(receiver=self.refresh)

    def refresh(self, sender, details: dict = None):
        start_time = time()

        div_ch = " | "
        server_version_str = ""
        hostname_str = ""
        title = ""

        if details is None:
            details = {}

        if ver := details.get("server_version", ""):
            server_version_str = ver

        hostname = config.get("HOST")
        port = config.get("PORT")
        hostname_str = (
            f"{hostname if hostname else ''}{f':{port}' if hostname and port else ''}"
        )

        if server_version_str:
            title = server_version_str
        if APPLICATION_NAME:
            title = title + (div_ch if title else "") + APPLICATION_NAME
        if hostname_str:
            title = title + (div_ch if title else "") + hostname_str

        self.set_text(title)

        assert log_timing(logger, "Updating", self, sender, start_time)


class AppStatusBar(uw.Columns):
    def __init__(self):

        self.left_column = uw.Text("", align=uw.LEFT, wrap=uw.CLIP)
        self.right_column = uw.Padding(uw.Text("", align=uw.RIGHT, wrap=uw.CLIP))

        column_w_list = [(uw.PACK, self.left_column), (uw.WEIGHT, 1, self.right_column)]
        super().__init__(
            widget_list=column_w_list,
            dividechars=1,
            focus_column=None,
            min_width=1,
            box_columns=None,
        )
        self.refresh("status bar init")
        server_state_changed.connect(receiver=self.refresh)

    def selectable(self):
        return False

    def refresh(self, sender, server_state: dict = None):
        start_time = time()

        if server_state is None:
            server_state = dict()

        """ Right column => <dl rate>⯆ [<dl limit>] (<dl size>) <up rate>⯅ [<up limit>] (<up size>) """
        # note: have to use unicode codes to avoid chars with too many bytes...urwid doesn't handle those well
        # <dl rate>⯆
        dl_up_text = f"{natural_file_size(server_state.get('dl_info_speed', 0), gnu=True).rjust(6)}/s{DOWN_TRIANGLE}"
        # [<dl limit>]
        if server_state.get("dl_rate_limit", None):
            dl_up_text = f"{dl_up_text} [{natural_file_size(server_state.get('dl_rate_limit', 0), gnu=True)}/s]"
        # (<dl size>)
        dl_up_text = f"{dl_up_text} ({natural_file_size(server_state.get('dl_info_data', 0), gnu=True)})"
        # <up rate>⯅
        dl_up_text = f"{dl_up_text} {natural_file_size(server_state.get('up_info_speed', 0), gnu=True).rjust(6)}/s{UP_TRIANGLE}"  # noqa: E501
        # [<up limit>]
        if server_state.get("up_rate_limit", None):
            dl_up_text = f"{dl_up_text} [{natural_file_size(server_state.get('up_rate_limit', 0), gnu=True)}/s]"
        # (<up size>)
        dl_up_text = f"{dl_up_text} ({natural_file_size(server_state.get('up_info_data', 0), gnu=True)})"
        """Left column => DHT: # Status: <status>"""
        dht_and_status = ""
        if server_state.get("dht_nodes", None):
            dht_and_status = f"DHT: {server_state.get('dht_nodes', None)} "
        dht_and_status = f"{dht_and_status}Status: {server_state.get('connection_status', 'disconnected')}"

        self.left_column.base_widget.set_text(dht_and_status)
        self.right_column.base_widget.set_text(dl_up_text)

        assert log_timing(logger, "Updating", self, sender, start_time)


class ConnectDialog(uw.ListBox):
    def __init__(self, main, error_message: str = "", support_auto_connect=False):
        self.main = main
        self.client = main.torrent_client

        self.button_group = list()
        self.attempt_auto_connect = False
        for section in config.keys():
            if section != "DEFAULT":
                # if CONNECT_AUTOMATICALLY is set to anything other than
                # 0 or FALSE/false/False, automatically connecting is enabled
                settings_auto_connect = config.get(
                    section=section, option="CONNECT_AUTOMATICALLY"
                )
                is_auto_connect = bool(
                    settings_auto_connect
                    and not settings_auto_connect.upper() == "FALSE"
                    and not settings_auto_connect == "0"
                )
                if (
                    support_auto_connect
                    and is_auto_connect
                    and not self.attempt_auto_connect
                ):
                    uw.RadioButton(self.button_group, section, state=True)
                    self.attempt_auto_connect = True
                else:
                    uw.RadioButton(self.button_group, section, state=False)

        self.error_w = uw.Text(f"{error_message}", align=uw.CENTER)
        self.hostname_w = uw.Edit(" Hostname: ", edit_text="")
        self.port_w = uw.Edit(" Port: ")
        self.username_w = uw.Edit(" Username: ")
        self.password_w = uw.Edit(" Password: ", mask="*")
        self.save_profile_w = uw.CheckBox(" Save this connection profile", state=True)

        walker_list = [
            uw.Text("Enter connection information", align=uw.CENTER),
            uw.Divider(),
            uw.AttrMap(self.error_w, "light red on default"),
            uw.Divider(),
        ]
        walker_list.extend(self.button_group)
        walker_list.extend(
            [
                uw.Divider(),
                uw.Text("Manual connection:"),
                self.hostname_w,
                self.port_w,
                self.username_w,
                self.password_w,
                self.save_profile_w,
                uw.Divider(),
                uw.Columns(
                    [
                        uw.Padding(uw.Text("")),
                        (
                            6,
                            uw.AttrMap(
                                ButtonWithoutCursor("OK", on_press=self.apply_settings),
                                "",
                                focus_map="selected",
                            ),
                        ),
                        (
                            10,
                            uw.AttrMap(
                                ButtonWithoutCursor(
                                    "Cancel", on_press=self.close_dialog
                                ),
                                "",
                                focus_map="selected",
                            ),
                        ),
                        uw.Padding(uw.Text("")),
                    ],
                    dividechars=3,
                ),
                uw.Divider(),
                uw.Divider(),
            ]
        )

        super().__init__(uw.SimpleFocusListWalker(walker_list))

        if self.attempt_auto_connect:
            self.main.loop.set_alarm_in(0.001, callback=self.auto_connect)

    def auto_connect(self, loop, _):
        if self.attempt_auto_connect:
            self.apply_settings()

    def keypress(self, size, key):
        log_keypress(logger, self, key)
        key = super().keypress(size, {"shift tab": "up", "tab": "down"}.get(key, key))
        if key in ["esc"]:
            self.close_dialog()
        return key

    def close_dialog(self, *a):
        if self.main.torrent_client.is_connected and hasattr(
            self.main.loop.widget, "bottom_w"
        ):
            self.main.loop.widget = self.main.loop.widget.bottom_w
        else:
            self.leave_app()

    @staticmethod
    def leave_app(_=None):
        exit_tui.send("connect dialog")

    def apply_settings(self, _=None):
        host = "<unknown>"
        port = ""
        try:
            section = "DEFAULT"
            # attempt manual connection
            host = self.hostname_w.get_edit_text()
            port = self.port_w.get_edit_text()
            user = self.username_w.get_edit_text()
            password = self.password_w.get_edit_text()
            if host:
                self.client.connect(
                    host=host,
                    port=port if port else None,
                    username=user,
                    password=password,
                )
                # if successful, save off manual connection information
                config.set(section=section, option="HOST", value=host)
                config.set(section=section, option="PORT", value=port)
                config.set(section=section, option="USERNAME", value=user)
                config.set(section=section, option="PASSWORD", value=password)
                # save to disk if checkbox is checked
                if self.save_profile_w.get_state():
                    config.save_manual_connection(
                        host=host, port=port, username=user, password=password
                    )
            else:
                # find selected pre-defined connection
                for b in self.button_group:
                    if b.get_state():
                        section = b.label
                        break
                # attempt pre-defined connection
                host = config.get(section=section, option="HOST")
                port = config.get(section=section, option="PORT")
                user = config.get(section=section, option="USERNAME")
                password = config.get(section=section, option="PASSWORD")
                self.client.connect(
                    host=f"{host}{f':{port}' if port else ''}",
                    username=user,
                    password=password,
                    verify_certificate=not bool(
                        config.get("DO_NOT_VERIFY_WEBUI_CERTIFICATE")
                    ),
                )

            config.set_default_section(section)
            # switch to torrent list window
            reset_daemons.send("connect dialog")
            self.main.app_window.body = self.main.app_window.torrent_list_w
            self.main.loop.widget = self.main.app_window
            initialize_torrent_list.send("connect dialog")
        except LoginFailed:
            self.error_w.set_text(
                f"Error: login failed for {host}{f':{port}' if port else ''}"
            )
        except ConnectorError as e:
            self.error_w.set_text("Error: %s" % e)


class ConfigManagerDialog(uw.ListBox):
    """Dialog for managing configuration profiles in-app."""

    def __init__(self, main):
        self.main = main
        self.section_widgets = {}
        self.new_profile_widgets = {}
        self.import_path_w = None
        self.status_w = uw.Text("", align=uw.CENTER)

        walker_list = self._build_walker_list()
        super().__init__(uw.SimpleFocusListWalker(walker_list))

    def _build_walker_list(self):
        walker_list = [
            uw.Text("Configuration Manager", align=uw.CENTER),
            uw.Divider(),
        ]

        # status line showing config file path
        config_path_str = (
            str(config.config_path) if config.config_path else "No config file loaded"
        )
        walker_list.append(uw.Text(f" Config file: {config_path_str}"))
        walker_list.append(uw.Divider())
        walker_list.append(uw.AttrMap(self.status_w, "light red on default"))
        walker_list.append(uw.Divider())

        # existing profiles
        sections = config.sections()
        if sections:
            walker_list.append(
                uw.AttrMap(uw.Text(" Existing Profiles", align=uw.LEFT), "reversed")
            )
            walker_list.append(uw.Divider())
            for section in sections:
                walker_list.append(uw.Text(f" [{section}]"))
                host_w = uw.Edit("  HOST: ", config.get(section=section, option="HOST"))
                port_w = uw.Edit("  PORT: ", config.get(section=section, option="PORT"))
                user_w = uw.Edit(
                    "  USERNAME: ", config.get(section=section, option="USERNAME")
                )
                pass_w = uw.Edit(
                    "  PASSWORD: ",
                    config.get(section=section, option="PASSWORD"),
                    mask="*",
                )
                auto_connect_val = config.get(
                    section=section, option="CONNECT_AUTOMATICALLY"
                )
                auto_w = uw.CheckBox(
                    "  Auto-connect",
                    state=bool(
                        auto_connect_val
                        and auto_connect_val.upper() != "FALSE"
                        and auto_connect_val != "0"
                    ),
                )
                self.section_widgets[section] = {
                    "host": host_w,
                    "port": port_w,
                    "username": user_w,
                    "password": pass_w,
                    "auto_connect": auto_w,
                }
                walker_list.extend(
                    [host_w, port_w, user_w, pass_w, auto_w, uw.Divider()]
                )
        else:
            walker_list.append(uw.Text(" No profiles configured."))
            walker_list.append(uw.Divider())

        # add new profile
        walker_list.append(
            uw.AttrMap(uw.Text(" Add New Profile", align=uw.LEFT), "reversed")
        )
        walker_list.append(uw.Divider())
        name_w = uw.Edit("  Profile name: ")
        host_w = uw.Edit("  HOST: ")
        port_w = uw.Edit("  PORT: ")
        user_w = uw.Edit("  USERNAME: ")
        pass_w = uw.Edit("  PASSWORD: ", mask="*")
        auto_w = uw.CheckBox("  Auto-connect", state=False)
        self.new_profile_widgets = {
            "name": name_w,
            "host": host_w,
            "port": port_w,
            "username": user_w,
            "password": pass_w,
            "auto_connect": auto_w,
        }
        walker_list.extend(
            [name_w, host_w, port_w, user_w, pass_w, auto_w, uw.Divider()]
        )

        # import section
        walker_list.append(
            uw.AttrMap(uw.Text(" Import Config", align=uw.LEFT), "reversed")
        )
        walker_list.append(uw.Divider())
        self.import_path_w = uw.Edit("  File path: ")
        walker_list.append(self.import_path_w)
        walker_list.append(
            uw.Columns(
                [
                    uw.Padding(uw.Text("")),
                    (
                        10,
                        uw.AttrMap(
                            ButtonWithoutCursor("Import", on_press=self.do_import),
                            "",
                            focus_map="selected",
                        ),
                    ),
                    uw.Padding(uw.Text("")),
                ],
                dividechars=2,
            )
        )
        walker_list.append(uw.Divider())

        # action buttons
        walker_list.append(
            uw.Columns(
                [
                    uw.Padding(uw.Text("")),
                    (
                        8,
                        uw.AttrMap(
                            ButtonWithoutCursor("Save", on_press=self.do_save),
                            "",
                            focus_map="selected",
                        ),
                    ),
                    (
                        16,
                        uw.AttrMap(
                            ButtonWithoutCursor("Clear Config", on_press=self.do_clear),
                            "",
                            focus_map="selected",
                        ),
                    ),
                    (
                        10,
                        uw.AttrMap(
                            ButtonWithoutCursor("Cancel", on_press=self.close_dialog),
                            "",
                            focus_map="selected",
                        ),
                    ),
                    uw.Padding(uw.Text("")),
                ],
                dividechars=2,
            )
        )
        walker_list.extend([uw.Divider(), uw.Divider()])

        return walker_list

    def keypress(self, size, key):
        log_keypress(logger, self, key)
        key = super().keypress(size, {"shift tab": "up", "tab": "down"}.get(key, key))
        if key in ["esc"]:
            self.close_dialog()
        return key

    def close_dialog(self, *a):
        if hasattr(self.main.loop.widget, "bottom_w"):
            self.main.loop.widget = self.main.loop.widget.bottom_w

    def do_save(self, *a):
        """Read all edit widgets, update config sections, and write to disk."""
        # update existing profiles
        for section, widgets in self.section_widgets.items():
            config.set(
                section=section, option="HOST", value=widgets["host"].get_edit_text()
            )
            config.set(
                section=section, option="PORT", value=widgets["port"].get_edit_text()
            )
            config.set(
                section=section,
                option="USERNAME",
                value=widgets["username"].get_edit_text(),
            )
            config.set(
                section=section,
                option="PASSWORD",
                value=widgets["password"].get_edit_text(),
            )
            config.set(
                section=section,
                option="CONNECT_AUTOMATICALLY",
                value="1" if widgets["auto_connect"].get_state() else "0",
            )

        # add new profile if name and host are provided
        new_name = self.new_profile_widgets["name"].get_edit_text().strip()
        new_host = self.new_profile_widgets["host"].get_edit_text().strip()
        if new_name and new_host:
            if not config.has_section(new_name):
                config.add_section(new_name)
            config.set(section=new_name, option="HOST", value=new_host)
            config.set(
                section=new_name,
                option="PORT",
                value=self.new_profile_widgets["port"].get_edit_text(),
            )
            config.set(
                section=new_name,
                option="USERNAME",
                value=self.new_profile_widgets["username"].get_edit_text(),
            )
            config.set(
                section=new_name,
                option="PASSWORD",
                value=self.new_profile_widgets["password"].get_edit_text(),
            )
            config.set(
                section=new_name,
                option="CONNECT_AUTOMATICALLY",
                value=(
                    "1" if self.new_profile_widgets["auto_connect"].get_state() else "0"
                ),
            )

        config.write_to_disk()
        self.status_w.set_text(f"Saved to {config.config_path}")

    def do_clear(self, *a):
        """Show confirmation before clearing config."""
        self.main.loop.widget = uw.Overlay(
            top_w=uw.LineBox(
                uw.ListBox(
                    uw.SimpleFocusListWalker(
                        [
                            uw.Divider(),
                            uw.Text(
                                "Are you sure you want to clear all config?",
                                align=uw.CENTER,
                            ),
                            uw.Divider(),
                            uw.Columns(
                                [
                                    uw.Padding(uw.Text("")),
                                    (
                                        6,
                                        uw.AttrMap(
                                            ButtonWithoutCursor(
                                                "OK", on_press=self.confirm_clear
                                            ),
                                            "",
                                            focus_map="selected",
                                        ),
                                    ),
                                    (
                                        10,
                                        uw.AttrMap(
                                            ButtonWithoutCursor(
                                                "Cancel",
                                                on_press=self.cancel_clear,
                                            ),
                                            "",
                                            focus_map="selected",
                                        ),
                                    ),
                                    uw.Padding(uw.Text("")),
                                ],
                                dividechars=2,
                            ),
                        ]
                    )
                )
            ),
            bottom_w=self.main.loop.widget,
            align=uw.CENTER,
            valign=uw.MIDDLE,
            width=50,
            height=10,
        )

    def confirm_clear(self, *a):
        config.clear_config()
        # pop confirmation overlay back to the config manager's parent
        if hasattr(self.main.loop.widget, "bottom_w"):
            # bottom_w is the config manager overlay; pop that too
            outer = self.main.loop.widget.bottom_w
            if hasattr(outer, "bottom_w"):
                self.main.loop.widget = outer.bottom_w
            else:
                self.main.loop.widget = outer

    def cancel_clear(self, *a):
        # pop just the confirmation overlay
        if hasattr(self.main.loop.widget, "bottom_w"):
            self.main.loop.widget = self.main.loop.widget.bottom_w

    def do_import(self, *a):
        """Import an external config file and merge into current config."""
        import_path = self.import_path_w.get_edit_text().strip()
        if not import_path:
            self.status_w.set_text("Error: no file path provided")
            return
        try:
            config.import_config(import_path)
            self.status_w.set_text(
                f"Imported from {import_path} - press Save to write to disk"
            )
        except Exception as e:
            self.status_w.set_text(f"Import error: {e}")
