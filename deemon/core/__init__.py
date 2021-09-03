from deemon.core import db
from deemon.utils import startup


class Deemon:
    def __init__(self):
        self.db = db.Database(startup.get_database())