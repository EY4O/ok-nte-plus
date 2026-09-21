import json
import tempfile
import unittest
from pathlib import Path

from src.utils.result_config import ResultConfig


class TestResultConfig(unittest.TestCase):
    """Scan results survive being loaded again, as happens on every app start."""

    def test_saved_results_survive_a_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            first = ResultConfig("Map", folder=folder)
            first["Hotori"] = {"status": "ascend", "cap": 60}
            again = ResultConfig("Map", folder=folder)
            self.assertEqual(again["Hotori"], {"status": "ascend", "cap": 60})
            saved = json.loads((Path(folder) / "Map.json").read_text(encoding="utf-8"))
            self.assertIn("Hotori", saved)

    def test_reset_clears_the_file(self):
        with tempfile.TemporaryDirectory() as folder:
            results = ResultConfig("Map", folder=folder)
            results["Edgar"] = {"status": "ascend"}
            results.reset_to_default()
            self.assertEqual(dict(ResultConfig("Map", folder=folder)), {})


if __name__ == "__main__":
    unittest.main()
