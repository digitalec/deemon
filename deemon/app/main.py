from deezer import Deezer
from argparse import ArgumentParser, HelpFormatter
from deemon.app.db import DB
from deemon.app.notify import EmailNotification
from deemon.app.dmi import DeemixInterface
from deemon.app import settings
from deemon import __version__
from packaging.version import parse as parse_version
import requests
import logging
import os

logger = logging.getLogger("deemon")


def parse_args():

    formatter = lambda prog: HelpFormatter(prog, max_help_position=35)
    parser = ArgumentParser(formatter_class=formatter)
    mutex_commands = parser.add_mutually_exclusive_group(required=True)
    mutex_commands.add_argument('-a', '--artists', dest='file', type=str, metavar='<file>',
                        help='file or directory containing artists')
    mutex_commands.add_argument('--test-email', dest="smtp_test", action="store_true",
                        help='test smtp settings')
    parser.add_argument('-m', '--music', dest='download_path', type=str, metavar='<path>',
                        help='path to music directory')
    parser.add_argument('-c', '--config', dest='config_path', type=str, metavar='<path>',
                        help='path to deemix config directory')
    parser.add_argument('-b', '--bitrate', dest='bitrate', type=int, choices=[1, 3, 9], metavar='N',
                        help='options: 1 (MP3 128k), 3 (MP3 320k), 9 (FLAC)', default=3)
    parser.add_argument('-d', '--db', dest='db_path', type=str, metavar='<path>',
                        help='custom path to store deemon database')
    parser.add_argument('-r', '--record-type', dest="record_type", type=str, metavar="type",
                        choices=['album', 'single'], help='choose record type: %(choices)s')
    parser.add_argument('-D', '--download-all', dest="download_all", action="store_true",
                        help='download all tracks by newly added artists')
    parser.add_argument('-V', '--version', action='version', version=f'%(prog)s-{__version__}',
                        help='show version information')
    parser.print_usage = parser.print_help

    return parser.parse_args()


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
                logger.info(f"Downloading {q.artist_name} - {q.album_title}... ")
                try:
                    self.di.download_url([q.url], self.bitrate)
                    notify_releases.append(q.artist_name + " - " + q.album_title)
                except IndexError:
                    logger.info(f"Error downloading {q.album_title} (no tracks available?), skipping... ")

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


if __name__ == "__main__":
    Deemon().main()
