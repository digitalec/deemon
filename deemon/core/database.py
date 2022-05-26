import time
from pathlib import Path

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    select,
    delete,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from deemon import config, __dbversion__, __version__, ProfileNotExistError

Base = declarative_base()


class Settings(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return f"<Settings {self.key}:{self.value}>"


class Artist(Base):
    __tablename__ = 'artist'
    __table_args__ = (
        UniqueConstraint('art_id', 'profile_id'),
    )

    id = Column(Integer, primary_key=True)
    art_id = Column(Integer)
    art_name = Column(String)
    bitrate = Column(String, nullable=True)
    rectype = Column(Integer, nullable=True)
    notify = Column(Boolean, nullable=True)
    dl_path = Column(String, nullable=True)
    profile_id = Column(Integer)
    txn_id = Column(Integer, ForeignKey('transaction.id', ondelete="CASCADE"), nullable=False)
    transaction = relationship("Transaction", back_populates="artist")

    def __init__(self, art_id, art_name, bitrate=None, rectype=None, notify=None, dl_path=None):
        self.art_id = art_id
        self.art_name = art_name
        self.bitrate = bitrate
        self.rectype = rectype
        self.notify = notify
        self.dl_path = dl_path
        self.profile_id = config.profile_id
        self.txn_id = Database.TXN_ID

    def __repr__(self):
        return f"<Artist {self.art_id} {self.art_name} Tx:{self.txn_id} Pr:{self.profile_id}>"


class ArtistPendingRefresh(Base):
    __tablename__ = 'artist_pending_refresh'

    id = Column(Integer, primary_key=True)
    art_id = Column(Integer)
    profile_id = Column(Integer)

    def __init__(self, art_id):
        self.art_id = art_id
        self.profile_id = config.profile_id

    def __repr__(self):
        return f"<ArtistPendingRefresh {self.art_id}>"


class AlbumFuture(Base):
    __tablename__ = 'album_future'
    __table_args__ = (
        UniqueConstraint('art_id', 'profile_id'),
    )

    id = Column(Integer, primary_key=True)
    art_id = Column(Integer)
    art_name = Column(String)
    alb_id = Column(Integer)
    alb_title = Column(String)
    alb_date = Column(String)
    added_on = Column(Integer)
    explicit = Column(Boolean)
    rectype = Column(Integer)
    profile_id = Column(Integer)
    txn_id = Column(Integer, ForeignKey('transaction.id', ondelete="CASCADE"), nullable=False)
    transaction = relationship("Transaction", cascade="delete", back_populates="album_future")

    def __init__(self, art_id, art_name, alb_id, alb_title, alb_date, explicit, rectype):
        self.art_id = art_id
        self.art_name = art_name
        self.alb_id = alb_id
        self.alb_title = alb_title
        self.alb_date = alb_date
        self.added_on = int(time.time())
        self.explicit = explicit
        self.rectype = rectype
        self.profile_id = config.profile_id
        self.txn_id = Database.TXN_ID

    def __repr__(self):
        return f"<AlbumFuture {self.alb_id} {self.txn_id}>"


class Album(Base):
    __tablename__ = 'album'
    __table_args__ = (
        UniqueConstraint('alb_id', 'profile_id'),
    )

    id = Column(Integer, primary_key=True)
    art_id = Column(Integer, ForeignKey('artist.art_id', ondelete="CASCADE"))
    art_name = Column(String)
    alb_id = Column(Integer)
    alb_title = Column(String)
    alb_date = Column(String)
    added_on = Column(Integer)
    explicit = Column(Boolean)
    rectype = Column(Integer)
    profile_id = Column(Integer, ForeignKey('profile.id', ondelete="CASCADE"))
    txn_id = Column(Integer, ForeignKey('transaction.id', ondelete="CASCADE"), nullable=False)
    transaction = relationship("Transaction", cascade="delete", back_populates="album")

    def __init__(self, art_id, art_name, alb_id, alb_title, alb_date, explicit, rectype):
        self.art_id = art_id
        self.art_name = art_name
        self.alb_id = alb_id
        self.alb_title = alb_title
        self.alb_date = alb_date
        self.added_on = int(time.time())
        self.explicit = explicit
        self.rectype = rectype
        self.profile_id = config.profile_id
        self.txn_id = Database.TXN_ID

    def __repr__(self):
        return f"<Album {self.alb_id} {self.txn_id}>"


class Playlist(Base):
    __tablename__ = 'playlist'
    __table_args__ = (
        UniqueConstraint('playlist_id', 'profile_id'),
    )

    id = Column(Integer, primary_key=True)
    playlist_id = Column(Integer)
    title = Column(String)
    url = Column(String)
    bitrate = Column(String, nullable=True)
    notify = Column(Boolean, nullable=True)
    dl_path = Column(String, nullable=True)
    profile_id = Column(Integer)
    txn_id = Column(Integer, ForeignKey('transaction.id', ondelete="CASCADE"), nullable=False)
    transaction = relationship("Transaction", cascade="delete", back_populates="playlist")

    def __init__(self, playlist_id, title, url, bitrate=None, notify=None, dl_path=None):
        self.playlist_id = playlist_id
        self.title = title
        self.url = url
        self.bitrate = bitrate
        self.notify = notify
        self.dl_path = dl_path
        self.profile_id = config.profile_id
        self.txn_id = Database.TXN_ID

    def __repr__(self):
        return f"<Playlist {self.playlist_id} {self.txn_id}>"


class PlaylistPendingRefresh(Base):
    __tablename__ = 'playlist_pending_refresh'

    id = Column(Integer, primary_key=True)
    playlist_id = Column(Integer)
    profile_id = Column(Integer, ForeignKey('profile.id', ondelete="CASCADE"), nullable=False)

    def __init__(self, playlist_id):
        self.playlist_id = playlist_id
        self.profile_id = config.profile_id

    def __repr__(self):
        return f"<PlaylistPendingRefresh {self.playlist_id}>"


class PlaylistRelease(Base):
    __tablename__ = 'playlist_release'
    __table_args__ = (
        UniqueConstraint('playlist_id', 'track_id', 'profile_id'),
    )

    id = Column(Integer, primary_key=True)
    playlist_id = Column(Integer)
    art_id = Column(Integer)
    art_name = Column(String)
    track_id = Column(Integer)
    track_name = Column(String)
    track_added = Column(Integer)
    profile_id = Column(Integer)
    txn_id = Column(Integer, ForeignKey('transaction.id', ondelete="CASCADE"), nullable=False)
    transaction = relationship("Transaction", cascade="delete", back_populates="playlist_release")

    def __init__(self, playlist_id, art_id, art_name, track_id, track_name):
        self.playlist_id = playlist_id
        self.art_id = art_id
        self.art_name = art_name
        self.track_id = track_id
        self.track_name = track_name
        self.track_added = int(time.time())
        self.profile_id = config.profile_id
        self.txn_id = Database.TXN_ID

    def __repr__(self):
        return f"<PlaylistRelease {self.track_id} {self.txn_id}>"


class Profile(Base):
    __tablename__ = 'profile'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, nullable=True)
    notify = Column(Boolean, nullable=True)
    bitrate = Column(String, nullable=True)
    rectype = Column(Integer, nullable=True)
    dl_path = Column(String, nullable=True)
    plex_url = Column(String, nullable=True)
    plex_token = Column(String, nullable=True)
    plex_library = Column(String, nullable=True)

    def __init__(self,
                 name,
                 email=None,
                 notify=None,
                 bitrate=None,
                 rectype=None,
                 dl_path=None,
                 plex_url=None,
                 plex_token=None,
                 plex_library=None
                 ):
        self.name = name
        self.email = email
        self.notify = notify
        self.bitrate = bitrate
        self.rectype = rectype
        self.dl_path = dl_path
        self.plex_url = plex_url
        self.plex_token = plex_token
        self.plex_library = plex_library

    def __repr__(self):
        return f"<Profile {self.id} {self.name}>"


