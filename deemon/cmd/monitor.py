import sys
from sqlite3 import OperationalError
from pathlib import Path
from deemon.core.db import Database
from deemon.core.config import Config as config
from deemon.cmd import search
import logging
import deezer

logger = logging.getLogger(__name__)


def monitor(profile, value, artist_config: dict = None, remove=False, dl_obj=None, is_search=False):

    bitrate = artist_config.get('bitrate')
    alerts = artist_config.get('alerts')
    record_type = artist_config.get('record_type')
    download_path = artist_config.get('download_path')

    dz = deezer.Deezer()
    db = Database()

    def purge_playlist(playlist_id, title):
        if playlist_id:
            output = str(playlist_id)
            playlist = db.get_monitored_playlist_by_id(playlist_id)
        else:
            output = title
            playlist = db.get_monitored_playlist_by_name(title)

        if playlist:
            db.remove_monitored_playlists(playlist['id'])
            logger.info(f"No longer monitoring playlist '{playlist['title']}'")
        else:
            logger.error(f"Unable to remove from monitoring: '{output}' not found.")

    def purge_artist(id: int = None, name: str = None):
        if id:
            output = str(id)
            artist = db.get_monitored_artist_by_id(id)
        else:
            output = name
            artist = db.get_monitored_artist_by_name(name)

        if artist:
            db.remove_monitored_artist(artist['artist_id'])
            logger.info(f"No longer monitoring artist '{artist['artist_name']}'")
        else:
            logger.error(f"Unable to remove from monitoring: '{output}' not found.")

    def get_best_result(api_data):
        matches: list = []
        for idx, artist in enumerate(api_data):
            if value.lower() == artist['name'].lower():
                matches.append(artist)
        if len(matches) == 1 and not is_search:
            return matches[0]
        elif len(matches) > 1:
            if is_search or config.prompt_duplicates():
                menu = search.Search()
                ask_user = menu.search_menu(value)
                if ask_user:
                    return ask_user[0]
                return logger.debug("No artist selected, skipping...")
            else:
                if not config.prompt_duplicates():
                    return matches[0]
                logger.error(f"Duplicate artist names found for {value}. Try again using --search")
        elif is_search or config.prompt_no_matches():
            menu = search.Search()
            ask_user = menu.search_menu(value)
            if ask_user:
                return ask_user[0]
        elif not config.prompt_no_matches():
            return api_data[0]
        else:
            logger.error(f"Artist {value} not found. Try again using --search")
            return

    # TODO move this to config!
    if not Path(config.download_path()).exists:
        return logger.error(f"Invalid download path: {config.download_path()}")

    if profile in ['artist', 'artist_id']:
        if profile == "artist":
            if remove:
                return purge_artist(name=value)
            api_result = dz.api.search_artist(value, limit=config.query_limit())["data"]

            if len(api_result) == 0:
                if is_search:
                    return logger.error(f"No results found for {value}")
                return logger.error(f"Artist {value} not found.")

            api_result = get_best_result(api_result)

            if not api_result:
                return
        else:
            if remove:
                return purge_artist(id=value)
            try:
                api_result = dz.api.get_artist(value)
            except deezer.api.DataException:
                logger.error(f"Artist ID {value} not found.")
                return

        if db.get_monitored_artist_by_id(api_result['id']):
            logger.warning(f"Artist '{api_result['name']}' is already being monitored")
            return

        sql_values = {
            'artist_id': api_result['id'],
            'artist_name': api_result['name'],
            'bitrate': bitrate,
            'record_type': record_type,
            'alerts': alerts,
            'download_path': download_path,
            'profile_id': config.profile_id()
        }
        query = ("INSERT INTO monitor "
                 "(artist_id, artist_name, bitrate, record_type, alerts, download_path, profile_id) "
                 "VALUES "
                 "(:artist_id, :artist_name, :bitrate, :record_type, :alerts, :download_path, :profile_id)")

        try:
            db.query(query, sql_values)
        except OperationalError as e:
            logger.info(e)

        logger.info(f"Now monitoring artist '{api_result['name']}'")
        logger.debug(f"bitrate: {bitrate}, record_type: {record_type}, "
                     f"alerts: {alerts}, download_path: {download_path}")
        if dl_obj:
            dl_obj.download(None, [api_result['id']], None, None, None, False)
        db.commit()
        return api_result['id']

    if profile == "playlist":
        playlist_id_from_url = value.split('/playlist/')
        try:
            playlist_id = int(playlist_id_from_url[1])
        except (IndexError, ValueError):
            logger.error(f"Invalid playlist URL -- {playlist_id_from_url}")
            return
        try:
            api_result = dz.api.get_playlist(playlist_id)
        except deezer.api.DataException:
            logger.error(f"Playlist ID {playlist_id} not found.")
            return

        playlist_exists = db.get_monitored_playlist_by_id(api_result['id'])

        # TODO remove should NOT access API!
        if remove:
            if not playlist_exists:
                logger.warning(f"Playlist '{api_result['title']}' is not being monitored yet")
                return
            purge_playlist(api_result['id'], api_result['title'])
            return
        if playlist_exists:
            logger.warning(f"Playlist '{api_result['title']}' is already being monitored")
            return

        api_result['bitrate'] = artist_config['bitrate'] or None
        api_result['alerts'] = artist_config['alerts'] or None
        api_result['download_path'] = artist_config['download_path'] or None

        try:
            db.monitor_playlist(api_result)
        except OperationalError as e:
            logger.error("sqlite Operational Error: " + e)

        logger.info(f"Now monitoring playlist '{api_result['title']}'")
        if dl_obj:
            dl_obj.download(None, None, None, [api_result['link']], None, False)
        db.commit()
        return api_result['id']
