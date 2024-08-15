import logging
import os
import sys

import requests
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tqdm import tqdm

import deemix.errors
import deezer
from deezer import errors
import plexapi.exceptions
from plexapi.server import PlexServer

from deemon import utils
from deemon.core import dmi, db, api, common
from deemon.core.config import Config as config
from deemon.utils import ui, dataprocessor, startup, dates

logger = logging.getLogger(__name__)


class QueueItem:
    # TODO - Accept new playlist tracks for output/alerts
    def __init__(self, artist=None, album=None, track=None, playlist=None,
                 bitrate: str = None, download_path: str = None,
                 release_full: dict = None):
        self.artist_name = None
        self.album_id = None
        self.album_title = None
        self.track_id = None
        self.track_title = None
        self.url = None
        self.playlist_title = None
        self.bitrate = bitrate or config.bitrate()
        self.download_path = download_path or config.download_path()
        self.release_type = None
        
        if release_full:
            self.artist_name = release_full['artist_name']
            self.album_id = release_full['id']
            self.album_title = release_full['title']
            self.url = f"https://www.deezer.com/album/{self.album_id}"
            self.release_type = release_full['record_type']
            self.bitrate = release_full['bitrate']
            self.download_path = release_full['download_path']

        if artist:
            try:
                self.artist_name = artist["artist_name"]
            except KeyError:
                self.artist_name = artist["name"]
            if not album and not track:
                self.url = artist["link"]

        if album:
            if not artist:
                self.artist_name = album["artist"]["name"]
            self.album_id = album["id"]
            self.album_title = album["title"]
            try:
                self.url = album["link"]
            except KeyError:
                self.url = f"https://www.deezer.com/album/{album['id']}"

        if track:
            self.artist_name = track["artist"]["name"]
            self.track_id = track["id"]
            self.track_title = track["title"]
            self.url = f"https://deezer.com/track/{self.track_id}"

        if playlist:
            try:
                self.url = playlist["link"]
            except KeyError:
                logger.debug("DEPRECATED dict key: playlist['url'] should not be used in favor of playlist['link']")
                self.url = playlist.get("url", None)
            self.playlist_title = playlist["title"]


def get_deemix_bitrate(bitrate: str):
    for bitrate_id, bitrate_name in config.allowed_values('bitrate').items():
        if bitrate_name.lower() == bitrate.lower():
            logger.debug(f"Setting deemix bitrate to {str(bitrate_id)}")
            return bitrate_id


def get_plex_server():
    if (config.plex_baseurl() != "") and (config.plex_token() != ""):
        session = None
        if not config.plex_ssl_verify():
            requests.packages.urllib3.disable_warnings()
            session = requests.Session()
            session.verify = False
        try:
            print("Plex settings found, trying to connect (10s)... ", end="")
            plex_server = PlexServer(config.plex_baseurl(), config.plex_token(), timeout=10, session=session)
            print(" OK")
            return plex_server
        except Exception as e:
            print(" FAILED")
            logger.error("Error: Unable to reach Plex server, please refresh manually.")
            logger.debug(e)
            return False


def refresh_plex(plexobj):
    try:
        plexobj.library.section(config.plex_library()).update()
        logger.debug("Plex library refreshed successfully")
    except plexapi.exceptions.BadRequest as e:
        logger.error("Error occurred while refreshing your library. See logs for additional info.")
        logger.debug(f"Error during Plex refresh: {e}")
    except plexapi.exceptions.NotFound as e:
        logger.error("Error: Plex library not found. See logs for additional info.")
        logger.debug(f"Error during Plex refresh: {e}")


