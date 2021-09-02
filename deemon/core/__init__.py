from deemon.core import db
from deemon.utils import startup


class Deemon:
    def __init__(self):
        self.db = db.DBHelper(startup.get_database())
