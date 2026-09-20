"""Add a weekday picker to the schedule task dialogs.

ok-script hardcodes <Monday> in the weekly trigger XML, so every weekly schedule entry fires
on Monday. This patch adds a "Day of Week" combo to the create/modify dialogs and makes the
generated trigger XML use it.

Both the COM and the schtasks creation paths run through WindowsScheduleManager
._get_trigger_xml(), so patching that one method covers every entry point. The dialogs are
modal and only one is open at a time, so the selected weekday is handed over through a
module-level holder instead of widening the existing Qt signals.
"""

from __future__ import annotations

import re
from functools import wraps

from ok import Logger

logger = Logger.get_logger(__name__)

_PATCH_INSTALLED = False

WEEKDAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

_DEFAULT_WEEKDAY = WEEKDAYS[0]
_WEEKLY_TRIGGER_INDEX = 1

# Weekday chosen in the dialog that is currently open.
_selected_weekday = _DEFAULT_WEEKDAY


def set_selected_weekday(weekday: str) -> None:
    global _selected_weekday
    if weekday not in WEEKDAYS:
        logger.warning(f"Ignoring unknown weekday: {weekday}")
        return
    _selected_weekday = weekday


def get_selected_weekday() -> str:
    return _selected_weekday


def parse_weekday(xml_config: str) -> str:
    """Read the weekday back out of an existing task's trigger XML."""
    if not xml_config:
        return _DEFAULT_WEEKDAY
    match = re.search(r"<DaysOfWeek>(.*?)</DaysOfWeek>", xml_config, re.DOTALL)
    if not match:
        return _DEFAULT_WEEKDAY
    for weekday in WEEKDAYS:
        if f"<{weekday}" in match.group(1):
            return weekday
    return _DEFAULT_WEEKDAY


def weekly_trigger_xml(start_boundary: str, weekday: str) -> str:
    """Weekly CalendarTrigger XML for the given weekday."""
    if weekday not in WEEKDAYS:
        weekday = _DEFAULT_WEEKDAY
    return f"""<CalendarTrigger>
            <StartBoundary>{start_boundary}</StartBoundary>
            <Enabled>true</Enabled>
      <ScheduleByWeek>
        <WeeksInterval>1</WeeksInterval>
        <DaysOfWeek>
                    <{weekday}></{weekday}>
        </DaysOfWeek>
      </ScheduleByWeek>
    </CalendarTrigger>"""


def _install_weekday_row(dialog, initial_weekday: str):
    """Append a Day of Week row to a schedule dialog and keep the holder in sync."""
    from PySide6.QtWidgets import QGridLayout, QLabel, QWidget
    from qfluentwidgets import ComboBox

    form_layout = None
    for child in dialog.findChildren(QWidget):
        layout = child.layout()
        if isinstance(layout, QGridLayout):
            form_layout = layout
            break
    if form_layout is None:
        logger.warning("Schedule dialog form layout not found; weekday picker not installed")
        return None

    weekday_label = QLabel(dialog.tr("Day of Week"))
    weekday_label.setMinimumWidth(120)
    weekday_combo = ComboBox()
    weekday_combo.setFixedHeight(34)
    # English source strings, like the rest of this dialog: it is an ok-script widget, so
    # tr() resolves against ok-script's Qt catalogs rather than this project's gettext ones.
    weekday_combo.addItems([dialog.tr(weekday) for weekday in WEEKDAYS])
    weekday_combo.setCurrentIndex(WEEKDAYS.index(initial_weekday))

    row = form_layout.rowCount()
    form_layout.addWidget(weekday_label, row, 0)
    form_layout.addWidget(weekday_combo, row, 1)

    dialog.weekday_label = weekday_label
    dialog.weekday_combo = weekday_combo

    def on_weekday_changed(index):
        if 0 <= index < len(WEEKDAYS):
            set_selected_weekday(WEEKDAYS[index])

    weekday_combo.currentIndexChanged.connect(on_weekday_changed)
    set_selected_weekday(initial_weekday)

    def sync_visibility():
        is_weekly = dialog.trigger_combo.currentIndex() == _WEEKLY_TRIGGER_INDEX
        weekday_label.setVisible(is_weekly)
        weekday_combo.setVisible(is_weekly)

    dialog.trigger_combo.currentIndexChanged.connect(sync_visibility)
    sync_visibility()
    return weekday_combo


def install_schedule_weekday_patch():
    global _PATCH_INSTALLED
    if _PATCH_INSTALLED:
        return

    from ok.ui.qt.tasks.ScheduleTaskTab import (
        CreateScheduleTaskDialog,
        ModifyScheduleTaskDialog,
    )
    from ok.util.windows_schedule import TriggerType, WindowsScheduleManager

    original_get_trigger_xml = WindowsScheduleManager._get_trigger_xml

    @wraps(original_get_trigger_xml)
    def get_trigger_xml_with_weekday(
        self, trigger_type, start_boundary, interval_days=0, interval_hours=0
    ):
        if trigger_type == TriggerType.WEEKLY:
            return weekly_trigger_xml(start_boundary, get_selected_weekday())
        return original_get_trigger_xml(
            self, trigger_type, start_boundary, interval_days, interval_hours
        )

    WindowsScheduleManager._get_trigger_xml = get_trigger_xml_with_weekday

    original_create_init = CreateScheduleTaskDialog.__init__

    @wraps(original_create_init)
    def create_init_with_weekday(self, parent=None):
        original_create_init(self, parent)
        _install_weekday_row(self, _DEFAULT_WEEKDAY)

    CreateScheduleTaskDialog.__init__ = create_init_with_weekday

    original_modify_init = ModifyScheduleTaskDialog.__init__

    @wraps(original_modify_init)
    def modify_init_with_weekday(self, task_info, parent=None):
        original_modify_init(self, task_info, parent)
        _install_weekday_row(self, parse_weekday(getattr(task_info, "xml_config", "")))

    ModifyScheduleTaskDialog.__init__ = modify_init_with_weekday

    _PATCH_INSTALLED = True
