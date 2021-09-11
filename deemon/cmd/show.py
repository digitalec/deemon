from deemon.core.db import Database
from operator import itemgetter
import logging
import time
import sys

logger = logging.getLogger(__name__)


class Show:

    def __init__(self):
        self.db = Database()

    def artists(self, csv: bool, artist_ids: bool, extended: bool, filter: str, hide_header: bool, artist: str = None):

        if artist:
            mon = self.db.get_monitored_artist_by_name(artist)
            if len(mon) == 0:
                return logger.info(f"Artist '{artist}' is not being monitored")

            print("{:<10} {:<35} {:<10} {:<10} {:<10} {:<25}".format('ID', 'Artist', 'Alerts',
                                                           'Bitrate', 'Type', 'Download Path'))

            print("{:<10} {:<35} {:<10} {:<10} {:<10} {:<25}".format(mon['artist_id'], mon['artist_name'],
                                                                     mon['alerts'], mon['bitrate'],
                                                                     mon['record_type'], mon['download_path']))
            print("")

            return

        monitored_artists = self.db.get_all_monitored_artists()
        if len(monitored_artists) == 0:
            return logger.info("No artists are being monitored")

        if csv:
            filter = filter.split(',')
            logger.debug(f"Generating CSV data using filters: {', '.join(filter)}")
            column_names = ['artist_id' if x == 'id' else x for x in filter]
            column_names = ['artist_name' if x == 'name' else x for x in column_names]
            column_names = ['record_type' if x == 'type' else x for x in column_names]
            column_names = ['download_path' if x == 'path' else x for x in column_names]

            for column in column_names:
                if not any(x.get(column) for x in monitored_artists):
                    logger.warning(f"Unknown filter specified: {column}")
                    column_names.remove(column)
                    filter.remove(column)

            if not hide_header:
                print(','.join(filter))
            for artist in monitored_artists:
                filtered_artists = []
                for column in column_names:
                    filtered_artists.append(str(artist[column]))
                if len(filtered_artists) > 0:
                    print(",".join(filtered_artists))
            return

        if extended:
            for artist in monitored_artists:
                if artist_ids:
                    print(f"{str(artist['artist_id'])} ({artist['artist_name']})")
                else:
                    print(f"{artist['artist_name']} ({artist['artist_id']})")
                    for column in ['bitrate', 'record_type', 'alerts', 'download_path']:
                        print("  " + column.replace("_", " ").title() + ": " + str(artist[column]))
                    print("")
            return

        if artist_ids:
            artist_data = [str(artist['artist_id']) for artist in monitored_artists]
        else:
            artist_data = [artist['artist_name'] for artist in monitored_artists]

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
            all_artists[idx] = artist
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
            release_list.sort(key=lambda x: x['album_release'], reverse=True)
            for release in release_list:
                print('+ [%-10s] %s - %s' % (release['album_release'], release['artist_name'], release['album_name']))
        else:
            logger.info(f"No releases found in the last {days} day(s)")

