import logging

from deemon.core.config import Config as config
from deemon.core.db import Database

logger = logging.getLogger(__name__)


class ProfileConfig:
    def __init__(self, profile_name):
        self.db = Database()
        self.profile_name = profile_name
        self.profile = None

    # TODO move this to utils
    @staticmethod
    def print_header(message: str = None):
        print("deemon Profile Editor")
        if message:
            print(":: " + message + "\n")
        else:
            print("")

    def edit(self):
        profile = self.db.get_profile(self.profile_name)
        self.print_header(f"Configuring '{profile['name']}' (Profile ID: {profile['id']})")
        modified = 0
        for property in profile:
            if property == "id":
                continue
            allowed_opts = config.allowed_values(property)
            if isinstance(allowed_opts, dict):
                allowed_opts = [str(x.lower()) for x in allowed_opts.values()]

            while True:
                friendly_text = property.replace("_", " ").title()
                user_input = input(f"{friendly_text} [{profile[property]}]: ").lower()
                if user_input == "":
                    break
                # TODO move to function to share with Config.set()?
                elif user_input == "false" or user_input == "0":
                    user_input = False
                elif user_input == "true" or user_input == "1":
                    user_input = True
                elif property == "name" and self.profile_name != user_input:
                    if self.db.get_profile(user_input):
                        print("Name already in use")
                        continue
                if user_input == "none" and property != "name":
                    user_input = None
                elif allowed_opts:
                    if user_input not in allowed_opts:
                        print(f"Allowed options: " + ', '.join(str(x) for x in allowed_opts))
                        continue
                logger.debug(f"User set {property} to {user_input}")
                profile[property] = user_input
                modified += 1
                break

        if modified > 0:
            user_input = input("\n:: Save these settings? [y|N] ")
            if user_input.lower() != "y":
                logger.info("No changes made, exiting...")
            else:
                self.db.update_profile(profile)
                print(f"\nProfile '{profile['name']}' has been updated!")
        else:
            print("No changes made, exiting...")

    def add(self):
        new_profile = {}
        profile_config = self.db.get_profile(self.profile_name)
        if profile_config:
            return logger.error(f"Profile {self.profile_name} already exists")
        else:
            logger.info("Adding new profile: " + self.profile_name)
            print("** Any option left blank will fallback to global config **\n")
            new_profile['name'] = self.profile_name

        menu = [
            {'setting': 'email', 'type': str, 'text': 'Email address', 'allowed': []},
            {'setting': 'alerts', 'type': bool, 'text': 'Alerts', 'allowed': config.allowed_values('alerts')},
            {'setting': 'bitrate', 'type': str, 'text': 'Bitrate',
             'allowed': config.allowed_values('bitrate').values()},
            {'setting': 'record_type', 'type': str, 'text': 'Record Type',
             'allowed': config.allowed_values('record_type')},
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

    def delete(self):
        profile_config = self.db.get_profile(self.profile_name)
        if not profile_config:
            return logger.error(f"Profile {self.profile_name} not found")

        if profile_config['id'] == 1:
            return logger.info("You cannot delete the default profile.")

        i = input(f":: Remove the profile '{self.profile_name}'? [y|N] ")
        if i.lower() == "y":
            self.db.delete_profile(self.profile_name)
            return logger.info("Profile " + self.profile_name + " deleted.")
        else:
            return logger.info("Operation cancelled")

    def show(self):
        if not self.profile_name:
            profile = self.db.get_all_profiles()
            self.print_header(f"Showing all profiles")
        else:
            profile = [self.db.get_profile(self.profile_name)]
            self.print_header(f"Showing profile '{profile[0]['name']}' (Profile ID: {profile[0]['id']})")
            if len(profile) == 0:
                return logger.error(f"Profile {self.profile_name} not found")

        print("{:<10} {:<40} {:<8} {:<8} {:<8} {:<25} "
              "{:<20} {:<20} {:<20}".format('Name', 'Email', 'Alerts', 'Bitrate', 'Type',
                                            'Plex Base URL', 'Plex Token', 'Plex Library', 'Download Path'))
        for u in profile:
            id, name, email, alerts, bitrate, rtype, url, token, \
            lib, dl_path = [x if x is not None else '' for x in u.values()]
            print("{:<10} {:<40} {:<8} {:<8} {:<8} {:<25} "
                  "{:<20} {:<20} {:<20}".format(name, email, alerts, bitrate, rtype, url, token, lib, dl_path))
            print("")

    def clear(self):
        profile = self.db.get_profile(self.profile_name)
        self.print_header(f"Configuring '{profile['name']}' (Profile ID: {profile['id']})")
        if not profile:
            return logger.error(f"Profile {self.profile_name} not found")

        for value in profile:
            if value in ["id", "name"]:
                continue
            profile[value] = None
        self.db.update_profile(profile)
        logger.info("All values have been cleared.")
