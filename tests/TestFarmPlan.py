import json
import tempfile
import unittest
from pathlib import Path

from src.builder import farm_plan as fp
from src.tasks.AnomalyHunter import AnomalyHunter as AH
from src.tasks.AnomalyTask import AnomalyTask as AT

# Records as saved by the live roster scan.
HOTORI = {"name": "Hotori", "status": "ascend", "materials": [
    {"name": "Paradoxical Whispers", "have": 0, "need": 6, "sources": ["Anomaly Drop"]},
    {"name": "Confessional Flower Seed", "have": 27, "need": 24,
     "sources": ["Open Material Selection Box", 'Anomaly Hunt"Serenetti"']},
]}
LACRIMOSA = {"name": "Lacrimosa", "status": "ascend", "materials": [
    {"name": "Paradoxical Whispers", "have": 0, "need": 6, "sources": ["Anomaly Drop"]},
    {"name": "Confessional Flower Seed", "have": 27, "need": 24,
     "sources": ["Open Material Selection Box", 'Anomaly Hunt "Serenetti"']},
]}
NANALLY = {"name": "Nanally", "status": "ascend", "materials": [
    {"name": "A Page from Delusion's Shore", "have": 0, "need": 36,
     "sources": ["Open Material Selection Box", 'Anomaly Hunt"Black Tome"']},
]}
JIUYUAN = {"name": "Jiuyuan", "status": "ascend", "materials": [
    {"name": "Blurred Silhouette", "have": 94, "need": 12, "sources": []},
    {"name": "Tear of the Sea", "have": 15, "need": 16,
     "sources": ["Open Material Selection Box", "Anomaly Hunt: Sea Prisoner"]},
]}
SKIA = {"name": "Skia", "status": "level_up", "materials": []}
LINKO = {"name": "Linko", "status": "level_up", "materials": []}


class TestParseSource(unittest.TestCase):
    def test_every_hunt_format_seen_in_game(self):
        cases = {
            'Anomaly Hunt "Headless Rider"': AH.TARGET_HEADLESS_RIDER,
            'Anomaly Hunt "Beat King"': AH.TARGET_SOUND_KING,
            'Anomaly Hunt"Serenetti"': AH.TARGET_SERENITY,
            'Anomaly Hunt "Serenetti"': AH.TARGET_SERENITY,
            'Anomaly Hunt"Black Tome"': AH.TARGET_BLACK_BOOK,
            "Anomaly Hunt: Sea Prisoner": AH.TARGET_SEA_PRISONER,
            "Anomaly Hunt: Nestbound Bird": AH.TARGET_NEST_BIRD,
            "Anomaly Hunt: Swallowtail": AH.TARGET_SPOTTED_BUTTERFLY,
        }
        for text, target in cases.items():
            with self.subTest(text=text):
                self.assertEqual(fp.parse_source(text), fp.Source(fp.KIND_HUNT, text, target))

    def test_ocr_misread_still_resolves(self):
        self.assertEqual(fp.parse_source('Anomaly Hunt "Headless Rlder"').target,
                         AH.TARGET_HEADLESS_RIDER)

    def test_unknown_hunt_is_not_guessed(self):
        self.assertEqual(fp.parse_source("Anomaly Hunt: Glass Leviathan").kind, fp.KIND_UNKNOWN)

    def test_non_task_sources(self):
        self.assertEqual(fp.parse_source("Anomaly Drop").kind, fp.KIND_ANOMALY_DROP)
        self.assertEqual(fp.parse_source("Open Material Selection Box").kind,
                         fp.KIND_SELECTION_BOX)
        self.assertEqual(fp.parse_source("Craft").kind, fp.KIND_CRAFT)

    def test_hunt_preferred_over_selection_box(self):
        best = fp.best_source(["Open Material Selection Box", "Anomaly Hunt: Sea Prisoner"])
        self.assertEqual(best.target, AH.TARGET_SEA_PRISONER)
        self.assertIsNone(fp.best_source([]))


