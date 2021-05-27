from pathlib import Path
from deemon.app.db import DB
from deemon import __version__
import logging
import platform
import datetime
import sys
import os

logger = logging.getLogger("deemon")
logger.setLevel(logging.INFO)
logger.propagate = False

home_dir = Path.home()
appdata_dir = ""

if os.getenv("XDG_CONFIG_HOME"):
    appdata_dir = Path(os.getenv("XDG_CONFIG_HOME")) / 'deemon'
elif os.getenv("APPDATA"):
    appdata_dir = Path(os.getenv("APPDATA")) / "deemon"
elif sys.platform.startswith('darwin'):
    appdata_dir = home_dir / 'Library' / 'Application Support' / 'deemon'
else:
    appdata_dir = home_dir / '.config' / 'deemon'


def get_appdata_dir():
    return appdata_dir


class Settings:

    def __init__(self, custom_path=None):
        self.config = {}
        self.config_path = Path(custom_path or get_appdata_dir())
        self.db_path = Path(self.config_path / 'releases.db')
        self.load_config()

    def load_config(self):
        db = DB(self.db_path)
        result = db.query("SELECT * FROM config")
        for row in result:
            self.config[row[0]] = row[1]

    def init_log(self):
        log_path = self.config_path / 'logs'
        now = datetime.datetime.now()
        log_file = now.strftime("%Y-%m-%d_%H%M%S") + ".log"

        os.makedirs(log_path, exist_ok=True)

        fh = logging.FileHandler(log_path / log_file, 'w', 'utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s - [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
        logger.addHandler(fh)

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(ch)

        logger.debug(f"deemon version {__version__}")
        logger.debug(f"Python version {platform.python_version()}")

        # circulating log
        max_log_files = 7
        log_list = os.listdir(log_path)
        log_list.sort()
        if len(log_list) > max_log_files:
            for i in range(len(log_list) - max_log_files):
                (log_path / log_list[i]).unlink()
