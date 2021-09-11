from pathlib import Path
import plexapi.exceptions
from plexapi.server import PlexServer
from deemon.core import dmi
from deemon.utils import dataprocessor
from deemon.core.config import Config as config
from deemon import utils
import logging
import deezer
import sys
import os

logger = logging.getLogger(__name__)


class QueueItem:
    # TODO - Accept new playlist tracks for output/alerts
    def __init__(self, artist=None, album=None, track=None, playlist=None):
        self.artist_name = None
        self.album_id = None
        self.album_title = None
        self.track_id = None
        self.track_title = None
        self.url = None
        self.playlist_title = None
        self.verbose = os.environ.get('VERBOSE')

        if artist:
            try:
                self.artist_name = artist["artist_name"]
            except KeyError:
                self.artist_name = artist["name"]
            if not album and not track:
                self.url = artist["link"]

        if album:
            if not artist:
                self.artist_name = album["artist"]["name"]
            self.album_id = album["id"]
            self.album_title = album["title"]
            self.url = album["link"]

        if track:
            self.artist_name = track["artist"]
            self.track_id = track["id"]
            self.track_title = track["title"]
            self.url = track["link"]

        if playlist:
            self.url = playlist["link"]
            self.playlist_title = playlist["title"]

        self.print_queue_to_log()

    def print_queue_to_log(self):
        if self.verbose == "true":
            logger.debug("Item created in queue: " + str(self.__dict__))


