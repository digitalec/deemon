from deemon import __version__
from deemon.app import utils
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

        sql_monitor = ("CREATE TABLE IF NOT EXISTS 'monitor' "
                       "('artist_id' INTEGER, 'artist_name' TEXT, 'bitrate' INTEGER, "
                       "'record_type' TEXT, 'alerts' INTEGER)")

        sql_releases = ("CREATE TABLE IF NOT EXISTS 'releases' "
                        "('artist_id' INTEGER, 'artist_name' TEXT, 'album_id' INTEGER, "
                        "'album_name' TEXT, 'album_release' TEXT, 'album_added' INTEGER, "
                        "'future_release' INTEGER DEFAULT 0)")

        self.query(sql_monitor)
        self.query(sql_releases)
        self.query("CREATE TABLE IF NOT EXISTS 'deemon' ('property' TEXT, 'value' TEXT)")
        self.query("CREATE UNIQUE INDEX 'idx_property' ON 'deemon' ('property')")
        self.query("CREATE UNIQUE INDEX 'idx_artist_id' ON 'monitor' ('artist_id')")
        self.query(f"INSERT INTO 'deemon' ('property', 'value') VALUES ('version', '{__version__}')")
        self.commit()

    def get_db_version(self):
        try:
            version = self.query(f"SELECT value FROM deemon WHERE property = 'version'").fetchone()[0]
        except sqlite3.OperationalError:
            version = '0.0.0'

        logger.debug(f"Database version {version}")
        return version

    def query(self, query: str, values=None):
        if values is None:
            values = {}
        result = self.cursor.execute(query, values)
        return result

    def reset_future(self, album_id):
        logger.debug("Clearing future_release flag from " + str(album_id))
        values = {'album_id': album_id}
        sql = "UPDATE 'releases' SET future_release = 0 WHERE album_id = :album_id"
        result = self.query(sql, values)

    def get_all_monitored_artists(self):
        '''
        Get unique set of artists stored in database

        :return: Unique set of all artists
        :rtype: set
        '''
        result = self.query(f"SELECT * FROM monitor")
        artists = set(x for x in result)
        return sorted(artists, key=lambda x: x[1])

    def get_specified_artist(self, artist):
        if type(artist) is int:
            values = {'artist': artist}
            result = self.query("SELECT * FROM monitor WHERE artist_id = :artist", values).fetchone()
        else:
            values = {'artist': artist}
            result = self.query("SELECT * FROM monitor WHERE artist_name = :artist COLLATE NOCASE", values).fetchone()
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
        return result
