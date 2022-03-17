import os
import sys
from pathlib import Path


def get_appdata_root():

    home_dir = Path.home()

    if os.getenv("XDG_CONFIG_HOME"):
        appdata_dir = Path(os.getenv("XDG_CONFIG_HOME"))
    elif os.getenv("APPDATA"):
        appdata_dir = Path(os.getenv("APPDATA"))
    elif sys.platform.startswith('darwin'):
        appdata_dir = home_dir / 'Library' / 'Application Support'
    else:
        appdata_dir = home_dir / '.config'

    return appdata_dir


def get_appdata_dir():
    """
    Get appdata directory where configuration and data is stored
    """
    return get_appdata_root() / 'deemon'


def get_backup_dir():
    return Path(get_appdata_dir() / "backups")


def init_appdata_dir(appdata):
    Path(appdata / 'logs').mkdir(parents=True, exist_ok=True)
    Path(appdata / 'backups').mkdir(exist_ok=True)