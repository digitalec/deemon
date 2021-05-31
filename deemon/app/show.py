from deemon.app import settings, db
from deemon.app import Deemon
import logging
import time
import sys

logger = logging.getLogger(__name__)


class ShowStats(Deemon):

    def __init__(self):
        super().__init__()

    def artists(self):
        monitored_artists = self.db.get_all_artists()
        if len(monitored_artists) == 0:
            logger.info("No artists are being monitored")
            sys.exit(0)

        artist_data = [artist[1] for artist in monitored_artists]

        if len(artist_data) > 0:
            for a, b in zip(artist_data[::2], artist_data[1::2]):
                print('{:<30}{:<}'.format(a, b))
        else:
            for artist in artist_data:
                print(artist)

    def releases(self, days):
        seconds_per_day = 86400
        days_in_seconds = (days * seconds_per_day)
        now = int(time.time())
        back_date = (now - days_in_seconds)
        releases = self.db.show_new_releases(back_date, now)
        if releases.rowcount > 0:
            logger.info(f"New releases found within last {days} day(s):")
            print("\n")
            for release in releases:
                logger.info(f"{release[1]} - {release[3]}")
        else:
            logger.info(f"No releases found in that timeframe")

    def stats(self):
        pass
