from packaging.version import parse as parse_version
from deemon import __version__
from datetime import datetime
from pathlib import Path
import requests
import time
import sys
import os


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


def get_log_file():
    """
    Get path to log file
    """
    return Path(get_appdata_dir() / 'logs' / 'deemon.log')


def get_todays_date():
    now_ts = int(time.time())
    today_date = datetime.utcfromtimestamp(now_ts).strftime('%Y-%m-%d')
    return today_date


def get_max_release_date(days):
    day_in_secs = 86400
    input_days_in_secs = days * day_in_secs
    max_date_ts = int(time.time()) - input_days_in_secs
    max_date = datetime.utcfromtimestamp(max_date_ts).strftime('%Y-%m-%d')
    return max_date

def check_version():
    latest_ver = "https://api.github.com/repos/digitalec/deemon/releases/latest"
    try:
        response = requests.get(latest_ver)
    except requests.exceptions.ConnectionError:
        return
    local_version = __version__
    remote_version = response.json()["name"]
    if parse_version(remote_version) > parse_version(local_version):
        return remote_version
