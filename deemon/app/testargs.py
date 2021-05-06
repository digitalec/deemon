import argparse
import sys
from pathlib import Path

def backup_path():
    appdata_path = Path("/home/seggleston/.config/deemon")

class CustomHelpFormatter(argparse.HelpFormatter):
    def _format_action(self, action):
        if type(action) == argparse._SubParsersAction:
            # inject new class variable for subcommand formatting
            subactions = action._get_subactions()
            invocations = [self._format_action_invocation(a) for a in subactions]
            self._subcommand_max_length = max(len(i) for i in invocations)

        if type(action) == argparse._SubParsersAction._ChoicesPseudoAction:
            # format subcommand help line
            subcommand = self._format_action_invocation(action) # type: str
            width = self._subcommand_max_length
            help_text = ""
            if action.help:
                help_text = self._expand_help(action)
            return "  {:{width}} -  {}\n".format(subcommand, help_text, width=width)

        elif type(action) == argparse._SubParsersAction:
            # process subcommand help section
            msg = '\n'
            for subaction in action._get_subactions():
                msg += self._format_action(subaction)
            return msg
        else:
            return super(CustomHelpFormatter, self)._format_action(action)


def command():
    if args.name:
        subparser.choices[args.name].print_help()
    else:
        print("Use help [name] to show help for given command")
        print("List of available commands:")
        print("\n".join(list(subparser.choices.keys())))


parser = argparse.ArgumentParser(add_help=False, formatter_class=CustomHelpFormatter)

subparser = parser.add_subparsers(dest="command", title="command")

# Help
parser_help = subparser.add_parser('help', help='show help')
parser_help.add_argument('name', nargs='?', help='command to show help for')
parser_help.set_defaults(command=command)

# Monitor
parser_monitor = subparser.add_parser('monitor', help='monitor artist by name or id')
parser_monitor._optionals.title = "options"
parser_monitor.add_argument('artist', help="artist id or artist name to monitor")
parser_monitor.add_argument('--remove', action='store_true', default=False,
                                  help='remove artist from monitoring')
parser_monitor.add_argument('--bitrate', type=int, choices=[1, 3, 9], metavar='N',
                                  help='options: 1 (MP3 128k), 3 (MP3 320k), 9 (FLAC)', default=3)
parser_monitor.add_argument('--record-type', metavar='TYPE', choices=['album', 'single', 'all'],
                                    default='all', help="specify record type (default: all | album, single)")

# Download
parser_download = subparser.add_parser('download', help='download specific artist or artist/album id')
parser_download._optionals.title = "options"
parser_download_mutex = parser_download.add_mutually_exclusive_group(required=True)
parser_download_mutex.add_argument('--artist', metavar='ARTIST', help='download all releases by artist')
parser_download_mutex.add_argument('--artist-id', metavar='N', help='download all releases by artist id')
parser_download_mutex.add_argument('--album-id', metavar='N', help='download all releases by album id')
parser_download.add_argument('--record-type', metavar='TYPE', choices=['album', 'single', 'all'],
                             help="specify record type (default: all | album, single)")


# Import
parser_import = subparser.add_parser('import', help='import list of artists from text, csv or directory')
parser_import._optionals.title = "options"
parser_import_mutex = parser_import.add_mutually_exclusive_group(required=True)
parser_import_mutex.add_argument('--file', type=str, metavar='PATH',
                                 help='list of artists stored as text list or csv')
parser_import_mutex.add_argument('--dir', type=str, metavar='PATH',
                                 help='parent directory containing individual artist directories')

# Export
parser_export = subparser.add_parser('export', help='export list of artists to csv')
parser_export._optionals.title = "options"
parser_export.add_argument('--output', type=str, metavar='PATH',
                           help='export to specified path')

# Show
parser_show = subparser.add_parser('show', help='show list of new releases, artists, etc.')
parser_show._optionals.title = "options"
parser_show_mutex = parser_show.add_mutually_exclusive_group(required=True)
parser_show_mutex.add_argument('--artists', action="store_true", help='show list of artists currently being monitored')
parser_show_mutex.add_argument('--new-releases', nargs='?', metavar="N", type=int, default="30",
                         help='show list of new releases from last N days (default: 30)')

# Backup
parser_backup = subparser.add_parser('backup', help='perform various backup functions')
parser_backup._optionals.title = "options"
parser_backup.add_argument('--config', action="store_true",
                           help='backup configuration', default=backup_path())
parser_backup.add_argument('--database', action="store_true",
                           help='backup database', default=backup_path())

# Alerts
parser_notify = subparser.add_parser('alerts', help='manage new release notifications')
parser_notify._optionals.title = "options"
parser_notify_mutex = parser_notify.add_mutually_exclusive_group(required=True)
parser_notify_mutex.add_argument('--setup', action='store_true', default=False,
                                 help='setup email server settings')
parser_notify_mutex.add_argument('--test', action='store_true', default=False,
                                 help='test email server settings')
parser_notify_mutex.add_argument('--enable', action='store_true', default=None,
                                 help='enable notifications')
parser_notify_mutex.add_argument('--disable', action='store_true', default=None,
                                 help='disable notifications')

# Config
parser_config = subparser.add_parser('config', help='view and modify configuration')
parser_config._optionals.title = "options"
parser_config_mutex = parser_config.add_mutually_exclusive_group(required=True)
parser_config_mutex.add_argument('--view', action='store_true', default=False,
                                 help='view current configuration')
parser_config_mutex.add_argument('--edit', action='store_true', default=False,
                                 help='edit configuration interactively')
parser_config_mutex.add_argument('--set', nargs=2, metavar=('PROPERTY', 'VALUE'),
                                 help='change value of specified property')
parser_config_mutex.add_argument('--reset', action='store_true', default=False,
                                 help='reset configuration to defaults')

parser._positionals.title = "commands"
parser._optionals.title = "options"

if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(0)

args = parser.parse_args()
args.command()