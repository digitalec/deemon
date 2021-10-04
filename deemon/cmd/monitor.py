import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tqdm import tqdm

from deemon.cmd import search
from deemon.cmd.refresh import Refresh
from deemon.core.api import PlatformAPI
from deemon.core.config import Config as config
from deemon.core.db import Database
from deemon.utils import performance, dataprocessor

logger = logging.getLogger(__name__)


class Monitor:

    def __init__(self):
        self.bitrate = None
        self.alerts = False
        self.record_type = None
        self.download_path = None
        self.remove = False
        self.refresh = True
        self.is_search = False
        self.duplicates = 0
        self.time_machine = None
        self.dl = None
        self.db = Database()
        self.api = PlatformAPI("deezer-gw")
        self.artist_not_found = []

    def set_config(self, bitrate: str, alerts: bool, record_type: str, download_path: Path):
        self.bitrate = bitrate
        self.alerts = alerts
        self.record_type = record_type
        self.download_path = download_path

    def set_options(self, remove, download_object, search):
        self.remove = remove
        self.dl = download_object
        self.is_search = search

    def get_best_result(self, name) -> list:
        api_result: list = self.api.search_artist(name)
        matches = [r for r in api_result if r['name'].lower() == name.lower()]
        if len(matches) == 1:
            if self.is_search:
                pass
            else:
                return [matches[0]]
        elif len(matches) > 1:
            if self.is_search or config.prompt_duplicates():
                prompt = self.prompt_search(name, matches)
                if prompt:
                    return [prompt]
                else:
                    logger.info(f"No selection made, skipping {name}...")
                    return []
            else:
                self.duplicates += 1
                return [matches[0]]
        elif not len(matches):
            if config.prompt_no_matches():
                prompt = self.prompt_search(name, api_result)
                if prompt:
                    return [prompt]
                else:
                    logger.info(f"No selection made, skipping {name}...")
                    return []
            else:
                self.artist_not_found.append(name)
                return []

    def prompt_search(self, value, api_result):
        menu = search.Search()
        ask_user = menu.artist_menu(value, api_result, True)
        if ask_user:
            return {'id': ask_user['id'], 'name': ask_user['name']}
        return logger.debug("No artist selected, skipping...")

    @performance.timeit
    def build_artist_query(self, api_result: list):
        existing = self.db.get_all_monitored_artist_ids()
        artists_to_add = []
        pbar = tqdm(api_result, total=len(api_result), desc="Monitoring artists ...", ascii=" #",
                    bar_format='[{n_fmt}/{total_fmt}] {desc} [{bar}] {percentage:3.0f}%')
        for i, artist in enumerate(pbar):
            if artist['id'] in existing:
                logger.info(f"Already monitoring {artist['name']}, skipping...")
            else:
                artist.update({'bitrate': self.bitrate, 'alerts': self.alerts, 'record_type': self.record_type,
                               'download_path': self.download_path, 'profile_id': config.profile_id(),
                               'trans_id': config.transaction_id()})
                artists_to_add.append(artist)
            if artist == api_result[-1]:
                pbar.set_description_str("Updating database  ...")
                self.db.new_transaction()
                self.db.fast_monitor(artists_to_add)
                self.db.commit()
                pbar.set_description_str("Monitoring complete!  ")

    def build_playlist_query(self, api_result: list):
        existing = self.db.get_all_monitored_playlist_ids() or []
        playlists_to_add = []
        pbar = tqdm(api_result, total=len(api_result), desc="Monitoring playlists..", ascii=" #",
                    bar_format='[{n_fmt}/{total_fmt}] {desc} [{bar}] {percentage:3.0f}%')
        for i, playlist in enumerate(pbar):
            if playlist['id'] in existing:
                logger.info(f"Already monitoring {playlist['title']}, skipping...")
            else:
                playlist.update({'bitrate': self.bitrate, 'alerts': self.alerts, 'download_path': self.download_path,
                                 'profile_id': config.profile_id(), 'trans_id': config.transaction_id()})
                playlists_to_add.append(playlist)
            if playlist == api_result[-1]:
                pbar.set_description_str("Updating database  ...")
                self.db.new_transaction()
                self.db.fast_monitor_playlist(playlists_to_add)
                self.db.commit()
                pbar.set_description_str("Monitoring complete!  ")

    def call_refresh(self):
        refresh = Refresh(self.time_machine)
        refresh.run()

    @performance.timeit
    def artists(self, names: list) -> None:
        """
        Return list of dictionaries containing each artist
        """
        if self.remove:
            return self.purge_artists(names=names)
        with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
            api_result = list(
                tqdm(ex.map(self.get_best_result, names), total=len(names), desc="Getting artist data...", ascii=" #",
                     bar_format='[{n_fmt}/{total_fmt}] {desc} [{bar}] {percentage:3.0f}%'))
        api_result = [item for elem in api_result for item in elem if len(item)]
        self.build_artist_query(api_result)
        self.call_refresh()

    # @performance.timeit
    def artist_ids(self, ids: list):
        ids = [int(x) for x in ids]
        if self.remove:
            return self.purge_artists(ids=ids)
        with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
            api_result = list(
                tqdm(ex.map(self.api.get_artist_by_id, ids), total=len(ids), desc="Getting artist info...", ascii=" #",
                     bar_format='[{n_fmt}/{total_fmt}] {desc} [{bar}] {percentage:3.0f}%'))
        self.build_artist_query(api_result)
        self.call_refresh()

    # @performance.timeit
    def importer(self, import_path: str):
        if Path(import_path).is_file():
            imported_file = dataprocessor.read_file_as_csv(import_path)
            artist_list = dataprocessor.process_input_file(imported_file)
            if isinstance(artist_list[0], int):
                self.artist_ids(artist_list)
            else:
                self.artists(artist_list)
        elif Path(import_path).is_dir():
            import_list = [x.relative_to(import_path) for x in sorted(Path(import_path).iterdir()) if x.is_dir()]
            if import_list:
                self.artists(import_list)
        else:
            logger.error(f"File or directory not found: {import_path}")
            return

    # @performance.timeit
    def playlists(self, playlists: list):
        if self.remove:
            return self.purge_playlists(ids=playlists)
        ids = [int(x) for x in playlists]
        with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
            api_result = list(
                tqdm(ex.map(self.api.get_playlist, ids), total=len(ids), desc="Getting playlist info...", ascii=" #",
                     bar_format='[{n_fmt}/{total_fmt}] {desc} [{bar}] {percentage:3.0f}%'))
        self.build_playlist_query(api_result)
        self.call_refresh()

    # @performance.timeit
    def purge_artists(self, names: list = None, ids: list = None):
        if names:
            for n in names:
                monitored = self.db.get_monitored_artist_by_name(n)
                if monitored:
                    self.db.remove_monitored_artist(monitored['artist_id'])
                    logger.info(f"No longer monitoring {monitored['artist_name']}")
                else:
                    logger.info(f"{n} is not being monitored yet")
        if ids:
            for i in ids:
                monitored = self.db.get_monitored_artist_by_id(i)
                if monitored:
                    self.db.remove_monitored_artist(monitored['artist_id'])
                    logger.info(f"No longer monitoring {monitored['artist_name']}")
                else:
                    logger.info(f"{i} is not being monitored yet")

    def purge_playlists(self, titles: list = None, ids: list = None):
        if ids:
            for i in ids:
                monitored = self.db.get_monitored_playlist_by_id(i)
                if monitored:
                    self.db.remove_monitored_playlists(monitored['id'])
                    logger.info(f"No longer monitoring {monitored['title']}")
                else:
                    logger.info(f"{i} is not being monitored yet")
