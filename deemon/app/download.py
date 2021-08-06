from pathlib import Path

import plexapi.exceptions
from plexapi.server import PlexServer
from deemon.app import dmi
from deemon.app import Deemon
import logging
import deezer
import sys
import os

logger = logging.getLogger(__name__)


class QueueItem:

    def __init__(self, artist=None, album=None, playlist=None):  # TODO - Accept new playlist tracks for output/alerts
        self.artist_name = None
        self.bitrate = None
        self.album_id = None
        self.album_title = None
        self.url = None
        self.playlist_title = None
        self.verbose = os.environ.get('VERBOSE')

        if artist:
            self.artist_name = artist["name"]
            self.bitrate = artist["bitrate"]
            self.url = artist["link"]

        if album:
            if not artist:
                self.artist_name = album["artist"]["name"]
                self.bitrate = album["bitrate"]
            self.album_id = album["id"]
            self.album_title = album["title"]
            self.url = album["link"]

        if playlist:
            self.bitrate = artist["bitrate"]
            self.url = playlist["url"]
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

    def download_queue(self, queue):  # TODO - Add support for downloading just Artist
        if queue:
            plex = self.get_plex_server()
            print("----------------------------")
            logger.info("Sending " + str(len(queue)) + " release(s) to deemix for download:")

            for q in queue:
                if self.verbose == "true":
                    logger.debug(f"Processing queue item {vars(q)}")
                if q.artist_name:
                    logger.info(f"+ {q.artist_name} - {q.album_title}... ")
                else:
                    logger.info(f"+ Updating playlist: {q.playlist_title}...")
                self.di.download_url([q.url], q.bitrate)

            print("")
            logger.info("Downloads complete!")
            if plex and (self.config["plex_library"] != ""):  # TODO - config validation should be done elsewhere
                self.refresh_plex(plex)

    # TODO Re-write manual download option - add_to_queue only used by download()
    def add_to_queue(self, artist, album):
        for _album in album['data']:
            if (self.record_type == _album["record_type"]) or (self.record_type == "all"):
                logger.debug(f"QUEUE: Adding '{_album['title']}' to queue...")
                artist["bitrate"] = self.bitrate
                self.queue_list.append(QueueItem(artist, _album))

    # TODO Re-write manual download option
    def download(self, artist, artist_id, album_id, url, bitrate, record_type, input_file):

        # TODO Download via URL needs to be reworked / self.di.download_url()

        def filter_artist_by_record_type(artist, record_type):
            album_api = self.dz.api.get_artist_albums(artist['id'])['data']
            filtered_albums = []
            for album in album_api:
                if (album['record_type'] == record_type) or record_type == "all":
                    filtered_albums.append(album)
            return filtered_albums

        def get_api_result(artist=None, artist_id=None, album_id=None):  # TODO Multiple try for detailed logging
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
            api_object['bitrate'] = bitrate
            filtered = filter_artist_by_record_type(api_object, record_type)
            for album in filtered:
                if check_queue_item_exists(album['id']):
                    self.queue_list.append(QueueItem(api_object, album))

        def check_queue_item_exists(i):
            for q in self.queue_list:
                if q.album_id == i:
                    logger.debug(f"Album ID {i} is already in queue")
                    return False
            return True

        def read_file_as_csv(file):
            with open(file, 'r', encoding="utf8", errors="replace") as f:
                make_csv = f.read().replace('\n', ',')
                csv_to_list = make_csv.split(',')
                sorted_list = sorted(list(filter(None, csv_to_list)))
                return sorted_list

        def check_for_artist_ids(artist_list):
            logger.debug("Processing file contents")
            int_artists = []
            str_artists = []
            for i in range(len(artist_list)):
                try:
                    int_artists.append(int(artist_list[i]))
                except ValueError:
                    str_artists.append(artist_list[i])
            logger.debug(f"Detected {len(int_artists)} artist ID(s) and {len(str_artists)} artist name(s)")
            return int_artists, str_artists

        def download_by_name(artist):
            for a in artist:
                artist_result = get_api_result(artist=a)
                if artist_result:
                    queue_filtered_releases(artist_result)

        def download_by_id(artist_id):
            for i in artist_id:
                artist_id_result = get_api_result(artist_id=i)
                if artist_id_result:
                    queue_filtered_releases(artist_id_result)

        if artist:
            logger.debug("Downloading by Artist")
            download_by_name(artist)

        if artist_id:
            logger.debug("Downloading by Artist ID")
            download_by_id(artist_id)

        if album_id:
            logger.debug("Downloading by Album ID")
            for i in album_id:
                record_type = "all"
                album_id_result = get_api_result(album_id=i)
                if album_id_result:
                    album_id_result['bitrate'] = bitrate
                    self.queue_list.append(QueueItem(album=album_id_result))

        if input_file:
            logger.info(f"Reading from file {input_file}")
            if Path(input_file).exists():
                artist_list = read_file_as_csv(input_file)
                artist_int_list, artist_str_list = check_for_artist_ids(artist_list)
                if artist_str_list:
                    download_by_name(artist_str_list)
                if artist_int_list:
                    download_by_id(artist_int_list)

        self.download_queue(self.queue_list)