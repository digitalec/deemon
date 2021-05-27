from deemon.app.db import DB
from deemon.app.notify import EmailNotification
from deemon.app.dmi import DeemixInterface
from deemon.app import settings
from deemon import __version__
from datetime import datetime
from pathlib import Path
import deezer
import sqlite3
import tarfile
import argparse
import logging
import os
import sys
import time

logger = logging.getLogger("deemon")


class deemonArgParser(argparse.ArgumentParser):

    def error(self, message):
        self.print_help()
        sys.exit()


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


class Download:
    def __init__(self):
        self.settings = settings.Settings()
        self.custom_download_path = None
        self.custom_deemix_path = None
        self.queue_list = []
        self.db = DB(self.settings.db_path)
        self.dz = deezer.Deezer()
        self.di = DeemixInterface(self.custom_download_path, self.custom_deemix_path)
        self.notify = EmailNotification(self.settings.config)

    def deemix_login(self):
        logger.info("Verifying ARL...")
        if not self.di.login():
            logger.critical("ARL verification failed. ")
            exit(1)

    def refresh(self, artists=[], skip_download=False):
        logger.info("Refreshing artists...")
        if not artists:
            monitored_artists = self.db.get_all_artists()
        else:
            monitored_artists = self.db.get_specified_artists(artists)
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
                logger.debug(f"New artist detected: {artist['name']}, future releases will be downloaded")

            albums = self.dz.api.get_artist_albums(artist["id"])
            for album in albums["data"]:
                already_exists = self.db.check_exists(album_id=album["id"])
                if not already_exists:
                    self.db.add_new_release(artist["id"], artist["name"], album["id"], album["title"], album["release_date"])

                if already_exists or skip_download or new_artist:
                    continue

                new_release_counter += 1

                if (record_type == album["record_type"]) or (record_type == "all"):
                    logger.debug(f"queue: added {artist['name']} - {album['title']} to the queue")
                    self.queue_list.append(QueueItem(artist, album))
        logger.info("Refresh complete")
        if self.queue_list:
            self.download_queue(self.queue_list)
        self.db.commit()

    def download_queue(self, queue):
        self.deemix_login()
        if queue:
            num_queued = len(queue)
            logger.info("----------------------------")
            logger.info("Sending " + str(num_queued) + " release(s) to deemix for download:")
            for q in queue:
                logger.info(f"Downloading {q.artist_name} - {q.album_title}... ")
                self.di.download_url([q.url], q.bitrate)

    def download(self, artist_id, artist_name, album_id, album_name, record_type, bitrate):

        if artist_id:
            artist = self.dz.api.get_artist(artist_id)
            artist_name = artist["name"]
        else:
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
                artist["bitrate"] = bitrate
                self.queue_list.append(QueueItem(artist, _album))

        self.download_queue(self.queue_list)

        sys.exit(0)