class Download:

    def __init__(self, active_api=None):
        super().__init__()
        self.api = active_api or api.PlatformAPI()
        self.dz = deezer.Deezer()
        self.di = dmi.DeemixInterface()
        self.queue_list = []
        self.db = db.Database()
        self.bitrate = None
        self.release_from = None
        self.release_to = None
        self.verbose = os.environ.get("VERBOSE")
        self.duplicate_id_count = 0

    def set_dates(self, from_date: str = None, to_date: str = None) -> None:
        """Set to/from dates to get while downloading"""
        if from_date:
            try:
                self.release_from = dates.str_to_datetime_obj(from_date)
            except ValueError as e:
                raise ValueError(f"Invalid date provided - {from_date}: {e}")
        if to_date:
            try:
                self.release_to = dates.str_to_datetime_obj(to_date)
            except ValueError as e:
                raise ValueError(f"Invalid date provided - {to_date}: {e}")

    # @performance.timeit
    def download_queue(self, queue_list: list = None):
        if queue_list:
            self.queue_list = queue_list

        if not self.di.login():
            logger.error("Failed to login, aborting download...")
            return False

        if self.queue_list:
            plex = get_plex_server()
            print("")
            logger.info(":: Sending " + str(len(self.queue_list)) + " release(s) to deemix for download:")

            with open(startup.get_appdata_dir() / "queue.csv", "w", encoding="utf-8") as f:
                f.writelines(','.join([str(x) for x in vars(self.queue_list[0]).keys()]) + "\n")
                logger.debug(f"Writing queue to CSV file - {len(self.queue_list)} items in queue")
                for q in self.queue_list:
                    raw_values = [str(x) for x in vars(q).values()]
                    # TODO move this to shared function
                    for i, v in enumerate(raw_values):
                        if '"' in v:
                            raw_values[i] = v.replace('"', "'")
                        if ',' in v:
                            raw_values[i] = f'"{v}"'
                    f.writelines(','.join(raw_values) + "\n")
            logger.debug(f"Queue exported to {startup.get_appdata_dir()}/queue.csv")

            failed_count = []
            download_progress = tqdm(
                self.queue_list,
                total=len(self.queue_list),
                desc="Downloading releases...",
                ascii=" #",
                bar_format=ui.TQDM_FORMAT
            )
            for index, item in enumerate(download_progress):
                i = str(index + 1)
                t = str(len(download_progress))
                download_progress.set_description_str(f"Downloading release {i} of {t}...")
                dx_bitrate = get_deemix_bitrate(item.bitrate)
                if self.verbose == "true":
                    logger.debug(f"Processing queue item {vars(item)}")
                try:
                    if item.download_path:
                        download_path = item.download_path
                    else:
                        download_path = None

                    if item.artist_name:
                        if item.album_title:
                            logger.info(f"   > {item.artist_name} - {item.album_title}... ")
                            self.di.download_url([item.url], dx_bitrate, download_path)
                        else:
                            logger.info(f"   > {item.artist_name} - {item.track_title}... ")
                            self.di.download_url([item.url], dx_bitrate, download_path)
                    else:
                        logger.info(f"   > {item.playlist_title} (playlist)...")
                        self.di.download_url([item.url], dx_bitrate, download_path, override_deemix=True)
                except (deemix.errors.GenerationError, errors.WrongGeolocation) as e:
                    logger.debug(e)
                    failed_count.append([(item, "No tracks listed or unavailable in your country")])
                except Exception as e:
                    if item.artist_name and item.album_title:
                        logger.info(f"The following error occured while downloading {item.artist_name} - {item.album_title}: {e}")
                    elif item.artist_name and item.track_title:
                        logger.info(f"The following error occured while downloading {item.artist_name} - {item.track_title}: {e}")
                    else:
                        logger.info(f"The following error occured while downloading {item.playlist_title}: {e}")
                    pass


            failed_count = [x for x in failed_count if x]

            print("")
            if len(failed_count):
                logger.info(f"   [!] Downloads completed with {len(failed_count)} error(s):")
                with open(startup.get_appdata_dir() / "failed.csv", "w", encoding="utf-8") as f:
                    f.writelines(','.join([str(x) for x in vars(self.queue_list[0]).keys()]) + "\n")
                    for failed in failed_count:
                        try:
                            raw_values = [str(x) for x in vars(failed[0]).values()]
                        except TypeError as e:
                            print(f"Error reading from failed.csv. Entry that failed was either invalid or empty: {failed}")
                            logger.error(e)
                        else:
                            # TODO move this to shared function
                            for i, v in enumerate(raw_values):
                                if '"' in v:
                                    raw_values[i] = v.replace('"', "'")
                                if ',' in v:
                                    raw_values[i] = f'"{v}"'
                            f.writelines(','.join(raw_values) + "\n")
                            print(f"+ {failed[0].artist_name} - {failed[0].album_title} --- Reason: {failed[1]}")
                print("")
                logger.info(f":: Failed downloads exported to: {startup.get_appdata_dir()}/failed.csv")
            else:
                logger.info("   Downloads complete!")
            if plex and (config.plex_library() != ""):
                refresh_plex(plex)
        return True

    def download(self, artist, artist_id, album_id, url,
                 artist_file, track_file, album_file, track_id, auto=True, monitored=False):

        def filter_artist_by_record_type(artist):
            album_api = self.api.get_artist_albums(query={'artist_name': '', 'artist_id': artist['id']})
            filtered_albums = []
            for album in album_api['releases']:
                if (album['record_type'] == config.record_type()) or config.record_type() == "all":
                    album_date = dates.str_to_datetime_obj(album['release_date'])
                    if self.release_from and self.release_to:
                        if album_date > self.release_from and album_date < self.release_to:
                            filtered_albums.append(album)
                    elif self.release_from:
                        if album_date > self.release_from:
                            filtered_albums.append(album)
                    elif self.release_to:
                        if album_date < self.release_to:
                            filtered_albums.append(album)
                    else:
                        filtered_albums.append(album)
            return filtered_albums

        def get_api_result(artist=None, artist_id=None, album_id=None, track_id=None):
            if artist:
                try:
                    return self.api.search_artist(artist, limit=1)['results'][0]
                except (deezer.api.DataException, IndexError):
                    logger.error(f"Artist {artist} not found.")
            if artist_id:
                try:
                    return self.api.get_artist_by_id(artist_id)
                except (deezer.api.DataException, IndexError):
                    logger.error(f"Artist ID {artist_id} not found.")
            if album_id:
                try:
                    return self.api.get_album(album_id)
                except (deezer.api.DataException, IndexError):
                    logger.error(f"Album ID {album_id} not found.")
            if track_id:
                try:
                    return self.api.get_track(track_id)
                except (deezer.api.DataException, IndexError):
                    logger.error(f"Track ID {track_id} not found.")

        def queue_filtered_releases(api_object):
            filtered = filter_artist_by_record_type(api_object)
            filtered = common.exclude_filtered_versions(filtered)

            for album in filtered:
                if not queue_item_exists(album['id']):
                    self.queue_list.append(QueueItem(artist=api_object, album=album))

        def queue_item_exists(i):
            for q in self.queue_list:
                if q.album_id == i:
                    logger.debug(f"Album ID {i} is already in queue")
                    self.duplicate_id_count += 1
                    return True
            return False

        def process_artist_by_name(name):
            artist_result = get_api_result(artist=name)
            if not artist_result:
                return
            logger.debug(f"Requested Artist: '{name}', Found: '{artist_result['name']}'")
            if artist_result:
                queue_filtered_releases(artist_result)

        def process_artist_by_id(i):
            artist_id_result = get_api_result(artist_id=i)
            if not artist_id_result:
                return
            logger.debug(f"Requested Artist ID: {i}, Found: {artist_id_result['name']}")
            if artist_id_result:
                queue_filtered_releases(artist_id_result)

        def process_album_by_id(i):
            logger.debug("Processing album by ID")
            album_id_result = get_api_result(album_id=i)
            if not album_id_result:
                logger.debug(f"Album ID {i} was not found")
                return
            logger.debug(f"Requested album: {i}, "
                         f"Found: {album_id_result['artist']['name']} - {album_id_result['title']}")
            if album_id_result and not queue_item_exists(album_id_result['id']):
                self.queue_list.append(QueueItem(album=album_id_result))

        def process_track_by_id(id):
            logger.debug("Processing track by ID")
            track_id_result = get_api_result(track_id=id)
            if not track_id_result:
                return
            logger.debug(f"Requested track: {id}, "
                         f"Found: {track_id_result['artist']['name']} - {track_id_result['title']}")
            if track_id_result and not queue_item_exists(id):
                self.queue_list.append(QueueItem(track=track_id_result))

        def process_track_file(id):
            if not queue_item_exists(id):
                track_data = {
                    "artist": {
                        "name": "TRACK ID"
                    },
                    "id": id,
                    "title": id
                }
                self.queue_list.append(QueueItem(track=track_data))

        def process_playlist_by_id(id):
            playlist_api = self.api.get_playlist(id)
            self.queue_list.append(QueueItem(playlist=playlist_api))

        def extract_id_from_url(url):
            id_group = ['artist', 'album', 'track', 'playlist']
            for group in id_group:
                id_type = group
                try:
                    # Strip ID from URL
                    id_from_url = url.split(f'/{group}/')[1]

                    # Support for share links: http://deezer.com/us/track/12345?utm_campaign...
                    id_from_url_extra = id_from_url.split('?')[0]

                    id = int(id_from_url_extra)
                    logger.debug(f"Extracted group={id_type}, id={id}")
                    return id_type, id
                except (IndexError, ValueError) as e:
                    continue
            return False, False

        logger.info("[!] Queueing releases, this might take awhile...")

        if self.release_from or self.release_to:
            if self.release_from and self.release_to:
                logger.info(":: Getting releases that were released between "
                            f"{dates.ui_date(self.release_from)} and "
                            f"{dates.ui_date(self.release_to)}")
            elif self.release_from:
                logger.info(":: Getting releases that were released after "
                            f"{dates.ui_date(self.release_from)}")
            elif self.release_to:
                logger.info(":: Getting releases that were released before "
                            f"{dates.ui_date(self.release_to)}")

        if monitored:
            artist_id = self.db.get_all_monitored_artist_ids()

        if artist:
            [process_artist_by_name(a) for a in artist]

        if artist_id:
            [process_artist_by_id(i) for i in artist_id]

        if album_id:
            [process_album_by_id(i) for i in album_id]

        if track_id:
            [process_track_by_id(i) for i in track_id]

        if album_file:
            logger.info(f":: Reading from file {album_file}")
            if Path(album_file).exists():
                album_list = utils.dataprocessor.read_file_as_csv(album_file, split_new_line=False)
                album_list = utils.dataprocessor.process_input_file(album_list)
                if album_list:
                    if isinstance(album_list[0], int):
                        with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
                            _api_results = list(tqdm(ex.map(process_album_by_id, album_list),
                                                     total=len(album_list),
                                                     desc=f"Fetching album data for {len(album_list)} "
                                                          f"album(s), please wait...", ascii=" #",
                                                     bar_format=ui.TQDM_FORMAT))
                    else:
                        logger.debug(f"Invalid album ID: \"{album_list[0]}\"")
                        logger.error(f"Invalid album ID file detected.")
            else:
                logger.error(f"The file {album_file} could not be found")
                sys.exit()

        if artist_file:
            # TODO artist_file is in different format than album_file and track_file
            # TODO is one continuous CSV line better than separate lines?
            logger.info(f":: Reading from file {artist_file}")
            if Path(artist_file).exists():
                artist_list = utils.dataprocessor.read_file_as_csv(artist_file)
                if artist_list:
                    if isinstance(artist_list[0], int):
                        logger.debug(f"{artist_file} contains artist IDs")
                        with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
                            _api_results = list(tqdm(ex.map(process_artist_by_id, artist_list),
                                                     total=len(artist_list),
                                                     desc=f"Fetching artist release data for {len(artist_list)} "
                                                          f"artist(s), please wait...", ascii=" #",
                                                     bar_format=ui.TQDM_FORMAT))
                    elif isinstance(artist_list[0], str):
                        logger.debug(f"{artist_file} contains artist names")
                        with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
                            _api_results = list(tqdm(ex.map(process_artist_by_name, artist_list),
                                                     total=len(artist_list),
                                                     desc=f"Fetching artist release data for {len(artist_list)} "
                                                          f"artist(s), please wait...",
                                                     ascii=" #",
                                                     bar_format=ui.TQDM_FORMAT))
            else:
                logger.error(f"The file {artist_file} could not be found")
                sys.exit()

        if track_file:
            logger.info(f":: Reading from file {track_file}")
            if Path(track_file).exists():
                track_list = utils.dataprocessor.read_file_as_csv(track_file, split_new_line=False)
                try:
                    track_list = [int(x) for x in track_list]
                except TypeError:
                    logger.info("Track file must only contain track IDs")
                    return

                if track_list:
                    with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
                        _api_results = list(tqdm(ex.map(process_track_file, track_list),
                                                 total=len(track_list),
                                                 desc=f"Fetching track release data for {len(track_list)} "
                                                      f"track(s), please wait...", ascii=" #",
                                                 bar_format=ui.TQDM_FORMAT))
            else:
                logger.error(f"The file {track_file} could not be found")
                sys.exit()

        if url:
            logger.debug("Processing URLs")
            for u in url:
                egroup, eid = extract_id_from_url(u)
                if not egroup or not eid:
                    logger.error(f"Invalid URL -- {u}")
                    continue

                if egroup == "artist":
                    process_artist_by_id(eid)
                elif egroup == "album":
                    process_album_by_id(eid)
                elif egroup == "playlist":
                    process_playlist_by_id(eid)
                elif egroup == "track":
                    process_track_by_id(eid)

        if self.duplicate_id_count > 0:
            logger.info(f"Cleaned up {self.duplicate_id_count} duplicate release(s). See log for additional info.")

        if auto:
            if len(self.queue_list):
                self.download_queue()
            else:
                print("")
                logger.info("No releases found matching applied filters.")
