from deemon.app import settings, db
from deemon import __dbversion__
from packaging.version import parse as parse_version


class Deemon:
    def __init__(self):
        self.settings = settings.Settings()
        self.config = self.settings.config
        self.db = db.DBHelper(self.settings.db_path)

        current_db_version = parse_version(self.db.get_db_version())
        app_db_version = parse_version(__dbversion__)

        if current_db_version < app_db_version:
            self.db.do_upgrade(current_db_version)
