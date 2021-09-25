from packaging.version import parse as parse_version
from pathlib import Path
import requests
import logging
import sys
import os

logger = logging.getLogger(__name__)


def get_appdata_dir():
    """
    Get appdata directory where configuration and data is stored
    """
    home_dir = Path.home()

    if os.getenv("XDG_CONFIG_HOME"):
        appdata_dir = Path(os.getenv("XDG_CONFIG_HOME")) / 'deemon'
    elif os.getenv("APPDATA"):
        appdata_dir = Path(os.getenv("APPDATA")) / "deemon"
    elif sys.platform.startswith('darwin'):
        appdata_dir = home_dir / 'Library' / 'Application Support' / 'deemon'
    else:
        appdata_dir = home_dir / '.config' / 'deemon'

    return appdata_dir


def get_backup_dir():
    return Path(get_appdata_dir() / "backups")


def init_appdata_dir(appdata):
    Path(appdata / 'logs').mkdir(parents=True, exist_ok=True)
    Path(appdata / 'backups').mkdir(exist_ok=True)


def get_config():
    return get_appdata_dir() / 'config.json'


def get_database():
    return get_appdata_dir() / 'deemon.db'


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
