from deemon.core import db, oldsettings


class Deemon:
    def __init__(self):
        self.settings = oldsettings.Settings()
        self.config = self.settings.config
        self.db = db.DBHelper(self.settings.db_path)
