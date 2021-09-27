import logging

from deezer import Deezer
from deemon.core.config import Config as config

logger = logging.getLogger(__name__)


class PlatformAPI:

    def __init__(self, platform: str = "deezer-api"):
        self.max_threads = 2
        self.platform = platform
        self.api = self.set_platform()

    def set_platform(self):
        if self.platform == "deezer-gw":
            dz = Deezer()
            if dz.login_via_arl(config.arl()):
                self.max_threads = 100
                logger.debug(f"Login OK, max_threads set to {self.max_threads}")
                api_obj = dz.gw
            else:
                logger.warning("Falling back to standard API (expired ARL?)")
                self.platform = "deezer-api"
                api_obj = dz.api
        else:
            dz = Deezer()
            api_obj = dz.api

        logger.debug(f"API in use: {self.platform}, thread count set to: {self.max_threads}")
        return api_obj

    def search_artist(self, query: str, limit: int = 1) -> list:
        """
        Return a list of dictionaries from API containing {'id': int, 'name': str}
        """
        if self.platform == "deezer-gw":
            result = self.api.search(query=query, limit=limit)['ARTIST']['data']
            api_result = []
            for r in result:
                api_result.append({'id': int(r['ART_ID']), 'name': r['ART_NAME']})
            return api_result
        else:
            return self.api.search_artist(query=query, limit=limit)['data']

    def get_artist_albums(self, query: int, limit: int = -1):
        """
        Return a list of dictionaries from API containing {'id
        """
        if self.platform == "deezer-gw":
            result = self.api.get_artist_discography(art_id=query, limit=limit)['data']
            api_result = []
            for r in result:
                if r['ART_ID'] == str(query):
                    api_result.append({'id': int(r['ALB_ID']), 'title': r['ALB_TITLE'],
                                       'release_date': r['DIGITAL_RELEASE_DATE'], 'record_type': r['__TYPE__'],
                                       'explicit_lyrics': r['EXPLICIT_ALBUM_CONTENT']['EXPLICIT_LYRICS_STATUS']})
            return api_result
        else:
            return self.api.get_artist_albums(query=query, limit=limit)