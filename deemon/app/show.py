from deemon.app import settings, db
from deemon.app import Deemon
import logging
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

    def releases(self, limit=None):
        pass

    def stats(self):
        pass