class Download:

    def __init__(self):
        super().__init__()
        self.dz = deezer.Deezer()
        self.di = dmi.DeemixInterface()
        self.queue_list = []
        self.bitrate = None
        self.verbose = os.environ.get("VERBOSE")
        self.duplicate_id_count = 0

        if not self.di.login():
            sys.exit(1)

    def get_plex_server(self):
        if (config.plex_baseurl() != "") and (config.plex_token() != ""):
            try:
                print("Plex settings found, trying to connect (10s)... ", end="")
                plex_server = PlexServer(config.plex_baseurl(), config.plex_token(), timeout=10)
                print(" OK")
                return plex_server
            except Exception:
                print(" FAILED")
                logger.error("Error: Unable to reach Plex server, please refresh manually.")
                return False

    def refresh_plex(self, plexobj):
        try:
            plexobj.library.section(config.plex_library()).update()
            logger.debug("Plex library refreshed successfully")
        except plexapi.exceptions.BadRequest as e:
            logger.error("Error occurred while refreshing your library. See logs for additional info.")
            logger.debug(f"Error during Plex refresh: {e}")
        except plexapi.exceptions.NotFound as e:
            logger.error("Error: Plex library not found. See logs for additional info.")
            logger.debug(f"Error during Plex refresh: {e}")

    def download_queue(self):
        if self.queue_list:
            plex = self.get_plex_server()
            print("----------------------------")
            logger.info("Sending " + str(len(self.queue_list)) + " release(s) to deemix for download:")

            current = 1
            total = len(self.queue_list)
            for q in self.queue_list:
                dx_bitrates = {"128": 1, "320": 3, "FLAC": 9}
                dx_bitrate = dx_bitrates[config.bitrate()]
                if self.verbose == "true":
                    logger.debug(f"Processing queue item {vars(q)}")
                if q.artist_name:
                    if q.album_title:
                        logger.info(f"[{current}/{total}] {q.artist_name} - {q.album_title}... ")
                    else:
                        logger.info(f"[{current}/{total}] {q.artist_name} - {q.track_title}... ")
                    self.di.download_url([q.url], dx_bitrate, config.download_path())
                else:
                    logger.info(f"+ {q.playlist_title} (playlist)...")
                    self.di.download_url([q.url], dx_bitrate, config.download_path(), override_deemix=False)
                current += 1
            print("")
            logger.info("Downloads complete!")
            if plex and (config.plex_library() != ""):
                self.refresh_plex(plex)

    def download(self, artist, artist_id, album_id, url, input_file, auto=True):

        def filter_artist_by_record_type(artist):
            album_api = self.dz.api.get_artist_albums(artist['id'])['data']
            filtered_albums = []
            for album in album_api:
                if (album['record_type'] == config.record_type()) or config.record_type() == "all":
                    filtered_albums.append(album)
                else:
                    logger.debug(f"Filtered release '{album['title']} ({album['id']})' as it "
                                 f"does not match record type '{config.record_type()}'")
            return filtered_albums

        def get_api_result(artist=None, artist_id=None, album_id=None):
            if artist:
                try:
                    return self.dz.api.search_artist(artist, limit=1)["data"][0]  # TODO handle incorrect artist
                except (deezer.api.DataException, IndexError):
                    logger.error(f"Artist {artist} not found.")
            if artist_id:
                try:
                    return self.dz.api.get_artist(artist_id)
                except (deezer.api.DataException, IndexError):
                    logger.error(f"Artist ID {artist_id} not found.")
            if album_id:
                try:
                    return self.dz.api.get_album(album_id)
                except (deezer.api.DataException, IndexError):
                    logger.error(f"Album ID {album_id} not found.")

        def queue_filtered_releases(api_object):
            filtered = filter_artist_by_record_type(api_object)
            for album in filtered:
                if not queue_item_exists(album['id']):
                    self.queue_list.append(QueueItem(artist=api_object, album=album))

        def queue_item_exists(i):
            for q in self.queue_list:
                if q.album_id == i:
                    logger.debug(f"Album ID {i} is already in queue")
                    self.duplicate_id_count += 1
                    return True
            return False

        def process_artist_by_name(name):
            logger.debug("Processing artists by name")
            artist_result = get_api_result(artist=name)
            logger.debug(f"Requested Artist: '{name}', Found: '{artist_result['name']}'")
            if artist_result:
                queue_filtered_releases(artist_result)

        def process_artist_by_id(i):
            logger.debug("Processing artists by ID")
            artist_id_result = get_api_result(artist_id=i)
            logger.debug(f"Requested Artist ID: {i}, Found: {artist_id_result['name']}")
            if artist_id_result:
                queue_filtered_releases(artist_id_result)

        def process_album_by_id(i):
            logger.debug("Processing album by name")
            # TODO handle album_id_result = None when not found
            album_id_result = get_api_result(album_id=i)
            logger.debug(f"Requested Album: {i}, "
                         f"Found: {album_id_result['artist']['name']} - {album_id_result['title']}")
            if album_id_result and not queue_item_exists(album_id_result['id']):
                self.queue_list.append(QueueItem(album=album_id_result))

        def process_playlist_by_id(id):
            playlist_api = self.dz.api.get_playlist(id)
            self.queue_list.append(QueueItem(playlist=playlist_api))

        def extract_id_from_url(url):
            id_group = ['artist', 'album', 'playlist']
            for group in id_group:
                id_type = group
                try:
                    id = int(url.split(f'/{group}/')[1])
                    logger.debug(f"Extracted group={id_type}, id={id}")
                    return id_type, id
                except (IndexError, ValueError):
                    continue
            return False, False

        if artist:
            [process_artist_by_name(a) for a in artist]

        if artist_id:
            [process_artist_by_id(i) for i in artist_id]

        if album_id:
            [process_album_by_id(i) for i in album_id]

        if input_file:
            logger.info(f"Reading from file {input_file}")
            if Path(input_file).exists():
                artist_list = utils.dataprocessor.read_file_as_csv(input_file)
                artist_int_list, artist_str_list = utils.dataprocessor.process_input_file(artist_list)
                if artist_str_list:
                    for artist in artist_str_list:
                        process_artist_by_name(artist)
                if artist_int_list:
                    for artist in artist_int_list:
                        process_artist_by_id(artist)

        if url:
            logger.debug("Processing URLs")
            for u in url:
                egroup, eid = extract_id_from_url(u)
                if not egroup or not eid:
                    logger.error(f"Invalid URL -- {u}")
                    continue

                if egroup == "artist":
                    process_artist_by_id(eid)
                elif egroup == "album":
                    process_album_by_id(eid)
                elif egroup == "playlist":
                    process_playlist_by_id(eid)

        if self.duplicate_id_count > 0:
            logger.info(f"Cleaned up {self.duplicate_id_count} duplicate release(s). See log for additional info.")

        if auto:
            self.download_queue()
