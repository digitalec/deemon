import logging

from packaging.version import parse as parse_version
from deemon import __version__
from pathlib import Path
import requests
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


def init_appdata_dir(appdata):
    Path(appdata / 'logs').mkdir(parents=True, exist_ok=True)
    Path(appdata / 'backups').mkdir(exist_ok=True)


def get_config():
    return get_appdata_dir() / 'config.json'


def get_log_file():
    """
    Get path to log file
    """
    return Path(get_appdata_dir() / 'logs' / 'deemon.log')


def check_version():
    logger.debug("Checking for update...")
    latest_ver = "https://api.github.com/repos/digitalec/deemon/releases/latest"
    try:
        response = requests.get(latest_ver)
    except requests.exceptions.ConnectionError:
        return
    local_version = __version__
    try:
        remote_version = response.json()["name"]
    except KeyError as e:
        logger.debug(f"Invalid data returned from version check; too many requests? {e}")
        return
    if parse_version(remote_version) > parse_version(local_version):
        return remote_version
