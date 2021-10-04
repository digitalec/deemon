import logging
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from datetime import datetime
from deemon.cmd.download import QueueItem, Download
from deemon.core.config import Config as config
from deemon.core import db, api
from deemon.utils import dates

logger = logging.getLogger(__name__)


class Refresh:
    def __init__(self, time_machine: datetime = None, skip_download: bool = False):
        self.db = db.Database()
        self.release_date = datetime.now()
        self.api = api.PlatformAPI("deezer-gw")
        self.new_releases = []
        self.new_playlist_releases = []
        self.time_machine = False
        self.total_new_releases = 0
        self.queue_list = []
        self.skip_download = skip_download

        if time_machine:
            self.release_date = time_machine
            self.time_machine = True
            logger.info(f":: Time Machine active: {datetime.strftime(self.release_date, '%b %d, %Y')}!")
            config.set('by_release_date', False)

    def remove_existing_releases(self, payload: dict) -> list:
        """
        Return list of releases that have not been stored in the database
        """
        new_releases = []

        if payload.get('artist_id'):
            new_releases = []
            artist_id = payload['artist_id']
            seen_releases = self.db.get_artist_releases(artist_id)
            if seen_releases:
                seen_releases = [v for x in seen_releases for k, v in x.items()]
                new_releases = [x for x in payload['releases'] if type(x) == dict for k, v in x.items() if k == "id" and v not in seen_releases]
                return new_releases
            return [x for x in payload['releases']]

        if payload.get('tracks'):
            playlist_id = payload['id']
            seen_releases = self.db.get_playlist_tracks(playlist_id)
            if seen_releases:
                seen_releases = [v for x in seen_releases for k, v in x.items()]
                new_releases = [x for x in payload['tracks'] if type(x) == dict for k, v in x.items() if k == "id" and v not in seen_releases]
                return new_releases

        return new_releases

    def filter_new_releases(self, payload: dict):
        if payload.get('artist_id'):
            for release in payload['releases']:
                if config.record_type() == release['record_type'] or config.record_type() == "all":
                    album_release = dates.str_to_datetime_obj(release['release_date'])
                    if album_release > datetime.now():
                        release['future'] = 1
                        logger.info(f":: FUTURE RELEASE DETECTED :: {release['artist_name']} - {release['title']} "
                                    f"({release['release_date']})")
                    else:
                        new_release = release.copy()
                        new_release['artist_id'] = payload['artist_id']
                        new_release['artist_name'] = payload['artist_name']
                        self.new_releases.append(new_release)
                        if self.skip_download:
                            continue
                        if (self.time_machine and album_release > self.release_date) or \
                                (payload['refreshed'] and not self.time_machine):
                            logger.debug(f"Queueing new release: {payload['artist_name']} - {release['title']} "
                                         f"({release['id']})")
                            self.queue_list.append(QueueItem(artist=payload, album=release,
                                                             bitrate=payload['bitrate'],
                                                             download_path=payload['download_path']))
        if payload.get('tracks'):
            if len(payload['tracks']):
                for track in payload['tracks']:
                    new_track = track.copy()
                    new_track['playlist_id'] = payload['id']
                    self.new_playlist_releases.append(new_track)
                if not self.skip_download:
                    self.queue_list.append(QueueItem(playlist=payload, bitrate=payload['bitrate'],
                                                     download_path=payload['download_path']))

    def waiting_for_refresh(self):
        playlists = self.db.get_unrefreshed_playlists()
        artists = self.db.get_unrefreshed_artists()
        if len(playlists) or len(artists):
            return {'artists': artists, 'playlists': playlists}

    # @performance.timeit
    def run(self, artists: list = None, playlists: list = None):
        if artists:
            monitored_artists = [self.db.get_monitored_artist_by_name(a) for a in artists]
            api_result = self.get_release_data({'artists': monitored_artists})
            logger.debug(f"Accepted {len(artists)} artist(s) for refresh")
        elif playlists:
            monitored_playlists = [self.db.get_monitored_playlist_by_name(p) for p in playlists]
            api_result = self.get_release_data({'playlists': monitored_playlists})
            logger.debug(f"Accepted {len(playlists)} playlist(s) for refresh")
        else:
            waiting = self.waiting_for_refresh()
            if waiting:
                logger.debug(f"There are {len(waiting['playlists'])} playlist(s) and "
                             f"{len(waiting['artists'])} artist(s) waiting to be refreshed.")
                api_result = self.get_release_data(waiting)
            else:
                monitored_playlists = self.db.get_all_monitored_playlists()
                monitored_artists = self.db.get_all_monitored_artists()
                api_result = self.get_release_data({'artists': monitored_artists, 'playlists': monitored_playlists})

        for payload in api_result['artists']:
            if len(payload):
                payload['releases'] = self.remove_existing_releases(payload)
                self.filter_new_releases(payload)

        for payload in api_result['playlists']:
            if len(payload):
                payload['tracks'] = self.remove_existing_releases(payload)
                self.filter_new_releases(payload)

        if len(self.queue_list):
            dl = Download()
            dl.download_queue(self.queue_list)

        self.db.add_new_playlist_releases(self.new_playlist_releases)
        self.db.add_new_releases(self.new_releases)
        self.db.commit()

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

        if len(to_refresh['playlists']):
            with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
                api_result['playlists'] = list(
                    tqdm(ex.map(self.api.get_playlist, to_refresh['playlists']),
                        total=len(to_refresh['playlists']), desc="Refreshing playlists ...", ascii=" #",
                        bar_format='[{n_fmt}/{total_fmt}] {desc} [{bar}] {percentage:3.0f}%')
                )

        if len(to_refresh['artists']):
            with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
                api_result['artists'] = list(
                    tqdm(ex.map(self.api.get_artist_albums, to_refresh['artists']),
                         total=len(to_refresh['artists']), desc="Refreshing artists ...", ascii=" #",
                         bar_format='[{n_fmt}/{total_fmt}] {desc} [{bar}] {percentage:3.0f}%')
                )
        return api_result

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