class MonitorArtist:

    def __init__(self, name=None, aid=None):
        self.settings = settings.Settings()
        self.artist_name = name
        self.artist_id = aid
        self.bitrate = self.settings.config['bitrate']
        self.record_type = self.settings.config['record_type']
        self.alerts = self.settings.config['alerts']
        self.dz = deezer.Deezer()
        self.db = DB(self.settings.db_path)

    def get_artist_info(self):
        if self.artist_id:
            try:
                artist = self.dz.api.get_artist(self.artist_id)
                self.artist_name = artist["name"]
                return True
            except deezer.api.DataException:
                logger.warning(f"Artist ID '{self.artist_id}' not found")
                return False

        if self.artist_name:
            try:
                artist = self.dz.api.search_artist(self.artist_name, limit=1)['data'][0]
                self.artist_id = artist["id"]
                return True
            except IndexError:
                logger.warning(f"WARNING: Artist '{self.artist_name}' was not found")
                return False

    def start_monitoring(self, silent=False):
        artist_info = self.get_artist_info()
        if artist_info:
            sql = ("INSERT OR REPLACE INTO monitor (artist_id, artist_name, bitrate, record_type, alerts) "
                   "VALUES (:artist_id, :artist_name, :bitrate, :record_type, :alerts)")
            values = {
                'artist_id': self.artist_id,
                'artist_name': self.artist_name,
                'bitrate': self.bitrate,
                'record_type': self.record_type,
                'alerts': self.alerts
            }

            try:
                result = self.db.query(sql, values)
            except sqlite3.OperationalError as e:
                logger.error(e)

            if not silent:
                logger.info(f"Now monitoring {self.artist_name}")
            else:
                logger.debug(f"Now monitoring {self.artist_name}")

            self.db.commit()

    def stop_monitoring(self):
        sql_releases = "DELETE FROM 'releases' WHERE artist_name LIKE :name"
        sql_monitor = "DELETE FROM 'monitor' WHERE artist_name = :name"
        values = {'name': self.artist_name}
        self.db.query(sql_releases, values)
        result = self.db.query(sql_monitor, values)
        if result.rowcount > 0:
            logger.info(f"No longer monitoring {self.artist_name}")
        else:
            logger.error(f"Artist '{self.artist_name}' is not being monitored")

        self.db.commit_and_close()


