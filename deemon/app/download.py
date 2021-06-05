from plexapi.server import PlexServer
from deemon.app import dmi, notify
from deemon.app import Deemon
import logging
import deezer
import sys

logger = logging.getLogger(__name__)


class QueueItem:

    def __init__(self, artist: dict, album: dict):
        self.artist_name = artist["name"]
        self.bitrate = artist["bitrate"]
        self.album_id = album["id"]
        self.album_title = album["title"]
        self.url = album["link"]


class Download(Deemon):

    def __init__(self, login=True):
        super().__init__()
        self.dz = deezer.Deezer()
        self.di = dmi.DeemixInterface(self.config["download_path"], self.config["deemix_path"])
        self.deemix_logger = logging.getLogger("deemix")
        self.queue_list = []

        if login:
            if not self.di.login():
                logger.error("Error: ARL is invalid, expired or missing")
                sys.exit(1)

    def get_plex_server(self):
        baseurl = self.config["plex_baseurl"]
        token = self.config["plex_token"]
        if (baseurl != "") and (token != ""):
            try:
                logger.info("----------------------------")
                logger.info("Plex settings found! Trying to connect...")
                plex_server = PlexServer(baseurl, token, timeout=10)
                return plex_server
            except Exception:
                logger.error("Error: Unable to reach Plex server, please refresh manually.")
                return False


    def download_queue(self, queue):
        if queue:
            plex = self.get_plex_server()
            plex = None
            num_queued = len(queue)
            logger.info("----------------------------")
            logger.info("Sending " + str(num_queued) + " release(s) to deemix for download:")

            for q in queue:
                logger.info(f"+ {q.artist_name} - {q.album_title}... ")
                self.di.download_url([q.url], q.bitrate)

            print("")
            logger.info("Downloads complete!")
            if plex:
                logger.debug("Sending signal to refresh Plex library")
                plex.library.section(self.config["plex_library"]).update()

    def download(self, opt: dict):
        logger.debug("download called with options: " + str(opt))

        if opt["url"]:
            logger.info("Sending URL to deemix for processing:")
            self.deemix_logger.setLevel(logging.INFO)
            self.di.download_url([opt["url"]], opt["bitrate"])
        else:
            artist = {}
            if opt["artist_id"] or opt["artist"]:
                if opt["artist_id"]:
                    artist = self.dz.api.get_artist(opt["artist_id"])
                elif opt["artist"]:
                    artist = self.dz.api.search_artist(opt["artist"], limit=1)['data'][0]
                    opt["artist_id"] = artist["id"]
                album = self.dz.api.get_artist_albums(opt["artist_id"])

            if opt["album_id"]:
                album = {'data': [self.dz.api.get_album(opt["album_id"])]}
                artist["name"] = album["data"][0]["artist"]["name"]

            for _album in album['data']:
                if (opt["record_type"] == _album["record_type"]) or (opt["record_type"] == "all"):
                    logger.debug(f"QUEUE: Adding '{_album['title']}' to queue...")
                    artist["bitrate"] = opt["bitrate"]
                    self.queue_list.append(QueueItem(artist, _album))

            self.download_queue(self.queue_list)
        self.db.commit_and_close()
