import sys
import time
import logging
from datetime import timedelta
from pathlib import Path
from mutagen.easyid3 import EasyID3
from itertools import groupby
from operator import itemgetter
from deezer import Deezer
from concurrent.futures import ThreadPoolExecutor
from unidecode import unidecode
from tqdm import tqdm
from deemon.core.common import exclude_filtered_versions
from deemon.core.config import Config as config

logger = logging.getLogger(__name__)

dz = Deezer()

LIBRARY_ROOT = None
ALBUM_ONLY = None
ALLOW_EXCLUSIONS = None

# TODO - Add an 'exclusions' key to albums/tracks for count
# TODO - to improve album title matching, extract all a-zA-Z0-9 and compare (remove special chars)

library_metadata = []
performance = {
    'startID3': 0,
    'endID3': 0,
    'completeID3': 0,
    'startAPI': 0,
    'endAPI': 0,
    'completeAPI': 0
}


class Performance:
    def __init__(self):
        self.startID3 = 0
        self.endID3 = 0
        self.completeID3 = 0
        self.startAPI = 0
        self.endAPI = 0
        self.completeAPI = 0

    def start(self, module: str):
        if module == 'ID3':
            self.startID3 = time.time()
        elif module == 'API':
            self.startAPI = time.time()

    def end(self, module: str):
        if module == 'ID3':
            self.endID3 = time.time()
            self.completeID3 = self.endID3 - self.startID3
        elif module == 'API':
            self.endAPI = time.time()
            self.completeAPI = self.endAPI - self.startAPI


def read_metadata(file):
    metadata = {
        'abs_path': file,
        'rel_path': str(file).replace(LIBRARY_ROOT, ".."),
        'error': None
    }

    try:
        _audio = EasyID3(file)

        # Remove featured artists from artist tag
        metadata['artist'] = _audio['artist'][0].split("/")[0].strip()

        # Remove special character replacement for search query
        metadata['album'] = _audio['album'][0].replace("_", " ").strip()
        metadata['title'] = _audio['title'][0].strip()
    except Exception as e:
        metadata['error'] = e

    return metadata


def get_time_from_secs(secs):
    td_str = str(timedelta(seconds=secs))
    x = td_str.split(":")
    x[2] = x[2].split(".")[0]

    if x[0] != "0":
        friendly_time = f"{x[0]} Hours {x[1]} Minutes {x[2]} Seconds"
    elif x[1] != "00":
        friendly_time = f"{x[1]} Minutes {x[2]} Seconds"
    elif x[2] == "00":
        friendly_time = f"Less than 1 second"
    else:
        friendly_time = f"{x[2]} Seconds"

    return friendly_time


def invalid_metadata(track: dict) -> bool:
    if not all([track['artist'], track['album'], track['title']]):
        return True
    else:
        return False


def get_artist_api(name: str) -> list:
    """ Get list of artists with exact name matches from API """
    artist_api = dz.gw.search(name)['ARTIST']['data']
    artist_matches = []

    for artist in artist_api:
        if artist['ART_NAME'].lower() == name.lower():
            artist_matches.append(artist)

    return artist_matches


def get_artist_discography_api(artist_name, artist_id) -> list:
    """ Get list of albums with exact name matches from API """
    album_search = dz.gw.search(artist_name)['ALBUM']['data']
    album_gw = dz.gw.get_artist_discography(artist_id)['data']
    album_api = dz.api.get_artist_albums(artist_id)['data']

    albums = []

    for album in album_api:
        if album['record_type'] == 'single':
            album['record_type'] = '0'
        elif album['record_type'] == 'album':
            album['record_type'] = '1'
        elif album['record_type'] == 'compilation':
            album['record_type'] = '2'
        elif album['record_type'] == 'ep':
            album['record_type'] = '3'

        if album['explicit_lyrics']:
            album['explicit_lyrics'] = '1'
        else:
            album['explicit_lyrics'] = '0'

        alb = {
            'ALB_ID': str(album['id']),
            'ALB_TITLE': album['title'],
            'EXPLICIT_LYRICS': album['explicit_lyrics'],
            'TYPE': album['record_type']
        }
        albums.append(alb)

    for album in album_gw:
        if album['ALB_ID'] not in [x['ALB_ID'] for x in albums]:
            albums.append(album)

    for album in album_search:
        if album['ART_ID'] == artist_id:
            if album['ALB_ID'] not in [x['ALB_ID'] for x in albums]:
                # Album returned via Search is missing EXPLICIT_LYRICS key
                if not album.get('EXPLICIT_LYRICS'):
                    album['EXPLICIT_LYRICS'] = '0'
                albums.append(album)

    return albums


def get_album_tracklist_api(album_id: str) -> list:
    """ Get tracklist for album based on album_id """
    tracklist_api = dz.gw.get_album_tracks(album_id)
    return tracklist_api


