#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of deemon.
#
# Copyright (C) 2022 digitalec <digitalec.dev@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

from deemon import config, db
from deemon.core.api import PlatformAPI
from deemon.core.database import Artist
from deemon.core.logger import logger
from deemon.core.config import MAX_API_THREADS
from deemon.cmd import search, refresh
from deemon.utils import dataprocessor, recordtypes


class Monitor:

    def __init__(self, args):
        self.args = args
        self.api = PlatformAPI()
        self.artists = list()
        self.artist_ids = list()
        self.playlist_ids = list()

        self.monitor_queue = []

        if args.artist:
            self.artists = dataprocessor.csv_to_list(args.artist)
        if args.artist_id:
            self.artist_ids = dataprocessor.csv_to_list(args.artist_id)
        if args.file:
            self.process_imports(args.file)
        if args.url:
            self.process_urls(args.url)

    def process_imports(self, import_path: list):
        logger.info("Processing artists from file/directory")
        for im in import_path:
            if Path(im).is_file():
                imported_file = dataprocessor.read_file_as_csv(im)
                artist_list = dataprocessor.process_input_file(imported_file)
                logger.info(f"Discovered {len(artist_list)} artist(s) from file/directory")
                if isinstance(artist_list[0], int):
                    [self.artist_ids.append(x) for x in artist_list]
                else:
                    [self.artists.append(x) for x in artist_list]
            elif Path(im).is_dir():
                import_list = [x.relative_to(im).name for x in sorted(Path(im).iterdir()) if x.is_dir()]
                if import_list:
                    [self.artists.append(x) for x in import_list]
            else:
                logger.error(f"File or directory not found: {im}")
                return

    def process_urls(self, urls: list):
        logger.info("Processing URL(s)")
        for url in urls:
            url_parts = url.split("/")
            url_type = url_parts[-2]

            try:
                url_id = int(url_parts[-1])
            except ValueError:
                logger.error(f"Unsupported URL - Invalid ID: {url}")
                continue

            if url_type not in ["artist", "playlist"]:
                logger.error(f"Unsupported URL for monitoring - Unknown Type: {url}")
                continue
            else:
                logger.info(f"Found URL with type '{url_type}' and ID of '{url_id}'")
                if url_type == "artist":
                    self.artist_ids.append(url_id)
                elif url_type == "playlist":
                    self.playlist_ids.append(url_id)

    def get_monitor_label(self):
        if self.artists:
            if len(self.artists) > 1:
                return "artists"
            else:
                return "artist"
        elif self.artist_ids:
            if len(self.artist_ids) > 1:
                return "artist IDs"
            else:
                return "artist ID"
        elif self.playlist_ids:
            if len(self.playlist_ids) > 1:
                return "playlists"
            else:
                return "playlist"

    def add(self):
        db.init_transaction()
        monitor_label = self.get_monitor_label()
        futures_list = []
        with tqdm(desc=f"Looking up {monitor_label}, please wait...", total=len(self.artists)) as pbar:
            with ThreadPoolExecutor(max_workers=MAX_API_THREADS) as ex:
                if self.artists:
                    logger.debug("Spawning threads for artist name API lookup")
                    futures_list += [ex.submit(self.api.search_artist, i) for i in self.artists]
                elif self.artist_ids:
                    logger.debug("Spawning threads for artist ID API lookup")
                    futures_list += [ex.submit(self.api.get_artist_by_id, i) for i in self.artist_ids]
                elif self.playlist_ids:
                    monitor_label = "playlist(s)"
                    logger.debug("Spawning threads for playlist ID API lookup")
                    futures_list += [ex.submit(self.api.get_playlist, i) for i in self.playlist_ids]

                result = []
                for future in as_completed(futures_list):
                    if future.result():
                        result.append(future.result())
                    pbar.update(1)

        for r in result:
            if isinstance(r, dict) and r.get('query'):
                selected_result = self.get_best_result(r)
                if selected_result:
                    self.monitor_queue.append(selected_result)
            else:
                self.monitor_queue.append(r)

        if len(self.monitor_queue):
            self.monitor_queue = sorted(self.monitor_queue, key=lambda i: i['art_name'])
            logger.info(f"Setting up {len(self.monitor_queue):,} {monitor_label} for monitoring")
            self.setup_monitoring()
        else:
            return logger.info("No artists to setup for monitoring.")

    def get_best_result(self, api_result):
        """ Filter results or prompt user for selection when
        monitoring artist by name

        Returns: dict
        """
        name = api_result['query']
        matches = [r for r in api_result['results'] if r['art_name'].lower() == name.lower()]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            logger.debug(f"Multiple matches were found for artist \"{api_result['query']}\"")
            if config.prompt_duplicates:
                logger.debug("Prompting for duplicate artist selection...")
                prompt = self.prompt_search(name, matches)
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
            if config.prompt_no_matches and len(api_result['results']):
                logger.debug("Waiting for user input...")
                prompt = self.prompt_search(name, api_result['results'])
                if prompt:
                    logger.debug(f"User selected {prompt}")
                    return prompt
                else:
                    logger.info(f"No selection made, skipping {name}...")
                    return
            else:
                logger.info(f"   [!] Artist {name} not found")
                return

    def setup_monitoring(self):
        artist_queue = []
        update_artist_queue = []
        playlist_queue = []
        update_playlist_queue = []

        monitored_artists = [x.Artist.art_id for x in db.get_artists()]
        monitored_playlists = [x.Playlist.playlist_id for x in db.get_playlist_ids()]

        if self.args.record_types:
            rt = recordtypes.get_record_type_index(self.args.record_types)
        else:
            rt = None

        extras = {
            'bitrate': self.args.bitrate,
            'notify': self.args.notify,
            'rectype': rt,
            'dl_path': self.args.download_path,
        }

        [x.update(extras) for x in self.monitor_queue]

        for item in self.monitor_queue:
            if item.get('link'):
                if item['playlist_id'] in monitored_playlists:
                    # TODO update item['playlist_title'] once playlist code has been implemented
                    logger.info(f"Updating artist: {item['playlist_title']}")
                    update_playlist_queue.append(item)
                else:
                    playlist_queue.append(item)
            else:
                # TODO Condense this code if it cannot be merged
                if item['art_id'] in monitored_artists:
                    logger.info(f"Updating artist: {item['art_name']}")
                    update_artist_queue.append(
                        Artist(
                            art_id=item['art_id'],
                            art_name=item['art_name'],
                            bitrate=item['bitrate'],
                            rectype=item['rectype'],
                            notify=item['notify'],
                            dl_path=item['dl_path'],
                        )
                    )
                else:
                    artist_queue.append(
                        Artist(
                            art_id=item['art_id'],
                            art_name=item['art_name'],
                            bitrate=item['bitrate'],
                            rectype=item['rectype'],
                            notify=item['notify'],
                            dl_path=item['dl_path'],
                        )
                    )

        if len(artist_queue):
            db.fast_monitor(artist_queue)
        elif len(playlist_queue):
            db.fast_monitor_playlist(playlist_queue)

        if len(update_artist_queue):
            db.update_monitor(update_artist_queue)
        elif len(update_playlist_queue):
            db.update_monitor_playlist(update_playlist_queue)

        if artist_queue or playlist_queue:
            r = refresh.Refresh(download_all=self.args.download, time_machine=self.args.time_machine)
            r.start()

    @staticmethod
    def prompt_search(value, api_result):
        menu = search.Search()
        ask_user = menu.artist_menu(value, api_result, True)
        if ask_user:
            return {'id': ask_user['art_id'], 'name': ask_user['art_name']}
        return logger.debug("No artist selected, skipping...")


