import logging

from deemon.core.config import Config as config
from deemon.core.db import Database

logger = logging.getLogger(__name__)
db = Database()


def print_header(message: str = None):
    from os import system, name
    if name == 'nt':
        _ = system('cls')
    else:
        _ = system('clear')
    print("deemon Artist Configurator")
    if message:
        print(":: " + message + "\n")
    else:
        print("")


def get_artist(query: str):
    artist_as_id = False
    artist_fromdb = None

    try:
        artist_as_id = int(query)
    except ValueError:
        pass

    by_name = db.get_monitored_artist_by_name(query)
    if by_name:
        logger.debug("Artist found by name")
        artist_fromdb = by_name

    if artist_as_id:
        by_id = db.get_monitored_artist_by_id(artist_as_id)
        if by_id:
            logger.debug(f"Artist found by ID")
            if not artist_fromdb:
                artist_fromdb = by_id
            else:
                logger.debug("Artist found by both ID and name, prompting user")

                while True:
                    prompt = input(":: Multiple artists found. Was that a name or ID? ")
                    if prompt.lower() == "name":
                        logger.debug("Artist confirmed by user to be a name")
                        return artist_fromdb
                    elif prompt.lower() == "id":
                        logger.debug("Artist confirmed by user to be an ID")
                        return by_id
        else:
            return logger.error(f"Artist/Artist ID not found for '{query}'")

    if artist_fromdb:
        return artist_fromdb
    else:
        return logger.error(f"Artist/Artist ID not found for '{query}'")


def artist_lookup(query):
    result = get_artist(query)
    if not result:
        return
    print_header(f"Configuring '{result['artist_name']}' (Artist ID: {result['artist_id']})")
    modified = 0
    for property in result:
        if property not in ['alerts', 'bitrate', 'record_type', 'download_path']:
            continue
        allowed_opts = config.allowed_values(property)
        if isinstance(allowed_opts, dict):
            allowed_opts = [str(x.lower()) for x in allowed_opts.values()]

        while True:
            friendly_text = property.replace("_", " ").title()
            user_input = input(f"{friendly_text} [{result[property]}]: ").lower()
            if user_input == "":
                break
            elif user_input == "false" or user_input == "0":
                user_input = False
            elif user_input == "true" or user_input == "1":
                user_input = True
            if user_input == "none":
                user_input = None
            elif allowed_opts:
                if user_input not in allowed_opts:
                    print(f"Allowed options: " + ', '.join(str(x) for x in allowed_opts))
                    continue
            logger.debug(f"User set {property} to {user_input}")
            result[property] = user_input
            modified += 1
            break
    if modified > 0:
        i = input("\n:: Save these settings? [y|N] ")
        if i.lower() != "y":
            logger.info("No changes made, exiting...")
        else:
            db.update_artist(result)
            print(f"\nArtist '{result['artist_name']}' has been updated!")
    else:
        print("No changes made, exiting...")
