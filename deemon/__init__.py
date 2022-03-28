#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of deemon.
#
# Copyright (C) 2022 digitalec <digitalec.dev@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
import sys

__version__ = '3.0_alpha1'
__dbversion__ = '4'

import requests

from deemon.logger import logger
from deemon.db import Database
from deemon.config import Config
from deemon.main import DeemonMain

if sys.version_info < (3, 6):
    print('deemon requires Python 3.6 or higher to run.')
    sys.exit(1)

config = Config()
db = Database()


def main():
    """ Main entry point for deemon """
    cli = DeemonMain()

    if cli.args.whats_new:
        try:
            response = requests.get("https://api.github.com/repos/digitalec/deemon/releases")
        except requests.exceptions.ConnectionError:
            print("Unable to reach GitHub API")
            sys.exit(1)
        for release in response.json():
            if release['name'] == __version__:
                print(release['body'])
                sys.exit()
        print(f"Changelog for v{__version__} was not found.")
        sys.exit()

    if cli.args.profile:
        config.set_property('profile', cli.args.profile)
        profile = db.get_profile_by_id(config.profile)
        logger.info(f"Active profile is {profile['id']} ({profile['name']})")

    if cli.args.command == "backup":
        from deemon.cmd import backup
        if cli.args.restore:
            backup.restore()
        else:
            backup.run(cli.args.include_logs)
    elif cli.args.command == "download":
        pass
    elif cli.args.command == "monitor":
        from deemon.cmd.monitor import Monitor
        monitor = Monitor(cli.args)
        monitor.add()
    elif cli.args.command == "profile":
        pass
    elif cli.args.command == "refresh":
        from deemon.cmd import refresh
        pass
    elif cli.args.command == "remove":
        from deemon.cmd import monitor
        monitor.remove(cli.args.name, cli.args.id, cli.args.playlist)
    elif cli.args.command == "reset":
        logger.warning("** WARNING: Everything except for profiles will be erased! **")
        confirm = input(":: Type 'reset' to confirm: ")
        if confirm.lower() == "reset":
            print("")
            db.reset_database()
        else:
            logger.info("Reset aborted. Database has NOT been modified.")
        return
    elif cli.args.command == "rollback":
        from deemon.cmd import rollback
        if cli.args.view:
            rollback.view_transactions()
        elif cli.args.num:
            rollback.rollback_last(cli.args.num)
    elif cli.args.command == "show":
        from deemon.cmd import monitor
        monitor.remove(config=cli.get_config(), args=cli.get_args())
    elif cli.args.command == "test":
        from deemon.notifier import Notify
        notification = Notify()
        notification.test()
