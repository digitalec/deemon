import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from tqdm import tqdm

from deemon.cmd.download import QueueItem, Download
from deemon.core import db, api, notifier
from deemon.core.config import Config as config
from deemon.utils import dates, ui, performance

logger = logging.getLogger(__name__)


class Refresh:
    def __init__(self, time_machine: datetime = None, skip_download: bool = False, ignore_filters: bool = False):
        self.db = db.Database()
        self.release_date = datetime.now()
        self.api = api.PlatformAPI("deezer-gw")
        self.new_releases = []
        self.new_releases_alert = []
        self.new_playlist_releases = []
        self.time_machine = False
        self.total_new_releases = 0
        self.queue_list = []
        self.skip_download = skip_download
        self.ignore_filters = ignore_filters

        if time_machine:
            self.release_date = time_machine
            self.time_machine = True
            logger.info(f":: Time Machine active: {datetime.strftime(self.release_date, '%b %d, %Y')}!")
            config.set('by_release_date', False)

    def debugger(self, message: str, payload = None):
        if config.debug_mode():
            if not payload:
                payload = ""
            logger.debug(f"DEBUG_MODE: {message} {str(payload)}")

    def remove_existing_releases(self, payload: dict) -> list:
        """
        Return list of releases that have not been stored in the database
        """
        new_releases = []

        if payload.get('artist_id'):
            seen_releases = self.db.get_artist_releases()
            if seen_releases:
                seen_releases = [v for x in seen_releases for k, v in x.items()]
                new_releases = [x for x in payload['releases'] if type(x) == dict for k, v in x.items() if
                                k == "id" and v not in seen_releases]
                return new_releases
            return [x for x in payload['releases']]

        if payload.get('tracks'):
            playlist_id = payload['id']
            seen_releases = self.db.get_playlist_tracks(playlist_id)
            if seen_releases:
                seen_releases = [v for x in seen_releases for k, v in x.items()]
                new_releases = [x for x in payload['tracks'] if type(x) == dict for k, v in x.items() if
                                k == "id" and v not in seen_releases]
                return new_releases

        return new_releases

    # TODO This is a mess.
    def filter_new_releases(self, payload: dict):
        if payload.get('artist_id'):
            self.debugger(f"Filtering {len(payload['releases'])} releases for artist {payload['artist_name']} "
                         f"({payload['artist_id']})")
            if self.ignore_filters:
                logger.debug("Ignore filters has been set, adding all releases")
                for release in payload['releases']:
                    release['artist_id'] = payload['artist_id']
                    release['artist_name'] = payload['artist_name']
                    release['future'] = 0
                    self.new_releases.append(release)
                    queue_obj = QueueItem(artist=payload, album=release, bitrate=payload['bitrate'],
                                          download_path=payload['download_path'])
                    self.debugger("QueueArtistItem", vars(queue_obj))
                    self.queue_list.append(queue_obj)
                return
            for release in payload['releases']:
                release['artist_id'] = payload['artist_id']
                release['artist_name'] = payload['artist_name']
                release['future'] = 0
                self.debugger("ProcessingRelease", release)
                if payload['record_type'] and payload['record_type'] != release['record_type']:
                    self.new_releases.append(release)
                    continue
                if payload['record_type'] == release['record_type'] or config.record_type() == release['record_type'] or config.record_type() == "all":
                    album_release = dates.str_to_datetime_obj(release['release_date'])
                    if config.release_by_date():
                        max_release_date = dates.str_to_datetime_obj(dates.get_max_release_date(config.release_max_days()))
                        if album_release < max_release_date:
                            logger.debug(f"Release {release['id']} outside of max_release_date, skipping...")
                            self.new_releases.append(release)
                            continue
                    if album_release > datetime.now():
                        release['future'] = 1
                        self.new_releases.append(release)
                        logger.debug(f"Future release detected >>> {payload['artist_name']} - {release['title']} "
                                     f"[{release['release_date']}]")
                    else:
                        new_release = release.copy()
                        self.new_releases.append(new_release)
                        if (self.time_machine and album_release > self.release_date) or \
                                (payload['refreshed'] and not self.time_machine):
                            logger.debug(f"Queueing new release: {payload['artist_name']} - {release['title']} "
                                         f"({release['id']})")
                            queue_obj = QueueItem(artist=payload, album=release, bitrate=payload['bitrate'],
                                                     download_path=payload['download_path'])
                            self.debugger("QueueArtistItem", vars(queue_obj))
                            self.queue_list.append(queue_obj)
                            if payload["alerts"] == 1 or not payload['alerts'] and config.alerts():
                                self.append_new_release(release['release_date'], payload['artist_name'],
                                                        release['title'])
                else:
                    logger.debug(f"Release {release['id']} does not match record_type "
                                 f"\"{config.record_type()}\", skipping...")
                    self.new_releases.append(release)


        if payload.get('tracks'):
            self.debugger(f"Filtering {len(payload['tracks'])} tracks for playlist {payload['title']}")
            if len(payload['tracks']):
                for track in payload['tracks']:
                    new_track = track.copy()
                    new_track['playlist_id'] = payload['id']
                    self.new_playlist_releases.append(new_track)
                    queue_obj = QueueItem(playlist=payload, bitrate=payload['bitrate'],
                                          download_path=payload['download_path'])
                    self.debugger("QueuePlaylistItem", queue_obj)
                    self.queue_list.append(queue_obj)

    def waiting_for_refresh(self):
        playlists = self.db.get_unrefreshed_playlists()
        artists = self.db.get_unrefreshed_artists()
        if len(playlists) or len(artists):
            return {'artists': artists, 'playlists': playlists}

    # @performance.timeit
    def run(self, artists: list = None, playlists: list = None):
        if artists:
            self.debugger("ManualRefresh", artists)
            monitored_artists = [x for x in (self.db.get_monitored_artist_by_name(a) for a in artists) if x]
            if not len(monitored_artists):
                return logger.warning("Specified artist(s) were not found")
            api_result = self.get_release_data({'artists': monitored_artists})
        elif playlists:
            self.debugger("ManualRefresh", playlists)
            monitored_playlists = [x for x in (self.db.get_monitored_playlist_by_name(p) for p in playlists) if x]
            if not len(monitored_playlists):
                return logger.warning("Specified playlist(s) were not found")
            api_result = self.get_release_data({'playlists': monitored_playlists})
        else:
            waiting = self.waiting_for_refresh()
            if waiting:
                logger.debug(f"There are {len(waiting['playlists'])} playlist(s) and "
                             f"{len(waiting['artists'])} artist(s) waiting to be refreshed.")
                api_result = self.get_release_data(waiting)
            else:
                self.debugger("FullRefresh")
                monitored_playlists = self.db.get_all_monitored_playlists()
                monitored_artists = self.db.get_all_monitored_artists()
                if not len(monitored_playlists) and not len(monitored_artists):
                    return logger.warning("No artists found to refresh")
                api_result = self.get_release_data({'artists': monitored_artists, 'playlists': monitored_playlists})

        artist_processor = tqdm(api_result['artists'], total=len(api_result['artists']), desc="Checking for new releases...",
                                ascii=" #", bar_format=ui.TQDM_FORMAT)
        for payload in artist_processor:
            if len(payload):
                payload['releases'] = self.remove_existing_releases(payload)
                self.filter_new_releases(payload)

        for payload in api_result['playlists']:
            if len(payload):
                payload['tracks'] = self.remove_existing_releases(payload)
                self.filter_new_releases(payload)

        if self.skip_download:
            logger.info(f"You have opted to skip downloads, emptying {len(self.queue_list)} item(s) from queue...")
            self.queue_list.clear()
            self.new_releases_alert.clear()

        if len(self.queue_list):
            dl = Download()
            dl.download_queue(self.queue_list)

        if len(self.new_playlist_releases) or len(self.new_releases):
            if len(self.new_playlist_releases):
                self.db.add_new_playlist_releases(self.new_playlist_releases)
            if len(self.new_releases):
                self.db.add_new_releases(self.new_releases)
            self.db.commit()
            self.db_stats()
            performance.operation_time(config.get('start_time'))
            logger.info("Database is up-to-date.")
        else:
            self.db_stats()
            performance.operation_time(config.get('start_time'))
            logger.info("Database is up-to-date. No new releases were found.")

        if len(self.new_releases_alert) > 0:
            notification = notifier.Notify(self.new_releases_alert)
            notification.send()

    def db_stats(self):
        artists = len(self.db.get_all_monitored_artist_ids())
        playlists = len(self.db.get_all_monitored_playlist_ids())
        releases = len(self.db.get_artist_releases())
        future = len(self.db.get_future_releases())

        print("")
        print(f"+ Artists monitored: {artists:,}")
        print(f"+ Playlists monitored: {playlists:,}")
        print(f"+ Releases seen: {releases:,}")
        print(f"+ Pending future releases: {future:,}")
        print("")

    # @performance.timeit
    def get_release_data(self, to_refresh: dict) -> dict:
        """
        Generate a list of dictionaries containing artist (DB) and release (API)
        information.
        """
        if self.time_machine:
            logger.debug("Time machine has been detected; clearing future releases...")
            artist_ids = [{'id': artist['artist_id']} for artist in to_refresh['artists']]
            playlist_ids = [{'id': playlist['id']} for playlist in to_refresh['playlists']]
            self.db.remove_specific_releases(artist_ids)
            self.db.remove_specific_playlist_tracks(playlist_ids)

        api_result = {'artists': [], 'playlists': []}

        logger.debug(f"Standby, starting refresh...")

        if to_refresh.get('playlists') and len(to_refresh.get('playlists')):
            logger.debug("Fetching playlist track data...")
            self.debugger("SpawningThreads", self.api.max_threads)
            with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
                api_result['playlists'] = list(
                    tqdm(ex.map(self.api.get_playlist, to_refresh['playlists']),
                         total=len(to_refresh['playlists']), desc=f"Fetching playlist track data for {len(to_refresh['playlists'])} playlist(s), please wait...", ascii=" #",
                         bar_format=ui.TQDM_FORMAT)
                )

        if to_refresh.get('artists') and len(to_refresh['artists']):
            logger.debug("Fetching artist release data...")
            self.debugger("SpawningThreads", self.api.max_threads)
            with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
                api_result['artists'] = list(
                    tqdm(ex.map(self.api.get_artist_albums, to_refresh['artists']),
                         total=len(to_refresh['artists']), desc=f"Fetching artist release data for {len(to_refresh['artists']):,} artist(s), please wait...", ascii=" #",
                         bar_format=ui.TQDM_FORMAT)
                )
        return api_result

    def append_new_release(self, release_date, artist, album):
        for days in self.new_releases_alert:
            for key in days:
                if key == "release_date":
                    if release_date in days[key]:
                        days["releases"].append({'artist': artist, 'album': album})
                        return

        self.new_releases_alert.append({'release_date': release_date, 'releases': [{'artist': artist, 'album': album}]})
