from deemon.app.db import DB
from deemon.app.notify import EmailNotification
from deemon.app.dmi import DeemixInterface
from deemon.app import settings
from datetime import datetime
from deemon import __version__
from packaging.version import parse as parse_version
from pathlib import Path
import deezer
import tarfile
import requests
import argparse
import logging
import os
import sys

logger = logging.getLogger("deemon")


class CustomHelpFormatter(argparse.HelpFormatter):

    def _format_action(self, action):
        if type(action) == argparse._SubParsersAction:
            subactions = action._get_subactions()
            invocations = [self._format_action_invocation(a) for a in subactions]
            self._subcommand_max_length = max(len(i) for i in invocations)

        if type(action) == argparse._SubParsersAction._ChoicesPseudoAction:
            subcommand = self._format_action_invocation(action)  # type: str
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


class Deemon:

    def __init__(self):
        self.parser = argparse.ArgumentParser(usage="%(prog)s", add_help=False,
                                              formatter_class=CustomHelpFormatter)
        self.parser._positionals.title = "commands"
        self.parser._optionals.title = "options"

        self.subparser = self.parser.add_subparsers(dest="command", title="command")

        # Help
        parser_help = self.subparser.add_parser('help', help='show help')
        parser_help.add_argument('name', nargs='?', help='command to show help for')
        # parser_help.set_defaults(command=self.sub_help)

        # Monitor
        parser_monitor = self.subparser.add_parser('monitor', help='monitor artist by name or id', add_help=False)
        parser_monitor._positionals.title = "commands"
        parser_monitor._optionals.title = "options"
        parser_monitor.add_argument('artist', nargs='*', help="artist id or artist name to monitor")
        parser_monitor.add_argument('--remove', action='store_true', default=False,
                                    help='remove artist from monitoring')
        parser_monitor.add_argument('--bitrate', type=int, choices=[1, 3, 9], metavar='N',
                                    help='options: 1 (MP3 128k), 3 (MP3 320k), 9 (FLAC)', default=3)
        parser_monitor.add_argument('--record-type', metavar='TYPE', choices=['album', 'single', 'all'],
                                    default='all', help="specify record type (default: all | album, single)")
        parser_monitor.add_argument('--alerts', dest='alerts', action='store_true', default=False,
                                    help='disable new release alerts for artist')

        # Refresh
        parser_refresh = self.subparser.add_parser('refresh', help='check for new releases', add_help=False)
        parser_refresh.add_argument('--no-download', action='store_true', default=False,
                                    help='only update database, do not download releases')

        # Download
        parser_download = self.subparser.add_parser('download', help='download specific artist or artist/album id',
                                                    add_help=False)
        parser_download._optionals.title = "options"
        parser_download_mutex = parser_download.add_mutually_exclusive_group(required=True)
        parser_download_mutex.add_argument('--artist', metavar='ARTIST', help='download all releases by artist')
        parser_download_mutex.add_argument('--artist-id', metavar='N', help='download all releases by artist id')
        parser_download_mutex.add_argument('--album-id', metavar='N', help='download all releases by album id')
        parser_download.add_argument('--album', metavar='ALBUM', help='download specific album by artist')
        parser_download.add_argument('--record-type', metavar='TYPE', choices=['album', 'single', 'all'],
                                     help="specify record type (default: all | album, single)")

        # Show
        parser_show = self.subparser.add_parser('show', help='show list of new releases, artists, etc.', add_help=False)
        parser_show._optionals.title = "options"
        parser_show_mutex = parser_show.add_mutually_exclusive_group(required=True)
        parser_show_mutex.add_argument('--artists', action="store_true",
                                       help='show list of artists currently being monitored')
        parser_show_mutex.add_argument('--new-releases', nargs='?', metavar="N", type=int, default="30",
                                       help='show list of new releases from last N days (default: 30)')

        # Alerts
        parser_alerts = self.subparser.add_parser('alerts', help='manage new release notifications', add_help=False)
        parser_alerts._optionals.title = "options"
        parser_alerts_mutex = parser_alerts.add_mutually_exclusive_group(required=True)
        parser_alerts_mutex.add_argument('--setup', action='store_true', default=False,
                                         help='setup email server settings')
        parser_alerts_mutex.add_argument('--test', action='store_true', default=False,
                                         help='test email server settings')
        parser_alerts_mutex.add_argument('--enable', action='store_true', default=None,
                                         help='enable notifications')
        parser_alerts_mutex.add_argument('--disable', action='store_true', default=None,
                                         help='disable notifications')

        # Import
        parser_import = self.subparser.add_parser('import',
                                                  help='import list of artists from text list, csv or a directory',
                                                  add_help=False)
        parser_import._positionals.title = "commands"
        parser_import._optionals.title = "options"
        parser_import.add_argument('path', metavar='PATH',
                                         help='list of artists stored as text list, csv or a directory')

        # Export
        parser_export = self.subparser.add_parser('export', help='export list of artists to csv', add_help=False)
        parser_export._positionals.title = "commands"
        parser_export._optionals.title = "options"
        parser_export.add_argument('path', type=str, metavar='PATH', help='export to specified path')

        # Backup
        parser_backup = self.subparser.add_parser('backup', help='backup config and database', add_help=False)

        # Config
        parser_config = self.subparser.add_parser('config', help='view and modify configuration', add_help=False)
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

        # if len(sys.argv) == 1:
        #     self.parser.print_help()
        #     sys.exit(0)

        self.args = self.parser.parse_args()
        self.config = settings.Settings()
        logger.debug(f"Args: {self.args}")
        self.queue_list = []
        self.custom_download_path = None
        self.custom_deemix_path = None
        self.appdata_dir = settings.get_appdata_dir()
        self.notify = EmailNotification(self.config.config)
        self.db = DB(self.config.db_path)
        self.dz = deezer.Deezer()
        self.di = DeemixInterface(self.custom_download_path, self.custom_deemix_path)

    def deemix_login(self):
        logger.info("Verifying ARL...")
        if not self.di.login():
            logger.critical("ARL verification failed. ")
            exit(1)

    def monitor(self, artist, remove, bitrate, record_type, alerts, loop=False):
        '''
        Adds artists to database to be monitored
        Supports comma separated list or individual artist names
        :return: None
        '''

        alerts = int(alerts)
        artist = " ".join(list(artist))
        artist = artist.split(",")

        logger.info(f"Processing artists: {artist}")

        for _artist in artist:

            try:
                _artist = int(_artist)
            except ValueError:
                pass

            if type(_artist) == int:
                api_artist = self.dz.api.get_artist(_artist)
            else:
                try:
                    api_artist = self.dz.api.search_artist(_artist, limit=1)['data'][0]
                except IndexError:
                    logger.warning(f"WARNING: Artist '{_artist}' was not found")
                    continue

            artist = api_artist["name"]
            artist_id = api_artist["id"]

            if remove:
                self.db.stop_monitoring(artist)
            elif not self.db.is_monitored(artist_id):
                self.db.start_monitoring(artist_id, artist, bitrate, record_type, alerts)

        if not loop:
            self.db.commit_and_close()
            sys.exit(0)

    def do_nothing(self):
        pass

    def show(self):
        if self.args.artists:
            monitored = self.db.get_all_artists()
            if len(monitored) == 0:
                print("No artists currently being monitored")
            else:
                artist_data = []
                for m in monitored:
                    artist = m[1]
                    bitrate = m[2]
                    record_type = m[3]
                    alerts = m[4]

                    if alerts == 0:
                        alerts = "off"
                    if alerts == 1:
                        alerts = "on"

                    if bitrate == 1:
                        bitrate = "128k"
                    if bitrate == 3:
                        bitrate = "320k"
                    if bitrate == 9:
                        bitrate = "FLAC"

                    if record_type == "all":
                        record_type = "all"
                    if record_type == "album":
                        record_type = "album"
                    if record_type == "ep":
                        record_type = "ep"
                    if record_type == "single":
                        record_type = "single"

                    artist_data.append(f"{artist} [{bitrate}, {record_type}, {alerts}]")

                print("Monitored Artists\n\n")

                if len(artist_data) > 3:
                    for a, b, c in zip(artist_data[::3], artist_data[1::3], artist_data[2::3]):
                        print('{:<30}{:<30}{:<}'.format(a, b, c))
                else:
                    for d in artist_data:
                        print(d)

                print("\n\nLegend: [bitrate, type, alerts]")
        else:
            print("Check releases for last N days")
        sys.exit(0)

    def download(self):
        self.deemix_login()
        artist_id = self.args.artist_id
        artist_name = self.args.artist
        album_id = self.args.album_id
        album_name = self.args.album
        record_type = self.args.record_type

        if artist_id:
            artist = self.dz.api.get_artist(artist_id)
            artist_name = artist["name"]
        elif artist_name:
            artist = self.dz.api.search_artist(artist_name, limit=1)['data'][0]
            artist_id = artist["id"]

        if album_id:
            album = {'data': [self.dz.api.get_album(album_id)]}
        elif album_name:
            album = self.dz.api.search_album(f'{artist_name} {album_name}', limit=1)
            if album['total'] == 0:
                logger.error(f"Album '{album_name}' was not found by artist '{artist_name}'")
                sys.exit(0)
        else:
            album = self.dz.api.get_artist_albums(artist_id)

        for _album in album['data']:
            if (record_type and record_type == _album["record_type"]) or (not record_type):
                logger.debug(f"QUEUE: Adding '{_album['title']}' to queue...")
                self.queue_list.append(QueueItem(artist, _album))

        self.download_queue(self.queue_list)

        sys.exit(0)

    def backup(self):
        backup_tar = datetime.today().strftime('%Y%m%d-%H%M%S') + ".tar"
        backup_path = Path(self.backup_path() / "backups")

        if not backup_path.is_dir():
            logger.debug(f"creating backup directory at {backup_path}")
            # TODO needs error handling
            Path(backup_path).mkdir(exist_ok=True)

        with tarfile.open(backup_path / backup_tar, "w") as tar:
                tar.add(self.config.config_path, "deemon/")
                tar.add(self.config.db_path, "deemon/")
                logger.info(f"Backed up to {backup_path / backup_tar}")

    def export_artists(self, export_path):
        export_file = Path(export_path / "deemon-artists.csv")
        with open(export_file, "w"):
            artist_dump = self.db.get_all_artists()
            for line in artist_dump:
                print(line)
        sys.exit(0)


    def import_artists(self):

        import_artists = self.args.path
        bitrate = self.config.config["bitrate"]
        record_type = self.config.config["record_type"]
        alerts = int(self.config.config["alerts_enabled"])
        # TODO check db for existing artist
        if import_artists:
            if Path(import_artists).is_file():
                with open(import_artists) as f:
                    import_list = f.read().splitlines()
            elif Path(import_artists).is_dir():
                import_list = os.listdir(import_artists)
                print(import_list)
            else:
                logger.error("Unrecognized import type")
                sys.exit(1)

            use_defaults = input("Use default import settings? (Y/n) ")
            if use_defaults.lower() == "n":

                # TODO move this to settings.py and use globally
                default_choices = {
                    "bitrate": {
                        "128": 1,
                        "320": 3,
                        "FLAC": 9
                    },
                    "record_type": ['all', 'album', 'ep', 'single'],
                    "alerts": {
                        "y": 1,
                        "n": 0
                    }
                }

                bitrate_opts = default_choices["bitrate"]
                bitrate_default = ([k for k, v in bitrate_opts.items() if v == bitrate][0])
                record_type_default = record_type
                alert_opts = default_choices["alerts"]
                alert_default = ([k for k, v in alert_opts.items() if v == alerts][0])
                alert_friendly = {}
                for k, v in alert_opts.items():
                    if v == alerts:
                        alert_friendly[k.upper()] = v
                    else:
                        alert_friendly[k] = v

                for artist in import_list:
                    print(f"Artist: {artist}")
                    user_bitrate, user_record_type, user_alerts = "", "", ""

                    # BITRATE
                    bitrate_names = ", ".join(list(bitrate_opts.keys()))
                    while user_bitrate not in bitrate_opts:
                        user_bitrate = input(f"Enter bitrate ({bitrate_names} "
                                             f"[{bitrate_default}]): ").upper() or bitrate_default

                    bitrate = bitrate_opts[user_bitrate]

                    # RECORD TYPE
                    record_type_opts = ", ".join(default_choices["record_type"])
                    while user_record_type.lower() not in default_choices["record_type"]:
                        user_record_type = input(f"Enter record type ({record_type_opts} "
                                                 f"[{record_type_default}]): ") or record_type_default
                    record_type = user_record_type

                    # ALERTS
                    alert_names = "/".join(list(alert_friendly.keys()))
                    while user_alerts not in alert_opts:
                        user_alerts = input(f"Enable new release notifications "
                                            f"for this artist? ({alert_names}) ").lower() or alert_default
                    alerts = alert_opts[user_alerts]
                    self.monitor(artist=[artist], remove=False, bitrate=bitrate,
                                 record_type=record_type, alerts=alerts, loop=True)
                self.db.commit_and_close()
                sys.exit(0)
            else:
                for artist in import_list:
                    self.monitor(artist=[artist], remove=False, bitrate=bitrate,
                                 record_type=record_type, alerts=alerts, loop=True)

        sys.exit(0)

    def refresh(self, skip_download=False):
        self.deemix_login()
        monitored_artists = self.db.get_all_artists()
        new_release_counter = 0
        new_artist = False

        if not len(monitored_artists) > 0:
            logger.error("No artists are currently being monitored")
            sys.exit(0)

        for _artist in monitored_artists:
            artist = {"id": _artist[0], "name": _artist[1], "bitrate": _artist[2]}
            record_type = _artist[3]
            alerts = _artist[4]
            artist_exists = self.db.check_exists(artist_id=artist["id"])
            if not artist_exists:
                new_artist = True
                logger.info(f"New artist detected: {artist['name']}, future releases will be downloaded")

            albums = self.dz.api.get_artist_albums(artist["id"])
            for album in albums["data"]:
                already_exists = self.db.check_exists(album_id=album["id"])

                if already_exists or skip_download or new_artist:
                    continue

                new_release_counter += 1
                self.db.add_new_release(artist["id"], album["id"], album["release_date"])

                if (record_type == album["record_type"]) or (record_type == "all"):
                    logger.debug(f"queue: added {artist['name']} - {album['title']} to the queue")
                    self.queue_list.append(QueueItem(artist, album))

        self.download_queue(self.queue_list)
        self.db.commit_and_close()
        sys.exit(0)

    def main(self):

        if self.args.command == "help":
            if self.args.name:
                self.subparser.choices[self.args.name].print_help()
            else:
                self.parser.print_help()
            sys.exit(0)

        if self.args.command == "monitor":
            if not self.args.artist:
                self.subparser.choices["monitor"].print_help()
                sys.exit(1)
            else:
                self.monitor(self.args.artist, self.args.remove,
                             self.args.bitrate, self.args.record_type, self.args.alerts)

        if self.args.command == "refresh":
            self.refresh(skip_download=self.args.no_download)

        if self.args.command == "download":
            self.download()

        if self.args.command == "show":
            self.show()

        if self.args.command == "alerts":
            print(self.args)

        if self.args.command == "import":
            self.import_artists()

        if self.args.command == "export":
            self.export_artists(self.args.path)

        if self.args.command == "backup":
            self.backup()

        elif self.args.command == "config":
            print(self.args)
        else:
            self.parser.print_help()

    def download_queue(self, queue):
        if queue:
            num_queued = len(queue)
            logger.info("----------------------------")
            logger.info("Sending " + str(num_queued) + " release(s) to deemix for download:")
            for q in queue:
                logger.info(f"Downloading {q.artist_name} - {q.album_title}... ")
                self.di.download_url([q.url], q.bitrate)

    @staticmethod
    def backup_path():
        appdata_path = Path("/home/seggleston/.config/deemon")
        return appdata_path


class QueueItem:

    def __init__(self, artist: dict, album: dict):
        self.artist_name = artist["name"]
        self.bitrate = artist["bitrate"]
        self.album_id = album["id"]
        self.album_title = album["title"]
        self.url = album["link"]


if __name__ == "__main__":
    Deemon().main()
