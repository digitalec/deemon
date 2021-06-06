from deemon.app import utils
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS = {
    "plex_baseurl": "",
    "plex_token": "",
    "plex_library": "",
    "download_path": "",
    "deemix_path": "",
    "release_by_date": 1,
    "release_max_days": 90,
    "bitrate": "320",
    "alerts": 0,
    "record_type": "all",
    "smtp_server": "",
    "smtp_port": 465,
    "smtp_user": "",
    "smtp_pass": "",
    "smtp_sender": "",
    "smtp_recipient": ""
}


class Settings:

    def __init__(self, custom_path=None):
        self.config_file = 'config.json'
        self.db_file = 'deemon.db'
        self.config_path = utils.get_appdata_dir()
        self.db_path = Path(self.config_path / self.db_file)

        if not Path(self.config_path / self.config_file).exists():
            self.create_default_config()

        self.config = self.load_config()
        self.verify_config()

    def create_default_config(self):
        with open(self.config_path / 'config.json', 'w') as f:
            json.dump(DEFAULT_SETTINGS, f, indent=4)

    def load_config(self):
        with open(Path(self.config_path / self.config_file)) as f:
            return json.load(f)

    def verify_config(self):
        for group in DEFAULT_SETTINGS:
            if group not in self.config:
                self.config[group] = DEFAULT_SETTINGS[group]
