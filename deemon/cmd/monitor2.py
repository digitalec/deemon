import logging
import deezer
from deemon.utils import performance
from deemon.core.db import Database
from deemon.core.config import Config as config
from deemon.cmd import search

logger = logging.getLogger(__name__)

class Monitor:

    def __init__(self):
        self.bitrate = None
        self.alerts = None
        self.record_type = None
        self.download_path = None
        self.remove = False
        self.refresh = True
        self.dl = None
        self.dz = deezer.Deezer()
        self.db = Database()

    def set_bitrate(self, bitrate: str):
        self.bitrate = bitrate

    def set_alerts(self, alerts: bool):
        self.alerts = alerts

    def set_record_type(self, record_type: str):
        self.record_type = record_type

    def set_download_path(self, download_path: str):
        self.download_path = download_path

    def get_best_result(self, api_data):
        pass

    def artists(self, name: list):
        pass

    def artist_ids(self, ids: list):
        pass

    def urls(self, urls: list):
        pass

    def playlists(self, playlists: list):
        pass

    @performance.timeit
    def purge_artists(self, names: list = None, ids: list = None):
        if names:
            # names = [(x,) for x in names]
            result = self.db.select_artists(names)
            print(result)
            exit()
            self.db.remove_artists(names)
        if ids:
            ids = [(x,) for x in ids]
            self.db.remove_artists(ids)


    def purge_playlists(self, titles: list):
        pass


list_of_artist_names = ['lifehouse', 'andrew belle', 'tate mcrae', 'taylor swift']
monitor = Monitor()
monitor.purge_artists(list_of_artist_names)