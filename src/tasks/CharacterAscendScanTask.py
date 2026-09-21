import re

from src.tasks.BaseNTETask import BaseNTETask
from src.tasks.NTEOneTimeTask import NTEOneTimeTask
from src.utils.result_config import ResultConfig


class CharacterAscendScanTask(NTEOneTimeTask, BaseNTETask):
    """Read the Ascend screen for characters in the C menu.

    Character Builder groundwork. The game itself holds the whole chain the builder
    needs: Ascend lists the required materials with have/need counts, and clicking a
    material shows a Source line such as 'Anomaly Hunt "Headless Rider"'. That removes
    the need for scraped build data and for a hand written material-to-domain table.

    By default it reads the character currently open in the C menu. With Scan All
    Characters on, it opens the character grid and reads every owned character in turn.
    Results are saved to configs/CharacterAscendMap.json.

    Clicks: C, the grid button and grid cells, Esc to close the grid (Ascend cannot be
    pressed while it is open), the Ascend button, each material icon to open its popup
    (closed again with Esc), and the Ascend page's back arrow. It never
    clicks a control that spends resources. The Ascend screen carries a confirm button
    and a Material Conversion button below the cost row; icon clicks are derived from
    each material's own count box, so they can only land on the icon row. Characters
    below their level cap show Level Up instead of Ascend, and that button is never
    clicked.

    Material Conversion is never used. It turns an inventory item into the materials an
    ascension needs, but the Character Builder farms raw materials instead, so each
    material's shortfall is recorded as "deficit" for farming to cover.
    """

    # C menu, character detail page.
    MENU_SIDEBAR_BOX = (0.03, 0.18, 0.28, 0.70)
    CHARACTER_NAME_BOX = (0.66, 0.16, 0.90, 0.23)
    # "Lvl: 70/70" under the name: level and cap of whoever is actually selected. The grid
    # badge is not used for this, since after a grid restore the badge clicked and the
    # character selected can differ; a live run recorded Chiz (Lvl 40) as level 70.
    LEVEL_PANEL_BOX = (0.66, 0.27, 0.78, 0.35)
    LEVEL_PANEL_MATCH = re.compile(r"(\d{1,2})\s*/\s*(\d{1,2})")
    ASCEND_BUTTON_BOX = (0.66, 0.87, 0.93, 0.96)
    # Ascend screen, right hand panel.
    ASCEND_PANEL_BOX = (0.66, 0.20, 1.0, 0.95)
    COST_BOX = (0.68, 0.60, 0.96, 0.78)
    # Back arrow on the Ascend page. On the info page the same spot is the X that closes
    # the whole C menu, so it is only clicked after the Ascend page is confirmed.
    BACK_BUTTON = (0.954, 0.058)
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
    # "Open Material Selection Box" only says a box can be opened for it; the drop that
    # actually farms the item is listed after it.
    SELECTION_BOX_MATCH = re.compile(r"Material\s*Selection\s*Box|自选")
    # A long description pushes the Source list past the popup's visible edge, where it
    # scrolls; the popup body is scrolled here to bring it up.
    POPUP_SCROLL_POS = (0.50, 0.65)
    POPUP_SCROLL_STEPS = 5
    # The popup's own chrome, which sits above the real item name.
    # OCR has read the header as "ltem", so the first letter is loose.
    POPUP_HEADER_MATCH = re.compile(r"^[IlL1|]tem$|^物品$|Growth\s*Material|成长材料")
    # The name sits in the same column as the owned count below it (x~910 vs ~925),
    # right of the "NEVERNESS TO EVERNESS" ring text around the icon (x~810-893).
    NAME_COLUMN_SLACK = 25
    # Header tokens on one line can differ in y by a few pixels.
    HEADER_ROW_TOLERANCE = 20
    # Owned quantity shown in the popup, e.g. "x27"; cross-checks the cost row.
    OWNED_MATCH = re.compile(r"^[x×]\s*(\d+)$")
    # Text that only appears on the Ascend page.
    ASCEND_PAGE_MATCH = re.compile(r"^Cost$|Ascend\s*Max|花费")
    # Characters below their level cap show Level Up instead of Ascend: they need EXP,
    # not ascension materials. Never clicked.
    LEVEL_UP_MATCH = re.compile(r"Level\s*Up|升级")
    CREDITS_MATCH = re.compile(r"[x×]\s*(\d{4,})")
    CAP_MATCH = re.compile(r"Max\s*Lvl\s*(\d+)")
    NEXT_CAP_MATCH = re.compile(r"[》»>]+\s*(\d+)")
    RESULT_FILE = "CharacterAscendMap"

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
    # Columns sit ~180px (0.094) apart; badge centres within one column wander by a
    # few pixels, and rounding them split one column in two on a live run.
    GRID_COLUMN_TOLERANCE = 0.03

    PANEL_TIMEOUT = 10
    SETTLE = 1.2

    CONF_SCAN_ROSTER = "扫描全部角色"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "角色突破扫描"
        self.description = "读取当前角色的突破材料需求, 只读取不消耗材料"
        self.default_config.update({self.CONF_SCAN_ROSTER: False})
        self.config_description.update(
            {self.CONF_SCAN_ROSTER: "打开角色网格, 依次读取每个角色的突破需求"}
        )
        self.ascend_map = None

    def on_create(self):
        self.ascend_map = ResultConfig(self.RESULT_FILE)

    def run(self):
        super().run()
        return self.do_run()

    def do_run(self) -> bool:
        self.ensure_main()

        if not self._open_character_menu():
            return False

        if self.config.get(self.CONF_SCAN_ROSTER):
            return self._scan_roster()

        name = self._read_character_name()
        self.log_info(f"当前角色: {name}")
        self.info_set("当前角色", name or "未知")
        record = self._scan_selected_character(name)
        self._save_record(record)
        return record["status"] == "ascend"

    # --- parsing helpers, pure so they can be tested without the game

    @classmethod
    def parse_ascend_header(cls, boxes: list) -> tuple:
        """Current and next level cap from the "Ascend Max Lvl60 》70" header row.

        Read by position: the arrow can come back as its own token with the number split
        off, and the stat rows below carry bare arrows too, so the next cap is the first
        number to the right of "Max Lvl" on the same row.
        """
        header = next((b for b in boxes if cls.CAP_MATCH.search(b.name or "")), None)
        if header is None:
            return None, None
        cap = int(cls.CAP_MATCH.search(header.name).group(1))
        if found := cls.NEXT_CAP_MATCH.search(header.name):
            return cap, int(found.group(1))
        row = sorted(
            (b for b in boxes
             if b is not header and b.x > header.x
             and abs(b.y - header.y) <= cls.HEADER_ROW_TOLERANCE),
            key=lambda b: b.x,
        )
        for box in row:
            digits = re.sub(r"\D", "", box.name or "")
            if digits:
                return cap, int(digits)
        return cap, None

    @classmethod
    def parse_credits(cls, texts: list):
        for text in texts:
            if found := cls.CREDITS_MATCH.search(text):
                return int(found.group(1))
        return None

    @classmethod
    def badge_click_point(cls, badge, screen_w: int, screen_h: int) -> tuple:
        """Relative click point for a level badge: its centre, nudged up onto the portrait."""
        x = (badge.x + badge.width / 2) / screen_w
        y = (badge.y + badge.height / 2) / screen_h - cls.BADGE_TO_PORTRAIT
        return x, y

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

    # --- one character

    @classmethod
    def is_safe_to_click(cls, text: str) -> bool:
        """Refuse any text-located click on Material Conversion.

        The task's only text-located click is the info page's Ascend button; this guard
        makes sure a future change cannot turn that into a conversion.
        """
        return not cls.CONVERSION_MATCH.search(text or "")

    @staticmethod
    def material_deficit(have: int, need: int) -> int:
        """Raw units still to farm. Conversion is never counted towards this."""
        return max(0, need - have)

    @classmethod
    def parse_level_panel(cls, texts: list) -> tuple:
        """Level and level cap from the detail panel's "Lvl: 70/70"."""
        for text in texts:
            if found := cls.LEVEL_PANEL_MATCH.search(text):
                return int(found.group(1)), int(found.group(2))
        return None, None

    def _scan_selected_character(self, name) -> dict:
        """Summarise the selected character, then read its Ascend page if it has one."""
        record = self._summarise_selected(name)
        if record["status"] == "ascend":
            record = self._ascend_scan(record)
        return record

    def _summarise_selected(self, name) -> dict:
        """Level, level cap and which button the selected character shows. Clicks nothing.

        Readable with the grid open, so a roster survey never has to leave the grid.
        Status is "ascend" when the Ascend button shows (materials still to be read),
        "level_up" below the level cap, otherwise "unknown".
        """
        record = {"name": name, "level": None, "status": "unknown", "cap": None,
                  "next_cap": None, "credits": None, "materials": []}
        level_texts = [(b.name or "").strip()
                       for b in self.ocr(*self.LEVEL_PANEL_BOX, name="level_panel") or []]
        record["level"], record["cap"] = self.parse_level_panel(level_texts)
        texts = [(b.name or "").strip()
                 for b in self.ocr(*self.ASCEND_BUTTON_BOX, name="ascend_button") or []]
        if any(self.ASCEND_MATCH.search(text) for text in texts):
            record["status"] = "ascend"
        elif any(self.LEVEL_UP_MATCH.search(text) for text in texts):
            record["status"] = "level_up"
        else:
            self.log_info(f"[{name}] 没有 Ascend 或 Level Up 按钮: {texts}")
        return record

    def _ascend_scan(self, record: dict) -> dict:
        """Open the selected character's Ascend page, read every material, go back.

        The Ascend button cannot be pressed while the grid is open, so the grid is closed
        with Esc first, which returns to the info page with the same character selected.
        """
        name = record["name"]
        if self._grid_is_open() and not self._close_grid():
            record["status"] = "unknown"
            return record
        buttons = self.ocr(*self.ASCEND_BUTTON_BOX, name="ascend_button") or []
        ascend = next((b for b in buttons if self.ASCEND_MATCH.search((b.name or "").strip())),
                      None)
        if ascend is None:
            self.log_warning(f"[{name}] 关闭网格后未找到 Ascend 按钮")
            record["status"] = "unknown"
            return record
        if not self.is_safe_to_click(ascend.name):
            self.log_error(f"[{name}] 拒绝点击: {ascend.name}")
            record["status"] = "unknown"
            return record
        self.click_box(ascend)
        self.sleep(self.SETTLE)
        entries = self._report_region("ascend_panel", self.ASCEND_PANEL_BOX)
        panel_texts = [(b.name or "").strip() for b in entries]
        if not any(self.ASCEND_PAGE_MATCH.search(text) for text in panel_texts):
            # Without confirming the page, the back arrow's spot could be the info page's
            # X, which closes the whole menu; reopening the grid recovers from either.
            self.screenshot("ascend_page_not_open")
            self.log_warning(f"[{name}] 点击 Ascend 后未识别到突破页面")
            record["status"] = "unknown"
            return record

        header_cap, record["next_cap"] = self.parse_ascend_header(entries)
        record["cap"] = record["cap"] or header_cap
        record["credits"] = self.parse_credits(panel_texts)
        # The narrow cost box reads the small "0/6" glyphs reliably; the wide panel
        # region misread the same text as "016", so prefer the narrow one.
        costs = self._report_region("cost", self.COST_BOX)
        count_boxes = self._count_boxes(costs or entries)
        record["materials"] = [
            self._inspect_material(i, b) for i, b in enumerate(count_boxes, 1)
        ]
        for m in record["materials"]:
            self.log_info(
                f"  [{name}] {m['name']} 拥有 {m['have']}/需要 {m['need']} 来源={m['sources']}"
            )
        self._leave_ascend_page()
        return record

    def _leave_ascend_page(self) -> bool:
        """Return from the Ascend page to the character info page via the back arrow."""
        self.operate_click(*self.BACK_BUTTON)
        found = self.wait_until(
            lambda: self.ocr(*self.MENU_SIDEBAR_BOX, match=self.SIDEBAR_MATCH, name="c_sidebar"),
            time_out=self.PANEL_TIMEOUT,
        )
        if not found:
            self.screenshot("ascend_back_failed")
            self.log_warning("返回角色信息页失败")
        return bool(found)

    def _save_record(self, record: dict) -> None:
        if self.ascend_map is None or not record.get("name"):
            return
        self.ascend_map[record["name"]] = dict(record)

    # --- roster through the character grid

    def _grid_is_open(self) -> bool:
        found = self.ocr(*self.GRID_LIST_LABEL_BOX, match=self.GRID_LIST_MATCH, name="grid_list")
        return bool(found)

    def _grid_badges(self) -> list:
        boxes = self.ocr(*self.GRID_PANEL_BOX, name="grid_badges") or []
        badges = [b for b in boxes if self.LEVEL_BADGE_MATCH.search((b.name or "").strip())]
        return sorted(badges, key=lambda b: (round(b.y / 40), b.x))

    def _close_grid(self) -> bool:
        """Close the grid with Esc, which keeps the C menu open on the selected character.

        Only sent while the grid is confirmed open: on the info page Esc would close the
        whole C menu instead.
        """
        self.send_key("esc", after_sleep=1.0)
        closed = self.wait_until(
            lambda: not self._grid_is_open()
            and self.ocr(*self.MENU_SIDEBAR_BOX, match=self.SIDEBAR_MATCH, name="c_sidebar"),
            time_out=self.PANEL_TIMEOUT,
        )
        if not closed:
            self.screenshot("roster_grid_close_failed")
            self.log_warning("Esc 未能关闭角色网格")
        return bool(closed)

    def _open_grid(self) -> bool:
        if self._grid_is_open():
            return True
        if not self.ocr(*self.MENU_SIDEBAR_BOX, match=self.SIDEBAR_MATCH, name="c_sidebar"):
            if not self._open_character_menu():
                return False
        self.operate_click(*self.GRID_BUTTON)
        if not self.wait_until(self._grid_is_open, time_out=self.PANEL_TIMEOUT):
            self.screenshot("roster_no_grid")
            self.log_error("未能打开角色网格")
            return False
        return True

    def _scroll_grid_to_end(self, up: bool) -> None:
        steps = self.GRID_TO_TOP_STEPS if up else -self.GRID_TO_TOP_STEPS
        for _ in range(self.GRID_TO_TOP_SCROLLS):
            self.operate(
                lambda: self.scroll_relative(*self.GRID_SCROLL_POS, steps), block=True
            )
            self.sleep(0.4)
        self.sleep(self.SETTLE)

    def _scroll_grid_down(self) -> None:
        self.operate(
            lambda: self.scroll_relative(*self.GRID_SCROLL_POS, -self.GRID_SCROLL_STEPS),
            block=True,
        )
        self.sleep(self.SETTLE)

    # Grid position of a surveyed cell: down-scrolls from the top, or the bottom of the list.
    BOTTOM = "bottom"

    def _go_to_position(self, position) -> bool:
        """Open the grid and scroll to a surveyed position.

        The grid reopens at the top, so replaying the same scrolls reproduces the layout
        the cell was surveyed in.
        """
        if not self._open_grid():
            return False
        self._scroll_grid_to_end(up=True)
        if position == self.BOTTOM:
            self._scroll_grid_to_end(up=False)
        else:
            for _ in range(position):
                self._scroll_grid_down()
        return True

    def _survey_points(self, points: list, labels: list, position, seen: list,
                       cells: list):
        """Select each point once and summarise new characters; the grid stays open.

        Returns how many new characters were found, or None if the grid closed.
        """
        new = 0
        for point, label in zip(points, labels):
            if not self._grid_is_open():
                self.screenshot("roster_grid_closed")
                self.log_warning("网格已关闭, 停止以免点到左侧菜单")
                return None
            # A point between portraits selects nothing and the name simply repeats.
            self.operate_click(*point)
            self.sleep(self.SETTLE)
            name = self._read_character_name()
            if not name or name in seen:
                continue
            seen.append(name)
            record = self._summarise_selected(name)
            self._save_record(record)
            cells.append({"record": record, "point": point, "position": position})
            self.log_info(f"[grid] {name} ({label}) {record['status']}")
            new += 1
        return new

    def _survey_grid(self) -> list:
        """First pass: select every character once, reading what shows with the grid open.

        Each character's cell is recorded with the scroll position it was found at, so
        the second pass can go straight back to it instead of re-selecting everything.
        """
        self._scroll_grid_to_end(up=True)
        cells, seen = [], []
        position = 0
        for page in range(self.GRID_MAX_PAGES):
            # The List label can render before the portraits finish animating in, so
            # wait for badges rather than reading once.
            badges = self.wait_until(self._grid_badges, time_out=self.PANEL_TIMEOUT) or []
            self.log_info(f"[grid] page {page + 1} ({position}): {len(badges)} badges")
            if not badges:
                self.screenshot(f"roster_no_badges_{page + 1}")
                for box in self.ocr(*self.GRID_PANEL_BOX, name="grid_raw") or []:
                    self.log_info(f"[grid raw] {box.name!r} @ x={box.x} y={box.y}")
            points = [self.badge_click_point(b, self.screen_width, self.screen_height)
                      for b in badges]
            labels = [b.name.strip() for b in badges]
            new = self._survey_points(points, labels, position, seen, cells)
            if new is None:
                break
            if position == self.BOTTOM:
                # At the end the last row sits clipped under the edge with its badges
                # hidden, so its portraits are clicked in the columns found above.
                columns = self.grid_columns(badges, self.screen_width, self.screen_height)
                self.log_info(f"[grid] 读取底部被遮挡的一行, {len(columns)} 列")
                partial = [(x, self.GRID_PARTIAL_ROW_Y) for x in columns]
                self._survey_points(partial, ["底部一行"] * len(partial), self.BOTTOM,
                                    seen, cells)
                break
            if new == 0:
                # A short scroll can move less than a row and expose nothing new, so an
                # empty page does not prove the end. Jump to the bottom and read it.
                self._scroll_grid_to_end(up=False)
                position = self.BOTTOM
                continue
            self._scroll_grid_down()
            position += 1
        return cells

    def _revisit(self, cell: dict) -> bool:
        """Second pass: select a surveyed character again by its recorded cell.

        The name is checked after the click. If the layout drifted, the cells on that
        page are tried in turn until the name matches.
        """
        target = cell["record"]["name"]
        if not self._go_to_position(cell["position"]):
            return False
        candidates = [cell["point"]]
        tried_page = False
        while candidates:
            point = candidates.pop(0)
            if not self._grid_is_open():
                self.log_warning("网格已关闭, 停止以免点到左侧菜单")
                return False
            self.operate_click(*point)
            self.sleep(self.SETTLE)
            if self._read_character_name() == target:
                return True
            if not tried_page:
                tried_page = True
                self.log_warning(f"[grid] 未能直接选中 {target}, 在当前页查找")
                badges = self._grid_badges()
                candidates = [self.badge_click_point(b, self.screen_width, self.screen_height)
                              for b in badges]
                if cell["position"] == self.BOTTOM:
                    columns = self.grid_columns(badges, self.screen_width, self.screen_height)
                    candidates += [(x, self.GRID_PARTIAL_ROW_Y) for x in columns]
        self.log_error(f"[grid] 未能重新选中 {target}")
        return False

    def _scan_roster(self) -> bool:
        """Read every owned character through the character grid, in two passes.

        The survey selects each character once without leaving the grid. Only characters
        that show Ascend are then revisited, each by its recorded cell, to read their
        materials. Re-selecting from the top after every Ascend page repeated most of the
        roster; this visits each cell at most twice.

        Before every click the grid is confirmed still open: it overlays the Arc /
        Console / Awaken / Esper Ability / Profile menu, so if it closed, the next clicks
        would land on those tabs.
        """
        if not self._open_grid():
            return False
        # A full pass replaces the file, so characters from an earlier or failed run
        # cannot linger alongside fresh ones.
        if self.ascend_map is not None:
            self.ascend_map.reset_to_default()

        cells = self._survey_grid()
        pending = [c for c in cells if c["record"]["status"] == "ascend"]
        self.log_info(f"[grid] 共 {len(cells)} 名角色, {len(pending)} 名需要读取突破材料")
        for cell in pending:
            if not self._revisit(cell):
                cell["record"]["status"] = "unknown"
                self._save_record(cell["record"])
                continue
            self._save_record(self._ascend_scan(cell["record"]))
        return self._finish_roster([c["record"]["name"] for c in cells])

    def _finish_roster(self, seen: list) -> bool:
        self.log_info(f"共 {len(seen)} 名角色: {seen}", notify=True)
        self.info_set("角色数量", len(seen))
        return bool(seen)

    # --- materials

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
        if self.sources_look_clipped(sources):
            sources = self._reread_sources(index, sources)
        owned = self._popup_owned(popup)
        self.send_key("esc", after_sleep=1.0)

        # The popup's owned count must match the cost row it was opened from; a mismatch
        # means the click landed on a different icon than the count came from.
        if owned is not None and owned != int(have):
            self.log_warning(
                f"[material {index}] 数量不一致: 成本行 {have} vs 弹窗 {owned}, 可能点错图标"
            )
        return {"index": index, "name": name, "have": int(have), "need": int(need),
                "deficit": self.material_deficit(int(have), int(need)),
                "owned": owned, "sources": sources}

    def _popup_name(self, boxes: list):
        """Item name: the lines in the owned count's column, above it, top to bottom.

        Taking the topmost plausible line returned the popup's "Item" header, the ring
        text around the icon ("NEVERNEER"), or only the first line of a wrapped name
        ("Charging Knight Spark" without "Plug"). The name always sits directly above the
        "x41" owned count, in its column, so that column is what is read.
        """
        boxes = boxes or []
        owned = next(
            (b for b in boxes if self.OWNED_MATCH.search((b.name or "").strip())), None
        )
        lines = [
            b for b in boxes
            if self.ITEM_NAME_MATCH.search((b.name or "").strip())
            and not self.POPUP_HEADER_MATCH.search((b.name or "").strip())
            and not self.CONVERSION_MATCH.search(b.name or "")
        ]
        if owned is not None:
            lines = [b for b in lines
                     if b.y < owned.y and b.x >= owned.x - self.NAME_COLUMN_SLACK]
            if lines:
                return " ".join(b.name.strip() for b in sorted(lines, key=lambda b: b.y))
            return None
        return min(lines, key=lambda b: b.y).name if lines else None

    def _popup_owned(self, boxes: list):
        """Owned count from the popup, used to confirm the right icon was opened."""
        for box in boxes or []:
            found = self.OWNED_MATCH.search((box.name or "").strip())
            if found:
                return int(found.group(1))
        return None

    @classmethod
    def sources_look_clipped(cls, sources: list) -> bool:
        """No farmable source read: nothing under Source, or only the selection box."""
        return all(cls.SELECTION_BOX_MATCH.search(s or "") for s in sources)

    def _reread_sources(self, index: int, sources: list) -> list:
        """Scroll the popup body down and read the Source list again, keeping order."""
        self.log_info(f"[material {index}] 来源可能被截断, 滚动弹窗后重读: {sources}")
        self.operate(
            lambda: self.scroll_relative(*self.POPUP_SCROLL_POS, -self.POPUP_SCROLL_STEPS),
            block=True,
        )
        self.sleep(self.SETTLE)
        again = self._popup_sources(
            self._report_region(f"item_{index}_scrolled", self.ITEM_POPUP_BOX)
        )
        return sources + [s for s in again if s not in sources]

    def _popup_sources(self, boxes: list) -> list:
        """Lines under the Source header, e.g. Anomaly Hunt "Headless Rider"."""
        header = next(
            (b for b in boxes or [] if self.SOURCE_HEADER_MATCH.search((b.name or "").strip())),
            None,
        )
        if header is None:
            return []
        return [b.name for b in boxes if b.y > header.y and (b.name or "").strip()]

    # --- navigation

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
        return boxes[0].name if boxes else None

    def _report_region(self, label: str, region: tuple) -> list:
        boxes = self.ocr(*region, name=label) or []
        if not boxes:
            self.log_info(f"[{label}] 未识别到文本, 区域 {region}")
            return []
        for box in boxes:
            self.log_info(f"[{label}] {box.name} @ x={box.x} y={box.y} w={box.width}")
        return boxes
