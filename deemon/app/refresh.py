from deemon.app import Deemon, utils, download, notify
import tqdm
import logging
import deezer

logger = logging.getLogger(__name__)


class Refresh(Deemon):

    def __init__(self, artist_id: list = None, skip_download: bool = False):
        super().__init__()

        if artist_id is None:
            self.artist_id = []

        self.skip_download = skip_download
        self.dz = deezer.Deezer()
        self.new_release_count = 0
        self.monitored_artists = []
        self.queue_list = []
        self.new_releases = []
        self.release_date = ""

    def is_future_release(self):
        today = utils.get_todays_date()
        if self.release_date > today:
            return 1
        else:
            return 0

    def get_monitored_artists(self):
        if len(self.artist_id) == 0:
            self.monitored_artists = self.db.get_all_monitored_artists()
        else:
            for artist in self.artist_id:
                self.monitored_artists.append(self.db.get_all_specified_artist(artist))

    def construct_new_release_list(self, release_date, artist, album, cover):
        for days in self.new_releases:
            for key in days:
                if key == "release_date":
                    if release_date in days[key]:
                        days["releases"].append({'artist': artist, 'album': album, 'cover': cover})
                        return

        self.new_releases.append({'release_date': release_date, 'releases': [{'artist': artist, 'album': album}]})

    def refresh(self):
        logger.debug(f"Refreshing artists")
        self.get_monitored_artists()

        if len(self.monitored_artists) == 0:
            logger.info("At least one artist needs to be monitored before you can refresh!")
            return

        progress = tqdm.tqdm(self.monitored_artists, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} '
                                                                '({elapsed}{postfix})')

        for artist in progress:
            progress.set_description("Refreshing")
            self.new_release_count = 0
            new_artist = False
            artist = {"id": artist[0], "name": artist[1], "bitrate": self.config["bitrate"], "record_type": artist[3]}
            artist_exists = self.db.get_artist_by_id(artist_id=artist["id"])
            albums = self.dz.api.get_artist_albums(artist["id"])

            if not artist_exists:
                new_artist = True
                logger.debug(f"New artist detected: {artist['name']}, future releases will be downloaded")

            if new_artist:
                if len(albums["data"]) == 0:
                    logger.warning(f"WARNING: Artist '{artist['name']}' setup for monitoring but no releases were found.")

            for album in albums["data"]:

                already_exists = self.db.get_album_by_id(album_id=album["id"])
                todays_date = utils.get_todays_date()

                if already_exists:
                    release = [x for x in already_exists]
                    _album = {
                        'artist_id': release[0],
                        'artist_name': release[1],
                        'album_id': release[2],
                        'album_name': release[3],
                        'release_date': release[4],
                        'future_release': release[6]
                    }

                    if _album["future_release"] and (_album["release_date"] <= todays_date):
                        logger.info(f"Artist: {_album['artist_name']} ** Pre-release has now been released "
                                    f"and will be downloaded **")
                        self.db.reset_future(_album['album_id'])
                    else:
                        continue
                else:
                    self.db.add_new_release(
                        artist["id"],
                        artist["name"],
                        album["id"],
                        album["title"],
                        album["release_date"],
                        future_release=self.is_future_release()
                    )

                if self.skip_download or new_artist:
                    continue

                self.new_release_count += 1

                if (self.config["record_type"] == album["record_type"]) or (self.config["record_type"] == "all"):
                    if self.config["release_by_date"]:
                        max_release_date = utils.get_max_release_date(self.config["release_max_days"])
                        if album['release_date'] < max_release_date:
                            logger.debug(f"Release '{artist['name']} - {album['title']}' skipped, too old...")
                            continue
                    logger.debug(f"queue: added {artist['name']} - {album['title']} to the queue")
                    self.queue_list.append(download.QueueItem(artist, album))
                    self.construct_new_release_list(album['release_date'], artist['name'],
                                                    album['title'], album['cover_medium'])

            if self.new_release_count > 0:
                logger.info(f"{artist['name']}: {self.new_release_count} new release(s)")

        logger.debug("Refresh complete")
        if self.queue_list:
            print("")
            dl = download.Download()
            dl.download_queue(self.queue_list)
        self.db.commit()

        if len(self.new_releases) > 0 and self.config["alerts"] == 1:
            notification = notify.Notify(self.new_releases)
            notification.send()
