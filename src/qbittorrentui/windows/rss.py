import logging

import urwid as uw

from qbittorrentui.config import rss_config
from qbittorrentui.debug import log_keypress
from qbittorrentui.events import (
    DIALOG_HINTS,
    RSS_WINDOW_HINTS,
    TORRENT_LIST_HINTS,
    keybind_context_changed,
    rss_data_changed,
    update_rss_now,
)
from qbittorrentui.misc_widgets import ButtonWithoutCursor

logger = logging.getLogger(__name__)


def _parse_category(description):
    """Parse category from RSS article description (e.g. '953 MB; TV/Web-DL' -> 'TV/Web-DL')."""
    if not description:
        return ""
    parts = description.split(";")
    if len(parts) >= 2:
        return parts[1].strip()
    return ""


def _match_query(query, title):
    """Match title against advanced query syntax.

    Commas separate OR groups, + separates AND terms within a group.
    Example: 'dub, sub, dual' matches if title contains 'dub' OR 'sub' OR 'dual'
    Example: '1080p + dual' matches if title contains BOTH '1080p' AND 'dual'
    Example: '1080p + dub, 720p + sub' matches (1080p AND dub) OR (720p AND sub)
    """
    if not query:
        return True
    title_lower = title.lower()
    or_groups = query.split(",")
    for group in or_groups:
        and_terms = [t.strip().lower() for t in group.split("+")]
        and_terms = [t for t in and_terms if t]
        if not and_terms:
            continue
        if all(term in title_lower for term in and_terms):
            return True
    return False


