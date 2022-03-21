import json
import yaml
import logging
from pathlib import Path

from deemon.utils import paths, validate
from deemon.core.exceptions import PropertyTypeMismatch, InvalidValue
from deemon.utils.constants import SENSITIVE_KEYS

DEFAULT_CONFIG = {
    "app": {
        "check_update": 1,
        "debug_mode": False,
        "release_channel": "stable",
        "max_search_results": 5,
        "rollback_view_limit": 10,
        "prompt_duplicates": False,
        "prompt_no_matches": True,
        "max_release_age": 90,
        "fast_api": True,
    },
    "defaults": {
        "profile": 1,
        "download_path": "",
        "bitrate": "320",
        "record_types": [
            'album',
            'ep',
            'single'
        ],
    },
    "alerts": {
        "enabled": False,
        "recipient_email": "",
        "smtp_server": "",
        "smtp_port": 465,
        "smtp_username": "",
        "smtp_password": "",
        "smtp_from_address": "",
    },
    "deemix": {
        "path": "",
        "arl": "",
        "check_account_status": True
    },
    "plex": {
        "base_url": "",
        "token": "",
        "library": ""
    }
}


class Config(object):

    _CONFIG_PATH = None
    _CONFIG_FILE = None
    CONFIG = None

    def __init__(self, config_path=None):
        self.logger = logging.getLogger(__name__)

        if Config.CONFIG:
            return

        if not config_path:
            Config._CONFIG_PATH = paths.get_appdata_dir()
        else:
            Config._CONFIG_PATH = Path(config_path)

        paths.init_appdata_dir(Config._CONFIG_PATH)
        Config._CONFIG_FILE = Path(Config._CONFIG_PATH / "config.yaml")

        if Path(Config._CONFIG_PATH / "config.json").exists() and not Config._CONFIG_FILE.exists():
            self.logger.debug("Migrating deemon configuration to new format, please wait...")
            self.__write_config(DEFAULT_CONFIG)
            self.migrate_config()

        if not Path(Config._CONFIG_FILE).exists():
            self.logger.debug("No configuration file exists, generating default config...")
            with open(Config._CONFIG_FILE, 'w') as f:
                self.__write_config(DEFAULT_CONFIG)

        with open(Config._CONFIG_FILE, 'r') as f:
            self.logger.debug(f"Reading config file: {Config._CONFIG_FILE}")
            Config.CONFIG = yaml.safe_load(f)

        if self.validate_config() > 0:
            self.__write_config(Config.CONFIG)

        self.logger.debug("Configuration loaded:")
        for key, value in Config.CONFIG.items():
            if isinstance(value, dict):
                for k, v in value.items():
                    if k in SENSITIVE_KEYS:
                        if v:
                            v = "********"
                    self.logger.debug(f"  {key}/{k}: {v}")
            else:
                self.logger.debug(f"  {key}: {value}")

        Config.CONFIG['runtime'] = {
            "artist": [],
            "artist_id": [],
            "playlist": [],
            "file": [],
            "url": [],
            "bitrate": None,
            "alerts": None,
            "record_type": None,
            "download_path": None,
            "transaction_id": None,
            "profile_id": Config.CONFIG['defaults']['profile'],
        }

    @staticmethod
    def __write_config(c):
        with open(Config._CONFIG_FILE, 'w') as f:
            yaml.dump(c, f, sort_keys=False, indent=4)

    def validate_config(self):
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

        def test_values(dict1, dict2):
            nonlocal modified
            for key, value in dict1.items():
                if key in dict2.keys():
                    if isinstance(dict1[key], dict):
                        test_values(dict1[key], dict2[key])
                    else:
                        if key == "bitrate" and not validate.validate_bitrates(value):
                            raise InvalidValue(f"Invalid bitrate: {value}")
                        elif key == "record_type":
                            invalid_rt = validate.validate_record_type(value)
                            if len(invalid_rt):
                                raise InvalidValue(f"Invalid record type(s): {value}")
                        elif key == "release_channel" and not validate.validate_release_channel(value):
                            raise InvalidValue(f"Invalid release channel: {value}")
                        elif not isinstance(dict1[key], type(dict2[key])):
                            raise PropertyTypeMismatch(f"Invalid type in config - '{str(key)}' incorrectly set "
                                                       f"as {type(value).__name__}")

        def add_new_options(dict1, dict2):
            nonlocal modified
            for key, value in dict1.items():
                if key not in dict2.keys():
                    self.logger.debug(f"New option added to config: {key}")
                    dict2[key] = value
                    modified += 1
                elif isinstance(value, dict):
                    for k, v in value.items():
                        if k not in dict2[key].keys():
                            self.logger.debug("New option added to config: "
                                         f"{key}/{k}")
                            dict2[key][k] = v
                            modified += 1

        add_new_options(DEFAULT_CONFIG, Config.CONFIG)
        Config.CONFIG = process_config(Config.CONFIG, DEFAULT_CONFIG)
        test_values(Config.CONFIG, DEFAULT_CONFIG)
        return modified

    def migrate_config(self):

        with open(Path(Config._CONFIG_PATH / 'config.json'), 'r') as f:
            old_config = json.load(f)

            with open(Path(Config._CONFIG_PATH / 'config.yaml'), 'r+') as fi:
                new_config = yaml.safe_load(fi)

                # App
                if old_config.get('check_update'):
                    new_config['app']['check_update'] = old_config['check_update']
                if old_config.get('debug_mode'):
                    new_config['app']['debug_mode'] = old_config['debug_mode']
                if old_config.get('release_channel'):
                    new_config['app']['release_channel'] = old_config['release_channel']
                if old_config.get('experimental_api'):
                    new_config['app']['fast_api'] = old_config['experimental_api']
                if old_config.get('fast_api'):
                    new_config['app']['fast_api'] = old_config['fast_api']
                if old_config.get('query_limit'):
                    new_config['app']['max_search_results'] = old_config['query_limit']
                if old_config.get('rollback_view_limit'):
                    new_config['app']['rollback_view_limit'] = old_config['rollback_view_limit']
                if old_config.get('prompt_duplicates'):
                    new_config['app']['prompt_duplicates'] = old_config['prompt_duplicates']
                if old_config.get('prompt_no_matches'):
                    new_config['app']['prompt_no_matches'] = old_config['prompt_no_matches']
                if 'by_release_date' in old_config.get('new_releases', {}):
                    if old_config['new_releases']['by_release_date']:
                        new_config['app']['max_release_age'] = old_config['new_releases']['release_max_age']
                    else:
                        new_config['app']['max_release_age'] = 0
                else:
                    new_config['app']['max_release_age'] = old_config['new_releases']['release_max_age']

                # Default
                if old_config.get('global', {}).get('bitrate'):
                    new_config['defaults']['bitrate'] = old_config['global']['bitrate']
                if old_config.get('global', {}).get('record_type'):
                    if old_config['global']['record_type'] == "all":
                        new_config['defaults']['record_types'] = ['album', 'ep', 'single']
                    elif old_config['global']['record_type'] in ['album', 'ep', 'single']:
                        new_config['defaults']['record_types'] = [old_config['global']['record_type']]
                    if old_config.get('new_releases'):
                        if old_config['new_releases'].get('include_unofficial'):
                            new_config['defaults']['record_types'].append('unofficial')
                        if old_config['new_releases'].get('include_compilations'):
                            new_config['defaults']['record_types'].append('comps')
                        if old_config['new_releases'].get('include_featured_in'):
                            new_config['defaults']['record_types'].append('feat')
                if old_config.get('global', {}).get('download_path'):
                    new_config['defaults']['download_path'] = old_config['global']['download_path']
                if old_config.get('global', {}).get('alerts'):
                    new_config['alerts']['enabled'] = True
                else:
                    new_config['alerts']['enabled'] = False
                if old_config.get('global', {}).get('email'):
                    new_config['alerts']['recipient_email'] = old_config['global']['email']
                if old_config.get('deemix', {}).get('path'):
                    new_config['deemix']['path'] = old_config['deemix']['path']
                if old_config.get('deemix', {}).get('arl'):
                    new_config['deemix']['arl'] = old_config['deemix']['arl']
                if old_config.get('deemix', {}).get('check_account_status'):
                    new_config['deemix']['check_account_status'] = old_config['deemix']['check_account_status']
                if old_config.get('smtp_settings', {}).get('server'):
                    new_config['alerts']['smtp_server'] = old_config['smtp_settings']['server']
                if old_config.get('smtp_settings', {}).get('port'):
                    new_config['alerts']['smtp_port'] = old_config['smtp_settings']['port']
                if old_config.get('smtp_settings', {}).get('username'):
                    new_config['alerts']['smtp_username'] = old_config['smtp_settings']['username']
                if old_config.get('smtp_settings', {}).get('password'):
                    new_config['alerts']['smtp_password'] = old_config['smtp_settings']['password']
                if old_config.get('smtp_settings', {}).get('from_addr'):
                    new_config['alerts']['smtp_from_address'] = old_config['smtp_settings']['from_addr']
                if old_config.get('plex', {}).get('base_url'):
                    new_config['plex']['base_url'] = old_config['plex']['base_url']
                if old_config.get('plex', {}).get('token'):
                    new_config['plex']['token'] = old_config['plex']['token']
                if old_config.get('plex', {}).get('library'):
                    new_config['plex']['library'] = old_config['plex']['library']
                if old_config.get('experimental', {}).get('experimental_api'):
                    new_config['experimental']['fast_api'] = old_config['experimental']['experimental_api']
                if old_config.get('experimental', {}).get('allow_unofficial_releases'):
                    new_config['experimental']['allow_unofficial_releases'] = old_config['experimental']['allow_unofficial_releases']
                if old_config.get('experimental', {}).get('allow_compilations'):
                    new_config['experimental']['allow_compilations'] = old_config['experimental']['allow_compilations']
                if old_config.get('experimental', {}).get('allow_featured_in'):
                    new_config['experimental']['allow_featured_in'] = old_config['experimental']['allow_featured_in']

                self.__write_config(new_config)
