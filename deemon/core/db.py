from deemon import __dbversion__
from deemon.utils import startup
from packaging.version import parse as parse_version
from datetime import datetime
from pathlib import Path
import logging
import sqlite3
import time


logger = logging.getLogger(__name__)


class Database(object):

    def __init__(self, db):
        self.conn = None
        self.cursor = None

        if not Path(db).exists():
            self.connect(db)
            self.create_new_database()
        else:
            self.connect(db)

        current_db_version = parse_version(self.get_db_version())
        app_db_version = parse_version(__dbversion__)

        if current_db_version < app_db_version:
            self.do_upgrade(current_db_version)

    def __enter__(self):
        return self

    def __exit__(self):
        self.close()

    @staticmethod
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def connect(self, db):
        try:
            self.conn = sqlite3.connect(db)
            self.conn.row_factory = self.dict_factory
            self.cursor = self.conn.cursor()
        except sqlite3.OperationalError as e:
            logger.error(f"Error opening database: {e}")

    def close(self):
        if self.conn:
            self.conn.commit()
            self.conn.close()

    def commit(self):
        self.conn.commit()

    def commit_and_close(self):
        logger.debug("Saving changes to DB")
        self.commit()
        self.close()

    def create_new_database(self):
        logger.debug("Creating database")

        self.query("CREATE TABLE monitor ("
                   "'artist_id' INTEGER,"
                   "'artist_name' TEXT,"
                   "'bitrate' INTEGER,"
                   "'record_type' TEXT,"
                   "'alerts' INTEGER,"
                   "'download_path' TEXT)")

        self.query("CREATE TABLE playlists ("
                   "'id' INTEGER UNIQUE,"
                   "'title' TEXT,"
                   "'url' TEXT,"
                   "'bitrate' INTEGER,"
                   "'alerts' INTEGER,"
                   "'download_path' TEXT)")

        self.query("CREATE TABLE playlist_tracks ("
                   "'track_id' INTEGER,"
                   "'playlist_id' INTEGER,"
                   "'artist_id' INTEGER,"
                   "'artist_name' TEXT,"
                   "'track_name' TEXT,"
                   "'track_added' TEXT)")

        self.query("CREATE TABLE releases ("
                   "'artist_id' INTEGER,"
                   "'artist_name' TEXT,"
                   "'album_id' INTEGER,"
                   "'album_name' TEXT,"
                   "'album_release' TEXT,"
                   "'album_added' INTEGER,"
                   "'explicit' INTEGER,"
                   "'future_release' INTEGER DEFAULT 0)")

        self.query("CREATE TABLE monitor ("
                   "'artist_id' INTEGER,"
                   "'artist_name' TEXT,"
                   "'bitrate' INTEGER,"
                   "'record_type' TEXT,"
                   "'alerts' INTEGER,"
                   "'download_path' TEXT)")

        self.query("CREATE TABLE playlists ("
                   "'id' INTEGER UNIQUE,"
                   "'title' TEXT,"
                   "'url' TEXT,"
                   "'bitrate' INTEGER,"
                   "'alerts' INTEGER,"
                   "'download_path' TEXT)")

        self.query("CREATE TABLE playlist_tracks ("
                   "'track_id' INTEGER,"
                   "'playlist_id' INTEGER,"
                   "'artist_id' INTEGER,"
                   "'artist_name' TEXT,"
                   "'track_name' TEXT,"
                   "'track_added' TEXT)")

        self.query("CREATE TABLE releases ("
                   "'artist_id' INTEGER,"
                   "'artist_name' TEXT,"
                   "'album_id' INTEGER,"
                   "'album_name' TEXT,"
                   "'album_release' TEXT,"
                   "'album_added' INTEGER,"
                   "'explicit' INTEGER,"
                   "'future_release' INTEGER DEFAULT 0)")

        self.query("CREATE TABLE 'deemon' ("
                   "'property' TEXT,"
                   "'value' TEXT)")

        self.query("CREATE UNIQUE INDEX 'idx_property' ON 'deemon' ('property')")
        self.query("CREATE UNIQUE INDEX 'idx_artist_id' ON 'monitor' ('artist_id')")
        self.query(f"INSERT INTO 'deemon' ('property', 'value') VALUES ('version', '{__dbversion__}')")
        self.query(f"INSERT INTO 'deemon' ('property', 'value') VALUES ('last_update_check', 0)")
        self.commit()

    def get_db_version(self):
        try:
            version = self.query(f"SELECT value FROM deemon WHERE property = 'version'").fetchone()['value']
        except sqlite3.OperationalError:
            version = '0.0.0'

        logger.debug(f"Database version {version}")
        return version

    def do_upgrade(self, current_ver):
        # Upgrade database v1.0 to v1.1
        if current_ver < parse_version("1.1"):
            sql_playlists = ("CREATE TABLE IF NOT EXISTS 'playlists' "
                             "('id' INTEGER UNIQUE, 'title' TEXT, 'url' TEXT)")

            sql_playlist_tracks = ("CREATE TABLE IF NOT EXISTS 'playlist_tracks' "
                                   "('track_id' INTEGER, 'playlist_id' INTEGER, 'artist_id' INTEGER, "
                                   "'artist_name' TEXT, 'track_name' TEXT, 'track_added' TEXT)")
            self.query(sql_playlists)
            self.query(sql_playlist_tracks)
            self.query("INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('version', '1.1')")
            logger.debug("Database upgraded to version 1.1")
        # Upgrade database v1.1 to v1.3
        if current_ver < parse_version("1.3"):
            sql_playlists_1 = "ALTER TABLE playlists ADD COLUMN bitrate INTEGER"
            sql_playlists_2 = "ALTER TABLE playlists ADD COLUMN alerts INTEGER"
            sql_updatever = "INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('version', '1.3')"
            self.query(sql_playlists_1)
            self.query(sql_playlists_2)
            self.query(sql_updatever)
            logger.debug(f"Database upgraded to version 1.3")
        if current_ver < parse_version("2.1"):
            self.query("INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('last_update_check', 0)")
            self.query("INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('version', '2.1')")
        if current_ver < parse_version("2.2"):
            self.query("ALTER TABLE monitor ADD COLUMN download_path TEXT")
            self.query("ALTER TABLE playlists ADD COLUMN download_path TEXT")
            self.query("INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('version', '2.2')")
        self.commit()

    def query(self, query, values=None):
        if values is None:
            values = {}
        return self.conn.execute(query, values)

    def reset_future(self, album_id):
        logger.debug("Clearing future_release flag from " + str(album_id))
        values = {'album_id': album_id}
        sql = "UPDATE 'releases' SET future_release = 0 WHERE album_id = :album_id"
        self.query(sql, values)

    def get_all_monitored_artists(self):
        result = self.query(f"SELECT * FROM monitor").fetchall()
        return sorted(result, key=lambda x: x['artist_name'])

    def get_monitored_artist_by_id(self, artist_id):
        '''
        Get unique set of artists stored in database

        :return: Unique set of all artists
        :rtype: set
        '''
        values = {'id': artist_id}
        return self.query(f"SELECT * FROM monitor WHERE artist_id = :id", values).fetchone()

    def get_specified_artist(self, artist):
        if type(artist) is int:
            values = {'artist': artist}
            return self.query("SELECT * FROM monitor WHERE artist_id = :artist", values).fetchone()
        else:
            values = {'artist': artist}
            return self.query("SELECT * FROM monitor WHERE artist_name = ':artist' COLLATE NOCASE", values).fetchone()

    def add_new_release(self, artist_id, artist_name, album_id, album_name, release_date, future_release):
        timestamp = int(time.time())
        values = {'artist_id': artist_id, 'artist_name': artist_name, 'album_id': album_id,
                  'album_name': album_name, 'release_date': release_date, 'future': future_release}
        sql = (f"INSERT INTO releases ('artist_id', 'artist_name', 'album_id', "
               f"'album_name', 'album_release', 'album_added', 'future_release') "
               f"VALUES (:artist_id, :artist_name, :album_id, :album_name, "
               f":release_date, {timestamp}, :future)")
        self.query(sql, values)

    def is_monitored(self, artist_id):
        result = self.query(f"SELECT artist_id, artist_name FROM monitor WHERE artist_id = {artist_id}").fetchone()
        if result:
            logger.info(f"Artist {result[1]} ({result[0]}) is already being monitored")
            return True

    def show_new_releases(self, from_date_ts, now_ts):
        today_date = datetime.utcfromtimestamp(now_ts).strftime('%Y-%m-%d')
        from_date = datetime.utcfromtimestamp(from_date_ts).strftime('%Y-%m-%d')
        values = {'from': from_date, 'today': today_date}
        sql = "SELECT * FROM 'releases' WHERE album_release >= :from AND album_release <= :today"
        return self.query(sql, values)

    def get_artist_by_id(self, artist_id):
        values = {'id': artist_id}
        sql = "SELECT * FROM 'releases' WHERE artist_id = :id"
        return self.query(sql, values).fetchone()

    def get_album_by_id(self, album_id):
        values = {'id': album_id}
        sql = "SELECT * FROM 'releases' WHERE album_id = :id"
        return self.query(sql, values).fetchone()

    def monitor_playlist(self, playlist):
        values = {'id': playlist['id'], 'title': playlist['title'],
                  'url': playlist['link']}
        sql = "INSERT OR REPLACE INTO playlists ('id', 'title', 'url') VALUES (:id, :title, :url)"
        self.query(sql, values)
        self.commit()

    def get_all_monitored_playlists(self):
        return self.query("SELECT * FROM playlists")

    def get_monitored_playlists_by_id(self, playlist_id):
        values = {'id': playlist_id}
        return self.query("SELECT * FROM playlists WHERE id = :id", values).fetchone()

    def get_playlist_by_id(self, playlist_id):
        values = {'id': playlist_id}
        sql = "SELECT * FROM 'playlist_tracks' WHERE playlist_id = :id"
        return self.query(sql, values).fetchone()

    def reset_database(self):
        self.query("DELETE FROM monitor")
        self.query("DELETE FROM releases")
        self.commit()
        logger.debug("All artists have been purged from database")

        self.query("DELETE FROM playlists")
        self.query("DELETE FROM playlist_tracks")
        self.commit()
        logger.debug("All playlists have been purge from database")
        logger.info("Database has been reset")

    def last_update_check(self):
        return self.query("SELECT value FROM 'deemon' WHERE property = 'last_update_check'").fetchone()['value']

    def set_last_update(self):
        now = int(time.time())
        self.query(f"UPDATE deemon SET value = {now} WHERE property = 'last_update_check'")
        self.commit()
