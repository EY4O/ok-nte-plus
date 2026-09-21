import unittest

from src.tasks.CharacterAscendScanTask import CharacterAscendScanTask


class TestAscendCostParsing(unittest.TestCase):
    def test_have_need_pairs(self):
        cases = {"0/6": ("0", "6"), "27/24": ("27", "24"), "120/240": ("120", "240")}
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(
                    CharacterAscendScanTask.HAVE_NEED_MATCH.search(text).groups(), expected
                )

    def test_item_name_accepts_names_and_rejects_counts(self):
        self.assertTrue(
            CharacterAscendScanTask.ITEM_NAME_MATCH.search("Charging Knight Spark Plug")
        )
        self.assertIsNone(CharacterAscendScanTask.ITEM_NAME_MATCH.search("27/24"))


class TestAscendClickSafety(unittest.TestCase):
    """The Ascend screen carries controls that spend resources.

    Hotori's scan put Material Conversion at y=947 and the cost counts at y=805. The
    material icon is clicked at a point derived from its own count box, so the click
    must always land on the icon row and never drift down onto those controls.
    """

    SCREEN_W, SCREEN_H = 1920, 1080
    # Real cost boxes read from the live Hotori scan.
    COST_BOXES = [(1405, 805, 36), (1521, 805, 54)]
    MATERIAL_CONVERSION_Y = 947
    ASCEND_CONFIRM_Y = 989

    def _click_point(self, x, y, width):
        cx = (x + width / 2) / self.SCREEN_W
        cy = y / self.SCREEN_H - CharacterAscendScanTask.ICON_OFFSET_ABOVE_COUNT
        return cx * self.SCREEN_W, cy * self.SCREEN_H

    def test_click_stays_clear_of_resource_spending_controls(self):
        for x, y, width in self.COST_BOXES:
            with self.subTest(count_x=x):
                _px, py = self._click_point(x, y, width)
                self.assertLess(py, self.MATERIAL_CONVERSION_Y - 40)
                self.assertLess(py, self.ASCEND_CONFIRM_Y - 40)

    def test_click_stays_inside_the_cost_panel(self):
        for x, y, width in self.COST_BOXES:
            with self.subTest(count_x=x):
                px, _py = self._click_point(x, y, width)
                self.assertTrue(1330 < px < 1820, f"x drifted outside the panel: {px}")

    def test_click_is_above_the_count_it_came_from(self):
        for x, y, width in self.COST_BOXES:
            with self.subTest(count_x=x):
                _px, py = self._click_point(x, y, width)
                self.assertLess(py, y)


class _Line:
    """Minimal stand-in for an OCR box: the parsers use .name, .x and .y."""

    def __init__(self, name, y, x=0):
        self.name = name
        self.y = y
        self.x = x


# Captured verbatim from a live Hotori scan, with real coordinates.
POPUP_PARADOXICAL = [
    _Line("Item", 190, 812),
    _Line("Paradoxical Whispers", 256, 910),
    _Line("×0", 384, 923),
    _Line("Growth Material", 474, 737),
    _Line("Substance left by Anomalies after", 526, 721),
    _Line("Character Ascension.", 581, 723),
    _Line("Source", 800, 712),
    _Line("Anomaly Drop", 847, 739),
]

POPUP_CONFESSIONAL = [
    _Line("Item", 190, 812),
    _Line("Confessional Flower Seed", 258, 914),
    _Line("EVERNESS", 336, 893),
    _Line("×27", 382, 927),
    _Line("Growth Material", 474, 737),
    _Line("Source", 744, 711),
    _Line("Open Material Selection Box", 796, 741),
    _Line('Anomaly Hunt"Serenetti"', 854, 740),
]

