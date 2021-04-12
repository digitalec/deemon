import logging
import sqlite3
from logging import getLogger, ERROR, DEBUG

class DB:

    def __init__(self, db_path: object):
        self.set_db_path(db_path)
        try:
            self.conn = sqlite3.connect(db_path)
            self.cursor = self.conn.cursor()
            self.query("CREATE TABLE IF NOT EXISTS releases (artist_id INTEGER, album_id INTEGER)")
        except sqlite3.OperationalError as e:
            print("Unable to open database file")
            exit(1)

    @staticmethod
    def set_db_path(p):
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            print(f"Error: Insufficient permissions to write to {p.parent}")
            exit(1)
        except FileExistsError:
            pass

    def query(self, query: str):
        result = self.cursor.execute(query)
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
        result = self.query("SELECT artist_id FROM releases")
        artists = set(x[0] for x in result)
        return artists

    def add_new_release(self, artist_id: int, album_id: int):
        '''
        Add new release to database
        :param artist_id: int
        :param album_id: int
        :return:
        '''
        self.query(f"INSERT INTO releases VALUES({artist_id}, {album_id})")

    def purge_unmonitored_artists(self, active_artists):
        db_artists = self.get_all_artists()
        purge_list = [x for x in db_artists if x not in active_artists]
        nb_artists = len(purge_list)
        if nb_artists > 0:
            self.query(f"DELETE FROM releases WHERE artist_id IN ({str(purge_list).strip('[]')})")
            return nb_artists

    def commit_and_close(self):
        self.conn.commit()
        self.conn.close()
