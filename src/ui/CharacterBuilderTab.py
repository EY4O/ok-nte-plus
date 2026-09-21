"""Character Builder: pick characters, see what their next ascension is short of, and
point the daily Anomaly tasks at farming it.

Everything shown comes from Character Ascend Scan (configs/CharacterAscendMap.json).
The only thing written is the Daily Routine's settings for Anomaly Hunts and Anomaly
Zone, after a before/after preview. Material Conversion is never used; the plan is sized
by the raw shortfall.
"""

from ok import og
from ok.ui.qt.widget.CustomTab import CustomTab
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QListWidgetItem,
    QTableWidgetItem,
    QVBoxLayout,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CheckBox,
    ComboBox,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    ListWidget,
    PrimaryPushButton,
    PushButton,
    SimpleCardWidget,
    StrongBodyLabel,
    TableWidget,
)

from src.builder import farm_plan as fp
from src.events import communicate
from src.tasks.CharacterAscendScanTask import CharacterAscendScanTask


class CharacterBuilderTab(CustomTab):
    def __init__(self):
        super().__init__()
        self.icon = FluentIcon.DEVELOPER_TOOLS
        self.tr_name = self.tr("角色养成")
        self.records: dict = {}
        self.steps: list = []
        self._hunts: list = []
        self._scan_pending = False
        self._scan_seen_running = False

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)
        root.addWidget(self._build_character_card(), 2)
        right = QVBoxLayout()
        right.setSpacing(16)
        right.addWidget(self._build_needs_card(), 3)
        right.addWidget(self._build_apply_card(), 2)
        root.addLayout(right, 5)

        communicate.task.connect(self._on_framework_task_changed)
        self.reload()

    @property
    def name(self):  # type: ignore
        return self.tr_name

    # --- layout

    def _build_character_card(self):
        card = SimpleCardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(StrongBodyLabel(self.tr("角色"), card))
        self.character_list = ListWidget(card)
        self.character_list.itemChanged.connect(self._refresh_plan)
        layout.addWidget(self.character_list, 1)

        row = QHBoxLayout()
        self.select_ascend_button = PushButton(self.tr("全选可突破"), card)
        self.clear_button = PushButton(self.tr("清除"), card)
        row.addWidget(self.select_ascend_button)
        row.addWidget(self.clear_button)
        layout.addLayout(row)
        self.rescan_button = PushButton(FluentIcon.SYNC, self.tr("重新扫描全部角色"), card)
        layout.addWidget(self.rescan_button)
        self.scan_hint = CaptionLabel(card)
        self.scan_hint.setWordWrap(True)
        layout.addWidget(self.scan_hint)

        self.select_ascend_button.clicked.connect(lambda: self._check_where(
            lambda r: r.get("status") == "ascend"))
        self.clear_button.clicked.connect(lambda: self._check_where(lambda r: False))
        self.rescan_button.clicked.connect(self._start_rescan)
        return card

    def _build_needs_card(self):
        card = SimpleCardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(StrongBodyLabel(self.tr("所需材料"), card))
        self.needs_table = TableWidget(card)
        self.needs_table.setColumnCount(4)
        self.needs_table.setHorizontalHeaderLabels(
            [self.tr("材料"), self.tr("缺少"), self.tr("获取途径"), self.tr("角色")]
        )
        self.needs_table.verticalHeader().hide()
        self.needs_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.needs_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        header = self.needs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.needs_table, 1)
        self.needs_hint = CaptionLabel(card)
        self.needs_hint.setWordWrap(True)
        layout.addWidget(self.needs_hint)
        return card

    def _build_apply_card(self):
        card = SimpleCardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(StrongBodyLabel(self.tr("应用到日常任务"), card))

        hunt_row = QHBoxLayout()
        self.hunt_check = CheckBox(self.tr("设置异象追猎目标"), card)
        self.hunt_combo = ComboBox(card)
        self.hunt_combo.setMinimumWidth(280)
        hunt_row.addWidget(self.hunt_check)
        hunt_row.addWidget(self.hunt_combo, 1)
        layout.addLayout(hunt_row)
        self.exp_check = CheckBox(self.tr("将异象界域设为角色经验"), card)
        layout.addWidget(self.exp_check)

        self.preview_label = BodyLabel(card)
        self.preview_label.setWordWrap(True)
        self.preview_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.preview_label)
        note = CaptionLabel(self.tr(
            "异象界域与异象追猎共用一个日常位置, 请在日常任务页选择执行哪一个。"
            "从不使用材料转换, 只刷取原始材料。"
        ), card)
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        self.apply_button = PrimaryPushButton(FluentIcon.ACCEPT, self.tr("应用"), card)
        layout.addWidget(self.apply_button, alignment=Qt.AlignmentFlag.AlignRight)

        self.hunt_check.stateChanged.connect(self._refresh_preview)
        self.exp_check.stateChanged.connect(self._refresh_preview)
        self.hunt_combo.currentIndexChanged.connect(self._refresh_preview)
        self.apply_button.clicked.connect(self._apply)
        return card

    # --- data

    def reload(self):
        checked = self._checked_names()
        self.records = fp.load_ascend_map()
        self.character_list.blockSignals(True)
        self.character_list.clear()
        for name, record in self.records.items():
            item = QListWidgetItem(self._character_label(name, record))
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if name in checked else Qt.CheckState.Unchecked
            )
            self.character_list.addItem(item)
        self.character_list.blockSignals(False)
        self.scan_hint.setText(
            self.tr("共 {} 名角色").format(len(self.records)) if self.records
            else self.tr("尚无扫描结果, 请点击重新扫描全部角色")
        )
        self._refresh_plan()

    def _character_label(self, name, record) -> str:
        level, cap = record.get("level"), record.get("cap")
        text = name
        if level is not None and cap is not None:
            text += f"   Lv {level}/{cap}"
        if record.get("status") == "ascend":
            text += "   " + self.tr("可突破")
            if record.get("next_cap"):
                text += f" → {record['next_cap']}"
        elif record.get("status") == "level_up":
            text += "   " + self.tr("需要经验")
        return text

    def _checked_names(self) -> list:
        names = []
        for i in range(self.character_list.count()):
            item = self.character_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                names.append(item.data(Qt.ItemDataRole.UserRole))
        return names

    def _check_where(self, predicate):
        self.character_list.blockSignals(True)
        for i in range(self.character_list.count()):
            item = self.character_list.item(i)
            record = self.records.get(item.data(Qt.ItemDataRole.UserRole), {})
            item.setCheckState(
                Qt.CheckState.Checked if predicate(record) else Qt.CheckState.Unchecked
            )
        self.character_list.blockSignals(False)
        self._refresh_plan()

    # --- plan

    def _route_text(self, step) -> str:
        if step.kind == fp.KIND_HUNT:
            target = step.config[fp.AnomalyHunter.CONF_HUNTER_TARGET]
            return f"{self.tr('异象追猎')}: {self.tr(target)}"
        if step.kind == fp.KIND_EXP:
            return f"{self.tr('异象界域')}: {self.tr('角色经验')}"
        if step.kind == fp.KIND_ANOMALY_DROP:
            return self.tr("手动: 野外异象掉落")
        return self.tr("手动") + (f": {step.source}" if step.source else "")

    def _refresh_plan(self, *_):
        records = [self.records[n] for n in self._checked_names() if n in self.records]
        self.steps = fp.build_plan(records)
        self.needs_table.setRowCount(len(self.steps))
        for row, step in enumerate(self.steps):
            material = step.material or self.tr("角色经验")
            short = str(step.deficit) if step.kind != fp.KIND_EXP else "—"
            cells = [material, short, self._route_text(step), ", ".join(step.characters)]
            for col, text in enumerate(cells):
                self.needs_table.setItem(row, col, QTableWidgetItem(text))
        if not records:
            self.needs_hint.setText(self.tr("勾选角色以查看所需材料"))
        elif not self.steps:
            self.needs_hint.setText(self.tr("所选角色的突破材料已足够"))
        else:
            self.needs_hint.setText("")

        # Keep the chosen hunt when the selection changes, as long as it is still needed.
        index = self.hunt_combo.currentIndex()
        previous = self._hunts[index].material if 0 <= index < len(self._hunts) else None
        self._hunts = fp.hunt_steps(self.steps)
        self.hunt_combo.blockSignals(True)
        self.hunt_combo.clear()
        for step in self._hunts:
            target = self.tr(step.config[fp.AnomalyHunter.CONF_HUNTER_TARGET])
            self.hunt_combo.addItem(
                f"{target} — {step.material} ({self.tr('缺少')} {step.deficit})"
            )
        materials = [s.material for s in self._hunts]
        if previous in materials:
            self.hunt_combo.setCurrentIndex(materials.index(previous))
        self.hunt_combo.blockSignals(False)
        self.hunt_check.setEnabled(bool(self._hunts))
        self.hunt_combo.setEnabled(bool(self._hunts))
        self.hunt_check.setChecked(bool(self._hunts))
        has_exp = any(s.kind == fp.KIND_EXP for s in self.steps)
        self.exp_check.setEnabled(has_exp)
        self.exp_check.setChecked(has_exp)
        self._refresh_preview()

    # --- apply

    def _routine(self):
        if self.executor is None:
            return None
        return self.executor.get_task_by_class_name("DailyRoutineTask")

    def _changes(self) -> dict:
        hunt = None
        if self.hunt_check.isChecked() and self._hunts:
            hunt = self._hunts[max(0, self.hunt_combo.currentIndex())]
        exp = None
        if self.exp_check.isChecked():
            exp = next((s for s in self.steps if s.kind == fp.KIND_EXP), None)
        return fp.routine_changes(hunt, exp)

    def _current_settings(self, routine, changes) -> dict:
        current = {}
        for task_id in changes:
            task = routine.task_for_id(task_id)
            if task is not None:
                current[task_id] = dict(routine.daily_task_config(task_id, task))
        return current

    def _refresh_preview(self, *_):
        changes = self._changes()
        routine = self._routine()
        if not changes:
            self.preview_label.setText(self.tr("没有需要更改的设置"))
            self.apply_button.setEnabled(False)
            return
        if routine is None:
            self.preview_label.setText(self.tr("日常任务未就绪"))
            self.apply_button.setEnabled(False)
            return
        rows = fp.preview_changes(self._current_settings(routine, changes), changes)
        if not rows:
            self.preview_label.setText(self.tr("日常任务已是这些设置"))
            self.apply_button.setEnabled(False)
            return
        lines = []
        for task_id, key, before, after in rows:
            task = self.tr("异象追猎") if task_id == fp.ROUTINE_HUNTER else self.tr("异象界域")
            shown = self.tr(str(before)) if before is not None else "—"
            lines.append(f"{task} · {self.tr(key)}: {shown} → {self.tr(str(after))}")
        self.preview_label.setText("\n".join(lines))
        self.apply_button.setEnabled(True)

    def _apply(self):
        routine = self._routine()
        changes = self._changes()
        if routine is None or not changes:
            return
        for task_id, values in changes.items():
            task = routine.task_for_id(task_id)
            if task is not None:
                routine.daily_task_config(task_id, task).update(values)
        self._refresh_preview()
        InfoBar.success(
            title=self.tr("已应用到日常任务"),
            content=self.tr("重新打开日常任务页即可看到新设置"),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self.window(),
        )

    # --- rescan

    def _scan_task(self):
        if self.executor is None:
            return None
        return self.get_task(CharacterAscendScanTask)

    def _start_rescan(self):
        task = self._scan_task()
        if task is None:
            return
        task.config[CharacterAscendScanTask.CONF_SCAN_ROSTER] = True
        self._scan_pending = True
        self._scan_seen_running = False
        self.rescan_button.setEnabled(False)
        self.scan_hint.setText(self.tr("扫描中, 请保持游戏窗口在前台..."))
        og.app.start_controller.start(task)

    def _on_framework_task_changed(self, task):
        if not self._scan_pending or task is not self._scan_task():
            return
        # The first notices can arrive before the task starts running; wait until it
        # has run and stopped.
        if task.running:
            self._scan_seen_running = True
            return
        if not self._scan_seen_running:
            return
        self._scan_pending = False
        self._scan_seen_running = False
        self.rescan_button.setEnabled(True)
        self.reload()
