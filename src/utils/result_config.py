from ok.util.config import Config


class ResultConfig(Config):
    """A Config for scan results, whose keys are data rather than settings.

    Config drops every key that is not in its defaults when it loads. Scan results are
    keyed by what was found (character or task names) and start from empty defaults, so
    a plain Config wiped them on every app start. This one keeps whatever was saved.
    """

    def __init__(self, name, folder=None):
        super().__init__(name, {}, folder=folder)

    def verify_config(self, current, default_config):
        dict.clear(self)
        dict.update(self, current if isinstance(current, dict) else {})
        return not isinstance(current, dict)
