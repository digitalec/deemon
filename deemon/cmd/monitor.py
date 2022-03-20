import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

from deemon.cmd import search
from deemon.cmd.refresh import Refresh
from deemon.core.api import PlatformAPI
from deemon.core.db import Database
from deemon.utils import dataprocessor, ui
from deemon.core.config import Config
from deemon.utils import dataprocessor

logger = logging.getLogger(__name__)

config = Config().CONFIG


def monitor(remove=False):
    # TODO: Need to find a home for this later
    max_threads = 50
    api = PlatformAPI()
    monitor_queue = []
    monitor_label = get_monitor_label()

    if config['runtime']['file']:
        process_imports()

    if config['runtime']['url']:
        process_urls()

    futures_list = []
    with tqdm(desc=f"Looking up {monitor_label}, please wait...", total=len(config['runtime']['artist'])) as pbar:
        with ThreadPoolExecutor(max_workers=max_threads) as ex:
            if config['runtime']['artist']:
                logger.debug("Spawning threads for artist name API lookup")
                futures_list += [ex.submit(api.search_artist, i) for i in config['runtime']['artist']]
            elif config['runtime']['artist_id']:
                logger.debug("Spawning threads for artist ID API lookup")
                futures_list += [ex.submit(api.get_artist_by_id, i) for i in config['runtime']['artist_id']]
            elif config['runtime']['playlist']:
                monitor_label = "playlist(s)"
                logger.debug("Spawning threads for playlist ID API lookup")
                futures_list += [ex.submit(api.get_playlist, i) for i in config['runtime']['playlist']]

            result = []
            for future in as_completed(futures_list):
                if future.result():
                    result.append(future.result())
                pbar.update(1)

    for r in result:
        if isinstance(r, dict) and r.get('query'):
            selected_result = get_best_result(r)
            if selected_result:
                monitor_queue.append(selected_result)
        else:
            monitor_queue.append(r)

class Monitor:
    monitor_queue = sorted(monitor_queue, key=lambda i: i['name'])
    logger.info(f"Setting up {len(monitor_queue)} {monitor_label} for monitoring")
    logger.debug(monitor_queue)

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
        self.api = PlatformAPI()

    def set_config(self, bitrate: str, alerts: bool, record_type: str, download_path: Path):
        self.bitrate = bitrate
        self.alerts = alerts
        self.record_type = record_type
        self.download_path = download_path
        self.debugger("SetConfig", {'bitrate': bitrate, 'alerts': alerts, 'type': record_type, 'path': download_path})
def process_imports():
    logger.info("Processing artists from file/directory")
    import_path = config['runtime']['files']
    for im in import_path:
        if Path(im).is_file():
            imported_file = dataprocessor.read_file_as_csv(im)
            artist_list = dataprocessor.process_input_file(imported_file)
            logger.info(f"Discovered {len(artist_list)} artist(s) from file/directory")
            if isinstance(artist_list[0], int):
                [config['runtime']['artist_id'].append(x) for x in artist_list]
            else:
                [config['runtime']['artist'].append(x) for x in artist_list]
        elif Path(im).is_dir():
            import_list = [x.relative_to(im).name for x in sorted(Path(im).iterdir()) if x.is_dir()]
            if import_list:
                [config['runtime']['artist'].append(x) for x in import_list]
        else:
            logger.error(f"File or directory not found: {im}")
            return

    def set_options(self, remove, dl_all, search):
        self.remove = True if remove else False
        self.dl = True if dl_all else False
        self.is_search = True if search else False
        self.debugger("SetOptions", {'remove': remove, 'dl': dl_all, 'search': search})

    def debugger(self, message: str, payload=None):
        if config.debug_mode():
            if not payload:
                payload = ""
            logger.debug(f"DEBUG_MODE: {message} {str(payload)}")
def process_urls():
    logger.info("Processing URL(s)")
    for url in config['runtime']['url']:
        url_parts = url.split("/")
        url_type = url_parts[-2]

    def get_best_result(self, api_result) -> list:
        name = api_result['query']
        try:
            url_id = int(url_parts[-1])
        except ValueError:
            logger.error(f"Unsupported URL - Invalid ID: {url}")
            continue

        if self.is_search:
            logger.debug("Waiting for user input...")
            prompt = self.prompt_search(name, api_result['results'])
        if url_type not in ["artist", "playlist"]:
            logger.error(f"Unsupported URL - Unknown Type: {url}")
            continue
        else:
            logger.info(f"Found URL with type '{url_type}' and ID of '{url_id}'")
            if url_type == "artist":
                config['runtime']['artist_id'].append(url_id)
            elif url_type == "playlist":
                config['runtime']['playlist'].append(url_id)


