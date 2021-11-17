import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from tqdm import tqdm

from deemon.cmd.download import QueueItem, Download
from deemon.core import db, api, notifier
from deemon.core.config import Config as config
from deemon.utils import dates, ui, performance

logger = logging.getLogger(__name__)


class Refresh:
    def __init__(self, time_machine: datetime = None, skip_download: bool = False, ignore_filters: bool = False):
        self.db = db.Database()
        self.refresh_date = datetime.now()
        self.max_refresh_date = None
        self.api = api.PlatformAPI()
        self.new_releases = []
        self.new_releases_alert = []
        self.new_playlist_releases = []
        self.time_machine = time_machine
        self.total_new_releases = 0
        self.queue_list = []
        self.skip_download = skip_download
        self.download_all = ignore_filters
        self.seen = None

        if self.time_machine:
            logger.info(f":: Time Machine active: {datetime.strftime(self.time_machine, '%b %d, %Y')}!")
            config.set('by_release_date', False)
            self.db.remove_specific_releases({'tm_date': str(self.time_machine)})
            self.db.commit()

    @staticmethod
    def debugger(message: str, payload = None):
        if config.debug_mode():
            if not payload:
                payload = ""
            logger.debug(f"DEBUG_MODE: {message} {str(payload)}")

    def remove_existing_releases(self, payload: dict, seen: dict) -> list:
        """
        Return list of releases that have not been stored in the database
        """
        new_releases = []

        if payload.get('artist_id'):
            seen_releases = seen
            if seen_releases:
                seen_releases = [v for x in seen_releases for k, v in x.items() if not x.get('future_release', 0)]
                new_releases = [x for x in payload['releases'] if type(x) == dict for k, v in x.items() if
                                k == "id" and v not in seen_releases]
                return new_releases
            return [x for x in payload['releases']]

        if payload.get('tracks'):
            playlist_id = payload['id']
            seen_releases = self.db.get_playlist_tracks(playlist_id)
            if seen_releases:
                seen_releases = [v for x in seen_releases for k, v in x.items()]
                new_releases = [x for x in payload['tracks']
                                if type(x) == dict for k, v in x.items()
                                if k == "id" and v not in seen_releases]
                return new_releases
            return [x for x in payload['tracks']]

        return new_releases

    def filter_artist_releases(self, payload: dict):
        """ Inspect artist releases and decide what to do with each release """
        self.debugger("FilterReleases", {'artist': payload['artist_id'],
                                         'releases': len(payload['releases'])})

        for release in payload['releases']:
            release['artist_id'] = payload['artist_id']
            release['artist_name'] = payload['artist_name']
            release['future'] = self.is_future_release(release['release_date'])
            
            if release['explicit_lyrics'] != 1:
                release['explicit_lyrics'] = 0
            
            self.append_database_release(release)
            
            if release['future']:
                continue

            explicit_album_id = self.explicit_id(release['title'], payload['releases'])
            if explicit_album_id:
                if explicit_album_id == release['id']:
                    logger.debug(f"An explicit release was found for {release['title']}")
                else:
                    continue

            if self.download_all:
                self.queue_release(release)
                continue

            if not self.allowed_record_type(payload['record_type'], release['record_type']):
                logger.debug(f"Record type \"{release['record_type']}\" has been filtered out, skipping release "
                             f"{release['id']}")
                continue

            if self.release_too_old(release['release_date']):
                logger.debug(f"Release {release['id']} is too old, skipping it.")
                continue

            if not payload['refreshed'] and not self.time_machine:
                continue

            self.queue_release(release)

    def append_database_release(self, new_release: dict):
        self.new_releases.append(new_release)
                
    @staticmethod
    def explicit_id(release_title: str, payload: list):
        for release in payload:
            if release['title'] == release_title:
                if release['explicit_lyrics'] == 1:
                    return release['id']

    def release_too_old(self, release_date: str):
        release_date_dt = dates.str_to_datetime_obj(release_date)
        if self.time_machine:
            if release_date_dt <= self.time_machine:
                self.debugger(f"Release date \"{release_date}\" is older than TIME_MACHINE ({str(dates.ui_date(self.time_machine))})")
                return True
        if config.release_by_date():
            if release_date_dt < (self.refresh_date - timedelta(config.release_max_age())):
                self.debugger(f"Release date \"{release_date}\" is older than RELEASE_MAX_AGE ({config.release_max_age()} day(s))")
                return True
            

    @staticmethod
    def is_future_release(release_date: str):
        """ Return 1 if release date is in future, otherwise return 0 """
        release_date_dt = dates.str_to_datetime_obj(release_date)
        if release_date_dt > datetime.now():
            return 1
        else:
            return 0

    @staticmethod
    def allowed_record_type(artist_rec_type, release_rec_type: str):
        """ Compare actual record_type against allowable """
        
        if artist_rec_type:
            if artist_rec_type == release_rec_type or artist_rec_type == "all":
                return True
            else:
                return
        elif config.record_type() == release_rec_type:
            return True
        elif config.record_type() == "all":
            return True

    def queue_release(self, release: dict):
        """ Add release to download queue and create alert notification """
        
        self.create_notification(release)
        self.queue_list.append(QueueItem(release_full=release))

    def filter_playlist_releases(self, payload: dict):
        self.debugger(f"Filtering {len(payload['tracks'])} tracks for playlist {payload['title']}")
        if len(payload['tracks']):
            for track in payload['tracks']:
                new_track = track.copy()
                new_track['playlist_id'] = payload['id']
                self.new_playlist_releases.append(new_track)
                
                if payload['refreshed'] == 0:
                    continue
                
            queue_obj = QueueItem(playlist=payload, bitrate=payload['bitrate'], download_path=payload['download_path'])
            self.debugger("QueuePlaylistItem", queue_obj)
            self.queue_list.append(queue_obj)

    def waiting_for_refresh(self):
        playlists = self.db.get_unrefreshed_playlists()
        artists = self.db.get_unrefreshed_artists()
        if len(playlists) or len(artists):
            return {'artists': artists, 'playlists': playlists}

    def prep_payload(self, p):
        if len(p):
            p['releases'] = self.remove_existing_releases(p, self.seen)
            self.filter_artist_releases(p)
        else:
            logger.debug("No payload provided")

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

        if len(api_result):
            self.seen = self.db.get_artist_releases()
            payload_container = tqdm(api_result['artists'], total=len(api_result['artists']),
                                     desc=f"Scanning release data for new releases...",
                                     ascii=" #",
                                     bar_format=ui.TQDM_FORMAT)
            for payload in payload_container:
                self.prep_payload(payload)

        for payload in api_result['playlists']:
            if len(payload):
                self.seen = self.db.get_playlist_tracks(payload['id'])
                payload['tracks'] = self.remove_existing_releases(payload, self.seen)
                self.filter_playlist_releases(payload)

        if self.skip_download:
            logger.info(f"   [!] You have opted to skip downloads, clearing {len(self.queue_list):,} item(s) from queue...")
            self.queue_list.clear()
            self.new_releases_alert.clear()

        if len(self.queue_list):
            if config.check_account_status():
                if self.api.account_type == "free" and config.bitrate() != "128":
                    notification = notifier.Notify()
                    notification.expired_arl()
                    return logger.error("   [X] Deezer account only allows low"
                                        " quality. If you wish to download "
                                        "anyway, set `check_account_status` "
                                        "to False in the config.")
            dl = Download()
            dl.download_queue(self.queue_list)


        if len(self.new_playlist_releases) or len(self.new_releases):
            if len(self.new_playlist_releases):
                logger.debug("Updating playlist releases in database...")
                self.db.add_new_playlist_releases(self.new_playlist_releases)
            if len(self.new_releases):
                logger.debug("Updating artist releases in database...")
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

    def get_release_data(self, to_refresh: dict) -> dict:
        """
        Generate a list of dictionaries containing artist (DB) and release (API)
        information.
        """

        api_result = {'artists': [], 'playlists': []}

        logger.debug(f"Standby, starting refresh...")

        if to_refresh.get('playlists') and len(to_refresh.get('playlists')):
            logger.debug("Fetching playlist track data...")
            self.debugger("SpawningThreads", self.api.max_threads)
            with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
                api_result['playlists'] = list(
                    tqdm(ex.map(self.api.get_playlist_tracks,
                                to_refresh['playlists']),
                         total=len(to_refresh['playlists']),
                         desc=f"Fetching playlist track data for "
                              f"{len(to_refresh['playlists'])} playlist(s), "
                              "please wait...",
                         ascii=" #",
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

    def create_notification(self, release: dict):
        for days in self.new_releases_alert:
            for key in days:
                if key == "release_date":
                    if release['release_date'] in days[key]:
                        days["releases"].append(
                            {
                                'artist': release['artist_name'],
                                'album': release['title'],
                                'cover': release['cover_big'],
                                'url': release['link'],
                                'track_num': release.get('nb_tracks', None),
                                'record_type': release['record_type'],
                            }
                        )
                        return

        self.new_releases_alert.append(
            {
                'release_date': release['release_date'], 
                'releases': [
                    {
                        'artist': release['artist_name'],
                        'album': release['title'],
                        'cover': release['cover_big'],
                        'url': release['link'],
                        'track_num': release.get('nb_tracks', None),
                        'record_type': release['record_type'],
                    }
                ]
            }
        )
