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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from tqdm import tqdm

from deemon import db, config
from deemon.core import notifier
from deemon.core.config import MAX_API_THREADS
from deemon.core.api import PlatformAPI
from deemon.core.logger import logger
from deemon.cmd.download import QueueItem, Download
from deemon.utils import dates, ui, recordtypes


class Refresh:

    def __init__(self, download_all: bool = False, skip_downloads: bool = False, time_machine: str = None):
        self.new_releases = list()
        self.holding_queue = list()
        self.notification_queue = list()
        self.download_all = download_all
        self.skip_downloads = skip_downloads
        self.time_machine = time_machine

        self.db_releases = [x['alb_id'] for x in db.get_releases()]
        self.db_future_releases = self.get_future_releases()

    @staticmethod
    def get_api_release_data(artists=None, playlists=None):
        api = PlatformAPI()
        api_result = {'artists': list(), 'playlists': list()}

        if artists:
            with ThreadPoolExecutor(max_workers=MAX_API_THREADS) as ex:
                api_result['artists'] = list(
                    tqdm(ex.map(api.get_artist_releases, artists),
                         total=len(artists),
                         desc=f"Getting artist release data for {len(artists)} artist(s), please wait...",
                         ascii=" #",
                         bar_format=ui.TQDM_FORMAT)
                )

        return api_result

    @staticmethod
    def release_date_in_future(release_date: str):
        """ Returns True if release date is in the future"""
        release_date_dt = dates.str_to_datetime_obj(release_date)
        if release_date_dt > datetime.now():
            return True

    @staticmethod
    def get_release_record_type_index(artist_id: int, release: dict):
        """ Returns releases' Record Type Index based on information returned from API """
        record_type = list()
        if artist_id == release['art_id'] and not release['official']:
            record_type.append("unofficial")
        if artist_id != release['art_id']:
            record_type.append("feat")
        if release['rectype'] == "0":
            record_type.append("single")
        elif release['rectype'] == "1":
            record_type.append("album")
        elif release['rectype'] == "2":
            record_type.append("comp")
        elif release['rectype'] == "3":
            record_type.append("ep")
        return recordtypes.get_record_type_index(record_type)

    @staticmethod
    def get_allowed_record_type_index(artist: dict) -> int:
        """ Returns Record Type Index for artist if defined, otherwise uses config """
        if artist['rectype']:
            logger.debug("Overriding record type based on artist settings")
            return artist['rectype']
        else:
            return recordtypes.get_record_type_index(config.record_types)

    @staticmethod
    def is_allowed_record_type(allowed_rt, release_rt):
        if recordtypes.compare_record_type_index(allowed_rt, release_rt):
            return True

    @staticmethod
    def get_explicit_value(value):
        """ Returns whether release is explicit or not """
        if value != 1:
            return 0
        else:
            return 1

    def release_before_time_machine(self, release_date):
        """ Returns True if release date is before time machine date """
        time_machine = dates.str_to_datetime_obj(self.time_machine)
        if release_date <= time_machine:
            return True

    @staticmethod
    def release_before_max_release_age(release_date):
        if release_date < (datetime.now() - timedelta(config.max_release_age)):
            return True

    def is_new_release(self, release):
        """ Returns True if release ID is not already stored in database """
        if release['alb_id'] not in self.db_releases:
            return True

    def is_in_future_table(self, release_id: int):
        """ Returns True if release ID is found in future_release table """
        if release_id in [x['alb_id'] for x in self.db_future_releases]:
            return True

    def is_future_changed(self, release: dict):
        """ Returns True if release date has changed """
        for future_release in self.db_future_releases:
            if future_release['alb_id'] == release['alb_id']:
                if future_release['album_release'] != release['alb_date']:
                    return True

    def is_released(self, release: dict):
        """ Checks if release is in future table and/or is a future release """
        if self.is_in_future_table(release['alb_id']):
            if self.release_date_in_future(release['alb_date']):
                if self.is_future_changed(release):
                    logger.info("Release date has changed on future release")
                    db.update_future_release(release)
                    return False
            else:
                db.remove_future_release(release['alb_id'])
                return True
        elif self.release_date_in_future(release['alb_date']):
            db.add_future_release(release)
            return False

    def filter_artist_releases(self, artist):
        """ Filter out releases already seen and add new to new_releases list, download_queue """

        download_queue = list()
        allowed_rti = self.get_allowed_record_type_index(artist)

        for release in artist['releases']:
            release['explicit'] = self.get_explicit_value(release['explicit'])
            release['rectype'] = self.get_release_record_type_index(artist['art_id'], release)

            if self.is_new_release(release) and self.is_allowed_record_type(allowed_rti, release['rectype']):
                self.new_releases.append(
                    {
                        "art_id": release['art_id'],
                        "art_name": release['art_name'],
                        "alb_id": release['alb_id'],
                        "alb_title": release['alb_title'],
                        "alb_date": release['alb_date'],
                        "explicit": release['explicit'],
                        "rectype": release['rectype'],
                    }
                )
            else:
                continue

            if not self.skip_downloads:
                if self.is_released(release):
                    if not self.download_all:
                        release_date_dt = dates.str_to_datetime_obj(release['alb_date'])
                        if self.time_machine and self.release_before_time_machine(release_date_dt):
                            continue
                        if config.max_release_age and self.release_before_max_release_age(release_date_dt):
                            continue
                        # TODO - Change notify
                        if artist['notify'] or (artist['notify'] is None and config.notifications):
                            self.append_notification(release)

                    download_queue.append(QueueItem(release))
        return download_queue

    def get_future_releases(self):
        """ Prune releases and return remaining """
        self.prune_future_releases()
        return db.get_future_albums()

    def prune_future_releases(self):
        """ Remove all future releases that are no longer in the future """
        future_releases = db.get_future_albums()
        to_prune = [x for x in future_releases if not self.release_date_in_future(x['alb_date'])]
        if to_prune:
            logger.debug(f"Pruning {len(to_prune)} release(s) from future release table")
            db.remove_future_release(to_prune)
            db.commit()

    def start(self):
        pending = db.get_pending_artist_refresh()
        artists = []

        if pending:
            logger.info(f"Refreshing {len(pending)} pending artist(s)/playlist(s)")
            for entry in pending:
                artists.append(entry)
            if not self.download_all:
                self.skip_downloads = True
        else:
            artists = db.get_artists()

        if not artists:
            return logger.info("No artists/playlists to refresh. Try monitoring something first!")

        api_releases = self.get_api_release_data(artists)

        # TODO Need to clean up this block
        with ThreadPoolExecutor(max_workers=MAX_API_THREADS) as ex:
            result = list(ex.map(self.filter_artist_releases, api_releases['artists']))
            queue = [elem for q in result for elem in q]

        if queue:
            # If operating in away_mode, dump queue to CSV format
            # TODO - Implement away mode
            if config.away_mode:
                logger.debug("Away Mode is enabled. Storing queue items for later")
                for release in queue:
                    self.holding_queue.append(vars(release))
                db.save_holding_queue(self.holding_queue)
                db.commit()
            else:
                dl = Download()
                dl.download_queue(queue)

        if self.new_releases:
            logger.debug("New releases found, adding to database...")
            db.add_new_releases(self.new_releases)

        if pending:
            db.drop_all_pending_artists()

        db.commit()

        if len(self.notification_queue):
            notification = notifier.Notify(self.notification_queue)
            notification.send()

        self.db_stats()

    def append_notification(self, release: dict):
        """ Append release to list for its release date """
        if release['alb_date'] in [x['release_date'] for x in self.notification_queue]:
            for day in self.notification_queue:
                if release['alb_date'] == day['release_date']:
                    if release['link'] not in [x['link'] for x in day['releases']]:
                        day["releases"].append(release)
        else:
            self.notification_queue.append(
                {
                    'release_date': release['alb_date'],
                    'releases': [release]
                }
            )

    @staticmethod
    def db_stats():
        """ Prints out some statistics at the end of a Refresh operation """
        artists = len(db.get_artists())
        playlists = len(db.get_playlists())
        releases = len(db.get_releases())
        future = len(db.get_future_albums())

        print("")
        print(f"+ Artists monitored: {artists:,}")
        print(f"+ Playlists monitored: {playlists:,}")
        print(f"+ Releases seen: {releases:,}")
        print(f"+ Pending future releases: {future:,}")
        print("")
