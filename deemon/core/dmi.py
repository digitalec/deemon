import logging
from pathlib import Path

import deemix
import deemix.utils.localpaths as localpaths
from deemix import generateDownloadObject
from deemix.downloader import Downloader
from deemix.settings import load as LoadSettings
from deemix.types.DownloadObjects import Collection
from deezer import Deezer
from deezer.api import APIError
from deezer.gw import GWAPIError, LyricsStatus
from deezer.utils import map_user_playlist

from deemon.core import notifier
from deemon.core.config import Config as config
from deemon.core.db import Database

logger = logging.getLogger(__name__)


class DeemixInterface:
    def __init__(self):
        logger.debug("Initializing deemix library")
        self.db = Database()
        self.dz = Deezer()

        if config.deemix_path() == "":
            self.config_dir = localpaths.getConfigFolder()
        else:
            self.config_dir = Path(config.deemix_path())

        self.dx_settings = LoadSettings(self.config_dir)

        if config.download_path() != "":
            # TODO is this necessary?
            self.download_path = Path(config.download_path())
            self.dx_settings['downloadLocation'] = str(self.download_path)

        logger.debug("deemix " + deemix.__version__)
        logger.debug(f"deemix Config Path: {self.config_dir}")
        logger.debug(f"deemix Download Path: {self.dx_settings['downloadLocation']}")

    def download_url(self, url, bitrate, download_path, override_deemix=True):
        if override_deemix:
            deemix.generatePlaylistItem = self.generatePlaylistItem

        if download_path and download_path != "":
            self.dx_settings['downloadLocation'] = download_path

        links = []
        for link in url:
            if ';' in link:
                for l in link.split(";"):
                    links.append(l)
            else:
                links.append(link)
        for link in links:
            download_object = generateDownloadObject(self.dz, link, bitrate)
            if isinstance(download_object, list):
                for obj in download_object:
                    Downloader(self.dz, obj, self.dx_settings).start()
            else:
                Downloader(self.dz, download_object, self.dx_settings).start()
    
    
    def deezer_acct_type(self):
        user_session = self.dz.get_session()['current_user']
    
        if user_session.get('can_stream_lossless'):
            logger.debug("Deezer account connected and supports lossless")
            config.set('deezer_quality', 'lossless', validate=False)
        elif user_session.get('can_stream_hq'):
            logger.debug("Deezer account connected and supports high quality")
            config.set('deezer_quality', 'hq', validate=False)
        else:
            logger.warning("Deezer account connected but only supports 128k")
            config.set('deezer_quality', 'lq', validate=False)

    def verify_arl(self, arl):
        if not self.dz.login_via_arl(arl):
            print("FAILED")
            logger.debug(f"ARL Failed: {arl}")
            return False
        self.deezer_acct_type()
            
        print("OK")
        logger.debug("ARL is valid")
        return True

    def login(self):
        failed_logins = 0
        logger.debug("Looking for ARL...")
        if config.arl():
            logger.debug("ARL found in deemon config")
            print(":: Found ARL in deemon config, checking... ", end="")
            if self.verify_arl(config.arl()):
                return True
            else:
                failed_logins += 1

        if self.config_dir.is_dir():
            if Path(self.config_dir / '.arl').is_file():
                with open(self.config_dir / '.arl', 'r') as f:
                    arl_from_file = f.readline().rstrip("\n")
                    logger.debug("ARL found in deemix config")
                    print(":: Found ARL in deemix .arl file, checking... ", end="")
                    if self.verify_arl(arl_from_file):
                        return True
                    else:
                        failed_logins += 1
            else:
                logger.error(f"ARL not found in {self.config_dir}")
                return False
        else:
            logger.error(f"ARL directory {self.config_dir} was not found")
            return False

        if failed_logins > 1:
            notification = notifier.Notify()
            notification.expired_arl()

    def generatePlaylistItem(self, dz, link_id, bitrate, playlistAPI=None, playlistTracksAPI=None):
        if not playlistAPI:
            if not str(link_id).isdecimal():
                raise InvalidID(f"https://deezer.com/playlist/{link_id}")
            # Get essential playlist info
            try:
                playlistAPI = dz.api.get_playlist(link_id)
            except APIError:
                playlistAPI = None
            # Fallback to gw api if the playlist is private
            if not playlistAPI:
                try:
                    userPlaylist = dz.gw.get_playlist_page(link_id)
                    playlistAPI = map_user_playlist(userPlaylist['DATA'])
                except GWAPIError as e:
                    raise GenerationError(f"https://deezer.com/playlist/{link_id}", str(e)) from e

            # Check if private playlist and owner
            if not playlistAPI.get('public', False) and playlistAPI['creator']['id'] != str(self.dz.current_user['id']):
                logger.warning("You can't download others private playlists.")
                raise NotYourPrivatePlaylist(f"https://deezer.com/playlist/{link_id}")

        if not playlistTracksAPI:
            playlistTracksAPI = dz.gw.get_playlist_tracks(link_id)
        playlistAPI['various_artist'] = dz.api.get_artist(5080)  # Useful for save as compilation

        totalSize = len(playlistTracksAPI)
        playlistAPI['nb_tracks'] = totalSize
        collection = []
        for pos, trackAPI in enumerate(playlistTracksAPI, start=1):
            # Check if release has been seen already and skip it
            vals = {'track_id': trackAPI['SNG_ID'], 'playlist_id': playlistAPI['id']}
            sql = "SELECT * FROM 'playlist_tracks' WHERE track_id = :track_id AND playlist_id = :playlist_id"
            result = self.db.query(sql, vals).fetchone()
            if result:
                continue
            if trackAPI.get('EXPLICIT_TRACK_CONTENT', {}).get('EXPLICIT_LYRICS_STATUS', LyricsStatus.UNKNOWN) in [
                LyricsStatus.EXPLICIT, LyricsStatus.PARTIALLY_EXPLICIT]:
                playlistAPI['explicit'] = True
            trackAPI['POSITION'] = pos
            trackAPI['SIZE'] = totalSize
            collection.append(trackAPI)

        if 'explicit' not in playlistAPI:
            playlistAPI['explicit'] = False

        return Collection({
            'type': 'playlist',
            'id': link_id,
            'bitrate': bitrate,
            'title': playlistAPI['title'],
            'artist': playlistAPI['creator']['name'],
            'cover': playlistAPI['picture_small'][:-24] + '/75x75-000000-80-0-0.jpg',
            'explicit': playlistAPI['explicit'],
            'size': totalSize,
            'collection': {
                'tracks_gw': collection,
                'playlistAPI': playlistAPI
            }
        })


class GenerationError(Exception):
    def __init__(self, link, message, errid=None):
        super().__init__()
        self.link = link
        self.message = message
        self.errid = errid

    def toDict(self):
        return {
            'link': self.link,
            'error': self.message,
            'errid': self.errid
        }


class InvalidID(GenerationError):
    def __init__(self, link):
        super().__init__(link, "Link ID is invalid!", "invalidID")


class NotYourPrivatePlaylist(GenerationError):
    def __init__(self, link):
        super().__init__(link, "You can't download others private playlists.", "notYourPrivatePlaylist")
