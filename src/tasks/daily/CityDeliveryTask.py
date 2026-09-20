import re

from src.Labels import Labels
from src.tasks.BaseNTETask import BaseNTETask
from src.tasks.NTEOneTimeTask import NTEOneTimeTask


class CityDeliveryTask(NTEOneTimeTask, BaseNTETask):
    """City Delivery job scanner.

    Slice 2: reach the Daily Deliveries list, select every job in turn, and read the
    reward its detail panel shows. It ranks the jobs and logs the winner; it does not
    press Track, travel, or hand anything in.

    Rows are visited in their current scroll position. An earlier version re-scrolled to
    the top before each job and addressed rows by ordinal, which made every index past
    the first page collapse onto the last visible row.

    UI path: M -> Hethereau Hobbies (map bottom left) -> City Delivery.
    Coordinates below were measured from 1920x1080 captures of the real screens.
    """

    # Map screen: the hobbies button sits in the bottom-left corner.
    HOBBIES_PANEL_BOX = (0.0, 0.62, 0.30, 1.0)
    # The hobby roster is a centred grid, not a column.
    HOBBY_LIST_BOX = (0.10, 0.15, 0.95, 0.95)
    # Daily Deliveries list: panel spans x~120-580, y~165-965 on a 1920x1080 frame.
    JOB_LIST_BOX = (0.06, 0.15, 0.31, 0.90)
    # Detail panel only renders once a job is selected; before that this area shows the map.
    JOB_DETAIL_BOX = (0.72, 0.04, 1.0, 0.94)
    # Wheel anchor inside the job list.
    LIST_SCROLL_POS = (0.18, 0.55)
    # Wheel anchor inside the detail panel, which has its own scroll area: a long
    # description pushes the reward tile below the visible content and OCR cannot see it.
    PANEL_SCROLL_POS = (0.86, 0.55)
    PANEL_SCROLL_STEPS = 3
    SCROLL_TO_TOP_STEPS = 6
    SCROLL_PAGE_STEPS = 4

    HOBBIES_MATCH = re.compile(r"Hethereau|Hobb|海泽|赫瑟|爱好|嗜好")
    # OCR clipped this to "City De" when the region cut it off, so match the prefix.
    DELIVERY_MATCH = re.compile(r"City\s*De|Deliver|配送|快递|外送|运送")
    # Headers and counters that sit inside the list region but are not jobs.
    NON_JOB_MATCH = re.compile(r"Daily\s*Deliver|每日|^\d+$")
    # The headline payout tier. Must not also match "Professional Rating: (80-90)",
    # which sits below it with a smaller reward.
    RATING_90_MATCH = re.compile(r"90\s*\+")
    RECIPIENT_MATCH = re.compile(r"Recipient|收件人")
    GOODS_TYPE_MATCH = re.compile(r"Goods\s*Type|货物类型")
    STAMINA_COST_MATCH = re.compile(r"Stamina\s*Cost|体力消耗")
    DIGITS_MATCH = re.compile(r"\d[\d,\s]*")
    STAMINA_RANGE_MATCH = re.compile(r"(\d+)\s*[-~]\s*(\d+)")
    # Observed on every job: the 90+ payout equals the upper stamina bound x 1000.
    FONS_PER_STAMINA = 1000

    # A stray glyph rendered at the list's bottom edge was being read as a job row.
    MIN_TITLE_LENGTH = 4
    # Wrapped titles sit ~31px apart; separate rows ~94px apart.
    ROW_GROUP_TOLERANCE = 0.045
    # Reward tile renders ~104px below the 90+ label; the next tier label is ~165px below,
    # so keep the band between those.
    REWARD_BAND_HEIGHT = 0.12

    MAP_TIMEOUT = 15
    PANEL_TIMEOUT = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "城市配送"
        self.description = "扫描城市配送任务列表并按报酬排序, 只读取不接取"

    def run(self):
        super().run()
        return self.do_run()

    def do_run(self) -> bool:
        self.ensure_main()
        if not self._open_delivery_list():
            return False

        results = self._scan_all_jobs()
        if not results:
            self.screenshot("city_delivery_no_jobs")
            self.log_error("未能在列表中识别出任务行")
            return False

        self._report_results(results)
        self.screenshot("city_delivery_scan_done")
        return True

    def _open_delivery_list(self) -> bool:
        if not self.wait_until(
            lambda: self.find_one(Labels.map_city_tycoon_activities),
            time_out=self.MAP_TIMEOUT,
            pre_action=lambda: self.send_key("m", interval=2),
        ):
            self.log_error("未能打开地图")
            return False

        if not self._click_text(self.HOBBIES_PANEL_BOX, self.HOBBIES_MATCH, "Hethereau Hobbies"):
            self.screenshot("city_delivery_no_hobbies")
            self.log_error("未在地图左下角找到 Hethereau Hobbies")
            return False

        self.sleep(1.2)
        if not self._click_text(self.HOBBY_LIST_BOX, self.DELIVERY_MATCH, "City Delivery"):
            self.screenshot("city_delivery_no_entry")
            self.log_error("未在爱好列表中找到 City Delivery")
            return False

        self.sleep(1.5)
        return True

    def _scan_all_jobs(self) -> list:
        """Visit every job, scrolling once to reach the ones below the fold.

        Each row is clicked while it is on screen, so no index bookkeeping survives a
        scroll. Titles repeat, so the second page is joined to the first by longest
        sequence overlap rather than by de-duplicating names.
        """
        self._scroll_list(self.SCROLL_TO_TOP_STEPS)
        first_rows = self._row_boxes()
        first_titles = [self._row_title(row) for row in first_rows]
        self.log_info(f"列表首屏 {len(first_titles)} 项: {first_titles}")

        results = []
        for row, title in zip(first_rows, first_titles):
            results.append(self._inspect_row(len(results) + 1, title, row))

        self._scroll_list(-self.SCROLL_PAGE_STEPS)
        second_rows = self._row_boxes()
        second_titles = [self._row_title(row) for row in second_rows]
        if second_titles == first_titles:
            return results

        self.log_info(f"列表次屏 {len(second_titles)} 项: {second_titles}")
        overlap = self._sequence_overlap(first_titles, second_titles)
        self.log_info(f"次屏与首屏重叠 {overlap} 项, 新增 {len(second_titles) - overlap} 项")
        for row, title in zip(second_rows[overlap:], second_titles[overlap:]):
            results.append(self._inspect_row(len(results) + 1, title, row))
        return results

    @staticmethod
    def _sequence_overlap(first: list, second: list) -> int:
        for size in range(min(len(first), len(second)), 0, -1):
            if first[-size:] == second[:size]:
                return size
        return 0

    def _scroll_panel(self) -> None:
        x, y = self.PANEL_SCROLL_POS
        self.operate(lambda: self.scroll_relative(x, y, -self.PANEL_SCROLL_STEPS), block=True)
        self.sleep(0.6)

    def _reward_from_stamina(self, stamina):
        """Fallback when the reward tile cannot be read: upper bound x 1000."""
        if not stamina:
            return None
        found = self.STAMINA_RANGE_MATCH.search(stamina)
        if not found:
            return None
        return int(found.group(2)) * self.FONS_PER_STAMINA

    def _scroll_list(self, steps: int) -> None:
        x, y = self.LIST_SCROLL_POS
        self.operate(lambda: self.scroll_relative(x, y, steps), block=True)
        self.sleep(0.6)

    @staticmethod
    def _row_title(row: list) -> str:
        return " ".join(box.name for box in row)

    def _row_boxes(self) -> list:
        """Group job-list OCR lines into rows; a wrapped title stays one row."""
        boxes = self.ocr(*self.JOB_LIST_BOX, name="job_rows") or []
        jobs = [b for b in boxes if not self.NON_JOB_MATCH.search((b.name or "").strip())]
        if not jobs:
            return []

        tolerance = self.ROW_GROUP_TOLERANCE * self.screen_height
        rows = []
        for box in sorted(jobs, key=lambda b: b.y):
            if rows and abs(box.y - rows[-1][-1].y) <= tolerance:
                rows[-1].append(box)
            else:
                rows.append([box])
        return [row for row in rows if len(self._row_title(row).strip()) >= self.MIN_TITLE_LENGTH]

    def _inspect_row(self, index: int, title: str, row: list) -> dict:
        anchor = row[0]
        self.log_info(f"[job {index}] 选择 {title} @ y={anchor.y}")
        self.click_box(anchor)
        self.sleep(1.0)

        detail = self.ocr(*self.JOB_DETAIL_BOX, name=f"job_detail_{index}") or []
        # Read the labelled fields before any scroll, which would push them out of view.
        goods = self._value_beside(detail, self.GOODS_TYPE_MATCH)
        stamina = self._value_beside(detail, self.STAMINA_COST_MATCH)
        recipient = self._value_beside(detail, self.RECIPIENT_MATCH)

        reward = self._extract_reward(detail)
        if reward is None:
            # Long descriptions push the reward tile out of the panel's scroll area.
            self.log_info(f"[job {index}] 报酬未在首屏出现, 滚动详情面板后重试")
            self._scroll_panel()
            scrolled = self.ocr(*self.JOB_DETAIL_BOX, name=f"job_detail_{index}_scrolled") or []
            reward = self._extract_reward(scrolled)
            detail = detail + scrolled
        if reward is None:
            reward = self._reward_from_stamina(stamina)
            if reward is not None:
                self.log_warning(f"[job {index}] 报酬由体力上限推算得出: {reward}")
        # Logged so a repeated recipient exposes a selection that silently did not change.
        self.log_info(
            f"[job {index}] {title} 报酬={reward} 货物={goods} 体力={stamina} 收件人={recipient}"
        )
        if reward is None:
            for box in detail:
                self.log_info(f"[job {index} detail] {box.name} @ y={box.y} x={box.x}")
        return {
            "index": index,
            "title": title,
            "reward": reward,
            "goods": goods,
            "stamina": stamina,
            "recipient": recipient,
        }

    def _extract_reward(self, boxes: list):
        """Read the number under the Professional Rating (90+) tier."""
        tiers = [b for b in boxes if self.RATING_90_MATCH.search(b.name or "")]
        if not tiers:
            return None
        # Topmost match wins: the 90+ tier renders above the lower ones.
        label = min(tiers, key=lambda b: b.y)
        band = self.REWARD_BAND_HEIGHT * self.screen_height
        values = []
        for box in boxes:
            if not (label.y < box.y <= label.y + band):
                continue
            for raw in self.DIGITS_MATCH.findall(box.name or ""):
                digits = re.sub(r"[^0-9]", "", raw)
                if digits:
                    values.append(int(digits))
        return max(values) if values else None

    def _value_beside(self, boxes: list, pattern):
        """Value rendered on the same line as a label, to its right."""
        label = next((b for b in boxes if pattern.search(b.name or "")), None)
        if label is None:
            return None
        line_height = 0.02 * self.screen_height
        same_line = [
            b
            for b in boxes
            if b is not label and abs(b.y - label.y) < line_height and b.x > label.x
        ]
        return same_line[0].name if same_line else None

    def _report_results(self, results: list) -> None:
        for item in results:
            self.log_info(
                f"  #{item['index']} {item['title']} -> {item['reward']} "
                f"({item['goods']}, 体力 {item['stamina']}, {item['recipient']})"
            )
        scored = [item for item in results if item["reward"] is not None]
        if not scored:
            self.log_error("未能读取到任何报酬数字, 请反馈 job_detail 日志")
            return
        best = max(scored, key=lambda item: item["reward"])
        self.log_info(f"报酬最高: #{best['index']} {best['title']} = {best['reward']}", notify=True)
        self.info_set("最高报酬任务", best["title"])
        self.info_set("最高报酬", best["reward"])

    def _click_text(self, region: tuple, match, description: str) -> bool:
        found = self.wait_until(
            lambda: self.ocr(*region, match=match, name=description),
            time_out=self.PANEL_TIMEOUT,
        )
        if not found:
            return False
        target = found[0] if isinstance(found, list) else found
        self.log_info(f"点击 {description}: {target.name}")
        self.click_box(target)
        return True
