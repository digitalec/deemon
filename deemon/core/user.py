from deemon.core.config import Config
from deemon.core.db import Database
from deemon.utils import startup


class User(object):
    def __init__(self):
        self.db = Database(startup.get_database())
        self.config = Config()
