import sqlite3
import time
from datetime import datetime
from pathlib import Path

from packaging.version import parse as parse_version

from deemon import __dbversion__, __version__, config
from deemon.core.logger import logger
from deemon.utils import startup, performance, dates, ui, recordtypes


class Database(object):

    def __init__(self):
        self.conn = None
        self.cursor = None
        self.db = startup.get_database()

        if not Path(self.db).exists():
            self.connect()
            self.create_new_database()
        else:
            self.connect()

        self.transaction_id = self.get_next_transaction_id()

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

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db)
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
        self.commit()
        self.close()

    def create_new_database(self):
        logger.debug("DATABASE CREATION IN PROGRESS!")

        self.query("CREATE TABLE monitor ("
                   "'id' INTEGER,"
                   "'name' TEXT,"
                   "'bitrate' TEXT,"
                   "'record_type' INTEGER,"
                   "'alerts' INTEGER,"
                   "'profile_id' INTEGER DEFAULT 1,"
                   "'download_path' TEXT,"
                   "'trans_id' INTEGER,"
                   "CONSTRAINT unique_artist UNIQUE (id, profile_id)"
                   "ON CONFLICT IGNORE)")

        self.query("CREATE TABLE playlists ("
                   "'id' INTEGER UNIQUE,"
                   "'title' TEXT,"
                   "'url' TEXT,"
                   "'bitrate' TEXT,"
                   "'alerts' INTEGER,"
                   "'profile_id' INTEGER DEFAULT 1,"
                   "'download_path' TEXT,"
                   "'trans_id' INTEGER,"
                   "CONSTRAINT unique_playlist UNIQUE (id, profile_id)"
                   "ON CONFLICT IGNORE)")

        self.query("CREATE TABLE playlist_tracks ("
                   "'track_id' INTEGER,"
                   "'playlist_id' INTEGER,"
                   "'artist_id' INTEGER,"
                   "'artist_name' TEXT,"
                   "'track_name' TEXT,"
                   "'profile_id' INTEGER DEFAULT 1,"
                   "'track_added' TEXT,"
                   "'trans_id' INTEGER)")

        self.query("CREATE TABLE releases ("
                   "'artist_id' INTEGER,"
                   "'artist_name' TEXT,"
                   "'album_id' INTEGER,"
                   "'album_name' TEXT,"
                   "'album_release' TEXT,"
                   "'album_added' INTEGER,"
                   "'explicit' INTEGER,"
                   "'label' TEXT,"
                   "'record_type' INTEGER,"
                   "'profile_id' INTEGER DEFAULT 1,"
                   "'trans_id' INTEGER,"
                   "unique(album_id, profile_id),"
                   "FOREIGN KEY (artist_id, profile_id) "
                   "REFERENCES monitor (id, profile_id) "
                   "ON DELETE CASCADE)")

        self.query("CREATE TABLE future_releases ("
                   "'artist_id' INTEGER,"
                   "'artist_name' TEXT,"
                   "'album_id' INTEGER,"
                   "'album_name' TEXT,"
                   "'album_release' TEXT,"
                   "'album_added' INTEGER,"
                   "'explicit' INTEGER,"
                   "'label' TEXT,"
                   "'record_type' INTEGER,"
                   "'profile_id' INTEGER DEFAULT 1,"
                   "'trans_id' INTEGER,"
                   "unique(album_id, profile_id),"
                   "FOREIGN KEY (artist_id, profile_id) "
                   "REFERENCES monitor (id, profile_id) "
                   "ON DELETE CASCADE)")

        self.query("CREATE TABLE 'deemon' ("
                   "'property' TEXT,"
                   "'value' TEXT)")

        self.query("CREATE TABLE 'profiles' ("
                   "'id' INTEGER,"
                   "'name' TEXT,"
                   "'email' TEXT,"
                   "'alerts' INTEGER,"
                   "'bitrate' TEXT,"
                   "'record_type' TEXT,"
                   "'plex_baseurl' TEXT,"
                   "'plex_token' TEXT,"
                   "'plex_library' TEXT,"
                   "'download_path' TEXT,"
                   "PRIMARY KEY('id' AUTOINCREMENT))")

        self.query("CREATE TABLE transactions ("
                   "'id' INTEGER,"
                   "'timestamp' INTEGER,"
                   "'profile_id' INTEGER DEFAULT 1,"
                   "PRIMARY KEY('id' AUTOINCREMENT))")

        self.query("CREATE TABLE queue ("
                   "'artist_name'	TEXT,"
                   "'album_id'	INTEGER,"
                   "'album_title'	TEXT,"
                   "'track_id'	INTEGER,"
                   "'track_title'	TEXT,"
                   "'url'	TEXT,"
                   "'playlist_title'	TEXT,"
                   "'bitrate'	TEXT,"
                   "'download_path'	TEXT,"
                   "'profile_id'	INTEGER,"
                   "UNIQUE (url, profile_id) "
                   "ON CONFLICT IGNORE)")

        self.query("CREATE TABLE pending_artist_refresh ("
                   "id INTEGER NOT NULL,"
                   "profile_id INTEGER NOT NULL,"
                   "UNIQUE (id, profile_id)"
                   " ON CONFLICT IGNORE,"
                   "FOREIGN KEY (id, profile_id) "
                   "REFERENCES monitor (id, profile_id)"
                   "ON DELETE CASCADE)")

        self.query("CREATE UNIQUE INDEX 'idx_property' ON 'deemon' ('property')")
        self.query("CREATE INDEX 'artist' ON 'releases' ('artist_id', 'profile_id')")
        self.query(f"INSERT INTO 'deemon' ('property', 'value') VALUES ('version', '{__dbversion__}')")
        self.query("INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('latest_ver', '')")
        self.query("INSERT INTO 'deemon' ('property', 'value') VALUES ('last_update_check', 0)")
        self.query(f"INSERT INTO 'deemon' ('property', 'value') "
                   f"VALUES ('release_channel', '{config['app']['release_channel']}')")
        self.query("INSERT INTO 'profiles' ('name') VALUES ('default')")
        self.commit()

    def get_latest_ver(self):
        return self.query("SELECT value FROM deemon WHERE property = 'latest_ver'").fetchone()['value']

    def get_db_version(self):
        version = self.query(f"SELECT value FROM deemon WHERE property = 'version'").fetchone()['value']
        logger.debug(f"Database version {version}")
        return version

    def do_upgrade(self):
        current_ver = parse_version(self.get_db_version())
        app_db_version = parse_version(__dbversion__)

        if current_ver == app_db_version:
            return

        logger.warning("DATABASE UPGRADE IN PROGRESS! PLEASE WAIT...")
        logger.warning(f"  - Migrating version {current_ver} -> {__dbversion__}")

        if current_ver < parse_version("3.6"):
            logger.error("Unsupported upgrade path. Please upgrade to at least v2.8 first.")
            
        if current_ver == parse_version("3.6"):
            logger.warning("  - Upgrading `monitor` table, this may take some time")
            self.query("CREATE TABLE monitor_temp AS SELECT * FROM monitor")
            logger.warning("  - Converting record types to new format")
            self.query("UPDATE 'monitor_temp' SET record_type = 1 WHERE record_type = 'single'")
            self.query("UPDATE 'monitor_temp' SET record_type = 2 WHERE record_type = 'ep'")
            self.query("UPDATE 'monitor_temp' SET record_type = 4 WHERE record_type = 'album'")
            self.query("UPDATE 'monitor_temp' SET record_type = 7 WHERE record_type = 'all'")
            self.query("DROP TABLE monitor")
            self.query("CREATE TABLE monitor ("
                       "'id' INTEGER,"
                       "'name' TEXT,"
                       "'bitrate' TEXT,"
                       "'record_type' INTEGER,"
                       "'alerts' INTEGER,"
                       "'profile_id' INTEGER DEFAULT 1,"
                       "'download_path' TEXT,"
                       "'trans_id' INTEGER,"
                       "CONSTRAINT unique_artist UNIQUE (id, profile_id)"
                       "ON CONFLICT IGNORE)")
            self.query("INSERT INTO monitor ("
                       "id, name, bitrate, record_type,"
                       "alerts, profile_id, download_path, trans_id) "
                       "SELECT artist_id, artist_name, bitrate, record_type,"
                       "alerts, profile_id, download_path, trans_id FROM monitor_temp")
            logger.warning("  - Upgrading `playlist` table, this may take some time")
            self.query("CREATE TABLE playlists_temp AS SELECT * FROM playlists")
            self.query("DROP TABLE playlists")
            self.query("CREATE TABLE playlists ("
                       "'id' INTEGER UNIQUE,"
                       "'title' TEXT,"
                       "'url' TEXT,"
                       "'bitrate' TEXT,"
                       "'alerts' INTEGER,"
                       "'profile_id' INTEGER DEFAULT 1,"
                       "'download_path' TEXT,"
                       "'trans_id' INTEGER,"
                       "CONSTRAINT unique_playlist UNIQUE (id, profile_id)"
                       "ON CONFLICT IGNORE)")
            self.query("INSERT INTO playlists ("
                       "id, title, url, bitrate, alerts,"
                       "profile_id, download_path, trans_id) "
                       "SELECT id, title, url, bitrate, alerts,"
                       "profile_id, download_path, trans_id FROM playlists_temp")
            logger.warning("  - Creating `queue` table")
            self.query("CREATE TABLE queue ("
                       "'artist_name'	TEXT,"
                       "'album_id'	INTEGER,"
                       "'album_title'	TEXT,"
                       "'track_id'	INTEGER,"
                       "'track_title'	TEXT,"
                       "'url'	TEXT,"
                       "'playlist_title'	TEXT,"
                       "'bitrate'	TEXT,"
                       "'download_path'	TEXT,"
                       "'profile_id'	INTEGER,"
                       "UNIQUE (url, profile_id) "
                       "ON CONFLICT IGNORE)")
            logger.warning("  - Creating `pending_artist_refresh` table")
            self.query("CREATE TABLE pending_artist_refresh ("
                       "id INTEGER NOT NULL,"
                       "profile_id INTEGER NOT NULL,"
                       "UNIQUE (id, profile_id)"
                       " ON CONFLICT IGNORE,"
                       "FOREIGN KEY (id, profile_id) "
                       "REFERENCES monitor (id, profile_id)"
                       "ON DELETE CASCADE)")
            logger.warning("  - Upgrading `releases` table, this may take some time")
            self.query("CREATE TABLE releases_temp AS SELECT * FROM releases")
            logger.warning("  - Converting record types to new format")
            self.query("UPDATE 'releases_temp' SET record_type = 1 WHERE record_type = 'single'")
            self.query("UPDATE 'releases_temp' SET record_type = 2 WHERE record_type = 'ep'")
            self.query("UPDATE 'releases_temp' SET record_type = 4 WHERE record_type = 'album'")
            self.query("DROP TABLE releases")
            self.query("CREATE TABLE releases ("
                       "'artist_id' INTEGER,"
                       "'artist_name' TEXT,"
                       "'album_id' INTEGER,"
                       "'album_name' TEXT,"
                       "'album_release' TEXT,"
                       "'album_added' INTEGER,"
                       "'explicit' INTEGER,"
                       "'label' TEXT,"
                       "'record_type' INTEGER,"
                       "'profile_id' INTEGER DEFAULT 1,"
                       "'trans_id' INTEGER,"
                       "unique(album_id, profile_id),"
                       "FOREIGN KEY (artist_id, profile_id) "
                       "REFERENCES monitor (id, profile_id) "
                       "ON DELETE CASCADE)")
            logger.warning("  - Copying releases to new `releases` table")
            self.query("INSERT INTO releases ("
                       "artist_id, artist_name, album_id, album_name,"
                       "album_release, album_added, explicit, label,"
                       "record_type, profile_id, trans_id) "
                       "SELECT artist_id, artist_name, album_id, album_name,"
                       "album_release, album_added, explicit, label,"
                       "record_type, profile_id, trans_id FROM releases_temp "
                       "WHERE future_release = 0")
            logger.warning("  - Creating `future_releases` table")
            self.query("CREATE TABLE future_releases ("
                       "'artist_id' INTEGER,"
                       "'artist_name' TEXT,"
                       "'album_id' INTEGER,"
                       "'album_name' TEXT,"
                       "'album_release' TEXT,"
                       "'album_added' INTEGER,"
                       "'explicit' INTEGER,"
                       "'label' TEXT,"
                       "'record_type' INTEGER,"
                       "'profile_id' INTEGER DEFAULT 1,"
                       "'trans_id' INTEGER,"
                       "unique(album_id, profile_id),"
                       "FOREIGN KEY (artist_id, profile_id) "
                       "REFERENCES monitor (id, profile_id) "
                       "ON DELETE CASCADE)")
            logger.warning("  - Copying future releases to new `future_releases` table")
            self.query("INSERT INTO future_releases ("
                       "artist_id, artist_name, album_id, album_name,"
                       "album_release, album_added, explicit, label,"
                       "record_type, profile_id, trans_id) "
                       "SELECT artist_id, artist_name, album_id, album_name,"
                       "album_release, album_added, explicit, label,"
                       "record_type, profile_id, trans_id FROM releases_temp "
                       "WHERE future_release = 1")
            logger.warning("  - Cleaning up database")
            self.query("DROP TABLE monitor_temp")
            self.query("DROP TABLE playlists_temp")
            self.query("DROP TABLE releases_temp")
            self.query(f"INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('version', '{__dbversion__}')")
            self.commit()
            logger.warning(f"Database has been upgraded to version {__dbversion__}")
            print("Starting deemon, please wait...")
            time.sleep(3)
            ui.clear()

    def query(self, query, values=None):
        if values is None:
            values = {}
        return self.cursor.execute(query, values)

    def reset_future(self, album_id):
        logger.debug("Clearing future_release flag from " + str(album_id))
        values = {'album_id': album_id, 'profile_id': config.profile}
        sql = "UPDATE 'releases' SET future_release = 0 WHERE album_id = :album_id AND profile_id = :profile_id"
        self.query(sql, values)

    def get_all_monitored_artists(self):
        vals = {'profile_id': config.profile}
        return self.query(f"SELECT * FROM monitor WHERE profile_id = :profile_id "
                          f"ORDER BY name COLLATE NOCASE ASC", vals).fetchall()

    def get_monitored_artist_by_id(self, artist_id: int):
        values = {'id': artist_id, 'profile_id': config.profile}
        return self.query(f"SELECT * FROM monitor WHERE id = :id AND profile_id = :profile_id",
                          values).fetchone()

    def get_monitored_artist_by_name(self, name):
        values = {'name': name, 'profile_id': config.profile}
        return self.query(f"SELECT * FROM monitor WHERE name = :name COLLATE NOCASE "
                          f"AND profile_id = :profile_id", values).fetchone()

    def get_all_monitored_playlist_ids(self):
        vals = {'profile_id': config.profile}
        query = self.query("SELECT id FROM playlists WHERE profile_id = :profile_id", vals).fetchall()
        return [v for x in query for v in x.values()]

    def get_all_monitored_playlists(self):
        vals = {'profile_id': config.profile}
        return self.query("SELECT * FROM playlists WHERE profile_id = :profile_id "
                          "ORDER BY title COLLATE NOCASE ASC", vals).fetchall()

    def get_monitored_playlist_by_id(self, playlist_id):
        values = {'id': playlist_id, 'profile_id': config.profile}
        return self.query("SELECT * FROM playlists WHERE id = :id AND profile_id = :profile_id", values).fetchone()

    def get_monitored_playlist_by_name(self, title):
        values = {'title': title, 'profile_id': config.profile}
        return self.query("SELECT * FROM playlists WHERE title = :title COLLATE NOCASE "
                          "AND profile_id = :profile_id", values).fetchone()

    def monitor_artist(self, artist: dict, artist_config: dict):
        self.new_transaction()
        vals = {
            'id': artist['id'], 'name': artist['name'], 'bitrate': artist_config['bitrate'],
            'record_type': artist_config['record_type'], 'alerts': artist_config['alerts'],
            'download_path': artist_config['download_path'], 'profile_id': config.profile,
            'trans_id': self.transaction_id
        }
        query = ("INSERT INTO monitor "
                 "(id, name, bitrate, record_type, alerts, download_path, profile_id, trans_id) "
                 "VALUES "
                 f"(:id, :name, :bitrate, :record_type, :alerts, :download_path, :profile_id,  {self.transaction_id})")
        self.query(query, vals)
        self.commit()

    def get_artist_releases(self, artist_id=None):
        sql_values = {'artist_id': artist_id, 'profile_id': config.profile}
        if artist_id:
            query = "SELECT album_id, album_release FROM 'releases' " \
                    "WHERE artist_id = :artist_id AND profile_id = :profile_id"
        else:
            query = "SELECT album_id, album_release FROM 'releases' WHERE profile_id = :profile_id"
        return self.query(query, sql_values).fetchall()

    def get_future_releases(self):
        vals = {'profile_id': config.profile}
        return self.query("SELECT * FROM future_releases WHERE profile_id = :profile_id", vals).fetchall()

    def get_playlist_tracks(self, playlist_id):
        sql_values = {'playlist_id': playlist_id, 'profile_id': config.profile}
        query = "SELECT * FROM 'playlist_tracks' WHERE playlist_id = :playlist_id AND profile_id = :profile_id"
        return self.query(query, sql_values).fetchall()

    def get_track_from_playlist(self, playlist_id, track_id):
        values = {'pid': playlist_id, 'tid': track_id, 'profile_id': config.profile}
        query = "SELECT * FROM 'playlist_tracks' WHERE track_id = :tid AND playlist_id = :pid AND profile_id = :profile_id"
        result = self.query(query, values).fetchone()
        if result:
            return True

    def monitor_playlist(self, api_result):
        self.new_transaction()
        values = {'id': api_result['id'], 'title': api_result['title'], 'url': api_result['link'],
                  'bitrate': api_result['bitrate'], 'alerts': api_result['alerts'],
                  'download_path': api_result['download_path'], 'profile_id': config.profile,
                  'trans_id': self.transaction_id}
        query = ("INSERT INTO playlists ('id', 'title', 'url', 'bitrate', 'alerts', 'download_path',"
                 "'profile_id', 'trans_id') "
                 f"VALUES (:id, :title, :url, :bitrate, :alerts, :download_path, :profile_id, {self.transaction_id})")
        self.query(query, values)
        self.commit()

    def remove_monitored_artist(self, id: int = None):
        values = {'id': id, 'profile_id': config.profile}
        self.query("DELETE FROM monitor WHERE id = :id AND profile_id = :profile_id", values)
        self.query("DELETE FROM releases WHERE artist_id = :id AND profile_id = :profile_id", values)
        self.commit()

    def remove_monitored_playlists(self, id: int = None):
        values = {'id': id, 'profile_id': config.profile}
        self.query("DELETE FROM playlists WHERE id = :id AND profile_id = :profile_id", values)
        self.query("DELETE FROM playlist_tracks WHERE playlist_id = :id AND profile_id = :profile_id", values)
        self.commit()

    def get_specified_artist(self, artist):
        values = {'artist': artist, 'profile_id': config.profile}
        if type(artist) is int:
            return self.query("SELECT * FROM monitor WHERE id = :artist "
                              "AND profile_id = :profile_id", values).fetchone()
        else:
            return self.query("SELECT * FROM monitor WHERE name = ':artist' "
                              "AND profile_id = :profile_id COLLATE NOCASE", values).fetchone()

    def add_new_releases(self, values):
        self.new_transaction()
        sql = (f"INSERT OR REPLACE INTO releases ("
               f"'artist_id', 'artist_name', 'album_id', 'album_name', 'album_release', "
               f"'album_added', 'explicit', 'record_type', 'profile_id', 'trans_id') "
               f"VALUES (:artist_id, :artist_name, :id, :title, :release_date, {int(time.time())}, "
               f":explicit_lyrics, :record_type, {config.profile}, {self.transaction_id})")
        self.cursor.executemany(sql, values)

    def add_new_playlist_releases(self, values):
        self.new_transaction()
        sql = (f"INSERT INTO playlist_tracks ('artist_id', 'artist_name', 'track_id', 'track_name', 'playlist_id', "
               f"'track_added', 'profile_id', 'trans_id') VALUES (:artist_id, :artist_name, :id, :title, :playlist_id, "
               f"{int(time.time())}, {config.profile}, {self.transaction_id})")
        self.cursor.executemany(sql, values)

    def show_new_releases(self, from_date_ts, now_ts):
        today_date = datetime.utcfromtimestamp(now_ts).strftime('%Y-%m-%d')
        from_date = datetime.utcfromtimestamp(from_date_ts).strftime('%Y-%m-%d')
        values = {'from': from_date, 'today': today_date, 'profile_id': config.profile}
        sql = "SELECT * FROM 'releases' WHERE album_release >= :from AND album_release <= :today AND profile_id = :profile_id"
        return self.query(sql, values).fetchall()

    def get_album_by_id(self, album_id):
        values = {'id': album_id, 'profile_id': config.profile}
        sql = "SELECT * FROM 'releases' WHERE album_id = :id AND profile_id = :profile_id"
        return self.query(sql, values).fetchone()

    def reset_database(self):
        self.query("DELETE FROM monitor")
        self.query("DELETE FROM releases")
        self.query("DELETE FROM playlists")
        self.query("DELETE FROM playlist_tracks")
        self.query("DELETE FROM transactions")
        self.query("DELETE FROM pending_artist_refresh")
        self.query("DELETE FROM future_releases")
        self.query("DELETE FROM queue")
        self.commit()
        logger.info("Database has been reset")

    def update_artist(self, settings: dict):
        self.query("UPDATE monitor SET bitrate = :bitrate, alerts = :alerts, record_type = :record_type,"
                   "download_path = :download_path WHERE id = :artist_id AND profile_id = :profile_id", settings)
        self.commit()

    def add_playlist_track(self, playlist, track):
        self.new_transaction()
        values = {'pid': playlist['id'], 'tid': track['id'], 'tname': track['title'], 'aid': track['artist']['id'],
                  'aname': track['artist']['name'], 'time': int(time.time()), 'profile_id': config.profile,
                  'trans_id': self.transaction_id}
        query = ("INSERT INTO 'playlist_tracks' "
                 "('track_id', 'playlist_id', 'artist_id', 'artist_name', 'track_name', 'track_added', 'profile_id',"
                 f"'trans_id') VALUES (:tid, :pid, :aid, :aname, :tname, :time, :profile_id, {self.transaction_id})")
        return self.query(query, values)

    def create_profile(self, settings: dict):
        self.query("INSERT INTO profiles (name, email, alerts, bitrate, record_type, plex_baseurl, plex_token,"
                   "plex_library, download_path) VALUES (:name, :email, :alerts, :bitrate, :record_type,"
                   ":plex_baseurl, :plex_token, :plex_library, :download_path)", settings)
        self.commit()

    def delete_profile(self, profile_name: str):
        profile = self.get_profile(profile_name)
        vals = {'profile_id': profile['id']}
        self.query("DELETE FROM monitor WHERE profile_id = :profile_id", vals)
        self.query("DELETE FROM releases WHERE profile_id = :profile_id", vals)
        self.query("DELETE FROM playlists WHERE profile_id = :profile_id", vals)
        self.query("DELETE FROM playlist_tracks WHERE profile_id = :profile_id", vals)
        self.query("DELETE FROM profiles WHERE id = :profile_id", vals)
        self.commit()

    def get_all_profiles(self):
        return self.query("SELECT * FROM profiles").fetchall()

    def get_profile(self, profile_name: str):
        vals = {'profile': profile_name}
        return self.query("SELECT * FROM profiles WHERE name = :profile COLLATE NOCASE", vals).fetchone()

    def get_profile_by_id(self, profile_id: int):
        vals = {'profile_id': profile_id}
        return self.query("SELECT * FROM profiles WHERE id = :profile_id", vals).fetchone()

    def update_profile(self, settings: dict):
        self.query("UPDATE profiles SET name = :name, email = :email, alerts = :alerts, bitrate = :bitrate,"
                   "record_type = :record_type, plex_baseurl = :plex_baseurl, plex_token = :plex_token,"
                   "plex_library = :plex_library, download_path = :download_path "
                   "WHERE id = :id", settings)
        self.commit()

    def last_update_check(self):
        return self.query("SELECT value FROM 'deemon' WHERE property = 'last_update_check'").fetchone()['value']

    def set_last_update_check(self):
        now = int(time.time())
        self.query(f"UPDATE deemon SET value = {now} WHERE property = 'last_update_check'")
        self.commit()

    def get_next_transaction_id(self):
        tid = self.query(f"SELECT seq FROM sqlite_sequence WHERE name = 'transactions'").fetchone()
        if not tid:
            return 0
        return tid['seq'] + 1

    def new_transaction(self):
        check_exists = self.query(f"SELECT * FROM transactions WHERE id = {self.transaction_id}").fetchone()
        if not check_exists:
            current_time = int(time.time())
            vals = {'timestamp': current_time, 'profile_id': config.profile}
            self.query(f"INSERT INTO transactions ('timestamp', 'profile_id') "
                       f"VALUES (:timestamp, :profile_id)", vals)
            self.commit()

    def rollback_last_refresh(self, rollback: int):
        vals = {'rollback': rollback, 'profile_id': config.profile}
        transactions = self.query("SELECT id FROM transactions WHERE profile_id = :profile_id "
                                  f"ORDER BY id DESC LIMIT {rollback}", vals).fetchall()
        for t in transactions:
            vals = {'id': t['id'], 'profile_id': config.profile}
            self.query(f"DELETE FROM monitor WHERE trans_id = :id AND profile_id = :profile_id", vals)
            self.query(f"DELETE FROM releases WHERE trans_id = :id AND profile_id = :profile_id", vals)
            self.query(f"DELETE FROM playlist_tracks WHERE trans_id = :id AND profile_id = :profile_id", vals)
            self.query(f"DELETE FROM transactions WHERE id = :id AND profile_id = :profile_id", vals)
            self.commit()

    def rollback_refresh(self, rollback: int):
        vals = {'rollback': rollback, 'profile_id': config.profile}
        self.query(f"DELETE FROM monitor WHERE trans_id = {rollback} AND profile_id = :profile_id", vals)
        self.query(f"DELETE FROM releases WHERE trans_id = {rollback} AND profile_id = :profile_id", vals)
        self.query(f"DELETE FROM playlist_tracks WHERE trans_id = {rollback} AND profile_id = :profile_id", vals)
        self.query(f"DELETE FROM transactions WHERE id = {rollback} AND profile_id = :profile_id", vals)
        self.commit()

    def set_latest_version(self, version):
        vals = {'version': version}
        self.query("INSERT OR REPLACE INTO deemon (property, value) VALUES ('latest_ver', :version)", vals)
        return self.commit()

    def get_release_channel(self):
        return self.query("SELECT value FROM deemon WHERE property = 'release_channel'").fetchone()

    def set_release_channel(self):
        self.query(f"INSERT OR REPLACE INTO deemon (property, value) "
                   f"VALUES ('release_channel', '{config.release_channel}')")
        return self.commit()

    def get_transactions(self):
        vals = {'profile_id': config.profile, 'trans_limit': config.rollback_view_limit}
        transaction_list = self.query("SELECT id, timestamp FROM transactions WHERE profile_id = :profile_id "
                                      "ORDER BY id DESC LIMIT :trans_limit", vals).fetchall()
        results = []
        for tid in transaction_list:
            vals = {'tid': tid['id'], 'profile_id': config.profile}
            transaction = {}
            transaction['id'] = tid['id']
            transaction['timestamp'] = tid['timestamp']
            transaction['releases'] = self.query("SELECT album_id "
                                                 "FROM releases "
                                                 "WHERE trans_id = :tid "
                                                 "AND profile_id = :profile_id", vals).fetchall()
            transaction['playlist_tracks'] = self.query("SELECT track_id "
                                                        "FROM playlist_tracks "
                                                        "WHERE trans_id = :tid "
                                                        "AND profile_id = :profile_id", vals).fetchall()
            transaction['playlists'] = self.query("SELECT title "
                                                  "FROM playlists "
                                                  "WHERE trans_id = :tid "
                                                  "AND profile_id = :profile_id", vals).fetchall()
            transaction['monitor'] = self.query("SELECT name "
                                                "FROM monitor "
                                                "WHERE trans_id = :tid "
                                                "AND profile_id = :profile_id", vals).fetchall()
            results.append(transaction)
        return results

    def get_all_monitored_artist_ids(self):
        values = {"profile_id": config.profile}
        query = self.query("SELECT id FROM monitor WHERE profile_id = :profile_id", values).fetchall()
        return [v for x in query for v in x.values()]

    @performance.timeit
    def get_monitored(self):
        values = {"profile_id": config.profile}
        query = self.query("SELECT id, name FROM monitor WHERE profile_id = :profile_id",
                           values).fetchall()
        return query

    def fast_monitor(self, values):
        self.new_transaction()
        self.cursor.executemany("INSERT OR REPLACE INTO monitor ("
                                "id, name, bitrate, record_type,"
                                "alerts, profile_id, download_path) "
                                "VALUES (:id, :name, :bitrate, :record_type, :alerts,"
                                ":profile_id, :download_path)", values)

        self.cursor.executemany("INSERT OR REPLACE INTO pending_artist_refresh ("
                                "id, profile_id) "
                                "VALUES (:id, :profile_id)", values)

    def fast_monitor_playlist(self, values):
        # TODO FIX THIS
        self.new_transaction()
        self.cursor.executemany("INSERT OR REPLACE INTO playlists ("
                                "id, title, url, bitrate, alerts, profile_id,"
                                "download_path, trans_id) "
                                "VALUES (:id, :name, :link, :bitrate, :alerts,"
                                f":profile_id, :download_path, {self.transaction_id})", values)

        self.cursor.executemany("INSERT OR REPLACE INTO pending_artist_refresh ("
                                "id, name, profile_id, playlist) "
                                "VALUES (:id, :name, :profile_id, 1)", values)

    def remove_by_name(self, values):
        self.cursor.executemany(f"DELETE FROM monitor WHERE profile_id = {config.profile} AND name = ?",
                                values)
        self.cursor.executemany(f"DELETE FROM releases WHERE profile_id = {config.profile} AND artist_name = ?",
                                values)
        self.commit()

    def remove_by_id(self, values):
        self.cursor.executemany(f"DELETE FROM monitor WHERE profile_id = {config.profile} AND id = ?",
                                values)
        self.cursor.executemany(f"DELETE FROM releases WHERE profile_id = {config.profile} AND artist_id = ?",
                                values)
        self.commit()

    # @performance.timeit
    def remove_specific_releases(self, values):
        self.query(f"DELETE FROM releases WHERE album_release > :tm_date AND profile_id = {config.profile}", values)

    def add_extra_release_info(self, values):
        self.new_transaction()
        sql = ("UPDATE releases SET label = :label WHERE album_id = :id AND "
               f"profile_id = {config.profile}")
        self.cursor.executemany(sql, values)

    def get_pending_artist_refresh(self):
        values = {'profile_id': config.profile}
        return self.query("SELECT m.* FROM pending_artist_refresh AS p "
                          "INNER JOIN monitor AS m "
                          "ON p.id = m.id "
                          "WHERE p.profile_id = :profile_id", values).fetchall()

    def get_release_ids(self):
        values = {'profile_id': config.profile}
        return self.query("SELECT album_id FROM releases WHERE profile_id = :profile_id", values).fetchall()

    def remove_future_release(self, values):
        self.cursor.executemany("DELETE FROM future_releases "
                                "WHERE album_id = :album_id AND profile_id = :profile_id", values)

    def update_future_release(self, values):
        values['profile_id'] = config.profile
        self.query("INSERT OR REPLACE INTO future_releases (album_id, album_release, profile_id) "
                   "VALUES (:id, :release_date, :profile_id)", values)

    def save_holding_queue(self, values):
        self.cursor.executemany("INSERT OR REPLACE INTO queue (artist_name, album_id, album_title, track_id,"
                                "track_title, url, playlist_title, bitrate, download_path, profile_id) "
                                "VALUES (:artist_name, :album_id, :album_title, :track_id, :track_title, :url,"
                                f":playlist_title, :bitrate, :download_path, "
                                f"{config.profile})", values)

    def drop_all_pending_artists(self):
        self.query("DELETE FROM pending_artist_refresh")