class Queue(Base):
    __tablename__ = 'queue'

    id = Column(Integer, primary_key=True)
    art_id = Column(Integer)
    art_name = Column(String)
    alb_id = Column(Integer)
    alb_title = Column(String)
    track_id = Column(Integer)
    track_title = Column(String)
    url = Column(String)
    playlist_title = Column(String)
    bitrate = Column(String)
    dl_path = Column(String)
    profile_id = Column(Integer)
    txn_id = Column(Integer, ForeignKey('transaction.id', ondelete="CASCADE"), nullable=False)

    def __init__(self,
                 art_id,
                 art_name,
                 alb_id,
                 alb_title,
                 track_id,
                 track_title,
                 url,
                 playlist_title,
                 bitrate,
                 dl_path
                 ):
        self.art_id = art_id
        self.art_name = art_name
        self.alb_id = alb_id
        self.alb_title = alb_title
        self.track_id = track_id
        self.track_title = track_title
        self.url = url
        self.playlist_title = playlist_title
        self.bitrate = bitrate
        self.dl_path = dl_path
        self.profile_id = config.profile_id
        self.txn_id = Database.TXN_ID

    def __repr__(self):
        return f"<Queue {self.id}>"


class Transaction(Base):
    __tablename__ = 'transaction'

    id = Column(Integer, primary_key=True)
    timestamp = Column(Integer, nullable=False)
    profile_id = Column(Integer, ForeignKey('profile.id', ondelete="CASCADE"), nullable=False)
    artist = relationship(
        "Artist",
        cascade="delete",
        back_populates='transaction',
    )
    album = relationship("Album", cascade="delete", back_populates="transaction")
    album_future = relationship("AlbumFuture", cascade="delete", back_populates="transaction")
    playlist = relationship("Playlist", cascade="delete", back_populates="transaction")
    playlist_release = relationship("PlaylistRelease", cascade="delete", back_populates="transaction")

    def __init__(self):
        self.timestamp = int(time.time())
        self.profile_id = config.profile_id

    def __repr__(self):
        return f"<Transaction txn:{self.id} prf:{self.profile_id}>"


