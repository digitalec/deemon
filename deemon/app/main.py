from deezer import Deezer
from pathlib import Path
from argparse import ArgumentParser, HelpFormatter
from deemon.app.db import DB
from deemon.app.dmi import DeemixInterface
from deemon import __version__
from packaging.version import parse as parse_version
import requests
import os


def parse_args():

    formatter = lambda prog: HelpFormatter(prog, max_help_position=35)
    parser = ArgumentParser(formatter_class=formatter)
    parser.add_argument('-a', '--artists', dest='file', type=str, metavar='<file>',
                        help='file or directory containing artists', required=True)
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
        self.artists = args.file
        self.download_path = args.download_path
        self.config_path = args.config_path
        self.bitrate = args.bitrate
        self.download_all = args.download_all
        self.record_type = args.record_type
        self.active_artists = []
        self.queue_list = []
        self.dz = Deezer()
        self.di = DeemixInterface(self.download_path, self.config_path)

        if args.db_path:
            self.db_path = Path(args.db_path + "/releases.db")
        else:
            # TODO: os.getenv()
            # TODO: check this path *first* before using env for backwards compatibility
            self.db_path = Path(Path.home() / ".config/deemon/releases.db")

        self.db = DB(self.db_path)

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

        print(f"- Bitrate: {quality[self.bitrate]}\n- Download: {download}\n- Record Type: {rtype}\n")

    def download_queue(self, queue):
        if queue:
            num_queued = len(queue)
            print("\n** Here we go! Starting download of " + str(num_queued) + " release(s):")
            for q in queue:
                print(f"Downloading {q.artist_name} - {q.album_title}... ", end='', flush=True)
                self.di.download_url([q.url], self.bitrate)
                print("done!")

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

        print("Starting deemon " + __version__ + "...")
        self.check_for_updates()
        self.print_settings()
        print("Verifying ARL, please wait... ", end="", flush=True)
        if not self.di.login():
            print("FAILED")
            exit(1)
        else:
            print("OK")

        print("Checking for new releases...\n")
        for line in self.import_artists(self.artists):
            print(f"Searching for releases by {line}... ", end="", flush=True)
            try:
                artist = self.dz.api.search_artist(line, limit=1)['data'][0]
            except IndexError:
                print("not found")
                continue

            new_releases = self.get_new_releases(artist)
            print(f"{new_releases} found")

        num_purged = self.db.purge_unmonitored_artists(self.active_artists)
        if num_purged:
            print(f"\nPurged {num_purged} artist(s) from database")

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
