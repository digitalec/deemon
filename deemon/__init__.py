#!/usr/bin/env python3
from deemon.utils import startup

__version__ = '2.18.3'
__dbversion__ = '3.7'

appdata = startup.get_appdata_dir()
startup.init_appdata_dir(appdata)
