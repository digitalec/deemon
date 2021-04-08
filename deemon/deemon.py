from deezer import Deezer
from deemix.app.cli import cli
from pathlib import Path
from argparse import ArgumentParser
from logging import getLogger, WARN
from deemon.queuemanager import QueueManager
from deemon.db import DB

BITRATE = {1: 'MP3 128', 3: 'MP3 320', 9: 'FLAC'}
HOME = str(Path.home())
DB_FILE = Path(HOME + "/.config/deemon/releases.db")
DB_FILE.parent.mkdir(parents=True, exist_ok=True)
DEFAULT_DOWNLOAD_PATH = HOME + "/Music/deemix Music"
DEFAULT_CONFIG_PATH = HOME + "/.config/deemix"

dz = Deezer()
dz_logger = getLogger('deemix')
dz_logger.setLevel(WARN)

db = DB(DB_FILE)
database_artists = db.get_all_artists()

parser = ArgumentParser()
parser.add_argument('-f', '--file', dest='artist_file', help='list of artists in plain text', required=True)
parser.add_argument('-o', '--output', dest='download_path', help='path for downloads', default=DEFAULT_DOWNLOAD_PATH)
parser.add_argument('-c', '--config', dest='config_path', help='path to deemix config dir', default=DEFAULT_CONFIG_PATH)
parser.add_argument('-b', '--bitrate', dest='bitrate', type=int, help='1=MP3 128, 3=MP3 320, 9=FLAC', default=3)
args = parser.parse_args()

artist_file = args.artist_file
deemix_download_path = args.download_path
deemix_config_path = args.config_path
deemix_bitrate = args.bitrate


def open_artist_file(file: object):
    if Path(file).exists():
        with open(file) as a:
            list_of_artists = a.read().splitlines()
            return list_of_artists
    else:
        print(f"{artist_file}: file not found")
        exit(1)


def main():
    url = []
    new_releases = []
    active_artists = []
    queue_list = []
    new_artist = False
    total_new_releases = 0
    textfile_artists = open_artist_file(artist_file)

    for line in textfile_artists:
        # Skip blank lines
        if line == '':
            continue

        try:
            print(f"Searching for new releases by '{line}'...", end='')
            #TODO: create class to handle artist object?
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
                    queue_list.append(QueueManager(artist, album))
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
        app = cli(deemix_download_path, deemix_config_path)
        app.login()
        print(f"Bitrate: {BITRATE[deemix_bitrate]}\n")
        for q in queue_list:
            print(f"Downloading {q.artist_name} - {q.album_title}... ", end='')
            app.downloadLink([q.url], deemix_bitrate)
            print("done!")

    # Save changes only after download is attempted
    db.commit_and_close()


if __name__ == "__main__":
    main()