class TestBuildPlan(unittest.TestCase):
    def _by_material(self, steps):
        return {s.material: s for s in steps if s.material}

    def test_hunt_material_gets_a_hunter_target(self):
        steps = self._by_material(fp.build_plan([NANALLY]))
        step = steps["A Page from Delusion's Shore"]
        self.assertEqual((step.task, step.deficit), ("AnomalyHunter", 36))
        self.assertEqual(step.config, {AH.CONF_HUNTER_TARGET: AH.TARGET_BLACK_BOOK})

    def test_covered_materials_are_left_out(self):
        steps = self._by_material(fp.build_plan([HOTORI]))
        self.assertNotIn("Confessional Flower Seed", steps)  # 27 of 24

    def test_anomaly_drop_is_reported_without_a_task(self):
        step = self._by_material(fp.build_plan([HOTORI]))["Paradoxical Whispers"]
        self.assertEqual((step.kind, step.task, step.deficit), (fp.KIND_ANOMALY_DROP, None, 6))

    def test_shared_inventory_is_counted_once(self):
        # Two characters each need 24 of the same seed, 27 owned: 21 short, not 0.
        steps = self._by_material(fp.build_plan([HOTORI, LACRIMOSA]))
        seed = steps["Confessional Flower Seed"]
        self.assertEqual(seed.deficit, 48 - 27)
        self.assertEqual(seed.characters, ["Hotori", "Lacrimosa"])
        self.assertEqual(seed.config, {AH.CONF_HUNTER_TARGET: AH.TARGET_SERENITY})
        self.assertEqual(steps["Paradoxical Whispers"].deficit, 12)

    def test_one_short_is_still_farmed(self):
        step = self._by_material(fp.build_plan([JIUYUAN]))["Tear of the Sea"]
        self.assertEqual(step.deficit, 1)
        self.assertEqual(step.config, {AH.CONF_HUNTER_TARGET: AH.TARGET_SEA_PRISONER})

    def test_level_up_characters_farm_character_exp(self):
        steps = fp.build_plan([SKIA, LINKO, NANALLY])
        exp = steps[-1]
        self.assertEqual((exp.kind, exp.task), (fp.KIND_EXP, "AnomalyTask"))
        self.assertEqual(exp.config, {AT.CONF_TASK_TYPE: AT.TASK_EXP_COIN,
                                      AT.CONF_EXP_TARGET: AT.EXP_CHAR})
        self.assertEqual(exp.characters, ["Skia", "Linko"])

    def test_config_values_are_valid_task_options(self):
        for step in fp.build_plan([HOTORI, NANALLY, JIUYUAN, SKIA]):
            if step.task == "AnomalyHunter":
                self.assertIn(step.config[AH.CONF_HUNTER_TARGET], AH.HUNTER_TARGETS)
            elif step.task == "AnomalyTask":
                self.assertIn(step.config[AT.CONF_EXP_TARGET], AT.EXP_TARGET_OPTIONS)

    def test_plan_never_mentions_conversion(self):
        for step in fp.build_plan([HOTORI, LACRIMOSA, NANALLY, JIUYUAN, SKIA]):
            self.assertNotIn("Conversion", json.dumps(step.__dict__, ensure_ascii=False))


class TestExchangeSources(unittest.TestCase):
    def test_shops_are_not_farm_routes(self):
        for text in ("Hunter Exchange", "Lost Exchange"):
            with self.subTest(text=text):
                self.assertEqual(fp.parse_source(text).kind, fp.KIND_EXCHANGE)

    def test_anomaly_drop_outranks_a_shop(self):
        best = fp.best_source(["Open Material Selection Box", "Anomaly Drop",
                               "Hunter Exchange", "Lost Exchange"])
        self.assertEqual(best.kind, fp.KIND_ANOMALY_DROP)


class TestRoutineChanges(unittest.TestCase):
    def test_hunt_choices_largest_shortfall_first(self):
        steps = fp.build_plan([NANALLY, JIUYUAN, HOTORI])
        self.assertEqual([s.material for s in fp.hunt_steps(steps)],
                         ["A Page from Delusion's Shore", "Tear of the Sea"])

    def test_changes_target_the_routine_entries(self):
        steps = fp.build_plan([NANALLY, SKIA])
        changes = fp.routine_changes(fp.hunt_steps(steps)[0], fp.exp_step([SKIA]))
        self.assertEqual(changes[fp.ROUTINE_HUNTER],
                         {AH.CONF_HUNTER_TARGET: AH.TARGET_BLACK_BOOK})
        self.assertEqual(changes[fp.ROUTINE_ANOMALY][AT.CONF_EXP_TARGET], AT.EXP_CHAR)
        self.assertEqual(fp.routine_changes(None, None), {})

    def test_preview_lists_only_what_changes(self):
        changes = {fp.ROUTINE_HUNTER: {AH.CONF_HUNTER_TARGET: AH.TARGET_BLACK_BOOK},
                   fp.ROUTINE_ANOMALY: {AT.CONF_TASK_TYPE: AT.TASK_EXP_COIN,
                                        AT.CONF_EXP_TARGET: AT.EXP_CHAR}}
        current = {fp.ROUTINE_HUNTER: {AH.CONF_HUNTER_TARGET: AH.TARGET_SOUND_KING},
                   fp.ROUTINE_ANOMALY: {AT.CONF_TASK_TYPE: AT.TASK_EXP_COIN,
                                        AT.CONF_EXP_TARGET: AT.EXP_COIN}}
        self.assertEqual(fp.preview_changes(current, changes), [
            (fp.ROUTINE_HUNTER, AH.CONF_HUNTER_TARGET, AH.TARGET_SOUND_KING,
             AH.TARGET_BLACK_BOOK),
            (fp.ROUTINE_ANOMALY, AT.CONF_EXP_TARGET, AT.EXP_COIN, AT.EXP_CHAR),
        ])


class TestLoadAscendMap(unittest.TestCase):
    def test_missing_file_is_empty(self):
        self.assertEqual(fp.load_ascend_map(Path("does/not/exist.json")), {})

    def test_reads_records(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "map.json"
            path.write_text(json.dumps({"Nanally": NANALLY}), encoding="utf-8")
            self.assertEqual(fp.load_ascend_map(path)["Nanally"]["status"], "ascend")


if __name__ == "__main__":
    unittest.main()
