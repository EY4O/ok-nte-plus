import unittest

from src.tasks.AnomalyMaterialScanTask import AnomalyMaterialScanTask
from src.tasks.AnomalyTask import AnomalyTask


class TestAnomalyMaterialScan(unittest.TestCase):
    """The scanner borrows AnomalyTask's tab coordinates but not its methods.

    Calling AnomalyTask.click_task_type_tab() with the scanner as self raised
    AttributeError at runtime, because that method reads constants off its own class.
    """

    def test_every_task_type_resolves_to_a_tab_position(self):
        for task_type in AnomalyTask.TASK_TYPES:
            with self.subTest(task_type=task_type):
                position = AnomalyMaterialScanTask.tab_position(task_type)
                self.assertIsNotNone(position)
                x, y = position
                self.assertTrue(0 < x < 1, f"x out of range: {x}")
                self.assertTrue(0 < y < 1, f"y out of range: {y}")

    def test_unknown_task_type_returns_none(self):
        self.assertIsNone(AnomalyMaterialScanTask.tab_position("not a task type"))

    def test_tab_positions_are_distinct(self):
        positions = [
            AnomalyMaterialScanTask.tab_position(t) for t in AnomalyTask.TASK_TYPES
        ]
        self.assertEqual(len(set(positions)), len(positions))


if __name__ == "__main__":
    unittest.main()
