import json
import logging
from datetime import datetime

import deezer.errors
from deezer import Deezer

from deemon.core.config import Config as config

logger = logging.getLogger(__name__)


class PlatformAPI:
    
    TOKEN = None

    def __init__(self):
        self.max_threads = 2
        self.dz = Deezer()
        
        # Make our session threadsafe
        logger.debug("Getting API Token")
        PlatformAPI.TOKEN = self.dz.gw.get_user_data()['checkForm']
        self.dz.gw._get_token = self._get_token
        
        self.platform = self.get_platform()
        self.account_type = self.get_account_type()
        self.api = self.set_platform()
        
    def _get_token(self):
        """Overrides deezer.gw._get_token()
        Returns API token to use across entire session
        """
        return PlatformAPI.TOKEN

    def debugger(self, message: str, payload = None):
        if config.debug_mode():
            if not payload:
                payload = ""
            logger.debug(f"DEBUG_MODE: {message} {str(payload)}")
            
    def get_platform(self):
        if config.fast_api():
            return "deezer-gw"
        return "deezer-api"

    def set_platform(self):
        if self.platform == "deezer-gw":
                self.max_threads = config.fast_api_threads()
                if self.max_threads > 50:
                    self.max_threads = 50
                if self.max_threads < 1:
                    self.max_threads = 1
                logger.debug("Using GW API, max_threads set "
                             f"to {self.max_threads}")
                return self.dz.gw
        else:
            return self.dz.api
        
    def get_account_type(self):
        logger.debug("Verifying ARL, please wait...")
        temp_dz = Deezer()
        temp_dz.login_via_arl(config.arl())
        if temp_dz.get_session()['current_user'].get('can_stream_lossless'):
            logger.debug(f"Deezer account type is \"Hi-Fi\"")
            return "hifi"
        elif temp_dz.get_session()['current_user'].get('can_stream_hq'):
            logger.debug(f"Deezer account type is \"Premium\"")
            return "premium"
        else:
            logger.debug(f"Deezer account type is \"Free\"")
            return "free"

    #TODO GW API appears to ignore limit; must implement afterwards
    def search_artist(self, query: str, limit: int = 5):
        """
        Return a list of dictionaries from API containing {'id': int, 'name': str}
        """
        if self.platform == "deezer-gw":
            api_result = []
            try:
                result = self.api.search(query=query, limit=limit)['ARTIST']['data']
            except json.decoder.JSONDecodeError:
                logger.error(f"   [!] Empty response from API while searching for artist {query}, retrying...")
                try:
                    result = self.api.search(query=query, limit=limit)['ARTIST']['data']
                except json.decoder.JSONDecodeError:
                    logger.error(f"   [!] API still sending empty response while searching for artist {query}")
                    return []
            for r in result:
                api_result.append({'id': int(r['ART_ID']), 'name': r['ART_NAME']})
        else:
            api_result = self.api.search_artist(query=query, limit=limit)['data']

        return {'query': query, 'results': api_result}

    def get_artist_by_id(self, query: int, limit: int = 1):
        """
        Return a dictionary from API containing {'id': int, 'name': str}
        """
        if self.platform == "deezer-gw":
            try:
                result = self.api.get_artist(query)
            except deezer.errors.GWAPIError as e:
                logger.debug(f"API error on artist ID {query}: {e}")
                return
            except json.decoder.JSONDecodeError:
                logger.error(f"   [!] Empty response from API while getting data for artist ID {query}, retrying...")
                try:
                    result = self.api.get_artist(query)
                except json.decoder.JSONDecodeError:
                    logger.error(f"   [!] API still sending empty response for artist ID {query}")
                    return
            return {'id': int(result['ART_ID']), 'name': result['ART_NAME']}
        else:
            try:
                result = self.api.get_artist(query)
            except deezer.errors.DataException as e:
                logger.debug(f"API error: {e}")
                return
            return {'id': result['id'], 'name': result['name']}
        
    def get_album(self, query: int) -> dict:
        """Return a dictionary from API containing album info"""
        if self.platform == "deezer-gw":
            try:
                result = self.api.get_album(query)
            except deezer.errors.GWAPIError as e:
                logger.debug(f"API error: {e}")
                return {}
            except json.decoder.JSONDecodeError:
                logger.error(f"   [!] Empty response from API while getting data for album ID {query}, retrying...")
                try:
                    result = self.api.get_album(query)
                except json.decoder.JSONDecodeError:
                    logger.error(f"   [!] API still sending empty response for album ID {query}")
                    return {}
            return {'id': int(result['ALB_ID']), 'title': result['ALB_TITLE'], 'artist': {'name': result['ART_NAME']}}
        else:
            try:
                result = self.api.get_album(query)
            except deezer.errors.DataException as e:
                logger.debug(f"API error: {e}")
                return
            else:
                return result

    def get_track(self, query: int) -> dict:
        """Return a dictionary from API containing album info"""
        if self.platform == "deezer-gw":
            try:
                result = self.api.get_track(query)
            except deezer.errors.GWAPIError as e:
                logger.debug(f"API error: {e}")
                return {}
            except json.decoder.JSONDecodeError:
                logger.error(f"   [!] Empty response from API while getting data for album ID {query}, retrying...")
                try:
                    result = self.api.get_album(query)
                except json.decoder.JSONDecodeError:
                    logger.error(f"   [!] API still sending empty response for album ID {query}")
                    return {}
            return {'id': int(result['SNG_ID']), 'title': result['SNG_TITLE'], 'artist': {'name': result['ART_NAME']}}
        else:
            try:
                result = self.api.get_track(query)
            except deezer.errors.DataException as e:
                logger.debug(f"API error: {e}")
            else:
                return result

    def get_extra_release_info(self, query: dict):
        album = {'id': query['album_id'], 'label': None}
        if self.platform == "deezer-gw":
            album_details = self.api.get_album(query['album_id'])
            if album_details.get('LABEL_NAME'):
                album['label'] = album_details['LABEL_NAME']
        else:
            album_details = self.api.get_album(query['album_id'])
            if album_details.get('label'):
                album['label'] = album_details['label']
        
        return album

    def get_artist_albums(self, query: dict, limit: int = -1):
        """
        Return a list of dictionaries from API containing
        """
        self.debugger(f"Refreshing artist releases for {query['artist_name']} ({query['artist_id']})")
        if self.platform == "deezer-gw":
            try:
                result = self.api.get_artist_discography(art_id=query['artist_id'], limit=limit)['data']
            except deezer.errors.GWAPIError as e:
                if "UNKNOWN" in str(e):
                    logger.debug(e)
                    logger.warning(f"   [!] Artist discography is not available for "
                                 f"{query['artist_name']} ({query['artist_id']})")
                else:
                    logger.debug(e)
                    logger.error(f"An error occured while attempting to get the discography for "
                                 f"{query['artist_name']} ({query['artist_id']})")
                query['releases'] = []
                return query
            except json.decoder.JSONDecodeError:
                logger.error(f"   [!] Empty response from API while getting data for discography for {query['artist_name']}, retrying...")
                try:
                    result = self.api.get_artist_discography(art_id=query['artist_id'], limit=limit)['data']
                except json.decoder.JSONDecodeError:
                    logger.error(f"   [!] API still sending empty response for discography for {query['artist_name']}")
                    query['releases'] = []
                    return query
            api_result = []
            for r in result:
                # Remove ID check to get compilations
                if (r['ART_ID'] == str(query['artist_id']) and r['ARTISTS_ALBUMS_IS_OFFICIAL']) or (r['ART_ID'] == str(query['artist_id']) and config.allow_unofficial()) or config.allow_compilations():
                    # TYPE 0 - single, TYPE 1 - album, TYPE 2 - compilation, TYPE 3 - ep
                    if r['TYPE'] == '0':
                        r['TYPE'] = "single"
                    elif r['TYPE'] == '1' and r['ART_ID'] != str(query['artist_id']):
                        if not config.allow_featured_in():
                            logger.debug(f"Featured In for {query['artist_name']} detected but are disabled in config")
                            continue
                        else:
                            logger.debug(f"Featured In detected for artist {query['artist_name']}: {r['ALB_TITLE']}")
                            r['TYPE'] = "album"
                            # TODO set unique r['TYPE'] for FEATURED IN
                    elif r['TYPE'] == '2':
                        if not config.allow_compilations():
                            logger.debug(f"Compilation for {query['artist_name']} detected but are disabled in config")
                            continue
                        else:
                            logger.debug(f"Compilation detected for artist {query['artist_name']}: {r['ALB_TITLE']}")
                            r['TYPE'] = "album"
                            # TODO set unique r['TYPE'] for COMPILATIONS
                    elif r['TYPE'] == '3':
                        r['TYPE'] = "ep"
                    else:
                        r['TYPE'] = "album"

                    if r['ORIGINAL_RELEASE_DATE'] != "0000-00-00":
                        release_date = r['ORIGINAL_RELEASE_DATE']
                    elif r['PHYSICAL_RELEASE_DATE'] != "0000-00-00":
                        release_date = r['PHYSICAL_RELEASE_DATE']
                    elif r['DIGITAL_RELEASE_DATE'] != "0000-00-00":
                        release_date = r['DIGITAL_RELEASE_DATE']
                    else:
                        # In the event of an unknown release date, set it to today's date
                        # See album ID: 417403
                        logger.warning(f"   [!] Found release without release date, assuming today: "
                                       f"{query['artist_name']} - {r['ALB_TITLE']}")
                        release_date = datetime.strftime(datetime.today(), "%Y-%m-%d")
                    
                    cover_art = f"https://e-cdns-images.dzcdn.net/images/cover/{r['ALB_PICTURE']}/500x500-00000-80-0-0.jpg"
                    album_url = f"https://www.deezer.com/album/{r['ALB_ID']}"
                    
                    api_result.append(
                        {
                            'id': int(r['ALB_ID']),
                            'title': r['ALB_TITLE'],
                            'release_date': release_date,
                            'explicit_lyrics': r['EXPLICIT_ALBUM_CONTENT']['EXPLICIT_LYRICS_STATUS'],
                            'record_type': r['TYPE'],
                            'cover_big': cover_art,
                            'link': album_url,
                            'nb_tracks': r['NUMBER_TRACK'],
                            }
                    )
        else:
            api_result = self.api.get_artist_albums(artist_id=query['artist_id'], limit=limit)['data']

        query['releases'] = api_result
        return query

    @staticmethod
    def get_playlist(query: int):
        try:
            api_result = Deezer().api.get_playlist(query)
        except deezer.errors.PermissionException:
            logger.warning(f"   [!] Permission Denied: Playlist {query} is private")
            return
        except deezer.errors.DataException:
            logger.warning(f"   [!] Playlist ID {query['id']} was not found")
            return
        except json.decoder.JSONDecodeError:
            logger.error(f"   [!] Empty response from API while getting data for playlist ID {query}, retrying...")
            try:
                api_result = Deezer().api.get_playlist(query)
            except json.decoder.JSONDecodeError:
                logger.error(f"   [!] API still sending empty response while getting data for playlist ID {query}")
                return
        return {'id': query, 'title': api_result['title'],
                'link': f"https://deezer.com/playlist/{str(api_result['id'])}"}

    @staticmethod
    def get_playlist_tracks(query: dict):
        track_list = []
        try:
            api_result = Deezer().api.get_playlist(query['id'])
        except deezer.errors.PermissionException:
            logger.warning(f"   [!] Permission Denied: Playlist {query['title']} ({query['id']}) is private")
            return
        except deezer.errors.DataException:
            logger.warning(f"   [!] Playlist ID {query} was not found")
            return
        except json.decoder.JSONDecodeError:
            logger.error(f"   [!] Empty response from API while getting data for playlist ID {query['id']}")
            try:
                api_result = Deezer().api.get_playlist(query['id'])
            except json.decoder.JSONDecodeError:
                logger.error(f"   [!] API still sending empty response while getting data for playlist ID {query['id']}")
                return
        for track in api_result['tracks']['data']:
            track_list.append({'id': track['id'], 'title': track['title'],
                               'artist_id': track['artist']['id'],
                               'artist_name': track['artist']['name']})
        query['tracks'] = track_list
        return query
