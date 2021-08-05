from pathlib import Path

import plexapi.exceptions
from plexapi.server import PlexServer
from deemon.app import dmi
from deemon.app import Deemon
import logging
import deezer
import sys

logger = logging.getLogger(__name__)


class QueueItem:

    def __init__(self, artist=None, album=None, playlist=None):  # TODO - Accept new playlist tracks for output/alerts
        self.artist_name = None
        self.bitrate = None
        self.album_id = None
        self.album_title = None
        self.url = None
        self.playlist_title = None

        if artist:
            self.artist_name = artist["name"]
            self.bitrate = artist["bitrate"]

        if album:
            self.album_id = album["id"]
            self.album_title = album["title"]
            self.url = album["link"]

        if playlist:
            self.bitrate = artist["bitrate"]
            self.url = playlist["url"]
            self.playlist_title = playlist["title"]


class Download:

    def __init__(self):
        super().__init__()
        self.dz = deezer.Deezer()
        self.di = dmi.DeemixInterface()
        self.db = Deemon().db
        self.config = Deemon().config
        self.queue_list = []
        self.bitrate = None

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

    def download_queue(self, queue):
        if queue:
            plex = self.get_plex_server()
            print("----------------------------")
            logger.info("Sending " + str(len(queue)) + " release(s) to deemix for download:")

            for q in queue:
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
    def download(self, opt: dict):
        logger.debug("download called with options: " + str(opt))
        artist = {}

        if opt["bitrate"]:
            self.bitrate = opt["bitrate"]
        if opt["record_type"]:
            self.record_type = opt["record_type"]

        if opt["url"]:
            logger.info("Sending URL to deemix for processing:")
            self.di.download_url([opt["url"]], opt["bitrate"])

        if opt["file"]:
            logger.info(f"Reading from file {opt['file']}")
            if Path(opt['file']).exists():
                with open(opt['file'], 'r', encoding="utf8", errors="replace") as f:
                    make_csv = f.read().replace('\n', ',')
                    csv_to_list = make_csv.split(',')
                    artist_list = sorted(list(filter(None, csv_to_list)))
                    for name in artist_list:
                        try:
                            artist = self.dz.api.search_artist(name, limit=1)['data'][0]
                            album = self.dz.api.get_artist_albums(artist["id"])
                            self.add_to_queue(artist, album)
                            logger.info(f"Artist `{name}` added to queue")
                        except IndexError:
                            logger.warning(f"Artist '{name}' not found")

        if opt["artist_id"] or opt["artist"]:
            if opt["artist_id"]:
                artist = self.dz.api.get_artist(opt["artist_id"])
            elif opt["artist"]:
                artist = self.dz.api.search_artist(opt["artist"], limit=1)['data'][0]
                opt["artist_id"] = artist["id"]

            album = self.dz.api.get_artist_albums(opt["artist_id"])
            self.add_to_queue(artist, album)

        if opt["album_id"]:
            album = {'data': [self.dz.api.get_album(opt["album_id"])]}
            artist["name"] = album["data"][0]["artist"]["name"]
            self.add_to_queue(artist, album)

        self.download_queue(self.queue_list)
        self.db.commit()
