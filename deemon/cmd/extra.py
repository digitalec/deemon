from concurrent.futures import ThreadPoolExecutor
import logging
from tqdm import tqdm
from deemon.core import db as dbase
from deemon.core.api import PlatformAPI
from deemon.core.config import Config as config
from deemon.utils import ui, performance

logger = logging.getLogger(__name__)



def debugger(message: str, payload = None):
    if config.debug_mode():
        if not payload:
            payload = ""
        logger.debug(f"DEBUG_MODE: {message} {str(payload)}")
            

def main():
    db = dbase.Database()
    api = PlatformAPI()
    releases = db.get_artist_releases()
    if not len(releases):
        return logger.warning("No releases found in local database")
    logger.debug("Fetching extra release data...")
    debugger("SpawningThreads", api.max_threads)
    with ThreadPoolExecutor(max_workers=api.max_threads) as ex:
        api_result = list(
            tqdm(ex.map(api.get_extra_release_info, releases),
                    total=len(releases),
                    desc=f"Fetching extra release data for {len(releases):,} "
                         "releases, please wait...", ascii=" #",
                    bar_format=ui.TQDM_FORMAT)
        )

    if len(api_result):
        logger.info(":: Saving changes to database, this can take several minutes...")
        db.add_extra_release_info(api_result)
        db.commit()
        print("")
        performance.operation_time(config.get('start_time'))
        logger.info("Extra release info has been updated")