class RSSWindow(uw.Frame):
    """Main RSS browsing window with feed sidebar and article list."""

    def __init__(self, main):
        self.main = main
        self.client = main.torrent_client

        self._rss_data = {}
        self._selected_feed = None
        self._search_text = ""
        self._selected_category = None
        self._categories = []
        self._auto_downloaded = set()

        rss_config.load()

        self.feed_list_w = RSSFeedList(self)
        self.article_list_w = RSSArticleList(self)

        body = uw.Columns(
            [
                (25, uw.AttrMap(self.feed_list_w, "background")),
                (1, uw.SolidFill("\u2502")),
                uw.AttrMap(self.article_list_w, "background"),
            ],
            focus_column=2,
        )

        self._header_text = uw.Text("RSS Feeds", align=uw.CENTER)
        self._category_bar = uw.Text("", align=uw.CENTER)
        header = uw.Pile(
            [
                uw.AttrMap(self._header_text, "reversed"),
                uw.AttrMap(self._category_bar, "bold"),
            ]
        )

        super().__init__(
            body=body,
            header=header,
            focus_part="body",
        )

        rss_data_changed.connect(receiver=self.on_rss_data)
        keybind_context_changed.send(self, hints=RSS_WINDOW_HINTS)
        update_rss_now.send("rss_window_init")

    def on_rss_data(self, sender, rss_data=None):
        if rss_data is not None:
            self._rss_data = rss_data
            self._update_categories()
            self.feed_list_w.refresh(rss_data)
            self._refresh_articles()
            self._process_auto_downloads(rss_data)

    def _update_categories(self):
        """Auto-detect unique categories from loaded RSS data."""
        cats = set()
        for feed_name, feed_data in self._rss_data.items():
            if not isinstance(feed_data, dict):
                continue
            for article in feed_data.get("articles", []):
                if not isinstance(article, dict):
                    continue
                cat = _parse_category(article.get("description", ""))
                if cat:
                    cats.add(cat)
        self._categories = sorted(cats)
        # If selected category no longer exists in data, reset it
        if self._selected_category and self._selected_category not in self._categories:
            self._selected_category = None
        self._update_category_bar()

    def _update_category_bar(self):
        if not self._categories:
            self._category_bar.set_text("")
            return
        parts = []
        label = "All"
        if self._selected_category is None:
            label = "[All]"
        parts.append(label)
        for cat in self._categories:
            if cat == self._selected_category:
                parts.append(f"[{cat}]")
            else:
                parts.append(cat)
        self._category_bar.set_text("  ".join(parts))

    def _refresh_articles(self):
        articles = self._collect_articles()
        self.article_list_w.refresh(articles)

    def _collect_articles(self):
        articles = []
        for feed_name, feed_data in self._rss_data.items():
            if not isinstance(feed_data, dict):
                continue
            feed_articles = feed_data.get("articles", [])
            for article in feed_articles:
                if not isinstance(article, dict):
                    continue
                if self._selected_feed and feed_name != self._selected_feed:
                    continue
                title = article.get("title", "")
                if self._search_text and not _match_query(self._search_text, title):
                    continue
                description = article.get("description", "")
                category = _parse_category(description)
                if self._selected_category and category != self._selected_category:
                    continue
                articles.append(
                    {
                        "title": title,
                        "date": article.get("date", ""),
                        "torrentURL": article.get("torrentURL", ""),
                        "link": article.get("link", ""),
                        "feed_name": feed_name,
                        "category": category,
                    }
                )
        return articles

    def select_feed(self, feed_name):
        self._selected_feed = feed_name
        self._update_header()
        self._refresh_articles()

    def _update_header(self):
        parts = ["RSS Feeds"]
        if self._selected_feed:
            parts.append(f"Feed: {self._selected_feed}")
        if self._search_text:
            parts.append(f'Search: "{self._search_text}"')
        self._header_text.set_text(" | ".join(parts))

    def _on_search_submit(self, query):
        self._search_text = query
        self._update_header()
        self._refresh_articles()

    def _show_search_dialog(self):
        dialog = RSSSearchDialog(self, self._search_text)
        self.main.loop.widget = uw.Overlay(
            top_w=uw.AttrMap(uw.LineBox(dialog, title="Search RSS"), "background"),
            bottom_w=self.main.loop.widget,
            align=uw.CENTER,
            width=(uw.RELATIVE, 60),
            valign=uw.MIDDLE,
            height=12,
        )
        keybind_context_changed.send(self, hints=DIALOG_HINTS)

    def _show_add_feed_dialog(self):
        dialog = RSSFeedEditDialog(self, config_dialog=None, name=None)
        self.main.loop.widget = uw.Overlay(
            top_w=uw.AttrMap(
                uw.LineBox(dialog, title="Add RSS Feed"), "background"
            ),
            bottom_w=self.main.loop.widget,
            align=uw.CENTER,
            width=(uw.RELATIVE, 60),
            valign=uw.MIDDLE,
            height=20,
        )
        keybind_context_changed.send(self, hints=DIALOG_HINTS)

    def _delete_feed(self):
        feed_name = self.feed_list_w.get_selected_feed()
        if feed_name is None:
            return
        dialog = RSSDeleteFeedDialog(self, feed_name)
        self.main.loop.widget = uw.Overlay(
            top_w=uw.AttrMap(uw.LineBox(dialog), "background"),
            bottom_w=self.main.loop.widget,
            align=uw.CENTER,
            valign=uw.MIDDLE,
            width=50,
            height=8,
        )

    def _refresh_feeds(self):
        feed_name = self.feed_list_w.get_selected_feed()
        if feed_name:
            self.client.rss_refresh_item(item_path=feed_name)
        update_rss_now.send("rss_refresh")

    def _download_article(self, article):
        url = article.get("torrentURL", "") or article.get("link", "")
        if not url:
            return
        feed_name = article.get("feed_name", "")
        feed_settings = rss_config.get_feed(feed_name) if feed_name else {}
        kwargs = {"urls": url}
        if feed_settings.get("category"):
            kwargs["category"] = feed_settings["category"]
        if feed_settings.get("save_path"):
            kwargs["save_path"] = feed_settings["save_path"]
        self.client.torrents_add(**kwargs)

    def _process_auto_downloads(self, rss_data):
        for feed_name in rss_config.feeds():
            settings = rss_config.get_feed(feed_name)
            pattern = settings.get("auto_download_pattern", "")
            if not pattern:
                continue
            feed_data = rss_data.get(feed_name)
            if not isinstance(feed_data, dict):
                continue
            for article in feed_data.get("articles", []):
                if not isinstance(article, dict):
                    continue
                title = article.get("title", "")
                key = (feed_name, title)
                if key in self._auto_downloaded:
                    continue
                if _match_query(pattern, title):
                    self._auto_downloaded.add(key)
                    url = article.get("torrentURL", "") or article.get("link", "")
                    if url:
                        kwargs = {"urls": url}
                        if settings.get("category"):
                            kwargs["category"] = settings["category"]
                        if settings.get("save_path"):
                            kwargs["save_path"] = settings["save_path"]
                        self.client.torrents_add(**kwargs)

    def _show_config_dialog(self):
        dialog = RSSConfigDialog(self)
        self.main.loop.widget = uw.Overlay(
            top_w=uw.AttrMap(uw.LineBox(dialog, title="RSS Feed Config"), "background"),
            bottom_w=self.main.loop.widget,
            align=uw.CENTER,
            width=(uw.RELATIVE, 70),
            valign=uw.MIDDLE,
            height=(uw.RELATIVE, 70),
        )
        keybind_context_changed.send(self, hints=DIALOG_HINTS)

    def _cycle_category(self):
        """Cycle through categories: All -> cat1 -> cat2 -> ... -> All."""
        if not self._categories:
            return
        if self._selected_category is None:
            self._selected_category = self._categories[0]
        else:
            try:
                idx = self._categories.index(self._selected_category)
                if idx + 1 < len(self._categories):
                    self._selected_category = self._categories[idx + 1]
                else:
                    self._selected_category = None
            except ValueError:
                self._selected_category = None
        self._update_category_bar()
        self._refresh_articles()

    def _close(self):
        rss_data_changed.disconnect(receiver=self.on_rss_data)
        self.main.app_window.body = uw.AttrMap(
            self.main.app_window.torrent_list_w, "background"
        )
        keybind_context_changed.send(self, hints=TORRENT_LIST_HINTS)

    def keypress(self, size, key):
        log_keypress(logger, self, key)

        if key == "esc":
            self._close()
            return None
        if key == "/":
            self._show_search_dialog()
            return None
        if key in ("a", "A"):
            self._show_add_feed_dialog()
            return None
        if key in ("d", "D"):
            self._delete_feed()
            return None
        if key in ("c", "C"):
            self._show_config_dialog()
            return None
        if key in ("r", "R"):
            self._refresh_feeds()
            return None
        if key in ("t", "T"):
            self._cycle_category()
            return None
        if key in ("f",):
            # focus feed list sidebar
            self.body.focus_position = 0
            return None
        if key in ("F",):
            # clear feed filter and category filter
            self._selected_feed = None
            self._selected_category = None
            self._update_header()
            self._update_category_bar()
            self._refresh_articles()
            return None

        return super().keypress(size, key)