def get_best_result(api_result):
    """ Filter results or prompt user for selection when
    monitoring artist by name

    Returns: dict
    """
    name = api_result['query']
    matches = [r for r in api_result['results'] if r['name'].lower() == name.lower()]
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        logger.debug(f"Multiple matches were found for artist \"{api_result['query']}\"")
        if config['app']['prompt_duplicates']:
            logger.debug("Prompting for duplicate artist selection...")
            prompt = prompt_search(name, matches)
            if prompt:
                logger.debug(f"User selected {prompt}")
                return [prompt]

        matches = [r for r in api_result['results'] if r['name'].lower() == name.lower()]
        self.debugger("Matches", matches)

        if len(matches) == 1:
            return [matches[0]]
        elif len(matches) > 1:
            logger.debug(f"Multiple matches were found for artist \"{api_result['query']}\"")
            if config.prompt_duplicates():
                logger.debug("Waiting for user input...")
                prompt = self.prompt_search(name, matches)
                if prompt:
                    logger.debug(f"User selected {prompt}")
                    return [prompt]
                else:
                    logger.info(f"No selection made, skipping {name}...")
                    return []
            else:
                self.duplicates += 1
                return [matches[0]]
        elif not len(matches):
            logger.debug(f"   [!] No matches were found for artist \"{api_result['query']}\"")
            if config.prompt_no_matches() and len(api_result['results']):
                logger.debug("Waiting for user input...")
                prompt = self.prompt_search(name, api_result['results'])
                if prompt:
                    logger.debug(f"User selected {prompt}")
                    return [prompt]
                else:
                    logger.info(f"No selection made, skipping {name}...")
                    return []
            else:
                logger.info(f"   [!] Artist {name} not found")
                return []

    def prompt_search(self, value, api_result):
        menu = search.Search()
        ask_user = menu.artist_menu(value, api_result, True)
        if ask_user:
            return {'id': ask_user['id'], 'name': ask_user['name']}
        return logger.debug("No artist selected, skipping...")

    # @performance.timeit
    def build_artist_query(self, api_result: list):
        existing = self.db.get_all_monitored_artist_ids()
        artists_to_add = []
        pbar = tqdm(api_result, total=len(api_result), desc="Setting up artists for monitoring...", ascii=" #",
                    bar_format=ui.TQDM_FORMAT)
        for artist in pbar:
            if artist['id'] in existing:
                logger.info(f"   - Already monitoring {artist['name']}, skipping...")
                return prompt
            else:
                artist.update({'bitrate': self.bitrate, 'alerts': self.alerts, 'record_type': self.record_type,
                               'download_path': self.download_path, 'profile_id': config.profile_id(),
                               'trans_id': config.transaction_id()})
                artists_to_add.append(artist)
        if len(artists_to_add):
            logger.debug("New artists have been monitored. Saving changes to the database...")
            self.db.new_transaction()
            self.db.fast_monitor(artists_to_add)
            self.db.commit()
            return True

    def build_playlist_query(self, api_result: list):
        existing = self.db.get_all_monitored_playlist_ids() or []
        playlists_to_add = []
        pbar = tqdm(api_result, total=len(api_result), desc="Setting up playlists for monitoring...", ascii=" #",
                    bar_format=ui.TQDM_FORMAT)
        for i, playlist in enumerate(pbar):
            if not playlist:
                continue
            if playlist['id'] in existing:
                logger.info(f"   Already monitoring {playlist['title']}, skipping...")
            else:
                playlist.update({'bitrate': self.bitrate, 'alerts': self.alerts, 'download_path': self.download_path,
                                 'profile_id': config.profile_id(), 'trans_id': config.transaction_id()})
                playlists_to_add.append(playlist)
        if len(playlists_to_add):
            logger.debug("New playlists have been monitored. Saving changes to the database...")
            self.db.new_transaction()
            self.db.fast_monitor_playlist(playlists_to_add)
            self.db.commit()
            return True

    def call_refresh(self):
        refresh = Refresh(self.time_machine, ignore_filters=self.dl)
        refresh.run()

    # @performance.timeit
    def artists(self, names: list) -> None:
        """
        Return list of dictionaries containing each artist
        """
        if self.remove:
            return self.purge_artists(names=names)
        self.debugger("SpawningThreads", self.api.max_threads)
        with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
            api_result = list(
                tqdm(ex.map(self.api.search_artist, names), total=len(names),
                     desc=f"Fetching artist data for {len(names):,} artist(s), please wait...",
                     ascii=" #", bar_format=ui.TQDM_FORMAT))

        select_artist = tqdm(api_result, total=len(api_result), desc="Examining results for best match...", ascii=" #",
                             bar_format=ui.TQDM_FORMAT)

        to_monitor = []
        for artist in select_artist:
            best_result = self.get_best_result(artist)
            if best_result:
                to_monitor.append(best_result)

        to_process = [item for elem in to_monitor for item in elem if len(item)]
        if self.build_artist_query(to_process):
            self.call_refresh()
                logger.info(f"No selection made, skipping {name}...")
                return
        else:
            print("")
            logger.info("No new artists have been added, skipping refresh.")

    # @performance.timeit
    def artist_ids(self, ids: list):
        ids = [int(x) for x in ids]
        if self.remove:
            return self.purge_artists(ids=ids)
        self.debugger("SpawningThreads", self.api.max_threads)
        with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
            api_result = list(
                tqdm(ex.map(self.api.get_artist_by_id, ids), total=len(ids),
                     desc=f"Fetching artist data for {len(ids):,} artist(s), please wait...",
                     ascii=" #", bar_format=ui.TQDM_FORMAT))

        if self.build_artist_query(api_result):
            self.call_refresh()
        else:
            print("")
            logger.info("No new artists have been added, skipping refresh.")

    # @performance.timeit
    def importer(self, import_path: str):
        if Path(import_path).is_file():
            imported_file = dataprocessor.read_file_as_csv(import_path)
            artist_list = dataprocessor.process_input_file(imported_file)
            if isinstance(artist_list[0], int):
                self.artist_ids(artist_list)
            return matches[0]
    elif not len(matches):
        logger.debug(f"   [!] No matches were found for artist \"{api_result['query']}\"")
        if config.prompt_no_matches() and len(api_result['results']):
            logger.debug("Waiting for user input...")
            prompt = prompt_search(name, api_result['results'])
            if prompt:
                logger.debug(f"User selected {prompt}")
                return prompt
            else:
                self.artists(artist_list)
        elif Path(import_path).is_dir():
            import_list = [x.relative_to(import_path).name for x in sorted(Path(import_path).iterdir()) if x.is_dir()]
            if import_list:
                self.artists(import_list)
                logger.info(f"No selection made, skipping {name}...")
                return
        else:
            logger.error(f"File or directory not found: {import_path}")
            logger.info(f"   [!] Artist {name} not found")
            return

    # @performance.timeit
    def playlists(self, playlists: list):
        if self.remove:
            return self.purge_playlists(ids=playlists)
        ids = [int(x) for x in playlists]
        self.debugger("SpawningThreads", self.api.max_threads)
        with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
            api_result = list(
                tqdm(ex.map(self.api.get_playlist, ids), total=len(ids),
                     desc=f"Fetching playlist data for {len(ids):,} playlist(s), please wait...",
                     ascii=" #", bar_format=ui.TQDM_FORMAT))

        if self.build_playlist_query(api_result):
            self.call_refresh()
        else:
            print("")
            logger.info("No new playlists have been added, skipping refresh.")