def retrieve_track_ids_per_artist(discography: tuple):
    artist = discography[0]
    albums = discography[1]

    # TODO - Need to implement this
    duplicate_artists = False
    found_artist = False

    track_ids = []
    album_ids = []

    api_artists = get_artist_api(artist)

    tqdm.write(f"Getting track IDs for tracks by \"{artist}\"")

    if len(api_artists):
        if len(api_artists) > 1:
            tqdm.write(f"Duplicate artists detected for \"{artist}\"")
            duplicate_artists = True

        for api_artist in api_artists:

            if found_artist:
                tqdm.write("Found correct artist, skipping duplicates")
                break

            if duplicate_artists:
                tqdm.write(f"Searching with: {api_artist['ART_NAME']} ({api_artist['ART_ID']})")

            discog = get_artist_discography_api(api_artist['ART_NAME'], api_artist['ART_ID'])

            for album, tracks in groupby(albums, key=itemgetter('album')):

                # Convert itertools.groupby to list so we can use it more than once
                tracks = [track for track in tracks]

                api_album_matches = [alb for alb in discog if alb['ALB_TITLE'].lower() == album.lower()]

                if ALLOW_EXCLUSIONS:
                    filtered_album_matches = exclude_filtered_versions(api_album_matches)
                    api_album = get_preferred_album(filtered_album_matches, len(tracks))
                else:
                    api_album = get_preferred_album(api_album_matches, len(tracks))

                if ALBUM_ONLY:
                    if api_album:
                        album_ids.append(api_album)
                        continue
                    else:
                        album_ids.append(
                            {
                                'artist': artist,
                                'title': album,
                                'info': "Album not found"
                            }
                        )
                        continue

                if api_album:
                    tracklist = get_album_tracklist_api(api_album['ALB_ID'])
                    for track in tracks:
                        track_variations = [track['title'].lower(), unidecode(track['title']).lower()]

                        for i, track_api in enumerate(tracklist, start=1):
                            if track_api['SNG_TITLE'].lower() in track_variations:
                                found_artist = True
                                track['id'] = track_api['SNG_ID']
                                track_ids.append(track)
                                break

                            elif f"{track_api['SNG_TITLE']} {track_api.get('VERSION', '')}".lower() in track_variations:
                                found_artist = True
                                track['id'] = track_api['SNG_ID']
                                track_ids.append(track)
                                break

                            if i == len(tracklist):
                                track['info'] = "Track not found"
                                tqdm.write(f"{track['info']}: {track['title']}")
                                track_ids.append(track)
                                break
                else:
                    if duplicate_artists:
                        info = f"Album not found under artist ID {api_artist['ART_ID']}"
                    else:
                        info = f"Album not found"
                    tqdm.write(f"{info}: {album}")
                    for track in tracks:
                        track['info'] = info
                        track_ids.append(track)
    else:
        tqdm.write(f"Artist not found: {artist}")
        for album, tracks in groupby(albums, key=itemgetter('album')):
            for track in tracks:
                track['info'] = "Artist not found"
                track_ids.append(track)

    if ALBUM_ONLY:
        return album_ids
    else:
        return track_ids


def get_preferred_album(api_albums: list, num_tracks: int):
    """ Return preferred album order based on config.prefer_explicit() """
    preferred_album = None

    if num_tracks < 4:
        preferred_album = [album for album in api_albums if album['EXPLICIT_LYRICS'] == '1' and album['TYPE'] == '0']
        if not preferred_album:
            preferred_album = [album for album in api_albums if album['TYPE'] == '0']

    if num_tracks >= 4 or not preferred_album:
        preferred_album = [album for album in api_albums if album['EXPLICIT_LYRICS'] == '1' and album['TYPE'] in ['1', '2', '3']]
        if not preferred_album:
            preferred_album = [album for album in api_albums if album['TYPE'] in ['1', '2', '3']]

    if preferred_album:
        return preferred_album[0]


def get_preferred_track_id(title: str, tracklist: list):
    """ Return preferred track ID by comparing against title of local track """
    track_id = None
    for track in tracklist:
        if track.get('VERSION'):
            api_title = f"{track['SNG_TITLE']} {track['VERSION']}".lower()
            if title.lower() == api_title:
                return track['SNG_ID']
        else:
            if track['SNG_TITLE'].lower() == title.lower():
                track_id = track['SNG_ID']
    return track_id