class RSSSearchDialog(uw.ListBox):
    """Popup dialog for searching RSS articles with advanced query syntax."""

    def __init__(self, rss_window, initial_query=""):
        self.rss_window = rss_window

        self.query_w = uw.Edit("  Query: ", edit_text=initial_query)

        walker_list = [
            uw.Divider(),
            self.query_w,
            uw.Divider(),
            uw.Text(
                [
                    "  Syntax:  ",
                    ("bold", "term1, term2"),
                    " = OR  |  ",
                    ("bold", "term1 + term2"),
                    " = AND",
                ],
            ),
            uw.Text("  Example: 1080p + dub, 720p + sub"),
            uw.Divider(),
            uw.Columns(
                [
                    uw.Padding(uw.Text("")),
                    (
                        10,
                        uw.AttrMap(
                            ButtonWithoutCursor("Search", on_press=self._submit),
                            "",
                            focus_map="selected",
                        ),
                    ),
                    (
                        9,
                        uw.AttrMap(
                            ButtonWithoutCursor("Clear", on_press=self._clear),
                            "",
                            focus_map="selected",
                        ),
                    ),
                    (
                        10,
                        uw.AttrMap(
                            ButtonWithoutCursor("Cancel", on_press=self._close),
                            "",
                            focus_map="selected",
                        ),
                    ),
                    uw.Padding(uw.Text("")),
                ],
                dividechars=1,
            ),
        ]

        super().__init__(uw.SimpleFocusListWalker(walker_list))

    def _submit(self, *a):
        query = self.query_w.get_edit_text().strip()
        self.rss_window._on_search_submit(query)
        self._dismiss()

    def _clear(self, *a):
        self.rss_window._on_search_submit("")
        self._dismiss()

    def _close(self, *a):
        self._dismiss()

    def _dismiss(self):
        if hasattr(self.rss_window.main.loop.widget, "bottom_w"):
            self.rss_window.main.loop.widget = self.rss_window.main.loop.widget.bottom_w
        keybind_context_changed.send(self, hints=RSS_WINDOW_HINTS)

    def keypress(self, size, key):
        log_keypress(logger, self, key)
        if key == "enter":
            self._submit()
            return None
        key = super().keypress(size, {"shift tab": "up", "tab": "down"}.get(key, key))
        if key == "esc":
            self._dismiss()
            return None
        return key


