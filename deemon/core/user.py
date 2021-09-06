from deemon.core.config import Config


class User(object):
    def __init__(self, profile: dict):
        config = Config()
        print(config.get_config())
        print("")
        for key, value in profile.items():
            if value is None:
                print("Skipping None value on key ", key)
                continue
            if config.get_config().get(key):
                print("Before: " + key, str(config.get_config().get(key)))
                config.set(key, value)
                print("After: " + key, str(config.get_config().get(key)))
            else:
                print("ERROR: key does not exist: " + key, value)



p = {'user_id': 1, 'name': 'default', 'email': "shawn.eggleston@icloud.com", 'active': None, 'alerts': None, 'bitrate': 9, 'record_type': "all", 'plex_baseurl': None, 'plex_token': None, 'plex_library': None}
u = User(p)