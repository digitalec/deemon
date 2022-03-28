#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of deemon.
#
# Copyright (C) 2022 digitalec <digitalec.dev@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
import json
import yaml
import logging
from pathlib import Path
from copy import deepcopy

from deemon.utils import paths
from deemon.exceptions import (
    PropertyTypeMismatch,
    InvalidValue,
)

from deemon.utils.constants import (
    DEFAULT_CONFIG,
    SENSITIVE_KEYS,
    RECORD_TYPES,
    RELEASE_CHANNELS,
    BITRATES
)

MAX_API_THREADS = 50


class Config(object):

    def __init__(self):

        self.logger = logging.getLogger(__name__)
        self._config_path = paths.get_appdata_dir()
        self._config_file = Path(self._config_path / "config.yaml")
        self._config_file_v2 = Path(self._config_path / "config.json")
        self._default_config = DEFAULT_CONFIG

        if not self._config_file.exists():
            if self._config_file_v2.exists():
                self._write_config(self._default_config)
                self._migrate_config()
            else:
                self._write_config(self._default_config)

        self._config = self._load_config()

        self._validate_config(deepcopy(self._default_config), self._config)

        if self._update_config:
            self._write_config(self._config)

    def _load_config(self):
        """ Load configuration from disk """
        with open(self._config_file, 'r') as f:
            return yaml.safe_load(f)

    def _update_config(self, source: dict, target: dict):
        modified = 0

        for key, value in source.items():
            if isinstance(value, dict):
                modified += self._update_config(value, target[key])
            elif key not in target.keys():
                target[key] = value
                modified += 1

        return modified

    def _validate_config(self, source: dict, target: dict):
        """
        Validate user config values against default dict and add
        missing key:val pairs
        """

        for key, value in source.items():
            if isinstance(value, dict):
                if not target.get(key):
                    target[key] = {}
                self._validate_config(value, target[key])
            elif key in target.keys():
                if isinstance(target[key], type(value)):
                    if key == "bitrate":
                        if value not in BITRATES.values():
                            raise InvalidValue(f"Invalid value specified for bitrate: {value}")
                    elif key == "record_types":
                        for rt in value:
                            if rt not in RECORD_TYPES.values():
                                raise InvalidValue(f"Invalid value specified for record_types: {value}")
                    elif key == "release_channel":
                        if value not in RELEASE_CHANNELS:
                            raise InvalidValue(f"Invalid value specified for release_channel: {value}")
                else:
                    raise PropertyTypeMismatch(f"Invalid value for `{key}`."
                                               f" Expected type {type(target[key]).__name__}"
                                               f" but got {type(value).__name__}")

    def _print_config(self, val: dict = None, parent: str = None):
        """
        Print configuration hiding sensitive information
        """
        for key, value in val.items():
            if not parent:
                parent = key
            if isinstance(value, dict):
                self._print_config(value, parent)
                parent = None
            else:
                if key in SENSITIVE_KEYS and value:
                    value = "********"
                if isinstance(value, list):
                    value = ", ".join(value)
                self.logger.debug(f"{parent}/{key}: {value}")

    def _get_property(self, property_name: str, d: dict = None):
        """ Recursively search dict for key and return its value """

        d = self._config if not d else d

        if property_name in d.keys():
            return d[property_name]
        else:
            for key, val in d.items():
                if isinstance(val, dict):
                    result = self._get_property(property_name, val)
                    if result:
                        return result

    def set_property(self, property_name: str, value, d: dict = None):
        """ Update configuration value during running instance """

        d = self._config if not d else d

        if property_name in d.keys():
            d[property_name] = value
            return True
        else:
            for key, val in d.items():
                if isinstance(val, dict):
                    if self.set_property(property_name, value, val):
                        return

    def _write_config(self, cfg: dict) -> None:
        """ Write config to config.yaml """
        with open(self._config_file, 'w') as f:
            yaml.dump(cfg, f, sort_keys=False, indent=4)

    def _migrate_config(self):

        with open(self._config_file_v2, 'r') as f:
            old_config = json.load(f)

            with open(self._config_file, 'r+') as fi:
                new_config = yaml.safe_load(fi)

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
                    new_config['notifications']['notify'] = True
                else:
                    new_config['notifications']['notify'] = False
                if old_config.get('global', {}).get('email'):
                    new_config['notifications']['recipient_email'] = old_config['global']['email']
                if old_config.get('deemix', {}).get('path'):
                    new_config['deemix']['path'] = old_config['deemix']['path']
                if old_config.get('deemix', {}).get('arl'):
                    new_config['deemix']['arl'] = old_config['deemix']['arl']
                if old_config.get('deemix', {}).get('check_account_status'):
                    new_config['deemix']['check_account_status'] = old_config['deemix']['check_account_status']
                if old_config.get('smtp_settings', {}).get('server'):
                    new_config['notifications']['smtp_server'] = old_config['smtp_settings']['server']
                if old_config.get('smtp_settings', {}).get('port'):
                    new_config['notifications']['smtp_port'] = old_config['smtp_settings']['port']
                if old_config.get('smtp_settings', {}).get('username'):
                    new_config['notifications']['smtp_username'] = old_config['smtp_settings']['username']
                if old_config.get('smtp_settings', {}).get('password'):
                    new_config['notifications']['smtp_password'] = old_config['smtp_settings']['password']
                if old_config.get('smtp_settings', {}).get('from_addr'):
                    new_config['notifications']['smtp_from_address'] = old_config['smtp_settings']['from_addr']
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

                self._write_config(new_config)

    @property
    def check_update(self):
        return self._get_property('check_update')

    @property
    def release_channel(self):
        return self._get_property('release_channel')

    @property
    def max_search_results(self):
        return self._get_property('max_search_results')

    @property
    def rollback_view_limit(self):
        return self._get_property('rollback_view_limit')

    @property
    def prompt_duplicates(self):
        return self._get_property('prompt_duplicates')

    @property
    def prompt_no_matches(self):
        return self._get_property('prompt_no_matches')

    @property
    def max_release_age(self):
        return self._get_property('max_release_age')

    @property
    def fast_api(self):
        return self._get_property('fast_api')

    @property
    def profile(self):
        return self._get_property('profile')

    @property
    def download_path(self):
        return self._get_property('download_path')

    @property
    def bitrate(self):
        return self._get_property('bitrate')

    @property
    def record_types(self):
        return self._get_property('record_types')

    @property
    def notifications(self):
        return self._get_property('enabled')

    @property
    def recipient(self):
        return self._get_property('recipient_email')

    @property
    def smtp_server(self):
        return self._get_property('smtp_server')

    @property
    def smtp_username(self):
        return self._get_property('smtp_username')

    @property
    def smtp_password(self):
        return self._get_property('smtp_password')

    @property
    def smtp_from(self):
        return self._get_property('smtp_from_address')

    @property
    def deemix_path(self):
        return self._get_property('path')

    @property
    def arl(self):
        return self._get_property('arl')

    @property
    def check_account_status(self):
        return self._get_property('check_account_status')

    @property
    def plex_url(self):
        return self._get_property('base_url')

    @property
    def plex_token(self):
        return self._get_property('token')

    @property
    def plex_library(self):
        return self._get_property('library')