class RSSFeedList(uw.ListBox):
    """Left sidebar showing all configured RSS feeds."""

    def __init__(self, rss_window):
        self.rss_window = rss_window
        self._walker = uw.SimpleFocusListWalker([])
        self._feed_names = []
        super().__init__(self._walker)

    def refresh(self, rss_data):
        # remember which feed was selected so we can restore it
        prev_selected = self.get_selected_feed()

        self._walker.clear()
        self._feed_names = []

        # "All Feeds" entry
        all_btn = _SelectableFeedRow("All Feeds")
        self._walker.append(uw.AttrMap(all_btn, "", focus_map="selected"))
        self._feed_names.append(None)

        restore_idx = 0
        for feed_name in sorted(rss_data.keys()):
            if not isinstance(rss_data[feed_name], dict):
                continue
            row = _SelectableFeedRow(feed_name)
            self._walker.append(uw.AttrMap(row, "", focus_map="selected"))
            self._feed_names.append(feed_name)
            if feed_name == prev_selected:
                restore_idx = len(self._feed_names) - 1

        if self._walker:
            self._walker.set_focus(restore_idx)

    def get_selected_feed(self):
        focus_w, focus_pos = self._walker.get_focus()
        if focus_pos is None:
            return None
        if focus_pos < len(self._feed_names):
            return self._feed_names[focus_pos]
        return None

    def keypress(self, size, key):
        key = super().keypress(size, key)
        if key == "enter":
            feed = self.get_selected_feed()
            self.rss_window.select_feed(feed)
            return None
        return key


class _SelectableFeedRow(uw.Text):
    _selectable = True

    @staticmethod
    def keypress(_, key):
        return key


class RSSArticleList(uw.ListBox):
    """Main content area showing RSS articles."""

    def __init__(self, rss_window):
        self.rss_window = rss_window
        self._walker = uw.SimpleFocusListWalker([])
        self._articles = []
        super().__init__(self._walker)

    def refresh(self, articles):
        self._walker.clear()
        self._articles = articles

        if not articles:
            self._walker.append(uw.Text("No articles found.", align=uw.CENTER))
            return

        for article in articles:
            row = RSSArticleRow(article)
            self._walker.append(uw.AttrMap(row, "", focus_map="selected"))

        if self._walker:
            self._walker.set_focus(0)

    def keypress(self, size, key):
        key = super().keypress(size, key)
        if key == "enter":
            focus_w, focus_pos = self._walker.get_focus()
            if focus_w is not None and focus_pos < len(self._articles):
                self.rss_window._download_article(self._articles[focus_pos])
            return None
        return key


