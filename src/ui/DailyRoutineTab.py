from ok.ui.qt.common.design_system import DesignToken, configure_page_layout
from ok.ui.qt.common.style_sheet import StyleSheet
from ok.ui.qt.tasks.TaskCard import TaskCard
from ok.ui.qt.widget.CustomTab import CustomTab
from PySide6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QWidget,
    QWidgetItem,
)
from qfluentwidgets import (
    CheckBox,
    ComboBox,
    ExpandLayout,
    FluentIcon,
    HorizontalSeparator,
    PushButton,
    ScrollArea,
    isDarkTheme,
)

from src.tasks.daily.DailyRoutineProfiles import DAILY_ROUTINE_PROFILE_CLASSES
from src.tasks.daily.DailyRoutineTask import (
    DailyRoutineEntry,
    DailyRoutineTask,
    selection_is_complete,
)
from src.ui.foundation.icons import FluentSystemIcon


class _DragHandle(QWidget):
    def __init__(self, routine_tab, routine_card, parent=None):
        super().__init__(parent)
        self.routine_tab = routine_tab
        self.routine_card = routine_card
        self.press_position = QPointF()
        self.dragging = False
        self.setFixedSize(24, 40)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAccessibleName("Drag to reorder")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(255, 255, 255, 105) if isDarkTheme() else QColor(0, 0, 0, 95)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        for row in range(3):
            for column in range(2):
                painter.drawEllipse(8 + column * 5, 14 + row * 5, 2, 2)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_position = event.globalPosition()
            self.dragging = False
            self.grabMouse()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not event.buttons() & Qt.MouseButton.LeftButton:
            super().mouseMoveEvent(event)
            return
        if not self.dragging:
            if (event.globalPosition() - self.press_position).manhattanLength() < 8:
                return
            self.dragging = True
            self.routine_tab.start_drag(self.routine_card, event.globalPosition())
            self.routine_card.set_dragging(True)
        self.routine_tab.move_drag(self.routine_card, event.globalPosition())
        event.accept()

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if event.button() == Qt.MouseButton.LeftButton:
            self.releaseMouse()
            if self.dragging:
                self.routine_card.set_dragging(False)
                self.routine_tab.finish_drag(self.routine_card)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class DailyRoutineCardLayout(ExpandLayout):
    """Lay out the daily routine's expandable cards and support drag reordering."""

    def addCard(self, card):
        if self.indexOf(card) >= 0:
            return

        parent = self.parentWidget()
        if parent is not None and card.parentWidget() is not parent:
            card.setParent(parent)

        super().addWidget(card)
        self.addItem(QWidgetItem(card))
        card.show()
        self.invalidate()

    def removeCard(self, card):
        index = self.indexOf(card)
        if index >= 0:
            item = self.takeAt(index)
            if widget := item.widget():
                widget.removeEventFilter(self)
            self.invalidate()

    def moveCard(self, card, index):
        cards = self.cards()
        try:
            current_index = cards.index(card)
        except ValueError:
            return

        index = max(0, min(index, len(cards) - 1))
        if index == current_index:
            return

        cards.insert(index, cards.pop(current_index))
        self._replace_cards(cards)
        self.activate()

    def cards(self):
        return [self.itemAt(index).widget() for index in range(self.count())]

    def _replace_cards(self, cards):
        while self.count():
            item = self.takeAt(0)
            if widget := item.widget():
                widget.removeEventFilter(self)

        for card in cards:
            self.addCard(card)


