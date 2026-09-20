import re

from src.tasks.BaseNTETask import BaseNTETask
from src.tasks.NTEOneTimeTask import NTEOneTimeTask


class CharacterAscendScanTask(NTEOneTimeTask, BaseNTETask):
    """Read the Ascend screen for the character currently shown in the C menu.

    Character Builder groundwork. The game itself holds the whole chain the builder
    needs: Ascend lists the required materials with have/need counts, and clicking a
    material shows a Source line such as 'Anomaly Hunt "Headless Rider"'. That removes
    the need for scraped build data and for a hand written material-to-domain table.

    Slice 1 is deliberately narrow: open C, click Ascend, log what is on screen. It does
    not switch characters and does not open the per-material popups yet.

    It never clicks a confirm control. The Ascend screen carries a confirm button in the
    same place this task reads text from, and pressing it would consume materials, so
    the only clicks here are C, Ascend, and the back arrow.
    """

    # C menu, character detail page.
    MENU_SIDEBAR_BOX = (0.03, 0.18, 0.28, 0.70)
    CHARACTER_NAME_BOX = (0.66, 0.16, 0.90, 0.23)
    ASCEND_BUTTON_BOX = (0.66, 0.87, 0.93, 0.96)
    # Ascend screen, right hand panel.
    ASCEND_PANEL_BOX = (0.66, 0.20, 1.0, 0.95)
    COST_BOX = (0.68, 0.60, 0.96, 0.78)
    BACK_BUTTON_BOX = (0.93, 0.02, 1.0, 0.10)
    # Item popup opened by clicking a material icon.
    ITEM_POPUP_BOX = (0.33, 0.12, 0.68, 0.90)
    # The icon sits directly above its have/need count.
    ICON_OFFSET_ABOVE_COUNT = 0.055

    SIDEBAR_MATCH = re.compile(r"Info|Arc|Console|Awaken|Esper|Profile|信息|终端|觉醒|档案")
    ASCEND_MATCH = re.compile(r"^Ascend|突破|升阶")
    # "0/9" = have 0, need 9. "41/36" = have 41, need 36.
    HAVE_NEED_MATCH = re.compile(r"(\d+)\s*/\s*(\d+)")
    # Guards: these controls spend resources and must never be clicked by this task.
    CONFIRM_MATCH = re.compile(r"确认|确定|Confirm|^Ascend$")
    CONVERSION_MATCH = re.compile(r"Material\s*Conversion|材料转换")
    ITEM_NAME_MATCH = re.compile(r"^[A-Za-z][A-Za-z'\- ]{3,}$|[一-鿿]{2,}")
    SOURCE_HEADER_MATCH = re.compile(r"^Source$|^来源$")
    # The popup's own chrome, which sits above the real item name.
    POPUP_HEADER_MATCH = re.compile(r"^Item$|^物品$|Growth\s*Material|成长材料")
    # Owned quantity shown in the popup, e.g. "x27"; cross-checks the cost row.
    OWNED_MATCH = re.compile(r"^[x×]\s*(\d+)$")

    PANEL_TIMEOUT = 10
    SETTLE = 1.2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "角色突破扫描"
        self.description = "读取当前角色的突破材料需求, 只读取不消耗材料"

    def run(self):
        super().run()
        return self.do_run()

    def do_run(self) -> bool:
        self.ensure_main()

        if not self._open_character_menu():
            return False

        name = self._read_character_name()
        self.log_info(f"当前角色: {name}")
        self.info_set("当前角色", name or "未知")

        if not self._open_ascend_page():
            return False

        entries = self._report_region("ascend_panel", self.ASCEND_PANEL_BOX)
        # The narrow cost box reads the small "0/6" glyphs reliably; the wide panel
        # region misread the same text as "016", so prefer the narrow one.
        costs = self._report_region("cost", self.COST_BOX)
        count_boxes = self._count_boxes(costs or entries)
        if not count_boxes:
            self.screenshot("ascend_no_costs")
            self.log_warning("未读取到材料数量, 该角色可能已满级或界面被遮挡")
            return False

        materials = [self._inspect_material(i, b) for i, b in enumerate(count_boxes, 1)]
        self.screenshot("ascend_scan")
        for m in materials:
            self.log_info(
                f"  {m['name']} 拥有 {m['have']}/需要 {m['need']} 来源={m['sources']}"
            )
        self.log_info(f"扫描完成: {name}, {len(materials)} 种材料", notify=True)
        self.info_set("材料组数", len(materials))
        return True

    def _count_boxes(self, boxes: list) -> list:
        """Cost entries that carry a have/need count, left to right."""
        found = [b for b in boxes or [] if self.HAVE_NEED_MATCH.search(b.name or "")]
        return sorted(found, key=lambda b: b.x)

    def _inspect_material(self, index: int, count_box) -> dict:
        """Open one material's popup to read its name and sources, then close it.

        The icon is clicked at a point derived from its own count box, so the click can
        never stray onto the Ascend confirm or the Material Conversion button lower down.
        """
        have, need = self.HAVE_NEED_MATCH.search(count_box.name).groups()
        icon_x = (count_box.x + count_box.width / 2) / self.screen_width
        icon_y = count_box.y / self.screen_height - self.ICON_OFFSET_ABOVE_COUNT
        self.log_info(f"[material {index}] 点击图标 @ ({icon_x:.3f}, {icon_y:.3f})")
        self.operate_click(icon_x, icon_y)
        self.sleep(self.SETTLE)

        popup = self._report_region(f"item_{index}", self.ITEM_POPUP_BOX)
        name = self._popup_name(popup)
        sources = self._popup_sources(popup)
        owned = self._popup_owned(popup)
        self.send_key("esc", after_sleep=1.0)

        # The popup's owned count must match the cost row it was opened from; a mismatch
        # means the click landed on a different icon than the count came from.
        if owned is not None and owned != int(have):
            self.log_warning(
                f"[material {index}] 数量不一致: 成本行 {have} vs 弹窗 {owned}, 可能点错图标"
            )
        return {"index": index, "name": name, "have": int(have), "need": int(need),
                "owned": owned, "sources": sources}

    def _popup_name(self, boxes: list):
        """Item name is the topmost line that is not the popup's own chrome.

        The literal header "Item" renders above the name, so taking the topmost match
        outright returns "Item" for every material.
        """
        candidates = [
            b for b in boxes or []
            if self.ITEM_NAME_MATCH.search((b.name or "").strip())
            and not self.POPUP_HEADER_MATCH.search((b.name or "").strip())
            and not self.CONVERSION_MATCH.search(b.name or "")
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda b: b.y).name

    def _popup_owned(self, boxes: list):
        """Owned count from the popup, used to confirm the right icon was opened."""
        for box in boxes or []:
            found = self.OWNED_MATCH.search((box.name or "").strip())
            if found:
                return int(found.group(1))
        return None

    def _popup_sources(self, boxes: list) -> list:
        """Lines under the Source header, e.g. Anomaly Hunt "Headless Rider"."""
        header = next(
            (b for b in boxes or [] if self.SOURCE_HEADER_MATCH.search((b.name or "").strip())),
            None,
        )
        if header is None:
            return []
        return [b.name for b in boxes if b.y > header.y and (b.name or "").strip()]

    def _open_character_menu(self) -> bool:
        self.log_info("按 C 打开角色界面")
        found = self.wait_until(
            lambda: self.ocr(*self.MENU_SIDEBAR_BOX, match=self.SIDEBAR_MATCH, name="c_sidebar"),
            time_out=self.PANEL_TIMEOUT,
            pre_action=lambda: self.send_key("c", after_sleep=1.5),
        )
        if not found:
            self.screenshot("ascend_no_c_menu")
            self.log_error("未能打开角色界面, 请确认 C 是角色界面快捷键")
            return False
        self.sleep(self.SETTLE)
        return True

    def _read_character_name(self):
        boxes = self.ocr(*self.CHARACTER_NAME_BOX, name="character_name") or []
        for box in boxes:
            self.log_info(f"[name] {box.name} @ x={box.x} y={box.y}")
        return boxes[0].name if boxes else None

    def _open_ascend_page(self) -> bool:
        boxes = self.ocr(*self.ASCEND_BUTTON_BOX, match=self.ASCEND_MATCH, name="ascend_button")
        if not boxes:
            self.screenshot("ascend_no_button")
            self.log_error("未找到 Ascend 按钮")
            return False
        target = boxes[0] if isinstance(boxes, list) else boxes
        self.log_info(f"点击 {target.name}")
        self.click_box(target)
        self.sleep(self.SETTLE)
        return True

    def _extract_have_need(self, boxes: list) -> list:
        pairs = []
        for box in boxes or []:
            for have, need in self.HAVE_NEED_MATCH.findall(box.name or ""):
                pairs.append((int(have), int(need)))
        return pairs

    def _report_region(self, label: str, region: tuple) -> list:
        boxes = self.ocr(*region, name=label) or []
        if not boxes:
            self.log_info(f"[{label}] 未识别到文本, 区域 {region}")
            return []
        for box in boxes:
            self.log_info(f"[{label}] {box.name} @ x={box.x} y={box.y} w={box.width}")
        return boxes
