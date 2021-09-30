import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from datetime import datetime
from deemon.cmd.download import QueueItem, Download
from deemon.core.config import Config as config
from deemon.core import db, api
from deemon.utils import dates, performance

logger = logging.getLogger(__name__)


class Refresh:
    def __init__(self, time_machine: datetime = None):
        self.db = db.Database()
        self.release_date = datetime.now()
        self.api = api.PlatformAPI("deezer-gw")
        self.new_releases = []
        self.time_machine = False
        self.total_new_releases = 0
        self.queue_list = []
        self.skip_download = False

        if time_machine:
            self.release_date = time_machine
            self.time_machine = True
            logger.info(f":: Time Machine active: {datetime.strftime(self.release_date, '%b %d, %Y')}!")
            config.set('by_release_date', False)

    def remove_existing_releases(self, payload: dict):
        """
        Return list of releases that have not been stored in the database
        """
        artist_id = payload['artist']['artist_id']
        seen_releases = self.db.get_artist_releases(artist_id)
        seen_releases = [v for x in seen_releases for k, v in x.items()]
        new_releases = [x for x in payload['releases'] if type(x) == dict for k, v in x.items() if k == "id" and v not in seen_releases]
        return new_releases

    def filter_new_releases(self, payload: dict):
        for release in payload['releases']:
            if config.record_type() == release['record_type'] or config.record_type() == "all":
                album_release = dates.str_to_datetime_obj(release['release_date'])
                if album_release > datetime.now():
                    release['future'] = 1
                    logger.info(f":: FUTURE RELEASE DETECTED :: {release['artist_name']} - {release['title']} "
                                f"({release['release_date']})")
                else:
                    self.new_releases.append(release)
                    if (self.time_machine and album_release > self.release_date) or \
                            (payload['artist']['refreshed'] and not self.skip_download and not self.time_machine):
                        logger.debug(f"Queueing new release: {payload['artist']['artist_name']} - {release['title']} "
                                     f"({release['id']})")
                        self.queue_list.append(QueueItem(artist=payload['artist'], album=release,
                                                         bitrate=payload['artist']['bitrate'],
                                                         download_path=payload['artist']['download_path']))

    # @performance.timeit
    def run(self, artists: list = None, playlists: list = None):
        api_result = self.get_release_data(artists)

        for payload in api_result:
            if len(payload):
                payload['releases'] = self.remove_existing_releases(payload)
                self.filter_new_releases(payload)

        if len(self.queue_list):
            dl = Download()
            dl.download_queue(self.queue_list)

        self.db.add_new_releases(self.new_releases)
        self.db.commit()

    # @performance.timeit
    def get_release_data(self, artists: list = None) -> list:
        """
        Generate a list of dictionaries containing artist (DB) and release (API)
        information.
        """
        if not artists:
            artists = self.db.get_unrefreshed_artists()
            if len(artists):
                logger.debug("Detected artist(s) awaiting refresh, selecting...")
            else:
                artists = self.db.get_all_monitored_artists()
                logger.debug("Selecting all artists for refresh...")
        if self.time_machine:
            logger.debug("Time machine has been detected; clearing future releases...")
            ids = [{'id': artist['artist_id']} for artist in artists]
            self.db.remove_specific_releases(ids)
        with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
            api_result = list(tqdm(ex.map(self.artist_payload, [artist for artist in artists]),
                                   total=len(artists), desc="Refreshing artists ...", ascii=" #",
                                   bar_format='[{n_fmt}/{total_fmt}] {desc} [{bar}] {percentage:3.0f}%'))
        return api_result

    def artist_payload(self, artist: dict) -> dict:
        return {"artist": artist, "releases": self.api.get_artist_albums(artist['artist_id'])}

    def queue_new_releases(self, artist, album):
        is_new_release = 0
        if (artist['record_type'] == album['record_type']) or artist['record_type'] == "all":
            if config.release_by_date():
                max_release_date = dates.get_max_release_date(config.release_max_days())
                if album['release_date'] < max_release_date:
                    logger.debug(f"Release {album['id']} outside of max_release_date, skipping...")
                    return is_new_release
            self.total_new_releases += 1
            is_new_release = 1

            self.queue_list.append(QueueItem(artist=artist, album=album, bitrate=artist['bitrate'],
                                                      download_path=artist['download_path']))
            logger.debug(f"Release {album['id']} added to queue")
            if artist["alerts"]:
                self.append_new_release(album['release_date'], artist['artist_name'],
                                        album['title'], album['cover_medium'])
        else:
            logger.debug(f"Release {album['id']} does not meet album_type "
                         f"requirement of '{config.record_type()}'")
        return is_new_release

    def append_new_release(self, release_date, artist, album, cover):
        for days in self.new_releases:
            for key in days:
                if key == "release_date":
                    if release_date in days[key]:
                        days["releases"].append({'artist': artist, 'album': album, 'cover': cover})
                        return

        self.new_releases.append({'release_date': release_date, 'releases': [{'artist': artist, 'album': album}]})
