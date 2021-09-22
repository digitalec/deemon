from pathlib import Path
import deemix.errors
import plexapi.exceptions
from datetime import datetime
from plexapi.server import PlexServer
from deemon.core import dmi
from deemon.utils import dataprocessor, validate, startup
from deemon.core.config import Config as config
from deemon import utils
import logging
import deezer
import sys
import os

logger = logging.getLogger(__name__)


class QueueItem:
    # TODO - Accept new playlist tracks for output/alerts
    def __init__(self, artist=None, album=None, track=None, playlist=None,
                 bitrate: str = None, download_path: str = None):
        self.artist_name = None
        self.album_id = None
        self.album_title = None
        self.track_id = None
        self.track_title = None
        self.url = None
        self.playlist_title = None
        self.bitrate = bitrate or config.bitrate()
        self.download_path = download_path or config.download_path()
        self.verbose = os.environ.get('VERBOSE')

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
            self.url = album["link"]

        if track:
            self.artist_name = track["artist"]
            self.track_id = track["id"]
            self.track_title = track["title"]
            self.url = track["link"]

        if playlist:
            self.url = playlist["url"]
            self.playlist_title = playlist["title"]

        self.print_queue_to_log()

    def print_queue_to_log(self):
        if self.verbose == "true":
            logger.debug("Item created in queue: " + str(self.__dict__))


