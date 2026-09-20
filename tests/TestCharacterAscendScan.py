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
    """Minimal stand-in for an OCR box: the parsers only use .name and .y."""

    def __init__(self, name, y):
        self.name = name
        self.y = y


# Captured verbatim from a live Hotori scan.
POPUP_PARADOXICAL = [
    _Line("Item", 190),
    _Line("Paradoxical Whispers", 256),
    _Line("×0", 384),
    _Line("Growth Material", 474),
    _Line("Substance left by Anomalies after", 526),
    _Line("Character Ascension.", 581),
    _Line("Source", 800),
    _Line("Anomaly Drop", 847),
]

POPUP_CONFESSIONAL = [
    _Line("Item", 190),
    _Line("Confessional Flower Seed", 258),
    _Line("×27", 382),
    _Line("Growth Material", 474),
    _Line("Source", 744),
    _Line("Open Material Selection Box", 796),
    _Line('Anomaly Hunt"Serenetti"', 854),
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


if __name__ == "__main__":
    unittest.main()
