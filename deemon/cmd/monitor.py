import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

from deemon import config, db
from deemon.core.api import PlatformAPI
from deemon.core.logger import logger
from deemon.core.config import MAX_API_THREADS
from deemon.cmd import search, refresh
from deemon.utils import dataprocessor, recordtypes

logger = logging.getLogger(__name__)

config = Config().CONFIG


def monitor():
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

    if len(monitor_queue):
        monitor_queue = sorted(monitor_queue, key=lambda i: i['name'])
        logger.info(f"Setting up {len(monitor_queue)} {monitor_label} for monitoring")
        setup_monitoring(monitor_queue)
    else:
        return logger.info("No artists to setup for monitoring.")


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


def process_urls():
    logger.info("Processing URL(s)")
    for url in config['runtime']['url']:
        url_parts = url.split("/")
        url_type = url_parts[-2]

        try:
            url_id = int(url_parts[-1])
        except ValueError:
            logger.error(f"Unsupported URL - Invalid ID: {url}")
            continue

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
                return prompt
            else:
                logger.info(f"No selection made, skipping {name}...")
                return
        else:
            return matches[0]
    elif not len(matches):
        logger.debug(f"   [!] No matches were found for artist \"{api_result['query']}\"")
        if config['app']['prompt_no_matches'] and len(api_result['results']):
            logger.debug("Waiting for user input...")
            prompt = prompt_search(name, api_result['results'])
            if prompt:
                logger.debug(f"User selected {prompt}")
                return prompt
            else:
                logger.info(f"No selection made, skipping {name}...")
                return
        else:
            logger.info(f"   [!] Artist {name} not found")
            return


def prompt_search(value, api_result):
    menu = search.Search()
    ask_user = menu.artist_menu(value, api_result, True)
    if ask_user:
        return {'id': ask_user['id'], 'name': ask_user['name']}
    return logger.debug("No artist selected, skipping...")


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


def setup_monitoring(queue):
    db = Database()
    artist_queue = []
    playlist_queue = []

    monitored_artists = db.get_all_monitored_artist_ids()
    monitored_playlists = db.get_all_monitored_playlist_ids()

    extras = {
        'bitrate': config['runtime']['bitrate'],
        'alerts': config['runtime']['alerts'],
        'record_type': config['runtime']['record_type'],
        'download_path': config['runtime']['download_path'],
        'profile_id': config['runtime']['profile_id'],
        'transaction_id': config['runtime']['transaction_id'],
    }

    [x.update(extras) for x in queue]

    for item in queue:
        if item.get('link'):
            if item['id'] in monitored_playlists:
                logger.info(f"   - Already monitoring playlist {item['name']} ({item['id']})")
            else:
                playlist_queue.append(item)
        else:
            if item['id'] in monitored_artists:
                logger.info(f"   - Already monitoring artist {item['name']} ({item['id']})")
            else:
                artist_queue.append(item)

    if len(artist_queue):
        db.new_transaction()
        db.fast_monitor(artist_queue)
    elif len(playlist_queue):
        db.new_transaction()
        db.fast_monitor_playlist(playlist_queue)
    db.commit()

    if artist_queue or playlist_queue:
        refresh.start()


def remove(names: list, by_id=False, playlist=False):
    db = Database()

    if by_id:
        try:
            by_id = [int(x) for x in names]
        except ValueError as e:
            return logger.error(f"Invalid ID detected: {e}")

        for item_id in by_id:
            if playlist:
                monitored = db.get_monitored_playlist_by_id(item_id)
                if monitored:
                    db.remove_monitored_playlists(monitored['id'])
                    logger.info(f"No longer monitoring {monitored['title']}")
                else:
                    logger.info(f"Playlist ID {item_id} not found")
            else:
                monitored = db.get_monitored_artist_by_id(item_id)
                if monitored:
                    db.remove_monitored_artist(monitored['id'])
                    logger.info(f"No longer monitoring {monitored['name']}")
                else:
                    logger.info(f"Artist ID {item_id} not found")
    else:
        for name in names:
            if playlist:
                monitored = db.get_monitored_playlist_by_name(name)
                if monitored:
                    db.remove_monitored_playlists(monitored['id'])
                    logger.info(f"No longer monitoring {monitored['title']}")
                else:
                    logger.info(f"Playlist {name} not found")
            else:
                monitored = db.get_monitored_artist_by_name(name)
                if monitored:
                    db.remove_monitored_artist(monitored['id'])
                    logger.info(f"No longer monitoring {monitored['name']}")
                else:
                    logger.info(f"Artist {name} not found")