def upgrade(library, output, albums=False, exclusions=False):

    global ALBUM_ONLY
    global ALLOW_EXCLUSIONS
    global LIBRARY_ROOT

    ALBUM_ONLY = albums
    ALLOW_EXCLUSIONS = exclusions
    LIBRARY_ROOT = library

    output_ids = Path(output) / "library_upgrade_ids.txt"
    output_log = Path(output) / "library_upgrade.log"

    perf = Performance()
    logger.info("Scanning library, standby...")
    logger.debug(f"Library path: {LIBRARY_ROOT}")
    library_files = Path(LIBRARY_ROOT).glob("**/*.mp3")
    files = [file for file in library_files if not file.name.startswith(".")]
    files.sort()

    if files:
        print(f"Found {len(files)} MP3 files")
    else:
        print("No MP3 files found")
        sys.exit()

    perf.start('ID3')
    with ThreadPoolExecutor(10) as executor:
        library_metadata = list(
            tqdm(
                executor.map(read_metadata, files),
                total=(len(files)),
                desc="Reading metadata",
            )
        )
    perf.end('ID3')

    library_metadata_errors = [file for file in library_metadata if file.get('error')]
    library_metadata = [file for file in library_metadata if not file.get('error')]

    artists = sorted(library_metadata, key=itemgetter('artist'))
    artist_list = [(artist, list(albums)) for artist, albums in groupby(artists, key=itemgetter('artist'))]

    perf.start('API')
    with ThreadPoolExecutor(20) as executor:
        result = list(
            tqdm(
                executor.map(retrieve_track_ids_per_artist, artist_list),
                total=len(artist_list),
                desc="Processing tracks by artist"
            )
        )
        if ALBUM_ONLY:
            album_result = result
            track_result = []
        else:
            track_result = result
            album_result = []
    perf.end('API')

    albums = [album for artist in album_result for album in artist]
    album_ids = [album['ALB_ID'] for album in albums if album.get('ALB_ID')]
    album_not_found = [album for album in albums if not album.get('ALB_ID')]

    tracks = [track for artist in track_result for track in artist]
    track_ids = [track['id'] for track in tracks if track.get('id') and not track.get('error')]
    track_not_found = [track for track in tracks if not track.get('id') and not track.get('error')]

    # TODO move this to function for reuse in f.write() below
    print(f"Found: {len(track_ids)} | Not Found: {len(track_not_found)} | "
          f"Errors: {len(library_metadata_errors)} | Total: {len(files)}\n\n")
    print(f"Time to read metadata: {get_time_from_secs(perf.completeID3)}")
    print(f"Time to retrieve API data: {get_time_from_secs(perf.completeAPI)}\n\n")

    if (ALBUM_ONLY and album_ids) or track_ids:
        with open(output_ids, "w") as f:
            if ALBUM_ONLY and album_ids:
                f.write(', '.join(album_ids))
            elif track_ids:
                f.write(', '.join(track_ids))

    with open(output_log, "w") as f:
        if ALBUM_ONLY:
            f.write(f"Albums Found: {len(album_ids)} | Albums Not Found: {len(album_not_found)} | "
                    f"ID3 Errors: {len(library_metadata_errors)} | Total Files: {len(files)}\n\n")
            f.write(f"Time to read metadata: {get_time_from_secs(perf.completeID3)}\n")
            f.write(f"Time to retrieve API data: {get_time_from_secs(perf.completeAPI)}\n\n")

            if library_metadata_errors:
                f.write("The following files had missing/invalid ID3 tag data:\n\n")
                for track in library_metadata_errors:
                    if track.get('error'):
                        f.write(f"\tFile: {track['rel_path']}\n")
                        f.write(f"\t\tError: {track['error']}\n\n")
                f.write("\n")

            if album_not_found:

                artists_not_found = [track['artist'] for track in tracks if track['info'] == 'Artist not found']
                if artists_not_found:
                    f.write("The following artists were not found:\n")
                    for artist in artists_not_found:
                        f.write("\n\t{track['artist']\n")

                f.write("The following albums were not found:\n")
                for album in album_not_found:
                    f.write(f"\n\tArtist: {album['artist']}\n")
                    f.write(f"\tAlbum: {album['title']}\n")
                    if album.get('info'):
                        f.write(f"\tInfo: {album['info']}\n")
        else:
            f.write(f"Tracks Found: {len(track_ids)} | Tracks Not Found: {len(track_not_found)} | "
                    f"ID3 Errors: {len(library_metadata_errors)} | Total Files: {len(files)}\n\n")
            f.write(f"Time to read metadata: {get_time_from_secs(perf.completeID3)}\n")
            f.write(f"Time to retrieve API data: {get_time_from_secs(perf.completeAPI)}\n\n")

            if library_metadata_errors:
                f.write("The following files had missing/invalid ID3 tag data:\n\n")
                for track in library_metadata_errors:
                    if track.get('error'):
                        f.write(f"\tFile: {track['rel_path']}\n")
                        f.write(f"\t\tError: {track['error']}\n\n")
                f.write("\n")

            if track_not_found:

                artists_not_found = [track['artist'] for track in tracks if track.get('info', '') == 'Artist not found']
                if artists_not_found:
                    f.write("The following artists were not found:\n")
                    for artist in artists_not_found:
                        f.write("\n\t{track['artist']\n")

                f.write("The following tracks were not found:\n")
                for track in track_not_found:
                    f.write(f"\n\tArtist: {track['artist']}\n")
                    f.write(f"\tAlbum: {track['album']}\n")
                    f.write(f"\tTrack: {track['title']}\n")
                    f.write(f"\tFile: {track['rel_path']}\n")
                    if track.get('info'):
                        f.write(f"\tInfo: {track['info']}\n")