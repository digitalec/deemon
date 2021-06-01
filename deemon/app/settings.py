from deemon.app import utils
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

BITRATE = {
    "MP3_128": 1,
    "MP3_320": 3,
    "FLAC": 9
}

DEFAULT_SETTINGS = {
    "plex_baseurl": "",
    "plex_token": "",
    "plex_library": "",
    "download_path": "",
    "deemix_path": "",
    "bitrate": "320",
    "alerts": 0,
    "record_type": "all",
    "smtp_server": "",
    "smtp_port": 465,
    "smtp_user": "",
    "smtp_pass": "",
    "smtp_recipient": ""
}


class Settings:

    def __init__(self, custom_path=None):
        self.config_file = 'config.json'
        self.db_file = 'deemon.db'
        self.legacy_path = Path(Path.home() / ".config/deemon")
        self.config_path = utils.get_appdata_dir()
        self.db_path = Path(self.config_path / self.db_file)

        if self.legacy_path != self.config_path:
            if Path(self.legacy_path / self.db_file).exists():
                self.migrate_legacy_versions()

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

    def migrate_legacy_versions(self):
        Path(self.legacy_path / self.db_file).rename(self.config_path / self.db_file)
        Path(self.legacy_path).rmdir()