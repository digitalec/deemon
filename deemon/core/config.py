from typing import List, Dict, Optional
from deemon.utils import startup
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "check_update": 1,
    "debug_mode": False,
    "query_limit": 5,
    "ranked_duplicates": True,
    "accept_closest_match": True,
    "new_releases": {
        "by_release_date": True,
        "release_max_age": 90
    },
    "global": {
        "bitrate": 3,
        "alerts": False,
        "record_type": "all",
        "download_path": "",
        "email": ""
    },
    "deemix": {
        "path": "",
        "arl": ""
    },
    "smtp_settings": {
        "server": "",
        "port": 465,
        "username": "",
        "password": "",
        "from_addr": ""
    },
    "plex": {
        "base_url": "",
        "token": "",
        "library": ""
    }
}


class Config(object):
    _CONFIG_FILE: Optional[Path] = startup.get_config()
    _CONFIG: Optional[dict] = None

    def __init__(self):
        if not Config._CONFIG_FILE.exists():
            self.__create_default_config()

        if Config._CONFIG is None:
            with open(Config._CONFIG_FILE, 'r') as f:
                try:
                    Config._CONFIG = json.load(f)
                except json.decoder.JSONDecodeError as e:
                    logger.exception(f"An error occured while reading from config: {e}")
                    raise

        if self.validate() > 0:
            self.__write_modified_config()

        # Set as default profile for init
        self.set('profile_id', 1, False)

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

        # Convert previous configuration keys to new 2.x values, removing unused
        if not Config._CONFIG.get('plex'):
            Config._CONFIG['plex'] = {}
            modified += 1

        if not Config._CONFIG.get('smtp_settings'):
            Config._CONFIG['smtp_settings'] = {}
            modified += 1

        if not Config._CONFIG.get('deemix'):
            Config._CONFIG['deemix'] = {}
            modified += 1

        if not Config._CONFIG.get('global'):
            Config._CONFIG['global'] = {}
            modified += 1

        if not Config._CONFIG.get('new_releases'):
            Config._CONFIG['new_releases'] = {}
            modified += 1

        temp_config = Config._CONFIG.copy()
        for key in temp_config:
            if key not in DEFAULT_CONFIG:
                if key == "smtp_recipient":
                    Config._CONFIG['email'] = Config._CONFIG.pop('smtp_recipient')
                    modified += 1
                elif key == "plex_baseurl":
                    Config._CONFIG['plex']['base_url'] = Config._CONFIG.pop('plex_baseurl')
                    modified += 1
                elif key == "plex_token":
                    Config._CONFIG['plex']['token'] = Config._CONFIG.pop('plex_token')
                    modified += 1
                elif key == "plex_library":
                    Config._CONFIG['plex']['library'] = Config._CONFIG.pop('plex_library')
                    modified += 1
                elif key == "smtp_server":
                    Config._CONFIG['smtp_settings']['server'] = Config._CONFIG.pop('smtp_server')
                    modified += 1
                elif key == "smtp_port":
                    Config._CONFIG['smtp_settings']['port'] = Config._CONFIG.pop('smtp_port')
                    modified += 1
                elif key == "smtp_user":
                    Config._CONFIG['smtp_settings']['username'] = Config._CONFIG.pop('smtp_user')
                    modified += 1
                elif key == "smtp_pass":
                    Config._CONFIG['smtp_settings']['password'] = Config._CONFIG.pop('smtp_pass')
                    modified += 1
                elif key == "smtp_sender":
                    Config._CONFIG['smtp_settings']['from_addr'] = Config._CONFIG.pop('smtp_sender')
                    modified += 1
                elif key == "deemix_path":
                    Config._CONFIG['deemix']['path'] = Config._CONFIG.pop('deemix_path')
                    modified += 1
                elif key == "arl":
                    Config._CONFIG['deemix']['arl'] = Config._CONFIG.pop('arl')
                    modified += 1
                elif key == "bitrate":
                    Config._CONFIG['global']['bitrate'] = Config._CONFIG.pop('bitrate')
                    modified += 1
                elif key == "alerts":
                    Config._CONFIG['global']['alerts'] = Config._CONFIG.pop('alerts')
                    modified += 1
                elif key == "record_type":
                    Config._CONFIG['global']['record_type'] = Config._CONFIG.pop('record_type')
                    modified += 1
                elif key == "download_path":
                    Config._CONFIG['global']['download_path'] = Config._CONFIG.pop('download_path')
                    modified += 1
                elif key == "email":
                    Config._CONFIG['global']['email'] = Config._CONFIG.pop('email')
                    modified += 1
                elif key == "release_by_date":
                    Config._CONFIG['new_releases']['by_release_date'] = Config._CONFIG.pop('release_by_date')
                    modified += 1
                elif key == "release_max_days":
                    Config._CONFIG['new_releases']['release_max_age'] = Config._CONFIG.pop('release_max_days')
                    modified += 1
                else:
                    logger.debug(f"Your config contains an unknown setting and will be removed: {key}")
                    del Config._CONFIG[key]
                    modified += 1

        # Convert previous configuration values to new 2.x values
        for key in DEFAULT_CONFIG:
            if key not in Config._CONFIG:
                logger.debug(f"Key '{key}' not set, using default value: {DEFAULT_CONFIG[key]}")
                Config._CONFIG[key] = DEFAULT_CONFIG[key]
                modified += 1
            else:
                if key == "release_by_date" and isinstance(Config._CONFIG[key], int):
                    if Config._CONFIG[key] == 1:
                        Config._CONFIG[key] = True
                    else:
                        Config._CONFIG[key] = False
                    modified += 1

                if not isinstance(DEFAULT_CONFIG[key], type(Config._CONFIG[key])) and key != "bitrate":
                    print(type(DEFAULT_CONFIG[key]), type(Config._CONFIG[key]))
                    raise PropertyTypeMismatch(f"Type mismatch on property '{key}'")

                if key == "record_type":
                    if Config._CONFIG[key].lower() not in ['all', 'album', 'ep', 'single']:
                        raise UnknownValue(f"Invalid value specified for record_type; "
                                           f"expected 'all', 'album', 'ep' or 'single'")

                if key == "bitrate":
                    if isinstance(Config._CONFIG[key], str):
                        if Config._CONFIG[key] in ["128", "1"]:
                            Config._CONFIG[key] = 1
                        elif Config._CONFIG[key] in ["320", "3"]:
                            Config._CONFIG[key] = 3
                        elif Config._CONFIG[key] in ["flac", "Flac", "FLAC", "9"]:
                            Config._CONFIG[key] = 9
                        else:
                            raise PropertyTypeMismatch("Unknown string value provided for bitrate")
                        modified += 1
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
        return Config._CONFIG.get('plex').get('base_url')

    @staticmethod
    def plex_token() -> str:
        return Config._CONFIG.get('plex_token').get('token')

    @staticmethod
    def plex_library() -> str:
        return Config._CONFIG.get('plex_library').get('library')

    @staticmethod
    def download_path() -> str:
        return Config._CONFIG.get('global').get('download_path')

    @staticmethod
    def deemix_path() -> str:
        return Config._CONFIG.get('deemix').get('deemix_path')

    @staticmethod
    def arl() -> str:
        return Config._CONFIG.get('deemix').get('arl')

    @staticmethod
    def release_by_date() -> bool:
        return Config._CONFIG.get('new_releases').get('by_release_date')

    @staticmethod
    def release_max_days() -> int:
        return Config._CONFIG.get('new_releases').get('release_max_age')

    @staticmethod
    def bitrate() -> int:
        return Config._CONFIG.get('global').get('bitrate')

    @staticmethod
    def alerts() -> bool:
        return Config._CONFIG.get('global').get('alerts')

    @staticmethod
    def record_type() -> str:
        return Config._CONFIG.get('global').get('record_type')

    @staticmethod
    def smtp_server() -> str:
        return Config._CONFIG.get('smtp_settings').get('server')

    @staticmethod
    def smtp_port() -> int:
        return Config._CONFIG.get('smtp_settings').get('port')

    @staticmethod
    def smtp_user() -> str:
        return Config._CONFIG.get('smtp_settings').get('username')

    @staticmethod
    def smtp_pass() -> str:
        return Config._CONFIG.get('smtp_settings').get('password')

    @staticmethod
    def smtp_sender() -> str:
        return Config._CONFIG.get('smtp_settings').get('from_addr')

    @staticmethod
    def smtp_recipient() -> list:
        return Config._CONFIG.get('global').get('email')

    @staticmethod
    def check_update() -> int:
        return Config._CONFIG.get('check_update')

    @staticmethod
    def debug_mode() -> bool:
        return Config._CONFIG.get('debug_mode')

    @staticmethod
    def profile_id() -> int:
        return Config._CONFIG.get('profile_id')

    @staticmethod
    def update_available() -> int:
        return Config._CONFIG.get('update_available')

    @staticmethod
    def query_limit() -> int:
        return Config._CONFIG.get('query_limit')

    @staticmethod
    def ranked_duplicates() -> int:
        return Config._CONFIG.get('ranked_duplicates')

    @staticmethod
    def accept_closest_match() -> bool:
        return Config._CONFIG.get('accept_closest_match')

    @staticmethod
    def set(property, value, validate=True):
        if validate:
            if not isinstance(value, type(DEFAULT_CONFIG[property])):
                raise PropertyTypeMismatch(f"Type mismatch while setting {property} "
                                           f"to {value} (type: {type(value).__name__})")
        Config._CONFIG[property] = value


class PropertyTypeMismatch(Exception):
    pass


class UnknownValue(Exception):
    pass
