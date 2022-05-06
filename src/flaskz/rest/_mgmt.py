__all__ = ['ModelRestManager']


class ModelRestManager:
    """
    Used to manage model rest permission and logging.
    """

    def __init__(self):
        self._permission_check = None
        self._login_check = None
        self._logging = None

    def init_app(self, app):
        app.model_rest_manager = self

    def permission_check(self, permission_check):
        self._permission_check = permission_check
        return self._permission_check

    @property
    def permission_check_callback(self):
        return self._permission_check

    def login_check(self, login_check):
        self._login_check = login_check
        return self._login_check

    @property
    def login_check_callback(self):
        return self._login_check

    def logging(self, logging):
        self._logging = logging
        return self._logging

    @property
    def logging_callback(self):
        return self._logging