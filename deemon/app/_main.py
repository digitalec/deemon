from deezer import Deezer
from deemon.app.db import DB
from deemon.app.notify import EmailNotification
from deemon.app.dmi import DeemixInterface
from deemon.app import settings
from deemon import __version__
from packaging.version import parse as parse_version
from pathlib import Path
import requests
import argparse
import logging
import os
import sys

logger = logging.getLogger("deemon")


def parse_args():

    def backup_path():
        appdata_path = Path("/home/seggleston/.config/deemon")
        return appdata_path

    def command():
        if args.name:
            subparser.choices[args.name].print_help()
        else:
            parser.print_help()

    parser = argparse.ArgumentParser(add_help=False, formatter_class=CustomHelpFormatter)

    subparser = parser.add_subparsers(dest="command", title="command")

    # Help
    parser_help = subparser.add_parser('help', help='show help')
    parser_help.add_argument('name', nargs='?', help='command to show help for')
    parser_help.set_defaults(command=command)

    # Monitor
    parser_monitor = subparser.add_parser('monitor', help='monitor artist by name or id', add_help=False)
    parser_monitor._optionals.title = "options"
    parser_monitor.add_argument('artist', help="artist id or artist name to monitor")
    parser_monitor.add_argument('--remove', action='store_true', default=False,
                                help='remove artist from monitoring')
    parser_monitor.add_argument('--bitrate', type=int, choices=[1, 3, 9], metavar='N',
                                help='options: 1 (MP3 128k), 3 (MP3 320k), 9 (FLAC)', default=3)
    parser_monitor.add_argument('--record-type', metavar='TYPE', choices=['album', 'single', 'all'],
                                default='all', help="specify record type (default: all | album, single)")

    # Download
    parser_download = subparser.add_parser('download', help='download specific artist or artist/album id',
                                           add_help=False)
    parser_download._optionals.title = "options"
    parser_download_mutex = parser_download.add_mutually_exclusive_group(required=True)
    parser_download_mutex.add_argument('--artist', metavar='ARTIST', help='download all releases by artist')
    parser_download_mutex.add_argument('--artist-id', metavar='N', help='download all releases by artist id')
    parser_download_mutex.add_argument('--album-id', metavar='N', help='download all releases by album id')
    parser_download.add_argument('--record-type', metavar='TYPE', choices=['album', 'single', 'all'],
                                 help="specify record type (default: all | album, single)")

    # Show
    parser_show = subparser.add_parser('show', help='show list of new releases, artists, etc.', add_help=False)
    parser_show._optionals.title = "options"
    parser_show_mutex = parser_show.add_mutually_exclusive_group(required=True)
    parser_show_mutex.add_argument('--artists', action="store_true",
                                   help='show list of artists currently being monitored')
    parser_show_mutex.add_argument('--new-releases', nargs='?', metavar="N", type=int, default="30",
                                   help='show list of new releases from last N days (default: 30)')

    # Alerts
    parser_notify = subparser.add_parser('alerts', help='manage new release notifications', add_help=False)
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

    # Import
    parser_import = subparser.add_parser('import', help='import list of artists from text, csv or directory',
                                         add_help=False)
    parser_import._optionals.title = "options"
    parser_import_mutex = parser_import.add_mutually_exclusive_group(required=True)
    parser_import_mutex.add_argument('--file', type=str, metavar='PATH',
                                     help='list of artists stored as text list or csv')
    parser_import_mutex.add_argument('--dir', type=str, metavar='PATH',
                                     help='parent directory containing individual artist directories')

    # Export
    parser_export = subparser.add_parser('export', help='export list of artists to csv', add_help=False)
    parser_export._optionals.title = "options"
    parser_export.add_argument('--output', type=str, metavar='PATH',
                               help='export to specified path')

    # Backup
    parser_backup = subparser.add_parser('backup', help='perform various backup operations', add_help=False)
    parser_backup._optionals.title = "options"
    parser_backup.add_argument('--config', action="store_true",
                               help='backup configuration', default=backup_path())
    parser_backup.add_argument('--database', action="store_true",
                               help='backup database', default=backup_path())

    # Config
    parser_config = subparser.add_parser('config', help='view and modify configuration', add_help=False)
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
    return args


