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
import argparse
import logging
import platform
from pathlib import Path

from deemon import __version__
from deemon.core.logger import logger
from deemon.utils.constants import RECORD_TYPES, BITRATES


class DeemonMain:

    usage_examples = """
Examples of usage:
  Monitor an artist for new releases:
    $ deemon monitor John Smith

  Monitor multiple artists for new releases:
    $ deemon monitor John Smith, The Sparrows
"""

    def __init__(self):
        self.args = self.process_args()

    def init_args(self):

        version = f"deemon v{__version__}"
        parser = argparse.ArgumentParser(
            prog='deemon',
            description=f'deemon is a deezer monitor that monitors artists for new releases',
            formatter_class=argparse.RawTextHelpFormatter,
            epilog=self.usage_examples,
        )

        # Optional arguments
        parser._optionals.title = 'Options'
        parser._positionals.title = 'Commands'
        parser.add_argument('--whats-new', action='store_true', help='show release notes from this version')
        parser.add_argument('-p', '--profile', metavar='ID', type=int, help='specify profile to use')
        parser.add_argument('--portable', action='store_true', help='store deemon data in current directory')
        parser.add_argument('-V', '--version', action='version', version=version)
        parser.add_argument('-v', '--verbose', action='count', help='show verbose output; use -vv for increased output')
        subparsers = parser.add_subparsers(dest='command')

        # Backup command
        backup_help_text = 'backup configuration and database'
        parser_a = subparsers.add_parser('backup', help=backup_help_text, description=backup_help_text)
        parser_a.add_argument('-i', '--include-logs', action='store_true', help='include log files in backup')
        parser_a.add_argument('-r', '--restore', action='store_true', help='restore from existing backup')

        # Download command
        download_help_text = "download an artist, album ID or URL"
        parser_c = subparsers.add_parser('download', help=download_help_text, description=download_help_text)
        parser_c.add_argument('-A', '--album-id', metavar='ID', type=str, help='download by album ID')
        parser_c.add_argument('-i', '--artist-id', metavar='ID', type=str, help='download by artist ID')
        parser_c.add_argument('-u', '--url', metavar='URL', type=str, help='download by URL')
        parser_c.add_argument('-m', '--monitored', action='store_true', help='download all monitored artists')
        parser_c.add_argument('-f', '--file', metavar='FILE', type=str, help='download batch of artists '
                                                                             'and/or artist IDs from file')
        parser_c.add_argument('-b', '--bitrate', type=str.upper, choices=BITRATES.values(), default=None,
                              metavar='BITRATE', help='specify bitrate')
        parser_c.add_argument('-t', '--record-types', type=str.lower, choices=RECORD_TYPES.values(), default=None,
                              metavar='TYPE', help='specify record type')
        parser_c.add_argument('-o', '--download-path', metavar='PATH', type=str, help='specify download path')
        parser_c.add_argument('-a', '--after', metavar='YYYY-MM-DD', help='download if released after this date')
        parser_c.add_argument('-B', '--before', metavar='YYYY-MM-DD', help='download if released before this date')

        # Monitor command
        monitor_help_text = 'monitor artists for new releases'
        parser_d = subparsers.add_parser('monitor', help=monitor_help_text, description=monitor_help_text)
        parser_d.add_argument('artist', nargs='*', type=str, help='monitor by artist name, separated by comma')
        parser_d.add_argument('-i', '--artist-id', nargs='*', metavar='ID', type=str,
                              help='monitor by artist ID, separated '
                                   'by comma')
        parser_d.add_argument('-b', '--bitrate', type=str.upper, choices=BITRATES.values(), default=None,
                              help='specify bitrate')
        parser_d.add_argument('-D', '--download', action='store_true', help='download releases matching record type')
        parser_d.add_argument('-o', '--download-path', type=str, help='specify download path')
        parser_d.add_argument('-f', '--file', nargs='*', metavar='PATH', type=str,
                              help='monitor artists from file or directory')
        parser_d.add_argument('-n', '--notify', action='store_true', default=None, help='enable new release notifications')
        parser_d.add_argument('-u', '--url', nargs='*', metavar='URL', type=str, help='monitor artist/playlist by URL, '
                                                                                      'separated by comma')
        parser_d.add_argument('-T', '--time-machine', metavar='YYYY-MM-DD', type=str, help='releases after this date '
                                                                                           'will be downloaded')
        parser_d.add_argument('-t', '--record-types', type=str.lower, choices=RECORD_TYPES.values(), default=None,
                              metavar='TYPE', nargs='+', help='specify record type')

        # Profile command
        profile_help_text = 'add, modify and delete configuration profiles'
        parser_e = subparsers.add_parser('profile', help=profile_help_text, description=profile_help_text)
        parser_e.add_argument('-a', '--add', action='store_true', help='add new profile')
        parser_e.add_argument('-m', '--modify', action='store_true', help='modify an existing profile')
        parser_e.add_argument('-d', '--delete', action='store_true', help='delete an existing profile')

        # Refresh command
        refresh_help_text = 'check monitored artists for new releases'
        parser_f = subparsers.add_parser('refresh', help=refresh_help_text, description=refresh_help_text)
        parser_f.add_argument('-s', '--skip-downloads', action='store_true', help='skip downloading of releases')
        parser_f.add_argument('-T', '--time-machine', metavar='YYYY-MM-DD', type=str,
                              help='refresh as if it were this date')

        # Remove command
        remove_help_text = "remove an artist or playlist from monitoring"
        parser_l = subparsers.add_parser('remove', help=remove_help_text, description=remove_help_text)
        parser_l.add_argument('name', nargs='*', metavar="name", type=str, help='remove name or ID from monitoring')
        parser_l.add_argument('-i', '--id', action='store_true', help='remove by ID rather than name')
        parser_l.add_argument('-p', '--playlist', action='store_true', help='remove playlist rather than artist')

        # Reset command
        reset_help_text = 'reset monitoring database for active profile'
        parser_g = subparsers.add_parser('reset', help=reset_help_text, description=reset_help_text)

        # Rollback command
        rollback_help_text = 'rollback a previous monitor or refresh transaction'
        parser_h = subparsers.add_parser('rollback', help=rollback_help_text, description=rollback_help_text)
        parser_h.add_argument('-v', '--view', action='store_true', help='view recent transactions')

        # Search command
        search_help_text = 'interactively search and download/monitor artists'
        parser_i = subparsers.add_parser('search', help=search_help_text, description=search_help_text)

        # Show command
        show_help_text = 'show monitored artists and latest releases'
        parser_j = subparsers.add_parser('show', help=show_help_text, description=show_help_text)
        parser_j_subparser = parser_j.add_subparsers()

        # Show - Artists command
        show_artist_help_text = 'show currently monitored artists'
        parser_j_a = parser_j_subparser.add_parser('artists', help=show_artist_help_text,
                                                   description=show_artist_help_text)
        parser_j_a.add_argument('-c', '--csv', action='store_true', help='Output artists as CSV')
        parser_j_a.add_argument('-e', '--export', type=Path, help='Export artist IDs to file')

        # Test command
        test_help_text = 'test email server settings'
        parser_k = subparsers.add_parser('test', help=test_help_text, description=test_help_text)

        return parser

    def process_args(self):
        args = self.init_args().parse_args()

        if args.verbose:
            logger.setLevel(logging.DEBUG)

        logger.debug(f"deemon v{__version__} started with args:")
        for k, v in vars(args).items():
            logger.debug(f"  {k}={v}")
        logger.debug(f"OS: {platform.system()}, Python: v{platform.python_version()}")

        return args

    def get_args(self):
        return self.args
