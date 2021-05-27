import logging
import sqlite3
import time
from pathlib import Path
from deemon import __version__

logger = logging.getLogger("deemon")


class DB:

    def __init__(self, db_path, first_run=True):
        if Path(db_path).exists():
            first_run = False

        self.db = db_path
        self.conn = self.connect()
        self.cursor = self.conn.cursor()

        if first_run:
            self.create_new_database()

    def connect(self):
        try:
            conn = sqlite3.connect(self.db)
            return conn
        except sqlite3.OperationalError as e:
            logger.error(f"Error opening database: {e}")
            exit(1)

    def create_new_database(self):
        logger.debug("Updating database structure")

        sql_config = ("CREATE TABLE IF NOT EXISTS 'config' "
                      "('property' TEXT, 'value' TEXT, 'allowed_values' TEXT, "
                      "'default_values' TEXT)")

        sql_config_data = ("INSERT INTO 'config' ('property','value','allowed_values','default_values') "
                           "VALUES ('bitrate','320','128,320,FLAC','320'), "
                           "('record_type','all','all,album,ep,single','all'), "
                           "('alerts','disable','enable,disable','disable'), "
                           "('smtp_server',NULL,NULL,NULL), "
                           "('smtp_port',NULL,NULL,NULL), "
                           "('smtp_username',NULL,NULL,NULL), "
                           "('smtp_password',NULL,NULL,NULL), "
                           "('smtp_recipient',NULL,NULL,NULL)")

        sql_monitor = ("CREATE TABLE IF NOT EXISTS 'monitor' "
                       "('artist_id' INTEGER, 'artist_name' TEXT, 'bitrate' INTEGER, "
                       "'record_type' TEXT, 'alerts' INTEGER)")

        sql_releases = ("CREATE TABLE IF NOT EXISTS 'releases' "
                        "('artist_id' INTEGER, 'artist_name' TEXT, 'album_id' INTEGER, "
                        "'album_name' TEXT, 'album_release' TEXT, 'album_added' INTEGER)")

        self.query(sql_config)
        self.query(sql_config_data)
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
        except Exception:
            version = '0.0.0'

        # logger.debug(f"Database version {version}")
        return version

    def query(self, query: str, values=None):
        if values is None:
            values = {}
        logger.debug(f"SQL: {query}")
        result = self.cursor.execute(query, values)
        return result

    def check_exists(self, artist_id: int = None, album_id: int = None):
        if album_id:
            result = self.query(f"SELECT * FROM releases WHERE album_id = {album_id}").fetchone()
        else:
            result = self.query(f"SELECT * FROM releases WHERE artist_id = {artist_id}").fetchone()
        return result

    def get_all_artists(self):
        '''
        Get unique set of artists stored in database

        :return: Unique set of all artists
        :rtype: set
        '''
        result = self.query(f"SELECT * FROM monitor")
        artists = set(x for x in result)
        return sorted(artists, key=lambda x: x[1])

    def get_specified_artists(self, artists):
        for artist in artists:
            values = {'artist': artist}
            result = self.query("SELECT * FROM monitor WHERE artist_name = :artist", values)
            artists = set(x for x in result)
            return sorted(artists, key=lambda x: x[1])

    def add_new_release(self, artist_id, artist_name, album_id, album_name, release_date):
        timestamp = int(time.time())
        values = {'artist_id': artist_id, 'artist_name': artist_name,
                  'album_id': album_id, 'album_name': album_name, 'release_date': release_date}
        sql = (f"INSERT INTO releases ('artist_id', 'artist_name', 'album_id', "
               f"'album_name', 'album_release', 'album_added') "
               f"VALUES (:artist_id, :artist_name, :album_id, :album_name, "
               f":release_date, {timestamp})")

        self.query(sql, values)

    def is_monitored(self, artist_id):
        result = self.query(f"SELECT artist_id, artist_name FROM monitor WHERE artist_id = {artist_id}").fetchone()
        if result:
            logger.info(f"Artist {result[1]} ({result[0]}) is already being monitored")
            return True

    def show_new_releases(self, from_date):
        result = self.query(f"SELECT * FROM 'releases' WHERE album_added >= {from_date}")
        return result

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def commit_and_close(self):
        logger.debug("Saving changes to DB")
        self.commit()
        self.close()
