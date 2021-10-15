import json
import logging
from datetime import datetime

import deezer.errors
from deezer import Deezer

from deemon.core.config import Config as config

logger = logging.getLogger(__name__)


class PlatformAPI:

    def __init__(self, platform: str = "deezer-api"):
        self.max_threads = 2
        self.platform = platform
        self.api = self.set_platform()

    def debugger(self, message: str, payload = None):
        if config.debug_mode():
            if not payload:
                payload = ""
            logger.debug(f"DEBUG_MODE: {message} {str(payload)}")

    def set_platform(self):
        if self.platform == "deezer-gw":
            dz = Deezer()
            if dz.login_via_arl(config.arl()):
                self.max_threads = 50
                logger.debug(f"Login OK, max_threads set to {self.max_threads}")
                api_obj = dz.gw
            else:
                logger.warning("[!] Falling back to standard API (expired ARL?)")
                self.platform = "deezer-api"
                api_obj = dz.api
        else:
            dz = Deezer()
            api_obj = dz.api

        logger.debug(f"API in use: {self.platform}, thread count set to: {self.max_threads}")
        return api_obj

    def search_artist(self, query: str, limit: int = 1) -> dict:
        """
        Return a list of dictionaries from API containing {'id': int, 'name': str}
        """
        if self.platform == "deezer-gw":
            result = self.api.search(query=query, limit=limit)['ARTIST']['data']
            api_result = []
            for r in result:
                api_result.append({'id': int(r['ART_ID']), 'name': r['ART_NAME']})
        else:
            api_result = self.api.search_artist(query=query, limit=limit)['data']

        return {'query': query, 'results': api_result}

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
                result = self.api.get_artist(query)
            except deezer.errors.DataException as e:
                logger.debug(f"API error: {e}")
                return {}
            return {'id': result['id'], 'name': result['name']}

    def get_artist_albums(self, query: dict, limit: int = -1):
        """
        Return a list of dictionaries from API containing
        """
        self.debugger("RefreshArtist", query['artist_name'])
        if self.platform == "deezer-gw":
            try:
                result = self.api.get_artist_discography(art_id=query['artist_id'], limit=limit)['data']
            except deezer.errors.GWAPIError as e:
                if "UNKNOWN" in str(e):
                    logger.error(f"   [!] Artist discography is not available for "
                                 f"{query['artist_name']} ({query['artist_id']})")
                else:
                    logger.error(f"An error occured while attempting to get the discography for "
                                 f"{query['artist_id']} ({query['artist_id']})")
                query['releases'] = []
                return query
            api_result = []
            for r in result:
                if r['ART_ID'] == str(query['artist_id']) and r['ARTISTS_ALBUMS_IS_OFFICIAL']:
                    # TYPE 0 - single, TYPE 1 - album, TYPE 2 - compilation, TYPE 3 - ep
                    if r['TYPE'] == '0':
                        r['TYPE'] = "single"
                    elif r['TYPE'] == '3':
                        r['TYPE'] = "ep"
                    else:
                        r['TYPE'] = "album"

                    if r['DIGITAL_RELEASE_DATE'] != "0000-00-00":
                        release_date = r['DIGITAL_RELEASE_DATE']
                    elif r['ORIGINAL_RELEASE_DATE'] != "0000-00-00":
                        release_date = r['ORIGINAL_RELEASE_DATE']
                    elif r['PHYSICAL_RELEASE_DATE'] != "0000-00-00":
                        release_date = r['PHYSICAL_RELEASE_DATE']
                    else:
                        # In the event of an unknown release date, set it to today's date
                        # See album ID: 417403
                        logger.warning(f"   [!] Found release without release date, assuming today: "
                                       f"{query['artist_name']} - {r['ALB_TITLE']}")
                        release_date = datetime.strftime(datetime.today(), "%Y-%m-%d")

                    api_result.append({'id': int(r['ALB_ID']), 'title': r['ALB_TITLE'],
                                       'release_date': release_date,
                                       'explicit_lyrics': r['EXPLICIT_ALBUM_CONTENT']['EXPLICIT_LYRICS_STATUS'],
                                       'record_type': r['TYPE']})
        else:
            api_result = self.api.get_artist_albums(artist_id=query['artist_id'], limit=limit)['data']

        query['releases'] = api_result
        return query

    def get_playlist(self, query: dict):
        # if self.platform == "deezer-gw":
        #     # deezer-py BUG: Receiving a 'method unknown' for 'playlist_getData'
        #     result = self.api.get_playlist(query)
        #     print(result)
        # else:
        #     return self.api.get_playlist(query)
        track_list = []
        api_result = Deezer().api.get_playlist(query['id'])
        for track in api_result['tracks']['data']:
            track_list.append({'id': track['id'], 'title': track['title'], 'artist_id': track['artist']['id'],
                               'artist_name': track['artist']['name']})
        query['tracks'] = track_list
        return query
