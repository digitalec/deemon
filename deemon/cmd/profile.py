from deemon.core.config import Config as config
from deemon.core.db import Database
import logging

logger = logging.getLogger(__name__)


class ProfileConfig:
    def __init__(self, profile_name):
        self.db = Database()
        self.profile = profile_name

    def add(self):
        new_profile = {}
        profile_config = self.db.get_profile(self.profile)
        if profile_config:
            return logger.error(f"Profile {self.profile} already exists")
        else:
            logger.info("Adding new profile: " + self.profile)
            print("** Any option left blank will fallback to global config **\n")
            new_profile['name'] = self.profile

        menu = [
            {'setting': 'email', 'type': str, 'text': 'Email address', 'allowed': []},
            {'setting': 'alerts', 'type': bool, 'text': 'Alerts', 'allowed': config.allowed_values('alerts')},
            {'setting': 'bitrate', 'type': str, 'text': 'Bitrate', 'allowed': config.allowed_values('bitrate')},
            {'setting': 'record_type', 'type': str, 'text': 'Record Type', 'allowed': config.allowed_values('record_type')},
            {'setting': 'plex_baseurl', 'type': str, 'text': 'Plex Base URL', 'allowed': []},
            {'setting': 'plex_token', 'type': str, 'text': 'Plex Token', 'allowed': []},
            {'setting': 'plex_library', 'type': str, 'text': 'Plex Library', 'allowed': []},
            {'setting': 'download_path', 'type': str, 'text': 'Download Path', 'allowed': []},
        ]

        for m in menu:
            repeat = True
            while repeat:
                i = input(m['text'] + ": ")
                if i == "":
                    new_profile[m['setting']] = None
                    break
                if not isinstance(i, m['type']):
                    try:
                        i = int(i)
                    except ValueError:
                        print(" - Allowed options: " + ', '.join(str(x) for x in m['allowed']))
                        continue
                if len(m['allowed']) > 0:
                    if i not in m['allowed']:
                        print(" - Allowed options: " + ', '.join(str(x) for x in m['allowed']))
                        continue
                new_profile[m['setting']] = i
                break

        print("\n")
        i = input(":: Save these settings? [y|N] ")
        if i.lower() != "y":
            return logger.info("Operation cancelled. No changes saved.")
        else:
            self.db.create_profile(new_profile)
            logger.debug(f"New profile created with the following configuration: {new_profile}")

    def edit(self):
        profile_config = self.db.get_profile(self.profile)
        if not profile_config:
            return logger.error(f"Profile {self.profile} was not found")

        menu = [
            {'setting': 'name', 'type': str, 'text': 'Profile Name', 'allowed': []},
            {'setting': 'email', 'type': str, 'text': 'Email address', 'allowed': []},
            {'setting': 'alerts', 'type': bool, 'text': 'Alerts', 'allowed': config.allowed_values('alerts')},
            {'setting': 'bitrate', 'type': str, 'text': 'Bitrate', 'allowed': config.allowed_values('bitrate')},
            {'setting': 'record_type', 'type': str, 'text': 'Record Type', 'allowed': config.allowed_values('record_type')},
            {'setting': 'plex_baseurl', 'type': str, 'text': 'Plex Base URL', 'allowed': []},
            {'setting': 'plex_token', 'type': str, 'text': 'Plex Token', 'allowed': []},
            {'setting': 'plex_library', 'type': str, 'text': 'Plex Library', 'allowed': []},
            {'setting': 'download_path', 'type': str, 'text': 'Download Path', 'allowed': []},
        ]

        modified = 0
        for m in menu:
            repeat = True
            while repeat:
                i = input(m['text'] + " [" + str(profile_config[m['setting']]) + "]: ")
                if i == "":
                    break
                if not isinstance(i, m['type']):
                    try:
                        i = int(i)
                    except ValueError:
                        print(" - Allowed options: " + ', '.join(str(x) for x in m['allowed']))
                        continue
                if len(m['allowed']) > 0:
                    if i not in m['allowed']:
                        print(" - Allowed options: " + ', '.join(str(x) for x in m['allowed']))
                        continue
                if m['setting'] == "name" and self.profile != i:
                    if self.db.get_profile(i):
                        print(" - Name already in use: " + i)
                        continue
                profile_config[m['setting']] = i
                modified += 1
                break

        if modified > 0:
            print("\n")
            i = input(":: Save these settings? [y|N] ")
            if i.lower() != "y":
                return logger.info("Operation cancelled. No changes saved.")
            else:
                self.db.update_profile(profile_config)
        else:
            print("No changes made, exiting...")

    def delete(self):
        profile_config = self.db.get_profile(self.profile)
        if not profile_config:
            return logger.error(f"Profile {self.profile} not found")

        if profile_config['id'] == 1:
            return logger.info("You cannot delete the default profile.")

        i = input(f":: Remove the profile '{self.profile}'? [y|N] ")
        if i.lower() == "y":
            self.db.delete_profile(self.profile)
            return logger.info("Profile " + self.profile + " deleted.")
        else:
            return logger.info("Operation cancelled")

    def show(self):
        if not self.profile:
            profile = self.db.get_all_profiles()
        else:
            profile = [self.db.get_profile(self.profile)]
            if len(profile) == 0:
                return logger.error(f"Profile {self.profile} not found")

        print("{:<10} {:<40} {:<8} {:<8} {:<8} {:<25} "
              "{:<20} {:<20} {:<20}".format('Name', 'Email', 'Alerts', 'Bitrate', 'Type',
                                            'Plex Base URL', 'Plex Token', 'Plex Library', 'Download Path'))
        for u in profile:
            id, name, email, alerts, bitrate, rtype, url, token, \
            lib, dl_path = [x if x is not None else '' for x in u.values()]
            print("{:<10} {:<40} {:<8} {:<8} {:<8} {:<25} "
                  "{:<20} {:<20} {:<20}".format(name, email, alerts, bitrate, rtype, url, token, lib, dl_path))
            print("")
