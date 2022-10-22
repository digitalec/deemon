import re
import logging
from deemon.core.config import Config as config

logger = logging.getLogger(__name__)


def exclude_filtered_versions(albums: list) -> list:
    """ Remove album versions containing specified text """
    exclusion_patterns = config.exclusion_patterns()
    exclusion_keywords = config.exclusion_keywords()
    allowed = []

    if exclusion_keywords or exclusion_patterns:
        for album in albums:
            album_title = album['title']
            exclusion_pattern_match = [p for p in exclusion_patterns if re.search(p, album_title)]
            keyword_search = re.search(r'\(([^)]+)\)|\[([^)]+)]', album_title.lower())
            exclusion_keyword_match = [e for e in exclusion_keywords if keyword_search and e in keyword_search.group()]
            result = exclusion_pattern_match + exclusion_keyword_match
            result = '", "'.join(result)

            if exclusion_keyword_match or exclusion_pattern_match:
                logger.info(f"    Album \"{album_title}\" excluded by filter: \"{result}\"")
                continue
            else:
                allowed.append(album)
        return allowed
    else:
        return albums
