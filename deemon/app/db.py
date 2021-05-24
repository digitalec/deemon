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

        self.conn = self.connect(db_path)
        self.cursor = self.conn.cursor()

        if first_run:
            self.create_new_database()

        self.db_app_version = self.get_db_version()

        logger.debug(f"Using db: {db_path}")

    def connect(self, db_path):
        try:
            conn = sqlite3.connect(db_path)
            return conn
        except sqlite3.OperationalError as e:
            logger.error(f"Error opening database: {e}")
            exit(1)

    def create_new_database(self):
        logger.debug("Building database structure")

        sql_monitor = ("CREATE TABLE IF NOT EXISTS 'monitor' "
                       "('artist_id' INTEGER, 'artist_name' TEXT, 'bitrate' INTEGER, "
                       "'record_type' TEXT, 'alerts' INTEGER)")

        sql_releases = ("CREATE TABLE IF NOT EXISTS 'releases' "
                        "('artist_id' INTEGER, 'album_id' INTEGER, "
                        "'album_release' TEXT, 'album_added' TEXT)")

        self.query(sql_monitor)
        self.query(sql_releases)
        self.query("CREATE TABLE IF NOT EXISTS 'deemon' ('property' TEXT, 'value' TEXT)")
        self.query("CREATE UNIQUE INDEX 'idx_property' ON 'deemon' ('property')")
        self.query(f"INSERT INTO 'deemon' ('property', 'value') VALUES ('version', '{__version__}')")

        self.commit()

    def get_db_version(self):
        try:
            version = self.query(f"SELECT value FROM deemon WHERE property = 'version'").fetchone()[0]
        except Exception:
            version = '0.0.0'

        logger.debug(f"Database version {version}")
        return version

    def query(self, query: str):
        # logger.debug(f"SQL: {query}")
        result = self.cursor.execute(query)
        return result

    def check_exists(self, artist_id: int = None, album_id: int = None):
        if album_id:
            result = self.query(f"SELECT * FROM releases WHERE album_id = {album_id}").fetchone()
        else:
            result = self.query(f"SELECT * FROM releases WHERE artist_id = {artist_id}").fetchone()
        return result

    def get_all_artists(self, monitored=False):
        '''
        Get unique set of artists stored in database

        :return: Unique set of all artists
        :rtype: set
        '''
        result = self.query(f"SELECT * FROM monitor")
        artists = set(x for x in result)
        return sorted(artists, key=lambda x: x[1])

    def add_new_release(self, artist_id: int, album_id: int, release_date: str):
        '''
        Add new release to database
        :param artist_id: int
        :param album_id: int
        :return:
        '''

        self.query(f"INSERT INTO releases VALUES({artist_id}, {album_id}, '{release_date}', '{time.time()}')")

    def purge_unmonitored_artists(self, active_artists):
        db_artists = self.get_all_artists()
        purge_list = [x for x in db_artists if x not in active_artists]
        nb_artists = len(purge_list)
        if nb_artists > 0:
            self.query(f"DELETE FROM releases WHERE artist_id IN ({str(purge_list).strip('[]')})")
            return nb_artists

    def is_monitored(self, artist_id):
        result = self.query(f"SELECT artist_id, artist_name FROM monitor WHERE artist_id = {artist_id}").fetchone()
        if result:
            logger.info(f"Artist {result[1]} ({result[0]}) is already being monitored")
            return True

    def start_monitoring(self, artist_id, artist_name, bitrate, record_type, alerts, quiet=False):
        result = self.query(f"INSERT INTO monitor (artist_id, artist_name, bitrate, record_type, alerts) "
                               f"VALUES ({artist_id}, '{artist_name}', {bitrate}, '{record_type}', {alerts})")
        if not quiet:
            logger.info(f"Now monitoring {artist_name}")
        else:
            logger.debug(f"Now monitoring {artist_name}")

    def stop_monitoring(self, artist_name):
        result = self.query(f"DELETE FROM monitor WHERE artist_name = '{artist_name}'")
        if result.rowcount > 0:
            logger.info(f"No longer monitoring {artist_name}")
        else:
            logger.info(f"Artist '{artist_name}' is not being monitored")

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def commit_and_close(self):
        logger.debug("Saving changes to DB")
        self.commit()
        self.close()
