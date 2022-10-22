from deemon.core.config import Config as config
from deezer import Deezer
import logging
import re

logger = logging.getLogger(__name__)

dz = Deezer()


def exclusion_test(url):
    match = False

    try:
        id_from_url = url.split(f'/album/')[1]
        id_from_share_url = id_from_url.split('?')[0]

        url_id = int(id_from_share_url)
        logger.debug(f"Extracted id={url_id}")
    except (IndexError, ValueError) as e:
        logger.info(f"Invalid url: {url}")
    else:
        album = dz.api.get_album(url_id)
        print(f"Artist: {album['artist']['name']}")
        print(f"Album: {album['title']}\n")

        if config.exclusion_patterns():
            print("Checking for the following patterns:")

            for i, pattern in enumerate(config.exclusion_patterns(), start=1):
                if re.search(pattern, album['title'].lower()):
                    print(f"  {i}.  {pattern}   >>   ** MATCH **")
                    match = True
                else:
                    print(f"  {i}.  {pattern}   >>   NO MATCH")

        if config.exclusion_keywords():
            print("\nChecking for the following keywords:")

            for i, keyword in enumerate(config.exclusion_keywords(), start=1):
                if re.search(r'\(([^)]+)\)|\[([^)]+)]', album['title'].lower()):
                    print(f"  {i}.  {keyword}   >>   ** MATCH **")
                    match = True
                else:
                    print(f"  {i}.  {keyword}   >>   NO MATCH")

            if match:
                print("\nResult: This release would be excluded")
            else:
                print("\nResult: This release would NOT be excluded")
