from deemon.core import Deemon
from operator import itemgetter
import logging
import time
import sys

logger = logging.getLogger(__name__)


class ShowStats(Deemon):

    def __init__(self):
        super().__init__()

    def artists(self, csv=False, artist_ids=False, extended=None):
        # TODO extended is list of fields to grab from database; 'id', 'name', etc.
        monitored_artists = self.db.get_all_monitored_artists()

        if len(monitored_artists) == 0:
            logger.info("No artists are being monitored")
            sys.exit(0)

        if extended:
            artist_data = monitored_artists
            for artist in artist_data:
                if csv:
                    if artist_ids:
                        print(str(artist['id']) + ", " + artist['name'])
                    else:
                        print(artist['name'] + ", " + str(artist['id']))
                else:
                    if artist_ids:
                        print(f"{str(artist['id'])} ({artist['name']})")
                    else:
                        print(f"{artist['name']} ({str(artist['id'])})")
                    print(f"    type: {artist['record_type'].upper()}, "
                          f"bitrate: {artist['bitrate']}, alerts: {artist['alerts']}\n")
            return
        elif artist_ids:
            artist_data = [str(artist['id']) for artist in monitored_artists]
        else:
            artist_data = [artist['name'] for artist in monitored_artists]

        if csv:
            logger.info(', '.join(artist_data))
        else:
            if len(artist_data) > 10:
                if not artist_ids:
                    artist_data = self.truncate_long_artists(artist_data)

                if len(artist_data) % 2 != 0:
                    artist_data.append(" ")

                for a, b in zip(artist_data[0::2], artist_data[1::2]):
                    print('{:<30}{:<}'.format(a, b))
            else:
                for artist in artist_data:
                    print(artist)

    def playlists(self, csv=False):
        monitored_playlists = self.db.get_all_monitored_playlists()
        for p in monitored_playlists:
            print(f"{p[1]} ({p[2]})")

    @staticmethod
    def truncate_long_artists(all_artists):
        for idx, artist in enumerate(all_artists):
            if len(artist) > 25:
                all_artists[idx] = artist[:22] + "..."
        return all_artists

    def releases(self, days):
        seconds_per_day = 86400
        days_in_seconds = (days * seconds_per_day)
        now = int(time.time())
        back_date = (now - days_in_seconds)
        releases = self.db.show_new_releases(back_date, now)
        release_list = [x for x in releases]
        if len(release_list) > 0:
            logger.info(f"New releases found within last {days} day(s):")
            print("")
            release_list.sort(key=itemgetter(4), reverse=True)
            for release in release_list:
                print('+ [%-10s] %s - %s' % (release[4], release[1], release[3]))
        else:
            logger.info(f"No releases found in that timeframe")

    def stats(self):
        pass