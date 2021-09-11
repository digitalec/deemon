from deemon import __dbversion__
from deemon.core.config import Config as config
from deemon.utils import startup
from packaging.version import parse as parse_version
from datetime import datetime
from pathlib import Path
import logging
import sqlite3
import time

logger = logging.getLogger(__name__)


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
        logger.debug("Saving changes to DB")
        self.commit()
        self.close()

    def create_new_database(self):
        logger.debug("DATABASE CREATION IN PROGRESS!")

        self.query("CREATE TABLE monitor ("
                   "'artist_id' INTEGER,"
                   "'artist_name' TEXT,"
                   "'bitrate' INTEGER,"
                   "'record_type' TEXT,"
                   "'alerts' INTEGER,"
                   "'profile_id' INTEGER DEFAULT 1,"
                   "'download_path' TEXT)")

        self.query("CREATE TABLE playlists ("
                   "'id' INTEGER UNIQUE,"
                   "'title' TEXT,"
                   "'url' TEXT,"
                   "'bitrate' INTEGER,"
                   "'alerts' INTEGER,"
                   "'profile_id' INTEGER DEFAULT 1,"
                   "'download_path' TEXT)")

        self.query("CREATE TABLE playlist_tracks ("
                   "'track_id' INTEGER,"
                   "'playlist_id' INTEGER,"
                   "'artist_id' INTEGER,"
                   "'artist_name' TEXT,"
                   "'track_name' TEXT,"
                   "'profile_id' INTEGER DEFAULT 1,"
                   "'track_added' TEXT)")

        self.query("CREATE TABLE releases ("
                   "'artist_id' INTEGER,"
                   "'artist_name' TEXT,"
                   "'album_id' INTEGER,"
                   "'album_name' TEXT,"
                   "'album_release' TEXT,"
                   "'album_added' INTEGER,"
                   "'explicit' INTEGER,"
                   "'profile_id' INTEGER DEFAULT 1,"
                   "'future_release' INTEGER DEFAULT 0)")

        self.query("CREATE TABLE 'deemon' ("
                   "'property' TEXT,"
                   "'value' TEXT)")

        self.query("CREATE TABLE 'profiles' ("
                   "'id' INTEGER,"
                   "'name' TEXT,"
                   "'email' TEXT,"
                   "'alerts' INTEGER,"
                   "'bitrate' INTEGER,"
                   "'record_type' TEXT,"
                   "'plex_baseurl' TEXT,"
                   "'plex_token' TEXT,"
                   "'plex_library' TEXT,"
                   "'download_path' TEXT,"
                   "PRIMARY KEY('id' AUTOINCREMENT))")

        self.query("CREATE UNIQUE INDEX 'idx_property' ON 'deemon' ('property')")
        self.query(f"INSERT INTO 'deemon' ('property', 'value') VALUES ('version', '{__dbversion__}')")
        self.query("INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('latest_ver', '')")
        self.query("INSERT INTO 'deemon' ('property', 'value') VALUES ('last_update_check', 0)")
        self.query("INSERT INTO 'profiles' ('name') VALUES ('default')")
        self.commit()

    def get_latest_ver(self):
        return self.query("SELECT value FROM deemon WHERE property = 'latest_ver'").fetchone()['value']

    def get_db_version(self):
        try:
            version = self.query(f"SELECT value FROM deemon WHERE property = 'version'").fetchone()['value']
        except sqlite3.OperationalError:
            version = '0.0.0'

        logger.debug(f"Database version {version}")
        return version

    def do_upgrade(self):
        current_ver = parse_version(self.get_db_version())
        app_db_version = parse_version(__dbversion__)

        if current_ver == app_db_version:
            return

        logger.debug("DATABASE UPGRADE IN PROGRESS!")
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

        # Upgrade database v1.1 to v1.3
        if current_ver < parse_version("1.3"):
            sql_playlists_1 = "ALTER TABLE playlists ADD COLUMN bitrate INTEGER"
            sql_playlists_2 = "ALTER TABLE playlists ADD COLUMN alerts INTEGER"
            sql_updatever = "INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('version', '1.3')"
            self.query(sql_playlists_1)
            self.query(sql_playlists_2)
            self.query(sql_updatever)
            self.commit()

        if current_ver < parse_version("2.1"):
            self.query("INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('last_update_check', 0)")
            self.query("INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('version', '2.1')")
            self.commit()

        if current_ver < parse_version("2.2"):
            self.query("ALTER TABLE monitor ADD COLUMN download_path TEXT")
            self.query("ALTER TABLE playlists ADD COLUMN download_path TEXT")
            self.query("INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('version', '2.2')")
            self.commit()

        # Upgrade database to v3
        if current_ver < parse_version("3.0"):
            self.query("CREATE TABLE 'profiles' ("
                       "'id' INTEGER,"
                       "'name' TEXT,"
                       "'email' TEXT,"
                       "'alerts' INTEGER,"
                       "'bitrate' INTEGER,"
                       "'record_type' TEXT,"
                       "'plex_baseurl' TEXT,"
                       "'plex_token' TEXT,"
                       "'plex_library' TEXT,"
                       "'download_path' TEXT,"
                       "PRIMARY KEY('id' AUTOINCREMENT))")
            self.query("INSERT INTO 'profiles' ('name') VALUES ('default')")
            self.query("ALTER TABLE monitor ADD COLUMN profile_id INTEGER DEFAULT 1")
            self.query("ALTER TABLE releases ADD COLUMN profile_id INTEGER DEFAULT 1")
            self.query("ALTER TABLE playlists ADD COLUMN profile_id INTEGER DEFAULT 1")
            self.query("ALTER TABLE playlist_tracks ADD COLUMN profile_id INTEGER DEFAULT 1")
            self.query("CREATE TABLE monitor_tmp ("
                       "'artist_id' INTEGER,"
                       "'artist_name' TEXT,"
                       "'bitrate' TEXT,"
                       "'record_type' TEXT,"
                       "'alerts' INTEGER,"
                       "'download_path' TEXT,"
                       "'profile_id' INTEGER DEFAULT 1)")
            self.query("INSERT INTO monitor_tmp SELECT * FROM monitor")
            self.query("DROP TABLE monitor")
            self.query("ALTER TABLE monitor_tmp RENAME TO monitor")
            self.query("INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('latest_ver', '')")
            self.query("INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('version', '3.0')")
            self.commit()
            logger.debug(f"Database upgraded to version 3.0")

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
        vals = {'profile_id': config.profile_id()}
        return self.query(f"SELECT * FROM monitor WHERE profile_id = :profile_id ORDER BY artist_name", vals).fetchall()

    def get_monitored_artist_by_id(self, artist_id: int):
        values = {'id': artist_id, 'profile_id': config.profile_id()}
        return self.query(f"SELECT * FROM monitor WHERE artist_id = :id AND profile_id = :profile_id", values).fetchone()

    def get_monitored_artist_by_name(self, name: str):
        values = {'name': name, 'profile_id': config.profile_id()}
        return self.query(f"SELECT * FROM monitor WHERE artist_name = :name COLLATE NOCASE "
                          f"AND profile_id = :profile_id", values).fetchone()

    def remove_monitored_artist(self, id: int = None, name: str = None):
        values = {'id': id, 'name': name, 'profile_id': config.profile_id()}
        self.query("DELETE FROM monitor WHERE artist_id = :id AND profile_id = :profile_id", values)
        self.query("DELETE FROM releases WHERE artist_id = :id AND profile_id = :profile_id", values)
        self.commit()

    def remove_monitored_playlists(self, id: int = None, title: str = None):
        values = {'id': id, 'title': title, 'profile_id': config.profile_id()}
        self.query("DELETE FROM playlists WHERE id = :id AND profile_id = :profile_id", values)
        self.query("DELETE FROM playlist_tracks WHERE playlist_id = :id AND profile_id = :profile_id", values)
        self.commit()

    def get_specified_artist(self, artist):
        values = {'artist': artist, 'profile_id': config.profile_id()}
        if type(artist) is int:
            return self.query("SELECT * FROM monitor WHERE artist_id = :artist "
                              "AND profile_id = :profile_id", values).fetchone()
        else:
            return self.query("SELECT * FROM monitor WHERE artist_name = ':artist' "
                              "AND profile_id = :profile_id COLLATE NOCASE", values).fetchone()

    def add_new_release(self, artist_id, artist_name, album_id, album_name, release_date, future_release):
        timestamp = int(time.time())
        values = {'artist_id': artist_id, 'artist_name': artist_name, 'album_id': album_id,
                  'album_name': album_name, 'release_date': release_date, 'future': future_release,
                  'profile_id': config.profile_id()}
        sql = (f"INSERT INTO releases ('artist_id', 'artist_name', 'album_id', "
               f"'album_name', 'album_release', 'album_added', 'future_release', 'profile_id') "
               f"VALUES (:artist_id, :artist_name, :album_id, :album_name, "
               f":release_date, {timestamp}, :future, :profile_id)")
        self.query(sql, values)

    def show_new_releases(self, from_date_ts, now_ts):
        today_date = datetime.utcfromtimestamp(now_ts).strftime('%Y-%m-%d')
        from_date = datetime.utcfromtimestamp(from_date_ts).strftime('%Y-%m-%d')
        values = {'from': from_date, 'today': today_date, 'profile_id': config.profile_id()}
        sql = "SELECT * FROM 'releases' WHERE album_release >= :from AND album_release <= :today AND profile_id = :profile_id"
        return self.query(sql, values).fetchall()

    def get_artist_by_id(self, artist_id):
        values = {'id': artist_id, 'profile_id': config.profile_id()}
        sql = "SELECT * FROM 'releases' WHERE artist_id = :id AND profile_id = :profile_id"
        return self.query(sql, values).fetchone()

    def get_album_by_id(self, album_id):
        values = {'id': album_id, 'profile_id': config.profile_id()}
        sql = "SELECT * FROM 'releases' WHERE album_id = :id AND profile_id = :profile_id"
        return self.query(sql, values).fetchone()

    def monitor_playlist(self, playlist):
        values = {'id': playlist['id'], 'title': playlist['title'],
                  'url': playlist['link'], 'profile_id': config.profile_id()}
        sql = "INSERT OR REPLACE INTO playlists ('id', 'title', 'url', 'profile_id') VALUES (:id, :title, :url, :profile_id)"
        self.query(sql, values)
        self.commit()

    def get_all_monitored_playlists(self):
        vals = {'profile_id': config.profile_id()}
        return self.query("SELECT * FROM playlists WHERE profile_id = :profile_id", vals)

    def get_monitored_playlist_by_id(self, playlist_id):
        values = {'id': playlist_id, 'profile_id': config.profile_id()}
        return self.query("SELECT * FROM playlists WHERE id = :id AND profile_id = :profile_id", values).fetchone()

    def get_monitored_playlist_by_name(self, title):
        values = {'title': title, 'profile_id': config.profile_id()}
        return self.query("SELECT * FROM playlists WHERE title = :title COLLATE NOCASE "
                          "AND profile_id = :profile_id", values).fetchone()

    def reset_database(self):
        self.query("DELETE FROM monitor")
        self.query("DELETE FROM releases")
        self.query("DELETE FROM playlists")
        self.query("DELETE FROM playlist_tracks")
        self.commit()
        logger.info("Database has been reset")

    def last_update_check(self):
        return self.query("SELECT value FROM 'deemon' WHERE property = 'last_update_check'").fetchone()['value']

    def set_last_update_check(self):
        now = int(time.time())
        self.query(f"UPDATE deemon SET value = {now} WHERE property = 'last_update_check'")
        self.commit()

    def get_profile(self, profile_name: str):
        vals = {'profile': profile_name}
        return self.query("SELECT * FROM profiles WHERE name = :profile COLLATE NOCASE", vals).fetchone()

    def get_profile_by_id(self, profile_id: int):
        vals = {'profile_id': profile_id}
        return self.query("SELECT * FROM profiles WHERE id = :profile_id", vals).fetchone()

    def update_artist(self, settings: dict):
        self.query("UPDATE monitor SET bitrate = :bitrate, alerts = :alerts, record_type = :record_type,"
                   "download_path = :download_path WHERE artist_id = :artist_id AND profile_id = :profile_id", settings)
        self.commit()

    def update_profile(self, settings: dict):
        self.query("UPDATE profiles SET name = :name, email = :email, alerts = :alerts, bitrate = :bitrate,"
                   "record_type = :record_type, plex_baseurl = :plex_baseurl, plex_token = :plex_token,"
                   "plex_library = :plex_library, download_path = :download_path "
                   "WHERE id = :id", settings)
        self.commit()

    def create_profile(self, settings: dict):
        self.query("INSERT INTO profiles (name, email, alerts, bitrate, record_type, plex_baseurl, plex_token,"
                   "plex_library, download_path) VALUES (:name, :email, :alerts, :bitrate, :record_type,"
                   ":plex_baseurl, :plex_token, :plex_library, :download_path)", settings)
        self.commit()

    def delete_profile(self, profile_name: str):
        profile = self.get_profile(profile_name)
        vals = {'profile_id': profile['profile_id']}
        self.query("DELETE FROM monitor WHERE profile_id = :profile_id", vals)
        self.query("DELETE FROM releases WHERE profile_id = :profile_id", vals)
        self.query("DELETE FROM playlists WHERE profile_id = :profile_id", vals)
        self.query("DELETE FROM playlist_tracks WHERE profile_id = :profile_id", vals)
        self.query("DELETE FROM profiles WHERE id = :profile_id", vals)
        self.commit()

    def get_all_profiles(self):
        return self.query("SELECT * FROM profiles").fetchall()
