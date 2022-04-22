import logging
import requests

from deemon import __version__
from deemon.cmd import monitor, refresh
from deemon.core import notifier
from deemon.core.db import Database
from deemon.core.config import Config
from deemon.core.exceptions import InvalidValueError
from deemon.utils import dataprocessor, validate, recordtypes

logger = logging.getLogger(__name__)


def cli(args):

    config = Config().CONFIG
    db = Database()

    db.do_upgrade()
    config['runtime']['transaction_id'] = db.get_next_transaction_id()

    def show_whats_new():
        try:
            response = requests.get("https://api.github.com/repos/digitalec/deemon/releases")
        except requests.exceptions.ConnectionError:
            return print("Unable to reach GitHub API")

        for release in response.json():
            if release['name'] == __version__:
                return print(release['body'])
        return print(f"Changelog for v{__version__} was not found.")

    if args.whats_new:
        show_whats_new()

    if args.profile_id:
        # if args.profile in db.available_profiles()
        config["defaults"]["profile"] = args.profile_id

    if args.command == 'backup':
        if args.restore:
            pass
        else:
            if args.include_logs:
                pass
        pass
    elif args.command == 'download':
        pass
    elif args.command == 'monitor':
        if args.notify:
            config['runtime']['notify'] = True
        if args.bitrate:
            if validate.validate_bitrates(args.bitrate):
                config['runtime']['bitrate'] = args.bitrate
            else:
                raise InvalidValueError(f"Invalid bitrate: {args.bitrate}")
        if args.download_path:
            config['runtime']['download_path'] = args.download_path
        if args.record_type:
            invalid_rt = validate.validate_record_type(args.record_type)
            if len(invalid_rt):
                raise InvalidValueError(f"Invalid record type(s): {args.record_type}")
            else:
                config['runtime']['record_type'] = recordtypes.get_record_type_index(args.record_type)
        if args.artist:
            config['runtime']['artist'] = dataprocessor.csv_to_list(args.artist)
        if args.artist_id:
            ids = [x.replace(',', '') for x in args.artist_id]
            [config['runtime']['artist_id'].append(i) for i in ids if i not in config['runtime']['artist_id']]
        if args.download:
            config['runtime']['download_all'] = args.download
        if args.file:
            config['runtime']['file'] = args.file
        if args.url:
            config['runtime']['url'] = args.url
        if args.time_machine:
            config['runtime']['time_machine'] = args.time_machine
        monitor.monitor()
    elif args.command == 'profile':
        pass
    elif args.command == 'refresh':
        refresh.start()
    elif args.command == 'remove':
        to_remove = dataprocessor.csv_to_list(args.name)
        monitor.remove(to_remove, by_id=args.id, playlist=args.playlist)
    elif args.command == 'reset':
        """Reset monitoring database"""
        logger.warning("** WARNING: Everything except for profiles will be erased! **")
        confirm = input(":: Type 'reset' to confirm: ")
        if confirm.lower() == "reset":
            print("")
            db.reset_database()
        else:
            logger.info("Reset aborted. Database has NOT been modified.")
        return
    elif args.command == 'rollback':
        pass
    elif args.command == 'show':
        pass
    elif args.command == 'test':
        notification = notifier.Notify()
        notification.test()
