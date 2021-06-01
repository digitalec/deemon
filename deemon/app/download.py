from deemon.app import settings, dmi, db, notify
from plexapi.server import PlexServer
from deemon.app import Deemon
import progressbar
import logging
import deezer
import sys

logger = logging.getLogger(__name__)


class Download(Deemon):

    def __init__(self, login=True):
        super().__init__()
        self.dz = deezer.Deezer()
        self.di = dmi.DeemixInterface(self.config["download_path"], self.config["deemix_path"])
        self.deemix_logger = logging.getLogger("deemix")
        self.queue_list = []

        if login:
            if not self.di.login():
                logger.error("ARL is invalid, expired or missing")
                sys.exit(1)

    def get_plex_server(self):
        baseurl = self.config["plex_baseurl"]
        token = self.config["plex_token"]
        if (baseurl != "") and (token != ""):
            plex_server = PlexServer(baseurl, token)
            return plex_server

    def download_queue(self, queue):
        if queue:
            plex = self.get_plex_server()
            num_queued = len(queue)
            logger.info("----------------------------")
            logger.info("Sending " + str(num_queued) + " release(s) to deemix for download:")

            for q in queue:
                logger.info(f"Downloading {q.artist_name} - {q.album_title}... ")
                self.di.download_url([q.url], q.bitrate)

            if plex:
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

    def refresh(self, artists=None, skip_download=False):
        if artists is None:
            monitored_artists = self.db.get_all_artists()
        elif type(artists) is int:
            monitored_artists = [self.db.get_specified_artist_from_id(artists)]
        else:
            monitored_artists = self.db.get_specified_artists(artists)
            if len(monitored_artists) == 0:
                sys.exit(0)

        new_release_counter = 0
        new_artist = False

        logger.info("\nRefreshing artists, this may take some time...")
        bar = progressbar.ProgressBar(maxval=len(monitored_artists),
                                      widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
        bar.start()
        for idx, _artist in enumerate(monitored_artists):
            artist = {"id": _artist[0], "name": _artist[1], "bitrate": _artist[2]}
            record_type = _artist[3]
            alerts = _artist[4]
            artist_exists = self.db.check_exists(artist_id=artist["id"])
            if not artist_exists:
                new_artist = True
                logger.debug(f"New artist detected: {artist['name']}, future releases will be downloaded")

            albums = self.dz.api.get_artist_albums(artist["id"])
            for album in albums["data"]:
                already_exists = self.db.check_exists(album_id=album["id"])
                if not already_exists:
                    self.db.add_new_release(artist["id"], artist["name"], album["id"], album["title"],
                                            album["release_date"])

                if already_exists or skip_download or new_artist:
                    continue

                new_release_counter += 1

                if (record_type == album["record_type"]) or (record_type == "all"):
                    logger.debug(f"queue: added {artist['name']} - {album['title']} to the queue")
                    self.queue_list.append(QueueItem(artist, album))
            bar.update(idx)
        bar.finish()
        logger.info("Refresh complete")
        if self.queue_list:
            self.download_queue(self.queue_list)
        self.db.commit()


class QueueItem:

    def __init__(self, artist: dict, album: dict):
        self.artist_name = artist["name"]
        self.bitrate = artist["bitrate"]
        self.album_id = album["id"]
        self.album_title = album["title"]
        self.url = album["link"]
