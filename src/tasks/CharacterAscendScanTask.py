import re

from src.tasks.BaseNTETask import BaseNTETask
from src.tasks.NTEOneTimeTask import NTEOneTimeTask


class CharacterAscendScanTask(NTEOneTimeTask, BaseNTETask):
    """Read the Ascend screen for the character currently shown in the C menu.

    Character Builder groundwork. The game itself holds the whole chain the builder
    needs: Ascend lists the required materials with have/need counts, and clicking a
    material shows a Source line such as 'Anomaly Hunt "Headless Rider"'. That removes
    the need for scraped build data and for a hand written material-to-domain table.

    By default it reads the character currently open in the C menu. With Scan All
    Characters on, it instead opens the character grid and selects each character in
    turn, reading names only.

    Clicks: C, the Ascend button, and each material icon to open its popup, closed again
    with Esc; in roster mode, the grid button and each grid cell. It never clicks a
    control that spends resources. The Ascend screen carries a confirm button and a
    Material Conversion button below the cost row; icon clicks are derived from each
    material's own count box, so they can only land on the icon row.
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

    # Character grid, opened from the grid button at the bottom right of the C menu.
    # Every cell carries a "Lvl N" badge, which gives each character a text anchor; the
    # portrait strip had none, and after a scroll it stopped off its resting grid so
    # fixed click points landed in the gaps. Measured from a 1920x1080 capture.
    GRID_BUTTON = (0.957, 0.916)
    # Fully visible rows only: the partial row under the top edge is excluded.
    GRID_PANEL_BOX = (0.01, 0.08, 0.30, 0.78)
    # The grid's "List" tab; if it is gone the grid has closed.
    GRID_LIST_LABEL_BOX = (0.19, 0.79, 0.31, 0.87)
    GRID_LIST_MATCH = re.compile(r"^List$|列表")
    # No end anchor: each badge has an element icon beside it, which OCR can append as a
    # stray character. The colon in the detail panel's "Lvl: 70/70" still fails to match.
    LEVEL_BADGE_MATCH = re.compile(r"^L[vV][lL1I]?\.?\s*\d{1,2}(?!\d)")
    # The badge sits on the lower edge of the portrait; click a little above it.
    BADGE_TO_PORTRAIT = 0.04
    GRID_SCROLL_POS = (0.155, 0.45)
    GRID_SCROLL_STEPS = 3
    GRID_MAX_PAGES = 10
    # The grid opens scrolled to the current character, not to the top: a capture
    # showed a cut-off row above the first full one. Sorted by level those are the
    # highest-level characters, so scroll to the top before reading.
    GRID_TO_TOP_SCROLLS = 3
    GRID_TO_TOP_STEPS = 8
    # At the bottom of the list the last row stays clipped under the panel edge: its
    # portraits show at y~745-815 but the badges are hidden, leaving no text anchor.
    # Those portraits are clicked in the columns the badges above them establish.
    GRID_PARTIAL_ROW_Y = 0.725

    PANEL_TIMEOUT = 10
    SETTLE = 1.2

    CONF_SCAN_ROSTER = "扫描全部角色"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "角色突破扫描"
        self.description = "读取当前角色的突破材料需求, 只读取不消耗材料"
        self.default_config.update({self.CONF_SCAN_ROSTER: False})
        self.config_description.update(
            {self.CONF_SCAN_ROSTER: "打开角色网格, 依次选择每个角色并记录名称"}
        )

    def run(self):
        super().run()
        return self.do_run()

    def do_run(self) -> bool:
        self.ensure_main()

        if not self._open_character_menu():
            return False

        if self.config.get(self.CONF_SCAN_ROSTER):
            return self._scan_roster_names()

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

    @classmethod
    def badge_click_point(cls, badge, screen_w: int, screen_h: int) -> tuple:
        """Relative click point for a level badge: its centre, nudged up onto the portrait."""
        x = (badge.x + badge.width / 2) / screen_w
        y = (badge.y + badge.height / 2) / screen_h - cls.BADGE_TO_PORTRAIT
        return x, y

    def _grid_is_open(self) -> bool:
        found = self.ocr(*self.GRID_LIST_LABEL_BOX, match=self.GRID_LIST_MATCH, name="grid_list")
        return bool(found)

    def _grid_badges(self) -> list:
        boxes = self.ocr(*self.GRID_PANEL_BOX, name="grid_badges") or []
        badges = [b for b in boxes if self.LEVEL_BADGE_MATCH.search((b.name or "").strip())]
        return sorted(badges, key=lambda b: (round(b.y / 40), b.x))

    def _scan_roster_names(self) -> bool:
        """Open the character grid and select each unlocked character in turn.

        Reads names only, no Ascend. Before every click the grid is confirmed still open:
        it overlays the Arc / Console / Awaken / Esper Ability / Profile menu, so if
        selecting a character closed it, the next clicks would land on those tabs.
        """
        self.operate_click(*self.GRID_BUTTON)
        if not self.wait_until(self._grid_is_open, time_out=self.PANEL_TIMEOUT):
            self.screenshot("roster_no_grid")
            self.log_error("未能打开角色网格")
            return False

        self._scroll_grid_to_end(up=True)

        seen = []
        at_bottom = False
        for page in range(self.GRID_MAX_PAGES):
            # The List label can render before the portraits finish animating in, so
            # wait for badges rather than reading once.
            badges = self.wait_until(self._grid_badges, time_out=self.PANEL_TIMEOUT) or []
            self.log_info(f"[grid] page {page + 1}: {len(badges)} badges")
            if not badges:
                self.screenshot(f"roster_no_badges_{page + 1}")
                for box in self.ocr(*self.GRID_PANEL_BOX, name="grid_raw") or []:
                    self.log_info(f"[grid raw] {box.name!r} @ x={box.x} y={box.y}")
            new_on_page = 0
            for badge in badges:
                if not self._grid_is_open():
                    self.screenshot("roster_grid_closed")
                    self.log_warning("选择角色后网格已关闭, 停止以免点到左侧菜单")
                    return self._finish_roster(seen)
                self.operate_click(
                    *self.badge_click_point(badge, self.screen_width, self.screen_height)
                )
                self.sleep(self.SETTLE)
                name = self._read_character_name()
                if name and name not in seen:
                    seen.append(name)
                    new_on_page += 1
                    self.log_info(f"[grid] {name} ({badge.name.strip()})")
            if new_on_page == 0:
                # A short scroll can move less than a row and expose nothing new, so an
                # empty page does not prove the end. Jump to the bottom once and re-read.
                if not at_bottom:
                    self._scroll_grid_to_end(up=False)
                    at_bottom = True
                    continue
                # Truly at the end: the last row may still sit clipped under the edge.
                self._scan_partial_last_row(badges, seen)
                break
            self.operate(
                lambda: self.scroll_relative(*self.GRID_SCROLL_POS, -self.GRID_SCROLL_STEPS),
                block=True,
            )
            self.sleep(self.SETTLE)
            self.screenshot(f"roster_grid_after_scroll_{page + 1}")
        return self._finish_roster(seen)

    def _scroll_grid_to_end(self, up: bool) -> None:
        steps = self.GRID_TO_TOP_STEPS if up else -self.GRID_TO_TOP_STEPS
        for _ in range(self.GRID_TO_TOP_SCROLLS):
            self.operate(
                lambda: self.scroll_relative(*self.GRID_SCROLL_POS, steps), block=True
            )
            self.sleep(0.4)
        self.sleep(self.SETTLE)

    # Columns sit ~180px (0.094) apart; badge centres within one column wander by a
    # few pixels, and rounding them split one column in two on a live run.
    GRID_COLUMN_TOLERANCE = 0.03

    @classmethod
    def grid_columns(cls, badges: list, screen_w: int, screen_h: int) -> list:
        """Column x positions of the visible badges, left to right, one per column."""
        xs = sorted(cls.badge_click_point(b, screen_w, screen_h)[0] for b in badges)
        columns = []
        for x in xs:
            if columns and x - columns[-1][-1] <= cls.GRID_COLUMN_TOLERANCE:
                columns[-1].append(x)
            else:
                columns.append([x])
        return [sum(group) / len(group) for group in columns]

    def _scan_partial_last_row(self, badges: list, seen: list) -> None:
        columns = self.grid_columns(badges, self.screen_width, self.screen_height)
        self.log_info(f"[grid] 读取底部被遮挡的一行, {len(columns)} 列")
        for x in columns:
            if not self._grid_is_open():
                self.screenshot("roster_grid_closed")
                self.log_warning("选择角色后网格已关闭, 停止以免点到左侧菜单")
                return
            # A column with no character below it selects nothing and the name repeats.
            self.operate_click(x, self.GRID_PARTIAL_ROW_Y)
            self.sleep(self.SETTLE)
            name = self._read_character_name()
            if name and name not in seen:
                seen.append(name)
                self.log_info(f"[grid] {name} (底部一行)")

    def _finish_roster(self, seen: list) -> bool:
        self.log_info(f"共 {len(seen)} 名角色: {seen}", notify=True)
        self.info_set("角色数量", len(seen))
        return bool(seen)

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
        # C toggles the menu, and wait_until runs pre_action on every iteration, so an
        # unguarded press re-fires while the menu is still animating open and closes it.
        # Press once, then only again while the HUD health bar shows the player is still
        # in the world, as openF5panel does; with the menu up the HUD is gone.
        self.send_key("c", after_sleep=1.5)
        found = self.wait_until(
            lambda: self.ocr(*self.MENU_SIDEBAR_BOX, match=self.SIDEBAR_MATCH, name="c_sidebar"),
            time_out=self.PANEL_TIMEOUT,
            pre_action=lambda: self.is_in_team() and self.send_key("c", after_sleep=1.5),
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
