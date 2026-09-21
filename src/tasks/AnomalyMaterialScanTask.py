from src.tasks.AnomalyTask import AnomalyTask
from src.tasks.BaseNTETask import BaseNTETask
from src.tasks.NTEOneTimeTask import NTEOneTimeTask
from src.utils.result_config import ResultConfig


class AnomalyMaterialScanTask(NTEOneTimeTask, BaseNTETask):
    """Read the Anomaly Zone domain page and record what each task type offers.

    Phase 1 of the Character Builder groundwork. AnomalyTask addresses materials by
    list index (CONF_ABILITY_ID and friends), but guides and the planned character data
    file name materials in words. This builds the index-to-name mapping from the
    player's own game, so it stays correct when a patch reorders the list.

    Strictly read-only: it opens the F1 domain page and clicks the four task type tabs,
    nothing else. It never selects a domain, never travels, and never enters an
    instance, so it costs no City Stamina.

    Phase 2, if this is not enough, would travel to a domain and read the in-world
    sub-item list that click_sub_idx() selects from.
    """

    MAP_FILE_NAME = "AnomalyMaterialMap"

    # Generous while calibrating: log everything on the page with coordinates.
    PANEL_BOX = (0.05, 0.10, 0.99, 0.95)
    # Where AnomalyTask looks for the domain enter buttons; names should sit left of it.
    DOMAIN_BUTTON_BOX = (0.925, 0.190, 0.982, 0.760)
    DOMAIN_LIST_BOX = (0.10, 0.19, 0.92, 0.80)

    TAB_SETTLE = 1.2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "异象材料扫描"
        self.description = "读取异象界域各页签的项目名称, 建立序号与材料名的对应, 不消耗体力"
        self.material_map = None

    def on_create(self):
        self.material_map = ResultConfig(self.MAP_FILE_NAME)

    def run(self):
        super().run()
        return self.do_run()

    def do_run(self) -> bool:
        self.ensure_main()
        self.log_info("打开 F1 异象界域页面")
        self.open_f1_domain_page()
        self.sleep(0.8)

        scanned = {}
        for task_type in AnomalyTask.TASK_TYPES:
            scanned[task_type] = self._scan_tab(task_type)

        self._save(scanned)
        total = sum(len(v) for v in scanned.values())
        self.log_info(f"扫描完成, 共记录 {total} 行文本", notify=True)
        self.info_set("已扫描页签", len(scanned))
        return True

    @staticmethod
    def tab_position(task_type: str):
        """Tab coordinates for a task type, or None if unknown.

        The constants live on AnomalyTask so the two tasks cannot drift apart, but the
        click is done here: AnomalyTask.click_task_type_tab() reads attributes off its
        own class, so calling it with this task as self raises AttributeError.
        """
        x = AnomalyTask.TASK_TYPE_TAB_X.get(task_type)
        return None if x is None else (x, AnomalyTask.TASK_TYPE_TAB_Y)

    def _scan_tab(self, task_type: str) -> list:
        position = self.tab_position(task_type)
        if position is None:
            self.log_error(f"未知任务类型, 跳过: {task_type}")
            return []
        self.log_info(f"切换至页签: {task_type}")
        self.operate_click(*position)
        self.sleep(self.TAB_SETTLE)

        lines = self._report_region(f"{task_type}/panel", self.PANEL_BOX)
        buttons = self._report_region(f"{task_type}/buttons", self.DOMAIN_BUTTON_BOX)
        self.log_info(f"[{task_type}] 面板 {len(lines)} 行, 按钮区 {len(buttons)} 行")
        self.screenshot(f"anomaly_scan_{AnomalyTask.TASK_TYPES.index(task_type)}")
        return lines

    def _report_region(self, label: str, region: tuple) -> list:
        boxes = self.ocr(*region, name=label) or []
        if not boxes:
            self.log_info(f"[{label}] 未识别到文本, 区域 {region}")
            return []
        entries = []
        for box in boxes:
            self.log_info(f"[{label}] {box.name} @ x={box.x} y={box.y} w={box.width}")
            entries.append({"text": box.name, "x": box.x, "y": box.y, "width": box.width})
        return entries

    def _save(self, scanned: dict) -> None:
        """Persist the raw scan so the mapping can be derived without another game run."""
        if self.material_map is None:
            self.log_warning("配置未初始化, 跳过保存")
            return
        for task_type, entries in scanned.items():
            self.material_map[task_type] = entries
        self.log_info(f"已写入 configs/{self.MAP_FILE_NAME}.json")
