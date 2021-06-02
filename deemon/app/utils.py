from datetime import datetime
from pathlib import Path
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
    Path(appdata).mkdir(exist_ok=True)
    Path(appdata / 'logs').mkdir(exist_ok=True)
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