class Download:

    def __init__(self):
        super().__init__()
        self.dz = deezer.Deezer()
        self.di = dmi.DeemixInterface()
        self.queue_list = []
        self.bitrate = None
        self.from_release_date = None
        self.verbose = os.environ.get("VERBOSE")
        self.duplicate_id_count = 0

        if not self.di.login():
            sys.exit(1)

    def get_deemix_bitrate(self, bitrate: str):
        for bitrate_id, bitrate_name in config.allowed_values('bitrate').items():
            if bitrate_name.lower() == bitrate.lower():
                return bitrate_id

    def get_plex_server(self):
        if (config.plex_baseurl() != "") and (config.plex_token() != ""):
            try:
                print("Plex settings found, trying to connect (10s)... ", end="")
                plex_server = PlexServer(config.plex_baseurl(), config.plex_token(), timeout=10)
                print(" OK")
                return plex_server
            except Exception:
                print(" FAILED")
                logger.error("Error: Unable to reach Plex server, please refresh manually.")
                return False

    def refresh_plex(self, plexobj):
        try:
            plexobj.library.section(config.plex_library()).update()
            logger.debug("Plex library refreshed successfully")
        except plexapi.exceptions.BadRequest as e:
            logger.error("Error occurred while refreshing your library. See logs for additional info.")
            logger.debug(f"Error during Plex refresh: {e}")
        except plexapi.exceptions.NotFound as e:
            logger.error("Error: Plex library not found. See logs for additional info.")
            logger.debug(f"Error during Plex refresh: {e}")

    def download_queue(self):
        if self.queue_list:
            plex = self.get_plex_server()
            print("----------------------------")
            logger.info("Sending " + str(len(self.queue_list)) + " release(s) to deemix for download:")

            current = 1
            failed_downloads = []
            total = len(self.queue_list)

            with open(startup.get_appdata_dir() / "queue.csv", "w") as f:
                f.writelines(','.join([str(x) for x in vars(self.queue_list[0]).keys()]) + "\n")
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

            for q in self.queue_list:
                dx_bitrate = self.get_deemix_bitrate(q.bitrate)
                logger.debug(f"deemix bitrate set to {str(dx_bitrate)} ({q.bitrate.upper()})")
                if self.verbose == "true":
                    logger.debug(f"Processing queue item {vars(q)}")
                try:
                    if q.artist_name:
                        if q.album_title:
                            logger.info(f"[{current}/{total}] {q.artist_name} - {q.album_title}... ")
                            self.di.download_url([q.url], dx_bitrate, config.download_path())
                        else:
                            logger.info(f"[{current}/{total}] {q.artist_name} - {q.track_title}... ")
                            self.di.download_url([q.url], dx_bitrate, config.download_path())
                    else:
                        logger.info(f"+ {q.playlist_title} (playlist)...")
                        self.di.download_url([q.url], dx_bitrate, q.download_path, override_deemix=False)
                except deemix.errors.GenerationError:
                    failed_downloads.append((q, "No tracks listed or unavailable in your country"))
                current += 1
            print("")
            if len(failed_downloads):
                logger.info(f"Downloads completed with {len(failed_downloads)} error(s):")
                with open(startup.get_appdata_dir() / "failed.csv", "w") as f:
                    f.writelines(','.join([str(x) for x in vars(self.queue_list[0]).keys()]) + "\n")
                    for failed in failed_downloads:
                        raw_values = [str(x) for x in vars(failed[0]).values()]
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
                logger.info("Downloads complete!")
            if plex and (config.plex_library() != ""):
                self.refresh_plex(plex)

    def download(self, artist, artist_id, album_id, url, input_file, auto=True, from_date: str = None):

        def filter_artist_by_record_type(artist):
            album_api = self.dz.api.get_artist_albums(artist['id'])['data']
            filtered_albums = []
            for album in album_api:
                if (album['record_type'] == config.record_type()) or config.record_type() == "all":
                    album_date = datetime.strptime(album['release_date'], "%Y-%m-%d")
                    if self.from_release_date and album_date >= self.from_release_date:
                        filtered_albums.append(album)
            return filtered_albums

        def get_api_result(artist=None, artist_id=None, album_id=None):
            if artist:
                try:
                    return self.dz.api.search_artist(artist, limit=1)["data"][0]  # TODO handle incorrect artist
                except (deezer.api.DataException, IndexError):
                    logger.error(f"Artist {artist} not found.")
            if artist_id:
                try:
                    return self.dz.api.get_artist(artist_id)
                except (deezer.api.DataException, IndexError):
                    logger.error(f"Artist ID {artist_id} not found.")
            if album_id:
                try:
                    return self.dz.api.get_album(album_id)
                except (deezer.api.DataException, IndexError):
                    logger.error(f"Album ID {album_id} not found.")

        def queue_filtered_releases(api_object):
            filtered = filter_artist_by_record_type(api_object)
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
            logger.debug("Processing album by name")
            album_id_result = get_api_result(album_id=i)
            if not album_id_result:
                return
            logger.debug(f"Requested Album: {i}, "
                         f"Found: {album_id_result['artist']['name']} - {album_id_result['title']}")
            if album_id_result and not queue_item_exists(album_id_result['id']):
                self.queue_list.append(QueueItem(album=album_id_result))

        def process_playlist_by_id(id):
            playlist_api = self.dz.api.get_playlist(id)
            self.queue_list.append(QueueItem(playlist=playlist_api))

        def extract_id_from_url(url):
            id_group = ['artist', 'album', 'playlist']
            for group in id_group:
                id_type = group
                try:
                    id = int(url.split(f'/{group}/')[1])
                    logger.debug(f"Extracted group={id_type}, id={id}")
                    return id_type, id
                except (IndexError, ValueError):
                    continue
            return False, False

        logger.info("Queueing releases, this might take awhile...")

        if from_date:
            logger.debug(f"Getting releases that were released on or after {from_date}")
            if validate.validate_date(from_date):
                self.from_release_date = datetime.strptime(from_date, "%Y-%m-%d")
            else:
                return logger.error(f"The date you entered is invalid: {from_date}")

        if artist:
            [process_artist_by_name(a) for a in artist]

        if artist_id:
            [process_artist_by_id(i) for i in artist_id]

        if album_id:
            [process_album_by_id(i) for i in album_id]

        if input_file:
            logger.info(f"Reading from file {input_file}")
            if Path(input_file).exists():
                artist_list = utils.dataprocessor.read_file_as_csv(input_file)
                artist_int_list, artist_str_list = utils.dataprocessor.process_input_file(artist_list)
                if artist_str_list:
                    for artist in artist_str_list:
                        process_artist_by_name(artist)
                if artist_int_list:
                    for artist in artist_int_list:
                        process_artist_by_id(artist)

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

        if self.duplicate_id_count > 0:
            logger.info(f"Cleaned up {self.duplicate_id_count} duplicate release(s). See log for additional info.")

        if auto:
            self.download_queue()
