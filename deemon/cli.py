import logging
from pathlib import Path

import requests

from deemon import VERSION
from deemon.core.logger import setup_logger
from deemon.core.config import Config
from deemon.utils import dataprocessor

import os
import argparse

from deemon.utils import paths

def show_whats_new():
    try:
        response = requests.get("https://api.github.com/repos/digitalec/deemon/releases")
    except requests.exceptions.ConnectionError:
        return print("Unable to reach GitHub API")

    for release in response.json():
        if release['name'] == VERSION:
            return print(release['body'])
    return print(f"Changelog for v{VERSION} was not found.")


parser = argparse.ArgumentParser(description=f'DEEMON_DESCRIPTION', formatter_class=argparse.RawTextHelpFormatter)

# Optional arguments
parser._optionals.title = 'Options'
parser._positionals.title = 'Commands'
parser.add_argument('--whats-new', action='store_true', help='show release notes from this version')
parser.add_argument('--profile', metavar='NAME', type=str, help='specify profile to use')
parser.add_argument('--portable', action='store_true', help='store deemon data in current directory')
parser.add_argument('-V', '--version', action='version', version=f"deemon {VERSION}", help='show version information')
parser.add_argument('-v', '--verbose', action='count', help='show verbose output; use -vv for increased output')
subparsers = parser.add_subparsers(dest='command')

# Backup command
backup_help_text = 'backup configuration and database'
parser_a = subparsers.add_parser('backup', help=backup_help_text, description=backup_help_text)
parser_a.add_argument('-i', '--include-logs', action='store_true', help='include log files in backup')
parser_a.add_argument('-r', '--restore', action='store_true', help='restore from existing backup')

# Config command
config_help_text = 'configure per-artist settings by name or ID'
parser_b = subparsers.add_parser('config', help=config_help_text, description=config_help_text)

# Download command
download_help_text = "download an artist, album ID or URL"
parser_c = subparsers.add_parser('download', help=download_help_text, description=download_help_text)
parser_c.add_argument('-A', '--album-id', metavar='ID', type=str, help='download by album ID')
parser_c.add_argument('-i', '--artist-id', metavar='ID', type=str, help='download by artist ID')
parser_c.add_argument('-u', '--url', metavar='URL', type=str, help='download by URL')
parser_c.add_argument('-m', '--monitored', action='store_true', help='download all monitored artists')
parser_c.add_argument('-f', '--file', metavar='FILE', type=str, help='download batch of artists '
                                                                     'and/or artist IDs from file')
parser_c.add_argument('-b', '--bitrate', default=None, metavar='BITRATE', type=str, help='specify bitrate')
parser_c.add_argument('-t', '--record-type', default=None, metavar='TYPE', type=str, help='specify record type')
parser_c.add_argument('-o', '--download-path', metavar='PATH', type=str, help='specify download path')
parser_c.add_argument('-a', '--after', metavar='YYYY-MM-DD', help='download if released after this date')
parser_c.add_argument('-B', '--before', metavar='YYYY-MM-DD', help='download if released before this date')

# Monitor command
monitor_help_text = 'monitor artists for new releases'
parser_d = subparsers.add_parser('monitor', help=monitor_help_text, description=monitor_help_text)
parser_d.add_argument('artist', nargs='*', type=str, help='monitor by artist name, separated by comma')
parser_d.add_argument('-i', '--artist-id', nargs='*', metavar='ID', type=str, help='monitor by artist ID, separated '
                                                                                   'by comma')
parser_d.add_argument('-a', '--alerts', action='store_true', default=None, help='enable new release alerts')
parser_d.add_argument('-b', '--bitrate', type=str, default=None, help='specify bitrate')
parser_d.add_argument('-D', '--download', action='store_true', help='download releases matching record type')
parser_d.add_argument('-o', '--download-path', type=str, help='specify download path')
parser_d.add_argument('-f', '--file', metavar='PATH', type=str,  help='monitor artists from file or directory')
parser_d.add_argument('-u', '--url', nargs='*', metavar='URL', type=str, help='monitor artist/playlist by URL, '
                                                                              'separated by comma')
parser_d.add_argument('-T', '--time-machine', metavar='YYYY-MM-DD', type=str, help='releases after this date '
                                                                                   'will be downloaded')
parser_d.add_argument('-t', '--record-type', default=None, metavar='TYPE', nargs='+', help='specify record type')

# Profile command
profile_help_text = 'add, modify and delete configuration profiles'
parser_e = subparsers.add_parser('profile', help=profile_help_text, description=profile_help_text)
parser_e.add_argument('-a', '--add', action='store_true', help='add new profile')
parser_e.add_argument('-m', '--modify', action='store_true', help='modify an existing profile')
parser_e.add_argument('-d', '--delete', action='store_true', help='delete an existing profile')

# Refresh command
refresh_help_text = 'check monitored artists for new releases'
parser_f = subparsers.add_parser('refresh', help=refresh_help_text, description=refresh_help_text)
parser_f.add_argument('-s', '--skip-download', action='store_true', help='skip downloading of releases')
parser_f.add_argument('-T', '--time-machine', metavar='YYYY-MM-DD', type=str, help='refresh as if it were this date')

# Remove command
remove_help_text = "remove an artist or playlist from monitoring"
parser_l = subparsers.add_parser('remove', help=remove_help_text, description=remove_help_text)
parser_l.add_argument('name', nargs='*', type=str, help='name of artist(s) to remove from monitoring')
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
# show_artist_help_text = 'Show currently monitored artists'
# parser_j_a = subparsers.add_parser('artists', help=show_artist_help_text, description=show_artist_help_text)
# parser_j_a.add_argument('-c', '--csv', action='store_true', help='Output artists as CSV')
# parser_j_a.add_argument('-e', '--export')

# Test command
test_help_text = 'test email server settings'
parser_k = subparsers.add_parser('test', help=test_help_text, description=test_help_text)

args = parser.parse_args()
print(args)

if args.whats_new:
    show_whats_new()

if args.portable:
    config_path = Path(os.getcwd())
else:
    config_path = paths.get_appdata_dir()

setup_logger(log_level='DEBUG' if args.verbose else 'INFO', log_file=Path(config_path / 'logs' / 'deemon.log'))
logger = logging.getLogger(__name__)
Config(config_path)
config = Config().CONFIG

if args.profile:
    # if args.profile in db.available_profiles()
    config["defaults"]["profile"] = args.profile

if args.command == 'backup':
    if args.restore:
        pass
    else:
        if args.include_logs:
            pass
    pass
elif args.command == 'config':
    pass
elif args.command == 'download':
    pass
elif args.command == 'monitor':
    # Validate settings
    config['alerts']['enabled'] = args.alerts
    config['defaults']['bitrate'] = args.bitrate
    config['defaults']['download_path'] = args.download_path
    config['defaults']['record_types'] = args.record_type
    config['runtime']['artist'] = dataprocessor.csv_to_list(args.artist)
    config['runtime']['artist_id'] = args.artist_id
    config['runtime']['download'] = args.download
    config['runtime']['file'] = args.file
    config['runtime']['url'] = args.url
    config['runtime']['time_machine'] = args.time_machine
elif args.command == 'profile':
    pass
elif args.command == 'refresh':
    pass
elif args.command == 'reset':
    pass
elif args.command == 'rollback':
    pass
elif args.command == 'search':
    pass
elif args.command == 'show':
    pass
elif args.command == 'test':
    pass