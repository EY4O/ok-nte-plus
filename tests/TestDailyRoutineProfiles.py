import gettext
import unittest

from src.patches.schedule_weekday_patch import (
    WEEKDAYS,
    parse_weekday,
    weekly_trigger_xml,
)
from src.tasks.daily.DailyRoutineProfiles import (
    DAILY_ROUTINE_PROFILE_CLASSES,
    PROFILE_COUNT,
    PROFILE_NAME_FMT,
)
from src.tasks.daily.DailyRoutineTask import DailyRoutineTask
from src.utils.i18n_format import match_i18n_format


class TestDailyRoutineProfiles(unittest.TestCase):
    def _profile(self, profile_class, items=None):
        task = object.__new__(profile_class)
        task.config = {DailyRoutineTask.CONF_ITEMS: items if items is not None else []}
        task.routine_task_configs = {}
        return task

    def test_profile_one_is_the_original_task_class(self):
        self.assertIs(DAILY_ROUTINE_PROFILE_CLASSES[0], DailyRoutineTask)

    def test_profile_count_matches_registered_classes(self):
        self.assertEqual(len(DAILY_ROUTINE_PROFILE_CLASSES), PROFILE_COUNT)

    def test_each_profile_has_a_distinct_config_key(self):
        # BaseTask.load_config() keys the config store by class name, so duplicate names
        # would make profiles share one selection.
        class_names = [cls.__name__ for cls in DAILY_ROUTINE_PROFILE_CLASSES]
        self.assertEqual(len(set(class_names)), len(class_names))

    def test_profiles_keep_independent_selections(self):
        monday = self._profile(
            DAILY_ROUTINE_PROFILE_CLASSES[0], [{"id": "daily_anomaly", "enabled": True}]
        )
        tuesday = self._profile(
            DAILY_ROUTINE_PROFILE_CLASSES[1],
            [{"id": "daily_anomaly_hunter", "enabled": True}],
        )

        monday_enabled = {i["id"] for i in monday.normalize_items() if i["enabled"]}
        tuesday_enabled = {i["id"] for i in tuesday.normalize_items() if i["enabled"]}

        self.assertIn("daily_anomaly", monday_enabled)
        self.assertNotIn("daily_anomaly_hunter", monday_enabled)
        self.assertIn("daily_anomaly_hunter", tuesday_enabled)
        self.assertNotIn("daily_anomaly", tuesday_enabled)

    def test_profiles_share_the_subtask_config_store(self):
        stores = {cls.TASK_CONFIGS_FILE_NAME for cls in DAILY_ROUTINE_PROFILE_CLASSES}
        self.assertEqual(stores, {DailyRoutineTask.TASK_CONFIGS_FILE_NAME})

    def test_profile_name_config_overrides_display_name(self):
        task = self._profile(DAILY_ROUTINE_PROFILE_CLASSES[1])
        task.name = "日常任务 2"

        self.assertEqual(task.name, "日常任务 2")

        task.config[DailyRoutineTask.CONF_PROFILE_NAME] = "周二"
        self.assertEqual(task.name, "周二")

        task.config[DailyRoutineTask.CONF_PROFILE_NAME] = "   "
        self.assertEqual(task.name, "日常任务 2")


class TestScheduleWeekday(unittest.TestCase):
    def test_weekly_xml_uses_selected_weekday(self):
        xml = weekly_trigger_xml("2026-09-20T09:00:00", "Tuesday")

        self.assertIn("<Tuesday></Tuesday>", xml)
        self.assertNotIn("<Monday>", xml)
        self.assertIn("<WeeksInterval>1</WeeksInterval>", xml)
        self.assertIn("<StartBoundary>2026-09-20T09:00:00</StartBoundary>", xml)

    def test_weekly_xml_falls_back_to_monday_for_unknown_weekday(self):
        xml = weekly_trigger_xml("2026-09-20T09:00:00", "Someday")

        self.assertIn("<Monday></Monday>", xml)

    def test_round_trip_for_every_weekday(self):
        for weekday in WEEKDAYS:
            with self.subTest(weekday=weekday):
                xml = weekly_trigger_xml("2026-09-20T09:00:00", weekday)
                self.assertEqual(parse_weekday(xml), weekday)

    def test_parse_weekday_defaults_to_monday_without_trigger_xml(self):
        self.assertEqual(parse_weekday(""), "Monday")
        self.assertEqual(parse_weekday("<CalendarTrigger></CalendarTrigger>"), "Monday")


class TestProfileEnglishStrings(unittest.TestCase):
    """The strings this feature adds must resolve in the en_US catalog."""

    @classmethod
    def setUpClass(cls):
        cls.translation = gettext.translation("ok", localedir="i18n", languages=["en_US"])

    def test_new_ui_strings_are_translated(self):
        expected = {
            "方案": "Profile",
            "日常任务": "Daily Tasks",
            "当前任务": "Current Task",
            "领取收益": "Collect Income",
            "体力消耗目标": "Stamina Target",
        }
        for source, english in expected.items():
            with self.subTest(source=source):
                self.assertEqual(self.translation.gettext(source), english)

    def test_profile_name_format_resolves_for_every_profile(self):
        for index in range(2, PROFILE_COUNT + 1):
            name = PROFILE_NAME_FMT.format(index)
            with self.subTest(name=name):
                matched = match_i18n_format(name)
                self.assertIsNotNone(matched, "profile name format rule is not registered")
                rule, match = matched
                template = self.translation.gettext(rule.template)
                values = [match[field] for field in rule.positional_fields]
                self.assertEqual(template.format(*values), f"Daily Tasks {index}")

    def test_profile_name_config_description_is_translated(self):
        source = DailyRoutineTask.PROFILE_NAME_DESCRIPTION
        self.assertNotEqual(self.translation.gettext(source), source)


if __name__ == "__main__":
    unittest.main()