class RSSArticleRow(uw.Columns):
    """Individual article display row."""

    _selectable = True

    def __init__(self, article):
        self.article = article
        title = article.get("title", "Unknown")
        feed = article.get("feed_name", "")
        category = article.get("category", "")

        cols = [
            uw.Text(title, wrap=uw.CLIP),
            (15, uw.Text(category, wrap=uw.CLIP, align=uw.RIGHT)),
            (20, uw.Text(feed, wrap=uw.CLIP, align=uw.RIGHT)),
        ]
        super().__init__(cols, dividechars=1)

    def keypress(self, size, key):
        return key


class RSSAddFeedDialog(uw.ListBox):
    """Dialog overlay for adding an RSS feed URL."""

    def __init__(self, rss_window):
        self.rss_window = rss_window

        self.url_w = uw.Edit("  URL: ")
        self.name_w = uw.Edit("  Name: ")
        self.error_w = uw.Text("", align=uw.CENTER)

        walker_list = [
            uw.Divider(),
            uw.Text("Add a new RSS feed", align=uw.CENTER),
            uw.Divider(),
            uw.AttrMap(self.error_w, "light red on default"),
            self.url_w,
            self.name_w,
            uw.Divider(),
            uw.Columns(
                [
                    uw.Padding(uw.Text("")),
                    (
                        8,
                        uw.AttrMap(
                            ButtonWithoutCursor("Add", on_press=self._add),
                            "",
                            focus_map="selected",
                        ),
                    ),
                    (
                        10,
                        uw.AttrMap(
                            ButtonWithoutCursor("Cancel", on_press=self._close),
                            "",
                            focus_map="selected",
                        ),
                    ),
                    uw.Padding(uw.Text("")),
                ],
                dividechars=2,
            ),
        ]

        super().__init__(uw.SimpleFocusListWalker(walker_list))

    def _add(self, *a):
        url = self.url_w.get_edit_text().strip()
        if not url:
            self.error_w.set_text("URL is required")
            return
        name = self.name_w.get_edit_text().strip()
        item_path = name if name else ""
        self.rss_window.client.rss_add_feed(url=url, item_path=item_path)
        self._dismiss()
        update_rss_now.send("rss_add_feed")

    def _close(self, *a):
        self._dismiss()

    def _dismiss(self):
        if hasattr(self.rss_window.main.loop.widget, "bottom_w"):
            self.rss_window.main.loop.widget = self.rss_window.main.loop.widget.bottom_w
        keybind_context_changed.send(self, hints=RSS_WINDOW_HINTS)

    def keypress(self, size, key):
        log_keypress(logger, self, key)
        key = super().keypress(size, {"shift tab": "up", "tab": "down"}.get(key, key))
        if key == "esc":
            self._dismiss()
            return None
        return key


