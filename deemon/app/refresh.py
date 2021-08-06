from deemon.app import Deemon, utils, download, notify
import time
import tqdm
import logging
import deezer

logger = logging.getLogger(__name__)


class Refresh:

    def __init__(self, artist_id=None, playlist_id=None, skip_download=False, time_machine=None, dl_obj=None):
        self.artist_id = artist_id if artist_id else None
        self.playlist_id = playlist_id if playlist_id else None
        self.skip_download = skip_download
        self.time_machine = time_machine
        self.total_new_releases = 0
        self.new_releases = []
        self.refresh_date = self.set_refresh_date()
        self.db = Deemon().db
        self.config = Deemon().config
        self.dz = deezer.Deezer()

        if not dl_obj:
            self.dl = None
            self.queue_list = []
        else:
            self.dl = dl_obj
            self.queue_list = self.dl.queue_list

        self.run()

    def set_refresh_date(self):
        if self.time_machine:
            if utils.validate_date(self.time_machine):
                return self.time_machine
            else:
                return False
        else:
            return utils.get_todays_date()

    def run(self):
        logger.debug("Starting refresh...")
        if not self.refresh_date:
            logger.error(f"Error while setting time machine to {self.time_machine}")

        if self.playlist_id or self.artist_id:
            if self.playlist_id:
                self.refresh_playlists()
            else:
                self.refresh_artists()
        else:
            if not self.monitoring_playlists() and not self.monitoring_artists():
                logger.info("Nothing to refresh. Try monitoring an artist or playlist first!")
                return

            if self.monitoring_playlists():
                self.refresh_playlists()

            if self.monitoring_artists():
                self.refresh_artists()

        if len(self.queue_list) > 0 and not self.skip_download:
            if not self.dl:
                self.dl = download.Download()
                self.dl.queue_list = self.queue_list
                self.dl.download_queue()
            else:
                self.dl.download_queue()

        if len(self.new_releases) > 0:
            notification = notify.Notify(self.new_releases)
            notification.send()

        self.db.commit()

    def refresh_playlists(self):
        if self.playlist_id:
            logger.debug("Playlist ID(s) have been passed, refreshing only those...")
            monitored = []
            for i in self.playlist_id:
                monitored.append(self.db.get_monitored_playlists_by_id(i))
        else:
            logger.debug("Refreshing all monitored playlists...")
            monitored = self.db.get_all_monitored_playlists()

        progress = tqdm.tqdm(monitored, ascii=" #",
                             bar_format='{desc}...  {n_fmt}/{total_fmt} [{bar:40}] {percentage:3.0f}%')

        for playlist in progress:
            new_track_count = 0
            new_playlist = self.existing_playlist(playlist[0])
            playlist_api = self.dz.api.get_playlist(playlist[0])
            progress.set_description_str("Refreshing playlists")

            for track in playlist_api['tracks']['data']:
                if not self.existing_playlist_track(playlist_api['id'], track['id']):
                    if not new_playlist:
                        logger.debug(f"New track {track['id']} detected on playlist {playlist_api['id']}")
                    self.add_playlist_track(playlist_api, track)
                    new_track_count += 1

            if new_track_count > 0 and not new_playlist:
                pl = {'id': playlist[0], 'title': playlist[1], 'link': playlist[2],'bitrate': playlist[3]}
                self.queue_list.append(download.QueueItem(pl['bitrate'], playlist=pl))
                logger.info(f"Playlist '{playlist_api['title']}' has {new_track_count} new track(s)")
            else:
                logger.debug(f"No new tracks have been added to playlist '{playlist_api['title']}'")

    def refresh_artists(self):
        if self.artist_id:
            logger.debug("Artist ID(s) have been passed, refreshing only those...")
            monitored = []
            for i in self.artist_id:
                monitored.append(self.db.get_monitored_artist_by_id(i))
        else:
            logger.debug("Refreshing all monitored artists...")
            monitored = self.db.get_all_monitored_artists()

        progress = tqdm.tqdm(monitored, ascii=" #",
                             bar_format='{desc}...  {n_fmt}/{total_fmt} [{bar:40}] {percentage:3.0f}%')

        for artist in progress:
            artist = {"id": artist[0], "name": artist[1], "bitrate": artist[2],
                      "record_type": artist[3], "alerts": artist[4]}  # TODO This could be cleaned up using rowfactory
            artist_new_release_count = 0
            new_artist = self.existing_artist(artist['id'])
            progress.set_description_str("Refreshing artists")
            artist_albums = self.dz.api.get_artist_albums(artist['id'])['data']

            logger.debug(f"Artist settings for {artist['name']} ({artist['id']}): bitrate={artist['bitrate']}, "
                         f"record_type={artist['record_type']}, alerts={artist['alerts']}")
            for album in artist_albums:
                exists = self.db.get_album_by_id(album_id=album['id'])
                if exists:
                    if exists['future_release'] and (exists['album_release'] <= self.refresh_date):
                        logger.debug(f"Pre-release released: {exists['album_release']} - {exists['album_name']}")
                        self.db.reset_future(exists['album_id'])
                    else:
                        continue

                logger.debug(f"Found release {album['id']} from artist {artist['name']} ({artist['id']})")
                future = self.is_future_release(album['release_date'])
                if future:
                    if self.time_machine:
                        continue
                    logger.debug(f"Pre-release detected: {artist['name']} - {album['title']} [{album['release_date']}]")

                self.db.add_new_release(artist['id'], artist['name'], album['id'],
                                        album['title'], album['release_date'], future_release=future)

                if new_artist:
                    if len(artist_albums) == 0:
                        logger.warning(
                            f"WARNING: Artist '{artist['name']}' setup for monitoring but no releases were found.")
                    continue

                if (artist['record_type'] == album['record_type']) or artist['record_type'] == "all":
                    if self.config['release_by_date']:
                        max_release_date = utils.get_max_release_date(self.config['release_max_days'])
                        if album['release_date'] < max_release_date:
                            logger.debug(f"Release {album['id']} outside of max_release_date, skipping...")
                            continue
                    self.total_new_releases += 1
                    artist_new_release_count += 1
                    self.queue_list.append(download.QueueItem(artist['bitrate'], artist, album))
                    logger.debug(f"Release {album['id']} added to queue")
                    if artist["alerts"]:
                        self.append_new_release(album['release_date'], artist['name'],
                                                album['title'], album['cover_medium'])
                else:
                    logger.debug(f"Release {album['id']} does not meet album_type "
                                 f"requirement of '{self.config['record_type']}'")
            if artist_new_release_count > 0:
                logger.info(f"{artist['name']}: {artist_new_release_count} new release(s)")
            else:
                if not new_artist:
                    logger.debug(f"No new releases found for artist {artist['name']} ({artist['id']})")

    def is_future_release(self, release_date):
        if release_date > self.refresh_date:
            return 1
        else:
            return 0

    def monitoring_playlists(self):
        query = "SELECT * FROM 'playlists'"
        result = self.db.query(query).fetchall()
        if result and len(result) > 0:
            return True

    def monitoring_artists(self):
        query = "SELECT * FROM 'monitor'"
        result = self.db.query(query).fetchall()
        if result and len(result) > 0:
            return True

    def existing_artist(self, artist_id):
        sql_values = {'artist_id': artist_id}
        # TODO BUG - issue #25 - Artist treated as new artist until at least one release has been seen
        query = "SELECT * FROM 'releases' WHERE artist_id = :artist_id"
        artist_exists = self.db.query(query, sql_values).fetchone()
        if not artist_exists:
            logger.debug(f"New artist {artist_id}")
            return True

    def existing_playlist(self, playlist_id):
        sql_values = {'playlist_id': playlist_id}
        # TODO BUG - issue #25 - Artist treated as new artist until at least one release has been seen
        query = "SELECT * FROM 'playlist_tracks' WHERE playlist_id = :playlist_id"
        playlist_exists = self.db.query(query, sql_values).fetchone()
        if not playlist_exists:
            logger.debug(f"Found new playlist {playlist_id}")
            return True

    def existing_playlist_track(self, playlist_id, track_id):
        values = {'pid': playlist_id, 'tid': track_id}
        query = "SELECT * FROM 'playlist_tracks' WHERE track_id = :tid AND playlist_id = :pid"
        result = self.db.query(query, values).fetchone()
        if result:
            return True

    def add_playlist_track(self, playlist, track):
        values = {'pid': playlist['id'], 'tid': track['id'], 'tname': track['title'], 'aid': track['artist']['id'],
                  'aname': track['artist']['name'], 'time': int(time.time())}
        query = ("INSERT INTO 'playlist_tracks' "
                 "('track_id', 'playlist_id', 'artist_id', 'artist_name', 'track_name', 'track_added') "
                 "VALUES (:tid, :pid, :aid, :aname, :tname, :time)")
        result = self.db.query(query, values)
        return result

    def append_new_release(self, release_date, artist, album, cover):
        for days in self.new_releases:
            for key in days:
                if key == "release_date":
                    if release_date in days[key]:
                        days["releases"].append({'artist': artist, 'album': album, 'cover': cover})
                        return

        self.new_releases.append({'release_date': release_date, 'releases': [{'artist': artist, 'album': album}]})
