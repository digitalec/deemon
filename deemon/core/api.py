import json
from datetime import datetime

import deezer.errors
from deezer import Deezer
from deemon import config
from deemon.core.logger import logger


class PlatformAPI:
    
    TOKEN = None

    def __init__(self):
        self.max_threads = 2
        self.dz = Deezer()
        
        # Make our session threadsafe
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
            
    def get_platform(self):
        if config.fast_api:
            return "deezer-gw"
        return "deezer-api"

    def set_platform(self):
        if self.platform == "deezer-gw":
                self.max_threads = 50
                logger.debug("Using GW API, max_threads set "
                             f"to {self.max_threads}")
                return self.dz.gw
        else:
            return self.dz.api

    @staticmethod
    def get_account_type():
        temp_dz = Deezer()
        temp_dz.login_via_arl(config.arl)
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
    def search_artist(self, query: str, limit: int = 5) -> dict:
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
                logger.info(f"An API error occurred while looking up artist ID {query}. See logs for more info.")
                logger.debug(f"The API error for artist ID {query} was:{e}")
                return {}
            return {'id': int(result['ART_ID']), 'name': result['ART_NAME']}
        else:
            try:
                result = self.api.get_artist(query)
            except deezer.errors.DataException as e:
                logger.info(f"An API error occurred while looking up artist ID {query}. See logs for more info.")
                logger.debug(f"The API error for artist ID {query} was: {e}")
                return {}
            return {'id': result['id'], 'name': result['name']}

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

    def get_artist_releases(self, query: dict, limit=-1):
        if self.platform == "deezer-gw":
            query['releases'] = []
            result = []
            attempts = 0
            while attempts < 5:
                attempts += 1
                try:
                    result = self.api.get_artist_discography(query['id'], limit=limit)['data']
                    break
                except deezer.errors.GWAPIError as e:
                    logger.debug(e)
                    if "UNKNOWN" in str(e):
                        logger.warning(f"Artist discography not available: {query['name']} ({query['id']})")
                    else:
                        logger.error(f"An error occured while attempting to get the "
                                     f"discography for: {query['name']} ({query['id']})")
                    break
                except json.decoder.JSONDecodeError:
                    logger.error(f"API response invalid for {query['name']} ({query['id']}), "
                                 f"retrying ({attempts}/5)...")
            for row in result:
                cover_art = f"https://e-cdns-images.dzcdn.net/images/cover/{row['ALB_PICTURE']}/500x500-00000-80-0-0.jpg"
                album_url = f"https://www.deezer.com/album/{row['ALB_ID']}"

                # Select best available release date
                release_date = datetime.strftime(datetime.today(), "%Y-%m-%d")
                try:
                    if row['ORIGINAL_RELEASE_DATE'] != "0000-00-00":
                        release_date = row['ORIGINAL_RELEASE_DATE']
                    elif row['PHYSICAL_RELEASE_DATE'] != "0000-00-00":
                        release_date = row['PHYSICAL_RELEASE_DATE']
                    elif row['DIGITAL_RELEASE_DATE'] != "0000-00-00":
                        release_date = row['DIGITAL_RELEASE_DATE']
                    else:
                        logger.warning(f"   [!] Found release without release date, assuming today: "
                                       f"{query['name']} - {row['ALB_TITLE']}")
                except KeyError:
                    pass

                query['releases'].append(
                    {
                        'artist_id': int(row['ART_ID']),
                        'artist_name': row['ART_NAME'],
                        'official': row['ARTISTS_ALBUMS_IS_OFFICIAL'],
                        'id': int(row['ALB_ID']),
                        'title': row['ALB_TITLE'],
                        'release_date': release_date,
                        'cover_big': cover_art,
                        'link': album_url,
                        'nb_tracks': row['NUMBER_TRACK'],
                        'record_type': row['TYPE'],
                        'explicit_lyrics': row['EXPLICIT_ALBUM_CONTENT']['EXPLICIT_LYRICS_STATUS'],
                    }
                )
        else:
            query['releases'] = self.api.get_artist_albums(query['id'], limit=limit)['data']
        return query

    @staticmethod
    def get_playlist(query: int):
        try:
            api_result = Deezer().api.get_playlist(query)
            return {'id': query, 'name': api_result['title'],
                    'link': f"https://deezer.com/playlist/{str(api_result['id'])}"}
        except deezer.errors.PermissionException:
            logger.warning(f"   [!] Playlist ID {query} is private")
        except deezer.errors.DataException:
            logger.warning(f"   [!] Playlist ID {query} was not found")

    @staticmethod
    def get_playlist_tracks(query: dict):
        track_list = []
        api_result = Deezer().api.get_playlist(query['id'])
        for track in api_result['tracks']['data']:
            track_list.append({'id': track['id'], 'title': track['title'],
                               'artist_id': track['artist']['id'],
                               'artist_name': track['artist']['name']})
        query['tracks'] = track_list
        return query