class RSSConfigDialog(uw.ListBox):
    """Dialog listing all RSS feeds from rss.conf with add/edit/delete."""

    def __init__(self, rss_window):
        self.rss_window = rss_window
        self._walker = uw.SimpleFocusListWalker([])
        super().__init__(self._walker)
        self._rebuild()

    def _rebuild(self):
        self._walker.clear()
        self._feed_names = []

        self._walker.append(uw.Divider())

        # Merge feeds from API data and local rss_config
        api_feeds = set()
        for feed_name, feed_data in self.rss_window._rss_data.items():
            if isinstance(feed_data, dict):
                api_feeds.add(feed_name)
        config_feeds = set(rss_config.feeds())
        all_feeds = sorted(api_feeds | config_feeds)

        if not all_feeds:
            self._walker.append(uw.Text("  No feeds configured.", align=uw.LEFT))
        else:
            for name in all_feeds:
                settings = rss_config.get_feed(name)
                url = settings.get("url", "")
                label = f"  {name}"
                if url:
                    label += f"  ({url})"
                row = _SelectableFeedRow(label)
                self._walker.append(uw.AttrMap(row, "", focus_map="selected"))
                self._feed_names.append(name)

        self._walker.append(uw.Divider())
        self._walker.append(
            uw.Columns(
                [
                    uw.Padding(uw.Text("")),
                    (
                        12,
                        uw.AttrMap(
                            ButtonWithoutCursor("Add Feed", on_press=self._add),
                            "",
                            focus_map="selected",
                        ),
                    ),
                    (
                        9,
                        uw.AttrMap(
                            ButtonWithoutCursor("Close", on_press=self._close),
                            "",
                            focus_map="selected",
                        ),
                    ),
                    uw.Padding(uw.Text("")),
                ],
                dividechars=2,
            ),
        )

    def _get_selected_feed_name(self):
        focus_w = self._walker.get_focus()[0]
        if focus_w is None:
            return None
        try:
            idx = self._walker.index(focus_w)
        except (ValueError, IndexError):
            return None
        # offset by 1 for the divider at top
        feed_idx = idx - 1
        if 0 <= feed_idx < len(self._feed_names):
            return self._feed_names[feed_idx]
        return None

    def _add(self, *a):
        dialog = RSSFeedEditDialog(self.rss_window, self, name=None)
        self.rss_window.main.loop.widget = uw.Overlay(
            top_w=uw.AttrMap(
                uw.LineBox(dialog, title="Add RSS Feed Config"), "background"
            ),
            bottom_w=self.rss_window.main.loop.widget,
            align=uw.CENTER,
            width=(uw.RELATIVE, 60),
            valign=uw.MIDDLE,
            height=20,
        )

    def _edit_selected(self):
        name = self._get_selected_feed_name()
        if name is None:
            return
        dialog = RSSFeedEditDialog(self.rss_window, self, name=name)
        self.rss_window.main.loop.widget = uw.Overlay(
            top_w=uw.AttrMap(
                uw.LineBox(dialog, title="Edit RSS Feed Config"), "background"
            ),
            bottom_w=self.rss_window.main.loop.widget,
            align=uw.CENTER,
            width=(uw.RELATIVE, 60),
            valign=uw.MIDDLE,
            height=20,
        )

    def _delete_selected(self):
        name = self._get_selected_feed_name()
        if name is None:
            return
        self.rss_window.client.rss_remove_item(item_path=name)
        rss_config.remove_feed(name)
        self._rebuild()
        update_rss_now.send("rss_config_delete")

    def _close(self, *a):
        self._dismiss()

    def _dismiss(self):
        if hasattr(self.rss_window.main.loop.widget, "bottom_w"):
            self.rss_window.main.loop.widget = self.rss_window.main.loop.widget.bottom_w
        keybind_context_changed.send(self, hints=RSS_WINDOW_HINTS)

    def keypress(self, size, key):
        log_keypress(logger, self, key)
        if key == "enter":
            self._edit_selected()
            return None
        if key in ("d", "D"):
            self._delete_selected()
            return None
        key = super().keypress(size, {"shift tab": "up", "tab": "down"}.get(key, key))
        if key == "esc":
            self._dismiss()
            return None
        return key


