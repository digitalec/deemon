#!/usr/bin/env python3
from deemon.utils import startup

__version__ = '2.6.3'
__dbversion__ = '3.5.2'

appdata = startup.get_appdata_dir()
startup.init_appdata_dir(appdata)