class Deemon:

    def __init__(self):
        self.settings = settings.Settings()
        self.settings.init_log()
        self.settings.load_config()
        self.args = self.cli()
        if self.args.verbose:
            logger.setLevel(logging.DEBUG)
        self.appdata_dir = settings.get_appdata_dir()
        self.dz = deezer.Deezer()
        self.db = DB(self.settings.db_path)
        # TODO move DMI to be called on an as needed basis to improve performance
        # self.
        logger.debug(f"Args: {self.args}")
        self.args.func()

    def cli(self):
        self.parser = deemonArgParser(usage="%(prog)s " + __version__, add_help=False,
                                              formatter_class=CustomHelpFormatter)
        self.parser._positionals.title = "commands"
        self.parser._optionals.title = "options"
        self.parser.set_defaults(func=self.parser.print_help)

        self.subparser = self.parser.add_subparsers(dest="command", title="command")

        # Help
        parser_help = self.subparser.add_parser('help', help='show help')
        parser_help.add_argument('name', nargs='?', help='command to show help for')
        parser_help.set_defaults(func=self.help)

        # Monitor
        self.parser_monitor = self.subparser.add_parser('monitor', help='monitor artist by name or id', add_help=False)
        self.parser_monitor.set_defaults(func=self.monitor)
        self.parser_monitor._positionals.title = "commands"
        self.parser_monitor._optionals.title = "options"
        self.parser_monitor.add_argument('artist', nargs='*', help="artist id or artist name to monitor")
        self.parser_monitor.add_argument('--remove', action='store_true', default=False,
                                    help='remove artist from monitoring')
        self.parser_monitor.add_argument('--bitrate', type=int, choices=[1, 3, 9], metavar='N',
                                    help='options: 1 (MP3 128k), 3 (MP3 320k), 9 (FLAC)', default=3)
        self.parser_monitor.add_argument('--record-type', metavar='TYPE', choices=['album', 'single', 'all'],
                                    default='all', help="specify record type (default: all | album, single)")
        self.parser_monitor.add_argument('--alerts', dest='alerts', action='store_true', default=False,
                                    help='disable new release alerts for artist')

        # Refresh
        parser_refresh = self.subparser.add_parser('refresh', help='check for new releases', add_help=False)
        parser_refresh.add_argument('--no-download', action='store_true', default=False,
                                    help='only update database, do not download releases')
        parser_refresh.set_defaults(func=self.download)

        # Download
        self.parser_download = self.subparser.add_parser('download', help='download specific artist or artist/album id',
                                                    add_help=False)
        self.parser_download._optionals.title = "options"
        self.parser_download.set_defaults(func=self.download)
        self.parser_download_mutex = self.parser_download.add_mutually_exclusive_group(required=True)
        self.parser_download_mutex.add_argument('--artist', metavar='ARTIST', nargs='*',
                                           help='download all releases by artist')
        self.parser_download_mutex.add_argument('--artist-id', metavar='N', help='download all releases by artist id')
        self.parser_download_mutex.add_argument('--album-id', metavar='N', help='download all releases by album id')
        self.parser_download.add_argument('--album', metavar='ALBUM', help='download specific album by artist')
        self.parser_download.add_argument('--record-type', metavar='TYPE', choices=['album', 'single', 'all'],
                                     help="specify record type (default: all | album, single)")
        self.parser_download.add_argument('--bitrate', metavar='N', choices=[1, 3, 9], help="1=128K, 3=320K, 9=FLAC",
                                     default=self.settings.config["bitrate"])

        # Show
        parser_show = self.subparser.add_parser('show', help='show list of new releases, artists, etc.', add_help=False)
        parser_show._optionals.title = "options"
        parser_show.set_defaults(func=self.show)
        parser_show_mutex = parser_show.add_mutually_exclusive_group(required=True)
        parser_show_mutex.add_argument('--artists', action="store_true",
                                       help='show list of artists currently being monitored')
        parser_show_mutex.add_argument('--new-releases', metavar="N", type=int, default="30",
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
        parser_import.set_defaults(func=self.import_artists)
        parser_import.add_argument('path', metavar='PATH',
                                   help='list of artists stored as text list, csv or a directory')

        # Export
        parser_export = self.subparser.add_parser('export', help='export list of artists to csv', add_help=False)
        parser_export._positionals.title = "commands"
        parser_export._optionals.title = "options"
        parser_export.set_defaults(func=self.export_artists)
        parser_export.add_argument('path', type=str, metavar='PATH', help='export to specified path')

        # Backup
        parser_backup = self.subparser.add_parser('backup', help='backup config and database', add_help=False)
        parser_backup.set_defaults(func=self.backup)

        # Config
        parser_config = self.subparser.add_parser('config', help='view and modify configuration', add_help=False)
        parser_config._optionals.title = "options"
        parser_config.set_defaults(func=self.config)
        parser_config_mutex = parser_config.add_mutually_exclusive_group(required=True)
        parser_config_mutex.add_argument('--view', action='store_true', default=False,
                                         help='view current configuration')
        parser_config_mutex.add_argument('--edit', action='store_true', default=False,
                                         help='edit configuration interactively')
        parser_config_mutex.add_argument('--set', nargs=2, metavar=('PROPERTY', 'VALUE'),
                                         help='change value of specified property')
        parser_config_mutex.add_argument('--reset', action='store_true', default=False,
                                         help='reset configuration to defaults')

        # Switches
        self.parser.add_argument('-v', '--verbose', action='store_true', default=False,
                                 help='enable verbose output')

        return self.parser.parse_args()

    def monitor(self):
        if not self.args.artist:
            self.parser_monitor.print_help()
            sys.exit(1)

        artists = ' '.join(self.args.artist)
        artists = artists.split(',')
        dl = Download()
        for artist in artists:
            ma = MonitorArtist()
            ma.artist_name = artist.lstrip()
            ma.bitrate = self.args.bitrate
            ma.record_type = self.args.record_type
            ma.alerts = self.args.alerts

            if self.args.remove:
                ma.stop_monitoring()
            else:
                ma.start_monitoring()

        dl.refresh(artists)
        sys.exit(0)

    def download(self):
        dl = Download()
        if self.args.command == "refresh":
            dl.refresh(skip_download=self.args.no_download)
        else:
            artist = ' '.join(self.args.artist)
            dl.download(self.args.artist_id, artist, self.args.album_id,
                        self.args.album, self.args.record_type, self.args.bitrate)

    def show(self):
        if self.args.artists:
            monitored = self.db.get_all_artists()
            if len(monitored) == 0:
                print("No artists currently being monitored")
            else:
                artist_data = []
                for m in monitored:
                    artist = m[1][:16]
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

                logger.info("Viewing: Monitored Artists\n\n")

                if len(artist_data) > 3:
                    for a, b in zip(artist_data[::2], artist_data[1::2]):
                        print('{:<40}{:<}'.format(a, b))
                else:
                    for d in artist_data:
                        print(d)

                print("\n\nLegend: [bitrate, album type, alerts]")
        elif self.args.new_releases:
            days = self.args.new_releases
            days_in_seconds = (days * 86400)
            now = int(time.time())
            get_time = (now - days_in_seconds)
            #TODO this should check by album release date to be more useful
            releases = self.db.show_new_releases(get_time)
            logger.info(f"New releases found within last {days} day(s):")
            print("")
            for release in releases:
                logger.info(f"{release[1]} - {release[3]}")

        sys.exit(0)

    def backup(self):
        backup_tar = datetime.today().strftime('%Y%m%d-%H%M%S') + ".tar"
        backup_path = Path(self.settings.config_path / "backups")

        if not backup_path.is_dir():
            logger.debug(f"creating backup directory at {backup_path}")
            # TODO needs error handling
            Path(backup_path).mkdir(exist_ok=True)

        with tarfile.open(backup_path / backup_tar, "w") as tar:
            tar.add(self.settings.db_path, arcname="releases.db")
            logger.info(f"Backed up to {backup_path / backup_tar}")

    def config(self):

        def view(prop=None):
            if prop:
                values = {'prop': prop}
                result = self.db.query("SELECT * FROM config WHERE property = :prop", values).fetchall()
            else:
                result = self.db.query("SELECT * FROM config").fetchall()

            for row in result:
                logger.info(f"{row[0]}: {row[1]}")

        def prop_exists(prop):
            values = {'prop': prop}
            result = self.db.query("SELECT * FROM config WHERE property = :prop", values).fetchone()
            if result:
                return True

        def get_allowed_values(prop):
            values = {'prop': prop}
            result = self.db.query("SELECT allowed_values FROM config WHERE property = :prop", values).fetchone()
            if result[0] is not None:
                print(result)
                allowed = ''.join(result).lower()
                return allowed.split(',')
            else:
                return []

        def set_property(prop, val, autosave=True, silent=False):
            values = {'prop': prop, 'val': val}
            if not prop_exists(prop):
                logger.error(f"Property '{prop}' does not exist")
            else:
                allowed_values = get_allowed_values(prop)
                if val in allowed_values or not allowed_values:
                    self.db.query("UPDATE config SET value = :val WHERE property = :prop", values)
                    if autosave:
                        self.db.commit()
                    sql = "SELECT * FROM config WHERE property = :prop AND value = :val"
                    result = self.db.query(sql, values).fetchone()
                    if result:
                        if not silent:
                            logger.info("Configuration updated successfully!")
                            view(prop=values['prop'])
                    else:
                        logger.error(f"An unknown error occurred while updating the database")
                else:
                    logger.error(f"\nInvalid option '{val}'. Allowed values are: {' '.join(allowed_values)}")

        def reset():
            confirm_reset = input("Resetting configuration to defaults... are you sure? (y|N) ")
            if confirm_reset.lower() == "y":
                result = self.db.query("SELECT * FROM config").fetchall()
                for row in result:
                    values = {'prop': row[0], 'default': row[3]}
                    self.db.query("UPDATE config SET value = :default WHERE property = :prop", values)
                    self.db.commit()
                view()
            else:
                logger.info("Configuration reset aborted")

        def edit():
            result = self.db.query("SELECT * FROM config").fetchall()
            logger.info("deemon Configuration Editor")
            counter = 0

            for row in result:
                prop = row[0]
                current_value = row[1]
                allowed_values = row[2]
                default_value = row[3]
                answer = None

                if not allowed_values:
                    allowed_values = []
                else:
                    allowed_values = ''.join(row[2]).lower().split(',')

                while (answer not in allowed_values) or (allowed_values is None):
                    if not allowed_values:
                        output = f"\nProperty: {prop}"
                    else:
                        output = f"\nProperty: {prop} || Options: {', '.join(allowed_values)}"

                    print(output)
                    answer = input(f"Set '{prop}' to [{current_value}]: ").lower()
                    if answer == "" or not default_value:
                        break

                if answer and (answer != current_value):
                    counter += 1
                    set_property(prop, answer, autosave=False, silent=True)

            if counter > 0:
                confirm = input("\nSave changes? (y|N): ").lower()
                if confirm != "y":
                    logger.warning("Changes have been discarded")
                else:
                    self.db.commit_and_close()
                    logger.info("Changes have been saved.")

        if self.args.view:
            view()
        elif self.args.edit:
            edit()
        elif self.args.set:
            update_prop = self.args.set[0].lower()
            update_value = self.args.set[1].lower()
            set_property(update_prop, update_value)
        elif self.args.reset:
            reset()

    def export_artists(self):
        export_path = Path(self.args.path)
        export_file = Path(export_path / "deemon-artists.csv")
        with open(export_file, "w+") as f:
            artist_dump = self.db.get_all_artists()
            for line in artist_dump:
                line = ','.join(map(str, line))
                f.write(line + "\n")
        sys.exit(0)

    def import_artists(self):
        import_artists = self.args.path
        bitrate = self.settings.config["bitrate"]
        record_type = self.settings.config["record_type"]
        alerts = self.settings.config["alerts"]
        # TODO check db for existing artist
        if import_artists:
            if Path(import_artists).is_file():
                with open(import_artists) as f:
                    #TODO check for CSV!
                    import_list = f.read().splitlines()
            elif Path(import_artists).is_dir():
                import_list = os.listdir(import_artists)
                num_to_import = len(import_list)
                logger.info(f"Importing {num_to_import} artist(s)...")
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
                        "y": "enable",
                        "n": "disable"
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

                    dl = Download()
                    for artist in import_list:
                        ma = MonitorArtist()
                        ma.artist_name = artist
                        ma.bitrate = bitrate
                        ma.record_type = record_type
                        ma.alerts = alerts
                        ma.start_monitoring()

                    dl.refresh()
            else:
                for artist in import_list:
                    dl = Download()
                    for artist in import_list:
                        ma = MonitorArtist()
                        ma.artist_name = artist
                        ma.bitrate = bitrate
                        ma.record_type = record_type
                        ma.alerts = alerts
                        ma.start_monitoring()

                    dl.refresh()

        sys.exit(0)

    def help(self):
        if self.args.name:
            try:
                self.subparser.choices[self.args.name].print_help()
            except KeyError as e:
                self.parser.print_help()
                logger.warning(f"\nInvalid command: {e}")
        else:
            self.parser.print_help()
        sys.exit(0)

    def main(self):
        if self.args.command == "refresh":
            self.refresh(skip_download=self.args.no_download)
        elif self.args.command == "download":
            self.download()
        elif self.args.command == "show":
            self.show()
        elif self.args.command == "alerts":
            print(self.args)
        elif self.args.command == "import":
            self.import_artists()
        elif self.args.command == "export":
            self.export_artists(self.args.path)
        elif self.args.command == "backup":
            self.backup()

class QueueItem:

    def __init__(self, artist: dict, album: dict):
        self.artist_name = artist["name"]
        self.bitrate = artist["bitrate"]
        self.album_id = album["id"]
        self.album_title = album["title"]
        self.url = album["link"]


if __name__ == "__main__":
    Deemon().main()
