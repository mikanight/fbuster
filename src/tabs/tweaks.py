
import json

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk

from tabs.system76_scheduler import System76SchedulerTweaksSection
from ui.common import load_module
from ui.rows import TaskRow
from ui.widgets import make_scrolled_page, scroll_child_into_view

# Pill badge — removed Sisyphus-specific badges. Only irreversible & experimental remain.
_tweak_page_css = Gtk.CssProvider()
_tweak_page_css.load_from_data(b"""
    .ab-tweak-irreversible-row image,
    .ab-tweak-irreversible-row label {
        color: @error_color;
    }
    .ab-tweak-irreversible-row .dim-label {
        color: @error_color;
        opacity: 1;
    }
    .ab-tweak-experimental-badge {
        font-size: 0.72em;
        font-weight: 600;
        min-height: 0;
        padding: 2px 8px;
        border-radius: 999px;
        color: @error_color;
        background-color: alpha(@error_color, 0.18);
    }
""")

class TweaksPage(Gtk.Box):
    def __init__(self, log_fn):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._log = log_fn

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), _tweak_page_css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        self.set_vexpand(True)
        self._search_focus_widgets: dict[str, Gtk.Widget] = {}

        self._sub_stack = Adw.ViewStack()
        self._sub_stack.set_vexpand(True)

        sub_switcher = Adw.ViewSwitcher()
        sub_switcher.set_stack(self._sub_stack)
        sub_switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        sub_switcher.set_halign(Gtk.Align.CENTER)
        sub_switcher.set_margin_top(10)
        sub_switcher.set_margin_bottom(6)
        sub_switcher.set_margin_start(20)
        sub_switcher.set_margin_end(20)

        self.append(sub_switcher)
        self.append(self._sub_stack)

        scroll_general, body_general = make_scrolled_page()
        self._scroll_general = scroll_general
        self._build_fixes_group(body_general)
        self._sub_stack.add_titled_with_icon(
            scroll_general, "general", "Общие твики", "preferences-system-symbolic",
        )

        scroll_prio, body_prio = make_scrolled_page()
        self._scroll_userspace_priorities = scroll_prio
        self._system76_section = System76SchedulerTweaksSection(self._log, self)
        w_s76 = self._system76_section.append_to(body_prio)
        self._search_focus_widgets["system76_scheduler"] = w_s76
        self._sub_stack.add_titled_with_icon(
            scroll_prio, "userspace_prio", "Планировщик", "system-run-symbolic",
        )

    def focus_row_by_id(self, row_id: str) -> bool:
        w = self._search_focus_widgets.get(row_id)
        if w is None:
            return False
        if row_id == "system76_scheduler":
            self._sub_stack.set_visible_child_name("userspace_prio")
            scroll = self._scroll_userspace_priorities
        else:
            self._sub_stack.set_visible_child_name("general")
            scroll = self._scroll_general
        scroll_child_into_view(scroll, w)
        GLib.idle_add(w.grab_focus)
        return True

    def _add_info_row(
        self,
        group: Adw.PreferencesGroup,
        icon_name: str,
        title: str,
        subtitle: str,
        *,
        error_emphasis: bool = False,
    ) -> Adw.ActionRow:
        row = Adw.ActionRow()
        row.set_title(title)
        row.set_subtitle(subtitle)
        row.set_activatable(False)
        if error_emphasis:
            row.add_css_class("ab-tweak-irreversible-row")
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_valign(Gtk.Align.CENTER)
        row.add_prefix(icon)
        group.add(row)
        return row

    def _build_fixes_group(self, body):
        try:
            data = load_module("maintenance")
            all_tasks = data.get("tasks", [])
        except (OSError, json.JSONDecodeError):
            all_tasks = []

        fix_ids = {"fix_gdm_usb", "fix_gsconnect", "disable_tracker"}
        fix_tasks = [t for t in all_tasks if t["id"] in fix_ids]

        if not fix_tasks:
            return

        group = Adw.PreferencesGroup()
        group.set_title("Различные баги и фиксы")
        body.append(group)

        for task in fix_tasks:
            row = TaskRow(task, self._log, None, btn_label="Применить")
            group.add(row)
