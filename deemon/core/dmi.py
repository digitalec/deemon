import logging
from pathlib import Path

import deemix
import deemix.utils.localpaths as localpaths
from deemix import generateDownloadObject
from deemix.downloader import Downloader
from deemix.settings import load as LoadSettings
from deemix.types.DownloadObjects import Collection
from deemix.utils import formatListener, pathtemplates
from deezer import Deezer
from deezer.api import APIError
from deezer.gw import GWAPIError
from deezer.utils import map_user_playlist, LyricsStatus, map_track

from deemon.core import notifier
from deemon.core.config import Config as config
from deemon.core.db import Database

logger = logging.getLogger(__name__)


class DeemixLogListener:
    @classmethod
    def send(cls, key, value=None):
        if isinstance(value, dict):
            if value.get('failed') and value['failed'] == True:
                logger.error(f"  [!] Error while downloading {value['data']['title']} by {value['data']['artist']}")
                logger.error(f"      >> {value['error']}")
        log_string = formatListener(key, value)
        if config.debug_mode():
            if log_string: logger.debug(f"[DEEMIX] {log_string}")


class DeemixInterface:
    def __init__(self):
        logger.debug("Initializing deemix library")
        self.db = Database()
        self.dz = Deezer()

        # Override deemix code causing unhandled TypeError exception on line 158
        pathtemplates.generateTrackName = self.generateTrackName

        if config.deemix_path() == "":
            self.config_dir = localpaths.getConfigFolder()
        else:
            self.config_dir = Path(config.deemix_path())

        self.dx_settings = LoadSettings(self.config_dir)

        logger.debug("deemix " + deemix.__version__)
        logger.debug(f"deemix config path: {self.config_dir}")

    def download_url(self, url, bitrate, download_path, override_deemix=True):
        listener = DeemixLogListener()

        if override_deemix:
            deemix.generatePlaylistItem = self.generatePlaylistItem

        if download_path:
            self.dx_settings['downloadLocation'] = download_path
            logger.debug(f"deemix download path set to: {self.dx_settings['downloadLocation']}")

        links = []
        for link in url:
            if ';' in link:
                for l in link.split(";"):
                    links.append(l)
            else:
                links.append(link)
        for link in links:
            download_object = generateDownloadObject(self.dz, link, bitrate, listener=listener)
            if isinstance(download_object, list):
                for obj in download_object:
                    Downloader(self.dz, obj, self.dx_settings, listener=listener).start()
            else:
                Downloader(self.dz, download_object, self.dx_settings, listener=listener).start()

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
                logger.error("Unable to login using ARL found in deemon config")
                failed_logins += 1
        else:
            logger.debug("ARL was not found in deemon config, checking if deemix has it...")

        if self.config_dir.is_dir():
            if Path(self.config_dir / '.arl').is_file():
                with open(self.config_dir / '.arl', 'r') as f:
                    arl_from_file = f.readline().rstrip("\n")
                    logger.debug("ARL found in deemix config")
                    print(":: Found ARL in deemix .arl file, checking... ", end="")
                    if self.verify_arl(arl_from_file):
                        return True
                    else:
                        logger.error("Unable to login using ARL found in deemix config directory")
                        failed_logins += 1
            else:
                logger.debug(f"ARL not found in {self.config_dir}")
        else:
            logger.error(f"ARL directory {self.config_dir} was not found")

        if failed_logins > 1:
            notification = notifier.Notify()
            notification.expired_arl()
        else:
            logger.error("No ARL was found, aborting...")
            return False

    def generatePlaylistItem(self, dz, link_id, bitrate, playlistAPI=None, playlistTracksAPI=None):
        if not playlistAPI:
            if not str(link_id).isdecimal(): raise InvalidID(f"https://deezer.com/playlist/{link_id}")
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
            #
            # BEGIN DEEMON PATCH
            #
            vals = {'track_id': trackAPI['SNG_ID'], 'playlist_id': playlistAPI['id']}
            sql = "SELECT * FROM 'playlist_tracks' WHERE track_id = :track_id AND playlist_id = :playlist_id"
            result = self.db.query(sql, vals).fetchone()
            if result:
                continue
            #
            # END DEEMON PATCH
            #
            trackAPI = map_track(trackAPI)
            if trackAPI['explicit_lyrics']:
                playlistAPI['explicit'] = True
            if 'track_token' in trackAPI: del trackAPI['track_token']
            trackAPI['position'] = pos
            collection.append(trackAPI)

        if 'explicit' not in playlistAPI: playlistAPI['explicit'] = False

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
                'tracks': collection,
                'playlistAPI': playlistAPI
            }
        })


    def generateTrackName(self, filename, track, settings):
        from deemix.utils.pathtemplates import fixName, pad, pathSep, antiDot, fixLongName

        logger.debug("[PATCH] Overriding deemix method generateTrackName with bug fix")

        c = settings['illegalCharacterReplacer']
        filename = filename.replace("%title%", fixName(track.title, c))
        filename = filename.replace("%artist%", fixName(track.mainArtist.name, c))
        filename = filename.replace("%artists%", fixName(", ".join(track.artists), c))
        filename = filename.replace("%allartists%", fixName(track.artistsString, c))
        filename = filename.replace("%mainartists%", fixName(track.mainArtistsString, c))
        if track.featArtistsString:
            filename = filename.replace("%featartists%", fixName('('+track.featArtistsString+')', c))
        else:
            filename = filename.replace("%featartists%", '')
        filename = filename.replace("%album%", fixName(track.album.title, c))
        filename = filename.replace("%albumartist%", fixName(track.album.mainArtist.name, c))
        filename = filename.replace("%tracknumber%", pad(track.trackNumber, track.album.trackTotal, settings))
        filename = filename.replace("%tracktotal%", str(track.album.trackTotal))
        filename = filename.replace("%discnumber%", str(track.discNumber))
        filename = filename.replace("%disctotal%", str(track.album.discTotal))
        if len(track.album.genre) > 0:
            filename = filename.replace("%genre%", fixName(track.album.genre[0], c))
        else:
            filename = filename.replace("%genre%", "Unknown")
        filename = filename.replace("%year%", str(track.date.year))
        filename = filename.replace("%date%", track.dateString)
        filename = filename.replace("%bpm%", str(track.bpm))
        filename = filename.replace("%label%", fixName(track.album.label, c))
        filename = filename.replace("%isrc%", track.ISRC)

        """ BEGIN DEEMON PATCH """
        """ Catches exception when track.album.barcode == None """
        try:
            filename = filename.replace("%upc%", track.album.barcode)
        except TypeError:
            pass
        """ END DEEMON PATCH """

        filename = filename.replace("%explicit%", "(Explicit)" if track.explicit else "")

        filename = filename.replace("%track_id%", str(track.id))
        filename = filename.replace("%album_id%", str(track.album.id))
        filename = filename.replace("%artist_id%", str(track.mainArtist.id))
        if track.playlist:
            filename = filename.replace("%playlist_id%", str(track.playlist.playlistID))
            filename = filename.replace("%position%", pad(track.position, track.playlist.trackTotal, settings))
        else:
            filename = filename.replace("%playlist_id%", '')
            filename = filename.replace("%position%", pad(track.position, track.album.trackTotal, settings))
        filename = filename.replace('\\', pathSep).replace('/', pathSep)
        return antiDot(fixLongName(filename))



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
