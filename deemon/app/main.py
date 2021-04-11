from deezer import Deezer
from pathlib import Path
from argparse import ArgumentParser
from logging import getLogger, WARN
from deemon.app.db import DB
from deemon.app.dmi import DeemixInterface
from deemon import __version__
import os

BITRATE = {1: 'MP3 128', 3: 'MP3 320', 9: 'FLAC'}
HOME = str(Path.home())
DEFAULT_DB_PATH = HOME + "/.config/deemon"
DB_FILE = "releases.db"

parser = ArgumentParser(description="Monitor artists for new releases and download via deemix")
parser.add_argument('-a', dest='file', type=str, metavar='artists_file',
                    help='file or directory containing artists', required=True)
parser.add_argument('-m', dest='download_path', type=str, metavar='music_path',
                    help='path to music directory')
parser.add_argument('-c', dest='config_path', type=str, metavar='config_path',
                    help='path to deemix config directory')
parser.add_argument('-b', dest='bitrate', type=int, choices=[1, 3, 9], metavar='bitrate',
                    help='available options: 1=MP3 128k, 3=MP3 320k, 9=FLAC', default=3)
parser.add_argument('-d', dest='db_path', type=str, metavar='database_path',
                    help='custom path to store deemon database', default=DEFAULT_DB_PATH)
parser.add_argument('--version', action='version', version=f'%(prog)s-{__version__}',
                    help='show version information')
parser.print_usage = parser.print_help


def import_artists(file):
    if os.path.isfile(file):
        with open(file) as text_file:
            list_of_artists = text_file.read().splitlines()
            return list_of_artists
    elif os.path.isdir(file):
        list_of_artists = os.listdir(file)
        return list_of_artists
    else:
        print(f"{file}: not found")


def custom_db_path(p):
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        print(f"Error: Insufficient permissions to write to {p.parent}")
        exit(1)
    except FileExistsError as e:
        pass


def main():
    dm_logger = getLogger('deemix')
    dm_logger.setLevel(WARN)

    args = parser.parse_args()

    artists = args.file
    deemix_download_path = args.download_path
    deemix_config_path = args.config_path
    deemix_bitrate = args.bitrate
    db_path = Path(args.db_path + "/" + DB_FILE)

    di = DeemixInterface(deemix_download_path, deemix_config_path)

    # TODO: MOVE THIS TO FUNCTION AND CLEAN IT UP
    print("Starting deemon " + __version__ + "...")
    print("Verifying ARL, please wait... ", end="", flush=True)
    if not di.login():
        print("FAILED\n")
        exit(1)
    else:
        print("OK!\n")

    custom_db_path(db_path)

    db = DB(db_path)
    database_artists = db.get_all_artists()

    dz = Deezer()

    active_artists = []
    queue_list = []
    new_artist = False

    for line in import_artists(artists):
        # Skip blank lines
        if line == '':
            continue

        try:
            print(f"Searching for new releases by '{line}'...", end='')
            artist = dz.api.search_artist(line, limit=1)['data'][0]
        except IndexError:
            print(f" not found")
            continue

        # Check if monitoring new artist and disable auto download
        active_artists.append(artist['id'])
        artist_exists = db.check_exists(artist_id=artist['id'])
        if not artist_exists:
            new_artist = True
            print(f" new artist detected...", end='')

        # Check for new release; add to queue if not available
        artist_new_releases = 0
        all_albums = dz.api.get_artist_albums(artist['id'])
        for album in all_albums['data']:
            album_exists = db.check_exists(album_id=album["id"])
            if not album_exists:
                if not new_artist:
                    queue_list.append(Queue(artist, album))
                artist_new_releases += 1
                db.add_new_release(artist['id'], album['id'])
        print(f" {artist_new_releases} releases")

    # Purge artists that are no longer being monitored
    purge_list = [x for x in database_artists if x not in active_artists]
    nb_purged = db.purge_unmonitored_artists(purge_list)
    if nb_purged:
        print(f"\nPurged {nb_purged} artist(s) from database")

    # Send queue to deemix
    if queue_list:
        print(f"\nHere we go! Starting download of {len(queue_list)} release(s):")
        print(f"Bitrate: {BITRATE[deemix_bitrate]}\n")
        for q in queue_list:
            print(f"Downloading {q.artist_name} - {q.album_title}... ", end='', flush=True)
            di.download_url([q.url], deemix_bitrate)
            print("done!")

    # Save changes only after download is attempted
    db.commit_and_close()


class Queue:

    def __init__(self, artist: dict, album: dict):
        self.artist_name = artist["name"]
        self.album_id = album["id"]
        self.album_title = album["title"]
        self.url = album["link"]


if __name__ == "__main__":
    main()
