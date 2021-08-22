from packaging.version import parse as parse_version
from deemon import __version__
from datetime import datetime
from pathlib import Path
import requests
import logging
import time
import sys
import os

logger = logging.getLogger(__name__)

ALLOWED_BITRATES = [1, 3, 9]
ALLOWED_ALERTS = [0, 1]


def validate_bitrate(bitrate):
    logger.debug(f"Bitrate requested: {bitrate}")
    if isinstance(bitrate, str):
        if "128" in bitrate:
            bitrate = 1
        elif "320" in bitrate:
            bitrate = 3
        elif "flac" in bitrate.lower():
            bitrate = 9
        else:
            try:
                bitrate = int(bitrate)
            except ValueError:
                logger.error(f"Unknown bitrate option: {bitrate} ({str(type(bitrate).__name__)})")
                sys.exit(1)

    if bitrate == 128:
        bitrate = 1
    if bitrate == 320:
        bitrate = 3

    if bitrate not in ALLOWED_BITRATES:
        logger.error(f"Unknown bitrate option: {bitrate}")
        sys.exit(1)

    logger.debug(f"Bitrate is set to: {bitrate}")
    return bitrate


def validate_alerts(alerts):
    if alerts not in ALLOWED_ALERTS:
        logger.error(f"Invalid alert value of: {alerts}")
        sys.exit(1)
    return alerts


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


def validate_date(d):
    try:
        datetime.strptime(d, '%Y-%m-%d')
    except ValueError as e:
        return False
    return True


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


def read_file_as_csv(file):
    with open(file, 'r', encoding="utf8", errors="replace") as f:
        make_csv = f.read().replace('\n', ',')
        csv_to_list = make_csv.split(',')
        sorted_list = sorted(list(filter(None, csv_to_list)))
        return sorted_list


def process_input_file(artist_list):
    logger.debug("Processing file contents")
    int_artists = []
    str_artists = []
    for i in range(len(artist_list)):
        try:
            int_artists.append(int(artist_list[i]))
        except ValueError:
            str_artists.append(artist_list[i])
    logger.debug(f"Detected {len(int_artists)} artist ID(s) and {len(str_artists)} artist name(s)")
    return int_artists, str_artists
