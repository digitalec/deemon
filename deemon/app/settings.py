from pathlib import Path
from deemon import __version__
import logging
import platform
import datetime
import json
import sys
import os

logger = logging.getLogger("deemon")
logger.setLevel(logging.DEBUG)
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


DEFAULT_CONFIG = {
    "smtp_server": "",
    "smtp_port": 465,
    "smtp_username": "",
    "smtp_password": "",
    "smtp_recipient": "",
    "smtp_sender_email": ""
}


class Settings:

    def __init__(self, custom_path=None):
        self.config = {}
        self.legacy_path = Path(Path.home() / ".config/deemon")
        self.config_path = Path(custom_path or get_appdata_dir())
        self.db_path = Path(self.config_path / 'releases.db')

        os.makedirs(self.config_path, exist_ok=True)
        self.init_log()

        # Migrate database file to correct path on non-Linux OSes
        if (self.legacy_path != self.config_path) and Path(self.legacy_path / 'releases.db').exists():
            logger.info(f"Migrating database to new path at: {self.config_path}")
            Path(self.legacy_path / 'releases.db').rename(self.config_path / 'releases.db')
            try:
                Path(self.legacy_path).rmdir()
            except Exception:
                logger.error(f"Unable to remove old appdata directory: {self.legacy_path}")

        if not (self.config_path / 'config.json').exists():
            with open(self.config_path / 'config.json', 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)

        with open(self.config_path / 'config.json') as f:
            self.config = json.load(f)

        for opt in DEFAULT_CONFIG:
            if opt not in self.config or not isinstance(self.config[opt], type(DEFAULT_CONFIG[opt])):
                logger.debug(f"config: {self.config[opt]} / default: {DEFAULT_CONFIG[opt]}")
                self.config[opt] = DEFAULT_CONFIG[opt]

    def init_log(self):
        log_path = self.config_path / 'logs'
        now = datetime.datetime.now()
        log_file = now.strftime("%Y-%m-%d_%H%M%S") + ".log"

        os.makedirs(log_path, exist_ok=True)

        fh = logging.FileHandler(log_path / log_file, 'w', 'utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s - [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
        logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(ch)

        logger.info(f"Starting deemon {__version__}...")
        logger.debug(f"Python version {platform.python_version()}")

        # circulating log
        max_log_files = 7
        log_list = os.listdir(log_path)
        log_list.sort()
        if len(log_list) > max_log_files:
            for i in range(len(log_list) - max_log_files):
                (log_path / log_list[i]).unlink()
