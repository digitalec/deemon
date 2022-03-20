import logging
import requests

from deemon import VERSION
from deemon.cmd import monitor
from deemon.core.config import Config
from deemon.utils import dataprocessor

logger = logging.getLogger(__name__)


def cli(args):

    config = Config().CONFIG

    def show_whats_new():
        try:
            response = requests.get("https://api.github.com/repos/digitalec/deemon/releases")
        except requests.exceptions.ConnectionError:
            return print("Unable to reach GitHub API")

        for release in response.json():
            if release['name'] == VERSION:
                return print(release['body'])
        return print(f"Changelog for v{VERSION} was not found.")


    if args.whats_new:
        show_whats_new()

    if args.profile:
        # if args.profile in db.available_profiles()
        config["defaults"]["profile"] = args.profile

    if args.command == 'backup':
        if args.restore:
            pass
        else:
            if args.include_logs:
                pass
        pass
    elif args.command == 'config':
        pass
    elif args.command == 'download':
        pass
    elif args.command == 'monitor':
        # Validate settings
        if args.alerts:
            config['alerts']['enabled'] = True
        if args.bitrate:
            config['defaults']['bitrate'] = args.bitrate
        if args.download_path:
            config['defaults']['download_path'] = args.download_path
        if args.record_type:
            config['defaults']['record_types'] = args.record_type
        if args.artist:
            config['runtime']['artist'] = dataprocessor.csv_to_list(args.artist)
        if args.artist_id:
            ids = [x.replace(',','') for x in args.artist_id]
            [config['runtime']['artist_id'].append(i) for i in ids if i not in config['runtime']['artist_id']]
        if args.download:
            config['runtime']['download'] = args.download
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
        pass
    elif args.command == 'reset':
        pass
    elif args.command == 'rollback':
        pass
    elif args.command == 'show':
        pass
    elif args.command == 'test':
        pass