class Deemon:

    def __init__(self):
        args = parse_args()
        logger.debug(f"Args used: {args}")
        self.artists = args.file
        self.custom_download_path = args.download_path
        # TODO rename args.db_path
        self.custom_deemon_path = args.db_path
        self.custom_deemix_path = args.config_path
        self.bitrate = args.bitrate
        self.download_all = args.download_all
        self.record_type = args.record_type
        self.active_artists = []
        self.queue_list = []
        self.appdata_dir = settings.get_appdata_dir()
        self.config = settings.Settings()
        self.notify = EmailNotification(self.config.config)
        self.dz = Deezer()
        self.di = DeemixInterface(self.custom_download_path, self.custom_deemix_path)
        self.db = DB(self.config.db_path)

        if args.smtp_test:
            logger.info("Attempting to send test notification...")
            if self.notify.enable_notify:
                self.smtp_test()
            else:
                logger.error("SMTP server settings have not been configured.")
            exit()

    def smtp_test(self):
        self.notify.notify(test=True)

    @staticmethod
    def import_artists(artists):
        if os.path.isfile(artists):
            with open(artists) as text_file:
                list_of_artists = [a for a in text_file.read().splitlines() if a]
                return sorted(list_of_artists)
        elif os.path.isdir(artists):
            list_of_artists = os.listdir(artists)
            return sorted(list_of_artists)
        else:
            print(f"{artists}: not found")

    @staticmethod
    def check_for_updates(enabled=True):
        if enabled:
            response = requests.get("https://api.github.com/repos/digitalec/deemon/releases/latest")
            local_version = __version__
            remote_version = response.json()["name"]
            if parse_version(remote_version) > parse_version(local_version):
                print("*" * 44)
                print("New version available: " + remote_version)
                print("To update, run: pip install --upgrade deemon")
                print("*" * 44)

    def print_settings(self):
        quality = {1: 'MP3 128k', 3: 'MP3 320k', 9: 'FLAC'}

        if self.download_all:
            download = "all"
        else:
            download = "only new"

        if not self.record_type:
            rtype = "any"
        else:
            rtype = self.record_type

        logger.info("----------------------------")

        if self.notify.enable_notify:
            logger.info("Notifications: enabled")
        else:
            logger.info("Notifications: disabled (not configured)")
            logger.debug("* New release notifications disabled: SMTP server settings have not been configured.")

        logger.info(f"Bitrate: {quality[self.bitrate]} / Download: {download} / Record Type: {rtype}")

    def download_queue(self, queue):
        if queue:
            # move notify_releases to notify Class attribute
            notify_releases = []
            num_queued = len(queue)
            logger.info("----------------------------")
            logger.info("** Here we go! Starting download of " + str(num_queued) + " release(s):")
            for q in queue:
                notify_releases.append(q.artist_name + " - " + q.album_title)
                logger.info(f"Downloading {q.artist_name} - {q.album_title}... ")
                self.di.download_url([q.url], self.bitrate)

            self.notify.notify(notify_releases)

    def get_new_releases(self, artist):
        new_artist = False
        self.active_artists.append(artist["id"])
        artist_exists = self.db.check_exists(artist_id=artist["id"])
        if not artist_exists:
            new_artist = True

        new_release_count = 0
        albums = self.dz.api.get_artist_albums(artist["id"])
        for album in albums["data"]:
            already_exists = self.db.check_exists(album_id=album["id"])

            if already_exists:
                continue

            if (new_artist and self.download_all) or (not new_artist):
                if (self.record_type and self.record_type == album["record_type"]) or (not self.record_type):
                    self.queue_list.append(QueueItem(artist, album))

            new_release_count += 1
            self.db.add_new_release(artist["id"], album["id"])
        return new_release_count

    def main(self):
        self.check_for_updates()
        self.print_settings()
        logger.info("Verifying ARL...")
        if not self.di.login():
            logger.critical("ARL verification failed. ")
            exit(1)
        logger.info("----------------------------")
        logger.info("Checking for new releases...")
        logger.info("----------------------------")
        # TODO move this to function and add validation and error checking
        for line in self.import_artists(self.artists):
            try:
                artist = self.dz.api.search_artist(line, limit=1)['data'][0]
                logger.debug(f"Found result - artist_id: {artist['id']}, artist_name: {artist['name']}")
            except IndexError:
                logger.error(f"Artist '{line}' not found")
                continue

            new_releases = self.get_new_releases(artist)
            logger.info(f"{line}: {new_releases} release(s)")

        num_purged = self.db.purge_unmonitored_artists(self.active_artists)
        if num_purged:
            logger.info(f"Purged {num_purged} artist(s) from database")

        self.download_queue(self.queue_list)

        self.db.commit_and_close()


class QueueItem:

    def __init__(self, artist: dict, album: dict):
        self.artist_name = artist["name"]
        self.album_id = album["id"]
        self.album_title = album["title"]
        self.url = album["link"]


class CustomHelpFormatter(argparse.HelpFormatter):

    def _format_action(self, action):
        if type(action) == argparse._SubParsersAction:
            subactions = action._get_subactions()
            invocations = [self._format_action_invocation(a) for a in subactions]
            self._subcommand_max_length = max(len(i) for i in invocations)

        if type(action) == argparse._SubParsersAction._ChoicesPseudoAction:
            subcommand = self._format_action_invocation(action) # type: str
            width = self._subcommand_max_length
            help_text = ""
            if action.help:
                help_text = self._expand_help(action)
            return "  {:{width}} -  {}\n".format(subcommand, help_text, width=width)

        elif type(action) == argparse._SubParsersAction:
            msg = '\n'
            for subaction in action._get_subactions():
                msg += self._format_action(subaction)
            return msg
        else:
            return super(CustomHelpFormatter, self)._format_action(action)

if __name__ == "__main__":
    Deemon().main()
