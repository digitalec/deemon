import logging

import deezer.errors
from deezer import Deezer
from deemon.core.config import Config as config
from deemon.utils import performance

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
                self.max_threads = 50
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

    def get_artist_by_id(self, query: int, limit: int = 1) -> dict:
        """
        Return a dictionary from API containing {'id': int, 'name': str}
        """
        if self.platform == "deezer-gw":
            try:
                result = self.api.get_artist(query)
            except deezer.errors.GWAPIError as e:
                logger.debug(f"API error: {e}")
                return {}
            return {'id': int(result['ART_ID']), 'name': result['ART_NAME']}
        else:
            try:
                self.api.get_artist(query)
            except deezer.errors.DataException as e:
                logger.debug(f"API error: {e}")
                return {}

    def get_artist_albums(self, query: int, limit: int = -1):
        """
        Return a list of dictionaries from API containing
        """
        if self.platform == "deezer-gw":
            result = self.api.get_artist_discography(art_id=query, limit=limit)['data']
            api_result = []
            for r in result:
                if r['ART_ID'] == str(query):
                    # TYPE 0 - single, TYPE 1 - album, TYPE 2 - compilation, TYPE 3 - ep
                    if r['TYPE'] == '0':
                        rtype = "single"
                    elif r['TYPE'] == '3':
                        rtype = "ep"
                    else:
                        rtype = "album"
                    api_result.append({'id': int(r['ALB_ID']), 'title': r['ALB_TITLE'],
                                       'release_date': r['DIGITAL_RELEASE_DATE'], 'record_type': rtype,
                                       'explicit_lyrics': r['EXPLICIT_ALBUM_CONTENT']['EXPLICIT_LYRICS_STATUS'],
                                       'artist_id': int(r['ART_ID']), 'artist_name': r['ART_NAME'], 'future': 0})
            return api_result
        else:
            return self.api.get_artist_albums(query=query, limit=limit)