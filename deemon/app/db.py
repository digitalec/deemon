from deemon import __dbversion__
from packaging.version import parse as parse_version
from datetime import datetime
from pathlib import Path
import logging
import sqlite3
import time


logger = logging.getLogger(__name__)


class DBHelper:

    def __init__(self, db=None):

        self.conn = None
        self.cursor = None
        if db:
            if not Path(db).exists():
                self.open(db)
                self.create_new_database()
            else:
                self.open(db)

        current_db_version = parse_version(self.get_db_version())
        app_db_version = parse_version(__dbversion__)

        if current_db_version < app_db_version:
            self.do_upgrade(current_db_version)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self, name):
        try:
            self.conn = sqlite3.connect(name)
            self.cursor = self.conn.cursor()
        except sqlite3.OperationalError as e:
            logger.error(f"Error opening database: {e}")

    def close(self):
        if self.conn:
            self.conn.commit()
            self.cursor.close()
            self.conn.close()

    def commit(self):
        self.conn.commit()

    def commit_and_close(self):
        logger.debug("Saving changes to DB")
        self.commit()
        self.close()

    def create_new_database(self):
        logger.debug("Updating database structure")
        # TODO MOVE TO ONE SQL STATEMENT OR BREAK INTO VERSIONED GROUPS
        sql_monitor = ("CREATE TABLE IF NOT EXISTS 'monitor' "
                       "('artist_id' INTEGER, 'artist_name' TEXT, 'bitrate' INTEGER, "
                       "'record_type' TEXT, 'alerts' INTEGER)")

        sql_playlists = ("CREATE TABLE IF NOT EXISTS 'playlists' "
                         "('id' INTEGER UNIQUE, 'title' TEXT, 'url' TEXT, "
                         "'bitrate' INTEGER, 'alerts' INTEGER)")

        sql_playlist_tracks = ("CREATE TABLE IF NOT EXISTS 'playlist_tracks' "
                               "('track_id' INTEGER, 'playlist_id' INTEGER, 'artist_id' INTEGER, "
                               "'artist_name' TEXT, 'track_name' TEXT, 'track_added' TEXT)")

        sql_releases = ("CREATE TABLE IF NOT EXISTS 'releases' "
                        "('artist_id' INTEGER, 'artist_name' TEXT, 'album_id' INTEGER, "
                        "'album_name' TEXT, 'album_release' TEXT, 'album_added' INTEGER, "
                        "'future_release' INTEGER DEFAULT 0)")

        self.query(sql_monitor)
        self.query(sql_playlists)
        self.query(sql_playlist_tracks)
        self.query(sql_releases)
        self.query("CREATE TABLE IF NOT EXISTS 'deemon' ('property' TEXT, 'value' TEXT)")
        self.query("CREATE UNIQUE INDEX 'idx_property' ON 'deemon' ('property')")
        self.query("CREATE UNIQUE INDEX 'idx_artist_id' ON 'monitor' ('artist_id')")
        self.query(f"INSERT INTO 'deemon' ('property', 'value') VALUES ('version', '{__dbversion__}')")
        self.commit()

    def get_db_version(self):
        try:
            version = self.query(f"SELECT value FROM deemon WHERE property = 'version'").fetchone()[0]
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
            self.commit()
            logger.debug("Database upgraded to version 1.1")
        # Upgrade database v1.1 to v1.3
        if current_ver < parse_version("1.3"):
            sql_playlists_1 = "ALTER TABLE playlists ADD COLUMN bitrate INTEGER"
            sql_playlists_2 = "ALTER TABLE playlists ADD COLUMN alerts INTEGER"
            sql_updatever = "INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('version', '1.3')"
            self.query(sql_playlists_1)
            self.query(sql_playlists_2)
            self.query(sql_updatever)
            self.commit()
            logger.debug(f"Database upgraded to version 1.3")

    def query(self, query, values=None):
        if values is None:
            values = {}
        result = self.cursor.execute(query, values)
        return result

    def reset_future(self, album_id):
        logger.debug("Clearing future_release flag from " + str(album_id))
        values = {'album_id': album_id}
        sql = "UPDATE 'releases' SET future_release = 0 WHERE album_id = :album_id"
        self.query(sql, values)

    def get_all_monitored_artists(self):
        '''
        Get unique set of artists stored in database

        :return: Unique set of all artists
        :rtype: set
        '''
        result = self.query(f"SELECT * FROM monitor")
        artists = set(x for x in result)
        return sorted(artists, key=lambda x: x[1])

    def get_monitored_artist_by_id(self, artist_id):
        '''
        Get unique set of artists stored in database

        :return: Unique set of all artists
        :rtype: set
        '''
        values = {'id': artist_id}
        result = self.query(f"SELECT * FROM monitor WHERE artist_id = :id", values).fetchone()
        return result

    def get_specified_artist(self, artist):
        if type(artist) is int:
            values = {'artist': artist}
            result = self.query("SELECT * FROM monitor WHERE artist_id = :artist", values).fetchone()
        else:
            values = {'artist': artist}
            result = self.query("SELECT * FROM monitor WHERE artist_name = ':artist' COLLATE NOCASE", values).fetchone()
        return result

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
        result = self.query(sql, values)
        return result

    def get_artist_by_id(self, artist_id):
        values = {'id': artist_id}
        sql = "SELECT * FROM 'releases' WHERE artist_id = :id"
        result = self.query(sql, values).fetchone()
        return result

    def get_album_by_id(self, album_id):
        values = {'id': album_id}
        sql = "SELECT * FROM 'releases' WHERE album_id = :id"
        result = self.query(sql, values).fetchone()
        if result:
            album = {'artist_id': result[0], 'artist_name': result[1],
                     'album_id': result[2], 'album_name': result[3],
                     'album_release': result[4], 'album_added': result[5],
                     'future_release': result[6]}
            return album

    def monitor_playlist(self, playlist):
        values = {'id': playlist['id'], 'title': playlist['title'],
                  'url': playlist['link']}
        sql = "INSERT OR REPLACE INTO playlists ('id', 'title', 'url') VALUES (:id, :title, :url)"
        self.query(sql, values)
        self.commit()

    def get_all_monitored_playlists(self):
        result = self.query("SELECT * FROM playlists")
        playlists = [x for x in result]
        return playlists

    def get_monitored_playlists_by_id(self, playlist_id):
        values = {'id': playlist_id}
        result = self.query("SELECT * FROM playlists WHERE id = :id", values).fetchone()
        return result

    def get_playlist_by_id(self, playlist_id):
        values = {'id': playlist_id}
        sql = "SELECT * FROM 'playlist_tracks' WHERE playlist_id = :id"
        result = self.query(sql, values).fetchone()
        return result

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