import csv
import logging
import os
import time
from pathlib import Path
from typing import Union

from deemon.core.db import Database
from deemon.utils.dates import generate_date_filename

logger = logging.getLogger(__name__)


class Show:

    def __init__(self):
        self.db = Database()

    def monitoring(self, artist: bool = True, query: str = None, export_csv: bool = False,
                   save_path: Union[str, Path] = None, filter: str = None, hide_header: bool = False,
                   is_id: bool = False):

        def csv_output(line: str):
            if save_path:
                output_to_file.append(line)
            else:
                print(line)

        output_to_file = []

        if artist:
            if query:
                if is_id:
                    try:
                        query = int(query)
                    except ValueError:
                        return logger.error(f"Invalid Artist ID - {query}")
                    db_result = self.db.get_monitored_artist_by_id(query)
                else:
                    db_result = self.db.get_monitored_artist_by_name(query)
            else:
                db_result = self.db.get_all_monitored_artists()

            if not db_result:
                if query:
                    return logger.error("Artist/ID not found: " + str(query))
                else:
                    return logger.error("No artists are being monitored")
        else:
            if query:
                if is_id:
                    try:
                        query = int(query)
                    except ValueError:
                        return logger.error(f"Invalid Playlist ID - {query}")
                    db_result = self.db.get_monitored_playlist_by_id(query)
                else:
                    db_result = self.db.get_monitored_playlist_by_name(query)
            else:
                db_result = self.db.get_all_monitored_playlists()

            if not db_result:
                if query:
                    return logger.error("Playlist/ID not found: " + str(query))
                else:
                    return logger.error("No playlists are being monitored")

        if artist and query:
            for key, val in db_result.items():
                if val == None:
                    db_result[key] = "-"

            print("{:<10} {:<35} {:<10} {:<10} {:<10} {:<25}".format('ID', 'Artist', 'Alerts',
                                                                     'Bitrate', 'Type', 'Download Path'))

            print("{!s:<10} {!s:<35} {!s:<10} {!s:<10} {!s:<10} {!s:<25}".format(db_result['artist_id'],
                                                                                 db_result['artist_name'],
                                                                                 db_result['alerts'],
                                                                                 db_result['bitrate'],
                                                                                 db_result['record_type'],
                                                                                 db_result['download_path']))
            print("")
        elif not artist and query:
            for key, val in db_result.items():
                if val == None:
                    db_result[key] = "-"

            print("{:<15} {:<30} {:<50} {:<10} {:<10} {:<25}".format('ID', 'Title', 'URL', 'Alerts',
                                                                     'Bitrate', 'Download Path'))

            print("{!s:<15} {!s:<30} {!s:<50}  {!s:<10} {!s:<10} {!s:<25}".format(db_result['id'], db_result['title'],
                                                                                  db_result['url'], db_result['alerts'],
                                                                                  db_result['bitrate'],
                                                                                  db_result['download_path']))
            print("")
        else:
            if export_csv or save_path:
                if artist:
                    if not filter:
                        filter = "name,id,bitrate,alerts,type,path"
                    filter = filter.split(',')
                    logger.debug(f"Generating CSV data using filters: {', '.join(filter)}")
                    column_names = ['artist_id' if x == 'id' else x for x in filter]
                    column_names = ['artist_name' if x == 'name' else x for x in column_names]
                    column_names = ['record_type' if x == 'type' else x for x in column_names]
                    column_names = ['download_path' if x == 'path' else x for x in column_names]
                else:
                    if not filter:
                        filter = "id,title,url,bitrate,alerts,path"
                    filter = filter.split(',')
                    logger.debug(f"Generating CSV data using filters: {', '.join(filter)}")
                    column_names = ['download_path' if x == 'path' else x for x in filter]

                for column in column_names:
                    if not len([x for x in db_result if column in x.keys()]):
                        logger.warning(f"Unknown filter specified: {column}")
                        column_names.remove(column)

                if not hide_header:
                    csv_output(','.join(filter))
                for artist in db_result:
                    filtered_artists = []
                    for key, value in artist.items():
                        if value is None:
                            artist[key] = ""
                    for column in column_names:
                        filtered_artists.append(str(artist[column]))
                    if len(filtered_artists):
                        for i, a in enumerate(filtered_artists):
                            if '"' in a:
                                a = a.replace('"', "'")
                            if ',' in a:
                                filtered_artists[i] = f'"{a}"'
                        csv_output(",".join(filtered_artists))

                if output_to_file:
                    if Path(save_path).is_dir():
                        output_filename = Path(save_path / f"{generate_date_filename('deemon_')}.csv")
                    else:
                        output_filename = Path(save_path)

                    with open(output_filename, 'w', encoding="utf-8") as f:
                        for line in output_to_file:
                            if line == output_to_file[-1]:
                                f.writelines(line)
                                break
                            f.writelines(line + "\n")

                    return logger.info("CSV data has been saved to: " + str(output_filename))

                return

            if artist:
                db_result = [x['artist_name'] for x in db_result]
            else:
                db_result = [x['title'] for x in db_result]
            if len(db_result) < 10:
                for artist in db_result:
                    print(artist)
            else:
                db_result = self.truncate_long_artists(db_result)

                size = os.get_terminal_size()
                max_cols = (int(size.columns / 30))
                if max_cols > 5:
                    max_cols = 5

                while len(db_result) % max_cols != 0:
                    db_result.append(" ")

                if max_cols >= 5:
                    for a, b, c, d, e in zip(db_result[0::5], db_result[1::5], db_result[2::5], db_result[3::5],
                                             db_result[4::5]):
                        print('{:<30}{:<30}{:<30}{:<30}{:<30}'.format(a, b, c, d, e))
                elif max_cols >= 4:
                    for a, b, c, d in zip(db_result[0::4], db_result[1::4], db_result[2::4], db_result[3::4]):
                        print('{:<30}{:<30}{:<30}{:<30}'.format(a, b, c, d))
                elif max_cols >= 3:
                    for a, b, c in zip(db_result[0::3], db_result[1::3], db_result[2::3]):
                        print('{:<30}{:<30}{:<30}'.format(a, b, c))
                elif max_cols >= 2:
                    for a, b in zip(db_result[0::2], db_result[1::2]):
                        print('{:<30}{:<30}'.format(a, b))
                else:
                    for a in db_result:
                        print(a)

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

    def releases(self, days, future):
        if future:
            future_releases = self.db.get_future_releases()
            future_release_list = [x for x in future_releases]
            if len(future_release_list) > 0:
                logger.info(f"Future releases:")
                print("")
                future_release_list.sort(key=lambda x: x['album_release'], reverse=True)
                for release in future_release_list:
                    print('+ [%-10s] %s - %s' % (release['album_release'], release['artist_name'], release['album_name']))
            else:
                logger.info("No future releases have been detected")
        else:
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
