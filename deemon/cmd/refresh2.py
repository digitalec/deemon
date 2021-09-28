import logging
from deemon.core.logger import setup_logger
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from datetime import datetime
from deemon.core.config import Config
from deemon.core import db, api
from deemon.utils import dates, startup, performance

setup_logger(log_level='DEBUG', log_file=startup.get_log_file())
logger = logging.getLogger("deemon")
config = Config()


class Refresh:
    def __init__(self):
        self.db = db.Database()
        self.release_date = datetime.now()
        self.api = api.PlatformAPI("deezer-gw")
        self.new_releases = []
        tid = self.db.get_next_transaction_id()
        config.set('tid', tid, validate=False)

    def filter_releases(self, releases: list):
        """
        Check if release matches conditions: record_type, future release, etc.
        """
        filtered = []
        artist_id = releases[0]['artist_id']
        seen_releases = self.db.get_artist_releases(artist_id)
        seen_releases = [v for x in seen_releases for k, v in x.items()]
        new_releases = [x for x in releases if type(x) == dict for k, v in x.items() if k == "id" and v not in seen_releases]
        for n in new_releases:
            if config.record_type() == n['record_type'] or config.record_type() == "all":
                album_release = dates.str_to_datetime_obj(n['release_date'])
                if album_release > self.release_date:
                    n['future'] = 1
                    logger.info(f":: FUTURE RELEASE DETECTED :: {n['artist_name']} - {n['title']} ({n['release_date']})")
                else:
                    logger.debug(f"Queueing new release by {n['artist_name']}")
                    self.new_releases.append(n)

    @performance.timeit
    def run(self, artists: list = None):
        logger.info("Collecting artists to refresh, please wait...")
        api_result = self.get_release_data(artists)
        [self.filter_releases(x) for x in api_result if len(x)]
        self.db.add_new_release(self.new_releases)
        self.db.commit()

    @performance.timeit
    def get_release_data(self, artists: list = None) -> list:
        if not artists:
            artists = self.db.get_unrefreshed_artists()
            if not len(artists):
                artists = self.db.get_monitored()
        with ThreadPoolExecutor(max_workers=self.api.max_threads) as ex:
            api_result = list(tqdm(ex.map(self.api.get_artist_albums, [artist['artist_id'] for artist in artists]),
                                   total=len(artists), desc="Getting release data...", ascii=" #",
                                   bar_format='[{n_fmt}/{total_fmt}] {desc} [{bar}] {percentage:3.0f}%'))
        return api_result


if __name__ == "__main__":
    r = Refresh()
    r.run()