class RSSFeedEditDialog(uw.ListBox):
    """Form dialog to add or edit per-feed RSS config settings."""

    def __init__(self, rss_window, config_dialog=None, name=None):
        self.rss_window = rss_window
        self.config_dialog = config_dialog
        self._editing = name is not None
        self._standalone = config_dialog is None

        settings = rss_config.get_feed(name) if self._editing else {}

        self.name_w = uw.Edit("  Name: ", edit_text=name or "")
        self.url_w = uw.Edit("  URL: ", edit_text=settings.get("url", ""))
        self.pattern_w = uw.Edit(
            "  Auto-download: ", edit_text=settings.get("auto_download_pattern", "")
        )
        self.category_w = uw.Edit(
            "  Category: ", edit_text=settings.get("category", "")
        )
        self.save_path_w = uw.Edit(
            "  Save path: ", edit_text=settings.get("save_path", "")
        )
        self.refresh_w = uw.Edit(
            "  Refresh (s): ", edit_text=settings.get("refresh_interval", "")
        )
        self.error_w = uw.Text("", align=uw.CENTER)

        walker_list = [
            uw.Divider(),
            uw.AttrMap(self.error_w, "light red on default"),
            self.name_w,
            self.url_w,
            uw.Divider(),
            self.pattern_w,
            uw.Text(
                [
                    "   ",
                    ("bold", "comma"),
                    " = OR  |  ",
                    ("bold", "+"),
                    " = AND    e.g. 1080p + dual, 720p",
                ],
            ),
            uw.Divider(),
            self.category_w,
            self.save_path_w,
            self.refresh_w,
            uw.Divider(),
            uw.Columns(
                [
                    uw.Padding(uw.Text("")),
                    (
                        8,
                        uw.AttrMap(
                            ButtonWithoutCursor("Save", on_press=self._save),
                            "",
                            focus_map="selected",
                        ),
                    ),
                    (
                        10,
                        uw.AttrMap(
                            ButtonWithoutCursor("Cancel", on_press=self._cancel),
                            "",
                            focus_map="selected",
                        ),
                    ),
                    uw.Padding(uw.Text("")),
                ],
                dividechars=2,
            ),
        ]

        super().__init__(uw.SimpleFocusListWalker(walker_list))

    def _save(self, *a):
        name = self.name_w.get_edit_text().strip()
        url = self.url_w.get_edit_text().strip()
        if not name:
            self.error_w.set_text("Name is required")
            return

        if not self._editing and url:
            self.rss_window.client.rss_add_feed(url=url, item_path=name)

        rss_config.set_feed(
            name,
            url=url,
            auto_download_pattern=self.pattern_w.get_edit_text().strip(),
            category=self.category_w.get_edit_text().strip(),
            save_path=self.save_path_w.get_edit_text().strip(),
            refresh_interval=self.refresh_w.get_edit_text().strip(),
        )
        rss_config.save()
        if self.config_dialog is not None:
            self.config_dialog._rebuild()
        self._dismiss()
        if not self._editing:
            update_rss_now.send("rss_config_add")

    def _cancel(self, *a):
        self._dismiss()

    def _dismiss(self):
        if hasattr(self.rss_window.main.loop.widget, "bottom_w"):
            self.rss_window.main.loop.widget = self.rss_window.main.loop.widget.bottom_w
        if self._standalone:
            keybind_context_changed.send(self, hints=RSS_WINDOW_HINTS)

    def keypress(self, size, key):
        log_keypress(logger, self, key)
        key = super().keypress(size, {"shift tab": "up", "tab": "down"}.get(key, key))
        if key == "esc":
            self._dismiss()
            return None
        return key


class RSSDeleteFeedDialog(uw.ListBox):
    """Confirmation dialog for deleting an RSS feed."""

    def __init__(self, rss_window, feed_name):
        self.rss_window = rss_window
        self.feed_name = feed_name

        walker_list = [
            uw.Divider(),
            uw.Text(f'Delete feed "{feed_name}"?', align=uw.CENTER),
            uw.Divider(),
            uw.Columns(
                [
                    uw.Padding(uw.Text("")),
                    (
                        7,
                        uw.AttrMap(
                            ButtonWithoutCursor("Yes", on_press=self._confirm),
                            "",
                            focus_map="selected",
                        ),
                    ),
                    (
                        6,
                        uw.AttrMap(
                            ButtonWithoutCursor("No", on_press=self._cancel),
                            "",
                            focus_map="selected",
                        ),
                    ),
                    uw.Padding(uw.Text("")),
                ],
                dividechars=2,
            ),
        ]
        super().__init__(uw.SimpleFocusListWalker(walker_list))

    def _confirm(self, *a):
        self.rss_window.client.rss_remove_item(item_path=self.feed_name)
        rss_config.remove_feed(self.feed_name)
        self._dismiss()
        update_rss_now.send("rss_delete_feed")

    def _cancel(self, *a):
        self._dismiss()

    def _dismiss(self):
        if hasattr(self.rss_window.main.loop.widget, "bottom_w"):
            self.rss_window.main.loop.widget = self.rss_window.main.loop.widget.bottom_w

    def keypress(self, size, key):
        if key == "esc":
            self._dismiss()
            return None
        key = super().keypress(size, {"shift tab": "up", "tab": "down"}.get(key, key))
        return key
