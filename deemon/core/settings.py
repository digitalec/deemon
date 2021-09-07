from deemon.core.config import Config as config
from deemon.core.db import Database
import logging

logger = logging.getLogger(__name__)


class UserConfig:
    def __init__(self, username):
        self.db = Database()
        self.user = username

    def add(self):
        new_user = {}
        user_settings = self.db.get_user(self.user)
        if user_settings:
            return logger.error(f"User {self.user} already exists")
        else:
            logger.info("Adding new user: " + self.user)
            print("** Any option left blank will fallback to global config (except email address) **\n")
            new_user['name'] = self.user

        menu = [
            {'setting': 'email', 'type': str, 'text': 'Email address', 'allowed': []},
            {'setting': 'alerts', 'type': int, 'text': 'Alerts', 'allowed': [0, 1]},
            {'setting': 'bitrate', 'type': int, 'text': 'Bitrate', 'allowed': [1, 3, 9]},
            {'setting': 'record_type', 'type': str, 'text': 'Record Type', 'allowed': ["all", "album", "ep", "single"]},
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
                    new_user[m['setting']] = None
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
                new_user[m['setting']] = i
                break

        print("\n")
        i = input("Save these settings? [y|N] ")
        if i.lower() != "y":
            return logger.info("Operation cancelled. No changes saved.")
        else:
            self.db.create_user(new_user)

    def edit(self):
        user_settings = self.db.get_user(self.user)
        if not user_settings:
            return logger.error(f"User {self.user} was not found")

        menu = [
            {'setting': 'name', 'type': str, 'text': 'User name', 'allowed': []},
            {'setting': 'email', 'type': str, 'text': 'Email address', 'allowed': []},
            {'setting': 'alerts', 'type': int, 'text': 'Alerts', 'allowed': [0, 1]},
            {'setting': 'bitrate', 'type': int, 'text': 'Bitrate', 'allowed': [1, 3, 9]},
            {'setting': 'record_type', 'type': str, 'text': 'Record Type', 'allowed': ["all", "album", "ep", "single"]},
            {'setting': 'plex_baseurl', 'type': str, 'text': 'Plex Base URL', 'allowed': []},
            {'setting': 'plex_token', 'type': str, 'text': 'Plex Token', 'allowed': []},
            {'setting': 'plex_library', 'type': str, 'text': 'Plex Library', 'allowed': []},
            {'setting': 'download_path', 'type': str, 'text': 'Download Path', 'allowed': []},
        ]

        modified = 0
        for m in menu:
            repeat = True
            while repeat:
                i = input(m['text'] + " [" + str(user_settings[m['setting']]) + "]: ")
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
                if m['setting'] == "name" and self.user != i:
                    if self.db.get_user(i):
                        print(" - Name already in use: " + i)
                        continue
                user_settings[m['setting']] = i
                modified += 1
                break

        if modified > 0:
            print("\n")
            i = input("Save these settings? [y|N] ")
            if i.lower() != "y":
                return logger.info("Operation cancelled. No changes saved.")
            else:
                self.db.update_user(user_settings)
        else:
            print("No changes made, exiting...")

    def delete(self):
        user_settings = self.db.get_user(self.user)
        if not user_settings:
            return logger.error(f"User {self.user} not found")

        if user_settings['user_id'] == 1:
            return logger.info("You cannot delete the primary user.")

        i = input("To confirm, please type the username: ")
        if i.lower() == self.user.lower():
            self.db.delete_user(self.user)
            return logger.info("User " + self.user + " deleted.")
        else:
            return logger.info("Username did not match, cancelled.")

    def show(self):
        if not self.user:
            user = self.db.get_all_users()
        else:
            user = [self.db.get_user(self.user)]
            if len(user) == 0:
                return logger.error(f"User {self.user} not found")

        print("{:<10} {:<40} {:<8} {:<8} {:<8} {:<25} "
              "{:<20} {:<20} {:<20}".format('Name', 'Email', 'Alerts', 'Bitrate', 'Type',
                                            'Plex Base URL', 'Plex Token', 'Plex Library', 'Download Path'))
        for u in user:
            id, name, email, active, alerts, bitrate, rtype, \
            url, token, lib, dl_path = [x if x is not None else '' for x in u.values()]
            print("{:<10} {:<40} {:<8} {:<8} {:<8} {:<25} "
                  "{:<20} {:<20} {:<20}".format(name, email, alerts, bitrate, rtype, url, token, lib, dl_path))


class AppConfig:
    def __init__(self):
        pass


class LoadUser(object):
    def __init__(self, profile: dict):
        logger.debug("Loading user config for ID " + str(profile['user_id']))
        for key, value in profile.items():
            if value is None:
                continue
            if config.get_config().get(key):
                config.set(key, value, validate=False)
