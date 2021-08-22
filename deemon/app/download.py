from pathlib import Path

import plexapi.exceptions
from plexapi.server import PlexServer
from deemon.app import dmi, Deemon, utils
import logging
import deezer
import sys
import os

logger = logging.getLogger(__name__)


class QueueItem:

    def __init__(self, bitrate, artist=None, album=None, playlist=None):  # TODO - Accept new playlist tracks for output/alerts
        self.artist_name = None
        self.bitrate = bitrate
        self.album_id = None
        self.album_title = None
        self.url = None
        self.playlist_title = None
        self.verbose = os.environ.get('VERBOSE')

        if artist:
            self.artist_name = artist["name"]
            if not album:
                self.url = artist["link"]

        if album:
            if not artist:
                self.artist_name = album["artist"]["name"]
            self.album_id = album["id"]
            self.album_title = album["title"]
            self.url = album["link"]

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
        self.config = Deemon().config
        self.queue_list = []
        self.bitrate = None
        self.verbose = os.environ.get("VERBOSE")
        self.duplicate_id_count = 0

        if not self.di.login():
            sys.exit(1)

    def get_plex_server(self):
        baseurl = self.config["plex_baseurl"]
        token = self.config["plex_token"]
        if (baseurl != "") and (token != ""):
            try:
                print("Plex settings found, trying to connect (10s)... ", end="")
                plex_server = PlexServer(baseurl, token, timeout=10)
                print(" OK")
                return plex_server
            except Exception:
                print(" FAILED")
                logger.error("Error: Unable to reach Plex server, please refresh manually.")
                return False

    def refresh_plex(self, plexobj):
        try:
            plexobj.library.section(self.config["plex_library"]).update()
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

            for q in self.queue_list:
                if self.verbose == "true":
                    logger.debug(f"Processing queue item {vars(q)}")
                if q.artist_name:
                    logger.info(f"+ {q.artist_name} - {q.album_title}... ")
                    self.di.download_url([q.url], q.bitrate)
                else:
                    logger.info(f"+ {q.playlist_title} (playlist)...")
                    self.di.download_url([q.url], q.bitrate, override_deemix=False)

            print("")
            logger.info("Downloads complete!")
            if plex and (self.config["plex_library"] != ""):  # TODO - config validation should be done elsewhere
                self.refresh_plex(plex)

    def download(self, artist, artist_id, album_id, url, bitrate, record_type, input_file, auto=True):

        def filter_artist_by_record_type(artist, record_type):
            album_api = self.dz.api.get_artist_albums(artist['id'])['data']
            filtered_albums = []
            for album in album_api:
                if (album['record_type'] == record_type) or record_type == "all":
                    filtered_albums.append(album)
                else:
                    logger.debug(f"Filtered release '{album['title']} ({album['id']})' as it "
                                 f"does not match record type '{record_type}'")
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
            filtered = filter_artist_by_record_type(api_object, record_type)
            for album in filtered:
                if not queue_item_exists(album['id']):
                    self.queue_list.append(QueueItem(bitrate, api_object, album))

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

        def process_artist_by_id(id):
            logger.debug("Processing artists by ID")
            artist_id_result = get_api_result(artist_id=id)
            logger.debug(f"Requested Artist ID: {id}, Found: {artist_id_result['name']}")
            if artist_id_result:
                queue_filtered_releases(artist_id_result)

        def process_album_by_id(id):
            logger.debug("Processing album by name")
            album_id_result = get_api_result(album_id=id)
            logger.debug(f"Requested Album: {id}, "
                         f"Found: {album_id_result['artist']['name']} - {album_id_result['title']}")
            if album_id_result and not queue_item_exists(album_id_result['id']):
                self.queue_list.append(QueueItem(bitrate, album=album_id_result))

        def process_playlist_by_id(id):
            playlist_api = self.dz.api.get_playlist(id)
            self.queue_list.append(QueueItem(bitrate, playlist=playlist_api))

        def extract_id_from_url(url):
            id_group = ['artist', 'album', 'playlist']
            for group in id_group:
                id_type = group
                try:
                    id = int(url.split(f'/{group}/')[1])
                    logger.debug(f"Extracted group={id_type}, id={id}")
                    return id_type, id
                except (IndexError, ValueError) as e:
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
                artist_list = utils.read_file_as_csv(input_file)
                artist_int_list, artist_str_list = utils.process_input_file(artist_list)
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
