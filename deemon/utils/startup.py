import logging
import os
import sys
from pathlib import Path

import requests
from packaging.version import parse as parse_version

logger = logging.getLogger(__name__)

# TODO REMOVE
def get_config():
    return get_appdata_dir() / 'config.json'


# TODO REMOVE
def get_database():
    return get_appdata_dir() / 'deemon.db'


# TODO REMOVE
def get_log_file():
    """
    Get path to log file
    """
    return Path(get_appdata_dir() / 'logs' / 'deemon.log')


def get_latest_version(release_type):
    latest_ver = "https://pypi.org/pypi/deemon/json"

    try:
        response = requests.get(latest_ver)
    except requests.exceptions.ConnectionError:
        return

    latest_stable = parse_version(response.json()['info']['version'])

    if release_type == "beta":
        all_releases = [parse_version(x) for x in response.json()['releases']]
        sorted_releases = sorted(all_releases, reverse=True)
        for release in sorted_releases:
            if "b" in str(release) or "rc" in str(release):
                if release > latest_stable:
                    return release
                else:
                    return latest_stable
    else:
        return latest_stable

def get_changelog(ver: str):
    try:
        response = requests.get("https://api.github.com/repos/digitalec/"
                                "deemon/releases")
    except requests.exceptions.ConnectionError:
        return print("Unable to reach GitHub API")
    
    for release in response.json():
        if release['name'] == ver:
            return print(release['body'])
    return print(f"Changelog for v{ver} was not found.")