class Database:

    TXN_ID = None

    def __init__(self):
        self.engine = create_engine(f'sqlite:////home/seggleston/.config/deemon/deemon3.db', echo=False)
        self.txn_id = None

        if not Path("/home/seggleston/.config/deemon/deemon3.db").exists():
            first_run = True
        else:
            first_run = False

        self.conn = self.engine.connect()
        self.session = self.get_session()

        if first_run:
            self.create_db()
        else:
            self.migrate_db()

        self.session.execute('PRAGMA foreign_keys = ON;')

    def create_db(self):
        Base.metadata.create_all(self.engine)
        # TODO disable this for testing
        self.session.add(Profile("default"))
        self.session.add(Settings("db_version", __dbversion__))
        self.session.add(Settings("latest_app_ver", __version__))
        self.session.add(Settings("last_update_check", 0))
        self.session.add(Settings("release_channel", config.release_channel))
        self.session.commit()

    def migrate_db(self):
        pass
        # print("UPGRADE")
        # stmt = select(Settings.value).where(Settings.key == "version")
        # db_version = self.session.execute(stmt).fetchone()
        # from packaging.version import parse as pv
        # if pv(str(db_version.value)) < pv("4"):
        #     print("Ver " + str(db_version.value))
        #     self.session.execute("""ALTER TABLE settings ADD COLUMN test""")
        #     self.session.commit()

    def get_session(self):
        _Session = sessionmaker(bind=self.engine)
        return _Session()

    def init_transaction(self):
        """ Starts new transaction but is not committed """
        if not Database.TXN_ID:
            txn = Transaction()
            self.session.add(txn)
            self.session.flush()
            Database.TXN_ID = self.session.query(Transaction.id).order_by(Transaction.id.desc()).first()[0]

    def get_profile_by_id(self, profile_id):
        stmt = select(Profile).where(Profile.id == profile_id)
        try:
            return self.session.execute(stmt).fetchone()[0]
        except TypeError:
            raise ProfileNotExistError("The profile ID does not exist.")

    def get_artists(self):
        stmt = select(Artist).where(Artist.profile_id == config.profile_id)
        return self.session.execute(stmt).all()

    def get_artist_by_name(self, art_name):
        stmt = select(Artist).join(Transaction).where(Artist.art_name.collate("NOCASE") == art_name).where(Artist.profile_id == config.profile_id)
        return self.session.execute(stmt).one_or_none()

    def remove_artist(self, art_id):
        stmt = delete(Artist).where(Artist.art_id == art_id).where(Artist.profile_id == config.profile_id)
        self.session.execute(stmt)
        self.session.commit()

    def get_pending_artist_refresh(self):
        return self.session.execute(
            select(ArtistPendingRefresh).where(ArtistPendingRefresh.profile_id == config.profile_id)
        ).all()

    def get_albums(self):
        stmt = select(Album).join(Transaction).where(Transaction.profile_id == config.profile_id)
        return self.session.execute(stmt).all()

    def get_future_albums(self):
        stmt = select(AlbumFuture).join(Transaction).where(Transaction.profile_id == config.profile_id)
        return self.session.execute(stmt).all()

    def get_playlists(self):
        stmt = select(Playlist).where(Playlist.profile_id == config.profile_id)
        return self.session.execute(stmt).scalars().all()

    def get_playlist_ids(self):
        _playlists = self.get_playlists()
        return [x.playlist_id for x in _playlists]

    def remove_playlist(self, playlist_id):
        stmt = delete(Playlist).\
            where(Playlist.profile_id == config.profile_id).where(Playlist.playlist_id == playlist_id)
        self.session.execute(stmt)
        self.session.commit()

    def add_new_releases(self, releases):
        self.session.bulk_save_objects(releases)
        self.session.commit()

    def fast_monitor(self, artists):
        self.session.bulk_save_objects(artists)
        self.session.commit()

    def update_monitor(self, artists):
        # TODO Placeholder
        pass

    def update_monitor_playlists(self, playlists):
        # TODO Placeholder
        pass

    def get_releases(self):
        stmt = select(Album).join(Transaction).where(Album.profile_id == config.profile_id)
        return self.session.execute(stmt).all()

    def reset(self):
        self.session.query(Transaction).filter(Transaction.profile_id == config.profile_id).delete()
        self.session.commit()


