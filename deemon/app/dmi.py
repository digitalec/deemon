from deemix.app import deemix, queuemanager
from deemix.app.queueitem import QICollection
from deezer.gw import APIError as gwAPIError, LyricsStatus
from deezer.utils import map_user_playlist
from deemon.app import Deemon
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DeemixInterface(deemix):
    def __init__(self, download_path, config_dir=None):
        logger.debug("Initializing deemix library")
        super().__init__(config_dir, overwriteDownloadFolder=download_path)
        self.qm = DMIQueueManager()

    def download_url(self, urls: list, bitrate: int):
        for url in urls:
            if ';' in url:
                for link in url.split(";"):
                    self.qm.addToQueue(self.dz, link, self.set.settings, bitrate)
            else:
                self.qm.addToQueue(self.dz, url, self.set.settings, bitrate)

    def login(self):
        logger.info("Verifying ARL is valid, please wait...")
        config_dir = Path(self.set.configFolder)
        if Path(config_dir).is_dir():
            if Path(config_dir / '.arl').is_file():
                with open(config_dir / '.arl', 'r') as f:
                    arl = f.readline().rstrip("\n")
                    logger.debug(f"ARL found: {arl}")
                if not self.dz.login_via_arl(arl):
                    logger.error(f"ARL is expired or invalid")
                    return False
            else:
                logger.error(f"ARL not found in {config_dir}")
                return False
        else:
            logger.error(f"ARL directory {config_dir} was not found")
            return False
        return True


class DMIQueueManager(queuemanager.QueueManager):

    def __init__(self):
        super().__init__()

    def generatePlaylistQueueItem(self, dz, id, settings, bitrate):
        # Get essential playlist info
        try:
            playlistAPI = dz.api.get_playlist(id)
        except:
            playlistAPI = None
        # Fallback to gw api if the playlist is private
        if not playlistAPI:
            try:
                userPlaylist = dz.gw.get_playlist_page(id)
                playlistAPI = map_user_playlist(userPlaylist['DATA'])
            except gwAPIError as e:
                e = str(e)
                message = "Wrong URL"
                if "DATA_ERROR" in e:
                    message += f": {e['DATA_ERROR']}"
                return queuemanager.QueueError("https://deezer.com/playlist/"+str(id), message)

        # Check if private playlist and owner
        if not playlistAPI.get('public', False) and playlistAPI['creator']['id'] != str(dz.current_user['id']):
            logger.warning("You can't download others private playlists.")
            return queuemanager.QueueError("https://deezer.com/playlist/"+str(id), "You can't download others private playlists.", "notYourPrivatePlaylist")

        playlistTracksAPI = dz.gw.get_playlist_tracks(id)
        playlistAPI['various_artist'] = dz.api.get_artist(5080) # Useful for save as compilation

        totalSize = len(playlistTracksAPI)
        playlistAPI['nb_tracks'] = totalSize
        collection = []
        dn = Deemon()
        for pos, trackAPI in enumerate(playlistTracksAPI, start=1):
            # Check if release has been seen already and skip it
            vals = {'track_id': trackAPI['SNG_ID'], 'playlist_id': id}
            sql = "SELECT * FROM 'playlist_tracks' WHERE track_id = :track_id AND playlist_id = :playlist_id"
            result = dn.db.query(sql, vals).fetchone()
            if result:
                continue
            if trackAPI.get('EXPLICIT_TRACK_CONTENT', {}).get('EXPLICIT_LYRICS_STATUS', LyricsStatus.UNKNOWN) in [LyricsStatus.EXPLICIT, LyricsStatus.PARTIALLY_EXPLICIT]:
                playlistAPI['explicit'] = True
            trackAPI['_EXTRA_PLAYLIST'] = playlistAPI
            trackAPI['POSITION'] = pos
            trackAPI['SIZE'] = totalSize
            trackAPI['FILENAME_TEMPLATE'] = settings['playlistTracknameTemplate']
            collection.append(trackAPI)
        if not 'explicit' in playlistAPI:
            playlistAPI['explicit'] = False

        return QICollection(
            id=id,
            bitrate=bitrate,
            title=playlistAPI['title'],
            artist=playlistAPI['creator']['name'],
            cover=playlistAPI['picture_small'][:-24] + '/75x75-000000-80-0-0.jpg',
            explicit=playlistAPI['explicit'],
            size=totalSize,
            type='playlist',
            settings=settings,
            collection=collection,
        )