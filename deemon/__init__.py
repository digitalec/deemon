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
import requests

__version__ = '3.0_alpha1'
__dbversion__ = '4'

from deemon.core.logger import logger
from deemon.main import DeemonMain
from deemon.utils import startup
from deemon.core.exceptions import ProfileNotExistError

from deemon.core.config import Config
config = Config()

from deemon.core.database import Database, Profile
db = Database()


def main():
    """ Main entry point for deemon """
    cli = DeemonMain()

    # TODO - Add LoadProfile
    # TODO - Add update check

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
        config.set_property('profile_id', cli.args.profile)
    profile = db.get_profile_by_id(config.profile_id)
    logger.debug(f"Active profile is {profile.id} ({profile.name})")

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
        r = refresh.Refresh(skip_downloads=cli.args.skip_downloads, time_machine=cli.args.time_machine)
        r.start()
    elif cli.args.command == "remove":
        from deemon.cmd import monitor
        monitor.remove(cli.args.name, cli.args.id, cli.args.playlist)
    elif cli.args.command == "reset":
        logger.warning("** WARNING: Everything except for profiles will be erased! **")
        confirm = input(":: Type 'reset' to confirm: ")
        if confirm.lower() == "reset":
            print("")
            db.reset()
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
        pass
    elif cli.args.command == "test":
        from deemon.core.notifier import Notify
        notification = Notify()
        notification.test()