# From the live roster scan: ring text beside the icon, and a name wrapped over two lines.
POPUP_RING_TEXT = [
    _Line("Item", 190, 812),
    _Line("NEVERNEER", 236, 813),
    _Line("Blurred Silhouette", 258, 911),
    _Line("×94", 380, 925),
    _Line("Growth Material", 474, 737),
]
POPUP_SPLIT_RING = [
    _Line("Item", 188, 812),
    _Line("NEV", 257, 810),
    _Line("ERNESS", 257, 855),
    _Line("Nest Guard Fragment", 257, 910),
    _Line("EVERNES", 335, 893),
    _Line("×0", 382, 925),
]
POPUP_WRAPPED = [
    _Line("Item", 190, 812),
    _Line("Charging Knight Spark", 256, 917),
    _Line("Plug", 290, 917),
    _Line("×41", 384, 923),
]
POPUP_LTEM = [
    _Line("ltem", 190, 812),
    _Line("Charging Knight Spark", 256, 917),
    _Line("Plug", 290, 917),
    _Line("×41", 384, 923),
]


class TestAscendPopupParsing(unittest.TestCase):
    """The popup's own header "Item" renders above the real name.

    Taking the topmost matching line outright returned "Item" for every material.
    """

    def setUp(self):
        self.task = object.__new__(CharacterAscendScanTask)

    def test_name_skips_the_popup_header(self):
        self.assertEqual(self.task._popup_name(POPUP_PARADOXICAL), "Paradoxical Whispers")
        self.assertEqual(self.task._popup_name(POPUP_CONFESSIONAL), "Confessional Flower Seed")

    def test_name_skips_the_growth_material_tag(self):
        for popup in (POPUP_PARADOXICAL, POPUP_CONFESSIONAL):
            with self.subTest(popup=popup[1].name):
                self.assertNotEqual(self.task._popup_name(popup), "Growth Material")

    def test_owned_count_is_read_for_cross_checking(self):
        self.assertEqual(self.task._popup_owned(POPUP_PARADOXICAL), 0)
        self.assertEqual(self.task._popup_owned(POPUP_CONFESSIONAL), 27)

    def test_sources_are_the_lines_below_the_source_header(self):
        self.assertEqual(self.task._popup_sources(POPUP_PARADOXICAL), ["Anomaly Drop"])
        self.assertEqual(
            self.task._popup_sources(POPUP_CONFESSIONAL),
            ["Open Material Selection Box", 'Anomaly Hunt"Serenetti"'],
        )

    def test_description_text_is_not_mistaken_for_a_source(self):
        sources = self.task._popup_sources(POPUP_PARADOXICAL)
        self.assertNotIn("Substance left by Anomalies after", sources)



class TestRosterGrid(unittest.TestCase):
    """Level badges are the grid's text anchors; clicks derive from them."""

    W, H = 1920, 1080

    def test_level_badges_are_recognised(self):
        # Includes a stray trailing glyph, as OCR can read the adjacent element icon.
        for text in ("Lvl 50", "LvL 20", "Lvl 1", "Lv 70", "Lvl.40", "Lvl 50 6", "LvL50"):
            with self.subTest(text=text):
                self.assertTrue(CharacterAscendScanTask.LEVEL_BADGE_MATCH.search(text))

    def test_other_grid_text_is_not_a_badge(self):
        for text in ("List", "Level", "Refia", "Lvl: 70/70"):
            with self.subTest(text=text):
                self.assertIsNone(CharacterAscendScanTask.LEVEL_BADGE_MATCH.search(text))

    def test_click_lands_on_the_portrait_inside_the_grid_panel(self):
        # "Lvl 50" badge of the first full row, measured from a capture.
        badge = _Box(x=100, y=242, width=56, height=26, name="Lvl 50")
        x, y = CharacterAscendScanTask.badge_click_point(badge, self.W, self.H)
        left, top, right, bottom = CharacterAscendScanTask.GRID_PANEL_BOX
        self.assertTrue(left < x < right)
        self.assertTrue(top < y < bottom)
        self.assertLess(y * self.H, badge.y, "click should sit above the badge, on the portrait")


    def test_partial_last_row_click_sits_on_the_visible_sliver(self):
        # At the end of the list the clipped row shows only y~745-815 above the panel edge.
        y = CharacterAscendScanTask.GRID_PARTIAL_ROW_Y * self.H
        self.assertTrue(745 < y < 815, f"click at y={y:.0f} misses the visible sliver")
        left, top, right, bottom = CharacterAscendScanTask.GRID_PANEL_BOX
        self.assertTrue(top < CharacterAscendScanTask.GRID_PARTIAL_ROW_Y < bottom)

    def test_columns_come_from_the_badges(self):
        # Three badges per row at x~127/307/487, across two rows.
        badges = [
            _Box(x=100, y=660, width=56, height=26, name="Lvl 1"),
            _Box(x=280, y=660, width=56, height=26, name="Lvl 1"),
            _Box(x=460, y=660, width=56, height=26, name="Lvl 1"),
            _Box(x=100, y=465, width=56, height=26, name="Lvl 30"),
            _Box(x=281, y=465, width=56, height=26, name="Lvl 20"),
        ]
        columns = CharacterAscendScanTask.grid_columns(badges, self.W, self.H)
        self.assertEqual(len(columns), 3)
        self.assertEqual(columns, sorted(columns))

    def test_jitter_within_a_column_does_not_split_it(self):
        # Centres straddling a rounding boundary produced 4 columns on a live run.
        badges = [
            _Box(x=x, y=y, width=w, height=26, name="Lvl 1")
            for x, y, w in [(100, 660, 56), (104, 465, 50), (98, 270, 60),
                            (280, 660, 56), (286, 465, 48),
                            (460, 660, 56), (455, 270, 62)]
        ]
        self.assertEqual(len(CharacterAscendScanTask.grid_columns(badges, self.W, self.H)), 3)