class _DailyRoutineCard(TaskCard):
    enabled_changed = Signal(str, bool)
    expansion_changed = Signal(bool)

    def __init__(self, entry: DailyRoutineEntry, task, routine_tab, enabled):
        with routine_tab.daily_task_card_context(entry.task_id, task) as card_task:
            if card_task is None:
                raise RuntimeError(f"Daily routine task is unavailable: {entry.task_id}")
            super().__init__(card_task, True)
        self.entry = entry
        self.task = task
        self.routine_tab = routine_tab
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.button_container.hide()
        self._drag_effect = None

        self.drag_handle = _DragHandle(routine_tab, self, self.card)
        self.enabled_check = CheckBox(self.card)
        self.enabled_check.setFixedSize(24, 24)
        self.enabled_check.setAccessibleName("Include in this daily routine")
        self.enabled_check.setChecked(True)
        self.card.hBoxLayout.insertWidget(0, self.drag_handle, 0, Qt.AlignmentFlag.AlignVCenter)
        self.card.hBoxLayout.insertSpacing(1, 8)
        self.card.hBoxLayout.insertWidget(2, self.enabled_check, 0, Qt.AlignmentFlag.AlignVCenter)
        self.card.hBoxLayout.insertSpacing(3, 8)

        self.enabled_check.toggled.connect(
            lambda checked: self.enabled_changed.emit(self.entry.task_id, checked)
        )
        self.set_enabled(enabled)

    def set_enabled(self, enabled):
        self.enabled_check.blockSignals(True)
        self.enabled_check.setChecked(enabled)
        self.enabled_check.blockSignals(False)
        if enabled:
            self.card.titleLabel.setGraphicsEffect(None)
        else:
            opacity_effect = QGraphicsOpacityEffect(self.card.titleLabel)
            opacity_effect.setOpacity(0.5)
            self.card.titleLabel.setGraphicsEffect(opacity_effect)

    def setExpand(self, isExpand):
        was_expanded = getattr(self, "isExpand", False)
        super().setExpand(isExpand)
        if was_expanded != self.isExpand:
            self.expansion_changed.emit(self.isExpand)

    def set_dragging(self, dragging):
        if dragging:
            effect = QGraphicsOpacityEffect(self)
            effect.setOpacity(0.0)
            self._drag_effect = effect
            self.setGraphicsEffect(effect)
            return
        self.setGraphicsEffect(None)
        self._drag_effect = None


