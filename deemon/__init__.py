#!/usr/bin/env python3
from deemon.utils import startup

__version__ = '2.0b7'
__dbversion__ = '3.1'

appdata = startup.get_appdata_dir()
startup.init_appdata_dir(appdata)