class _Box:
    def __init__(self, x, y, width, height, name):
        self.x, self.y, self.width, self.height, self.name = x, y, width, height, name

# Text captured from a live Hotori Ascend page, and from a character info page.
ASCEND_PAGE_TEXT = ["Ascend Max Lvl60", "\u300b70", "HP", "11864", "12928", "Cost",
                    "0/6", "27/24", "Requires", "\u00d7125000", "Material Conversion"]
INFO_PAGE_TEXT = ["Info", "Arc", "Console", "Awaken", "Esper Ability", "Profile", "Refia",
                  "Cosmos", "Lvl: 70/70", "Attributes", "Effects", "HP", "21066", "Ascend"]


class TestAscendPageRecognition(unittest.TestCase):
    """The back arrow on the Ascend page sits where the info page's X closes the menu.

    It is only clicked after the Ascend page is recognised, so recognition must hold on
    the Ascend page and must not fire on the info page.
    """

    def test_ascend_page_is_recognised(self):
        self.assertTrue(
            any(CharacterAscendScanTask.ASCEND_PAGE_MATCH.search(t) for t in ASCEND_PAGE_TEXT)
        )

    def test_info_page_is_not_mistaken_for_the_ascend_page(self):
        self.assertFalse(
            any(CharacterAscendScanTask.ASCEND_PAGE_MATCH.search(t) for t in INFO_PAGE_TEXT)
        )

    def test_header_gives_current_and_next_cap(self):
        boxes = [_Line("Ascend Max Lvl60", 270, 1375), _Line("》70", 271, 1616)]
        self.assertEqual(CharacterAscendScanTask.parse_ascend_header(boxes), (60, 70))

    def test_credits_are_read_and_counts_are_not_mistaken_for_them(self):
        self.assertEqual(CharacterAscendScanTask.parse_credits(ASCEND_PAGE_TEXT), 125000)
        self.assertIsNone(CharacterAscendScanTask.parse_credits(["0/6", "27/24", "x27"]))


class TestAscendButton(unittest.TestCase):
    """Below the level cap the button reads Level Up, which must never be clicked."""

    def test_ascend_button_matches(self):
        self.assertTrue(CharacterAscendScanTask.ASCEND_MATCH.search("Ascend"))

    def test_level_up_is_not_taken_for_ascend(self):
        self.assertIsNone(CharacterAscendScanTask.ASCEND_MATCH.search("Level Up"))
        self.assertTrue(CharacterAscendScanTask.LEVEL_UP_MATCH.search("Level Up"))


