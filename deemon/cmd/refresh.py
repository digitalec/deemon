import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from tqdm import tqdm

from deemon import db, config
from deemon.core import notifier
from deemon.core.config import MAX_API_THREADS
from deemon.core.api import PlatformAPI
from deemon.core.db import Database
from deemon.core.config import Config
from deemon.utils import dates, ui, dataprocessor, recordtypes

logger = logging.getLogger(__name__)
config = Config().CONFIG
db = Database()
new_releases = []
holding_queue = []
notification_queue = []


def get_api_release_data(artists=None, playlists=None):
    api = PlatformAPI()
    api_result = {}

    if artists:
        with ThreadPoolExecutor(max_workers=config['max_threads']) as ex:
            api_result['artists'] = list(
                tqdm(ex.map(api.get_artist_releases, artists),
                     total=len(artists),
                     desc=f"Getting artist release data for {len(artists)} artist(s), please wait...",
                     ascii=" #",
                     bar_format=ui.TQDM_FORMAT)
            )

    return api_result


def is_future_release(release_date: str):
    """ Returns True if release date is in the future"""
    release_date_dt = dates.str_to_datetime_obj(release_date)
    if release_date_dt > datetime.now():
        return True


def filter_api_release_data(api_releases):

    allowed_record_types = None
    existing_future_releases = db.get_future_releases()
    queue = []

    # Get existing releases in database
    db_releases = db.get_artist_releases()
    db_release_ids = [x['album_id'] for x in db_releases]

    # Loop over each artist containing all of their releases
    for artist in api_releases['artists']:

        # Check if record type matches what user specified
        if artist['record_type']:
            logger.debug("Overriding record type based on artist settings")
            allowed_record_types = recordtypes.get_record_type_str(artist['record_type'])
        else:
            allowed_record_types = config['defaults']['record_types']

        # Loop over each release for this artist
        for release in artist['releases']:

            record_type = []

            # Explicit is either 1 or 0
            if release['explicit_lyrics'] != 1:
                release['explicit_lyrics'] = 0

            # Convert record type to our own format for filtering
            if artist['id'] == release['artist_id'] and not release['official']:
                record_type.append("unofficial")
            if artist['id'] != release['artist_id']:
                record_type.append("feat")
            if release['record_type'] == "0":
                record_type.append("single")
            elif release['record_type'] == "1":
                record_type.append("album")
            elif release['record_type'] == "2":
                record_type.append("comp")
            elif release['record_type'] == "3":
                record_type.append("ep")

            release['record_type'] = recordtypes.get_record_type_index(record_type)

            # Check if release already exists in database or else store it in list to add later
            if release['id'] in db_release_ids:
                continue
from deemon.core.logger import logger
from deemon.cmd.download import QueueItem, Download
from deemon.utils import dates, ui, recordtypes

            else:
                new_releases.append(release)

            if config['runtime']['skip_downloads']:
                continue

            # #####
            # Filtering beyond this point to see if release qualifies for download
            # #####

            # Check if release is in future release list and update if release date has changed
            if release['id'] in [x['album_id'] for x in existing_future_releases]:
                for existing in existing_future_releases:
                    if existing['album_id'] == release['id']:
                        if not existing['album_release'] == release['release_date']:
                            if is_future_release(release['release_date']):
                                logger.info(f"Release date has changed to {release['release_date']} for "
                                            f"{release['artist_name']} - {release['title']}.")
                                db.update_future_release(release)

            # If record type(s) of release aren't all allowed, skip it
            if not all(elem in allowed_record_types for elem in record_type):
                continue

            # If download_all is set, release date doesn't matter
            if not config['runtime']['download_all']:
                # Verify if release is within time_machine date
                release_date_dt = dates.str_to_datetime_obj(release['release_date'])
                if config['runtime']['time_machine']:
                    time_machine_dt = dates.str_to_datetime_obj(config['runtime']['time_machine'])
                    if release_date_dt <= time_machine_dt:
                        continue

                # Verify if release is within max_release_age range
                if config['app']['max_release_age']:
                    if release_date_dt < (datetime.now() - timedelta(config['app']['max_release_age'])):
                        continue

            if artist['alerts'] or artist['alerts'] is None:
                create_notification(release)

            # Queue release if it made it this far
            queue.append(QueueItem(release))

        return queue


def prune_future_releases(f):
    to_prune = [x for x in f if not is_future_release(x['album_release'])]
    if to_prune:
        logger.debug(f"Pruning {len(to_prune)} release(s) from future release table")
        db.remove_future_release(to_prune)


def start():

    artists = []

    pending = db.get_pending_artist_refresh()

    if pending:
        logger.info(f"Refreshing {len(pending)} pending artist(s)/playlist(s)")
        for entry in pending:
            artists.append(entry)
        if not config['runtime']['download_all']:
            config['runtime']['skip_downloads'] = True
    else:
        artists = db.get_all_monitored_artists()

    if not artists:
        return logger.info("No artists/playlists to refresh. Try monitoring something first!")

    prune_future_releases(db.get_future_releases())

    api_releases = get_api_release_data(artists)
    queue = filter_api_release_data(api_releases)

    if queue:
        # If operating in away_mode, dump queue to CSV format
        if config['app']['away_mode']:
            logger.debug("Away Mode is enabled. Storing queue items for later")
            for release in queue:
                holding_queue.append(vars(release))
            db.save_holding_queue(holding_queue)
            db.commit()
        else:
            dl = Download()
            dl.download_queue(queue)

    if new_releases:
        db.add_new_releases(new_releases)
        db.commit()

    if pending:
        db.drop_all_pending_artists()
        db.commit()

    if len(notification_queue):
        notification = notifier.Notify(notification_queue)
        notification.send()


def create_notification(release: dict):

    if release['release_date'] in [x['release_date'] for x in notification_queue]:
        for day in notification_queue:
            if release['release_date'] == day['release_date']:
                if release['link'] not in [x['link'] for x in day['releases']]:
                    day["releases"].append(release)
    else:
        notification_queue.append(
            {
                'release_date': release['release_date'],
                'releases': [release]
            }
        )