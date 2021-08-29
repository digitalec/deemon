from deemon.core import db, settings


class Deemon:
    def __init__(self):
        self.settings = settings.Settings()
        self.config = self.settings.config
        self.db = db.DBHelper(self.settings.db_path)
