"""Daily routine profiles.

Each profile is a separate DailyRoutineTask subclass so that ok-script gives it its own
config file; ok.task.task.BaseTask.load_config() keys the store by class name. That lets one
schedule entry per weekday carry its own task selection.

The per-subtask settings store (DailyRoutineTask.TASK_CONFIGS_FILE_NAME) stays shared, so
coffee/anomaly settings are edited once and reused by every profile.

Profile 1 is DailyRoutineTask itself, which keeps existing user configs working.
"""

from src.tasks.daily.DailyRoutineTask import DailyRoutineTask
from src.utils.i18n_format import register_i18n_format

__all__ = ["PROFILE_COUNT", "PROFILE_NAME_FMT", "DAILY_ROUTINE_PROFILE_CLASSES"]

PROFILE_COUNT = 7

# Default display name of profiles 2..N; registered below so every numbered name resolves
# through one catalog entry instead of one entry per profile.
PROFILE_NAME_FMT = "日常任务 {}"


def _make_profile_class(index: int) -> type[DailyRoutineTask]:
    def __init__(self, *args, **kwargs):
        DailyRoutineTask.__init__(self, *args, **kwargs)
        self.name = PROFILE_NAME_FMT.format(index)

    return type(
        f"DailyRoutineProfile{index}",
        (DailyRoutineTask,),
        {"__init__": __init__, "profile_index": index},
    )


DAILY_ROUTINE_PROFILE_CLASSES: tuple[type[DailyRoutineTask], ...] = (DailyRoutineTask,) + tuple(
    _make_profile_class(index) for index in range(2, PROFILE_COUNT + 1)
)

# Exposed as module attributes so ok.util.clazz.init_class_by_name() can resolve them by name.
for _profile_class in DAILY_ROUTINE_PROFILE_CLASSES[1:]:
    globals()[_profile_class.__name__] = _profile_class
    __all__.append(_profile_class.__name__)

register_i18n_format(PROFILE_NAME_FMT)
