import deemon.app
from deemon.app.db import DB
from deemon.app.notify import EmailNotification
from deemon.app import utils
from deemon.app.logger import setup_logger
from deemon.app import settings
from deemon.app.dmi import DeemixInterface
from deemon import __version__
from datetime import datetime
from pathlib import Path
import deezer
import sqlite3
import tarfile
import argparse
import logging
import os
import sys
import time
import click


def show(self):
    if self.args.artists:
        monitored = self.db.get_all_artists()
        if len(monitored) == 0:
            print("No artists currently being monitored")
        else:
            artist_data = []
            for m in monitored:
                artist = m[1][:16]
                bitrate = m[2]
                record_type = m[3]
                alerts = m[4]

                if alerts == 0:
                    alerts = "off"
                if alerts == 1:
                    alerts = "on"

                if bitrate == 1:
                    bitrate = "128k"
                if bitrate == 3:
                    bitrate = "320k"
                if bitrate == 9:
                    bitrate = "FLAC"

                if record_type == "all":
                    record_type = "all"
                if record_type == "album":
                    record_type = "album"
                if record_type == "ep":
                    record_type = "ep"
                if record_type == "single":
                    record_type = "single"

                artist_data.append(f"{artist} [{bitrate}, {record_type}, {alerts}]")

            logger.info("Viewing: Monitored Artists\n\n")

            if len(artist_data) > 3:
                for a, b in zip(artist_data[::2], artist_data[1::2]):
                    print('{:<40}{:<}'.format(a, b))
            else:
                for d in artist_data:
                    print(d)

            print("\n\nLegend: [bitrate, album type, alerts]")
    elif self.args.new_releases:
        days = self.args.new_releases
        days_in_seconds = (days * 86400)
        now = int(time.time())
        get_time = (now - days_in_seconds)
        # TODO this should check by album release date to be more useful
        releases = self.db.show_new_releases(get_time, now)
        logger.info(f"New releases found within last {days} day(s):")
        print("")
        for release in releases:
            logger.info(f"{release[1]} - {release[3]}")

    sys.exit(0)


def export_artists(self):
    export_path = Path(self.args.path)
    export_file = Path(export_path / "deemon-artists.csv")
    with open(export_file, "w+") as f:
        artist_dump = self.db.get_all_artists()
        for line in artist_dump:
            line = ','.join(map(str, line))
            f.write(line + "\n")
    sys.exit(0)

def import_artists(self):
    import_artists = self.args.path
    bitrate = self.settings.config["bitrate"]
    record_type = self.settings.config["record_type"]
    alerts = self.settings.config["alerts"]
    # TODO check db for existing artist
    if import_artists:
        if Path(import_artists).is_file():
            with open(import_artists) as f:
                # TODO check for CSV!
                import_list = f.read().splitlines()
        elif Path(import_artists).is_dir():
            import_list = os.listdir(import_artists)
            num_to_import = len(import_list)
            logger.info(f"Importing {num_to_import} artist(s)...")
        else:
            logger.error("Unrecognized import type")
            sys.exit(1)

        use_defaults = input("Use default import settings? (Y/n) ")
        if use_defaults.lower() == "n":

            # TODO move this to settings.py and use globally
            default_choices = {
                "bitrate": {
                    "128": 1,
                    "320": 3,
                    "FLAC": 9
                },
                "record_type": ['all', 'album', 'ep', 'single'],
                "alerts": {
                    "y": "enable",
                    "n": "disable"
                }
            }

            bitrate_opts = default_choices["bitrate"]
            bitrate_default = ([k for k, v in bitrate_opts.items() if v == bitrate][0])
            record_type_default = record_type
            alert_opts = default_choices["alerts"]
            alert_default = ([k for k, v in alert_opts.items() if v == alerts][0])
            alert_friendly = {}
            for k, v in alert_opts.items():
                if v == alerts:
                    alert_friendly[k.upper()] = v
                else:
                    alert_friendly[k] = v

            for artist in import_list:
                print(f"Artist: {artist}")
                user_bitrate, user_record_type, user_alerts = "", "", ""

                # BITRATE
                bitrate_names = ", ".join(list(bitrate_opts.keys()))
                while user_bitrate not in bitrate_opts:
                    user_bitrate = input(f"Enter bitrate ({bitrate_names} "
                                         f"[{bitrate_default}]): ").upper() or bitrate_default

                bitrate = bitrate_opts[user_bitrate]

                # RECORD TYPE
                record_type_opts = ", ".join(default_choices["record_type"])
                while user_record_type.lower() not in default_choices["record_type"]:
                    user_record_type = input(f"Enter record type ({record_type_opts} "
                                             f"[{record_type_default}]): ") or record_type_default
                record_type = user_record_type

                # ALERTS
                alert_names = "/".join(list(alert_friendly.keys()))
                while user_alerts not in alert_opts:
                    user_alerts = input(f"Enable new release notifications "
                                        f"for this artist? ({alert_names}) ").lower() or alert_default
                alerts = alert_opts[user_alerts]

                dl = Download()
                for artist in import_list:
                    ma = MonitorArtist()
                    ma.artist_name = artist
                    ma.bitrate = bitrate
                    ma.record_type = record_type
                    ma.alerts = alerts
                    ma.start_monitoring()

                dl.refresh()
        else:
            for artist in import_list:
                dl = Download()
                for artist in import_list:
                    ma = MonitorArtist()
                    ma.artist_name = artist
                    ma.bitrate = bitrate
                    ma.record_type = record_type
                    ma.alerts = alerts
                    ma.start_monitoring()

                dl.refresh()

    sys.exit(0)



