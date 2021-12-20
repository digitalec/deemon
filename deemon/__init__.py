#!/usr/bin/env python3
from deemon.utils import startup

__version__ = '2.9.0-beta1'
__dbversion__ = '3.6'

appdata = startup.get_appdata_dir()
startup.init_appdata_dir(appdata)
