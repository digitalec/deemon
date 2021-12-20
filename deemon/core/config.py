import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Optional

from deemon.core.exceptions import ValueNotAllowed, UnknownValue, PropertyTypeMismatch
from deemon.utils import startup

logger = logging.getLogger(__name__)

ALLOWED_VALUES = {
    'bitrate': {1: "128", 3: "320", 9: "FLAC"},
    'alerts': [True, False],
    'record_type': ['all', 'album', 'ep', 'single'],
    'release_channel': ['stable', 'beta']
}

DEFAULT_CONFIG = {
    "check_update": 1,
    "debug_mode": False,
    "release_channel": "stable",
    "experimental_api": True,
    "query_limit": 5,
    "rollback_view_limit": 10,
    "prompt_duplicates": False,
    "prompt_no_matches": True,
    "compilations": False,
    "new_releases": {
        "by_release_date": True,
        "release_max_age": 90
    },
    "global": {
        "bitrate": "320",
        "alerts": False,
        "record_type": "all",
        "download_path": "",
        "email": ""
    },
    "deemix": {
        "path": "",
        "arl": "",
        "check_account_status": True
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

            if not self.arl():
                logger.debug("Attempting to locate deemix's .arl file")
                arl_file = startup.get_appdata_root() / 'deemix' / '.arl'
                if Path(arl_file).is_file():
                    with open(arl_file) as f:
                        arl_from_file = f.readline().replace("\n", "")
                        self.set('arl', arl_from_file)
                        logger.debug("Successfully loaded ARL")

            if len(self.arl()) > 0 and len(self.arl()) != 192:
                logger.warning(f"   [!] Possible invalid ARL detected (length: {len(self.arl())}). ARL should "
                               "be 192 characters")

            # Set default for runtime settings
            self.set('profile_id', 1, validate=False)

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

        def process_config(dict1, dict2):
            """
            Process user configuration, applying values to a default config
            """
            for key, value in dict1.items():
                if key in dict2.keys():
                    if isinstance(dict1[key], dict):
                        process_config(dict1[key], dict2[key])
                    else:
                        dict2[key] = dict1[key]
            return dict2

        def find_position(d, key):
            for k, v in d.items():
                if isinstance(v, dict):
                    next = find_position(v, key)
                    if next:
                        return [k] + next
                elif k == key:
                    return [k]

        def update_config_layout(user_config, reference_config):
            nonlocal modified
            migration_map = [
                {'check_update': 'check_update'},
                {'plex_baseurl': 'base_url'},
                {'plex_token': 'token'},
                {'plex_library': 'library'},
                {'deemix_path': 'path'},
                {'arl': 'arl'},
                {'smtp_recipient': 'email'},
                {'smtp_server': 'server'},
                {'smtp_user': 'username'},
                {'smtp_pass': 'password'},
                {'smtp_port': 'port'},
                {'smtp_sender': 'from_addr'},
                {'bitrate': 'bitrate'},
                {'alerts': 'alerts'},
                {'record_type': 'record_type'},
                {'download_path': 'download_path'},
                {'release_by_date': 'by_release_date'},
                {'release_max_days': 'release_max_age'},
                {'ranked_duplicates': 'prompt_duplicates'}
            ]
            for mlist in migration_map:

                for old, new in mlist.items():
                    user_config_tmp = deepcopy(user_config)
                    user_config_copy = user_config
                    if not user_config.get(old):
                        continue

                    old_position = find_position(user_config, old) or [old]
                    new_position = find_position(reference_config, new) or [new]

                    for i in old_position[:-1]:
                        user_config_tmp = user_config_tmp.setdefault(i, {})

                    for i in new_position[:-1]:
                        user_config_copy = user_config_copy.setdefault(i, {})

                    if user_config_tmp != user_config_copy:
                        logger.debug("Migrating " + ':'.join([str(x) for x in old_position]) + " -> " + ':'.join(
                            [str(x) for x in new_position]))
                        user_config_copy[new_position[-1]] = user_config_tmp[old_position[-1]]
                        modified += 1

            return user_config

        def test_values(dict1, dict2):
            nonlocal modified
            for key, value in dict1.items():
                if key in dict2.keys():
                    if isinstance(dict1[key], dict):
                        test_values(dict1[key], dict2[key])
                    else:
                        if key in ALLOWED_VALUES:
                            if isinstance(ALLOWED_VALUES[key], dict):
                                if key == "bitrate" and value in ["1", "3", "9"]:
                                    if value == "1":
                                        dict1['bitrate'] = "128"
                                    if value == "3":
                                        dict1['bitrate'] = "320"
                                    if value == "9":
                                        dict1['bitrate'] = "FLAC"
                                    modified += 1
                                elif value in ALLOWED_VALUES[key].keys():
                                    dict1_tmp = dict1
                                    pos = find_position(dict1_tmp, key)
                                    for i in pos[:-1]:
                                        dict1_tmp = dict1.setdefault(i, {})
                                    dict1_tmp[key] = ALLOWED_VALUES[key][value]
                                    modified += 1
                                elif value in ALLOWED_VALUES[key].values():
                                    continue
                                else:
                                    raise UnknownValue(
                                        f"Unknown value in config - '{key}': {value} (type: {type(value).__name__})")
                            elif not isinstance(dict1[key], type(dict2[key])):
                                if isinstance(dict2[key], bool):
                                    if dict1[key] == 1:
                                        dict1[key] = True
                                        modified += 1
                                    if dict1[key] == 0:
                                        dict1[key] = False
                                        modified += 1
                                else:
                                    raise UnknownValue(
                                        f"Unknown value in config - '{key}': {value} (type: {type(value).__name__})")
                            else:
                                if value in ALLOWED_VALUES[key]:
                                    continue
                                else:
                                    raise UnknownValue(
                                        f"Unknown value in config - '{key}': {value} (type: {type(value).__name__})")
                        elif not isinstance(dict1[key], type(dict2[key])):
                            if isinstance(dict2[key], bool):
                                if dict1[key] == 1:
                                    dict1[key] = True
                                    modified += 1
                                if dict1[key] == 0:
                                    dict1[key] = False
                                    modified += 1
                            else:
                                raise PropertyTypeMismatch(
                                    f"Invalid type in config - '{str(key)}' incorrectly set as {type(value).__name__}")
                        else:
                            pass

        def add_new_options(dict1, dict2):
            nonlocal modified
            for key, value in dict1.items():
                if key not in dict2.keys():
                    logger.debug(f"New option added to config: {key}")
                    dict2[key] = value
                    modified += 1
                elif isinstance(value, dict):
                    for k, v in value.items():
                        if k not in dict2[key].keys():
                            logger.debug("New option added to config: "
                                         f"{key}/{k}")
                            dict2[key][k] = v
                            modified += 1

        logger.debug("Loading configuration, please wait...")
        add_new_options(DEFAULT_CONFIG, Config._CONFIG)
        migrated_config = update_config_layout(Config._CONFIG, DEFAULT_CONFIG)
        Config._CONFIG = process_config(migrated_config, DEFAULT_CONFIG)
        test_values(Config._CONFIG, DEFAULT_CONFIG)
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
        return Config._CONFIG.get('plex').get('token')

    @staticmethod
    def plex_library() -> str:
        return Config._CONFIG.get('plex').get('library')

    @staticmethod
    def download_path() -> str:
        return Config._CONFIG.get('global').get('download_path')

    @staticmethod
    def deemix_path() -> str:
        return Config._CONFIG.get('deemix').get('path')

    @staticmethod
    def arl() -> str:
        return Config._CONFIG.get('deemix').get('arl')

    @staticmethod
    def release_by_date() -> bool:
        return Config._CONFIG.get('new_releases').get('by_release_date')

    @staticmethod
    def release_max_age() -> int:
        return Config._CONFIG.get('new_releases').get('release_max_age')

    @staticmethod
    def bitrate() -> str:
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
    def prompt_duplicates() -> int:
        return Config._CONFIG.get('prompt_duplicates')

    @staticmethod
    def prompt_no_matches() -> bool:
        return Config._CONFIG.get('prompt_no_matches')

    @staticmethod
    def allowed_values(prop):
        return ALLOWED_VALUES.get(prop)

    @staticmethod
    def release_channel() -> str:
        return Config._CONFIG.get('release_channel')

    @staticmethod
    def rollback_view_limit() -> int:
        return Config._CONFIG.get('rollback_view_limit')

    @staticmethod
    def transaction_id() -> int:
        return Config._CONFIG.get('tid')
    
    @staticmethod
    def check_account_status() -> bool:
        return Config._CONFIG.get('deemix').get('check_account_status')
    
    @staticmethod
    def experimental_api() -> bool:
        return Config._CONFIG.get('experimental_api')

    @staticmethod
    def compilations() -> bool:
        return Config._CONFIG.get('compilations')

    @staticmethod
    def find_position(d, property):
        for k, v in d.items():
            if isinstance(v, dict):
                next = Config.find_position(v, property)
                if next:
                    return [k] + next
            elif k == property:
                return [k]

    @staticmethod
    def get(property):
        return Config._CONFIG.get(property)

    @staticmethod
    def set(property, value, validate=True):
        if not validate:
            Config._CONFIG[property] = value
        if Config._CONFIG.get(property):
            if property in ALLOWED_VALUES:
                if value.lower() == "true" or value == "1":
                    value = True
                elif value.lower() == "false" or value == "0":
                    value = ""
                if value in ALLOWED_VALUES[property]:
                    Config._CONFIG[property] = value
                    return
                raise ValueNotAllowed(f"Property {property} requires one of "
                                      f"{', '.join(ALLOWED_VALUES[property])}, not {value}.")

            if isinstance(value, type(Config._CONFIG[property])):
                Config._CONFIG[property] = value
                return
            else:
                raise PropertyTypeMismatch(f"Type mismatch while setting {property} "
                                           f"to {value} (type: {type(value).__name__})")

        else:
            property_path = Config.find_position(Config._CONFIG, property)
            tmpConfig = Config._CONFIG
            for k in property_path[:-1]:
                tmpConfig = tmpConfig.setdefault(k, {})
            if property in ALLOWED_VALUES:
                if isinstance(value, str):
                    if value.lower() == "true" or value == "1":
                        value = True
                    elif value.lower() == "false" or value == "0":
                        value = False
                if isinstance(ALLOWED_VALUES[property], dict):
                    if value in [str(x.lower()) for x in ALLOWED_VALUES[property].values()]:
                        tmpConfig[property_path[-1]] = value
                        return
                if value in ALLOWED_VALUES[property]:
                    tmpConfig[property_path[-1]] = value
                    return
                raise ValueNotAllowed(f"Value for {property} is invalid: {value} (type: {type(value).__name__})")

            if isinstance(value, type(tmpConfig[property])):
                tmpConfig[property] = value
                return
            else:
                raise PropertyTypeMismatch(f"Type mismatch while setting {property} "
                                           f"to {value} (type: {type(value).__name__})")


class LoadProfile(object):
    def __init__(self, profile: dict):
        logger.debug(f"Loaded config for profile {str(profile['id'])} ({str(profile['name'])})")
        # Rename keys to match config
        profile["profile_id"] = profile.pop("id")
        profile["base_url"] = profile.pop("plex_baseurl")
        profile["token"] = profile.pop("plex_token")
        profile["library"] = profile.pop("plex_library")

        # Append to config for debug output; Remove profile name from dict
        Config.set("profile_name", profile.pop("name"), validate=False)

        for key, value in profile.items():
            if value is None:
                continue
            Config.set(key, value)

        for key, value in Config.get_config().items():
            if isinstance(value, dict):
                for k, v in value.items():
                    if key in ['smtp_settings'] or k in ['arl', 'email', 'token']:
                        if v:
                            v = "********"
                    logger.debug(f"> {key}/{k}: {v}")
            else:
                logger.debug(f"> {key}: {value}")
