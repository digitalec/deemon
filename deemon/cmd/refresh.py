from deemon.cmd import download
from deemon.core.db import Database
from deemon.core.config import Config as config
from deemon.utils import validate, dates, ui
from deemon.core import notifier
import tqdm
import logging
import deezer

logger = logging.getLogger(__name__)


class Refresh:

    def __init__(self, artist_name: list = None, artist_id: list = None, playlist_title:list = None,
                 playlist_id: list = None, skip_download=False, time_machine=None, dl_obj=None,
                 rollback: int = None, dry_run: bool = False):
        self.artist_id = artist_id or []
        self.artist_name = artist_name
        self.playlist_title = playlist_title
        self.playlist_id = playlist_id or []
        self.message_queue = []
        self.skip_download = skip_download
        self.time_machine = time_machine
        self.total_new_releases = 0
        self.new_releases = []
        self.refresh_date = self.set_refresh_date()
        self.trans_id = None
        self.rollback = rollback
        self.dry_run = dry_run
        self.dz = deezer.Deezer()
        self.db = Database()

        if self.dry_run:
            logger.debug("--DRY-RUN enabled")
            self.skip_download = True

        if not dl_obj:
            self.dl = None
            self.queue_list = []
        else:
            self.dl = dl_obj
            self.queue_list = self.dl.queue_list

        if self.rollback:
            self.rollback_transaction()
        else:
            self.run()

    def set_refresh_date(self):
        if self.time_machine:
            if validate.validate_date(self.time_machine):
                return self.time_machine
            else:
                return False
        else:
            return dates.get_todays_date()

    def store_message(self, message):
        if message:
            self.message_queue.append(message)

    def rollback_transaction(self):
        self.db.rollback_refresh(self.rollback)
        return logger.info(f"Rolled back the last {self.rollback} refresh(es)")

    def run(self):
        logger.debug("Starting refresh...")
        if not self.refresh_date:
            logger.error(f"Error while setting time machine to {self.time_machine}")

        if self.artist_name:
            for name in self.artist_name:
                artist = self.db.get_monitored_artist_by_name(name)
                if artist:
                    self.artist_id.append(artist['artist_id'])
                else:
                    self.store_message(f"Artist '{name}' is not being monitored")
            if not len(self.artist_id):
                return
        elif self.playlist_title:
            for title in self.playlist_title:
                playlist = self.db.get_monitored_playlist_by_name(title)
                if playlist:
                    self.playlist_id.append(playlist['id'])
                else:
                    self.store_message(f"Playlist '{title}' is not being monitored")
            if not len(self.playlist_id):
                return

        if self.playlist_id or self.artist_id:
            if self.playlist_id:
                self.refresh_playlists()
            if self.artist_id:
                self.refresh_artists()
        else:

            monitored_playlists = self.db.get_all_monitored_playlists()
            monitored_artists = self.db.get_all_monitored_artists()

            if not monitored_playlists and not monitored_artists:
                logger.info("Nothing to refresh. Try monitoring an artist or playlist first!")
                return

            if monitored_playlists:
                self.refresh_playlists()

            if monitored_artists:
                self.refresh_artists()

        if len(self.message_queue):
            print("\nThe following could not be refreshed:")
            for msg in self.message_queue:
                print(" - " + msg)

        if len(self.queue_list) > 0 and not self.skip_download:
            if not self.dl:
                self.dl = download.Download()
                self.dl.queue_list = self.queue_list
                self.dl.download_queue()
            else:
                self.dl.download_queue()

        if len(self.new_releases) > 0:
            notification = notifier.Notify(self.new_releases)
            notification.send()

        if not self.dry_run:
            self.db.commit()

        if self.time_machine:
            self.time_machine = None
            self.run()

    def queue_new_releases(self, artist, album):
        is_new_release = 0
        if (artist['record_type'] == album['record_type']) or artist['record_type'] == "all":
            if config.release_by_date():
                max_release_date = dates.get_max_release_date(config.release_max_days())
                if album['release_date'] < max_release_date:
                    logger.debug(f"Release {album['id']} outside of max_release_date, skipping...")
                    return
            self.total_new_releases += 1
            is_new_release = 1

            self.queue_list.append(download.QueueItem(artist=artist, album=album, bitrate=artist['bitrate'],
                                                      download_path=artist['download_path']))
            logger.debug(f"Release {album['id']} added to queue")
            if artist["alerts"]:
                self.append_new_release(album['release_date'], artist['artist_name'],
                                        album['title'], album['cover_medium'])
        else:
            logger.debug(f"Release {album['id']} does not meet album_type "
                         f"requirement of '{config.record_type()}'")
        return is_new_release

    def refresh_playlists(self):
        monitored = []
        if self.playlist_id:
            logger.debug("Playlist ID(s) have been passed, refreshing only those...")
            for i in self.playlist_id:
                monitored.append(self.db.get_monitored_playlist_by_id(i))
        else:
            logger.debug("Refreshing all monitored playlists...")
            monitored = self.db.get_all_monitored_playlists()

        max_title_length = 0
        for m in monitored:
            string_len = len(m['title'])
            if string_len > max_title_length:
                max_title_length = string_len

        progress = tqdm.tqdm(monitored, ascii=" #",
                             bar_format='{desc}  {n_fmt}/{total_fmt} [{bar}] {percentage:3.0f}%')

        for playlist in progress:
            descr = ui.set_progress_bar_text(f"Refreshing {playlist['title']}", max_title_length)
            progress.set_description_str(descr)

            playlist['bitrate'] = playlist.get('bitrate') or config.bitrate()
            playlist['alerts'] = playlist.get('alerts') or config.alerts()
            playlist['record_type'] = playlist.get('record_type') or config.record_type()
            playlist['download_path'] = playlist.get('download_path') or config.download_path()

            new_track_count = 0
            new_playlist = self.db.get_playlist_tracks(playlist['id'])
            playlist_api = self.dz.api.get_playlist(playlist['id'])

            for track in playlist_api['tracks']['data']:
                if not self.db.get_track_from_playlist(playlist_api['id'], track['id']):
                    if not new_playlist:
                        logger.debug(f"New track {track['id']} detected on playlist {playlist_api['id']}")
                    self.db.add_playlist_track(playlist_api, track)
                    new_track_count += 1

            if new_track_count > 0 and not new_playlist:
                self.queue_list.append(
                    download.QueueItem(playlist=playlist, bitrate=playlist['bitrate'],
                                       download_path=playlist['download_path'])
                )
                logger.info(f"Playlist '{playlist_api['title']}' has {new_track_count} new track(s)")
            else:
                logger.debug(f"No new tracks have been added to playlist '{playlist_api['title']}'")

            self.db.set_playlist_refreshed(playlist['id'])

            if playlist == monitored[-1]:
                progress.set_description_str("Refresh complete")

    def refresh_artists(self):
        if self.artist_id:
            logger.debug("Artist ID(s) have been passed, refreshing only those...")
            monitored = []
            for i in self.artist_id:
                monitored.append(self.db.get_monitored_artist_by_id(i))
        else:
            logger.debug("Refreshing all monitored artists...")
            monitored = self.db.get_all_monitored_artists()

        max_title_length = 0
        for m in monitored:
            string_len = len(m['artist_name'])
            if string_len > max_title_length:
                max_title_length = string_len

        progress = tqdm.tqdm(monitored, ascii=" #",
                             bar_format='{desc}  {n_fmt}/{total_fmt} [{bar}] {percentage:3.0f}%')

        for artist in progress:
            descr = ui.set_progress_bar_text(f"Refreshing {artist['artist_name']}", max_title_length)
            progress.set_description_str(descr)

            logger.debug(f"Artist settings for {artist['artist_name']} ({artist['artist_id']}): bitrate={artist['bitrate']}, "
                         f"record_type={artist['record_type']}, alerts={artist['alerts']}, "
                         f"download_path={artist['download_path']}")

            artist['bitrate'] = artist['bitrate'] or config.bitrate()
            artist['alerts'] = artist['alerts'] or config.alerts()
            artist['record_type'] = artist['record_type'] or config.record_type()
            artist['download_path'] = artist['download_path'] or config.download_path()

            artist_new_release_count = 0
            artist_albums = self.dz.api.get_artist_albums(artist['artist_id'])['data']

            for album in artist_albums:
                exists = self.db.get_album_by_id(album_id=album['id'])
                if exists:
                    if exists['future_release'] and (exists['album_release'] <= self.refresh_date):
                        logger.debug(f"Pre-release released: {exists['album_release']} - {exists['album_name']}")
                        self.db.reset_future(exists['album_id'])
                    else:
                        continue

                logger.debug(f"Found release {album['id']} from artist {artist['artist_name']} ({artist['artist_id']})")
                future = self.is_future_release(album['release_date'])
                if future:
                    if self.time_machine:
                        continue
                    logger.debug(f"Pre-release detected: {artist['artist_name']} - {album['title']} [{album['release_date']}]")

                self.db.add_new_release(artist['artist_id'], artist['artist_name'], album['id'],
                                        album['title'], album['release_date'], future)

                if artist['refreshed'] == 0:
                    continue

                artist_new_release_count += self.queue_new_releases(artist, album)

            if artist_new_release_count > 0:
                logger.info(f"{artist['artist_name']}: {artist_new_release_count} new release(s)")
            else:
                logger.debug(f"No new releases found for artist {artist['artist_name']} ({artist['artist_id']})")

            self.db.set_artist_refreshed(artist['artist_id'])

            if artist == monitored[-1]:
                progress.set_description_str("Refresh complete")

    def is_future_release(self, release_date):
        if release_date > self.refresh_date:
            return 1
        else:
            return 0

    def append_new_release(self, release_date, artist, album, cover):
        for days in self.new_releases:
            for key in days:
                if key == "release_date":
                    if release_date in days[key]:
                        days["releases"].append({'artist': artist, 'album': album, 'cover': cover})
                        return

        self.new_releases.append({'release_date': release_date, 'releases': [{'artist': artist, 'album': album}]})
