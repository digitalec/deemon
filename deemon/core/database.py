import logging
import sqlite3
from pathlib import Path

from packaging.version import parse as parse_version

from deemon import config, __dbversion__, __version__, ProfileNotExistError
from deemon.utils import startup, performance, dates

logger = logging.getLogger(__name__)


class Database(object):

    TXN_ID = None

    def __init__(self):
        self.conn = None
        self.cursor = None
        self.db = startup.get_database()

        if not Path(self.db).exists():
            self.connect()
            self.create_next_gen_database()
        else:
            self.connect()
            self.test()

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
            self.conn.execute('PRAGMA foreign_keys = ON')
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

    def create_next_gen_database(self):
        logger.debug("DATABASE CREATION IN PROGRESS!")
        self.create_album_table()
        self.create_album_future_table()
        self.create_artist_table()
        self.create_artist_pending_refresh_table()
        self.create_playlist_table()
        self.create_playlist_pending_refresh_table()
        self.create_playlist_release_table()
        self.create_profile_table()
        self.create_queue_table()
        self.create_settings_table()
        self.create_transactions_table()
        self.query("INSERT INTO profile (name) VALUES ('default')")
        self.commit()
        exit()

    def create_album_table(self):
        self.query("""
            CREATE TABLE album (
            id         INTEGER NOT NULL,
            art_id     INTEGER,
            art_name   VARCHAR,
            alb_id     INTEGER,
            alb_title  VARCHAR,
            alb_date   VARCHAR,
            added_on   INTEGER,
            explicit   BOOLEAN,
            rectype    INTEGER,
            profile_id INTEGER,
            txn_id     INTEGER NOT NULL,
            PRIMARY KEY (
                id
            ),
            UNIQUE (
                alb_id,
                profile_id
            ),
            FOREIGN KEY (
                art_id,
                profile_id
            )
            REFERENCES artist (art_id,
            profile_id) ON DELETE CASCADE,
            FOREIGN KEY (
                profile_id
            )
            REFERENCES profile (id) ON DELETE CASCADE,
            FOREIGN KEY (
                txn_id
            )
            REFERENCES [transaction] (id) ON DELETE CASCADE
        )""")

    def create_album_future_table(self):
        self.query("""
            CREATE TABLE album_future (
            id         INTEGER NOT NULL,
            art_id     INTEGER,
            art_name   VARCHAR,
            alb_id     INTEGER,
            alb_title  VARCHAR,
            alb_date   VARCHAR,
            added_on   INTEGER,
            explicit   BOOLEAN,
            rectype    INTEGER,
            profile_id INTEGER,
            txn_id     INTEGER NOT NULL,
            PRIMARY KEY (
                id
            ),
            UNIQUE (
                art_id,
                profile_id
            ),
            FOREIGN KEY (
                txn_id
            )
            REFERENCES [transaction] (id) ON DELETE CASCADE
        )""")

    def create_artist_table(self):
        self.query("""
            CREATE TABLE artist (
            id         INTEGER NOT NULL,
            art_id     INTEGER,
            art_name   VARCHAR,
            bitrate    VARCHAR,
            rectype    INTEGER,
            notify     BOOLEAN,
            dl_path    VARCHAR,
            profile_id INTEGER,
            txn_id     INTEGER NOT NULL,
            PRIMARY KEY (
                id
            ),
            UNIQUE (
                art_id,
                profile_id
            ),
            FOREIGN KEY (
                txn_id
            )
            REFERENCES [transaction] (id) ON DELETE CASCADE
        )""")

    def create_artist_pending_refresh_table(self):
        self.query("""
            CREATE TABLE artist_pending_refresh (
            id         INTEGER NOT NULL,
            art_id     INTEGER,
            profile_id INTEGER,
            PRIMARY KEY (
                id
            )
        )""")

    def create_playlist_table(self):
        self.query("""
            CREATE TABLE playlist (
            id          INTEGER NOT NULL,
            playlist_id INTEGER,
            title       VARCHAR,
            url         VARCHAR,
            bitrate     VARCHAR,
            notify      BOOLEAN,
            dl_path     VARCHAR,
            profile_id  INTEGER,
            txn_id      INTEGER NOT NULL,
            PRIMARY KEY (
                id
            ),
            UNIQUE (
                playlist_id,
                profile_id
            ),
            FOREIGN KEY (
                txn_id
            )
            REFERENCES [transaction] (id) ON DELETE CASCADE
        )""")

    def create_playlist_pending_refresh_table(self):
        self.query("""
            CREATE TABLE playlist_pending_refresh (
            id          INTEGER NOT NULL,
            playlist_id INTEGER,
            profile_id  INTEGER NOT NULL,
            PRIMARY KEY (
                id
            ),
            FOREIGN KEY (
                profile_id
            )
            REFERENCES profile (id) ON DELETE CASCADE
        )""")

    def create_playlist_release_table(self):
        self.query("""
            CREATE TABLE playlist_release (
            id          INTEGER NOT NULL,
            playlist_id INTEGER,
            art_id      INTEGER,
            art_name    VARCHAR,
            track_id    INTEGER,
            track_name  VARCHAR,
            track_added INTEGER,
            profile_id  INTEGER,
            txn_id      INTEGER NOT NULL,
            PRIMARY KEY (
                id
            ),
            UNIQUE (
                playlist_id,
                track_id,
                profile_id
            ),
            FOREIGN KEY (
                txn_id
            )
            REFERENCES [transaction] (id) ON DELETE CASCADE
        )""")

    def create_profile_table(self):
        self.query("""
            CREATE TABLE profile (
            id           INTEGER NOT NULL,
            name         VARCHAR,
            email        VARCHAR,
            notify       BOOLEAN,
            bitrate      VARCHAR,
            rectype      INTEGER,
            dl_path      VARCHAR,
            plex_url     VARCHAR,
            plex_token   VARCHAR,
            plex_library VARCHAR,
            PRIMARY KEY (
                id
            )
        )""")

    def create_queue_table(self):
        self.query("""
            CREATE TABLE queue (
            id             INTEGER NOT NULL,
            art_id         INTEGER,
            art_name       VARCHAR,
            alb_id         INTEGER,
            alb_title      VARCHAR,
            track_id       INTEGER,
            track_title    VARCHAR,
            url            VARCHAR,
            playlist_title VARCHAR,
            bitrate        VARCHAR,
            dl_path        VARCHAR,
            profile_id     INTEGER,
            txn_id         INTEGER NOT NULL,
            PRIMARY KEY (
                id
            ),
            FOREIGN KEY (
                txn_id
            )
            REFERENCES [transaction] (id) ON DELETE CASCADE
        )""")

    def create_settings_table(self):
        self.query("""
            CREATE TABLE settings (
            id    INTEGER NOT NULL,
            [key] VARCHAR NOT NULL,
            value VARCHAR NOT NULL,
            PRIMARY KEY (
                id
            )
        )""")

    def create_transactions_table(self):
        self.query("""
            CREATE TABLE transactions (
            id         INTEGER NOT NULL,
            timestamp  INTEGER DEFAULT (strftime('%s', 'now')) NOT NULL,
            profile_id INTEGER NOT NULL,
            PRIMARY KEY (
                id
            ),
            FOREIGN KEY (
                profile_id
            )
            REFERENCES profile (id) ON DELETE CASCADE
        )""")

    def init_transaction(self):
        txn = self.cursor.execute(
            "INSERT INTO transactions (profile_id) VALUES (?) RETURNING id",
            str(config.profile_id)
        )
        Database.TXN_ID = txn.fetchone()['id']

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

        if current_ver < parse_version("3.5"):
            logger.error("Due to database changes, you must be on at least "
                         f"v2.5 before upgrading to v{__version__}.")
            exit()

        if current_ver < parse_version("3.5.2"):
            self.query("CREATE TABLE releases_tmp ("
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
                       "'future_release' INTEGER DEFAULT 0,"
                       "'trans_id' INTEGER,"
                       "unique(album_id, profile_id))")
            self.query("INSERT OR REPLACE INTO releases_tmp(artist_id, artist_name, "
                       "album_id, album_name, album_release, album_added, "
                       "explicit, label, record_type, profile_id, "
                       "future_release, trans_id) SELECT artist_id, "
                       "artist_name, album_id, album_name, album_release, "
                       "album_added, explicit, label, record_type, "
                       "profile_id, future_release, trans_id FROM releases")
            self.query("DROP TABLE releases")
            self.query("ALTER TABLE releases_tmp RENAME TO releases")
            self.query("INSERT OR REPLACE INTO 'deemon' ('property', 'value') VALUES ('version', '3.5.2')")
            self.commit()
            logger.debug(f"Database upgraded to version 3.5.2")

        if current_ver < parse_version("3.6"):
            # album_release_ts REMOVED
            pass

    def query(self, query, values=None):
        if values is None:
            values = {}
        return self.cursor.execute(query, values)

    def get_profile_by_id(self, profile_id):
        """
        Returns profile matching profile_id
        """
        stmt = self.query(
            "SELECT * FROM profile WHERE id = ?",
            str(profile_id)
        ).fetchone()

        if stmt is None:
            raise ProfileNotExistError("The profile ID does not exist.")
        else:
            return stmt

    def fast_monitor(self, artists):
        self.cursor.executemany(
            "INSERT OR REPLACE INTO artist ("
            "art_id,"
            "art_name,"
            "bitrate,"
            "rectype,"
            "notify,"
            "dl_path,"
            "profile_id,"
            "txn_id"
            ") VALUES ("
            ":art_id,"
            ":art_name,"
            ":bitrate,"
            ":rectype,"
            ":notify,"
            ":dl_path,"
            ":profile_id,"
            ":txn_id"
        )

    def test(self):
        exit()