def prompt_search(value, api_result):
    menu = search.Search()
    ask_user = menu.artist_menu(value, api_result, True)
    if ask_user:
        return {'id': ask_user['id'], 'name': ask_user['name']}
    return logger.debug("No artist selected, skipping...")

    # @performance.timeit
    def purge_artists(self, names: list = None, ids: list = None):
        if names:
            for n in names:
                monitored = self.db.get_monitored_artist_by_name(n)
                if monitored:
                    self.db.remove_monitored_artist(monitored['artist_id'])
                    logger.info(f"\nNo longer monitoring {monitored['artist_name']}")
                else:
                    logger.info(f"{n} is not being monitored yet")
        if ids:
            for i in ids:
                monitored = self.db.get_monitored_artist_by_id(i)
                if monitored:
                    self.db.remove_monitored_artist(monitored['artist_id'])
                    logger.info(f"\nNo longer monitoring {monitored['artist_name']}")
                else:
                    logger.info(f"{i} is not being monitored yet")

    def purge_playlists(self, titles: list = None, ids: list = None):
        if ids:
            for i in ids:
                monitored = self.db.get_monitored_playlist_by_id(i)
                if monitored:
                    self.db.remove_monitored_playlists(monitored['id'])
                    logger.info(f"\nNo longer monitoring {monitored['title']}")
                else:
                    logger.info(f"{i} is not being monitored yet")
def get_monitor_label():
    if config['runtime']['artist']:
        if len(config['runtime']['artist']) > 1:
            return "artists"
        else:
            return "artist"
    elif config['runtime']['artist_id']:
        if len(config['runtime']['artist_id']) > 1:
            return "artist IDs"
        else:
            return "artist ID"
    elif config['runtime']['playlist']:
        if len(config['runtime']['playlist']) > 1:
            return "playlists"
        else:
            return "playlist"