def remove(names: list, by_id=False, playlist=False):
    names = dataprocessor.csv_to_list(names)
    if by_id:
        try:
            by_id = [int(x) for x in names]
        except ValueError as e:
            return logger.error(f"Invalid ID detected: {e}")

        for item_id in by_id:
            if playlist:
                monitored = db.get_playlist_by_id(item_id)
                if monitored:
                    db.remove_playlist(monitored[0].playlist_id)
                    logger.info(f"No longer monitoring {monitored[0].title}")
                else:
                    logger.info(f"Playlist ID {item_id} not found")
            else:
                monitored = db.get_artist_by_id(item_id)
                if monitored:
                    db.remove_artist(monitored[0].art_id)
                    logger.info(f"No longer monitoring {monitored[0].art_name}")
                else:
                    logger.info(f"Artist ID {item_id} not found")
    else:
        for name in names:
            if playlist:
                monitored = db.get_playist_by_name(name)
                if monitored:
                    db.remove_playlist(monitored[0].playlist_id)
                    logger.info(f"No longer monitoring {monitored[0].title}")
                else:
                    logger.info(f"Playlist {name} not found")
            else:
                monitored = db.get_artist_by_name(name)
                if monitored:
                    db.remove_artist(monitored[0].art_id)
                    logger.info(f"No longer monitoring {monitored[0].art_name}")
                else:
                    logger.info(f"Artist {name} not found")
