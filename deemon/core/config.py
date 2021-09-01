from typing import List, Dict, Optional
from deemon.utils import startup
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "plex_baseurl": "",
    "plex_token": "",
    "plex_library": "",
    "download_path": "",
    "deemix_path": "",
    "arl": "",
    "bitrate": 3,
    "alerts": False,
    "record_type": "all",
    "smtp_server": "",
    "smtp_port": 465,
    "smtp_user": "",
    "smtp_pass": "",
    "smtp_sender": "",
    "smtp_recipient": [],
    "check_update": 1,
    "debug_mode": False
}


class Config(object):
    _CONFIG_FILE: Optional[Path] = startup.get_config()
    _CONFIG: Optional[dict] = None

    def __init__(self):
        if not Config._CONFIG_FILE.exists():
            self.__create_default_config()

        with open(Config._CONFIG_FILE, 'r') as f:
            try:
                Config._CONFIG = json.load(f)
            except json.decoder.JSONDecodeError as e:
                logger.exception(f"An error occured while reading from config: {e}")
                raise

        if self.validate() > 0:
            self.__write_modified_config()

    @staticmethod
    def __create_default_config():
        with open(Config._CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)

    @staticmethod
    def __write_modified_config():
        with open(Config._CONFIG_FILE, 'w') as f:
            json.dump(Config._CONFIG, f, indent=4)

    @staticmethod
    def validate():
        modified = 0
        for key in DEFAULT_CONFIG:
            if key not in Config._CONFIG or Config._CONFIG[key] == "":
                if not DEFAULT_CONFIG[key] == "":
                    logger.error(f"Key '{key}' not set, using default value: {DEFAULT_CONFIG[key]}")
                    Config._CONFIG[key] = DEFAULT_CONFIG[key]
                    modified += 1
            else:
                # Convert previous configuration values to new 2.x values
                if key == "release_by_date" and isinstance(Config._CONFIG[key], int):
                    if Config._CONFIG[key] == 1:
                        Config._CONFIG[key] = True
                    else:
                        Config._CONFIG[key] = False
                    modified += 1

                if key == "bitrate" and isinstance(Config._CONFIG[key], str):
                    if Config._CONFIG[key] == "128":
                        Config._CONFIG[key] = 1
                    elif Config._CONFIG[key] == "320":
                        Config._CONFIG[key] = 3
                    elif Config._CONFIG[key].upper() == "FLAC":
                        Config._CONFIG[key] = 9
                    modified += 1

                if key == "smtp_recipient" and isinstance(Config._CONFIG[key], str):
                    Config._CONFIG[key] = Config._CONFIG[key].split(" ")
                    modified += 1

                if not isinstance(DEFAULT_CONFIG[key], type(Config._CONFIG[key])):
                    raise PropertyTypeMismatch(f"Type mismatch on property '{key}'")

                if key == "record_type":
                    if Config._CONFIG[key].lower() not in ['all', 'album', 'ep', 'single']:
                        raise UnknownValue(f"Invalid value specified for record_type; "
                                           f"expected 'all', 'album', 'ep' or 'single'")

                if Config._CONFIG['bitrate'] not in [1, 3, 9]:
                    raise UnknownValue(f"Unknown value specified for bitrate: {Config._CONFIG['bitrate']}")

                if key == "alerts":
                    if Config._CONFIG['alerts'] not in [0, 1]:
                        raise UnknownValue(f"Unknown value specified for alerts: {Config._CONFIG['alerts']}")

                if key == "release_by_date":
                    if not isinstance(Config._CONFIG['release_by_date'], bool):
                        raise UnknownValue(f"Unknown value specified for release_by_date: "
                                           f"{Config._CONFIG['release_by_date']}")
        return modified

    @staticmethod
    def get_config_file() -> Path:
        return Config._CONFIG_FILE

    @staticmethod
    def get_config() -> dict:
        return Config._CONFIG

    @staticmethod
    def plex_baseurl() -> str:
        return Config._CONFIG.get('plex_baseurl')

    @staticmethod
    def plex_token() -> str:
        return Config._CONFIG.get('plex_token')

    @staticmethod
    def plex_library() -> str:
        return Config._CONFIG.get('plex_library')

    @staticmethod
    def download_path() -> str:
        return Config._CONFIG.get('download_path')

    @staticmethod
    def deemix_path() -> str:
        return Config._CONFIG.get('deemix_path')

    @staticmethod
    def arl() -> str:
        return Config._CONFIG.get('arl')

    @staticmethod
    def release_by_date() -> bool:
        return Config._CONFIG.get('release_by_date')

    @staticmethod
    def release_max_days() -> int:
        return Config._CONFIG.get('release_max_days')

    @staticmethod
    def bitrate() -> int:
        return Config._CONFIG.get('bitrate')

    @staticmethod
    def alerts() -> bool:
        return Config._CONFIG.get('alerts')

    @staticmethod
    def record_type() -> str:
        return Config._CONFIG.get('record_type')

    @staticmethod
    def smtp_server() -> str:
        return Config._CONFIG.get('smtp_server')

    @staticmethod
    def smtp_port() -> int:
        return Config._CONFIG.get('smtp_port')

    @staticmethod
    def smtp_user() -> str:
        return Config._CONFIG.get('smtp_user')

    @staticmethod
    def smtp_pass() -> str:
        return Config._CONFIG.get('smtp_pass')

    @staticmethod
    def smtp_sender() -> str:
        return Config._CONFIG.get('smtp_sender')

    @staticmethod
    def smtp_recipient() -> list:
        return Config._CONFIG.get('smtp_recipient')

    @staticmethod
    def update_freq() -> int:
        return Config._CONFIG.get('check_update')

    @staticmethod
    def debug_mode() -> bool:
        return Config._CONFIG.get('debug_mode')


class PropertyTypeMismatch(Exception):
    pass


class UnknownValue(Exception):
    pass


class InvalidConfig(Exception):
    pass
