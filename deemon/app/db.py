import logging
import sqlite3
import time
from deemon import __version__
from packaging.version import parse as parse_version

logger = logging.getLogger("deemon")


class DB:

    def __init__(self, db_path: object):
        self.db_app_version = ""
        try:
            self.conn = sqlite3.connect(db_path)
            self.cursor = self.conn.cursor()
            self.check_db_version()
            logger.debug(f"Using db: {db_path}")
        except sqlite3.OperationalError as e:
            logger.error(f"Error opening database: {e}")
            exit(1)

    def setup_db(self):
        '''Check if tables exist, otherwise create them'''
        tables = {
            'deemon': {
                'struct': 'property STRING, value STRING',
                'data': f"'version', '{__version__}'"
            },
            'releases': {
                'struct': 'artist_id INTEGER, album_id INTEGER, album_release STRING, album_added STRING'
            },
            'monitor': {
                'struct': 'artist_id INTEGER, artist_name STRING, bitrate INTEGER, '
                          'record_type STRING, alerts INTEGER'
            }
        }

        for tbl in tables:
            self.query(f"CREATE TABLE IF NOT EXISTS '{tbl}' ({tables[tbl]['struct']})")
            if 'data' in tables[tbl]:
                self.query(f"INSERT INTO '{tbl}' VALUES ({tables[tbl]['data']})")

        self.commit()

    def check_db_version(self):
        try:
            self.db_app_version = self.query(f"SELECT value FROM deemon WHERE property = 'version'").fetchone()[0]
        except Exception as e:
            self.db_app_version = '< 1.0.0'

        if parse_version(self.db_app_version) < parse_version(__version__):
            logger.debug(f"DB version is {self.db_app_version}, upgrading to {__version__}")
            self.upgrade_db()

    def upgrade_db(self):
        if self.db_app_version == '< 1.0.0':
            self.query('ALTER TABLE releases ADD COLUMN album_release STRING')
            self.query('ALTER TABLE releases ADD COLUMN album_added STRING')
            self.setup_db()

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

    def start_monitoring(self, artist_id, artist_name, bitrate, record_type, alerts):
        result = self.query(f"INSERT INTO monitor (artist_id, artist_name, bitrate, record_type, alerts) "
                               f"VALUES ({artist_id}, '{artist_name}', {bitrate}, '{record_type}', {alerts})")
        logger.info(f"Now monitoring {artist_name}")

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