# TODO TESTS - REMOVE THIS LATER
if __name__ == "__main__":
    print(config.profile_id)
    db = Database()
    print("Creating profile DEFAULT")
    db.session.add(Profile("default"))
    print("Creating profile ROCK")
    db.session.add(Profile("rock"))
    print("Creating profile JAZZ")
    db.session.add(Profile("jazz"))
    db.session.commit()
    db.session.close()

    config.set_property("profile_id", 1)
    db = Database()
    Database.TXN_ID = None
    db.init_transaction()
    print(f"Adding artist under txn:{Database.TXN_ID} prf:{config.profile_id}")
    db.session.add(Artist(726, "Lifehouse"))
    db.session.commit()

    config.set_property("profile_id", 2)
    db = Database()
    Database.TXN_ID = None
    db.init_transaction()
    print(f"Adding artist under txn:{Database.TXN_ID} prf:{config.profile_id}")
    db.session.add(Artist(726, "Lifehouse"))
    db.session.commit()

    config.set_property("profile_id", 3)
    db = Database()
    Database.TXN_ID = None
    db.init_transaction()
    print(f"Adding artist under txn:{Database.TXN_ID} prf:{config.profile_id}")
    add_3 = Artist(726, "Lifehouse")
    print(add_3)
    db.session.add(add_3)
    db.session.commit()
    db.session.close()
    db.conn.close()
    db.engine.dispose()

    db = Database()
    Database.TXN_ID = None

    try:
        result = db.session.execute(
            select(Artist).join(Transaction).where(Transaction.profile_id == config.profile_id)
        )
        for row in result:
            print(f"ROW: {row.Artist.transaction.profile_id}")
    except Exception as e:
        print(f" **** {e} ****")
        pass

    try:
        result = db.session.query(Artist).where(Transaction.profile_id == config.profile_id)
        for row in result:
            print(f"ROW: {row.Artist.transaction.profile_id}")
    except Exception as e:
        print(f" **** {e} ****")
        pass

    try:
        result = db.session.execute(
            select(Artist)
        )
        for row in result:
            print(f"ROW: {row.Artist.transaction.profile_id}")
    except Exception as e:
        print(f" **** {e} ****")
        pass

    print("Cleaning up")
    db.session.execute(delete(Profile).where(Profile.name == "default"))
    db.session.execute(delete(Profile).where(Profile.name == "rock"))
    db.session.execute(delete(Profile).where(Profile.name == "jazz"))
    db.session.commit()
    db.session.close()

    # if 726 not in db.get_artist_ids():
    #     print("Adding artist")
    #     db.init_transaction()
    #     db.session.add(Artist(726, "Lifehouse"))
    #     db.session.commit()
    # else:
    #     print("Removing artist")
    #     db.remove_artist(726)