class DailyRoutineTab(CustomTab):
    ACTION_BAR_HEIGHT = 72

    def __init__(self):
        super().__init__()
        self.setObjectName("DailyRoutineTab")
        self.icon = FluentIcon.CALENDAR
        self.tr_name = self.tr("日常任务")
        self._rendered = False
        self._cards = {}
        self._profiles = []
        # Cards are built once per profile and toggled: ExpandLayout.addWidget() appends to a
        # private list that removeWidget() never clears, so deleting a card leaves the layout
        # dereferencing a freed C++ object.
        self._settings_cards = {}
        self._control_cards = {}
        self._routine_settings_card = None
        self.routine_separator = None
        self._task_control_card = None
        self._order_changed = False
        self._drag_proxy = None
        self._drag_animations = []
        self._drag_offset = None
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)

        self.profile_bar = QWidget(self.view)
        self.profile_bar.setObjectName("dailyRoutineProfileBar")
        profile_layout = QHBoxLayout(self.profile_bar)
        profile_layout.setContentsMargins(DesignToken.PAGE_MARGIN, 12, DesignToken.PAGE_MARGIN, 0)
        profile_layout.setSpacing(12)
        self.profile_label = QLabel(self.tr("方案"), self.profile_bar)
        self.profile_combo = ComboBox(self.profile_bar)
        self.profile_combo.setFixedHeight(34)
        self.profile_combo.setMinimumWidth(200)
        profile_layout.addWidget(self.profile_label)
        profile_layout.addWidget(self.profile_combo)
        profile_layout.addStretch(1)
        self.vBoxLayout.addWidget(self.profile_bar)

        self.routine_settings_view = QWidget(self.view)
        self.routine_settings_view.setObjectName("view")
        self.routine_settings_layout = ExpandLayout(self.routine_settings_view)
        configure_page_layout(self.routine_settings_layout)
        self.vBoxLayout.addWidget(self.routine_settings_view)

        self.routine_scroll_area = ScrollArea(self.view)
        self.routine_scroll_area.setObjectName("view")
        self.routine_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.routine_scroll_area.setWidgetResizable(True)
        StyleSheet.TAB.apply(self.routine_scroll_area)

        self.routine_view = QWidget(self.routine_scroll_area)
        self.routine_view.setObjectName("view")
        self.routine_layout = DailyRoutineCardLayout(self.routine_view)
        configure_page_layout(self.routine_layout)
        self.routine_scroll_area.setWidget(self.routine_view)
        self.vBoxLayout.addWidget(self.routine_scroll_area, 1)

        self.action_bar = QWidget(self.view)
        self.action_bar.setObjectName("dailyRoutineActionBar")
        self.action_bar.setFixedHeight(self.ACTION_BAR_HEIGHT)

        action_layout = QHBoxLayout(self.action_bar)
        action_layout.setContentsMargins(DesignToken.PAGE_MARGIN, 12, DesignToken.PAGE_MARGIN, 12)
        action_layout.setSpacing(16)
        self.select_all_check = CheckBox(self.tr("全选"), self.action_bar)
        self.collapse_button = PushButton(
            FluentSystemIcon.CHEVRON_UP_DOWN, self.tr("全部展开"), self.action_bar
        )
        action_layout.addWidget(self.select_all_check)
        action_layout.addWidget(self.collapse_button)
        action_layout.addStretch(1)
        self.action_layout = action_layout
        self.vBoxLayout.addWidget(self.action_bar)

        self.select_all_check.toggled.connect(self._set_all_selected)
        self.collapse_button.clicked.connect(self._toggle_all_expansion)
        self.profile_combo.currentIndexChanged.connect(self._select_profile)

    @property
    def executor(self):
        return self._executor

    @executor.setter
    def executor(self, value):
        self._executor = value
        if value is None:
            self._profiles = []
            self.task = None
            return
        # Resolve by exact class name: every profile is a DailyRoutineTask subclass, so an
        # isinstance lookup would always return the first one.
        self._profiles = [
            task
            for profile_class in DAILY_ROUTINE_PROFILE_CLASSES
            if (task := value.get_task_by_class_name(profile_class.__name__)) is not None
        ]
        self.task = self._profiles[0] if self._profiles else self.get_task(DailyRoutineTask)
        self._sync_profile_combo()
        if getattr(self, "_rendered", False) is False:
            self._render_routine()

    def _sync_profile_combo(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems([self.tr(task.name) for task in self._profiles])
        if self.task in self._profiles:
            self.profile_combo.setCurrentIndex(self._profiles.index(self.task))
        self.profile_bar.setVisible(len(self._profiles) > 1)
        self.profile_combo.blockSignals(False)

    def _refresh_profile_names(self):
        """Reflect a renamed profile in the dropdown without rebuilding it."""
        for index, task in enumerate(self._profiles):
            if index < self.profile_combo.count():
                self.profile_combo.setItemText(index, self.tr(task.name))

    def _watch_profile_name(self, card):
        """Update the dropdown live while the Profile Name field is edited."""
        widget = card.config_widget_by_key.get(DailyRoutineTask.CONF_PROFILE_NAME)
        line_edit = getattr(widget, "line_edit", None)
        if line_edit is not None:
            line_edit.textChanged.connect(lambda _text: self._refresh_profile_names())

    def _select_profile(self, index):
        if index < 0 or index >= len(self._profiles):
            return
        if self.task is self._profiles[index]:
            return
        self.task = self._profiles[index]
        self._render_routine()

    @property
    def name(self):  # type: ignore
        return self.tr_name

    def _routine_task(self):
        return self.task

    def daily_task_card_context(self, task_id, task):
        routine_task = self._routine_task()
        if routine_task is None:
            raise RuntimeError("Daily routine task is unavailable")
        return routine_task.daily_task_card_context(task_id, task)

    def _install_routine_settings(self, routine_task):
        key = type(routine_task).__name__
        entry = self._settings_cards.get(key)
        if entry is None:
            card = TaskCard(routine_task, True)
            card.button_container.hide()
            if card.reset_config is not None:
                card.reset_config.clicked.connect(self._render_routine)
            card.setParent(self.routine_settings_view)
            self.routine_settings_layout.addWidget(card)
            # Each profile carries its own separator so the visible pair always stays in
            # order; ExpandLayout appends and cannot insert. Parent it to the same widget as
            # the card: routine_settings_layout positions in routine_settings_view's
            # coordinates, so a separator parented elsewhere paints at the wrong offset.
            separator = HorizontalSeparator(self.routine_settings_view)
            self.routine_settings_layout.addWidget(separator)
            entry = (card, separator)
            self._settings_cards[key] = entry
            self._watch_profile_name(card)

        for other_key, (card, separator) in self._settings_cards.items():
            visible = other_key == key
            card.setVisible(visible)
            separator.setVisible(visible)

        self._routine_settings_card, self.routine_separator = entry
        self.routine_settings_layout.invalidate()

    def _render_routine(self):
        routine_task = self._routine_task()
        if routine_task is None:
            return
        self._install_routine_settings(routine_task)
        while self.routine_layout.count():
            layout_item = self.routine_layout.takeAt(0)
            if widget := layout_item.widget():
                widget.deleteLater()
        self._cards.clear()
        for routine_item in routine_task.normalize_items():
            entry = routine_task.entries_by_id()[routine_item["id"]]
            task = routine_task.task_for_id(entry.task_id)
            if task is None:
                continue
            card = _DailyRoutineCard(entry, task, self, routine_item["enabled"])
            card.setParent(self.routine_view)
            card.enabled_changed.connect(self._set_enabled)
            card.expansion_changed.connect(self._sync_expansion_control)
            self.routine_layout.addCard(card)
            self._cards[entry.task_id] = card
        self._install_task_controls(routine_task)
        self.routine_layout.invalidate()
        self.routine_layout.activate()
        self._rendered = True
        self._sync_profile_combo()
        self._sync_selection_controls()
        self._sync_expansion_control()

    def start_drag(self, card, global_position):
        pixmap = card.grab()
        self._drag_proxy = QLabel(self.routine_view)
        self._drag_proxy.setPixmap(pixmap)
        effect = QGraphicsOpacityEffect(self._drag_proxy)
        effect.setOpacity(0.7)
        self._drag_proxy.setGraphicsEffect(effect)

        self._drag_offset = card.mapFromGlobal(global_position.toPoint())
        self._drag_proxy.resize(card.size())

        local_pos = self.routine_view.mapFromGlobal(global_position.toPoint()) - self._drag_offset
        self._drag_proxy.move(card.pos().x(), local_pos.y())

        self._drag_proxy.raise_()
        self._drag_proxy.show()

    def move_drag(self, card, global_position):
        if not self._drag_proxy:
            return

        local_pos = self.routine_view.mapFromGlobal(global_position.toPoint()) - self._drag_offset

        target_x = card.pos().x()
        max_y = self.routine_view.height()
        clamped_y = max(-self._drag_proxy.height(), min(local_pos.y(), max_y))
        self._drag_proxy.move(target_x, clamped_y)

        local_y = self._drag_proxy.geometry().center().y()
        current_index = self.routine_layout.indexOf(card)
        target_index = self.routine_layout.count()

        for index in range(self.routine_layout.count()):
            candidate = self.routine_layout.itemAt(index).widget()
            if candidate and candidate is not card:
                if local_y < candidate.geometry().center().y():
                    target_index = index
                    break

        if target_index > current_index:
            target_index -= 1

        if target_index != current_index:
            self.routine_view.setUpdatesEnabled(False)
            old_positions = {}
            for index in range(self.routine_layout.count()):
                w = self.routine_layout.itemAt(index).widget()
                if w:
                    old_positions[w] = w.pos()

            self.routine_layout.moveCard(card, target_index)

            self._drag_animations.clear()

            for index in range(self.routine_layout.count()):
                w = self.routine_layout.itemAt(index).widget()
                if w and w in old_positions:
                    new_pos = w.pos()
                    old_pos = old_positions[w]
                    if new_pos != old_pos and w is not card:
                        anim = QPropertyAnimation(w, b"pos")
                        anim.setDuration(200)
                        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
                        anim.setStartValue(old_pos)
                        anim.setEndValue(new_pos)
                        self._drag_animations.append(anim)
                        w.move(old_pos)
            self.routine_view.setUpdatesEnabled(True)
            for anim in self._drag_animations:
                anim.start()

            self._order_changed = True

    def finish_drag(self, card):
        if self._drag_proxy:
            self._drag_proxy.hide()
            self._drag_proxy.deleteLater()
            self._drag_proxy = None

        if self._order_changed:
            self._order_changed = False
            self._routine_task().set_available_item_order(
                [
                    self.routine_layout.itemAt(index).widget().entry.task_id
                    for index in range(self.routine_layout.count())
                ]
            )

    def _visible_items(self):
        return [
            {"id": card.entry.task_id, "enabled": card.enabled_check.isChecked()}
            for index in range(self.routine_layout.count())
            if (card := self.routine_layout.itemAt(index).widget()) is not None
        ]

    def _sync_routine_items(self, items):
        enabled_by_id = {item["id"]: item["enabled"] for item in items}
        for task_id, card in self._cards.items():
            card.set_enabled(enabled_by_id.get(task_id, False))
        self._sync_selection_controls()

    def _set_enabled(self, task_id, enabled):
        items = self._routine_task().set_item_enabled(task_id, enabled)
        self._sync_routine_items(items)

    def _set_all_selected(self, selected):
        items = self._routine_task().set_all_available_items_selected(selected)
        self._sync_routine_items(items)

    def _sync_selection_controls(self):
        items = self._visible_items()
        has_selection = any(item["enabled"] for item in items)
        if self._task_control_card is not None:
            routine_task = self._routine_task()
            self._task_control_card.update_buttons(routine_task)
            if not routine_task.enabled:
                self._task_control_card.start_button.setEnabled(has_selection)
        entries = {item["id"]: self._routine_task().entries_by_id()[item["id"]] for item in items}
        is_complete = selection_is_complete(items, entries)
        self.select_all_check.blockSignals(True)
        self.select_all_check.setChecked(is_complete)
        self.select_all_check.blockSignals(False)
        self.select_all_check.setText(self.tr("取消全选") if is_complete else self.tr("全选"))

    def _toggle_all_expansion(self):
        expand = not any(card.isExpand for card in self._cards.values())
        for card in self._cards.values():
            card.setExpand(expand)

    def _sync_expansion_control(self):
        should_collapse = any(card.isExpand for card in self._cards.values())
        self.collapse_button.setIcon(
            FluentSystemIcon.CHEVRON_DOWN_UP
            if should_collapse
            else FluentSystemIcon.CHEVRON_UP_DOWN
        )
        self.collapse_button.setText(
            self.tr("全部折叠") if should_collapse else self.tr("全部展开")
        )

    def _install_task_controls(self, routine_task):
        key = type(routine_task).__name__
        card = self._control_cards.get(key)
        if card is None:
            card = TaskCard(routine_task, True)
            card.hide()
            controls = card.button_container
            controls.setParent(self.action_bar)
            self.action_layout.addWidget(controls)
            self._control_cards[key] = card

        for other_key, other in self._control_cards.items():
            other.button_container.setVisible(other_key == key)

        self._task_control_card = card
