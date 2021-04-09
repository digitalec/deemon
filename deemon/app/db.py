import sqlite3

class DB:

    def __init__(self, db_path: object):
        try:
            self.conn = sqlite3.connect(db_path)
            self.cursor = self.conn.cursor()
            self.query("CREATE TABLE IF NOT EXISTS releases (artist_id INTEGER, album_id INTEGER)")
        except sqlite3.OperationalError as e:
            print("Error: unable to open database file")
            exit()


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

    def purge_unmonitored_artists(self, artists: list):
        '''

        :param artists:
        :return:
        '''
        nb_artists = len(artists)
        if nb_artists > 0:
            self.query(f"DELETE FROM releases WHERE artist_id IN ({str(artists).strip('[]')})")
            return nb_artists

    def commit_and_close(self):
        self.conn.commit()
        self.conn.close()