class TestLevelPanel(unittest.TestCase):
    """Level is read from the selected character's panel, not from the clicked badge.

    After a grid restore the badge clicked and the character selected can differ; a live
    run recorded Chiz, shown as Lvl 40 in the grid, as level 70.
    """

    def test_level_and_cap(self):
        cases = {"Lvl: 70/70": (70, 70), "Lvl: 1/20": (1, 20), "Lvl:40/40": (40, 40)}
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(CharacterAscendScanTask.parse_level_panel([text]), expected)

    def test_missing_level_gives_none(self):
        self.assertEqual(CharacterAscendScanTask.parse_level_panel(["Refia"]), (None, None))


class TestNoMaterialConversion(unittest.TestCase):
    """Material Conversion is never used; the builder farms raw materials instead."""

    def test_conversion_is_refused(self):
        for text in ("Material Conversion", "Material  Conversion", "\u6750\u6599\u8f6c\u6362"):
            with self.subTest(text=text):
                self.assertFalse(CharacterAscendScanTask.is_safe_to_click(text))

    def test_the_ascend_button_is_allowed(self):
        self.assertTrue(CharacterAscendScanTask.is_safe_to_click("Ascend"))

    def test_deficit_is_the_raw_shortfall(self):
        # Hotori: 0/6 and 27/24.
        self.assertEqual(CharacterAscendScanTask.material_deficit(0, 6), 6)
        self.assertEqual(CharacterAscendScanTask.material_deficit(27, 24), 0)
        self.assertEqual(CharacterAscendScanTask.material_deficit(3, 9), 6)


class TestPopupNameColumn(unittest.TestCase):
    """Names are read from the owned count's column, joined across wrapped lines."""

    def setUp(self):
        self.task = object.__new__(CharacterAscendScanTask)

    def test_ring_text_beside_the_icon_is_ignored(self):
        self.assertEqual(self.task._popup_name(POPUP_RING_TEXT), "Blurred Silhouette")
        self.assertEqual(self.task._popup_name(POPUP_SPLIT_RING), "Nest Guard Fragment")

    def test_wrapped_name_is_joined(self):
        self.assertEqual(self.task._popup_name(POPUP_WRAPPED), "Charging Knight Spark Plug")

    def test_misread_header_is_not_the_name(self):
        self.assertEqual(self.task._popup_name(POPUP_LTEM), "Charging Knight Spark Plug")


class TestAscendHeaderRow(unittest.TestCase):
    """The next cap is read by position on the "Max Lvl" row."""

    def test_arrow_split_from_the_number(self):
        boxes = [_Line("Ascend Max Lvl70", 270, 1375), _Line("》", 271, 1620),
                 _Line("80", 272, 1650), _Line("》", 427, 1675), _Line("951", 422, 1702)]
        self.assertEqual(CharacterAscendScanTask.parse_ascend_header(boxes), (70, 80))

    def test_stat_rows_do_not_supply_the_next_cap(self):
        boxes = [_Line("Ascend Max Lvl70", 270, 1375), _Line("》", 427, 1675),
                 _Line("951", 422, 1702)]
        self.assertEqual(CharacterAscendScanTask.parse_ascend_header(boxes), (70, None))

    def test_merged_header(self):
        boxes = [_Line("Ascend Max Lvl70》80", 270, 1375)]
        self.assertEqual(CharacterAscendScanTask.parse_ascend_header(boxes), (70, 80))


class TestClippedSources(unittest.TestCase):
    """A Source list with no farmable drop is re-read after scrolling the popup."""

    def test_empty_or_selection_box_only_is_clipped(self):
        self.assertTrue(CharacterAscendScanTask.sources_look_clipped([]))
        self.assertTrue(CharacterAscendScanTask.sources_look_clipped(
            ["Open Material Selection Box"]))

    def test_a_real_drop_is_not_clipped(self):
        for sources in (["Anomaly Drop"],
                        ["Open Material Selection Box", "Anomaly Hunt: Sea Prisoner"]):
            with self.subTest(sources=sources):
                self.assertFalse(CharacterAscendScanTask.sources_look_clipped(sources))


if __name__ == "__main__":
    unittest.main()
